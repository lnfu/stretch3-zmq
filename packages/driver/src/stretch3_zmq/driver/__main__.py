"""Main entry point that orchestrates all Stretch3-ZMQ Driver services."""

import argparse
import logging
import threading

from dotenv import load_dotenv

from .config import DriverConfig
from .services import (
    arducam_service,
    command_service,
    d405_service,
    d435if_service,
    listen_service,
    speak_service,
    status_service,
)

logger = logging.getLogger(__name__)


def thread_exception_hook(args: threading.ExceptHookArgs) -> None:
    """Hook to catch uncaught exceptions in threads."""
    thread_name = args.thread.name if args.thread is not None else "<unknown>"
    logger.error(
        f"Uncaught exception in thread {thread_name}: {args.exc_type.__name__}: {args.exc_value}",
        exc_info=args.exc_value,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stretch3-ZMQ Driver")
    parser.add_argument("--config", type=str, help="Path to config.yaml")
    args = parser.parse_args()

    # Load configuration
    config = DriverConfig.from_yaml(args.config)

    load_dotenv()

    # Set up thread exception hook
    threading.excepthook = thread_exception_hook

    logger.info("Starting Stretch3-ZMQ Driver...")

    threads: list[threading.Thread] = []

    # Robot services
    logger.info("Initializing robot in main thread...")
    from .control.robot import StretchRobot

    try:
        robot_instance = StretchRobot()
    except Exception as e:
        logger.error(f"Failed to initialize robot: {e}")
        return

    # Reconfigure logging after stretch_body initialization
    # stretch_body modifies the root logger, so we reconfigure it
    root_logger = logging.getLogger()

    # Remove all handlers that stretch_body added
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our own clean handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if config.debug else logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] [%(name)s]: %(message)s")
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG if config.debug else logging.INFO)

    logger.info("Logging reconfigured after robot initialization")

    threads.append(
        threading.Thread(
            target=status_service,
            name="StatusService",
            daemon=True,
            args=(config, robot_instance),
        )
    )
    threads.append(
        threading.Thread(
            target=command_service,
            name="CommandService",
            daemon=True,
            args=(config, robot_instance),
        )
    )

    # TTS/ASR services (only if enabled)
    if config.tts.enabled:
        threads.append(
            threading.Thread(
                target=speak_service,
                name="SpeakService",
                daemon=True,
                args=(config,),
            )
        )

    if config.asr.enabled:
        threads.append(
            threading.Thread(
                target=listen_service,
                name="ListenService",
                daemon=True,
                args=(config,),
            )
        )

    # Camera services (only if enabled)
    if config.arducam.enabled:
        threads.append(
            threading.Thread(
                target=arducam_service,
                name="ArducamService",
                daemon=True,
                args=(config,),
            )
        )

    if config.d435if.enabled:
        threads.append(
            threading.Thread(
                target=d435if_service,
                name="D435iService",
                daemon=True,
                args=(config,),
            )
        )

    if config.d405.enabled:
        threads.append(
            threading.Thread(
                target=d405_service,
                name="D405Service",
                daemon=True,
                args=(config,),
            )
        )

    # Start all threads
    for thread in threads:
        thread.start()

    logger.info("All services started successfully")

    logger.info(f"  - Status service: tcp://*:{config.ports.status} (PUB)")
    logger.info(f"  - Command service: tcp://*:{config.ports.command} (SUB)")
    if config.tts.enabled:
        logger.info(f"  - Speak service: tcp://*:{config.ports.tts} (PULL)")
    if config.asr.enabled:
        logger.info(f"  - Listen service: tcp://*:{config.ports.asr} (REP)")
    if config.arducam.enabled:
        logger.info(f"  - Arducam service: tcp://*:{config.ports.arducam} (PUB)")
    if config.d435if.enabled:
        logger.info(f"  - D435i service: tcp://*:{config.ports.d435if} (PUB, topics: rgb/depth)")
    if config.d405.enabled:
        logger.info(f"  - D405 service: tcp://*:{config.ports.d405} (PUB, topics: rgb/depth)")

    try:
        # Keep main thread alive
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Stretch3-ZMQ Driver...")


if __name__ == "__main__":
    main()
