"""Camera endpoints: publish frames from Arducam and RealSense cameras to ZeroMQ."""

import logging
import sys
from typing import NoReturn

import blosc2
import numpy as np
import zmq

from stretch3_zmq.core.messages.protocol import encode_with_timestamp

from ..camera.arducam import ArducamCamera
from ..camera.realsense import RealSenseCamera
from ..config import DriverConfig
from .zmq_helpers import zmq_socket

logger = logging.getLogger(__name__)


def _compress(data: np.ndarray) -> bytes:
    """Compress a numpy array with blosc2 + LZ4."""
    return bytes(blosc2.compress(data.tobytes(), typesize=data.itemsize, codec=blosc2.Codec.LZ4))


def _setup_camera_logger() -> None:
    """
    Set up camera endpoint logger.

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


def arducam_endpoint(config: DriverConfig) -> NoReturn:
    """
    Arducam endpoint: Publishes camera frames to ZeroMQ.

    Publishes on tcp://*:{ports.arducam} using PUB socket pattern.
    """
    try:
        _setup_camera_logger()

        logger.info(
            f"Arducam starting: {config.cameras.arducam.device} @ "
            f"{config.cameras.arducam.width}x{config.cameras.arducam.height} "
            "{config.cameras.arducam.fps}fps"
        )

        camera = ArducamCamera(
            device=config.cameras.arducam.device,
            width=config.cameras.arducam.width,
            height=config.cameras.arducam.height,
            fps=config.cameras.arducam.fps,
        )
        camera.start()

        with zmq_socket(zmq.PUB, f"tcp://*:{config.ports.arducam}") as socket:
            logger.info(f"Arducam endpoint started. Publishing on tcp://*:{config.ports.arducam}")

            try:
                while True:
                    success, frame, _ = camera.read()
                    if success and frame is not None:
                        payload = (
                            _compress(frame)
                            if config.cameras.arducam.compressed
                            else frame.tobytes()
                        )
                        socket.send_multipart(encode_with_timestamp(payload))
            finally:
                camera.stop()
    except Exception as e:
        logger.error(f"FATAL ERROR in arducam_endpoint: {e}", exc_info=True)
        raise


def _realsense_endpoint(
    camera: RealSenseCamera, port: int, name: str, compressed: bool
) -> NoReturn:
    """
    RealSense endpoint: Publishes color and depth frames to ZeroMQ.

    Publishes on tcp://*:{port} using topic-prefixed multipart messages:
      [b"rgb",   timestamp, payload] - color frame
      [b"depth", timestamp, payload] - depth frame
    """
    try:
        _setup_camera_logger()

        logger.info(f"{name} starting...")
        camera.start()

        with zmq_socket(zmq.PUB, f"tcp://*:{port}") as socket:
            logger.info(f"{name} endpoint started. Publishing on tcp://*:{port}")

            try:
                while True:
                    success, color_frame, depth_frame = camera.read()
                    if success and color_frame is not None:
                        payload = _compress(color_frame) if compressed else color_frame.tobytes()
                        socket.send_multipart([b"rgb", *encode_with_timestamp(payload)])
                    if success and depth_frame is not None:
                        payload = _compress(depth_frame) if compressed else depth_frame.tobytes()
                        socket.send_multipart([b"depth", *encode_with_timestamp(payload)])
            finally:
                camera.stop()
    except Exception as e:
        logger.error(f"FATAL ERROR in {name} endpoint: {e}", exc_info=True)
        raise


def d435if_endpoint(config: DriverConfig) -> NoReturn:
    """D435i endpoint: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D435i",
        width=config.cameras.d435if.width,
        height=config.cameras.d435if.height,
        fps=config.cameras.d435if.fps,
        serial=config.cameras.d435if.serial,
    )
    _realsense_endpoint(camera, config.ports.d435if, "D435i", config.cameras.d435if.compressed)


def d405_endpoint(config: DriverConfig) -> NoReturn:
    """D405 endpoint: Publishes color and depth frames to ZeroMQ."""
    camera = RealSenseCamera(
        name="D405",
        width=config.cameras.d405.width,
        height=config.cameras.d405.height,
        fps=config.cameras.d405.fps,
        serial=config.cameras.d405.serial,
    )
    _realsense_endpoint(camera, config.ports.d405, "D405", config.cameras.d405.compressed)
