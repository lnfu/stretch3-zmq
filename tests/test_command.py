"""Tests for Command data model serialization and validation."""

import msgpack
import pytest
from pydantic import ValidationError

from stretch3_zmq.core.messages.command import Command


class TestCommand:
    def test_create_valid_command(self) -> None:
        positions = (0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)
        cmd = Command(joint_positions=positions)
        assert cmd.joint_positions == positions

    def test_invalid_joint_count_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 9 joint positions"):
            Command(joint_positions=(0.0, 0.1))

    def test_empty_joints_raises(self) -> None:
        with pytest.raises(ValueError, match="Need 9 joint positions"):
            Command(joint_positions=())

    def test_to_bytes_returns_bytes(self) -> None:
        positions = (0.0,) * 9
        cmd = Command(joint_positions=positions)
        data = cmd.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_from_bytes_roundtrip(self) -> None:
        positions = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
        original = Command(joint_positions=positions)
        data = original.to_bytes()
        restored = Command.from_bytes(data)
        assert restored.joint_positions == original.joint_positions

    def test_from_bytes_invalid_msgpack(self) -> None:
        with pytest.raises((msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException, ValidationError)):
            Command.from_bytes(b"not msgpack")

    def test_from_bytes_missing_fields(self) -> None:
        # Missing joint_positions field
        with pytest.raises(ValidationError):
            Command.from_bytes(msgpack.packb({}))

    def test_msgpack_format(self) -> None:
        """Verify messages are serialized with msgpack."""
        positions = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
        cmd = Command(joint_positions=positions)
        data = cmd.to_bytes()

        # Decode with msgpack and verify structure
        unpacked = msgpack.unpackb(data)
        assert "joint_positions" in unpacked
        assert unpacked["joint_positions"] == list(positions)
        # Timestamp should not be in the serialized data anymore
        assert "timestamp" not in unpacked
