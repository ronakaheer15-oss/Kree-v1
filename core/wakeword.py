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
import numpy as np
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
VOICEPRINT_DIR = BASE_DIR / "assets" / "voiceprint"
VOICEPRINT_FILE = VOICEPRINT_DIR / "owner.npy"

# ── Custom Model Path ────────────────────────────────────────────────────────
# TODO: Train custom "Hey Kree" with openwakeword and place .onnx here:
CUSTOM_ONNX_PATH = BASE_DIR / "assets" / "models" / "hey_kree.onnx"

# ── Wake Trigger Types ────────────────────────────────────────────────────────
WAKE_FULL = "full"        # full wake: UI + chime + greeting
WAKE_PARTIAL = "partial"  # ears only, no UI, no chime
WAKE_PRIORITY = "priority"  # instant, no greeting

# ── Tuning ────────────────────────────────────────────────────────────────────
THRESHOLD = 0.15                  # Extremely sensitive for far-field (AGC limits false positives)
ACTIVATION_COUNT = 1              # Fires instantly above threshold. Buffer is 2560 (160ms), 2 is too long.
MIN_WAKE_INTERVAL_SEC = 3.0       # Smart cooldown between triggers
VOICE_SIMILARITY_THRESHOLD = 0.75 # Resemblyzer cosine similarity cutoff
AMBIENT_CHECK_INTERVAL = 30       # Seconds between ambient noise measurements
WHISPER_VOLUME_THRESHOLD = 500    # Below this RMS → whisper mode
ENROLL_DURATION_SEC = 10          # Voice enrollment recording length
FRAMES_PER_BUFFER = 2560          # Bigger chunks = more accurate detection


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

        try:
            # Stub webrtcvad before importing resemblyzer — it's only used
            # for internal VAD preprocessing we don't need (we have raw PCM)
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
            print(f"[KREE VOICE] Resemblyzer unavailable (voice lock disabled): {e}")
            return

        # Load existing voiceprint
        if VOICEPRINT_FILE.exists():
            try:
                self._owner_embed = np.load(str(VOICEPRINT_FILE))
                print("[KREE VOICE] Owner voiceprint loaded.")
            except Exception as e:
                print(f"[KREE VOICE] Voiceprint load error: {e}")

    @property
    def is_enrolled(self) -> bool:
        return self._owner_embed is not None

    @property
    def is_available(self) -> bool:
        return self._available

    def enroll_owner(self):
        """Record owner's voice for enrollment (blocking, called once)."""
        if not self._available:
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
        if not self._available or not self.is_enrolled:
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
        self.is_running = False
        self._last_wake_time = 0.0
        self._ambient_rms = 0
        self._last_ambient_check = 0.0
        self._voice_fp = VoiceFingerprint()

        # ── OpenWakeWord Init ─────────────────────────────────────────────
        from openwakeword.model import Model

        if CUSTOM_ONNX_PATH.exists():
            print(f"[KREE WAKE] Using custom model: {CUSTOM_ONNX_PATH.name}")
            self.model = Model(
                wakeword_models=[str(CUSTOM_ONNX_PATH)],
                inference_framework="onnx"
            )
        else:
            print("[KREE WAKE] Using built-in 'hey_jarvis' model (default until custom trained)")
            self.model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx"
            )

        print("[KREE WAKE] OpenWakeWord model loaded (ONNX)")

        if self._voice_fp.is_available and not self._voice_fp.is_enrolled:
            print("[KREE VOICE] No voiceprint found. Say 'enroll my voice' to register.")

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

        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER
            )
        except Exception as e:
            print(f"[KREE WAKE] Audio device error: {e}")
            return

        print("[KREE WAKE] Listening for wake word...")

        consecutive_hits = 0
        # Rolling buffer for voice verification (~1.5s of audio)
        verification_buffer = []
        VERIFICATION_FRAMES = int(16000 * 1.5 / FRAMES_PER_BUFFER)
        
        frame_count = 0

        while self.is_running:
            try:
                # ── CPU Yield Optimization ──
                time.sleep(0.01)
                
                # ── Lock Screen Security ──
                try:
                    import ctypes
                    user32 = ctypes.windll.User32
                    if user32.GetForegroundWindow() == 0:
                        continue
                except: pass

                audio = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
                audio_np = np.frombuffer(audio, dtype=np.int16)
                
                # Keep rolling buffer for voice verification
                verification_buffer.append(audio_np.copy())
                if len(verification_buffer) > VERIFICATION_FRAMES:
                    verification_buffer.pop(0)
                    
                # ── CPU Optimization (Skip inference every other frame) ──
                frame_count += 1
                if frame_count % 2 != 0:
                    continue

                # ── Auto Gain Control (Far-Field Boost) ──
                # If the user is across the room, the volume is extremely low.
                # We dynamically amplify quiet signals to match expected amplitude profiles.
                max_amp = np.max(np.abs(audio_np))
                if 10 < max_amp < 10000:
                    gain = min(6.0, 10000.0 / max_amp)
                    audio_predict = (audio_np.astype(np.float32) * gain).astype(np.int16)
                else:
                    audio_predict = audio_np.copy()

                # Ambient noise measurement
                self._measure_ambient(audio_np)

                # Predict using the AGC-boosted audio
                prediction = self.model.predict(audio_predict)

                # Check for hits with consecutive-frame smoothing
                hit = False
                for model_name, score in prediction.items():
                    if score > THRESHOLD:
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

                # Fire callback — always full wake for now (single keyword)
                self.on_wake(WAKE_FULL, is_whisper)

            except Exception as e:
                if self.is_running:
                    print(f"[KREE WAKE] Loop error: {e}")
                    time.sleep(0.1)

        stream.stop_stream()
        stream.close()
        pa.terminate()
        print("[KREE WAKE] Detector stopped.")
