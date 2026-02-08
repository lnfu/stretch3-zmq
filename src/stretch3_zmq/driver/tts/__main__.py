"""Standalone TTS demo that converts a sample sentence to speech."""

import logging
import os

from dotenv import load_dotenv

from .providers import PROVIDER_ENV_KEYS, TTSProvider
from .service import (
    TTSConfig,
    TTSService,
    VoiceSettings,
)
from .speaker import play_audio

logger = logging.getLogger("tts")


def main() -> None:
    load_dotenv()

    TEXT = "Hello, have you taken your medicine yet?"

    provider = TTSProvider.ELEVENLABS
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"API key not found. Please set {env_key} in your environment.")

    service = TTSService(
        provider=provider,
        api_key=api_key,
    )

    tts_config = TTSConfig(
        voice_id="",
        model_id=None,
        voice_settings=VoiceSettings(speed=0.75),
    )

    logger.info(f"TTS Service initialized with provider: {service.provider_name.value}")

    audio_data = service.convert(TEXT, tts_config)
    play_audio(audio_data)


if __name__ == "__main__":
    main()
