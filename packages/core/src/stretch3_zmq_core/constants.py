"""Shared constants for ManipulatorCommand and Status data models."""

import os
from enum import StrEnum

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
