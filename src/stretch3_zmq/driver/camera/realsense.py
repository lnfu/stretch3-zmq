"""Shared Intel RealSense camera implementation."""

import contextlib
import logging

import numpy as np
import pyrealsense2 as rs

from .base import CameraBase

logger = logging.getLogger(__name__)


class RealSenseCamera(CameraBase):
    """Intel RealSense camera with color and depth streams."""

    def __init__(self, name: str, width: int, height: int, fps: int, serial: str | None = None):
        self._name = name
        self._width = width
        self._height = height
        self._fps = fps
        self._serial = serial
        self._pipeline: rs.pipeline | None = None
        self._depth_scale: float | None = None

    @property
    def depth_scale(self) -> float:
        if self._depth_scale is None:
            raise RuntimeError(f"{self._name}: Camera not started")
        return self._depth_scale

    def start(self) -> None:
        """Initialize and start the camera."""
        # Re-enable logger (stretch_body disables it)
        logger.disabled = False

        if self._pipeline is not None:
            logger.warning(f"{self._name}: Already started")
            return

        pipeline = rs.pipeline()
        config = rs.config()

        # Enable device by serial number if specified
        if self._serial:
            config.enable_device(self._serial)

        # Configure color and depth streams
        config.enable_stream(rs.stream.color, self._width, self._height, rs.format.rgb8, self._fps)
        config.enable_stream(rs.stream.depth, self._width, self._height, rs.format.z16, self._fps)

        self._align = rs.align(rs.stream.color)

        try:
            profile = pipeline.start(config)
            depth_sensor = profile.get_device().first_depth_sensor()
            self._depth_scale = depth_sensor.get_depth_scale()  # Unit: meters per unit
            device = profile.get_device()
            device_serial = device.get_info(rs.camera_info.serial_number)
            self._pipeline = pipeline

            logger.info(
                f"{self._name} started: {self._width}x{self._height} @ {self._fps}fps "
                f"(Serial: {device_serial}, Depth Scale (m/unit): {self._depth_scale:.6f})"
            )

            # Drop first few frames to let camera stabilize
            for _ in range(30):
                with contextlib.suppress(Exception):
                    self._pipeline.wait_for_frames(timeout_ms=2000)

        except Exception as e:
            logger.error(f"{self._name}: Failed to start camera: {e}")
            raise RuntimeError(f"Failed to start {self._name}: {e}") from e

    def stop(self) -> None:
        """Stop the camera and release resources."""
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None
            logger.info(f"{self._name} stopped")

    def read(self) -> tuple[bool, np.ndarray | None, np.ndarray | None]:
        """Read color and depth frames from the camera."""
        if self._pipeline is None:
            return False, None, None

        # TODO(lnfu): undistort (Inverse Brown-Conrady, Brown-Conrady, etc.)
        try:
            frames = self._pipeline.wait_for_frames(timeout_ms=1000)
            aligned_frames = self._align.process(frames)
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()

            if not color_frame or not depth_frame:
                return False, None, None

            color_data = np.asanyarray(color_frame.get_data())
            depth_data = np.asanyarray(depth_frame.get_data())
            return True, color_data, depth_data
        except Exception:
            logger.exception(f"{self._name}: Failed to read frames")
            return False, None, None
