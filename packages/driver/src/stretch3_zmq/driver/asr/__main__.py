"""Standalone ASR entry point for single-utterance transcription."""

import asyncio
import logging
import os

from dotenv import load_dotenv

from .providers import PROVIDER_ENV_KEYS, ASRConfig, ASRProvider
from .service import ASRService

logging.basicConfig(level=logging.INFO)

TIMEOUT_SECONDS = 10.0


async def listen_once() -> str:
    """Listen for one sentence and return transcript."""
    load_dotenv()

    provider = ASRProvider.DEEPGRAM
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"API key not found. Set {env_key} in .env")

    service = ASRService(
        provider=provider,
        api_key=api_key,
    )

    asr_config = ASRConfig(
        language="en",
    )

    return await service.transcribe_microphone(asr_config, timeout=TIMEOUT_SECONDS)


def main() -> None:
    result = asyncio.run(listen_once())
    print(f"\n>>> {result}")


if __name__ == "__main__":
    main()
