# Legacy First Commit Hardware Test

This directory is an isolated copy of commit `815f369 first commit`, kept for hardware regression testing.
It is intentionally not wired into the current app.

## What This Firmware Uses

- Wi-Fi SSID: `MyBrakeMachine`
- Wi-Fi password: `12345678`
- Protocol: TCP
- Board IP: `192.168.4.1`
- TCP port: `1234`
- Start command: `Start\n`
- Event messages: `Pain`, `Pain2`, `HighDamp`, `LowDamp`, `Keep`

Important: this legacy firmware does not send realtime `POS` packets. The current AR app expects UDP `surgeryBox` telemetry, so use the probe script below instead of the current AR screen for this legacy test.

## Upload

From this directory:

```powershell
pio run -t upload
```

If your PlatformIO command is installed as `platformio`, use:

```powershell
platformio run -t upload
```

## Test

1. Flash this legacy firmware.
2. Connect the PC Wi-Fi to `MyBrakeMachine` with password `12345678`.
3. Run:

```powershell
python tools\legacy_tcp_probe.py
```

The probe sends `Start`, prints incoming hardware events, and auto-replies:

- `HighDamp` -> `OK`
- `LowDamp` -> `OK1`
- `Keep` -> `OK2`

If events arrive here, the old hardware/encoder path is alive. If no events arrive while pulling, check encoder ticks/wiring/interrupts on the hardware side.
