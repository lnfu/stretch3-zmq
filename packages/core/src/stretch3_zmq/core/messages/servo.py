from typing import cast

import msgpack
from pydantic import BaseModel, field_validator

from ..constants import SKIP_VALIDATION
from .pose_3d import Pose3D


class ServoCommand(BaseModel):
    ee_pose: Pose3D  # relative: end-effector delta pose in current EE frame
    gripper: float  # absolute: gripper opening, 0.0 = fully closed, 1.0 = fully open

    @field_validator("gripper")
    @classmethod
    def validate_gripper(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"gripper must be in [0, 1], got {v}")
        return v

    def to_bytes(self) -> bytes:
        return cast(bytes, msgpack.packb(self.model_dump()))

    @classmethod
    def from_bytes(cls, data: bytes) -> "ServoCommand":
        if SKIP_VALIDATION:
            return cls.model_construct(**msgpack.unpackb(data))
        return cls.model_validate(msgpack.unpackb(data))
