"""Quick test to verify openwakeword model loads and returns expected prediction keys."""
import numpy as np
from openwakeword.model import Model

model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")
print("Model loaded OK")

# Feed a chunk of silence to see what keys come back
dummy = np.zeros(2560, dtype=np.int16)
prediction = model.predict(dummy)
print(f"Prediction keys: {list(prediction.keys())}")
print(f"Prediction values: {prediction}")

# Also list all available pre-trained models
try:
    from openwakeword import utils
    available = utils.list_available_models() if hasattr(utils, 'list_available_models') else "N/A"
    print(f"Available models: {available}")
except Exception as e:
    print(f"Could not list models: {e}")
