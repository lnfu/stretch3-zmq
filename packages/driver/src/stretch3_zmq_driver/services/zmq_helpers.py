"""Shared ZeroMQ context manager utilities."""

import contextlib
from collections.abc import Generator

import zmq


@contextlib.contextmanager
def zmq_socket(socket_type: int, address: str) -> Generator[zmq.Socket[bytes], None, None]:
    """Create a bound ZeroMQ socket with automatic cleanup."""
    context = zmq.Context()
    socket = context.socket(socket_type)

    # Set HWM=1 for PUB/SUB sockets to keep only the latest message
    if socket_type == zmq.PUB:
        socket.setsockopt(zmq.SNDHWM, 1)
    elif socket_type == zmq.SUB:
        socket.setsockopt(zmq.RCVHWM, 1)

    socket.bind(address)
    try:
        yield socket
    finally:
        socket.close()
        context.term()


@contextlib.contextmanager
def zmq_socket_pair(
    address_a: str, address_b: str
) -> Generator[tuple[zmq.Socket[bytes], zmq.Socket[bytes]], None, None]:
    """Create two bound PUB sockets sharing a context, with automatic cleanup."""
    context = zmq.Context()
    socket_a = context.socket(zmq.PUB)
    socket_a.setsockopt(zmq.SNDHWM, 1)
    socket_a.bind(address_a)
    socket_b = context.socket(zmq.PUB)
    socket_b.setsockopt(zmq.SNDHWM, 1)
    socket_b.bind(address_b)
    try:
        yield socket_a, socket_b
    finally:
        socket_a.close()
        socket_b.close()
        context.term()
