"""Tests for JointName enum and SKIP_VALIDATION constant."""

import importlib
import os
from enum import StrEnum

import pytest

from stretch3_zmq_core.constants import JointName


class TestJointName:
    def test_is_str_enum(self) -> None:
        assert issubclass(JointName, StrEnum)

    def test_has_ten_members(self) -> None:
        assert len(JointName) == 10

    def test_member_values(self) -> None:
        assert JointName.BASE_TRANSLATE.value == "base_translate"
        assert JointName.BASE_ROTATE.value == "base_rotate"
        assert JointName.LIFT.value == "lift"
        assert JointName.ARM.value == "arm"
        assert JointName.HEAD_PAN.value == "head_pan"
        assert JointName.HEAD_TILT.value == "head_tilt"
        assert JointName.WRIST_YAW.value == "wrist_yaw"
        assert JointName.WRIST_PITCH.value == "wrist_pitch"
        assert JointName.WRIST_ROLL.value == "wrist_roll"
        assert JointName.GRIPPER.value == "gripper"

    def test_order_matches_command_indices(self) -> None:
        """Enum order must match joint_positions indices in ManipulatorCommand."""
        members = list(JointName)
        assert members[0] == JointName.BASE_TRANSLATE
        assert members[1] == JointName.BASE_ROTATE
        assert members[2] == JointName.LIFT
        assert members[3] == JointName.ARM
        assert members[4] == JointName.HEAD_PAN
        assert members[5] == JointName.HEAD_TILT
        assert members[6] == JointName.WRIST_YAW
        assert members[7] == JointName.WRIST_PITCH
        assert members[8] == JointName.WRIST_ROLL
        assert members[9] == JointName.GRIPPER

    def test_str_comparison(self) -> None:
        assert JointName.LIFT.value == "lift"
        assert str(JointName.LIFT) == "lift"

    def test_value_lookup(self) -> None:
        assert JointName("lift") == JointName.LIFT
        assert JointName("arm") == JointName.ARM

    def test_unknown_value_raises(self) -> None:
        with pytest.raises(ValueError):
            JointName("unknown_joint")

    def test_iterable(self) -> None:
        names = [j.value for j in JointName]
        assert "lift" in names
        assert "gripper" in names
        assert len(names) == 10


class TestSkipValidation:
    def test_default_is_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SKIP_VALIDATION defaults to False when env var is absent."""
        monkeypatch.delenv("SKIP_VALIDATION", raising=False)
        import stretch3_zmq_core.constants as mod

        importlib.reload(mod)
        assert mod.SKIP_VALIDATION is False

    def test_enabled_when_set_to_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKIP_VALIDATION", "1")
        import stretch3_zmq_core.constants as mod

        importlib.reload(mod)
        assert mod.SKIP_VALIDATION is True

    def test_not_enabled_when_set_to_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKIP_VALIDATION", "0")
        import stretch3_zmq_core.constants as mod

        importlib.reload(mod)
        assert mod.SKIP_VALIDATION is False

    def test_not_enabled_for_other_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for val in ("true", "True", "yes", "on", "1 "):
            monkeypatch.setenv("SKIP_VALIDATION", val)
            import stretch3_zmq_core.constants as mod

            importlib.reload(mod)
            assert mod.SKIP_VALIDATION is False, f"Expected False for SKIP_VALIDATION={val!r}"

    def teardown_method(self) -> None:
        """Restore constants module to default state after each test."""
        os.environ.pop("SKIP_VALIDATION", None)
        import stretch3_zmq_core.constants as mod

        importlib.reload(mod)
