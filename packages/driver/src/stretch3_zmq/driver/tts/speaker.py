"""Audio playback utility that resamples PCM data and plays via sounddevice."""

import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy import signal

PLAYBACK_SAMPLE_RATE = 48000
PCM_MAX_VALUE = 32768.0


def list_devices() -> None:
    """Print all available audio output devices."""
    devices = sd.query_devices()
    print(f"{'IDX':<5} {'NAME':<40} {'OUT_CH'}")
    print("-" * 55)
    default_out = sd.default.device[1]
    for i, d in enumerate(devices):
        if d["max_output_channels"] > 0:
            marker = " *" if i == default_out else ""
            print(f"{i:<5} {d['name'][:39]:<40} {d['max_output_channels']}{marker}")
    print("(* = current default)")


def save_wav(audio_data: bytes, path: str | Path, sample_rate: int = 16000) -> None:
    """Save raw PCM 16-bit mono audio to a WAV file."""
    path = Path(path)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)


def play_audio(audio_data: bytes, sample_rate: int = 22050, device: int | None = None) -> None:
    # Convert bytes to numpy array (16-bit PCM) then normalize to float32 [-1.0, 1.0]
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / PCM_MAX_VALUE

    # Resample to 48000 Hz (more widely supported by hardware)
    if sample_rate == PLAYBACK_SAMPLE_RATE:
        resampled_audio = audio_array
    else:
        num_samples = int(len(audio_array) * PLAYBACK_SAMPLE_RATE / sample_rate)
        resampled_audio = signal.resample(audio_array, num_samples).astype(np.float32)

    sd.play(
        resampled_audio,
        samplerate=PLAYBACK_SAMPLE_RATE,
        device=device if device is not None else sd.default.device[1],
        blocking=True,
    )
