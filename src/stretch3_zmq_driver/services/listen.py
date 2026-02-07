"""ASR service: receives requests, records audio, and returns transcribed text."""

import asyncio
import logging
import os
from typing import NoReturn

import zmq

from ..asr.providers import PROVIDER_ENV_KEYS, ASRConfig, ASRProvider
from ..asr.service import ASRService
from ..config import DriverConfig
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def listen_service(config: DriverConfig) -> NoReturn:
    """
    ASR service: Receives requests, records audio, and returns transcribed text.

    Listens on tcp://*:{ports.asr} using REP socket pattern.
    When a request is received, starts listening for speech and returns transcript.
    """
    provider = ASRProvider(config.service.asr_provider)
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"API key not found. Please set {env_key} in your environment.")

    asr_config = ASRConfig(
        language="en",
    )

    with zmq_socket(zmq.REP, f"tcp://*:{config.ports.asr}") as socket:
        logger.info(f"Listen service started. Listening on tcp://*:{config.ports.asr}")

        async def transcribe() -> str:
            """Create a new service instance and transcribe."""
            service = ASRService(
                provider=provider,
                api_key=api_key,
            )
            return await service.transcribe_microphone(
                asr_config, timeout=config.service.asr_timeout_seconds
            )

        try:
            while True:
                request = socket.recv_string()
                logger.info(f"[LISTEN] Received request: {request}")

                try:
                    transcript = asyncio.run(transcribe())
                    logger.info(f"[LISTEN] Transcript: {transcript}")
                except Exception as e:
                    logger.exception(f"[LISTEN] Error during transcription: {e}")
                    transcript = ""

                socket.send_string(transcript)
                logger.info(f"[LISTEN] Sent response: {transcript!r}")

        except KeyboardInterrupt:
            logger.info("[LISTEN] Shutting down...")
