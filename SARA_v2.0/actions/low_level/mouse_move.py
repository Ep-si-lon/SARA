#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/mouse_move.py

 Moves the mouse cursor to the given screen coordinates.

 Usage:
   python3 mouse_move.py <x> <y> [--duration=0.3]

 Arguments:
   x              : Target X coordinate (integer)
   y              : Target Y coordinate (integer)
   --duration=N   : Movement duration in seconds (default: 0.3)

 Examples:
   python3 mouse_move.py 960 540
   python3 mouse_move.py 100 200 --duration=0.5
=============================================================================
"""

import sys
import os
import subprocess
import re

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = float(os.environ.get("SARA_ACTION_DELAY", "0.3"))
except ImportError:
    PYAUTOGUI_AVAILABLE = False

def move_xdotool(x: int, y: int):
    display = os.environ.get("SARA_DISPLAY", ":0")
    result = subprocess.run(
        ["xdotool", "mousemove", str(x), str(y)],
        env={**os.environ, "DISPLAY": display},
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"xdotool: {result.stderr.strip()}")

def main():
    args = sys.argv[1:]
    positional = [a for a in args if not a.startswith("--")]
    flags      = {a.lstrip("-").split("=")[0]: a.split("=")[1]
                  for a in args if a.startswith("--") and "=" in a}

    if len(positional) < 2:
        print("ERROR: x and y required.", file=sys.stderr); sys.exit(1)

    try:
        x = int(positional[0])
        y = int(positional[1])
        duration = float(flags.get("duration", "0.3"))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)

    print(f"[MOUSE_MOVE] move_to({x}, {y}, duration={duration})", flush=True)

    try:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.moveTo(x, y, duration=duration)
        else:
            move_xdotool(x, y)
        print(f"[MOUSE_MOVE] OK", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[MOUSE_MOVE] ERROR — {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
