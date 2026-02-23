"""Command service: receives robot commands from ZeroMQ and executes them."""

import logging
from collections.abc import Callable
from typing import Any, NoReturn

import zmq

from stretch3_zmq_core.messages.command import BaseCommand, ManipulatorCommand
from stretch3_zmq_core.messages.protocol import decode_with_timestamp

from ..config import DriverConfig
from ..control.robot import StretchRobot
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def command_service(config: DriverConfig, robot: StretchRobot) -> NoReturn:
    """
    Command service: Receives robot commands from ZeroMQ and executes them.

    Listens on tcp://*:{ports.command} using SUB socket pattern.
    Message format: [topic, timestamp, payload]
    """
    dispatch: dict[str, tuple[type[Any], Callable[[Any], None]]] = {
        "manipulator": (ManipulatorCommand, robot.execute_manipulator_command),
        "base": (BaseCommand, robot.execute_base_command),
    }

    with zmq_socket(zmq.SUB, f"tcp://*:{config.ports.command}") as socket:
        for topic in dispatch:
            socket.setsockopt_string(zmq.SUBSCRIBE, topic)

        logger.info(f"Command service started. Listening on tcp://*:{config.ports.command}")

        while True:
            try:
                parts = socket.recv_multipart()
                topic = parts[0].decode()

                if topic not in dispatch:
                    logger.warning(f"[COMMAND] Unknown topic: {topic!r}, ignoring")
                    continue

                timestamp_ns, payload = decode_with_timestamp(parts[1:])
                logger.debug(f"[COMMAND] topic={topic!r} at {timestamp_ns}ns, {len(payload)} bytes")

                CommandClass, handler = dispatch[topic]
                command = CommandClass.from_bytes(payload)
                handler(command)
                logger.info(f"[COMMAND] {topic!r} command executed")

            except Exception as e:
                logger.exception(f"[COMMAND] Error processing command: {e}")
