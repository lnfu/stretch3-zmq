"""Shared ZeroMQ context manager utilities."""

import contextlib
from collections.abc import Generator

import zmq


@contextlib.contextmanager
def zmq_socket(socket_type: int, address: str) -> Generator[zmq.Socket, None, None]:
    """Create a bound ZeroMQ socket with automatic cleanup."""
    context = zmq.Context()
    socket = context.socket(socket_type)
    socket.bind(address)
    try:
        yield socket
    finally:
        socket.close()
        context.term()


@contextlib.contextmanager
def zmq_socket_pair(
    address_a: str, address_b: str
) -> Generator[tuple[zmq.Socket, zmq.Socket], None, None]:
    """Create two bound PUB sockets sharing a context, with automatic cleanup."""
    context = zmq.Context()
    socket_a = context.socket(zmq.PUB)
    socket_a.bind(address_a)
    socket_b = context.socket(zmq.PUB)
    socket_b.bind(address_b)
    try:
        yield socket_a, socket_b
    finally:
        socket_a.close()
        socket_b.close()
        context.term()
