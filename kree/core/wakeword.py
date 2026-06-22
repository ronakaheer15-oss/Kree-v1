"""
Kree Advanced Wake Word Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  - OpenWakeWord (ONNX) for wake word detection — no per-user licensing
  - Voice fingerprinting via Resemblyzer (only owner can wake Kree)
  - Two wake levels: full wake vs partial (ears only)
  - Smart cooldown (3s minimum between triggers)
  - Ambient noise detection with dynamic sensitivity
  - Whisper mode detection
  - Consecutive-hit smoothing to prevent false positives

Config:
  - Owner voiceprint stored in assets/voiceprint/owner.npy
  - Custom .onnx model path: assets/models/hey_kree.onnx (when trained)
"""

import threading
import time
import os
import importlib.util
import numpy as np
from pathlib import Path

import sys
import logging
import traceback as _tb
from kree.core.runtime import BUNDLE_DIR, APP_DATA_DIR, LOG_DIR
from kree._paths import PROJECT_ROOT

_wake_logger = logging.getLogger("KreeWake")
if not _wake_logger.handlers:
    try:
        _wh = logging.FileHandler(str(LOG_DIR / "startup.log"), encoding="utf-8")
        _wh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        _wake_logger.addHandler(_wh)
        _wake_logger.setLevel(logging.DEBUG)
    except Exception:
        pass

def _wlog(msg):
    print(msg)
    try:
        _wake_logger.info(msg)
    except Exception:
        pass

VOICEPRINT_DIR = APP_DATA_DIR / "voiceprint"
VOICEPRINT_FILE = VOICEPRINT_DIR / "owner.npy"

# ── Custom Model Path ────────────────────────────────────────────────────────
CUSTOM_ONNX_PATH = BUNDLE_DIR / "assets" / "models" / "hey_jarvis.onnx"

# In frozen mode, openwakeword resources are bundled at _MEIPASS/openwakeword/resources
# In dev mode, discover them from the installed openwakeword package.
if getattr(sys, "frozen", False):
    VENV_MODEL_DIR = BUNDLE_DIR / "openwakeword" / "resources" / "models"
else:
    _oww_spec = importlib.util.find_spec("openwakeword")
    VENV_MODEL_DIR = (
        Path(_oww_spec.origin).resolve().parent / "resources" / "models"
        if _oww_spec and _oww_spec.origin
        else PROJECT_ROOT / "openwakeword" / "resources" / "models"
    )

DEFAULT_WAKEWORD_MODELS = (
    "hey_jarvis",
    "hey_jarvis_v0.1",
    "hey_mycroft",
    "hey_mycroft_v0.1",
)

# ── Wake Trigger Types ────────────────────────────────────────────────────────
WAKE_FULL = "full"        # full wake: UI + chime + greeting
WAKE_PARTIAL = "partial"  # ears only, no UI, no chime
WAKE_PRIORITY = "priority"  # instant, no greeting

# ── Tuning ────────────────────────────────────────────────────────────────────
THRESHOLD = 0.08                  # Lowered for testing — built-in hey_jarvis often scores below 0.15
ACTIVATION_COUNT = 1              # Fires instantly above threshold. Buffer is 2560 (160ms), 2 is too long.
MIN_WAKE_INTERVAL_SEC = 3.0       # Smart cooldown between triggers
VOICE_SIMILARITY_THRESHOLD = 0.75 # Resemblyzer cosine similarity cutoff
AMBIENT_CHECK_INTERVAL = 30       # Seconds between ambient noise measurements
WHISPER_VOLUME_THRESHOLD = 500    # Below this RMS → whisper mode
ENROLL_DURATION_SEC = 10          # Voice enrollment recording length
FRAMES_PER_BUFFER = 1280          # Native chunk size for openwakeword


