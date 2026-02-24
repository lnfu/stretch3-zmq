"""ReSpeaker 4 Mic Array input handler for 16 kHz mono capture."""

import logging
import queue
from typing import Any, Self, cast

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

# Audio constants
SAMPLE_RATE = 16000  # ReSpeaker native sample rate (no resampling needed)
_DEVICE_CHANNELS = 6  # ReSpeaker 4 Mic Array has 6 channels
_CHUNK_SIZE = 1024  # Audio chunk size in frames


class Microphone:
    """
    Microphone input handler for ReSpeaker 4 Mic Array.

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
        # Take first channel only (mono), no resampling needed
        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        audio_bytes = (mono * 32767).astype(np.int16).tobytes()
        self._audio_queue.put(audio_bytes)

    @staticmethod
    def _find_input_device() -> int:
        """Find the best available input device."""
        sd._initialize()
        devices = sd.query_devices()

        hw_devices = [d for d in devices if d["max_input_channels"] > 0 and "hw:" in d["name"]]

        if not hw_devices:
            raise RuntimeError("No hardware input devices found.")

        # Prefer ReSpeaker 4 Mic Array (hw:1,0)
        respeaker = [d for d in hw_devices if "ReSpeaker" in d["name"]]
        if respeaker:
            logger.info(f"Using ReSpeaker: {respeaker[0]['name']}")
            return cast(int, respeaker[0]["index"])

        logger.info(f"Using input device: {hw_devices[0]['name']}")
        return cast(int, hw_devices[0]["index"])

    def start(self) -> None:
        """Start recording from microphone."""
        self._device_id = self._find_input_device()
        self._stream = sd.InputStream(
            device=self._device_id,
            samplerate=SAMPLE_RATE,
            channels=_DEVICE_CHANNELS,
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
