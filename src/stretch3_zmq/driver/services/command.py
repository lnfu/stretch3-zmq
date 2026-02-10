"""Command service: receives robot commands from ZeroMQ and executes them."""

import logging
from typing import NoReturn

import zmq

from stretch3_zmq.core.messages.command import Command
from stretch3_zmq.core.messages.protocol import decode_with_timestamp

from ..config import DriverConfig
from ..control.robot import StretchRobot
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def command_service(config: DriverConfig, robot: StretchRobot) -> NoReturn:
    """
    Command service: Receives robot commands from ZeroMQ and executes them.

    Listens on tcp://*:{ports.command} using SUB socket pattern.
    """
    with zmq_socket(zmq.SUB, f"tcp://*:{config.ports.command}") as socket:
        socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics

        logger.info(f"Command service started. Listening on tcp://*:{config.ports.command}")

        try:
            while True:
                try:
                    parts = socket.recv_multipart()
                    timestamp_ns, payload = decode_with_timestamp(parts)
                    logger.debug(f"[COMMAND] Received at {timestamp_ns}ns, {len(payload)} bytes")

                    command = Command.from_bytes(payload)
                    robot.execute_command(command)
                    logger.info("[COMMAND] Command executed")

                except Exception as e:
                    logger.exception(f"[COMMAND] Error processing command: {e}")

        except KeyboardInterrupt:
            logger.info("[COMMAND] Shutting down...")
