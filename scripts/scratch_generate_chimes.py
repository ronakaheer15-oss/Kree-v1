import os
import wave
import math
import struct

def generate_tone(filename, base_freq, is_wake=True):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    sample_rate = 44100
    if is_wake:
        duration = 0.4
        freq_start = base_freq
        freq_end = base_freq * 1.5
    else:
        duration = 0.5
        freq_start = base_freq * 1.5
        freq_end = base_freq * 0.5

    num_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Smooth frequency slide and amplitude envelope
            t = float(i) / sample_rate
            progress = i / num_samples
            
            # Slide frequency
            current_freq = freq_start + (freq_end - freq_start) * progress
            
            # Envelope (quick attack, long release)
            if progress < 0.1:
                envelope = progress / 0.1
            else:
                envelope = 1.0 - ((progress - 0.1) / 0.9)
                
            value = int(32767.0 * envelope * 0.5 * math.sin(2.0 * math.pi * current_freq * t))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

if __name__ == '__main__':
    generate_tone('assets/sounds/wake.wav', 600, True)
    generate_tone('assets/sounds/sleep.wav', 600, False)
    print("WAV assets generated.")
