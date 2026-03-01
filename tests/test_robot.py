"""Tests for StretchRobot hardware wrapper.

Tests are split into two groups:
- Mock-based unit tests: exercise execute_manipulator_command / get_status branching logic
  using a mocked stretch_body.Robot.  These run on any machine because
  stretch_body is stubbed out before the driver package is imported.
- Hardware integration tests (``TestStretchRobotHardware``): marked with
  ``requires_robot`` and skipped unless HELLO_FLEET_ID is set.
"""

import os
import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from stretch3_zmq.driver.control.robot import StretchRobot

# ---------------------------------------------------------------------------
# Stub stretch_body before any driver package import.
# stretch_body.robot_params runs fleet-path lookups at class-definition
# time, so the module fails to import when HELLO_FLEET_PATH is absent even
# if we only intend to unit-test with mocks.
# ---------------------------------------------------------------------------
for _mod in (
    "stretch_body",
    "stretch_body.robot",
    "stretch_body.robot_params",
    "stretch_body.hello_utils",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from stretch3_zmq.core.messages.command import ManipulatorCommand  # noqa: E402
from stretch3_zmq.core.messages.status import Status  # noqa: E402

requires_robot = pytest.mark.skipif(
    not os.getenv("HELLO_FLEET_ID"),
    reason="Requires real robot environment (HELLO_FLEET_ID not set)",
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_mock_inner() -> MagicMock:
    """Return a fully-configured mock for stretch_body.robot.Robot."""
    mock = MagicMock()
    mock.startup.return_value = True
    mock.is_homed.return_value = True

    # Status dict layout mirroring the real stretch_body structure
    mock.status = {
        "pimu": {
            "charger_is_charging": False,
            "low_voltage_alert": False,
            "runstop_event": False,
            "imu": {
                "roll": 0.01,
                "pitch": -0.02,
                "heading": 1.57,
                "ax": 0.1,
                "ay": -0.1,
                "az": 9.8,
                "gx": 0.0,
                "gy": 0.0,
                "gz": 0.0,
            },
        },
        "base": {"x": 1.0, "y": 2.0, "theta": 0.5, "x_vel": 0.1, "theta_vel": 0.0},
        "lift": {"pos": 0.5, "vel": 0.0, "force": 0.0},
        "arm": {"pos": 0.3, "vel": 0.0, "force": 0.0},
        "head": {
            "head_pan": {"pos": 0.0, "vel": 0.0, "effort": 0.0},
            "head_tilt": {"pos": -0.5, "vel": 0.0, "effort": 0.0},
        },
        "end_of_arm": {
            "wrist_yaw": {"pos": 0.0, "vel": 0.0, "effort": 0.0},
            "wrist_pitch": {"pos": 0.0, "vel": 0.0, "effort": 0.0},
            "wrist_roll": {"pos": 0.0, "vel": 0.0, "effort": 0.0},
            "stretch_gripper": {"pos": 50.0, "vel": 0.0, "effort": 0.0},
        },
    }
    return mock


@pytest.fixture  # type: ignore[untyped-decorator]
def mock_robot() -> Iterator[tuple["StretchRobot", MagicMock]]:
    """Fixture providing a StretchRobot with mocked internals.

    We bypass __init__ (which calls stretch_body.robot.Robot()) via __new__
    and directly inject the mock_inner as the internal _robot.  This avoids
    the MagicMock attribute-aliasing issue where sys.modules["stretch_body.robot"]
    and stretch_body.robot (as seen inside robot.py) are different objects.
    """
    from stretch3_zmq.driver.control.robot import StretchRobot

    mock_inner = _make_mock_inner()
    robot = StretchRobot.__new__(StretchRobot)
    robot._robot = mock_inner
    yield robot, mock_inner


# ---------------------------------------------------------------------------
# Unit tests (mock-based, no real hardware)
# ---------------------------------------------------------------------------


class TestExecuteCommandLogic:
    def test_base_translate_only_calls_translate(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        positions = (0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.base.translate_by.assert_called_once_with(0.5)
        inner.base.rotate_by.assert_not_called()
        inner.push_command.assert_called_once()

    def test_base_rotate_only_calls_rotate(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.base.rotate_by.assert_called_once_with(0.3)
        inner.base.translate_by.assert_not_called()
        inner.push_command.assert_called_once()

    def test_both_base_nonzero_skips_command(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        """When both base_translate and base_rotate are non-zero, the command is skipped."""
        robot, inner = mock_robot
        positions = (0.5, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.base.translate_by.assert_not_called()
        inner.base.rotate_by.assert_not_called()
        inner.push_command.assert_not_called()

    def test_all_zeros_skips_base_commands(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        """Zero values for base joints are skipped even if other joints are zero."""
        robot, inner = mock_robot
        positions = (0.0,) * 10
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.base.translate_by.assert_not_called()
        inner.base.rotate_by.assert_not_called()
        # Non-base joints (all 0.0) are still sent
        inner.push_command.assert_called_once()

    def test_lift_command_calls_move_to(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.lift.move_to.assert_called_once_with(0.6)

    def test_arm_command_calls_move_to(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.arm.move_to.assert_called_once_with(0.4)

    def test_head_pan_command(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.0, 0.0, -0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.head.move_to.assert_any_call("head_pan", -0.5)

    def test_head_tilt_command(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.0, 0.0, 0.0, -0.3, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.head.move_to.assert_any_call("head_tilt", -0.3)

    def test_wrist_yaw_command(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.end_of_arm.move_to.assert_any_call("wrist_yaw", 1.0)

    def test_gripper_command(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 80.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.end_of_arm.move_to.assert_any_call("stretch_gripper", 80.0)

    def test_push_command_called_after_valid_command(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        positions = (0.0, 0.0, 0.5, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.push_command.assert_called_once()

    def test_push_command_not_called_when_skipped(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        positions = (0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        robot.execute_manipulator_command(ManipulatorCommand(joint_positions=positions))
        inner.push_command.assert_not_called()


class TestGetStatusLogic:
    def test_get_status_returns_status_instance(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, _ = mock_robot
        status = robot.get_status()
        assert isinstance(status, Status)

    def test_get_status_calls_pull_status(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        robot.get_status()
        inner.pull_status.assert_called_once()

    def test_get_status_joint_counts(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        """get_status returns 10 joint readings (one per JointName entry)."""
        from stretch3_zmq.core.constants import JointName

        robot, _ = mock_robot
        status = robot.get_status()
        n = len(JointName)
        assert len(status.joint_positions) == n
        assert len(status.joint_velocities) == n
        assert len(status.joint_efforts) == n

    def test_get_status_base_joints_always_zero(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        """Base translate (index 0) and base rotate (index 1) are always 0.0."""
        robot, _ = mock_robot
        status = robot.get_status()
        assert status.joint_positions[0] == 0.0  # base_translate
        assert status.joint_positions[1] == 0.0  # base_rotate
        assert status.joint_velocities[0] == 0.0
        assert status.joint_velocities[1] == 0.0
        assert status.joint_efforts[0] == 0.0
        assert status.joint_efforts[1] == 0.0

    def test_get_status_lift_position(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["lift"]["pos"] = 0.75
        status = robot.get_status()
        assert status.joint_positions[2] == 0.75  # lift is index 2

    def test_get_status_arm_position(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["arm"]["pos"] = 0.45
        status = robot.get_status()
        assert status.joint_positions[3] == 0.45  # arm is index 3

    def test_get_status_odometry_fields(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["base"]["x"] = 3.0
        inner.status["base"]["y"] = 4.0
        inner.status["base"]["theta"] = 1.2
        status = robot.get_status()
        assert status.odometry.pose.x == 3.0
        assert status.odometry.pose.y == 4.0
        assert status.odometry.pose.theta == 1.2

    def test_get_status_imu_acceleration(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        inner.status["pimu"]["imu"]["az"] = 9.81
        status = robot.get_status()
        assert abs(status.imu.acceleration.z - 9.81) < 1e-9

    def test_get_status_battery_fields(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["pimu"]["charger_is_charging"] = True
        inner.status["pimu"]["low_voltage_alert"] = True
        status = robot.get_status()
        assert status.is_charging is True
        assert status.is_low_voltage is True

    def test_get_status_runstop_field(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["pimu"]["runstop_event"] = True
        status = robot.get_status()
        assert status.runstop is True

    def test_get_status_imu_orientation(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["pimu"]["imu"]["roll"] = 0.1
        inner.status["pimu"]["imu"]["pitch"] = 0.2
        inner.status["pimu"]["imu"]["heading"] = 1.57
        status = robot.get_status()
        assert abs(status.imu.orientation.roll - 0.1) < 1e-9
        assert abs(status.imu.orientation.pitch - 0.2) < 1e-9
        assert abs(status.imu.orientation.yaw - 1.57) < 1e-9

    def test_get_status_twist(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        inner.status["base"]["x_vel"] = 0.3
        inner.status["base"]["theta_vel"] = 0.1
        status = robot.get_status()
        assert abs(status.odometry.twist.linear - 0.3) < 1e-9
        assert abs(status.odometry.twist.angular - 0.1) < 1e-9


class TestGotoLogic:
    def test_goto_linear_only_calls_translate(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        from stretch3_zmq.core.messages.twist_2d import Twist2D

        robot, inner = mock_robot
        robot.goto(Twist2D(linear=0.5, angular=0.0))
        inner.base.translate_by.assert_called_once_with(0.5)
        inner.base.rotate_by.assert_not_called()
        inner.push_command.assert_called_once()
        inner.wait_command.assert_called_once()

    def test_goto_angular_only_calls_rotate(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        from stretch3_zmq.core.messages.twist_2d import Twist2D

        robot, inner = mock_robot
        robot.goto(Twist2D(linear=0.0, angular=0.3))
        inner.base.rotate_by.assert_called_once_with(0.3)
        inner.base.translate_by.assert_not_called()
        inner.push_command.assert_called_once()
        inner.wait_command.assert_called_once()

    def test_goto_both_nonzero_raises(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        from stretch3_zmq.core.messages.twist_2d import Twist2D

        robot, inner = mock_robot
        with pytest.raises(ValueError, match="both linear"):
            robot.goto(Twist2D(linear=0.5, angular=0.3))
        inner.push_command.assert_not_called()
        inner.wait_command.assert_not_called()

    def test_goto_both_zero_skips_move(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        from stretch3_zmq.core.messages.twist_2d import Twist2D

        robot, inner = mock_robot
        robot.goto(Twist2D(linear=0.0, angular=0.0))
        inner.base.translate_by.assert_not_called()
        inner.base.rotate_by.assert_not_called()
        inner.push_command.assert_called_once()
        inner.wait_command.assert_called_once()


class TestStretchRobotLifecycle:
    def test_startup_failure_raises(self) -> None:
        """__init__ raises when stretch_body.Robot.startup() returns False."""
        mock_inner = MagicMock()
        mock_inner.startup.return_value = False
        # Patch Robot where it's imported in robot.py
        with patch(
            "stretch3_zmq.driver.control.robot.stretch_body.robot.Robot", return_value=mock_inner
        ):
            from stretch3_zmq.driver.control.robot import StretchRobot

            with pytest.raises(RuntimeError, match="Failed to startup stretch robot"):
                StretchRobot()

    def test_not_homed_after_home_raises(self) -> None:
        """__init__ raises when the robot is never homed even after home() is called."""
        mock_inner = MagicMock()
        mock_inner.startup.return_value = True
        mock_inner.is_homed.return_value = False  # never becomes homed
        with patch(
            "stretch3_zmq.driver.control.robot.stretch_body.robot.Robot", return_value=mock_inner
        ):
            from stretch3_zmq.driver.control.robot import StretchRobot

            with pytest.raises(RuntimeError, match="not homed"):
                StretchRobot()

    def test_shutdown_calls_robot_shutdown(
        self, mock_robot: tuple["StretchRobot", MagicMock]
    ) -> None:
        robot, inner = mock_robot
        robot.shutdown()
        inner.shutdown.assert_called_once()

    def test_stop_calls_robot_stop(self, mock_robot: tuple["StretchRobot", MagicMock]) -> None:
        robot, inner = mock_robot
        robot.stop()
        inner.stop.assert_called_once()


# ---------------------------------------------------------------------------
# Hardware integration tests (require real robot)
# ---------------------------------------------------------------------------


@requires_robot
class TestStretchRobotHardware:
    def test_startup_and_shutdown(self) -> None:
        from stretch3_zmq.driver.control.robot import StretchRobot

        robot = StretchRobot()
        robot.shutdown()

    def test_get_status_returns_valid_status(self) -> None:
        from stretch3_zmq.driver.control.robot import StretchRobot

        robot = StretchRobot()
        try:
            status = robot.get_status()
            assert isinstance(status, Status)
            assert len(status.joint_positions) == 9
            assert len(status.joint_velocities) == 9
            assert len(status.joint_efforts) == 9
            assert isinstance(status.is_charging, bool)
            assert isinstance(status.is_low_voltage, bool)
            assert isinstance(status.runstop, bool)
        finally:
            robot.shutdown()

    def test_get_status_base_joints_are_zero(self) -> None:
        from stretch3_zmq.driver.control.robot import StretchRobot

        robot = StretchRobot()
        try:
            status = robot.get_status()
            assert status.joint_positions[0] == 0.0  # base_translate
            assert status.joint_positions[1] == 0.0  # base_rotate
        finally:
            robot.shutdown()

    def test_execute_command_dual_base_is_noop(self) -> None:
        """Command with both base axes non-zero must be silently skipped."""
        from stretch3_zmq.driver.control.robot import StretchRobot

        robot = StretchRobot()
        try:
            positions = (0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            cmd = ManipulatorCommand(joint_positions=positions)
            robot.execute_manipulator_command(cmd)  # should not raise
        finally:
            robot.shutdown()

    def test_get_status_serializable(self) -> None:
        """Status returned by real hardware must survive a to_bytes/from_bytes roundtrip."""
        from stretch3_zmq.driver.control.robot import StretchRobot

        robot = StretchRobot()
        try:
            status = robot.get_status()
            data = status.to_bytes()
            restored = Status.from_bytes(data)
            assert restored.is_charging == status.is_charging
            assert restored.joint_positions == status.joint_positions
        finally:
            robot.shutdown()
