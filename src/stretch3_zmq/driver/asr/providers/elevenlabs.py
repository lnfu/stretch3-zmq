"""ElevenLabs Scribe ASR provider using WebSocket streaming."""

import json
import logging
from urllib.parse import urlencode

import websockets

from .base import ASRConfig, ASRProvider, BaseASRProvider

logger = logging.getLogger(__name__)


class ElevenLabsProvider(BaseASRProvider):
    """ElevenLabs Scribe ASR provider using WebSocket."""

    # ElevenLabs-specific constants (hardcoded)
    ENCODING = "pcm_16000"
    ENABLE_LOGGING = True

    WS_BASE_URL = "wss://api.elevenlabs.io/v1/speech-to-text"

    @property
    def provider_name(self) -> ASRProvider:
        return ASRProvider.ELEVENLABS

    async def connect(self, config: ASRConfig) -> None:
        """Establish WebSocket connection with query parameters."""
        params = {
            "encoding": self.ENCODING,
            "language_code": config.language,
            "enable_logging": str(self.ENABLE_LOGGING).lower(),
        }

        # Model is specified via model_id if provided
        if config.model_id:
            params["model_id"] = config.model_id

        url = f"{self.WS_BASE_URL}?{urlencode(params)}"
        headers = {"xi-api-key": self._api_key}

        self._ws = await websockets.connect(url, additional_headers=headers)
        logger.info("ElevenLabs WebSocket connected")

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send raw audio bytes directly."""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        await self._ws.send(audio_chunk)

    async def receive_transcript(self) -> str | None:
        """Receive and parse transcription events."""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        try:
            response = await self._ws.recv()
            data = json.loads(response)

            # ElevenLabs sends committed_transcript for final results
            if "committed_transcript" in data:
                return data["committed_transcript"]
            elif "partial_transcript" in data:
                # Partial result, could be used for real-time display
                return None

        except websockets.exceptions.ConnectionClosed:
            logger.info("ElevenLabs WebSocket connection closed")
            return None

        return None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("ElevenLabs WebSocket closed")
