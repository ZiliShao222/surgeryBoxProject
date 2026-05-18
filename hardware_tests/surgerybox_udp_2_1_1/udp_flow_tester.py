"""
UDP full-flow tester to simulate the PC side when talking to the MCU.

Usage examples:
  python udp_flow_tester.py --mcu-ip 192.168.4.1 --mcu-port 4210 --local-port 4211 --start --auto
  python udp_flow_tester.py --auto-ok2-delay 1.0

Features:
  - Binds to --local-port to receive MCU data (SEQ/DIST/SPEED/events).
  - Sends an initial HELLO_PC so MCU learns the return port.
  - Optional --start to send Start on launch.
  - Optional --auto to auto-respond to HighDamp/LowDamp:
        HighDamp -> send OK
        LowDamp -> send Continue then OK2 after --auto-ok2-delay
        Keep    -> send OK2
  - Interactive REPL: type any text to send raw, or use shortcuts:
        start, stop, winding, ok, ok1, ok2, continue, hello
  - Logs all RX/TX with timestamps.
"""

import argparse
import socket
import sys
import threading
import time


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def main():
    parser = argparse.ArgumentParser(description="UDP full-flow tester (PC side simulator)")
    parser.add_argument("--mcu-ip", default="192.168.4.1", help="MCU UDP IP")
    parser.add_argument("--mcu-port", type=int, default=4210, help="MCU UDP port")
    parser.add_argument("--local-port", type=int, default=4211, help="Local bind port to receive MCU data")
    parser.add_argument("--start", action="store_true", help="Send Start on launch")
    parser.add_argument("--auto", action="store_true", help="Auto respond to HighDamp/LowDamp/Keep")
    parser.add_argument("--auto-ok2-delay", type=float, default=1.0, help="Delay before sending OK2 after Continue")
    args = parser.parse_args()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", args.local_port))
    except Exception as e:
        log(f"Bind failed on port {args.local_port}: {e}")
        sys.exit(1)

    stop_flag = {"stop": False}
    current = {"seq": "", "pos": 0.0, "speed": 0.0}

    def send(msg: str):
        try:
            sock.sendto(msg.encode(), (args.mcu_ip, args.mcu_port))
            log(f"[TX] -> {args.mcu_ip}:{args.mcu_port} : {msg}")
        except Exception as e:
            log(f"[TX] error: {e}")

    def schedule_ok2():
        delay = max(0.0, args.auto_ok2_delay)
        timer = threading.Timer(delay, lambda: send("OK2"))
        timer.daemon = True
        timer.start()

    def handle_auto(msg_lower: str):
        if not args.auto:
            return
        if msg_lower == "highdamp":
            send("OK")
        elif msg_lower == "lowdamp":
            send("Continue")
            schedule_ok2()
        elif msg_lower == "keep":
            send("OK2")

    def listener():
        sock.settimeout(1.0)
        while not stop_flag["stop"]:
            try:
                data, addr = sock.recvfrom(2048)
                text = data.decode(errors="replace").strip()
                lower = text.lower()
                # Parse and print structured fields
                if lower.startswith("seq:"):
                    seq_body = text[4:].strip()
                    current["seq"] = seq_body
                    log(f"[SEQ] {seq_body}")
                elif lower.startswith("dist:") or lower.startswith("pull:") or lower.startswith("pos:"):
                    try:
                        val = float(text.split(":", 1)[1])
                        current["pos"] = val
                        log(f"[POS] {val:.2f} cm   (raw: {text})")
                    except Exception:
                        log(f"[RX] {addr}: {text}")
                elif lower.startswith("speed:"):
                    try:
                        val = float(text.split(":", 1)[1])
                        current["speed"] = val
                        log(f"[SPEED] {val:.2f} cm/s  (raw: {text})")
                    except Exception:
                        log(f"[RX] {addr}: {text}")
                else:
                    # Treat as event or misc
                    if lower in ("pain", "pain2", "highdamp", "lowdamp", "keep", "ok", "ok1", "ok2", "continue"):
                        log(f"[EVENT] {text}")
                    else:
                        log(f"[RX] {addr}: {text}")
                handle_auto(lower)
            except socket.timeout:
                continue
            except Exception as e:
                if not stop_flag["stop"]:
                    log(f"[RX] error: {e}")
                break

    # Start listener thread
    t = threading.Thread(target=listener, daemon=True)
    t.start()

    # Initial probe and optional Start
    send("HELLO_PC")
    if args.start:
        send("Start")

    log("Ready. Shortcuts: start/stop/winding/ok/ok1/ok2/continue/hello. Ctrl+C to quit.")
    try:
        while True:
            try:
                user = input("> ").strip()
            except EOFError:
                break
            if not user:
                continue
            cmd = user.lower()
            if cmd in ("start", "stop", "winding", "ok", "ok1", "ok2", "continue", "hello"):
                send(cmd.capitalize() if cmd != "hello" else "HELLO_PC")
            else:
                send(user)
    except KeyboardInterrupt:
        pass
    finally:
        stop_flag["stop"] = True
        time.sleep(0.2)
        sock.close()
        log("Exit.")


if __name__ == "__main__":
    main()
