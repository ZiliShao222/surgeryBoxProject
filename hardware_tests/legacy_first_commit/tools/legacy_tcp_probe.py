#!/usr/bin/env python3
"""TCP probe for the legacy first-commit SurgeryBox firmware.

The legacy firmware exposes a TCP server at 192.168.4.1:1234 and emits event
names instead of realtime POS telemetry. This script sends Start and logs events.
"""

from __future__ import annotations

import argparse
import socket
import time


def send_line(sock: socket.socket, line: str) -> None:
    data = (line.rstrip("\r\n") + "\n").encode("utf-8")
    sock.sendall(data)
    print(f">>> {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe legacy TCP hardware firmware")
    parser.add_argument("--host", default="192.168.4.1", help="board IP address")
    parser.add_argument("--port", type=int, default=1234, help="legacy TCP port")
    parser.add_argument("--duration", type=float, default=120.0, help="seconds to listen")
    parser.add_argument("--no-auto-reply", action="store_true", help="do not auto-reply to damping events")
    args = parser.parse_args()

    deadline = time.time() + args.duration
    buffer = ""

    print(f"Connecting to {args.host}:{args.port} ...")
    with socket.create_connection((args.host, args.port), timeout=10.0) as sock:
        sock.settimeout(0.5)
        print("Connected. Sending Start. Pull the catheter/encoder now.")
        send_line(sock, "Start")

        while time.time() < deadline:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                continue
            if not chunk:
                print("Connection closed by board.")
                return 1

            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                raw, buffer = buffer.split("\n", 1)
                event = raw.strip()
                if not event:
                    continue
                print(f"<<< {event}")

                if args.no_auto_reply:
                    continue
                lower = event.lower()
                if lower == "highdamp":
                    send_line(sock, "OK")
                elif lower == "lowdamp":
                    send_line(sock, "OK1")
                elif lower == "keep":
                    send_line(sock, "OK2")

    print("Probe finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
