"""Tests for ManipulatorCommand data model serialization and validation."""

import msgpack
import pytest
from pydantic import ValidationError

import stretch3_zmq.core.messages.command as cmd_module
from stretch3_zmq.core.messages.command import ManipulatorCommand


class TestManipulatorCommand:
    def test_create_valid_command(self) -> None:
        positions = (0.0, 0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)
        cmd = ManipulatorCommand(joint_positions=positions)
        assert cmd.joint_positions == positions

    def test_invalid_joint_count_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 10 joint positions"):
            ManipulatorCommand(joint_positions=(0.0, 0.1))

    def test_empty_joints_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 10 joint positions"):
            ManipulatorCommand(joint_positions=())

    def test_to_bytes_returns_bytes(self) -> None:
        positions = (0.0,) * 10
        cmd = ManipulatorCommand(joint_positions=positions)
        data = cmd.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_from_bytes_roundtrip(self) -> None:
        positions = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)
        original = ManipulatorCommand(joint_positions=positions)
        data = original.to_bytes()
        restored = ManipulatorCommand.from_bytes(data)
        assert restored.joint_positions == original.joint_positions

    def test_from_bytes_invalid_msgpack(self) -> None:
        with pytest.raises(
            (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException, ValidationError)
        ):
            ManipulatorCommand.from_bytes(b"not msgpack")

    def test_from_bytes_missing_fields(self) -> None:
        # Missing joint_positions field
        with pytest.raises(ValidationError):
            ManipulatorCommand.from_bytes(msgpack.packb({}))

    def test_msgpack_format(self) -> None:
        """Verify messages are serialized with msgpack."""
        positions = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
        cmd = ManipulatorCommand(joint_positions=positions)
        data = cmd.to_bytes()

        # Decode with msgpack and verify structure
        unpacked = msgpack.unpackb(data)
        assert "joint_positions" in unpacked
        assert unpacked["joint_positions"] == list(positions)
        # Timestamp should not be in the serialized data anymore
        assert "timestamp" not in unpacked

    def test_nine_joints_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 10 joint positions"):
            ManipulatorCommand(joint_positions=(0.0,) * 9)

    def test_eleven_joints_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 10 joint positions"):
            ManipulatorCommand(joint_positions=(0.0,) * 11)

    def test_list_input_accepted(self) -> None:
        """Pydantic should coerce a list to a tuple."""
        positions_list = [0.0, 0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0]
        cmd = ManipulatorCommand(joint_positions=positions_list)
        assert len(cmd.joint_positions) == 10

    def test_negative_values_accepted(self) -> None:
        """Negative joint positions should be allowed (no range check yet)."""
        positions = (-1.0, -1.0, -0.5, -0.2, -1.0, -1.0, -3.14, -1.0, -1.0, -50.0)
        cmd = ManipulatorCommand(joint_positions=positions)
        assert cmd.joint_positions[0] == -1.0

    def test_to_bytes_is_deterministic(self) -> None:
        """Same input should always produce the same bytes."""
        positions = (0.0, 0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)
        cmd = ManipulatorCommand(joint_positions=positions)
        assert cmd.to_bytes() == cmd.to_bytes()

    def test_skip_validation_allows_wrong_joint_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With SKIP_VALIDATION=True, from_bytes uses model_construct and skips validation."""
        monkeypatch.setattr(cmd_module, "SKIP_VALIDATION", True)
        data = msgpack.packb({"joint_positions": [1.0, 2.0]})  # only 2 joints
        cmd = ManipulatorCommand.from_bytes(data)
        # model_construct does not validate, so the truncated list is accepted
        assert len(cmd.joint_positions) == 2

    def test_skip_validation_false_enforces_joint_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With SKIP_VALIDATION=False, from_bytes validates and rejects wrong counts."""
        monkeypatch.setattr(cmd_module, "SKIP_VALIDATION", False)
        data = msgpack.packb({"joint_positions": [1.0, 2.0]})
        with pytest.raises(ValidationError):
            ManipulatorCommand.from_bytes(data)

    def test_from_bytes_wrong_type_for_joint(self) -> None:
        """Non-numeric values in joint_positions should raise ValidationError."""
        data = msgpack.packb({"joint_positions": ["a"] * 10})
        with pytest.raises(ValidationError):
            ManipulatorCommand.from_bytes(data)
