"""TTS service: receives text from ZeroMQ and plays audio."""

import logging
import os
import time
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

    Listens on tcp://*:{ports.tts} using REP socket pattern.
    Immediately replies with a job_id (nanosecond timestamp string) upon receiving text.
    Publishes playback status on tcp://*:{ports.tts_status} using PUB socket.
    Each status message is two frames: [job_id, status ("started"|"done"|"error")].
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

    with (
        zmq_socket(zmq.REP, f"tcp://*:{config.ports.tts}") as rep_socket,
        zmq_socket(zmq.PUB, f"tcp://*:{config.ports.tts_status}") as status_socket,
    ):
        logger.info(
            f"Speak service started. Listening on tcp://*:{config.ports.tts}, "
            f"publishing status on tcp://*:{config.ports.tts_status}"
        )

        while True:
            text = rep_socket.recv_string()
            job_id = str(time.time_ns())
            rep_socket.send_string(job_id)
            logger.info(f"[SPEAK] Received text (id={job_id}): {text}")

            if text.strip():
                status_socket.send_multipart([job_id.encode(), b"started"])
                try:
                    audio_data = tts_service.convert(text, tts_config)
                    play_audio(audio_data)
                    logger.info(f"[SPEAK] Audio playback completed (id={job_id})")
                    status_socket.send_multipart([job_id.encode(), b"done"])
                except Exception as e:
                    logger.exception(f"[SPEAK] Error converting text to speech (id={job_id}): {e}")
                    status_socket.send_multipart([job_id.encode(), b"error"])
