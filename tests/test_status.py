"""Tests for Status data model serialization."""

import json

import pytest
from pydantic import ValidationError

from stretch3_zmq.core.messages.orientation import Orientation
from stretch3_zmq.core.messages.pose_2d import Pose2D
from stretch3_zmq.core.messages.status import IMU, Odometry, Status
from stretch3_zmq.core.messages.twist_2d import Twist2D
from stretch3_zmq.core.messages.vector_3d import Vector3D


def _make_status() -> Status:
    """Create a sample Status for testing."""
    return Status(
        is_charging=False,
        is_low_voltage=False,
        runstop=False,
        odometry=Odometry(
            pose=Pose2D(x=1.0, y=2.0, theta=0.5),
            twist=Twist2D(linear=0.1, angular=0.0),
        ),
        imu=IMU(
            orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
            acceleration=Vector3D(x=0.0, y=0.0, z=9.8),
            gyro=Vector3D(),
        ),
        joint_positions=(0.0,) * 9,
        joint_velocities=(0.0,) * 9,
        joint_efforts=(0.0,) * 9,
    )


class TestStatus:
    def test_create_status(self) -> None:
        status = _make_status()
        assert status.timestamp > 0
        assert not status.is_charging
        assert not status.runstop
        assert len(status.joint_positions) == 9

    def test_to_bytes_returns_bytes(self) -> None:
        status = _make_status()
        data = status.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_from_bytes_roundtrip(self) -> None:
        original = _make_status()
        data = original.to_bytes()
        restored = Status.from_bytes(data)
        assert restored.timestamp == original.timestamp
        assert restored.is_charging == original.is_charging
        assert restored.joint_positions == original.joint_positions
        assert restored.odometry.pose.x == original.odometry.pose.x
        assert restored.imu.acceleration.z == original.imu.acceleration.z

    def test_from_bytes_invalid_json(self) -> None:
        with pytest.raises((json.JSONDecodeError, ValidationError)):
            Status.from_bytes(b"not json")
