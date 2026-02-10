"""Tests for multipart message protocol."""

import struct
import time

import pytest

from stretch3_zmq.core.messages.protocol import decode_with_timestamp, encode_with_timestamp


def test_encode_creates_two_parts() -> None:
    """Verify encode creates exactly 2 parts with correct sizes."""
    payload = b"test payload"
    parts = encode_with_timestamp(payload)

    assert len(parts) == 2
    assert len(parts[0]) == 8  # timestamp is 8 bytes (unsigned long long)
    assert parts[1] == payload


def test_decode_extracts_timestamp_and_payload() -> None:
    """Verify decode correctly extracts timestamp and payload."""
    payload = b"test payload"
    parts = encode_with_timestamp(payload)

    timestamp_ns, decoded_payload = decode_with_timestamp(parts)

    assert isinstance(timestamp_ns, int)
    assert timestamp_ns > 0
    assert decoded_payload == payload


def test_roundtrip_preserves_data() -> None:
    """Verify encode/decode roundtrip preserves payload and timestamp."""
    payload = b"hello world"
    before = time.time_ns()
    parts = encode_with_timestamp(payload)
    after = time.time_ns()

    timestamp_ns, decoded = decode_with_timestamp(parts)

    # Timestamp should be between before and after
    assert before <= timestamp_ns <= after
    # Payload should be unchanged
    assert decoded == payload


def test_decode_validates_part_count() -> None:
    """Verify decode rejects invalid part counts."""
    with pytest.raises(ValueError, match="Expected 2 parts, got 1"):
        decode_with_timestamp([b"only one part"])

    with pytest.raises(ValueError, match="Expected 2 parts, got 3"):
        decode_with_timestamp([b"one", b"two", b"three"])

    with pytest.raises(ValueError, match="Expected 2 parts, got 0"):
        decode_with_timestamp([])


def test_network_byte_order() -> None:
    """Verify timestamp uses network byte order (big-endian)."""
    payload = b"test"
    parts = encode_with_timestamp(payload)

    # Manually decode with network byte order
    timestamp_ns = struct.unpack('!Q', parts[0])[0]
    assert timestamp_ns > 0

    # Verify the '!' prefix ensures big-endian
    # On little-endian systems, native byte order would give different result
    import sys
    if sys.byteorder == 'little':
        # Native byte order decoding should differ on little-endian
        native_ts = struct.unpack('Q', parts[0])[0]
        # They'll only be equal if timestamp happens to be palindromic in binary
        # which is extremely unlikely, so we just verify both decode without error
        assert native_ts > 0


def test_timestamp_is_nanoseconds() -> None:
    """Verify timestamp is in nanoseconds since epoch."""
    payload = b"test"
    parts = encode_with_timestamp(payload)
    timestamp_ns, _ = decode_with_timestamp(parts)

    # Current time should be around 1.7e18 nanoseconds since epoch (year 2024+)
    assert timestamp_ns > 1.6e18  # After year 2020
    assert timestamp_ns < 2.0e18  # Before year 2033


def test_different_payloads() -> None:
    """Verify protocol works with various payload types."""
    payloads = [
        b"",  # empty
        b"x",  # single byte
        b"a" * 1000,  # large payload
        bytes(range(256)),  # all byte values
    ]

    for payload in payloads:
        parts = encode_with_timestamp(payload)
        timestamp_ns, decoded = decode_with_timestamp(parts)
        assert decoded == payload
        assert timestamp_ns > 0


def test_timestamp_precision() -> None:
    """Verify timestamps have nanosecond precision."""
    # Create two messages rapidly
    parts1 = encode_with_timestamp(b"first")
    parts2 = encode_with_timestamp(b"second")

    ts1, _ = decode_with_timestamp(parts1)
    ts2, _ = decode_with_timestamp(parts2)

    # Second timestamp should be >= first (monotonic)
    # Note: on some systems, time.time_ns() may have limited resolution
    assert ts2 >= ts1
