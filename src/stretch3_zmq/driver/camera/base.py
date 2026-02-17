"""Abstract base class for camera implementations."""

from abc import ABC, abstractmethod
from typing import Self

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
    def read(self) -> tuple[bool, np.ndarray | None, np.ndarray | None]:
        """
        Read color and depth frames from the camera.

        Returns:
            Tuple of (success, color, depth). Color is an RGB/BGR numpy array,
            depth is a uint16 depth array. Cameras without depth support return
            None for the depth component.
        """
        pass

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        self.stop()
