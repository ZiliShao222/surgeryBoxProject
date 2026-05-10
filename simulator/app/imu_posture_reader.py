"""
Serial reader for the high-precision IMU posture sensor.

The sensor emits binary frames. Euler angle frames use:
  7E 23 11 26 <roll float32> <pitch float32> <yaw float32> <checksum>

Euler angles are radians in the vendor protocol. This module converts them to
degrees and reports whether the selected axis looks like a side-lying posture.
"""

from __future__ import annotations

import ctypes
import math
import struct
import time
from ctypes import wintypes

from PySide6.QtCore import QThread, Signal


GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
FILE_ATTRIBUTE_NORMAL = 0x80

NOPARITY = 0
ONESTOPBIT = 0

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


class WindowsSerial:
    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self.handle = None

    def __enter__(self):
        path = self.port if self.port.startswith("\\\\.\\") else "\\\\.\\" + self.port
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
            raise OSError(err, f"Could not open {self.port}. Close UartAssist or other serial tools.")
        self.handle = handle

        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        if not kernel32.GetCommState(handle, ctypes.byref(dcb)):
            raise OSError(ctypes.get_last_error(), "GetCommState failed")
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
        if not kernel32.SetCommState(handle, ctypes.byref(dcb)):
            raise OSError(ctypes.get_last_error(), "SetCommState failed")

        timeouts = COMMTIMEOUTS()
        timeouts.ReadIntervalTimeout = 20
        timeouts.ReadTotalTimeoutMultiplier = 0
        timeouts.ReadTotalTimeoutConstant = 100
        timeouts.WriteTotalTimeoutMultiplier = 0
        timeouts.WriteTotalTimeoutConstant = 100
        if not kernel32.SetCommTimeouts(handle, ctypes.byref(timeouts)):
            raise OSError(ctypes.get_last_error(), "SetCommTimeouts failed")
        kernel32.PurgeComm(handle, PURGE_RXCLEAR | PURGE_TXCLEAR)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle is not None:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def read(self, size: int = 512) -> bytes:
        buf = ctypes.create_string_buffer(size)
        read_count = wintypes.DWORD(0)
        ok = kernel32.ReadFile(self.handle, buf, size, ctypes.byref(read_count), None)
        if not ok:
            raise OSError(ctypes.get_last_error(), "ReadFile failed")
        return buf.raw[: read_count.value]


def _checksum_ok(frame: bytes) -> bool:
    return (sum(frame[:-1]) & 0xFF) == frame[-1]


def _iter_frames(stream: bytearray):
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
        if _checksum_ok(frame):
            yield frame


def _parse_euler_degrees(frame: bytes):
    if len(frame) != 0x11 or frame[3] != 0x26:
        return None
    roll, pitch, yaw = struct.unpack("<fff", frame[4:16])
    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


class ImuPostureThread(QThread):
    posture_changed = Signal(str, float, float, float, float)
    error = Signal(str)

    def __init__(
        self,
        port: str = "COM3",
        baud: int = 115200,
        axis: str = "roll",
        min_deg: float = 70.0,
        max_deg: float = 110.0,
        parent=None,
    ):
        super().__init__(parent)
        self.port = port
        self.baud = baud
        self.axis = axis
        self.min_deg = min_deg
        self.max_deg = max_deg
        self.stop_flag = False

    def run(self):
        axis_index = {"roll": 0, "pitch": 1, "yaw": 2}.get(self.axis, 0)
        buf = bytearray()
        last_emit = 0.0
        try:
            with WindowsSerial(self.port, self.baud) as serial_port:
                while not self.stop_flag:
                    chunk = serial_port.read(512)
                    if chunk:
                        buf.extend(chunk)
                    for frame in _iter_frames(buf):
                        euler = _parse_euler_degrees(frame)
                        if euler is None:
                            continue
                        now = time.time()
                        if now - last_emit < 0.2:
                            continue
                        last_emit = now
                        selected_angle = euler[axis_index]
                        abs_angle = abs(selected_angle)
                        status = "OK" if self.min_deg <= abs_angle <= self.max_deg else "BAD"
                        self.posture_changed.emit(status, euler[0], euler[1], euler[2], selected_angle)
        except Exception as exc:
            self.error.emit(str(exc))
