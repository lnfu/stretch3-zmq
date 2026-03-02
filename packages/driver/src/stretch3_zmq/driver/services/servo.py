"""Servo service: end-effector Cartesian control via SUB socket."""

import logging
from typing import NoReturn

import zmq

from stretch3_zmq.core.messages.protocol import decode_with_timestamp
from stretch3_zmq.core.messages.servo import ServoCommand

from ..config import DriverConfig
from ..control.robot import StretchRobot
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)

_TOPIC = "servo"


def servo_service(config: DriverConfig, robot: StretchRobot) -> NoReturn:
    """
    Servo service: receive relative EE pose + absolute gripper, execute via IK.

    Listens on tcp://*:{ports.servo} using SUB socket pattern.
    Topic: "servo"
    Message format: [topic, timestamp, payload] — msgpack-encoded ServoCommand.
    Failures (including IK errors) are logged and silently ignored.
    """
    with zmq_socket(zmq.SUB, f"tcp://*:{config.ports.servo}") as socket:
        socket.setsockopt_string(zmq.SUBSCRIBE, _TOPIC)
        logger.info(f"Servo service started. Listening on tcp://*:{config.ports.servo}")

        while True:
            try:
                parts = socket.recv_multipart()
                topic = parts[0].decode()

                if topic != _TOPIC:
                    logger.warning(f"[SERVO] Unknown topic: {topic!r}, ignoring")
                    continue

                _timestamp_ns, payload = decode_with_timestamp(parts[1:])
                command = ServoCommand.from_bytes(payload)
                logger.debug(f"[SERVO] ee_pose={command.ee_pose}, gripper={command.gripper}")

                robot.servo(command)
                logger.info("[SERVO] Command executed")

            except Exception as e:
                logger.warning(f"[SERVO] Ignored error: {e}")
