"""Status service: publishes robot status to ZeroMQ."""

import logging
import time
from typing import NoReturn

import zmq

from stretch3_zmq_core.messages.protocol import encode_with_timestamp

from ..config import DriverConfig
from ..control.robot import StretchRobot
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def status_service(config: DriverConfig, robot: StretchRobot) -> NoReturn:
    """
    Status service: Publishes robot status to ZeroMQ.

    Publishes on tcp://*:{ports.status} using PUB socket pattern.
    """
    status_interval = 1.0 / config.service.status_rate_hz

    with zmq_socket(zmq.PUB, f"tcp://*:{config.ports.status}") as socket:
        logger.info(f"Status service started. Publishing on tcp://*:{config.ports.status}")

        while True:
            loop_start = time.time()

            try:
                status = robot.get_status()
                parts = encode_with_timestamp(status.to_bytes())
                socket.send_multipart(parts)
            except Exception as e:
                logger.exception(f"[STATUS] Error getting/publishing status: {e}")

            # Sleep to maintain rate
            elapsed = time.time() - loop_start
            sleep_time = status_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
