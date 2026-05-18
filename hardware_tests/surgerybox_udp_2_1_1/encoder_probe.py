"""
Poll the SurgeryBox encoder diagnostic command over UDP.

Flash this test firmware first, connect the PC to the surgeryBox Wi-Fi, then run:
  python encoder_probe.py --start

While it is running, pull the catheter. Watch whether raw/ticks changes and
whether A/B pin levels toggle.
"""

import argparse
import socket
import sys
import time


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def drain(sock: socket.socket, timeout: float) -> None:
    end = time.time() + timeout
    sock.settimeout(0.05)
    while time.time() < end:
        try:
            data, addr = sock.recvfrom(4096)
            text = data.decode(errors="replace").strip()
            log(f"[RX] {addr}: {text}")
        except socket.timeout:
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description="SurgeryBox encoder UDP probe")
    parser.add_argument("--mcu-ip", default="192.168.4.1", help="MCU UDP IP")
    parser.add_argument("--mcu-port", type=int, default=4210, help="MCU UDP port")
    parser.add_argument("--local-port", type=int, default=4211, help="Local bind port for replies")
    parser.add_argument("--interval", type=float, default=0.5, help="Polling interval in seconds")
    parser.add_argument("--duration", type=float, default=60.0, help="Probe duration in seconds")
    parser.add_argument("--start", action="store_true", help="Send Start before polling ENC")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("", args.local_port))
    except OSError as exc:
        print(f"Bind failed on port {args.local_port}: {exc}")
        print("Close other UDP testers first, or use another --local-port such as 4212.")
        sys.exit(1)

    def send(msg: str) -> None:
        sock.sendto(msg.encode(), (args.mcu_ip, args.mcu_port))
        log(f"[TX] -> {args.mcu_ip}:{args.mcu_port} : {msg}")

    try:
        send("HELLO_PC")
        drain(sock, 0.4)
        if args.start:
            send("Start")
            drain(sock, 0.6)

        log("Pull the catheter now. Ctrl+C to stop.")
        deadline = time.time() + args.duration
        while time.time() < deadline:
            send("ENC")
            drain(sock, max(0.1, args.interval))
    except KeyboardInterrupt:
        log("Stopped by user.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
