"""
Configuration module for Stretch3-ZMQ Driver.

Loads configuration from config.yaml file with Pydantic validation.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class PortsConfig(BaseModel):
    status: int = 5555
    command: int = 5556
    arducam: int = 6000
    d435if: int = 6001
    d405: int = 6002
    tts: int = 6101
    asr: int = 6102


class ServiceConfig(BaseModel):
    status_rate_hz: float = 50.0
    asr_timeout_seconds: float = 10.0
    tts_provider: str = "fish_audio"
    asr_provider: str = "deepgram"


class ArducamConfig(BaseModel):
    enabled: bool = False
    device: str = "/dev/video4"
    width: int = 1280
    height: int = 720
    fps: int = 30


class D435ifConfig(BaseModel):
    enabled: bool = False
    serial: str | None = None
    width: int = 640
    height: int = 480
    fps: int = 30


class D405Config(BaseModel):
    enabled: bool = False
    serial: str | None = None
    width: int = 640
    height: int = 480
    fps: int = 15


class DriverConfig(BaseModel):
    ports: PortsConfig = PortsConfig()
    service: ServiceConfig = ServiceConfig()
    arducam: ArducamConfig = ArducamConfig()
    d435if: D435ifConfig = D435ifConfig()
    d405: D405Config = D405Config()
    debug: bool = False

    @classmethod
    def from_yaml(cls, path: Path | str | None = None) -> "DriverConfig":
        """Load configuration from a YAML file."""
        if path is None:
            return cls()

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(**data)
