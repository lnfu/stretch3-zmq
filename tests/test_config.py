"""Tests for DriverConfig loading and validation."""

import tempfile

import pytest
import yaml
from pydantic import ValidationError

from stretch3_zmq.driver.config import (
    ArducamConfig,
    ASRConfig,
    D405Config,
    D435ifConfig,
    DriverConfig,
    PortsConfig,
    ServiceConfig,
    TTSConfig,
)


class TestDriverConfig:
    def test_default_config(self) -> None:
        config = DriverConfig()
        assert config.ports.status == 5555
        assert config.ports.command == 5556
        assert config.service.status_rate_hz == 50.0
        assert config.tts.provider == "fish_audio"
        assert config.asr.provider == "deepgram"
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
            "tts": {"provider": "elevenlabs"},
            "debug": True,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.ports.status == 9999
            assert config.tts.provider == "elevenlabs"
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


class TestPortsConfig:
    def test_all_defaults(self) -> None:
        ports = PortsConfig()
        assert ports.status == 5555
        assert ports.command == 5556
        assert ports.goto == 5557
        assert ports.arducam == 6000
        assert ports.d435if == 6001
        assert ports.d405 == 6002
        assert ports.tts == 6101
        assert ports.tts_status == 6102
        assert ports.asr == 6103

    def test_custom_status_port(self) -> None:
        ports = PortsConfig(status=9999)
        assert ports.status == 9999
        assert ports.command == 5556  # unchanged

    def test_invalid_port_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            PortsConfig(status="not_a_port")


class TestServiceConfig:
    def test_defaults(self) -> None:
        svc = ServiceConfig()
        assert svc.status_rate_hz == 50.0

    def test_custom_rate(self) -> None:
        svc = ServiceConfig(status_rate_hz=100.0)
        assert svc.status_rate_hz == 100.0

    def test_invalid_rate_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            ServiceConfig(status_rate_hz="fast")


class TestTTSConfig:
    def test_defaults(self) -> None:
        tts = TTSConfig()
        assert tts.enabled is True
        assert tts.provider == "fish_audio"

    def test_disabled(self) -> None:
        tts = TTSConfig(enabled=False)
        assert tts.enabled is False

    def test_custom_provider(self) -> None:
        tts = TTSConfig(provider="elevenlabs")
        assert tts.provider == "elevenlabs"


class TestASRConfig:
    def test_defaults(self) -> None:
        asr = ASRConfig()
        assert asr.enabled is True
        assert asr.provider == "deepgram"
        assert asr.timeout_seconds == 10.0

    def test_disabled(self) -> None:
        asr = ASRConfig(enabled=False)
        assert asr.enabled is False

    def test_custom_provider_and_timeout(self) -> None:
        asr = ASRConfig(provider="openai", timeout_seconds=30.0)
        assert asr.provider == "openai"
        assert asr.timeout_seconds == 30.0


class TestArducamConfig:
    def test_defaults(self) -> None:
        cam = ArducamConfig()
        assert cam.enabled is False
        assert cam.device == "/dev/video4"
        assert cam.width == 1280
        assert cam.height == 720
        assert cam.fps == 30

    def test_enable(self) -> None:
        cam = ArducamConfig(enabled=True)
        assert cam.enabled is True

    def test_custom_device(self) -> None:
        cam = ArducamConfig(device="/dev/video0")
        assert cam.device == "/dev/video0"


class TestD435ifConfig:
    def test_defaults(self) -> None:
        cam = D435ifConfig()
        assert cam.enabled is False
        assert cam.serial is None
        assert cam.width == 640
        assert cam.height == 480
        assert cam.fps == 30

    def test_with_serial(self) -> None:
        cam = D435ifConfig(enabled=True, serial="123456789")
        assert cam.enabled is True
        assert cam.serial == "123456789"


class TestD405Config:
    def test_defaults(self) -> None:
        cam = D405Config()
        assert cam.enabled is False
        assert cam.serial is None
        assert cam.width == 640
        assert cam.height == 480
        assert cam.fps == 15

    def test_with_serial(self) -> None:
        cam = D405Config(enabled=True, serial="987654321")
        assert cam.serial == "987654321"


class TestDriverConfigFromYaml:
    def test_camera_sections_loaded(self) -> None:
        data = {
            "arducam": {"enabled": True, "device": "/dev/video0"},
            "d435if": {"enabled": True, "serial": "abc123"},
            "d405": {"enabled": True, "fps": 10},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.arducam.enabled is True
            assert config.arducam.device == "/dev/video0"
            assert config.d435if.enabled is True
            assert config.d435if.serial == "abc123"
            assert config.d405.enabled is True
            assert config.d405.fps == 10

    def test_partial_ports_override(self) -> None:
        data = {"ports": {"tts": 7000, "asr": 7001}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.ports.tts == 7000
            assert config.ports.asr == 7001
            assert config.ports.status == 5555  # default unchanged

    def test_service_section_loaded(self) -> None:
        data = {
            "service": {"status_rate_hz": 25.0},
            "asr": {"timeout_seconds": 30.0},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()

            config = DriverConfig.from_yaml(f.name)
            assert config.service.status_rate_hz == 25.0
            assert config.asr.timeout_seconds == 30.0
