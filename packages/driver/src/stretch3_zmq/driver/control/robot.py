"""Low-level wrapper around stretch_body for joint position control."""

import logging
from collections.abc import Callable
from typing import Any

import numpy as np
import stretch_body.robot
from scipy.spatial.transform import Rotation

from stretch3_zmq.core.messages.command import BaseCommand, ManipulatorCommand
from stretch3_zmq.core.messages.orientation import Orientation
from stretch3_zmq.core.messages.pose_2d import Pose2D
from stretch3_zmq.core.messages.servo import ServoCommand
from stretch3_zmq.core.messages.status import IMU, Odometry, Status
from stretch3_zmq.core.messages.twist_2d import Twist2D
from stretch3_zmq.core.messages.vector_3d import Vector3D
from stretch3_zmq.driver.control.pin_model import PinModel

logger = logging.getLogger(__name__)

# Joint command mapping: index -> callable that executes the command
# Order matches JointName enum and Command.joint_positions indices
_JOINT_COMMANDS: list[Callable[[stretch_body.robot.Robot, float], None]] = [
    lambda r, v: r.base.translate_by(v),
    lambda r, v: r.base.rotate_by(v),
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
        Callable[[dict[str, Any]], dict[str, Any]],  # extract sub-dict
        str,  # position key
        str,  # velocity key
        str,  # effort key
    ]
] = [
    (lambda s: s, "", "", ""),  # base_translate: always 0.0
    (lambda s: s, "", "", ""),  # base_rotate: always 0.0
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

        self._pin_model = PinModel()
        logger.info("PinModel initialized successfully.")

    def execute_manipulator_command(self, command: ManipulatorCommand) -> None:
        """Execute a joint position command on the robot."""

        # TODO(lnfu): 目前先讓 command 允許 base rotate
        # 因此需要檢查是否同時控制 base translate + base rotate (不允許)
        # 未來如果要區分開 command & navigation, 或許就可以移除這部份 (同時移除 rotate)
        base_translate = command.joint_positions[0]
        base_rotate = command.joint_positions[1]

        if base_translate != 0.0 and base_rotate != 0.0:
            logger.warning(
                f"Skipping command: both base_translate ({base_translate}) and "
                f"base_rotate ({base_rotate}) are non-zero. Only one can be non-zero at a time."
            )
            return

        for i, (cmd_fn, value) in enumerate(
            zip(_JOINT_COMMANDS, command.joint_positions, strict=True)
        ):
            # TODO(lnfu): 這裡的判斷邏輯需要再想一下要不要移除
            # Skip base_translate (i=0) and base_rotate (i=1) if their values are 0.0
            # to avoid interfering with each other
            if (i == 0 or i == 1) and value == 0.0:
                continue
            cmd_fn(self._robot, value)

        self._robot.push_command()

    def execute_base_command(self, command: BaseCommand) -> None:
        """Execute a base command on the robot."""

        if command.mode == "position":
            if command.twist.linear != 0.0 and command.twist.angular != 0.0:
                logger.warning(
                    f"Skipping command: both base_translate ({command.twist.linear}) and "
                    f"base_rotate ({command.twist.angular}) are non-zero. "
                    "Only one can be non-zero at a time."
                )
                return
            if command.twist.linear != 0.0:
                self._robot.base.translate_by(command.twist.linear)
            if command.twist.angular != 0.0:
                self._robot.base.rotate_by(command.twist.angular)
            self._robot.push_command()
        elif command.mode == "velocity":
            raise NotImplementedError("Velocity control is not implemented yet.")
        else:
            raise ValueError(f"Unknown command mode: {command.mode}")

    def goto(self, twist: Twist2D) -> None:
        """Blocking base position move — returns only after motion completes."""
        if twist.linear != 0.0 and twist.angular != 0.0:
            raise ValueError(
                f"Skipping goto: both linear ({twist.linear}) and angular ({twist.angular}) "
                "are non-zero. Only one can be non-zero at a time."
            )
        if twist.linear != 0.0:
            self._robot.base.translate_by(twist.linear)
        if twist.angular != 0.0:
            self._robot.base.rotate_by(twist.angular)
        self._robot.push_command()
        self._robot.wait_command()  # blocking

    def servo(self, command: ServoCommand) -> None:
        """
        Execute an end-effector servo command.

        Converts the relative EE pose delta + absolute gripper value into joint positions
        via IK, then sends a ManipulatorCommand to the robot.

        Args:
            command: ServoCommand with relative ee_pose and absolute gripper (0~1).
        """
        joint_positions = self._solve_ik(command)
        self.execute_manipulator_command(ManipulatorCommand(joint_positions=joint_positions))

    def _solve_ik(
        self, command: ServoCommand
    ) -> tuple[float, ...]:  # TODO(lnfu) rename function & description
        """
        Solve inverse kinematics for the given servo command.

        Args:
            command: ServoCommand with relative ee_pose and absolute gripper (0-1).

        Returns:
            Joint positions tuple matching JointName order.
        """
        ee_frame = "link_grasp_center"

        # 1. Get current joint positions from robot status
        self._robot.pull_status()
        s = self._robot.status

        lift_pos = s["lift"]["pos"]
        arm_pos = s["arm"]["pos"]  # total extension (0-0.52)
        wrist_yaw = s["end_of_arm"]["wrist_yaw"]["pos"]
        wrist_pitch = s["end_of_arm"]["wrist_pitch"]["pos"]
        wrist_roll = s["end_of_arm"]["wrist_roll"]["pos"]

        # 2. Map stretch_body joints to URDF joint names
        #    The arm extension is split equally across 4 prismatic joints
        arm_per_segment = arm_pos / 4.0
        joint_positions = {
            "joint_base_translation": 0.0,
            "joint_lift": lift_pos,
            "joint_arm_l3": arm_per_segment,
            "joint_arm_l2": arm_per_segment,
            "joint_arm_l1": arm_per_segment,
            "joint_arm_l0": arm_per_segment,
            "joint_wrist_yaw": wrist_yaw,
            "joint_wrist_pitch": wrist_pitch,
            "joint_wrist_roll": wrist_roll,
        }

        # 3. Update pinocchio model with current joint positions (runs FK internally)
        self._pin_model.update_q(joint_positions)

        # 4. Get current EE pose in world frame (4x4 homogeneous matrix)
        current_ee_pose = self._pin_model.get_transform("base_link", ee_frame)

        # 5. Build the relative 4x4 transform from the servo command
        p = command.ee_pose.position
        o = command.ee_pose.orientation

        rot = Rotation.from_quat([o.x, o.y, o.z, o.w]).as_matrix()
        delta = np.eye(4)
        delta[:3, :3] = rot
        delta[:3, 3] = [p.x, p.y, p.z]

        # 6. Compute target EE pose in world frame: current * delta
        target_pose = current_ee_pose @ delta

        # 7. Run IK
        q_result = self._pin_model.ik(target_pose, ee_frame=ee_frame)
        if q_result is None:
            raise RuntimeError("IK did not converge")

        # 8. Extract joint positions from IK result and map back to JointName order
        model = self._pin_model.model

        def _get_q(name: str) -> float:
            jid = model.getJointId(name)
            idx = model.joints[jid].idx_q
            return float(q_result[idx])

        ik_base_translation = _get_q("joint_base_translation")
        ik_lift = _get_q("joint_lift")
        ik_arm = (
            _get_q("joint_arm_l3")
            + _get_q("joint_arm_l2")
            + _get_q("joint_arm_l1")
            + _get_q("joint_arm_l0")
        )
        ik_wrist_yaw = _get_q("joint_wrist_yaw")
        ik_wrist_pitch = _get_q("joint_wrist_pitch")
        ik_wrist_roll = _get_q("joint_wrist_roll")

        # Gripper: map from 0-1 (ServoCommand) to 0-100 (stretch_body)
        gripper_value = command.gripper * 100.0

        # Return in JointName order:
        # base_translate, base_rotate, lift, arm,
        # head_pan, head_tilt,
        # wrist_yaw, wrist_pitch, wrist_roll, gripper
        return (
            ik_base_translation,  # base_translate
            0.0,  # base_rotate (no base movement during servo)
            ik_lift,  # lift
            ik_arm,  # arm (summed from 4 segments)
            0.0,  # head_pan (unchanged)
            0.0,  # head_tilt (unchanged)
            ik_wrist_yaw,  # wrist_yaw
            ik_wrist_pitch,  # wrist_pitch
            ik_wrist_roll,  # wrist_roll
            gripper_value,  # gripper (mapped 0-1 -> 0-100)
        )

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
            if i == 0 or i == 1:
                # base_translate and base_rotate: differential commands, no absolute position
                # TODO(lnfu): 未來也許可以移除 base_rotate
                positions.append(0.0)
                velocities.append(0.0)
                efforts.append(0.0)
            else:
                joint = extract(s)
                positions.append(joint[pos_key])
                velocities.append(joint[vel_key])
                efforts.append(float(joint[eff_key]))

        return Status(
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
