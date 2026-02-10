import msgpack
from pydantic import BaseModel, field_validator

from .constants import NUM_JOINTS, SKIP_VALIDATION


class Command(BaseModel):
    joint_positions: tuple[float, ...]

    @field_validator("joint_positions")
    @classmethod
    def validate_joints(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if len(v) != NUM_JOINTS:
            raise ValueError(f"Need {NUM_JOINTS} joint positions, received {len(v)}")

        # TODO(lnfu): check range for each joint position

        return v

    def to_bytes(self) -> bytes:
        return msgpack.packb(self.model_dump())

    @classmethod
    def from_bytes(cls, data: bytes) -> "Command":
        if SKIP_VALIDATION:
            return cls.model_construct(**msgpack.unpackb(data))
        return cls.model_validate(msgpack.unpackb(data))
