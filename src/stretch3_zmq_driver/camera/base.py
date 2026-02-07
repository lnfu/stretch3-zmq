"""Abstract base class for camera implementations."""

from abc import ABC, abstractmethod

import numpy as np


class CameraBase(ABC):
    """
    Abstract base class for all camera implementations.

    Provides a unified interface for different camera types (RealSense, UVC, etc.).
    """

    @abstractmethod
    def start(self) -> None:
        """
        Initialize and start the camera.

        Raises:
            RuntimeError: If camera cannot be initialized.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the camera and release resources."""
        pass

    @abstractmethod
    def read_color(self) -> tuple[bool, np.ndarray | None]:
        """
        Read a color frame from the camera.

        Returns:
            Tuple of (success, frame). Frame is BGR format numpy array if success,
            None otherwise.
        """
        pass

    def read_depth(self) -> tuple[bool, np.ndarray | None]:
        """
        Read a depth frame from the camera.

        Returns:
            Tuple of (success, frame). Frame is uint16 depth array if success,
            None otherwise. Returns (False, None) if camera doesn't support depth.
        """
        return False, None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
