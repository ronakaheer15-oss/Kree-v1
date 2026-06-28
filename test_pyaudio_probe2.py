import pyaudio

pa = pyaudio.PyAudio()
target_idx = 1
all_input_indices = []

for i in range(pa.get_device_count()):
    try:
        di = pa.get_device_info_by_index(i)
        global_idx = di.get('index')
        print(f"Global dev {global_idx}: {di.get('name')}, maxIn={di.get('maxInputChannels')}")
        if int(di.get('maxInputChannels', 0)) > 0 and global_idx != target_idx:
            name = di.get('name', '')
            if 'stereo mix' not in name.lower() and 'sound mapper' not in name.lower():
                all_input_indices.append(global_idx)
    except Exception as e:
        print(f"Error on {i}: {e}")

print(f"Found candidate indices: {all_input_indices}")
