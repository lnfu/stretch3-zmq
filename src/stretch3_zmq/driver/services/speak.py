"""TTS service: receives text from ZeroMQ and plays audio."""

import logging
import os
from typing import NoReturn

import zmq

from ..config import DriverConfig
from ..tts.providers import PROVIDER_ENV_KEYS, TTSConfig, TTSProvider, VoiceSettings
from ..tts.service import TTSService
from ..tts.speaker import play_audio
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def speak_service(config: DriverConfig) -> NoReturn:
    """
    TTS service: Receives text from ZeroMQ and plays audio.

    Listens on tcp://*:{ports.tts} using PULL socket pattern.
    """
    provider = TTSProvider(config.tts.provider)
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"API key not found. Please set {env_key} in your environment.")

    tts_service = TTSService(
        provider=provider,
        api_key=api_key,
    )

    tts_config = TTSConfig(
        voice_id="",
        model_id=None,
        voice_settings=VoiceSettings(speed=1.0),
    )

    logger.info(f"TTS Service initialized with provider: {tts_service.provider_name.value}")

    with zmq_socket(zmq.PULL, f"tcp://*:{config.ports.tts}") as socket:
        logger.info(f"Speak service started. Listening on tcp://*:{config.ports.tts}")

        while True:
            text = socket.recv_string()
            logger.info(f"[SPEAK] Received text: {text}")

            if text.strip():
                try:
                    audio_data = tts_service.convert(text, tts_config)
                    play_audio(audio_data)
                    logger.info("[SPEAK] Audio playback completed")
                except Exception as e:
                    logger.exception(f"[SPEAK] Error converting text to speech: {e}")
