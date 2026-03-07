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
    goto: int = 5557
    arducam: int = 6000
    d435if: int = 6001
    d405: int = 6002
    tts: int = 6101
    tts_status: int = 6102
    asr: int = 6103


class ServiceConfig(BaseModel):
    status_rate_hz: float = 15.0


class TTSConfig(BaseModel):
    enabled: bool = True
    provider: str = "fish_audio"
    voice_id: str = ""
    model_id: str | None = None
    output_format: str = "pcm_22050"  # ElevenLabs: pcm_22050 | pcm_24000 | pcm_44100 | pcm_48000
    speed: float = 1.0


class ASRConfig(BaseModel):
    enabled: bool = True
    provider: str = "deepgram"
    timeout_seconds: float = 10.0
    language: str = "en"
    model_id: str | None = None
    microphone: str = "auto"  # "auto" | "default" | device name substring (e.g. "DJI MIC MINI")


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


class JointProfileConfig(BaseModel):
    """Trapezoid motion profile for a single joint (v = max velocity, a = max acceleration)."""

    v: float
    a: float


class TrapezoidProfileConfig(BaseModel):
    # Prismatic joints (stretch_body uses v_m / a_m)
    lift: JointProfileConfig = JointProfileConfig(v=0.13, a=0.25)
    arm: JointProfileConfig = JointProfileConfig(v=0.05, a=0.05)
    # Rotary joints (stretch_body uses v_r / a_r)
    head_pan: JointProfileConfig = JointProfileConfig(v=1.0, a=4.0)
    head_tilt: JointProfileConfig = JointProfileConfig(v=3.0, a=8.0)
    wrist_yaw: JointProfileConfig = JointProfileConfig(v=0.75, a=1.5)
    wrist_pitch: JointProfileConfig = JointProfileConfig(v=1.0, a=4.0)
    wrist_roll: JointProfileConfig = JointProfileConfig(v=1.0, a=4.0)
    gripper: JointProfileConfig = JointProfileConfig(v=6.0, a=19.0)


class DriverConfig(BaseModel):
    ports: PortsConfig = PortsConfig()
    service: ServiceConfig = ServiceConfig()
    tts: TTSConfig = TTSConfig()
    asr: ASRConfig = ASRConfig()
    arducam: ArducamConfig = ArducamConfig()
    d435if: D435ifConfig = D435ifConfig()
    d405: D405Config = D405Config()
    trapezoid_profile: TrapezoidProfileConfig = TrapezoidProfileConfig()
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
