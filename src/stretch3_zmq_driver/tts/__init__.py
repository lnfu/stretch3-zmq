"""Text-to-Speech (TTS) package with pluggable providers."""

from .providers import PROVIDER_ENV_KEYS, TTSConfig, TTSProvider, VoiceSettings
from .service import ProviderNotFoundError, TTSService, TTSServiceError
from .speaker import play_audio

__all__ = [
    "PROVIDER_ENV_KEYS",
    "ProviderNotFoundError",
    "TTSConfig",
    "TTSProvider",
    "TTSService",
    "TTSServiceError",
    "VoiceSettings",
    "play_audio",
]
