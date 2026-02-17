"""Abstract base class and shared types for ASR providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from websockets.client import WebSocketClientProtocol


class ASRProvider(StrEnum):
    """Supported ASR providers."""

    OPENAI = "openai"
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"


@dataclass
class ASRConfig:
    """Configuration for ASR request."""

    model_id: str | None = None
    language: str = "en"
    sample_rate: int = 16000


PROVIDER_ENV_KEYS: dict[ASRProvider, str] = {
    ASRProvider.OPENAI: "OPENAI_API_KEY",
    ASRProvider.DEEPGRAM: "DEEPGRAM_API_KEY",
    ASRProvider.ELEVENLABS: "ELEVENLABS_API_KEY",
}


class BaseASRProvider(ABC):
    """Abstract base class for ASR providers."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._ws: WebSocketClientProtocol | None = None

    @property
    @abstractmethod
    def provider_name(self) -> ASRProvider:
        """Return the provider identifier."""
        pass

    @abstractmethod
    async def connect(self, config: ASRConfig) -> None:
        """
        Establish WebSocket connection for streaming ASR.

        Args:
            config: Configuration for the ASR session.
        """
        pass

    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """
        Send audio chunk to the ASR service.

        Args:
            audio_chunk: PCM audio bytes to transcribe.
        """
        pass

    @abstractmethod
    async def receive_transcript(self) -> str | None:
        """
        Receive transcription result from the ASR service.

        Returns:
            Transcribed text or None if no result available.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the WebSocket connection."""
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        await self.close()
