"""Tests for DriverConfig loading and validation."""

import tempfile

import pytest
import yaml
from pydantic import ValidationError

from stretch3_zmq_driver.config import DriverConfig


class TestDriverConfig:
    def test_default_config(self) -> None:
        config = DriverConfig()
        assert config.ports.status == 5555
        assert config.ports.command == 5556
        assert config.service.status_rate_hz == 50.0
        assert config.service.tts_provider == "fish_audio"
        assert config.service.asr_provider == "deepgram"
        assert not config.debug

    def test_from_yaml_none_returns_default(self) -> None:
        config = DriverConfig.from_yaml(None)
        assert config.ports.status == 5555

    def test_from_yaml_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            DriverConfig.from_yaml("/nonexistent/config.yaml")

    def test_from_yaml_valid_file(self) -> None:
        data = {
            "ports": {"status": 9999},
            "service": {"tts_provider": "elevenlabs"},
            "debug": True,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.ports.status == 9999
            assert config.service.tts_provider == "elevenlabs"
            assert config.debug is True
            # Unspecified fields should use defaults
            assert config.ports.command == 5556

    def test_from_yaml_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.ports.status == 5555

    def test_from_yaml_invalid_types(self) -> None:
        data = {"ports": {"status": "not_a_number"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            with pytest.raises(ValidationError):
                DriverConfig.from_yaml(f.name)
