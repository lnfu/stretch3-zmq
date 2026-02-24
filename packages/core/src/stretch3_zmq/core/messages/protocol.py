"""ZeroMQ multipart message protocol with timestamps.

This module provides utilities for encoding and decoding ZeroMQ multipart messages
with nanosecond-precision timestamps. The protocol uses a two-part format:
1. Timestamp frame: 8 bytes, unsigned long long in network byte order (big-endian)
2. Payload frame: arbitrary bytes (serialized message or raw data)

The timestamp represents nanoseconds since epoch (1970-01-01 00:00:00 UTC) and is
captured at message transmission time.
"""

import struct
import time


def encode_with_timestamp(payload: bytes) -> list[bytes]:
    """Encode payload with timestamp for ZeroMQ send_multipart.

    Args:
        payload: Message payload as bytes (msgpack data, raw binary, etc.)

    Returns:
        List of two byte frames: [timestamp_bytes, payload_bytes]
        Timestamp is 8 bytes in network byte order (big-endian).

    Example:
        >>> msg = b"hello"
        >>> parts = encode_with_timestamp(msg)
        >>> len(parts)
        2
        >>> len(parts[0])  # timestamp is 8 bytes
        8
    """
    timestamp_ns = time.time_ns()
    timestamp_bytes = struct.pack("!Q", timestamp_ns)
    return [timestamp_bytes, payload]


def decode_with_timestamp(parts: list[bytes]) -> tuple[int, bytes]:
    """Decode ZeroMQ multipart message into timestamp and payload.

    Args:
        parts: List of message parts from recv_multipart()

    Returns:
        Tuple of (timestamp_ns, payload) where timestamp_ns is an integer
        representing nanoseconds since epoch.

    Raises:
        ValueError: If parts does not contain exactly 2 frames
        struct.error: If timestamp frame is not 8 bytes

    Example:
        >>> parts = [struct.pack('!Q', 1234567890000000000), b"hello"]
        >>> timestamp_ns, payload = decode_with_timestamp(parts)
        >>> timestamp_ns
        1234567890000000000
        >>> payload
        b'hello'
    """
    if len(parts) != 2:
        raise ValueError(f"Expected 2 parts, got {len(parts)}")

    timestamp_ns = struct.unpack("!Q", parts[0])[0]
    payload = parts[1]
    return timestamp_ns, payload
