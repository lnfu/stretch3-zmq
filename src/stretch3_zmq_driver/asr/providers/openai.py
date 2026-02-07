"""OpenAI Realtime API provider for streaming speech-to-text."""

import base64
import json
import logging

import websockets

from .base import ASRConfig, ASRProvider, BaseASRProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseASRProvider):
    """OpenAI Realtime API provider for ASR using WebSocket."""

    # OpenAI-specific constants (hardcoded)
    TURN_DETECTION = "server_vad"
    NOISE_REDUCTION = "near_field"
    AUDIO_FORMAT = "pcm16"
    DEFAULT_MODEL = "gpt-4o-transcribe"

    WS_URL = "wss://api.openai.com/v1/realtime?intent=transcription"

    @property
    def provider_name(self) -> ASRProvider:
        return ASRProvider.OPENAI

    async def connect(self, config: ASRConfig) -> None:
        """Establish WebSocket connection and configure session."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        self._ws = await websockets.connect(self.WS_URL, additional_headers=headers)
        logger.info("OpenAI WebSocket connected")

        # Wait for session.created event
        response = await self._ws.recv()
        event = json.loads(response)
        if event.get("type") != "session.created":
            raise RuntimeError(f"Unexpected event: {event}")

        # Configure session
        session_config = {
            "type": "session.update",
            "session": {
                "input_audio_format": self.AUDIO_FORMAT,
                "input_audio_transcription": {
                    "model": config.model_id or self.DEFAULT_MODEL,
                    "language": config.language,
                },
                "turn_detection": {"type": self.TURN_DETECTION},
            },
        }
        await self._ws.send(json.dumps(session_config))
        logger.info("OpenAI session configured")

    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send audio chunk as base64-encoded data."""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        event = {
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(audio_chunk).decode("utf-8"),
        }
        await self._ws.send(json.dumps(event))

    async def receive_transcript(self) -> str | None:
        """Receive and parse transcription events."""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        try:
            response = await self._ws.recv()
            event = json.loads(response)

            event_type = event.get("type", "")

            if event_type == "conversation.item.input_audio_transcription.completed":
                return event.get("transcript", "")
            elif event_type == "conversation.item.input_audio_transcription.delta":
                # Partial result, could be used for real-time display
                return None
            elif event_type == "error":
                logger.error(f"OpenAI error: {event}")
                return None

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WebSocket connection closed")
            return None

        return None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("OpenAI WebSocket closed")
