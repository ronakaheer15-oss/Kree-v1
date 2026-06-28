import pyaudio

pa = pyaudio.PyAudio()
target_idx = 1
all_input_indices = []
host_info = pa.get_host_api_info_by_index(0)
print(f"Device count for API 0: {host_info.get('deviceCount', 0)}")

for i in range(host_info.get('deviceCount', 0)):
    try:
        di = pa.get_device_info_by_host_api_device_index(0, i)
        global_idx = di.get('index')
        print(f"API dev {i} -> Global dev {global_idx}: {di.get('name')}, maxIn={di.get('maxInputChannels')}")
        if int(di.get('maxInputChannels', 0)) > 0 and global_idx != target_idx:
            name = di.get('name', '')
            if 'stereo mix' not in name.lower() and 'sound mapper' not in name.lower():
                all_input_indices.append(global_idx)
    except Exception as e:
        print(f"Error on {i}: {e}")

print(f"Found candidate indices: {all_input_indices}")
