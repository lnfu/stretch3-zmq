"""Goto service: blocking base position move via REQ+REP."""

import logging
from typing import NoReturn

import msgpack
import zmq

from stretch3_zmq.core.messages.twist_2d import Twist2D

from ..config import DriverConfig
from ..control.robot import StretchRobot
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def goto_service(config: DriverConfig, robot: StretchRobot) -> NoReturn:
    """
    Goto service: blocking base position move.

    Listens on tcp://*:{ports.goto} using REP socket pattern.
    Request: msgpack-encoded {linear: float, angular: float} (Twist2D fields).
    Reply: "ok" on success, error message string on failure.
    """
    with zmq_socket(zmq.REP, f"tcp://*:{config.ports.goto}") as socket:
        logger.info(f"Goto service started. Listening on tcp://*:{config.ports.goto}")

        while True:
            try:
                data = msgpack.unpackb(socket.recv())
                twist = Twist2D.model_validate(data)
                logger.info(f"[GOTO] linear={twist.linear}, angular={twist.angular}")

                robot.goto(twist)

                logger.info("[GOTO] Motion completed")
                socket.send_string("ok")

            except Exception as e:
                logger.exception(f"[GOTO] Error: {e}")
                socket.send_string(f"error: {e}")