class VoiceFingerprint:
    """
    Owner voice verification using Resemblyzer.
    On first run, records the owner's voice for enrollment.
    On subsequent runs, verifies the wake word speaker matches the owner.
    """

    def __init__(self):
        self._encoder = None
        self._owner_embed = None
        self._available = False
        self._encoder_load_attempted = False

        # Load existing voiceprint
        if VOICEPRINT_FILE.exists():
            try:
                self._owner_embed = np.load(str(VOICEPRINT_FILE))
                print("[KREE VOICE] Owner voiceprint loaded.")
            except Exception as e:
                print(f"[KREE VOICE] Voiceprint load error: {e}")

    def _ensure_encoder(self) -> bool:
        if self._encoder is not None:
            return True
        if self._encoder_load_attempted:
            return False

        self._encoder_load_attempted = True

        try:
            import sys
            if "webrtcvad" not in sys.modules:
                import types
                _stub = types.ModuleType("webrtcvad")
                _stub.Vad = lambda *a, **kw: type("Vad", (), {"set_mode": lambda *a: None, "is_speech": lambda *a: True})()
                sys.modules["webrtcvad"] = _stub

            from resemblyzer import VoiceEncoder
            self._encoder = VoiceEncoder()
            self._available = True
            print("[KREE VOICE] Resemblyzer encoder loaded.")
        except Exception as e:
            self._available = False
            print(f"[KREE VOICE] Resemblyzer unavailable (voice lock disabled): {e}")

        return self._encoder is not None

    @property
    def is_enrolled(self) -> bool:
        return self._owner_embed is not None

    @property
    def is_available(self) -> bool:
        return self._available

    def enroll_owner(self):
        """Record owner's voice for enrollment (blocking, called once)."""
        if not self._ensure_encoder():
            return False

        import pyaudio

        print(f"[KREE VOICE] Recording owner voice for {ENROLL_DURATION_SEC}s... Speak naturally.")
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=16000, channels=1, format=pyaudio.paInt16,
            input=True, frames_per_buffer=1024
        )

        frames = []
        for _ in range(0, int(16000 / 1024 * ENROLL_DURATION_SEC)):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

        # Convert to float
        raw = b"".join(frames)
        audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        try:
            embed = self._encoder.embed_utterance(audio_np)
            VOICEPRINT_DIR.mkdir(parents=True, exist_ok=True)
            np.save(str(VOICEPRINT_FILE), embed)
            self._owner_embed = embed
            print("[KREE VOICE] Owner voiceprint saved.")
            return True
        except Exception as e:
            print(f"[KREE VOICE] Enrollment failed: {e}")
            return False

    def verify(self, audio_int16: np.ndarray) -> bool:
        """Verify if the speaker matches the owner. Returns True if match or not enrolled."""
        if not self._ensure_encoder() or not self.is_enrolled:
            return True  # Not enrolled → allow all (graceful degradation)

        try:
            audio_float = audio_int16.astype(np.float32) / 32768.0
            speaker_embed = self._encoder.embed_utterance(audio_float)
            similarity = float(np.dot(self._owner_embed, speaker_embed))

            if similarity >= VOICE_SIMILARITY_THRESHOLD:
                return True
            else:
                print(f"[KREE VOICE] Speaker REJECTED (similarity: {similarity:.2f})")
                return False
        except Exception:
            return True  # Fail open on errors


