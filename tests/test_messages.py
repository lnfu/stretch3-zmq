"""Tests for sub-message data models: Pose2D, Twist2D, Vector3D, Orientation, Odometry, IMU."""

import pytest
from pydantic import ValidationError

from stretch3_zmq_core.messages.orientation import Orientation
from stretch3_zmq_core.messages.pose_2d import Pose2D
from stretch3_zmq_core.messages.status import IMU, Odometry
from stretch3_zmq_core.messages.twist_2d import Twist2D
from stretch3_zmq_core.messages.vector_3d import Vector3D


class TestPose2D:
    def test_defaults(self) -> None:
        pose = Pose2D()
        assert pose.x == 0.0
        assert pose.y == 0.0
        assert pose.theta == 0.0

    def test_explicit_values(self) -> None:
        pose = Pose2D(x=1.5, y=-2.3, theta=3.14)
        assert pose.x == 1.5
        assert pose.y == -2.3
        assert pose.theta == 3.14

    def test_negative_values(self) -> None:
        pose = Pose2D(x=-100.0, y=-200.0, theta=-3.14)
        assert pose.x == -100.0
        assert pose.y == -200.0

    def test_int_coerced_to_float(self) -> None:
        pose = Pose2D(x=1, y=2, theta=0)
        assert pose.x == 1.0
        assert isinstance(pose.x, float)

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValidationError):
            Pose2D(x="not_a_float")  # type: ignore[arg-type]

    def test_model_dump(self) -> None:
        pose = Pose2D(x=1.0, y=2.0, theta=0.5)
        d = pose.model_dump()
        assert d == {"x": 1.0, "y": 2.0, "theta": 0.5}

    def test_model_validate_from_dict(self) -> None:
        pose = Pose2D.model_validate({"x": 3.0, "y": 4.0, "theta": 1.5})
        assert pose.x == 3.0
        assert pose.theta == 1.5


class TestTwist2D:
    def test_defaults(self) -> None:
        twist = Twist2D()
        assert twist.linear == 0.0
        assert twist.angular == 0.0

    def test_explicit_values(self) -> None:
        twist = Twist2D(linear=0.5, angular=-0.3)
        assert twist.linear == 0.5
        assert twist.angular == -0.3

    def test_int_coerced(self) -> None:
        twist = Twist2D(linear=1, angular=0)
        assert twist.linear == 1.0

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            Twist2D(linear="fast")  # type: ignore[arg-type]

    def test_model_dump(self) -> None:
        twist = Twist2D(linear=0.5, angular=0.1)
        assert twist.model_dump() == {"linear": 0.5, "angular": 0.1}


class TestVector3D:
    def test_defaults(self) -> None:
        v = Vector3D()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_explicit_values(self) -> None:
        v = Vector3D(x=1.0, y=2.0, z=9.8)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 9.8

    def test_negative_z(self) -> None:
        v = Vector3D(x=0.0, y=0.0, z=-9.8)
        assert v.z == -9.8

    def test_model_dump(self) -> None:
        v = Vector3D(x=1.0, y=2.0, z=3.0)
        assert v.model_dump() == {"x": 1.0, "y": 2.0, "z": 3.0}

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Vector3D(x="bad")  # type: ignore[arg-type]


class TestOrientation:
    def test_creation(self) -> None:
        o = Orientation(roll=0.1, pitch=0.2, yaw=0.3)
        assert o.roll == 0.1
        assert o.pitch == 0.2
        assert o.yaw == 0.3

    def test_zero(self) -> None:
        o = Orientation(roll=0.0, pitch=0.0, yaw=0.0)
        assert o.roll == 0.0
        assert o.pitch == 0.0
        assert o.yaw == 0.0

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            # missing yaw
            Orientation(roll=0.0, pitch=0.0)  # type: ignore[call-arg]

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Orientation(roll="bad", pitch=0.0, yaw=0.0)  # type: ignore[arg-type]

    def test_model_dump(self) -> None:
        o = Orientation(roll=1.0, pitch=2.0, yaw=3.0)
        assert o.model_dump() == {"roll": 1.0, "pitch": 2.0, "yaw": 3.0}

    def test_full_rotation(self) -> None:
        import math

        o = Orientation(roll=math.pi, pitch=-math.pi / 2, yaw=2 * math.pi)
        assert abs(o.roll - math.pi) < 1e-9


