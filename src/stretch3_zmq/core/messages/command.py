from typing import Literal, cast

import msgpack
from pydantic import BaseModel, field_validator

from ..constants import SKIP_VALIDATION, JointName
from .pose_2d import Pose2D


class ManipulatorCommand(BaseModel):
    joint_positions: tuple[float, ...]

    @field_validator("joint_positions")
    @classmethod
    def validate_joints(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        n = len(JointName)
        if len(v) != n:
            raise ValueError(f"Need {n} joint positions, received {len(v)}")

        # TODO(lnfu): check range for each joint position

        return v

    def to_bytes(self) -> bytes:
        return cast(bytes, msgpack.packb(self.model_dump()))

    @classmethod
    def from_bytes(cls, data: bytes) -> "ManipulatorCommand":
        if SKIP_VALIDATION:
            return cls.model_construct(**msgpack.unpackb(data))
        return cls.model_validate(msgpack.unpackb(data))


class BaseCommand(BaseModel):
    mode: Literal["velocity", "position"] = "velocity"
    pose: Pose2D

    def to_bytes(self) -> bytes:
        return cast(bytes, msgpack.packb(self.model_dump()))

    @classmethod
    def from_bytes(cls, data: bytes) -> "BaseCommand":
        if SKIP_VALIDATION:
            return cls.model_construct(**msgpack.unpackb(data))
        return cls.model_validate(msgpack.unpackb(data))
