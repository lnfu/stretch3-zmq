"""Tests for ASRService provider instantiation and error handling."""

import pytest

from stretch3_zmq.driver.asr.providers.base import PROVIDER_ENV_KEYS, ASRProvider
from stretch3_zmq.driver.asr.service import ASRService, ProviderNotFoundError


class TestASRService:
    def test_create_deepgram_provider(self) -> None:
        service = ASRService(provider=ASRProvider.DEEPGRAM, api_key="test-key")
        assert service.provider_name == ASRProvider.DEEPGRAM

    def test_create_openai_provider(self) -> None:
        service = ASRService(provider=ASRProvider.OPENAI, api_key="test-key")
        assert service.provider_name == ASRProvider.OPENAI

    def test_create_elevenlabs_provider(self) -> None:
        service = ASRService(provider=ASRProvider.ELEVENLABS, api_key="test-key")
        assert service.provider_name == ASRProvider.ELEVENLABS

    def test_create_from_string(self) -> None:
        service = ASRService(provider="deepgram", api_key="test-key")
        assert service.provider_name == ASRProvider.DEEPGRAM

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ProviderNotFoundError, match="Unknown provider"):
            ASRService(provider="nonexistent", api_key="test-key")

    def test_provider_env_keys_complete(self) -> None:
        for provider in ASRProvider:
            assert provider in PROVIDER_ENV_KEYS, f"Missing env key for {provider}"
