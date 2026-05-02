#!/usr/bin/env python3
"""Apply or restore the MCU phase-2 AR debug helper.

The debug helper temporarily replaces
``RemoveNeedleTraining._phase_2_update`` with a verbose version so we can see
why the "Press here" target is or is not being triggered.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SIMULATOR_DIR = PROJECT_ROOT / "simulator"
TARGET_FILE = SIMULATOR_DIR / "app" / "training_remove_needle_mcu.py"
DEBUG_FILE = SIMULATOR_DIR / "app" / "training_remove_needle_mcu_debug.py"
MAIN_FILE = SIMULATOR_DIR / "main.py"
PYTHON_EXE = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
BACKUP_FILE = TARGET_FILE.with_suffix(TARGET_FILE.suffix + ".backup")


def print_header(text: str) -> None:
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")


def backup_target() -> None:
    if not TARGET_FILE.exists():
        raise FileNotFoundError(f"Target file not found: {TARGET_FILE}")

    if not BACKUP_FILE.exists():
        shutil.copy2(TARGET_FILE, BACKUP_FILE)
        print(f"[OK] Backup created: {BACKUP_FILE}")
    else:
        print(f"[OK] Backup already exists: {BACKUP_FILE}")


def extract_function_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1:node.end_lineno]) + "\n"

    raise ValueError(f"Function not found: {function_name}")


def replace_method_source(source: str, method_name: str, replacement: str) -> str:
    marker = f"    def {method_name}(self, frame, hand_data_list):"
    start = source.find(marker)
    if start == -1:
        raise ValueError(f"Method not found in target: {method_name}")

    next_method = source.find("\n    def ", start + len(marker))
    if next_method == -1:
        raise ValueError(f"Could not locate end of method: {method_name}")

    replacement = replacement.replace("_phase_2_update_debug", method_name, 1)
    replacement = textwrap.indent(replacement.strip() + "\n", "    ")
    return source[:start] + replacement + source[next_method + 1:]


def apply_debug_code() -> None:
    print_header("Apply Debug Code")
    backup_target()

    target_source = read_text(TARGET_FILE)
    debug_source = read_text(DEBUG_FILE)
    debug_method = extract_function_source(debug_source, "_phase_2_update_debug")
    updated_source = replace_method_source(target_source, "_phase_2_update", debug_method)
    write_text(TARGET_FILE, updated_source)

    print("[OK] Debug phase-2 method applied.")
    print("[INFO] Use `python run_debug_test.py restore` to restore the backup.")


def restore_backup() -> None:
    print_header("Restore Backup")
    if not BACKUP_FILE.exists():
        raise FileNotFoundError(f"Backup file not found: {BACKUP_FILE}")

    shutil.copy2(BACKUP_FILE, TARGET_FILE)
    BACKUP_FILE.unlink()
    print("[OK] Original training file restored.")


def run_application() -> int:
    print_header("Run Application")
    if not PYTHON_EXE.exists():
        raise FileNotFoundError(f"Python executable not found: {PYTHON_EXE}")
    if not MAIN_FILE.exists():
        raise FileNotFoundError(f"Main file not found: {MAIN_FILE}")

    print(f"[INFO] Command: {PYTHON_EXE} {MAIN_FILE}")
    print(f"[INFO] Working directory: {SIMULATOR_DIR}")

    process = subprocess.Popen(
        [str(PYTHON_EXE), str(MAIN_FILE)],
        cwd=SIMULATOR_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    try:
        for line in process.stdout:
            if "[DEBUG]" in line or "[Phase 2]" in line:
                print(line.rstrip())
    except KeyboardInterrupt:
        print("\n[INFO] Stopping output stream.")
        process.terminate()

    return process.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug the MCU phase-2 AR target flow.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("apply", help="Apply the debug phase-2 method.")
    subparsers.add_parser("run", help="Run the simulator without changing files.")
    subparsers.add_parser("restore", help="Restore training_remove_needle_mcu.py from backup.")
    subparsers.add_parser("apply-run", help="Apply debug method and run the simulator.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command or "apply-run"

    try:
        if command == "apply":
            apply_debug_code()
            return 0
        if command == "run":
            return run_application()
        if command == "restore":
            restore_backup()
            return 0
        if command == "apply-run":
            apply_debug_code()
            return run_application()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"[ERROR] Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
