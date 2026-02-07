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


def main() -> None:
    parser = argparse.ArgumentParser(description="Stretch3-ZMQ Driver")
    parser.add_argument("--config", type=str, help="Path to config.yaml")
    args = parser.parse_args()

    # Load configuration
    config = DriverConfig.from_yaml(args.config)

    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

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

    # TTS/ASR services
    threads.append(
        threading.Thread(
            target=speak_service,
            name="SpeakService",
            daemon=True,
            args=(config,),
        )
    )
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
    logger.info(f"  - Speak service: tcp://*:{config.ports.tts} (PULL)")
    logger.info(f"  - Listen service: tcp://*:{config.ports.asr} (REP)")
    if config.arducam.enabled:
        logger.info(f"  - Arducam service: tcp://*:{config.ports.arducam} (PUB)")
    if config.d435if.enabled:
        logger.info(
            f"  - D435i service: tcp://*:{config.ports.d435if_color}, "
            f"{config.ports.d435if_depth} (PUB)"
        )
    if config.d405.enabled:
        logger.info(
            f"  - D405 service: tcp://*:{config.ports.d405_color}, {config.ports.d405_depth} (PUB)"
        )

    try:
        # Keep main thread alive
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Stretch3-ZMQ Driver...")


if __name__ == "__main__":
    main()
