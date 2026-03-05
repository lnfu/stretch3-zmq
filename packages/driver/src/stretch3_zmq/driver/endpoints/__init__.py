"""Endpoint functions for the Stretch3-ZMQ Driver."""

from .camera import arducam_endpoint, d405_endpoint, d435if_endpoint
from .command import command_endpoint
from .goto import goto_endpoint
from .listen import listen_endpoint
from .speak import speak_endpoint
from .status import status_endpoint

__all__ = [
    "arducam_endpoint",
    "command_endpoint",
    "d405_endpoint",
    "d435if_endpoint",
    "goto_endpoint",
    "listen_endpoint",
    "speak_endpoint",
    "status_endpoint",
]
