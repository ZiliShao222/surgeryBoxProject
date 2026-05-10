#!/usr/bin/env python3
"""
Read the high-precision IMU over a Windows COM port and print posture status.

The sensor sends binary protocol frames:
  7E 23 11 26 <roll float32> <pitch float32> <yaw float32> <checksum>

The manual says Euler angles are in radians. This script also prints degrees
because degrees are easier to understand while testing side-lying posture.
"""

from __future__ import annotations

import argparse
import ctypes
import math
import struct
import sys
import time
from ctypes import wintypes


GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
FILE_ATTRIBUTE_NORMAL = 0x80

NOPARITY = 0
ONESTOPBIT = 0

EV_RXCHAR = 0x0001
PURGE_RXCLEAR = 0x0008
PURGE_TXCLEAR = 0x0004


class DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength", wintypes.DWORD),
        ("BaudRate", wintypes.DWORD),
        ("fBinary", wintypes.DWORD, 1),
        ("fParity", wintypes.DWORD, 1),
        ("fOutxCtsFlow", wintypes.DWORD, 1),
        ("fOutxDsrFlow", wintypes.DWORD, 1),
        ("fDtrControl", wintypes.DWORD, 2),
        ("fDsrSensitivity", wintypes.DWORD, 1),
        ("fTXContinueOnXoff", wintypes.DWORD, 1),
        ("fOutX", wintypes.DWORD, 1),
        ("fInX", wintypes.DWORD, 1),
        ("fErrorChar", wintypes.DWORD, 1),
        ("fNull", wintypes.DWORD, 1),
        ("fRtsControl", wintypes.DWORD, 2),
        ("fAbortOnError", wintypes.DWORD, 1),
        ("fDummy2", wintypes.DWORD, 17),
        ("wReserved", wintypes.WORD),
        ("XonLim", wintypes.WORD),
        ("XoffLim", wintypes.WORD),
        ("ByteSize", wintypes.BYTE),
        ("Parity", wintypes.BYTE),
        ("StopBits", wintypes.BYTE),
        ("XonChar", ctypes.c_char),
        ("XoffChar", ctypes.c_char),
        ("ErrorChar", ctypes.c_char),
        ("EofChar", ctypes.c_char),
        ("EvtChar", ctypes.c_char),
        ("wReserved1", wintypes.WORD),
    ]


class COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [
        ("ReadIntervalTimeout", wintypes.DWORD),
        ("ReadTotalTimeoutMultiplier", wintypes.DWORD),
        ("ReadTotalTimeoutConstant", wintypes.DWORD),
        ("WriteTotalTimeoutMultiplier", wintypes.DWORD),
        ("WriteTotalTimeoutConstant", wintypes.DWORD),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _check(ok: bool, message: str) -> None:
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(err, f"{message}: Windows error {err}")


class WindowsSerial:
    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.handle = None

    def __enter__(self) -> "WindowsSerial":
        path = self.port
        if not path.startswith("\\\\.\\"):
            path = "\\\\.\\" + path
        handle = kernel32.CreateFileW(
            path,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            raise OSError(err, f"Could not open {self.port}. Close UartAssist first, then try again.")
        self.handle = handle

        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        _check(kernel32.GetCommState(handle, ctypes.byref(dcb)), "GetCommState failed")
        dcb.BaudRate = self.baud
        dcb.ByteSize = 8
        dcb.Parity = NOPARITY
        dcb.StopBits = ONESTOPBIT
        dcb.fBinary = 1
        dcb.fParity = 0
        dcb.fOutxCtsFlow = 0
        dcb.fOutxDsrFlow = 0
        dcb.fDtrControl = 1
        dcb.fRtsControl = 1
        _check(kernel32.SetCommState(handle, ctypes.byref(dcb)), "SetCommState failed")

        timeouts = COMMTIMEOUTS()
        timeouts.ReadIntervalTimeout = 20
        timeouts.ReadTotalTimeoutMultiplier = 0
        timeouts.ReadTotalTimeoutConstant = 100
        timeouts.WriteTotalTimeoutMultiplier = 0
        timeouts.WriteTotalTimeoutConstant = 100
        _check(kernel32.SetCommTimeouts(handle, ctypes.byref(timeouts)), "SetCommTimeouts failed")
        kernel32.PurgeComm(handle, PURGE_RXCLEAR | PURGE_TXCLEAR)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is not None:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def read(self, size: int = 256) -> bytes:
        buf = ctypes.create_string_buffer(size)
        read_count = wintypes.DWORD(0)
        ok = kernel32.ReadFile(self.handle, buf, size, ctypes.byref(read_count), None)
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(err, f"ReadFile failed: Windows error {err}")
        return buf.raw[: read_count.value]


def checksum_ok(frame: bytes) -> bool:
    return (sum(frame[:-1]) & 0xFF) == frame[-1]


def iter_frames(stream: bytearray):
    while True:
        start = stream.find(b"\x7E\x23")
        if start < 0:
            del stream[:-1]
            return
        if start:
            del stream[:start]
        if len(stream) < 3:
            return
        frame_len = stream[2]
        if frame_len < 5 or frame_len > 64:
            del stream[0]
            continue
        if len(stream) < frame_len:
            return
        frame = bytes(stream[:frame_len])
        del stream[:frame_len]
        if checksum_ok(frame):
            yield frame


def parse_euler_frame(frame: bytes):
    if len(frame) != 0x11 or frame[3] != 0x26:
        return None
    roll, pitch, yaw = struct.unpack("<fff", frame[4:16])
    return roll, pitch, yaw


def posture_status(angle_deg: float, min_deg: float, max_deg: float) -> str:
    a = abs(angle_deg)
    return "OK" if min_deg <= a <= max_deg else "BAD"


def main() -> int:
    parser = argparse.ArgumentParser(description="IMU side-lying posture tester")
    parser.add_argument("--port", default="COM3", help="Serial port, for example COM3")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument(
        "--axis",
        choices=["roll", "pitch", "yaw"],
        default="roll",
        help="Euler angle used for side-lying judgement",
    )
    parser.add_argument("--min-deg", type=float, default=70.0, help="Minimum absolute angle for OK")
    parser.add_argument("--max-deg", type=float, default=110.0, help="Maximum absolute angle for OK")
    parser.add_argument("--print-every", type=float, default=0.2, help="Seconds between printed lines")
    args = parser.parse_args()

    print("IMU posture tester")
    print(f"Port: {args.port}, baud: {args.baud}")
    print(f"Rule: abs({args.axis}) between {args.min_deg:.1f} and {args.max_deg:.1f} degrees => POSTURE:OK")
    print("Close UartAssist before running this script. Press Ctrl+C to stop.\n")

    axis_index = {"roll": 0, "pitch": 1, "yaw": 2}[args.axis]
    buf = bytearray()
    last_print = 0.0
    frames = 0

    try:
        with WindowsSerial(args.port, args.baud) as ser:
            while True:
                chunk = ser.read(512)
                if chunk:
                    buf.extend(chunk)
                for frame in iter_frames(buf):
                    euler = parse_euler_frame(frame)
                    if euler is None:
                        continue
                    now = time.time()
                    if now - last_print < args.print_every:
                        continue
                    last_print = now
                    frames += 1
                    deg = tuple(math.degrees(v) for v in euler)
                    chosen = deg[axis_index]
                    status = posture_status(chosen, args.min_deg, args.max_deg)
                    print(
                        f"{frames:05d} "
                        f"roll={deg[0]:8.2f}deg pitch={deg[1]:8.2f}deg yaw={deg[2]:8.2f}deg "
                        f"POSTURE:{status}"
                    )
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    except OSError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("Tip: close UartAssist, check the COM number, then run again.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
