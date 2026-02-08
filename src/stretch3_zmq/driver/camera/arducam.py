"""Arducam UVC camera implementation."""

import logging

import cv2
import numpy as np

from .base import CameraBase

logger = logging.getLogger(__name__)


class ArducamCamera(CameraBase):
    """Arducam UVC camera using OpenCV VideoCapture."""

    def __init__(
        self,
        device: str = "/dev/video4",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ):
        self._device = device
        self._width = width
        self._height = height
        self._fps = fps
        self._cap: cv2.VideoCapture | None = None

    def start(self) -> None:
        """Initialize and start the camera."""
        # Re-enable logger (stretch_body disables it)
        logger.disabled = False

        self._cap = cv2.VideoCapture(self._device)

        if not self._cap.isOpened():
            logger.error(f"Failed to open Arducam at {self._device}")
            raise RuntimeError(f"Failed to open Arducam at {self._device}")

        # Set MJPG format for full FPS
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, self._fps)

        logger.info(
            f"Arducam started: {self._device} @ {self._width}x{self._height} {self._fps}fps"
        )
        actual_w = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logger.info(f"Actual resolution: {actual_w}x{actual_h}")

    def stop(self) -> None:
        """Stop the camera and release resources."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Arducam stopped")

    def read_color(self) -> tuple[bool, np.ndarray | None]:
        """Read a color frame from the camera."""
        if self._cap is None:
            return False, None

        ret, frame = self._cap.read()
        if not ret:
            return False, None

        return True, frame

    # read_depth() inherited from base - returns (False, None)
