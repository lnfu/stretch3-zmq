"""Fish Audio TTS provider using the v1 REST API."""

from typing import Any

import httpx

from .base import BaseTTSProvider, TTSConfig, TTSProvider


class FishAudioProvider(BaseTTSProvider):
    """Fish Audio TTS provider using REST API."""

    # Default model
    DEFAULT_MODEL = "s1"

    # Fish Audio-specific voice settings (hardcoded)
    TEMPERATURE: float = 0.7
    TOP_P: float = 1.0

    def _default_base_url(self) -> str:
        return "https://api.fish.audio"

    @property
    def provider_name(self) -> TTSProvider:
        return TTSProvider.FISH_AUDIO

    def _get_format_string(self) -> str:
        """Get the format string for Fish Audio API. Fixed to PCM."""
        return "pcm"

    def _build_request_body(self, text: str, config: TTSConfig) -> dict[str, Any]:
        """Build the request body for the API call."""
        body = {
            "text": text,
            "format": self._get_format_string(),
            "normalize": True,
            "sample_rate": 16000,  # Fixed to 16000 Hz
        }

        # Add reference_id (voice_id in our abstraction)
        if config.voice_id:
            body["reference_id"] = config.voice_id

        # Add voice settings with hardcoded Fish Audio-specific values
        if config.voice_settings.speed != 1.0:
            body["prosody"] = {"speed": config.voice_settings.speed, "volume": 0}

        # Add hardcoded Fish Audio-specific parameters
        body["temperature"] = self.TEMPERATURE
        body["top_p"] = self.TOP_P

        return body

    def _get_headers(self, model: str | None = None) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "model": model or self.DEFAULT_MODEL,
        }
        return headers

    def convert(self, text: str, config: TTSConfig) -> bytes:
        """
        Convert text to speech and return full audio data (PCM 16000).

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        url = f"{self.base_url}/v1/tts"
        body = self._build_request_body(text, config)
        headers = self._get_headers(config.model_id)

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                headers=headers,
                json=body,
            )
            response.raise_for_status()

            return response.content
