"""Interactive ZMQ client for testing Stretch3-ZMQ Driver services.

Supports robot control (command/status), speech (TTS/ASR), and camera
streaming (Arducam, D435if, D405) with a 5-second receive timeout so
camera windows close cleanly even if the server stops sending frames.
"""

import argparse

import cv2
import numpy as np
import zmq

from stretch3_zmq_core.messages.command import Command
from stretch3_zmq_core.messages.status import Status

CAMERA_RECV_TIMEOUT_MS = 5000


# ---------------------------------------------------------------------------
# Camera helpers
# ---------------------------------------------------------------------------

def _show_rgbd_frame(
    window_name: str,
    color_raw: bytes,
    depth_raw: bytes,
    rotate_code: int | None = None,
) -> None:
    """Decode raw RGB-D buffers, colorize depth, and display side-by-side."""
    color = np.frombuffer(color_raw, np.uint8).reshape(480, 640, 3)
    depth = np.frombuffer(depth_raw, np.uint16).reshape(480, 640)

    depth_vis = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    depth_cmap = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

    if rotate_code is not None:
        color = cv2.rotate(color, rotate_code)
        depth_cmap = cv2.rotate(depth_cmap, rotate_code)

    cv2.imshow(window_name, np.hstack((color, depth_cmap)))


