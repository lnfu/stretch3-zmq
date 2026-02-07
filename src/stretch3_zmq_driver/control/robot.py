"""Low-level wrapper around stretch_body for joint position control."""

import logging
import time
from collections.abc import Callable

import stretch_body.robot

from stretch3_zmq_core.messages.command import Command
from stretch3_zmq_core.messages.orientation import Orientation
from stretch3_zmq_core.messages.pose_2d import Pose2D
from stretch3_zmq_core.messages.status import IMU, Odometry, Status
from stretch3_zmq_core.messages.twist_2d import Twist2D
from stretch3_zmq_core.messages.vector_3d import Vector3D

logger = logging.getLogger(__name__)

# Joint command mapping: index -> callable that executes the command
# Order matches JointName enum and Command.joint_positions indices
_JOINT_COMMANDS: list[Callable[[stretch_body.robot.Robot, float], None]] = [
    lambda r, v: r.base.translate_by(v),
    lambda r, v: r.lift.move_to(v),
    lambda r, v: r.arm.move_to(v),
    lambda r, v: r.head.move_to("head_pan", v),
    lambda r, v: r.head.move_to("head_tilt", v),
    lambda r, v: r.end_of_arm.move_to("wrist_yaw", v),
    lambda r, v: r.end_of_arm.move_to("wrist_pitch", v),
    lambda r, v: r.end_of_arm.move_to("wrist_roll", v),
    lambda r, v: r.end_of_arm.move_to("stretch_gripper", v),
]

# Joint status reading: (status_path, pos_key, vel_key, effort_key)
# Each entry defines how to extract position, velocity, and effort for a joint.
_JOINT_STATUS_READERS: list[
    tuple[
        Callable[[dict], dict],  # extract sub-dict
        str,  # position key
        str,  # velocity key
        str,  # effort key
    ]
] = [
    (lambda s: s, "", "", ""),  # base_translate: always 0.0
    (lambda s: s["lift"], "pos", "vel", "force"),
    (lambda s: s["arm"], "pos", "vel", "force"),
    (lambda s: s["head"]["head_pan"], "pos", "vel", "effort"),
    (lambda s: s["head"]["head_tilt"], "pos", "vel", "effort"),
    (lambda s: s["end_of_arm"]["wrist_yaw"], "pos", "vel", "effort"),
    (lambda s: s["end_of_arm"]["wrist_pitch"], "pos", "vel", "effort"),
    (lambda s: s["end_of_arm"]["wrist_roll"], "pos", "vel", "effort"),
    (lambda s: s["end_of_arm"]["stretch_gripper"], "pos", "vel", "effort"),
]


class StretchRobot:
    """
    Wrapper for the Hello Robot Stretch 3 robot.
    Handles low-level control using stretch_body.
    """

    def __init__(self) -> None:
        logger.info("Initializing StretchRobot...")
        self._robot = stretch_body.robot.Robot()
        if not self._robot.startup():
            logger.error("Failed to startup stretch robot")
            raise RuntimeError("Failed to startup stretch robot")

        if not self._robot.is_homed():
            self._robot.home()

        if not self._robot.is_homed():
            logger.error("Stretch robot is not homed")
            raise RuntimeError("Stretch robot is not homed")

        logger.info("StretchRobot started successfully.")

    def execute_command(self, command: Command) -> None:
        """Execute a joint position command on the robot."""
        for cmd_fn, value in zip(_JOINT_COMMANDS, command.joint_positions, strict=True):
            cmd_fn(self._robot, value)

        self._robot.push_command()

    def stop(self) -> None:
        """Stop the robot motion."""
        self._robot.stop()

    def get_status(self) -> Status:
        """
        Get the current robot status.

        Returns:
            Status: Current robot status including battery, odometry, IMU, and joint states.
        """
        self._robot.pull_status()
        s = self._robot.status

        # Battery & Runstop
        is_charging = s["pimu"]["charger_is_charging"]
        is_low_voltage = s["pimu"]["low_voltage_alert"]
        runstop = s["pimu"]["runstop_event"]

        # Odometry
        odometry = Odometry(
            pose=Pose2D(
                x=s["base"]["x"],
                y=s["base"]["y"],
                theta=s["base"]["theta"],
            ),
            twist=Twist2D(
                linear=s["base"]["x_vel"],
                angular=s["base"]["theta_vel"],
            ),
        )

        # IMU
        imu_data = s["pimu"]["imu"]
        imu = IMU(
            orientation=Orientation(
                roll=imu_data["roll"],
                pitch=imu_data["pitch"],
                yaw=imu_data["heading"],
            ),
            acceleration=Vector3D(
                x=imu_data["ax"],
                y=imu_data["ay"],
                z=imu_data["az"],
            ),
            gyro=Vector3D(
                x=imu_data["gx"],
                y=imu_data["gy"],
                z=imu_data["gz"],
            ),
        )

        # Joints — read positions, velocities, efforts from status dict
        positions: list[float] = []
        velocities: list[float] = []
        efforts: list[float] = []

        for i, (extract, pos_key, vel_key, eff_key) in enumerate(_JOINT_STATUS_READERS):
            if i == 0:
                # base_translate: relative, no absolute position
                positions.append(0.0)
                velocities.append(0.0)
                efforts.append(0.0)
            else:
                joint = extract(s)
                positions.append(joint[pos_key])
                velocities.append(joint[vel_key])
                efforts.append(float(joint[eff_key]))

        return Status(
            timestamp=time.time_ns(),
            is_charging=is_charging,
            is_low_voltage=is_low_voltage,
            runstop=runstop,
            odometry=odometry,
            imu=imu,
            joint_positions=tuple(positions),
            joint_velocities=tuple(velocities),
            joint_efforts=tuple(efforts),
        )

    def shutdown(self) -> None:
        """Shutdown the robot connection."""
        self._robot.shutdown()
