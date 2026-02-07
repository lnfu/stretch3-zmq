"""Audio playback utility that resamples PCM data and plays via sounddevice."""

import numpy as np
import sounddevice as sd
from scipy import signal

PCM_SAMPLE_RATE = 16000
PLAYBACK_SAMPLE_RATE = 48000
PCM_MAX_VALUE = 32768.0


def play_audio(audio_data: bytes) -> None:
    # Convert bytes to numpy array (16-bit PCM, little-endian)
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    # Normalize to float32 range [-1.0, 1.0]
    audio_array = audio_array.astype(np.float32) / PCM_MAX_VALUE

    # Resample from 16000 Hz to 48000 Hz (more widely supported)
    if PCM_SAMPLE_RATE == PLAYBACK_SAMPLE_RATE:
        resampled_audio = audio_array
    else:
        num_samples = int(len(audio_array) * PLAYBACK_SAMPLE_RATE / PCM_SAMPLE_RATE)
        resampled_audio = signal.resample(audio_array, num_samples)

    # Play audio: 48000 Hz, mono
    # sounddevice automatically detects mono from 1D array shape
    # Explicitly specify device to ensure it uses the correct output
    sd.play(
        resampled_audio,
        samplerate=PLAYBACK_SAMPLE_RATE,
        device=sd.default.device[1],
        blocking=True,
    )
