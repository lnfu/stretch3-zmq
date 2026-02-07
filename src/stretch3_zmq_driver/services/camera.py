"""Camera services: publish frames from Arducam and RealSense cameras to ZeroMQ."""

import logging
from typing import NoReturn

import zmq

from ..camera.arducam import ArducamCamera
from ..camera.realsense import RealSenseCamera
from ..config import DriverConfig
from .zmq_helpers import zmq_socket, zmq_socket_pair

logger = logging.getLogger(__name__)


def arducam_service(config: DriverConfig) -> NoReturn:
    """
    Arducam service: Publishes camera frames to ZeroMQ.

    Publishes on tcp://*:{ports.arducam} using PUB socket pattern.
    """
    camera = ArducamCamera(
        device=config.arducam.device,
        width=config.arducam.width,
        height=config.arducam.height,
        fps=config.arducam.fps,
    )
    camera.start()

    with zmq_socket(zmq.PUB, f"tcp://*:{config.ports.arducam}") as socket:
        logger.info(f"Arducam service started. Publishing on tcp://*:{config.ports.arducam}")

        try:
            while True:
                success, frame = camera.read_color()
                if success and frame is not None:
                    socket.send(frame.tobytes())
        except KeyboardInterrupt:
            logger.info("[ARDUCAM] Shutting down...")
        finally:
            camera.stop()


def _realsense_service(
    camera: RealSenseCamera, color_port: int, depth_port: int, name: str
) -> NoReturn:
    """
    RealSense service: Publishes color and depth frames to ZeroMQ.

    Publishes color on tcp://*:{color_port} and depth on tcp://*:{depth_port}.
    """
    camera.start()

    with zmq_socket_pair(f"tcp://*:{color_port}", f"tcp://*:{depth_port}") as (
        color_socket,
        depth_socket,
    ):
        logger.info(
            f"{name} service started. Color: tcp://*:{color_port}, Depth: tcp://*:{depth_port}"
        )

        try:
            while True:
                success, color_frame = camera.read_color()
                if success and color_frame is not None:
                    color_socket.send(color_frame.tobytes())

                success, depth_frame = camera.read_depth()
                if success and depth_frame is not None:
                    depth_socket.send(depth_frame.tobytes())
        except KeyboardInterrupt:
            logger.info(f"[{name}] Shutting down...")
        finally:
            camera.stop()


def d435if_service(config: DriverConfig) -> NoReturn:
    """D435i service: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D435i",
        width=config.d435if.width,
        height=config.d435if.height,
        fps=config.d435if.fps,
    )
    _realsense_service(camera, config.ports.d435if_color, config.ports.d435if_depth, "D435i")


def d405_service(config: DriverConfig) -> NoReturn:
    """D405 service: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D405",
        width=config.d405.width,
        height=config.d405.height,
        fps=config.d405.fps,
    )
    _realsense_service(camera, config.ports.d405_color, config.ports.d405_depth, "D405")
