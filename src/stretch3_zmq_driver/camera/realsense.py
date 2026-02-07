"""Shared Intel RealSense camera implementation."""

import logging

import numpy as np
import pyrealsense2 as rs

from .base import CameraBase

logger = logging.getLogger(__name__)


class RealSenseCamera(CameraBase):
    """Intel RealSense camera with color and depth streams."""

    def __init__(self, name: str, width: int, height: int, fps: int):
        self._name = name
        self._width = width
        self._height = height
        self._fps = fps
        self._pipeline: rs.pipeline | None = None
        self._config: rs.config | None = None

    def start(self) -> None:
        """Initialize and start the camera."""
        # Re-enable logger (stretch_body disables it)
        logger.disabled = False

        self._pipeline = rs.pipeline()
        self._config = rs.config()

        # Configure color and depth streams
        self._config.enable_stream(
            rs.stream.color, self._width, self._height, rs.format.rgb8, self._fps
        )
        self._config.enable_stream(
            rs.stream.depth, self._width, self._height, rs.format.z16, self._fps
        )

        try:
            self._pipeline.start(self._config)
            logger.info(f"{self._name} started: {self._width}x{self._height} @ {self._fps}fps")
        except Exception as e:
            self._pipeline = None
            raise RuntimeError(f"Failed to start {self._name}: {e}") from e

    def stop(self) -> None:
        """Stop the camera and release resources."""
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None
            logger.info(f"{self._name} stopped")

    def read_color(self) -> tuple[bool, np.ndarray | None]:
        """Read a color frame from the camera."""
        if self._pipeline is None:
            return False, None

        try:
            frames = self._pipeline.wait_for_frames(timeout_ms=1000)
            color_frame = frames.get_color_frame()

            if not color_frame:
                return False, None

            return True, np.asanyarray(color_frame.get_data())
        except Exception:
            logger.exception(f"{self._name}: failed to read color frame")
            return False, None

    def read_depth(self) -> tuple[bool, np.ndarray | None]:
        """Read a depth frame from the camera."""
        if self._pipeline is None:
            return False, None

        try:
            frames = self._pipeline.wait_for_frames(timeout_ms=1000)
            depth_frame = frames.get_depth_frame()

            if not depth_frame:
                return False, None

            return True, np.asanyarray(depth_frame.get_data())
        except Exception:
            logger.exception(f"{self._name}: failed to read depth frame")
            return False, None
