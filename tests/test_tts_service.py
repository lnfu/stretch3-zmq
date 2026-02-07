"""Tests for TTSService provider instantiation and error handling."""

import pytest

from stretch3_zmq_driver.tts.providers.base import PROVIDER_ENV_KEYS, TTSProvider
from stretch3_zmq_driver.tts.service import ProviderNotFoundError, TTSService


class TestTTSService:
    def test_create_elevenlabs_provider(self) -> None:
        service = TTSService(provider=TTSProvider.ELEVENLABS, api_key="test-key")
        assert service.provider_name == TTSProvider.ELEVENLABS

    def test_create_fish_audio_provider(self) -> None:
        service = TTSService(provider=TTSProvider.FISH_AUDIO, api_key="test-key")
        assert service.provider_name == TTSProvider.FISH_AUDIO

    def test_create_from_string(self) -> None:
        service = TTSService(provider="elevenlabs", api_key="test-key")
        assert service.provider_name == TTSProvider.ELEVENLABS

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ProviderNotFoundError, match="Unknown provider"):
            TTSService(provider="nonexistent", api_key="test-key")

    def test_provider_env_keys_complete(self) -> None:
        for provider in TTSProvider:
            assert provider in PROVIDER_ENV_KEYS, f"Missing env key for {provider}"
