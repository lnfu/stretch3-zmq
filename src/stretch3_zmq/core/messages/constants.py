"""Shared constants for Command and Status data models."""

import os
from enum import StrEnum

NUM_JOINTS = 10
SKIP_VALIDATION = os.getenv("SKIP_VALIDATION", "0") == "1"


class JointName(StrEnum):
    BASE_TRANSLATE = "base_translate"
    BASE_ROTATE = "base_rotate"
    LIFT = "lift"
    ARM = "arm"
    HEAD_PAN = "head_pan"
    HEAD_TILT = "head_tilt"
    WRIST_YAW = "wrist_yaw"
    WRIST_PITCH = "wrist_pitch"
    WRIST_ROLL = "wrist_roll"
    GRIPPER = "gripper"