class TestOdometry:
    def test_creation(self) -> None:
        odom = Odometry(
            pose=Pose2D(x=1.0, y=2.0, theta=0.5),
            twist=Twist2D(linear=0.1, angular=0.0),
        )
        assert odom.pose.x == 1.0
        assert odom.twist.linear == 0.1

    def test_nested_dict_construction(self) -> None:
        """Pydantic should accept nested dicts and coerce them to model instances."""
        odom = Odometry(
            pose={"x": 3.0, "y": 4.0, "theta": 1.0},  # type: ignore[arg-type]
            twist={"linear": 0.5, "angular": 0.1},  # type: ignore[arg-type]
        )
        assert odom.pose.x == 3.0
        assert isinstance(odom.pose, Pose2D)
        assert isinstance(odom.twist, Twist2D)

    def test_missing_pose_raises(self) -> None:
        with pytest.raises(ValidationError):
            Odometry(twist=Twist2D())  # type: ignore[call-arg]

    def test_missing_twist_raises(self) -> None:
        with pytest.raises(ValidationError):
            Odometry(pose=Pose2D())  # type: ignore[call-arg]

    def test_model_dump_nested(self) -> None:
        odom = Odometry(
            pose=Pose2D(x=1.0, y=2.0, theta=0.0),
            twist=Twist2D(linear=0.5, angular=0.0),
        )
        d = odom.model_dump()
        assert "pose" in d
        assert "twist" in d
        assert d["pose"]["x"] == 1.0
        assert d["twist"]["linear"] == 0.5

    def test_default_pose_values(self) -> None:
        odom = Odometry(pose=Pose2D(), twist=Twist2D())
        assert odom.pose.x == 0.0
        assert odom.twist.linear == 0.0


class TestIMU:
    def test_creation(self) -> None:
        imu = IMU(
            orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
            acceleration=Vector3D(x=0.0, y=0.0, z=9.8),
            gyro=Vector3D(),
        )
        assert imu.acceleration.z == 9.8
        assert imu.gyro.x == 0.0

    def test_missing_gyro_raises(self) -> None:
        with pytest.raises(ValidationError):
            IMU(  # type: ignore[call-arg]
                orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
                acceleration=Vector3D(),
            )

    def test_missing_orientation_raises(self) -> None:
        with pytest.raises(ValidationError):
            IMU(  # type: ignore[call-arg]
                acceleration=Vector3D(),
                gyro=Vector3D(),
            )

    def test_nested_dict_construction(self) -> None:
        imu = IMU(
            orientation={"roll": 0.1, "pitch": 0.2, "yaw": 0.3},  # type: ignore[arg-type]
            acceleration={"x": 0.0, "y": 0.0, "z": 9.8},  # type: ignore[arg-type]
            gyro={"x": 0.0, "y": 0.0, "z": 0.0},  # type: ignore[arg-type]
        )
        assert imu.orientation.roll == 0.1
        assert isinstance(imu.orientation, Orientation)
        assert imu.acceleration.z == 9.8

    def test_model_dump(self) -> None:
        imu = IMU(
            orientation=Orientation(roll=0.0, pitch=0.0, yaw=0.0),
            acceleration=Vector3D(x=0.0, y=0.0, z=9.8),
            gyro=Vector3D(x=0.01, y=0.02, z=0.03),
        )
        d = imu.model_dump()
        assert "orientation" in d
        assert "acceleration" in d
        assert "gyro" in d
        assert d["acceleration"]["z"] == 9.8
        assert d["gyro"]["x"] == 0.01