def _stream_arducam(socket: zmq.Socket) -> None:
    """Stream Arducam: 1280x720, rotated 90 CW + vertical flip."""
    print("Opening Arducam (press 'q' to quit)...")
    try:
        while True:
            try:
                raw = socket.recv()
            except zmq.Again:
                print("\nArducam: no frame received (timeout).")
                break
            frame = np.frombuffer(raw, np.uint8).reshape(720, 1280, 3)
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            frame = cv2.flip(frame, 0)
            cv2.imshow("Arducam", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()


def _stream_rgbd(
    name: str,
    color_socket: zmq.Socket,
    depth_socket: zmq.Socket,
    rotate_code: int | None = None,
) -> None:
    """Stream an RGB-D camera pair with optional rotation."""
    print(f"Opening {name} (press 'q' to quit)...")
    try:
        while True:
            try:
                color_raw = color_socket.recv()
                depth_raw = depth_socket.recv()
            except zmq.Again:
                print(f"\n{name}: no frame received (timeout).")
                break
            _show_rgbd_frame(name, color_raw, depth_raw, rotate_code)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# Socket setup
# ---------------------------------------------------------------------------

def _connect_sub(
    context: zmq.Context,
    address: str,
    *,
    timeout_ms: int | None = None,
) -> zmq.Socket:
    """Create a SUB socket with HWM=1 and an optional receive timeout."""
    sock = context.socket(zmq.SUB)
    sock.setsockopt(zmq.RCVHWM, 1)
    if timeout_ms is not None:
        sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
    sock.connect(address)
    sock.setsockopt_string(zmq.SUBSCRIBE, "")
    return sock


# ---------------------------------------------------------------------------
# REPL command handlers
# ---------------------------------------------------------------------------

def _handle_tts(tts_socket: zmq.Socket, text: str) -> None:
    if text:
        tts_socket.send_string(text)
        print("Sent\n")
    else:
        print("No text provided\n")


def _handle_asr(asr_socket: zmq.Socket) -> None:
    print("Listening... Speak now!")
    asr_socket.send_string("listen")
    transcript = asr_socket.recv_string()
    print(f"Transcript: {transcript}\n" if transcript else "No speech detected\n")


def _handle_command(cmd_socket: zmq.Socket, args_str: str) -> None:
    try:
        if args_str:
            positions = tuple(float(p) for p in args_str.split())
        else:
            print("No positions provided. Using default dummy positions.")
            positions = (0.0, 0.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 100.0)

        cmd_socket.send(Command(joint_positions=positions).to_bytes())
        print(f"Sent command: {positions}\n")
    except ValueError as e:
        print(f"Invalid input: {e}")
        print("Usage: command <p0> <p1> ... <p8>")
        print("Example: command 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9\n")
    except Exception as e:
        print(f"Error sending command: {e}\n")


def _handle_status(status_socket: zmq.Socket) -> None:
    print("Receiving status... (Ctrl+C to stop)")
    try:
        while True:
            status = Status.from_bytes(status_socket.recv())
            pos_str = ", ".join(f"{p:.2f}" for p in status.joint_positions)
            print(
                f"\r[Status] pos=[{pos_str}] runstop={status.runstop}",
                end="",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\nStopped receiving status.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

HELP_TEXT = """\
Commands:
  tts <text>             Send text to TTS
  asr                    Start listening for speech
  command <p0>...<p8>    Send robot command (9 joint positions)
  status                 Subscribe to robot status (Ctrl+C to stop)
  camera [camera_name]   Stream camera feed (press 'q' to stop)
                         Options: arducam, d435if (default), d405
  quit                   Exit
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Stretch3-ZMQ Client")
    parser.add_argument("server_ip", help="Server IP address")
    parser.add_argument("--status-port", type=int, default=5555, help="Status port")
    parser.add_argument("--command-port", type=int, default=5556, help="Command port")
    parser.add_argument("--tts-port", type=int, default=6101, help="TTS port")
    parser.add_argument("--asr-port", type=int, default=6102, help="ASR port")
    parser.add_argument("--arducam-port", type=int, default=6000, help="Arducam port")
    parser.add_argument("--d435if-color-port", type=int, default=6001, help="D435if color port")
    parser.add_argument("--d435if-depth-port", type=int, default=6002, help="D435if depth port")
    parser.add_argument("--d405-color-port", type=int, default=6003, help="D405 color port")
    parser.add_argument("--d405-depth-port", type=int, default=6004, help="D405 depth port")
    args = parser.parse_args()

    server_ip: str = args.server_ip
    context = zmq.Context()

    try:
        # Control & speech sockets
        tts_socket = context.socket(zmq.PUSH)
        tts_socket.connect(f"tcp://{server_ip}:{args.tts_port}")

        asr_socket = context.socket(zmq.REQ)
        asr_socket.connect(f"tcp://{server_ip}:{args.asr_port}")

        cmd_socket = context.socket(zmq.PUB)
        cmd_socket.connect(f"tcp://{server_ip}:{args.command_port}")

        status_socket = context.socket(zmq.SUB)
        status_socket.connect(f"tcp://{server_ip}:{args.status_port}")
        status_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # Camera sockets (with receive timeout for safe shutdown)
        def cam_sub(port: int) -> zmq.Socket:
            return _connect_sub(
                context,
                f"tcp://{server_ip}:{port}",
                timeout_ms=CAMERA_RECV_TIMEOUT_MS,
            )

        arducam_socket = cam_sub(args.arducam_port)
        d435if_color = cam_sub(args.d435if_color_port)
        d435if_depth = cam_sub(args.d435if_depth_port)
        d405_color = cam_sub(args.d405_color_port)
        d405_depth = cam_sub(args.d405_depth_port)

        print(f"Connected to {server_ip}")
        print(HELP_TEXT)

        while True:
            try:
                user_input = input("> ").strip()
            except KeyboardInterrupt:
                print("\nShutting down...")
                break

            if not user_input:
                continue

            cmd = user_input.lower()

            if cmd == "quit":
                break
            elif cmd.startswith("tts "):
                _handle_tts(tts_socket, user_input[4:].strip())
            elif cmd == "asr":
                _handle_asr(asr_socket)
            elif cmd.startswith("command"):
                _handle_command(cmd_socket, user_input[7:].strip())
            elif cmd == "status":
                _handle_status(status_socket)
            elif cmd == "camera" or cmd.startswith("camera "):
                # Parse camera name, default to d435if
                parts = user_input.split(maxsplit=1)
                camera_name = parts[1].strip().lower() if len(parts) > 1 else "d435if"

                if camera_name == "arducam":
                    _stream_arducam(arducam_socket)
                elif camera_name == "d435if":
                    _stream_rgbd("D435if", d435if_color, d435if_depth, cv2.ROTATE_90_CLOCKWISE)
                elif camera_name == "d405":
                    _stream_rgbd("D405", d405_color, d405_depth)
                else:
                    print(f"Unknown camera: {camera_name}. Options: arducam, d435if, d405\n")
            else:
                print("Unknown command. Type a command from the list above.\n")

    finally:
        context.term()


if __name__ == "__main__":
    main()
