"""ElevenLabs TTS provider using the v1 REST API."""

from typing import Any

import httpx

from .base import (
    BaseTTSProvider,
    TTSConfig,
    TTSProvider,
)


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs TTS provider using REST API."""

    # Default voice ID
    DEFAULT_VOICE_ID = "9lHjugDhwqoxA5MhX0az"

    # Default model ID
    # eleven_multilingual_v2 | eleven_flash_v2_5 | eleven_turbo_v2_5 | eleven_v3
    DEFAULT_MODEL_ID = "eleven_v3"

    # ElevenLabs-specific voice settings
    STABILITY: float = 0.5
    SIMILARITY_BOOST: float = 0.75
    STYLE: float = 0.0
    USE_SPEAKER_BOOST: bool = True

    def _default_base_url(self) -> str:
        return "https://api.elevenlabs.io"

    @property
    def provider_name(self) -> TTSProvider:
        return TTSProvider.ELEVENLABS

    def _build_request_body(self, text: str, config: TTSConfig) -> dict[str, Any]:
        """Build the request body for the API call."""
        body: dict[str, Any] = {
            "text": text,
            "model_id": config.model_id or self.DEFAULT_MODEL_ID,
        }

        # Build voice settings with hardcoded ElevenLabs-specific values
        voice_settings: dict[str, Any] = {
            "stability": self.STABILITY,
            "similarity_boost": self.SIMILARITY_BOOST,
            "style": self.STYLE,
            "use_speaker_boost": self.USE_SPEAKER_BOOST,
        }
        # Add speed from config (common parameter)
        if config.voice_settings.speed != 1.0:
            voice_settings["speed"] = config.voice_settings.speed

        body["voice_settings"] = voice_settings

        return body

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    def convert(self, text: str, config: TTSConfig) -> bytes:
        """
        Convert text to speech and return full audio data (PCM 16000).

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        voice_id = config.voice_id or self.DEFAULT_VOICE_ID

        url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
        params = {"output_format": "pcm_16000"}
        body = self._build_request_body(text, config)

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers=self._get_headers(),
                params=params,
                json=body,
            )
            response.raise_for_status()

            return response.content
