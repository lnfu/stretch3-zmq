"""Interactive ZMQ client for testing Stretch3-ZMQ Driver services."""

import argparse

import zmq

from stretch3_zmq_core.messages.command import Command
from stretch3_zmq_core.messages.status import Status


def main() -> None:
    parser = argparse.ArgumentParser(description="Stretch3-ZMQ Client")
    parser.add_argument("server_ip", help="Server IP address")
    parser.add_argument("--status-port", type=int, default=5555, help="Status port")
    parser.add_argument("--command-port", type=int, default=5556, help="Command port")
    parser.add_argument("--tts-port", type=int, default=6101, help="TTS port")
    parser.add_argument("--asr-port", type=int, default=6102, help="ASR port")
    args = parser.parse_args()

    server_ip: str = args.server_ip

    context = zmq.Context()

    try:
        # TTS socket (PUSH)
        tts_address = f"tcp://{server_ip}:{args.tts_port}"
        tts_socket: zmq.Socket = context.socket(zmq.PUSH)
        tts_socket.connect(tts_address)

        # ASR socket (REQ)
        asr_address = f"tcp://{server_ip}:{args.asr_port}"
        asr_socket: zmq.Socket = context.socket(zmq.REQ)
        asr_socket.connect(asr_address)

        # Command socket (PUB)
        cmd_address = f"tcp://{server_ip}:{args.command_port}"
        cmd_socket: zmq.Socket = context.socket(zmq.PUB)
        cmd_socket.connect(cmd_address)

        # Status socket (SUB)
        status_address = f"tcp://{server_ip}:{args.status_port}"
        status_socket: zmq.Socket = context.socket(zmq.SUB)
        status_socket.connect(status_address)
        status_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        print(f"Connected to {server_ip}")
        print(f"  TTS: {tts_address}")
        print(f"  ASR: {asr_address}")
        print(f"  Command: {cmd_address}")
        print(f"  Status: {status_address}")
        print("\nCommands:")
        print("  tts <text>                - Send text to TTS")
        print("  asr                       - Start listening for speech")
        print("  command <p0> ... <p8>     - Send robot command (9 joint positions)")
        print("  status                    - Subscribe to robot status (Ctrl+C to stop)")
        print("  quit                      - Exit\n")

        try:
            while True:
                cmd = input("> ").strip()

                if not cmd:
                    continue

                if cmd.lower() == "quit":
                    break

                if cmd.lower() == "asr":
                    print("Listening... Speak now!")
                    asr_socket.send_string("listen")
                    transcript = asr_socket.recv_string()
                    if transcript:
                        print(f"Transcript: {transcript}\n")
                    else:
                        print("No speech detected\n")

                elif cmd.lower().startswith("tts "):
                    text = cmd[4:].strip()
                    if text:
                        tts_socket.send_string(text)
                        print("Sent\n")
                    else:
                        print("No text provided\n")

                elif cmd.lower().startswith("command"):
                    cmd_args = cmd[7:].strip()
                    try:
                        if cmd_args:
                            parts = cmd_args.split()
                            positions = tuple(float(p) for p in parts)
                        else:
                            print("No positions provided. Using default dummy positions.")
                            positions = (0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)

                        c = Command(joint_positions=positions)
                        cmd_socket.send(c.to_bytes())
                        print(f"Sent command: {positions}\n")

                    except ValueError as e:
                        print(f"Invalid input: {e}")
                        print("Usage: command <p0> <p1> ... <p8>")
                        print("Example: command 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9\n")
                    except Exception as e:
                        print(f"Error sending command: {e}\n")

                elif cmd.lower() == "status":
                    print("Receiving status... (Ctrl+C to stop)")
                    try:
                        while True:
                            msg = status_socket.recv()
                            status = Status.from_bytes(msg)
                            pos_str = ", ".join(f"{p:.2f}" for p in status.joint_positions)
                            print(
                                f"\r[Status] pos=[{pos_str}] runstop={status.runstop}",
                                end="",
                                flush=True,
                            )
                    except KeyboardInterrupt:
                        print("\nStopped receiving status.\n")

                else:
                    print(
                        "Unknown command. Use 'tts <text>', 'asr', 'command', 'status', or 'quit'\n"
                    )

        except KeyboardInterrupt:
            print("\nShutting down...")
    finally:
        context.term()


if __name__ == "__main__":
    main()
