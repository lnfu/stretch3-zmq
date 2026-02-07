"""Unified TTS service with provider abstraction."""

from typing import ClassVar

from .providers import (
    BaseTTSProvider,
    ElevenLabsProvider,
    FishAudioProvider,
    TTSConfig,
    TTSProvider,
    VoiceSettings,
)


class TTSServiceError(Exception):
    """Base exception for TTS service errors."""

    pass


class ProviderNotFoundError(TTSServiceError):
    """Raised when an unknown provider is requested."""

    pass


class TTSService:
    """
    Unified TTS service that abstracts multiple providers.

    Usage:
        # Create service with a specific provider
        service = TTSService.create(TTSProvider.ELEVENLABS, api_key="your-key")

        # Or create directly
        service = TTSService(provider=TTSProvider.ELEVENLABS, api_key="your-key")

        # Configure and convert
        config = TTSConfig(
            voice_id="your-voice-id",
            voice_settings=VoiceSettings(speed=0.75),
        )
        audio_data = service.convert("Hello, world!", config)
    """

    _PROVIDER_MAP: ClassVar[dict[TTSProvider, type[BaseTTSProvider]]] = {
        TTSProvider.ELEVENLABS: ElevenLabsProvider,
        TTSProvider.FISH_AUDIO: FishAudioProvider,
    }

    def __init__(
        self,
        provider: TTSProvider | str,
        api_key: str,
        base_url: str | None = None,
    ):
        """
        Initialize the TTS service.

        Args:
            provider: The TTS provider to use (TTSProvider enum or string).
            api_key: API key for the provider.
            base_url: Optional custom base URL for the API.

        Raises:
            ProviderNotFoundError: If the provider is not supported.
        """
        if isinstance(provider, str):
            try:
                provider = TTSProvider(provider)
            except ValueError as err:
                raise ProviderNotFoundError(
                    f"Unknown provider: {provider}. "
                    f"Supported providers: {[p.value for p in TTSProvider]}"
                ) from err

        provider_class = self._PROVIDER_MAP.get(provider)
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider {provider} is not implemented. "
                f"Supported providers: {[p.value for p in TTSProvider]}"
            )

        self._provider: BaseTTSProvider = provider_class(
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> TTSProvider:
        """Return the current provider name."""
        return self._provider.provider_name

    def convert(self, text: str, config: TTSConfig) -> bytes:
        """
        Convert text to speech and return full audio data.

        Args:
            text: The text to convert to speech.
            config: Configuration for the TTS request.

        Returns:
            Complete audio bytes (PCM 16000 Hz, 16-bit, mono).
        """
        return self._provider.convert(text, config)


# Convenience exports
__all__ = [
    "ProviderNotFoundError",
    "TTSConfig",
    "TTSProvider",
    "TTSService",
    "TTSServiceError",
    "VoiceSettings",
]
