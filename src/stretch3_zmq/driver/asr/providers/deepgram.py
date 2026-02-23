"""Deepgram ASR provider using the Nova-2 streaming WebSocket API."""

import json
import logging
from urllib.parse import urlencode

import websockets

from .base import ASRConfig, ASRProvider, BaseASRProvider

logger = logging.getLogger(__name__)


class DeepgramProvider(BaseASRProvider):
    """Deepgram ASR provider using WebSocket streaming."""

    # Deepgram-specific constants (hardcoded)
    ENCODING = "linear16"
    INTERIM_RESULTS = True
    PUNCTUATE = True
    ENDPOINTING = 300
    DEFAULT_MODEL = "nova-2"

    WS_BASE_URL = "wss://api.deepgram.com/v1/listen"

    @property
    def provider_name(self) -> ASRProvider:
        return ASRProvider.DEEPGRAM

    async def connect(self, config: ASRConfig) -> None:
        """Establish WebSocket connection with query parameters."""
        params = {
            "model": config.model_id or self.DEFAULT_MODEL,
            "language": config.language,
            "sample_rate": config.sample_rate,
            "encoding": self.ENCODING,
            "interim_results": str(self.INTERIM_RESULTS).lower(),
            "punctuate": str(self.PUNCTUATE).lower(),
            "endpointing": self.ENDPOINTING,
        }

        url = f"{self.WS_BASE_URL}?{urlencode(params)}"
        headers = {"Authorization": f"Token {self._api_key}"}

        self._ws = await websockets.connect(url, extra_headers=headers)
        logger.info("Deepgram WebSocket connected")

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

            # Check for final transcript
            if data.get("is_final"):
                alternatives = data.get("channel", {}).get("alternatives", [{}])
                if alternatives:
                    return str(alternatives[0].get("transcript", ""))

        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram WebSocket connection closed")
            return None

        return None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            # Send close frame to signal end of audio
            await self._ws.send(json.dumps({"type": "CloseStream"}))
            await self._ws.close()
            self._ws = None
            logger.info("Deepgram WebSocket closed")