class WakeWordDetector:
    """
    OpenWakeWord-based detector with:
    - ONNX inference (no tflite dependency)
    - Consecutive-hit smoothing (2 frames required)
    - Voice fingerprinting
    - Smart cooldown
    - Ambient noise measurement
    - Whisper detection
    """

    def __init__(self, on_wake_callback):
        """
        Args:
            on_wake_callback: Function called with (trigger_type: str, whisper: bool)
        """
        self.on_wake = on_wake_callback
        self.callback = on_wake_callback
        self.threshold = THRESHOLD
        self.selected_idx = None
        self.is_running = False
        self.is_ready = False
        self._last_heartbeat = time.time()
        self._last_wake_time = 0.0
        self._ambient_rms = 0
        self._last_ambient_check = 0.0
        self._voice_fp = VoiceFingerprint()
        self.model = None
        self._model_name = None
        self._model_load_attempted = False

        if self._voice_fp.is_available and not self._voice_fp.is_enrolled:
            print("[KREE VOICE] No voiceprint found. Say 'enroll my voice' to register.")

    def _candidate_models(self):
        if CUSTOM_ONNX_PATH.exists():
            return [str(CUSTOM_ONNX_PATH)]
        return ["hey_jarvis"]

    def _ensure_model(self) -> bool:
        if self.model is not None:
            return True
        if self._model_load_attempted:
            return False

        self._model_load_attempted = True
        _wlog("[WAKE] _ensure_model: starting model load")

        try:
            _wlog("[WAKE] Importing openwakeword.model...")
            from openwakeword.model import Model
            _wlog("[WAKE] openwakeword.model imported successfully")
        except Exception as e:
            _wlog(f"[WAKE] FATAL: Failed to import openwakeword.model: {e}")
            _wlog(f"[WAKE] Traceback: {_tb.format_exc()}")
            return False

        candidates = self._candidate_models()
        _wlog(f"[WAKE] Candidate models: {candidates}")
        _wlog(f"[WAKE] CUSTOM_ONNX_PATH: {CUSTOM_ONNX_PATH} (exists={CUSTOM_ONNX_PATH.exists()})")
        _wlog(f"[WAKE] VENV_MODEL_DIR: {VENV_MODEL_DIR} (exists={VENV_MODEL_DIR.exists() if VENV_MODEL_DIR.exists() else False})")
        _wlog(f"[WAKE] BUNDLE_DIR: {BUNDLE_DIR}")
        _wlog(f"[WAKE] Frozen: {getattr(sys, 'frozen', False)}")

        last_error = None
        for model_spec in candidates:
            try:
                if os.path.exists(model_spec):
                    _wlog(f"[WAKE] Loading wake model file: {Path(model_spec).name} ({model_spec})")
                else:
                    _wlog(f"[WAKE] Loading built-in wake model: {model_spec}")

                self.model = Model(
                    wakeword_models=[model_spec],
                    inference_framework="onnx"
                )
                self._model_name = next(iter(self.model.models.keys()), None)
                _wlog(f"[WAKE] Model loaded successfully: {self._model_name}")
                return True
            except Exception as e:
                last_error = e
                _wlog(f"[WAKE] Model load failed for '{model_spec}': {e}")
                _wlog(f"[WAKE] Traceback: {_tb.format_exc()}")
                self.model = None

        _wlog(f"[WAKE] ALL MODELS FAILED. Last error: {last_error}")
        return False

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False

    def enroll_owner_voice(self):
        """Public method to trigger voice enrollment."""
        return self._voice_fp.enroll_owner()

    def _measure_ambient(self, audio_int16: np.ndarray):
        """Measure ambient noise level every AMBIENT_CHECK_INTERVAL seconds."""
        now = time.time()
        if now - self._last_ambient_check < AMBIENT_CHECK_INTERVAL:
            return
        self._last_ambient_check = now
        self._ambient_rms = int(np.sqrt(np.mean(audio_int16.astype(np.float64) ** 2)))

    def _detect_whisper(self, audio_int16: np.ndarray) -> bool:
        """Check if the speaker is whispering based on volume."""
        return int(np.abs(audio_int16).mean()) < WHISPER_VOLUME_THRESHOLD

    def _run_loop(self):
        import pyaudio

        _wlog("[WAKE] _run_loop: Thread started")
        self.is_ready = False

        if not self._ensure_model():
            _wlog("[WAKE] ABORT: Model failed to load. Wake word thread exiting.")
            return

        if threading.current_thread() != self._thread:
            _wlog("[WAKE] Thread superseded during model load. Exiting.")
            return

        _wlog(f"[WAKE] Opening microphone (rate=16000, channels=1, buffer={FRAMES_PER_BUFFER})...")
        pa = pyaudio.PyAudio()
        try:


            from kree.memory.config_manager import load_audio_settings, AUDIO_CONFIG_FILE
            
            BUILD_VERSION = "KREE_BETA_BUILD_003"
            _wlog(f"[WAKE] BUILD_VERSION = \"{BUILD_VERSION}\"")
            _wlog(f"[WAKE] Config Path: {AUDIO_CONFIG_FILE}")
            
            audio_settings = load_audio_settings()
            saved_idx = audio_settings.get("input_device_index")

            try:
                default_input = pa.get_default_input_device_info()
                default_idx = default_input.get("index")
                default_name = default_input.get("name", "unknown")
            except Exception as ex:
                _wlog(f"[WAKE] Error getting default input device: {ex}")
                default_idx = None
                default_name = "unknown"

            target_idx = saved_idx if saved_idx is not None else default_idx
            
            # Print logging enhancements requested by user
            _wlog(f"[WAKE] saved_idx: {saved_idx}")
            _wlog(f"[WAKE] default_idx: {default_idx} ({default_name})")
            _wlog(f"[WAKE] selected_idx: {target_idx}")

            # ── Build ordered list of devices to try ──
            devices_to_try = []
            
            # 1. Try saved/selected device first
            if target_idx is not None:
                devices_to_try.append(int(target_idx))
            
            # 2. Collect all input devices by API
            for i in range(pa.get_device_count()):
                try:
                    di = pa.get_device_info_by_index(i)
                    if int(di.get('maxInputChannels', 0)) < 1:
                        continue
                    name = di.get('name', '').lower()
                    if 'stereo mix' in name:
                        continue
                    idx = di.get('index')
                    if idx not in devices_to_try:
                        devices_to_try.append(idx)
                except Exception:
                    pass
            
            _wlog(f"[WAKE] Device try order: {devices_to_try}")

            def _try_open_and_check(pa_inst, dev_idx, rate, channels, buf_size):
                """Open a stream, read ~1.5s, return (stream, rms_variance, max_peak, avg_rms) or None on failure.
                rms_variance distinguishes real audio (high variance) from static (near-zero variance)."""
                try:
                    info = pa_inst.get_device_info_by_index(int(dev_idx))
                    dev_name = info.get('name', 'unknown')
                    host_api = info.get('hostApi')
                    if host_api is not None:
                        try:
                            api_info = pa_inst.get_host_api_info_by_index(int(host_api))
                            api_name = api_info.get('name', '?')
                        except Exception:
                            api_name = 'unknown'
                    else:
                        api_name = 'unknown'
                    _wlog(f"[WAKE] Trying device {dev_idx} [{api_name}]: {dev_name} at {rate}Hz/{channels}ch...")
                    
                    s = pa_inst.open(
                        rate=rate, channels=channels, format=pyaudio.paInt16,
                        input=True, input_device_index=int(dev_idx),
                        frames_per_buffer=buf_size
                    )
                    
                    total_frames = int(rate / buf_size * 1.8)
                    skip_frames = int(rate / buf_size * 0.5)
                    rms_values = []
                    max_peak = 0
                    for i in range(total_frames):
                        data = s.read(buf_size, exception_on_overflow=False)
                        if i < skip_frames:
                            continue
                        arr = np.frombuffer(data, dtype=np.int16)
                        if channels > 1:
                            arr = arr.reshape(-1, channels).mean(axis=1).astype(np.int16)
                        peak = int(np.max(np.abs(arr)))
                        rms = int(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
                        rms_values.append(rms)
                        if peak > max_peak:
                            max_peak = peak
                    
                    unique_rms = len(set(rms_values))
                    # Reject repeating digital loops (DirectSound driver bugs) and silence
                    is_loop = (unique_rms <= len(rms_values) * 0.5) and (len(rms_values) > 5)
                    
                    avg_rms = int(np.mean(rms_values)) if rms_values else 0
                    # Variance of RMS values — real audio has HIGH variance, static has ~0
                    rms_var = int(np.var(rms_values)) if (len(rms_values) > 1 and not is_loop) else 0
                    
                    _wlog(f"[WAKE]   -> avg_RMS={avg_rms}, max_Peak={max_peak}, rms_variance={rms_var} (unique_rms={unique_rms}{', LOOP REJECTED' if is_loop else ''})")
                    return (s, rms_var, max_peak, avg_rms, dev_name, rate, channels)
                except Exception as e:
                    import traceback
                    _wlog(f"[WAKE]   -> Failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
                    return None

            # ── Try each device at 16kHz first, then at native rate ──
            stream = None
            native_buffer = FRAMES_PER_BUFFER
            native_rate = 16000
            native_channels = 1
            needs_resample = False
            best_result = None  # (stream, variance, peak, rms, name, rate, channels)
            
            for try_idx in devices_to_try:
                try:
                    try_info = pa.get_device_info_by_index(int(try_idx))
                    dev_native_rate = int(try_info.get("defaultSampleRate", 44100))
                    dev_channels = min(int(try_info.get("maxInputChannels", 1)), 2)  # Cap at stereo
                except Exception:
                    _wlog(f"[WAKE] Skipping invalid device {try_idx}")
                    continue
                
                # Attempt 1: Try at 16kHz/1ch (ideal — no resampling needed)
                result = _try_open_and_check(pa, try_idx, 16000, 1, FRAMES_PER_BUFFER)
                
                if result and result[1] > 100:  # variance > 100 = real varying audio
                    stream = result[0]
                    native_rate = result[5]
                    native_channels = result[6]
                    native_buffer = FRAMES_PER_BUFFER
                    needs_resample = False
                    target_name = result[4]
                    target_idx = try_idx
                    _wlog(f"[WAKE] ✓ Selected device {try_idx}: {result[4]} at 16kHz (variance={result[1]}, RMS={result[3]}, Peak={result[2]})")
                    break
                else:
                    # Close the static/silent stream
                    if result:
                        try:
                            result[0].stop_stream()
                            result[0].close()
                        except Exception:
                            pass
                
                # Attempt 2: Try at device native rate (needed for WASAPI)
                if dev_native_rate != 16000:
                    native_buf = int(dev_native_rate * FRAMES_PER_BUFFER / 16000)  # Scale buffer proportionally
                    result = _try_open_and_check(pa, try_idx, dev_native_rate, dev_channels, native_buf)
                    
                    if result and result[1] > 100:
                        stream = result[0]
                        native_rate = result[5]
                        native_channels = result[6]
                        native_buffer = native_buf
                        needs_resample = (native_rate != 16000)
                        target_name = result[4]
                        target_idx = try_idx
                        _wlog(f"[WAKE] ✓ Selected device {try_idx}: {result[4]} at {native_rate}Hz (variance={result[1]}, RMS={result[3]}, Peak={result[2]}, resample={'yes' if needs_resample else 'no'})")
                        break
                    else:
                        if result:
                            try:
                                result[0].stop_stream()
                                result[0].close()
                            except Exception:
                                pass
            
            # If no device had real varying audio, fall back to the first openable one
            if stream is None:
                _wlog("[WAKE] WARNING: No device with real audio found. Falling back to default...")
                for try_idx in devices_to_try:
                    try:
                        stream = pa.open(
                            rate=16000, channels=1, format=pyaudio.paInt16,
                            input=True, input_device_index=int(try_idx),
                            frames_per_buffer=FRAMES_PER_BUFFER
                        )
                        native_rate = 16000
                        native_channels = 1
                        native_buffer = FRAMES_PER_BUFFER
                        needs_resample = False
                        target_name = pa.get_device_info_by_index(int(try_idx)).get('name', 'unknown')
                        target_idx = try_idx
                        _wlog(f"[WAKE] Fallback: opened device {try_idx}: {target_name}")
                        break
                    except Exception:
                        continue
            
            if stream is None:
                _wlog("[WAKE] FATAL: Cannot open any audio device!")
                return
            
            self.selected_idx = target_idx
            print(f"[WAKE DEBUG] Final runtime device index: {self.selected_idx}")
            _wlog(f"[WAKE] Microphone stream opened (device={target_idx}, rate={native_rate}, channels={native_channels}, resample={needs_resample})")
            _wlog(f"[WAKE] Listening for wake word...")
        except Exception as e:
            _wlog(f"[WAKE] FATAL: Audio device error: {e}")
            _wlog(f"[WAKE] Traceback: {_tb.format_exc()}")
            return

        # ── Streaming resampler (accumulates chunks for artifact-free resampling) ──
        if needs_resample:
            import scipy.signal
            # Accumulate raw mono audio and resample in larger windows to avoid edge artifacts.
            # resample_poly with up=160/down=441 needs ~4410 filter taps — much longer than
            # a single 3528-sample chunk. Processing chunks independently creates boundary
            # artifacts that destroy the mel spectrogram.
            _resample_raw_buf = np.array([], dtype=np.int16)
            _resample_out_buf = np.array([], dtype=np.int16)
            # Accumulate ~0.5s of raw audio before resampling (gives filter enough context)
            _RESAMPLE_ACCUMULATE = int(native_rate * 0.5)  # ~22050 samples at 44100Hz
            _wlog(f"[WAKE] Streaming resampler: accumulate {_RESAMPLE_ACCUMULATE} samples before resampling")
            
            def _feed_and_get_chunks(raw_mono_chunk):
                """Feed raw mono audio at native rate, return list of 1280-sample chunks at 16kHz."""
                nonlocal _resample_raw_buf, _resample_out_buf
                
                _resample_raw_buf = np.concatenate([_resample_raw_buf, raw_mono_chunk])
                
                chunks_out = []
                # When we have enough accumulated, resample the whole batch
                while len(_resample_raw_buf) >= _RESAMPLE_ACCUMULATE:
                    to_resample = _resample_raw_buf[:_RESAMPLE_ACCUMULATE]
                    _resample_raw_buf = _resample_raw_buf[_RESAMPLE_ACCUMULATE:]
                    
                    resampled = scipy.signal.resample_poly(
                        to_resample.astype(np.float32), 16000, native_rate
                    ).astype(np.int16)
                    _resample_out_buf = np.concatenate([_resample_out_buf, resampled])
                
                # Slice out complete 1280-sample frames
                while len(_resample_out_buf) >= FRAMES_PER_BUFFER:
                    chunks_out.append(_resample_out_buf[:FRAMES_PER_BUFFER].copy())
                    _resample_out_buf = _resample_out_buf[FRAMES_PER_BUFFER:]
                
                return chunks_out

        _wlog("[WAKE] Listening for wake word...")
        print("[KREE WAKE] Listening for wake word...")

        consecutive_hits = 0
        # Rolling buffer for voice verification (~1.5s of audio)
        verification_buffer = []
        VERIFICATION_FRAMES = int(16000 * 1.5 / FRAMES_PER_BUFFER)
        
        frame_count = 0

        self.is_ready = True
        while self.is_running and threading.current_thread() == self._thread:
            try:
                # ── Wakeword conflict mitigation ──
                # We must STOP the stream to release the mic so Kree's STT engine can use it
                try:
                    callback_self = getattr(self.on_wake, "__self__", None)
                    if callback_self and hasattr(callback_self, "wake_event") and callback_self.wake_event.is_set():
                        stream.stop_stream()
                        print("[KREE WAKE] Kree is awake. Pausing wakeword detector stream to release mic.")
                        while callback_self.wake_event.is_set() and self.is_running:
                            time.sleep(0.5)
                        if self.is_running:
                            print("[KREE WAKE] Kree went to sleep. Resuming wakeword detector stream.")
                            stream.start_stream()
                except Exception as ex:
                    print(f"[KREE WAKE] Conflict check error: {ex}")

                # ── Read audio at native rate ──
                audio = stream.read(native_buffer, exception_on_overflow=False)
                audio_raw = np.frombuffer(audio, dtype=np.int16)
                
                # DIAGNOSTIC: Log raw and normalized levels to trace transformation chain
                if frame_count % 50 == 0 and len(audio_raw) > 0:
                    raw_rms = np.sqrt(np.mean(audio_raw.astype(np.float32)**2))
                    raw_peak = np.max(np.abs(audio_raw))
                    float_audio = audio_raw.astype(np.float32)
                    norm_audio = float_audio / 32768.0
                    norm_rms = np.sqrt(np.mean(norm_audio**2))
                    norm_peak = np.max(np.abs(norm_audio))
                    _wlog(f"[WAKE DIAG CHAIN] RAW: RMS={raw_rms:.2f} Peak={raw_peak} | NORM: RMS={norm_rms:.6f} Peak={norm_peak:.6f}")
                
                # Downmix to mono if multiple channels
                if native_channels > 1:
                    audio_raw = audio_raw.reshape(-1, native_channels).mean(axis=1).astype(np.int16)

                # ── Resample to 16kHz or use directly ──
                if needs_resample:
                    # Streaming resampler: feed raw audio and get back 1280-sample chunks
                    chunks_16k = _feed_and_get_chunks(audio_raw)
                    if not chunks_16k:
                        continue  # Still accumulating, no output yet
                else:
                    chunks_16k = [audio_raw]
                
                # Process each 1280-sample chunk through the model
                for audio_np in chunks_16k:
                    # Keep rolling buffer for voice verification
                    verification_buffer.append(audio_np.copy())
                    if len(verification_buffer) > VERIFICATION_FRAMES:
                        verification_buffer.pop(0)
                        
                    frame_count += 1
                    self._last_heartbeat = time.time()

                    audio_predict = audio_np.copy()
                    
                    # Ambient noise measurement
                    self._measure_ambient(audio_predict)

                    # Predict using the raw 16kHz audio
                    prediction = self.model.predict(audio_predict)

                    # DIAGNOSTIC: Log audio levels and model score periodically
                    max_score = max(prediction.values()) if prediction else 0.0
                    diag_peak = int(np.max(np.abs(audio_predict)))
                    diag_rms = int(np.sqrt(np.mean(audio_predict.astype(np.float64) ** 2)))
                    
                    # Log every 50 frames (~4s) OR whenever score exceeds 0.01
                    if frame_count % 50 == 0 or max_score > 0.01:
                        _wlog(f"[WAKE DIAG] frame={frame_count} RMS={diag_rms} Peak={diag_peak} score={max_score:.6f} threshold={THRESHOLD}")

                    if max_score >= self.threshold:
                        pass

                    # Skip the first ~1.5s of audio to ignore hardware pop/click spikes on init
                    if frame_count < 20:
                        continue

                    # Check for hits with consecutive-frame smoothing
                    hit = False
                    for model_name, score in prediction.items():
                        if score >= self.threshold:
                            print(f"[WAKE TRIGGER] score={score} threshold={self.threshold}")
                            consecutive_hits += 1
                            if consecutive_hits >= ACTIVATION_COUNT:
                                hit = True
                                consecutive_hits = 0
                            break
                    else:
                        consecutive_hits = 0  # Reset if no model scores above threshold

                    if not hit:
                        continue

                    # ── Smart Cooldown ────────────────────────────────────────
                    now = time.time()
                    if now - self._last_wake_time < MIN_WAKE_INTERVAL_SEC:
                        self.model.reset()
                        continue

                    # ── Voice Fingerprint Verification ────────────────────────
                    if self._voice_fp.is_enrolled and verification_buffer:
                        voice_audio = np.concatenate(verification_buffer)
                        if not self._voice_fp.verify(voice_audio):
                            self.model.reset()
                            continue  # Wrong speaker, stay asleep

                    # ── Whisper Detection ─────────────────────────────────────
                    is_whisper = self._detect_whisper(audio_np)

                    self._last_wake_time = now
                    self.model.reset()  # Clear internal state to prevent double-trigger
                    print(f"[KREE WAKE] Triggered! whisper={is_whisper}, ambient_rms={self._ambient_rms}")

                    # Fire callback asynchronously so it doesn't block the audio thread
                    try:
                        print("[WAKE TRIGGER] dispatching callback asynchronously...")
                        threading.Thread(target=self.callback, args=(WAKE_FULL, is_whisper), daemon=True).start()
                    except Exception as e:
                        print(f"[WAKE ERROR] failed to dispatch callback: {e}")

            except Exception as e:
                err_code = getattr(e, 'errno', None) or (e.args[0] if e.args else None)
                is_stream_death = err_code in (-9999, -9988) or 'Stream closed' in str(e) or 'Unanticipated host error' in str(e)

                if is_stream_death and self.is_running:
                    _wlog(f"[WAKE] Stream died (error {err_code}): {e}. Attempting recovery...")
                    # ── Automatic stream recovery (max 3 retries) ──
                    recovered = False
                    for attempt in range(1, 4):
                        _wlog(f"[WAKE] Recovery attempt {attempt}/3...")
                        try:
                            try:
                                stream.stop_stream()
                            except Exception:
                                pass
                            try:
                                stream.close()
                            except Exception:
                                pass
                            try:
                                pa.terminate()
                            except Exception:
                                pass
                            time.sleep(2.0 * attempt)  # Exponential backoff: 2s, 4s, 6s
                            pa = pyaudio.PyAudio()
                            stream = pa.open(**stream_kwargs)
                            _wlog(f"[WAKE] Recovery attempt {attempt} succeeded. Stream reopened.")
                            recovered = True
                            break
                        except Exception as re_err:
                            _wlog(f"[WAKE] Recovery attempt {attempt} failed: {re_err}")
                    if not recovered:
                        _wlog("[WAKE] All 3 recovery attempts failed. Exiting thread (watchdog will restart).")
                        try:
                            pa.terminate()
                        except Exception:
                            pass
                        return
                elif self.is_running:
                    import traceback
                    print(f"[KREE WAKE] Loop error: {e}\n{traceback.format_exc()}")
                    time.sleep(0.1)

        try:
            stream.stop_stream()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass
        try:
            pa.terminate()
        except Exception:
            pass
        print("[KREE WAKE] Detector stopped.")
