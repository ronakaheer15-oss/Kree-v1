import pytest
from unittest.mock import MagicMock
import numpy as np
import threading

# Restore real numpy for testing to bypass MockModule in conftest.py
import sys
mock_numpy = sys.modules.get('numpy')
if mock_numpy:
    del sys.modules['numpy']
try:
    import numpy as real_np
    sys.modules['numpy'] = real_np
except ImportError:
    if mock_numpy:
        sys.modules['numpy'] = mock_numpy

# Create a mock for pyaudio before importing wakeword
mock_pyaudio = MagicMock()
sys.modules['pyaudio'] = mock_pyaudio

from kree.core.wakeword import WakeWordDetector

def test_wakeword_device_selection(monkeypatch):
    detector = WakeWordDetector(lambda t, w: None)
    
    mock_pa = MagicMock()
    
    def get_device_info_by_index(idx):
        return {"index": idx, "name": f"Device {idx}", "defaultSampleRate": 16000, "maxInputChannels": 1}
    
    mock_pa.get_device_info_by_index.side_effect = get_device_info_by_index
    mock_pa.get_default_input_device_info.return_value = get_device_info_by_index(0)
    mock_pa.get_device_count.return_value = 2
    
    def mock_open(*args, **kwargs):
        idx = kwargs.get("input_device_index", 0)
        s = MagicMock()
        if idx == 0:
            # Dead device: returns 0s
            s.read.return_value = b'\x00' * 1280 * 2
        else:
            # Live device: returns varying signal with unique RMS values
            state = {"count": 0}
            def read_side_effect(*a, **kw):
                state["count"] += 1
                # Generate a buffer where the values vary dynamically (ensuring unique RMS)
                val = int(state["count"] * 1000)
                b_val = bytes([val & 0xFF, (val >> 8) & 0xFF]) * 1280
                return b_val
            s.read.side_effect = read_side_effect
        return s
        
    mock_pa.open.side_effect = mock_open
    mock_pa.get_device_count.return_value = 2
    mock_pa.get_device_info_by_index.side_effect = lambda i: {
        'index': i,
        'maxInputChannels': 1,
        'name': f'Mock Device {i}'
    }
    
    # Apply to the global mock module
    mock_pyaudio.PyAudio.return_value = mock_pa
    
    # Mock settings to return saved_idx=0
    monkeypatch.setattr("kree.memory.config_manager.load_audio_settings", lambda: {"input_device_index": 0})
    
    # Prevent model load and break loop early
    mock_model = MagicMock()
    def break_loop(*args, **kwargs):
        detector.is_running = False
        raise Exception("Test Break")
        
    mock_model.predict.side_effect = break_loop

    detector.model = mock_model
    detector._model_name = "test_model"
    detector._ensure_model = lambda: True
    
    detector._thread = threading.current_thread()
    detector.is_running = True
    
    detector._run_loop()
    
    # It should have attempted to open device 0 (failed test), then device 1 (passed test), then opened main stream on device 1
    kwargs = mock_pa.open.call_args_list[-1].kwargs
    assert kwargs.get("input_device_index") == 1

def test_whisper_detection(monkeypatch):
    import numpy as np
    detector = WakeWordDetector(lambda t, w: None)
    
    # Create fake objects for np.abs to return
    class FakeAbsQuiet:
        def mean(self):
            return 400
            
    class FakeAbsLoud:
        def mean(self):
            return 10000
            
    def mock_abs(x):
        if hasattr(x, 'is_loud') and x.is_loud:
            return FakeAbsLoud()
        return FakeAbsQuiet()
        
    monkeypatch.setattr(np, "abs", mock_abs)
    
    quiet_audio = MagicMock()
    quiet_audio.is_loud = False
    assert detector._detect_whisper(quiet_audio) == True
    
    loud_audio = MagicMock()
    loud_audio.is_loud = True
    assert detector._detect_whisper(loud_audio) == False
