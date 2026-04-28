"""Serial transport for the wired mannequin hardware."""

from __future__ import annotations

import threading
from typing import List

from PySide6.QtCore import QThread, Signal

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - handled at runtime for friendly UI errors
    serial = None
    list_ports = None


def list_serial_ports() -> List[str]:
    """Return available serial port names, or an empty list if pyserial is absent."""

    if list_ports is None:
        return []
    try:
        return [port.device for port in list_ports.comports()]
    except Exception:
        return []


class SerialConnectionTestThread(QThread):
    """Quick, non-blocking serial availability check for the Simulator page."""

    connection_result = Signal(bool, str)

    def __init__(self, port: str = "COM3", baudrate: int = 115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate

    def run(self):
        if serial is None:
            self.connection_result.emit(False, "pyserial is not installed. Run: pip install pyserial==3.5")
            return

        ports = list_serial_ports()
        if ports and self.port not in ports:
            self.connection_result.emit(False, f"{self.port} not found. Available: {', '.join(ports)}")
            return
        if not ports:
            self.connection_result.emit(False, f"No serial ports detected. Expected {self.port} @ {self.baudrate}")
            return

        handle = None
        try:
            handle = serial.Serial(self.port, self.baudrate, timeout=0.5)
            self.connection_result.emit(True, f"Serial ready on {self.port} @ {self.baudrate}")
        except Exception as exc:
            self.connection_result.emit(False, f"Serial test failed on {self.port}: {str(exc)[:120]}")
        finally:
            try:
                if handle is not None:
                    handle.close()
            except Exception:
                pass


class SerialHardwareListener(QThread):
    """Read line-based hardware telemetry from a USB serial port."""

    message_received = Signal(str)
    connection_changed = Signal(bool, str)

    def __init__(self, port: str = "COM3", baudrate: int = 115200, read_timeout: float = 0.1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.read_timeout = read_timeout
        self.stop_flag = False
        self.ready = False
        self.last_error = ""
        self._serial = None
        self._lock = threading.Lock()

    def run(self):
        if serial is None:
            self.last_error = "pyserial is not installed. Run: pip install pyserial==3.5"
            self.connection_changed.emit(False, self.last_error)
            return

        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=self.read_timeout)
            self.ready = True
            self.connection_changed.emit(True, f"Connected to {self.port} @ {self.baudrate}")

            while not self.stop_flag:
                try:
                    line = self._serial.readline()
                    if not line:
                        continue
                    text = line.decode("utf-8", errors="replace").strip()
                    if text:
                        self.message_received.emit(text)
                except Exception as exc:
                    if self.stop_flag:
                        break
                    self.last_error = str(exc)
                    self.connection_changed.emit(False, self.last_error)
                    break
        except Exception as exc:
            self.last_error = str(exc)
            self.connection_changed.emit(False, self.last_error)
        finally:
            self.ready = False
            self._close_serial()
            self.connection_changed.emit(False, "Serial disconnected")

    def send_message(self, message: str) -> bool:
        """Send one command line to the hardware."""

        if not self.ready or self._serial is None:
            return False

        try:
            payload = (message.strip() + "\n").encode("utf-8")
            with self._lock:
                self._serial.write(payload)
                self._serial.flush()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.connection_changed.emit(False, self.last_error)
            return False

    def stop(self):
        self.stop_flag = True
        self._close_serial()

    def _close_serial(self):
        try:
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass
        finally:
            self._serial = None
