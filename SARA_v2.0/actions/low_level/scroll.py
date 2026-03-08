#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/scroll.py

 Scrolls the mouse wheel at the current position or given coordinates.

 Usage:
   python3 scroll.py <direction> [amount] [x] [y]

 Arguments:
   direction : up | down | left | right
   amount    : number of scroll ticks (default: 3)
   x, y      : optional screen position to scroll at

 Examples:
   python3 scroll.py down 5
   python3 scroll.py up 3
   python3 scroll.py down 3 960 540
=============================================================================
"""

import sys
import os
import subprocess

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = float(os.environ.get("SARA_ACTION_DELAY", "0.1"))
except ImportError:
    PYAUTOGUI_AVAILABLE = False

def scroll_xdotool(direction: str, amount: int, x=None, y=None):
    # xdotool button: 4=scroll up, 5=scroll down, 6=left, 7=right
    btn_map = {"up": 4, "down": 5, "left": 6, "right": 7}
    btn = btn_map.get(direction, 5)
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    cmd = ["xdotool"]
    if x is not None and y is not None:
        cmd += ["mousemove", str(x), str(y)]
    cmd += ["click", f"--repeat={amount}", str(btn)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"xdotool scroll: {result.stderr.strip()}")

def main():
    args = sys.argv[1:]
    if not args:
        print("ERROR: direction required (up|down|left|right)", file=sys.stderr); sys.exit(1)

    direction = args[0].lower()
    if direction not in ("up", "down", "left", "right"):
        print(f"ERROR: unknown direction '{direction}'", file=sys.stderr); sys.exit(1)

    amount = int(args[1]) if len(args) > 1 else 3
    x = int(args[2]) if len(args) > 2 else None
    y = int(args[3]) if len(args) > 3 else None

    print(f"[SCROLL] {direction} x{amount}" + (f" at ({x},{y})" if x else ""), flush=True)

    try:
        if PYAUTOGUI_AVAILABLE:
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.2)
            scroll_val = amount if direction == "up" else -amount
            if direction in ("up", "down"):
                pyautogui.scroll(scroll_val)
            else:
                pyautogui.hscroll(amount if direction == "right" else -amount)
        else:
            scroll_xdotool(direction, amount, x, y)

        print(f"[SCROLL] OK", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[SCROLL] ERROR — {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
