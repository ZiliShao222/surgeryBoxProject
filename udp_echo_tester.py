"""
Simple UDP send/receive test script for MCU link.

Usage:
  python udp_echo_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211

Behavior:
  - Binds to --local-port to receive MCU replies.
  - Sends a probe ("HELLO_PC") on start to help the MCU learn the return port.
  - Press ENTER to send a test message; type text to send custom payloads.
  - Ctrl+C to exit.
"""
import argparse
import socket
import sys
import threading
import time


def start_listener(sock: socket.socket, stop_flag):
    sock.settimeout(1.0)
    while not stop_flag["stop"]:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode(errors="replace").strip()
            print(f"[RX] {addr}: {msg}")
        except socket.timeout:
            continue
        except Exception as e:
            if not stop_flag["stop"]:
                print(f"[RX] error: {e}")
            break


def main():
    parser = argparse.ArgumentParser(description="UDP echo tester")
    parser.add_argument("--mcu-ip", default="192.168.4.1", help="MCU UDP IP")
    parser.add_argument("--mcu-port", type=int, default=4210, help="MCU UDP port")
    parser.add_argument("--local-port", type=int, default=4211, help="Local bind port for replies")
    args = parser.parse_args()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", args.local_port))
    except Exception as e:
        print(f"Bind failed on port {args.local_port}: {e}")
        sys.exit(1)

    stop_flag = {"stop": False}
    listener = threading.Thread(target=start_listener, args=(sock, stop_flag), daemon=True)
    listener.start()

    def send(msg: str):
        try:
            sock.sendto(msg.encode(), (args.mcu_ip, args.mcu_port))
            print(f"[TX] -> {args.mcu_ip}:{args.mcu_port} : {msg}")
        except Exception as e:
            print(f"[TX] error: {e}")

    # Initial probe to register return port on MCU
    send("HELLO_PC")

    print("Ready. Press ENTER to send 'PING', or type a message then ENTER. Ctrl+C to quit.")
    try:
        while True:
            user = input().strip()
            payload = user if user else "PING"
            send(payload)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stop_flag["stop"] = True
        time.sleep(0.2)
        sock.close()


if __name__ == "__main__":
    main()
