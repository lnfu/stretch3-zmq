"""Abstract base class and shared types for TTS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class TTSProvider(StrEnum):
    """Supported TTS providers."""

    ELEVENLABS = "elevenlabs"
    FISH_AUDIO = "fish_audio"


@dataclass
class VoiceSettings:
    """Common voice settings across providers."""

    speed: float = 1.0  # Speech speed multiplier (supported by both providers)


@dataclass
class TTSConfig:
    """Configuration for TTS request."""

    voice_id: str
    model_id: str | None = None
    bitrate: int = 128
    voice_settings: VoiceSettings = field(default_factory=VoiceSettings)


PROVIDER_ENV_KEYS: dict[TTSProvider, str] = {
    TTSProvider.ELEVENLABS: "ELEVENLABS_API_KEY",
    TTSProvider.FISH_AUDIO: "FISH_AUDIO_API_KEY",
}


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, api_key: str, base_url: str | None = None):
        self._api_key = api_key
        self.base_url = base_url or self._default_base_url()

    @abstractmethod
    def _default_base_url(self) -> str:
        """Return the default base URL for this provider."""
        pass

    @abstractmethod
    def convert(self, text: str, config: TTSConfig) -> bytes:
        """
        Convert text to speech and return full audio data.

        Args:
            text: The text to convert to speech.
            config: Configuration for the TTS request.

        Returns:
            Complete audio bytes (PCM 16000 Hz, 16-bit, mono).
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> TTSProvider:
        """Return the provider identifier."""
        pass
