"""Standalone ASR entry point for single-utterance transcription."""

import argparse
import asyncio
import logging
import os

import sounddevice as sd
from dotenv import load_dotenv

from .providers import PROVIDER_ENV_KEYS, ASRConfig, ASRProvider
from .service import ASRService

logging.basicConfig(level=logging.INFO)


async def listen_once(
    provider: ASRProvider,
    language: str,
    model_id: str | None,
    timeout: float,
    microphone: str = "auto",
) -> str:
    """Listen for one sentence and return transcript."""
    load_dotenv()

    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        raise ValueError(f"API key not found. Set {env_key} in .env")

    service = ASRService(provider=provider, api_key=api_key)
    asr_config = ASRConfig(language=language, model_id=model_id)

    return await service.transcribe_microphone(asr_config, timeout=timeout, microphone=microphone)


def _list_devices() -> None:
    """Print all available audio input devices."""
    sd._initialize()
    devices = sd.query_devices()
    print("Available input devices:")
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            marker = " *" if i == sd.default.device[0] else ""
            print(f"  [{i}] {dev['name']} ({dev['max_input_channels']}ch){marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ASR single-utterance transcription")
    parser.add_argument(
        "--provider",
        choices=[p.value for p in ASRProvider],
        default=ASRProvider.DEEPGRAM.value,
        help="ASR provider (default: deepgram)",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code, e.g. en, zh, zh-TW (default: en)",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Provider-specific model ID (default: provider default)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Max seconds to wait for speech (default: 10.0)",
    )
    parser.add_argument(
        "--microphone",
        default="auto",
        help='Microphone device: "auto", "default", or a name substring (e.g. "DJI MIC MINI")',
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )
    args = parser.parse_args()

    if args.list_devices:
        _list_devices()
        return

    result = asyncio.run(
        listen_once(
            provider=ASRProvider(args.provider),
            language=args.language,
            model_id=args.model_id,
            timeout=args.timeout,
            microphone=args.microphone,
        )
    )
    print(f"\n>>> {result}")


if __name__ == "__main__":
    main()
