"""Tests for ZeroMQ socket context managers in zmq_helpers.

stretch_body initialises fleet configuration at class-definition time
(not at instantiation), so the entire driver.services package fails to
import when HELLO_FLEET_PATH is absent.  We stub out stretch_body in
sys.modules before the import to make these tests runnable on any machine.
"""

import sys
from unittest.mock import MagicMock

# Stub stretch_body before driver package is imported so the package
# __init__.py (which imports command_service -> StretchRobot) can load.
for _mod in ("stretch_body", "stretch_body.robot"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest  # noqa: E402
import zmq  # noqa: E402

from stretch3_zmq_driver.services.zmq_helpers import zmq_socket, zmq_socket_pair  # noqa: E402

# Use ports in a high range unlikely to conflict with running services.
# Each test binds and immediately releases, so sequential reuse is safe.
_BASE_PORT = 19500


class TestZmqSocket:
    def test_creates_pub_socket(self) -> None:
        with zmq_socket(zmq.PUB, f"tcp://127.0.0.1:{_BASE_PORT}") as socket:
            assert socket is not None
            assert socket.type == zmq.PUB

    def test_creates_sub_socket(self) -> None:
        with zmq_socket(zmq.SUB, f"tcp://127.0.0.1:{_BASE_PORT + 1}") as socket:
            assert socket is not None
            assert socket.type == zmq.SUB

    def test_pub_socket_sndhwm_set_to_one(self) -> None:
        with zmq_socket(zmq.PUB, f"tcp://127.0.0.1:{_BASE_PORT + 2}") as socket:
            assert socket.getsockopt(zmq.SNDHWM) == 1

    def test_sub_socket_rcvhwm_set_to_one(self) -> None:
        with zmq_socket(zmq.SUB, f"tcp://127.0.0.1:{_BASE_PORT + 3}") as socket:
            assert socket.getsockopt(zmq.RCVHWM) == 1

    def test_non_pub_sub_socket_has_no_hwm_override(self) -> None:
        """PUSH socket should use ZMQ's default HWM (not forced to 1)."""
        default_hwm = zmq.Context().socket(zmq.PUSH).getsockopt(zmq.SNDHWM)
        with zmq_socket(zmq.PUSH, f"tcp://127.0.0.1:{_BASE_PORT + 4}") as socket:
            # The helper only overrides HWM for PUB/SUB, not PUSH
            assert socket.getsockopt(zmq.SNDHWM) == default_hwm

    def test_socket_closed_after_context_exits(self) -> None:
        with zmq_socket(zmq.PUB, f"tcp://127.0.0.1:{_BASE_PORT + 5}") as socket:
            pass
        assert socket.closed

    def test_socket_closed_on_exception(self) -> None:
        socket_ref = None
        with (
            pytest.raises(RuntimeError),
            zmq_socket(zmq.PUB, f"tcp://127.0.0.1:{_BASE_PORT + 6}") as socket,
        ):
            socket_ref = socket
            raise RuntimeError("intentional error")
        assert socket_ref is not None
        assert socket_ref.closed

    def test_yields_bound_socket(self) -> None:
        """The socket should already be bound when yielded."""
        with zmq_socket(zmq.PUB, f"tcp://127.0.0.1:{_BASE_PORT + 7}") as socket:
            # A bound socket will have a non-empty endpoint
            endpoints = socket.getsockopt_string(zmq.LAST_ENDPOINT)
            assert str(_BASE_PORT + 7) in endpoints


class TestZmqSocketPair:
    def test_creates_two_pub_sockets(self) -> None:
        with zmq_socket_pair(
            f"tcp://127.0.0.1:{_BASE_PORT + 10}",
            f"tcp://127.0.0.1:{_BASE_PORT + 11}",
        ) as (a, b):
            assert a is not None
            assert b is not None
            assert a.type == zmq.PUB
            assert b.type == zmq.PUB

    def test_both_sockets_have_sndhwm_one(self) -> None:
        with zmq_socket_pair(
            f"tcp://127.0.0.1:{_BASE_PORT + 12}",
            f"tcp://127.0.0.1:{_BASE_PORT + 13}",
        ) as (a, b):
            assert a.getsockopt(zmq.SNDHWM) == 1
            assert b.getsockopt(zmq.SNDHWM) == 1

    def test_both_sockets_closed_after_context(self) -> None:
        with zmq_socket_pair(
            f"tcp://127.0.0.1:{_BASE_PORT + 14}",
            f"tcp://127.0.0.1:{_BASE_PORT + 15}",
        ) as (a, b):
            pass
        assert a.closed
        assert b.closed

    def test_both_sockets_closed_on_exception(self) -> None:
        sock_a = None
        sock_b = None
        with (
            pytest.raises(ValueError),
            zmq_socket_pair(
                f"tcp://127.0.0.1:{_BASE_PORT + 16}",
                f"tcp://127.0.0.1:{_BASE_PORT + 17}",
            ) as (a, b),
        ):
            sock_a, sock_b = a, b
            raise ValueError("intentional error")
        assert sock_a is not None and sock_a.closed
        assert sock_b is not None and sock_b.closed

    def test_sockets_are_distinct(self) -> None:
        """The two sockets must be different objects."""
        with zmq_socket_pair(
            f"tcp://127.0.0.1:{_BASE_PORT + 18}",
            f"tcp://127.0.0.1:{_BASE_PORT + 19}",
        ) as (a, b):
            assert a is not b

    def test_each_socket_bound_to_different_port(self) -> None:
        port_a = _BASE_PORT + 20
        port_b = _BASE_PORT + 21
        with zmq_socket_pair(
            f"tcp://127.0.0.1:{port_a}",
            f"tcp://127.0.0.1:{port_b}",
        ) as (a, b):
            ep_a = a.getsockopt_string(zmq.LAST_ENDPOINT)
            ep_b = b.getsockopt_string(zmq.LAST_ENDPOINT)
            assert str(port_a) in ep_a
            assert str(port_b) in ep_b
            assert ep_a != ep_b
