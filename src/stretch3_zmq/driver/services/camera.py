"""Camera services: publish frames from Arducam and RealSense cameras to ZeroMQ."""

import logging
import sys
from typing import NoReturn

import zmq

from stretch3_zmq.core.messages.protocol import encode_with_timestamp

from ..camera.arducam import ArducamCamera
from ..camera.realsense import RealSenseCamera
from ..config import DriverConfig
from .zmq_helpers import zmq_socket, zmq_socket_pair

logger = logging.getLogger(__name__)


def _setup_camera_logger():
    """
    Set up camera service logger.

    WORKAROUND: stretch_body disables loggers, so we need to:
    1. Re-enable the logger
    2. Add a handler since propagation doesn't work in daemon threads
    """
    # Critical: Re-enable logger (stretch_body disables it)
    logger.disabled = False

    # Only add handler if none exists to avoid duplicates
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(levelname)s] [%(name)s]: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False


def arducam_service(config: DriverConfig) -> NoReturn:
    """
    Arducam service: Publishes camera frames to ZeroMQ.

    Publishes on tcp://*:{ports.arducam} using PUB socket pattern.
    """
    try:
        _setup_camera_logger()

        logger.info(
            f"Arducam starting: {config.arducam.device} @ "
            f"{config.arducam.width}x{config.arducam.height} {config.arducam.fps}fps"
        )

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
                        parts = encode_with_timestamp(frame.tobytes())
                        socket.send_multipart(parts)
            except KeyboardInterrupt:
                logger.info("Arducam shutting down...")
            finally:
                camera.stop()
    except Exception as e:
        logger.error(f"FATAL ERROR in arducam_service: {e}", exc_info=True)
        raise


def _realsense_service(
    camera: RealSenseCamera, color_port: int, depth_port: int, name: str
) -> NoReturn:
    """
    RealSense service: Publishes color and depth frames to ZeroMQ.

    Publishes color on tcp://*:{color_port} and depth on tcp://*:{depth_port}.
    """
    try:
        _setup_camera_logger()

        logger.info(f"{name} starting...")
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
                    success, color_frame, depth_frame = camera.read_frames()
                    if success and color_frame is not None:
                        parts = encode_with_timestamp(color_frame.tobytes())
                        color_socket.send_multipart(parts)
                    if success and depth_frame is not None:
                        parts = encode_with_timestamp(depth_frame.tobytes())
                        depth_socket.send_multipart(parts)
            except KeyboardInterrupt:
                logger.info(f"{name} shutting down...")
            finally:
                camera.stop()
    except Exception as e:
        logger.error(f"FATAL ERROR in {name} service: {e}", exc_info=True)
        raise


def d435if_service(config: DriverConfig) -> NoReturn:
    """D435i service: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D435i",
        width=config.d435if.width,
        height=config.d435if.height,
        fps=config.d435if.fps,
        serial=config.d435if.serial,
    )
    _realsense_service(camera, config.ports.d435if_color, config.ports.d435if_depth, "D435i")


def d405_service(config: DriverConfig) -> NoReturn:
    """D405 service: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D405",
        width=config.d405.width,
        height=config.d405.height,
        fps=config.d405.fps,
        serial=config.d405.serial,
    )
    _realsense_service(camera, config.ports.d405_color, config.ports.d405_depth, "D405")
