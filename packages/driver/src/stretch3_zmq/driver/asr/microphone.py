"""Microphone input handler for 16 kHz mono audio capture.

Prefers ReSpeaker 4 Mic Array when available; falls back to the system default
input device so the module works on development machines without ReSpeaker.
"""

import logging
import queue
from typing import Any, Self, cast

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# Audio constants
SAMPLE_RATE = 16000  # Target sample rate
_CHUNK_SIZE = 1024  # Audio chunk size in frames


class Microphone:
    """
    Microphone input handler.

    Prefers ReSpeaker 4 Mic Array (hw:) when available; otherwise falls back to
    the system default input device (works on regular laptops for local testing).

    Usage:
        mic = Microphone()
        mic.start()
        while recording:
            chunk = mic.get_audio_chunk()  # Returns 16kHz int16 bytes
            ...
        mic.stop()
    """

    def __init__(self) -> None:
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._device_id: int | None = None
        self._channels: int = 1
        self._native_rate: int = SAMPLE_RATE

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags | None,
    ) -> None:
        """Callback for sounddevice InputStream."""
        if status:
            logger.warning(f"Audio status: {status}")
        # Take first channel only (mono)
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        # Resample to target rate if device native rate differs
        if self._native_rate != SAMPLE_RATE:
            target_len = int(len(mono) * SAMPLE_RATE / self._native_rate)
            mono = np.interp(
                np.linspace(0, len(mono) - 1, target_len),
                np.arange(len(mono)),
                mono,
            )
        audio_bytes = (mono * 32767).astype(np.int16).tobytes()
        self._audio_queue.put(audio_bytes)

    @staticmethod
    def _find_input_device() -> tuple[int | None, int]:
        """Find the best available input device. Returns (device_id, channels)."""
        sd._initialize()
        devices = sd.query_devices()

        hw_devices = [d for d in devices if d["max_input_channels"] > 0 and "hw:" in d["name"]]

        # Prefer ReSpeaker 4 Mic Array (hw:1,0)
        respeaker = [d for d in hw_devices if "ReSpeaker" in d["name"]]
        if respeaker:
            dev = respeaker[0]
            logger.info(f"Using ReSpeaker: {dev['name']}")
            return cast(int, dev["index"]), dev["max_input_channels"]

        if hw_devices:
            dev = hw_devices[0]
            logger.info(f"Using hardware input device: {dev['name']}")
            return cast(int, dev["index"]), dev["max_input_channels"]

        # Fall back to system default input device (e.g. laptop built-in mic)
        default_dev = sd.query_devices(kind="input")
        channels = max(1, min(default_dev["max_input_channels"], 2))
        logger.info(f"Using default input device: {default_dev['name']} ({channels}ch)")
        return None, channels

    def start(self) -> None:
        """Start recording from microphone."""
        self._device_id, self._channels = self._find_input_device()
        # Query the device's native sample rate; resample to SAMPLE_RATE if needed
        dev_info = (
            sd.query_devices(self._device_id)
            if self._device_id is not None
            else sd.query_devices(kind="input")
        )
        self._native_rate = int(dev_info["default_samplerate"])
        if self._native_rate != SAMPLE_RATE:
            logger.info(
                f"Device native rate {self._native_rate} Hz; will resample to {SAMPLE_RATE} Hz"
            )
        self._stream = sd.InputStream(
            device=self._device_id,
            samplerate=self._native_rate,
            channels=self._channels,
            blocksize=_CHUNK_SIZE,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop recording."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_audio_chunk(self) -> bytes | None:
        """Get next audio chunk from queue, or None if empty."""
        try:
            return self._audio_queue.get_nowait()
        except queue.Empty:
            return None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.stop()
