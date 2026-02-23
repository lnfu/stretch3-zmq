"""Tests for Status data model serialization."""

import msgpack
import pytest
from pydantic import ValidationError

import stretch3_zmq_core.messages.status as status_module
from stretch3_zmq_core.messages.orientation import Orientation
from stretch3_zmq_core.messages.pose_2d import Pose2D
from stretch3_zmq_core.messages.status import IMU, Odometry, Status
from stretch3_zmq_core.messages.twist_2d import Twist2D
from stretch3_zmq_core.messages.vector_3d import Vector3D


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
        assert restored.is_charging == original.is_charging
        assert restored.joint_positions == original.joint_positions
        assert restored.odometry.pose.x == original.odometry.pose.x
        assert restored.imu.acceleration.z == original.imu.acceleration.z

    def test_from_bytes_invalid_msgpack(self) -> None:
        with pytest.raises(
            (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException, ValidationError)
        ):
            Status.from_bytes(b"not msgpack")

    def test_msgpack_format(self) -> None:
        """Verify Status is serialized with msgpack."""
        status = _make_status()
        data = status.to_bytes()

        # Decode with msgpack and verify structure
        unpacked = msgpack.unpackb(data)
        assert "is_charging" in unpacked
        assert "runstop" in unpacked
        assert "joint_positions" in unpacked
        assert "odometry" in unpacked
        assert "imu" in unpacked
        # Timestamp should not be in the serialized data anymore
        assert "timestamp" not in unpacked

    def test_charging_and_low_voltage_flags(self) -> None:
        status = Status(
            is_charging=True,
            is_low_voltage=True,
            runstop=True,
            odometry=Odometry(pose=Pose2D(), twist=Twist2D()),
            imu=IMU(
                orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
                acceleration=Vector3D(),
                gyro=Vector3D(),
            ),
            joint_positions=(0.0,) * 9,
            joint_velocities=(0.0,) * 9,
            joint_efforts=(0.0,) * 9,
        )
        assert status.is_charging is True
        assert status.is_low_voltage is True
        assert status.runstop is True

    def test_from_bytes_preserves_all_fields(self) -> None:
        original = _make_status()
        restored = Status.from_bytes(original.to_bytes())
        assert restored.runstop == original.runstop
        assert restored.is_low_voltage == original.is_low_voltage
        assert restored.joint_velocities == original.joint_velocities
        assert restored.joint_efforts == original.joint_efforts
        assert restored.odometry.pose.theta == original.odometry.pose.theta
        assert restored.imu.orientation.yaw == original.imu.orientation.yaw
        assert restored.imu.gyro.x == original.imu.gyro.x

    def test_from_bytes_missing_required_field_raises(self) -> None:
        """from_bytes should raise ValidationError when a required field is absent."""
        data = msgpack.packb({"is_charging": False})  # missing most fields
        with pytest.raises(ValidationError):
            Status.from_bytes(data)

    def test_to_bytes_is_deterministic(self) -> None:
        status = _make_status()
        assert status.to_bytes() == status.to_bytes()

    def test_skip_validation_allows_incomplete_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With SKIP_VALIDATION=True, from_bytes skips pydantic validation."""
        monkeypatch.setattr(status_module, "SKIP_VALIDATION", True)
        data = msgpack.packb({"is_charging": False})
        status = Status.from_bytes(data)
        # model_construct does not set missing fields, so they're absent
        assert status.is_charging is False

    def test_skip_validation_false_enforces_schema(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(status_module, "SKIP_VALIDATION", False)
        data = msgpack.packb({"is_charging": False})
        with pytest.raises(ValidationError):
            Status.from_bytes(data)

    def test_joint_values_roundtrip(self) -> None:
        positions = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
        velocities = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8)
        efforts = (2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8)
        original = Status(
            is_charging=False,
            is_low_voltage=False,
            runstop=False,
            odometry=Odometry(pose=Pose2D(), twist=Twist2D()),
            imu=IMU(
                orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
                acceleration=Vector3D(),
                gyro=Vector3D(),
            ),
            joint_positions=positions,
            joint_velocities=velocities,
            joint_efforts=efforts,
        )
        restored = Status.from_bytes(original.to_bytes())
        assert restored.joint_positions == positions
        assert restored.joint_velocities == velocities
        assert restored.joint_efforts == efforts
