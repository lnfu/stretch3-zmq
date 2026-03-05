"""Local TTS tester — synthesize speech and play it back."""

import argparse
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

from ..config import DriverConfig
from .providers import PROVIDER_ENV_KEYS, TTSConfig, TTSProvider, VoiceSettings
from .service import TTSService
from .speaker import list_devices, play_audio, save_wav

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("tts")

DEFAULT_TEXT = "Hello, have you taken your medicine yet?"


def _parse_sample_rate(output_format: str) -> int:
    """Extract sample rate from format string like 'pcm_22050' → 22050."""
    try:
        return int(output_format.split("_")[-1])
    except (ValueError, IndexError):
        return 22050


def _list_elevenlabs_voices(api_key: str, language: str | None = None) -> None:
    """Fetch and print available ElevenLabs voices, optionally filtered by language."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
        )
        response.raise_for_status()

    voices = response.json().get("voices", [])

    # Filter by language if specified
    if language:
        lang_lower = language.lower()
        voices = [
            v
            for v in voices
            if any(
                lang_lower in (lbl.get("language") or "").lower()
                or lang_lower in (lbl.get("language_id") or "").lower()
                for lbl in v.get("labels", {}).values()
                if isinstance(lbl, dict)
            )
            or lang_lower in str(v.get("labels", {})).lower()
            or lang_lower in (v.get("name") or "").lower()
        ]

    if not voices:
        print("No voices found.")
        return

    print(f"{'NAME':<30} {'VOICE ID':<24} {'CATEGORY':<14} {'LABELS'}")
    print("-" * 90)
    for v in sorted(voices, key=lambda x: x.get("name", "")):
        name = v.get("name", "")[:29]
        vid = v.get("voice_id", "")
        category = v.get("category", "")
        labels = v.get("labels", {})
        label_str = ", ".join(f"{k}={val}" for k, val in labels.items() if val)
        print(f"{name:<30} {vid:<24} {category:<14} {label_str}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Local TTS tester — synthesize and play back speech.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", default=DEFAULT_TEXT, help="Text to speak")
    parser.add_argument("--config", metavar="PATH", help="Path to config.yaml (loads tts defaults)")
    parser.add_argument(
        "--provider",
        choices=[p.value for p in TTSProvider],
        help="TTS provider (overrides config)",
    )
    parser.add_argument("--voice-id", metavar="ID", help="Voice ID (overrides config)")
    parser.add_argument("--model-id", metavar="ID", help="Model ID (overrides config)")
    parser.add_argument(
        "--speed", type=float, metavar="N", help="Speed multiplier (overrides config)"
    )
    parser.add_argument(
        "--format",
        metavar="FMT",
        default="pcm_22050",
        help="Output format for ElevenLabs (pcm_22050|pcm_24000|pcm_44100|pcm_48000, "
        "default: pcm_22050)",
    )
    parser.add_argument(
        "--list-voices",
        nargs="?",
        const="",
        metavar="LANGUAGE",
        help="List available ElevenLabs voices. Optionally filter by language "
        "keyword (e.g. chinese, zh)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio output devices and exit",
    )
    parser.add_argument(
        "--device",
        type=int,
        metavar="IDX",
        help="Audio output device index (see --list-devices)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save audio to a WAV file instead of playing (e.g. out.wav)",
    )
    args = parser.parse_args()

    # --list-devices mode (no API key needed)
    if args.list_devices:
        list_devices()
        return

    # Load base config from YAML if provided, else use defaults
    cfg = DriverConfig.from_yaml(args.config) if args.config else DriverConfig()
    tts_cfg = cfg.tts

    # CLI overrides
    provider_str: str = args.provider or tts_cfg.provider
    voice_id: str = args.voice_id if args.voice_id is not None else tts_cfg.voice_id
    model_id: str | None = args.model_id if args.model_id is not None else tts_cfg.model_id
    speed: float = args.speed if args.speed is not None else tts_cfg.speed
    output_format: str = args.format

    provider = TTSProvider(provider_str)
    env_key = PROVIDER_ENV_KEYS[provider]
    api_key = os.getenv(env_key)

    if not api_key:
        print(f"ERROR: API key not found. Set {env_key} in your environment.", file=sys.stderr)
        sys.exit(1)

    # --list-voices mode
    if args.list_voices is not None:
        if provider != TTSProvider.ELEVENLABS:
            print("ERROR: --list-voices is only supported for elevenlabs.", file=sys.stderr)
            sys.exit(1)
        _list_elevenlabs_voices(api_key, language=args.list_voices or None)
        return

    service = TTSService(provider=provider, api_key=api_key)
    config = TTSConfig(
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
        voice_settings=VoiceSettings(speed=speed),
    )

    print(f"provider      : {provider.value}")
    print(f"voice_id      : {voice_id!r}  (empty = provider default)")
    print(f"model_id      : {model_id!r}  (None = provider default)")
    print(f"output_format : {output_format}")
    print(f"speed         : {speed}")
    print(f"text          : {args.text!r}")
    print()

    audio_data = service.convert(args.text, config)
    # Fish Audio always returns PCM at the sample_rate set in the request body (16000 Hz).
    # ElevenLabs encodes the rate in the output_format string (e.g. pcm_22050 → 22050 Hz).
    pcm_rate = 16000 if provider == TTSProvider.FISH_AUDIO else _parse_sample_rate(output_format)

    if args.output:
        save_wav(audio_data, args.output, sample_rate=pcm_rate)
        print(f"Saved to {args.output}")
    else:
        play_audio(audio_data, sample_rate=pcm_rate, device=args.device)
        print("Done.")


if __name__ == "__main__":
    main()
