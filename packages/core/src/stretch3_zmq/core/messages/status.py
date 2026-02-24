from typing import cast

import msgpack
from pydantic import BaseModel

from ..constants import SKIP_VALIDATION
from .orientation import Orientation
from .pose_2d import Pose2D
from .twist_2d import Twist2D
from .vector_3d import Vector3D


class Odometry(BaseModel):
    pose: Pose2D
    twist: Twist2D


class IMU(BaseModel):
    orientation: Orientation
    acceleration: Vector3D
    gyro: Vector3D


class Status(BaseModel):
    # Battery
    is_charging: bool
    is_low_voltage: bool

    # Runstop
    runstop: bool

    # Odometry
    odometry: Odometry

    # IMU
    imu: IMU

    # Joint
    joint_positions: tuple[float, ...]
    joint_velocities: tuple[float, ...]
    joint_efforts: tuple[float, ...]

    def to_bytes(self) -> bytes:
        return cast(bytes, msgpack.packb(self.model_dump()))

    @classmethod
    def from_bytes(cls, data: bytes) -> "Status":
        if SKIP_VALIDATION:
            return cls.model_construct(**msgpack.unpackb(data))
        return cls.model_validate(msgpack.unpackb(data))
