"""Quick wake word diagnostic — speaks scores live so you can see what's happening."""
import pyaudio
import numpy as np
from openwakeword.model import Model

print("Loading model...")
model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
print("Model loaded. Say 'hey jarvis' now — watching scores...\n")

pa = pyaudio.PyAudio()
stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16,
                 input=True, frames_per_buffer=2560)

frame_count = 0
try:
    while True:
        audio = stream.read(2560, exception_on_overflow=False)
        audio_np = np.frombuffer(audio, dtype=np.int16)
        prediction = model.predict(audio_np)
        
        frame_count += 1
        for name, score in prediction.items():
            if score > 0.01:  # Print anything above noise floor
                vol = int(np.abs(audio_np).mean())
                print(f"[frame {frame_count}] {name}: {score:.4f}  (vol={vol})")
            
            if score > 0.35:
                print(f"\n*** TRIGGERED! score={score:.4f} ***\n")
                
except KeyboardInterrupt:
    print("\nDone.")
    stream.stop_stream()
    stream.close()
    pa.terminate()
