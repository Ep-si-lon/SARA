#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/mouse_click.py

 Performs a mouse click at the given screen coordinates.
 Falls back to xdotool if PyAutoGUI is not available.

 Usage:
   python3 mouse_click.py <x> <y> [button] [--double]

 Arguments:
   x        : X screen coordinate (integer)
   y        : Y screen coordinate (integer)
   button   : left | right | middle  (default: left)
   --double : perform a double-click

 Examples:
   python3 mouse_click.py 960 540
   python3 mouse_click.py 200 300 right
   python3 mouse_click.py 400 400 left --double

 Exit codes:
   0  success
   1  argument error
   2  execution error
=============================================================================
"""

import sys
import os
import time
import subprocess

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True       # Move mouse to top-left to abort
    pyautogui.PAUSE = float(os.environ.get("SARA_ACTION_DELAY", "0.3"))
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# =============================================================================
#  Helpers
# =============================================================================

BUTTON_MAP = {
    "left"   : 1,
    "middle" : 2,
    "right"  : 3,
}

def usage():
    print(__doc__)
    sys.exit(1)

def click_pyautogui(x: int, y: int, button: str, double: bool):
    """Use PyAutoGUI to click."""
    pyautogui.moveTo(x, y, duration=0.2)
    if double:
        pyautogui.doubleClick(x, y, button=button)
    else:
        pyautogui.click(x, y, button=button)

def click_xdotool(x: int, y: int, button: int, double: bool):
    """Use xdotool as fallback."""
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    cmd = ["xdotool", "mousemove", str(x), str(y),
           "click", f"--repeat={'2' if double else '1'}", str(button)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"xdotool error: {result.stderr.strip()}")

# =============================================================================
#  Entry Point
# =============================================================================
def main():
    args = sys.argv[1:]

    # Parse positional args
    positional = [a for a in args if not a.startswith("--")]
    flags      = [a for a in args if a.startswith("--")]

    if len(positional) < 2:
        print("ERROR: x and y coordinates are required.", file=sys.stderr)
        usage()

    try:
        x = int(positional[0])
        y = int(positional[1])
    except ValueError:
        print("ERROR: x and y must be integers.", file=sys.stderr)
        sys.exit(1)

    button_str = positional[2].lower() if len(positional) > 2 else "left"
    if button_str not in BUTTON_MAP:
        print(f"ERROR: Unknown button '{button_str}'. Use left|right|middle.", file=sys.stderr)
        sys.exit(1)

    button_int = BUTTON_MAP[button_str]
    double     = "--double" in flags

    # Log action
    action_desc = f"{'double-' if double else ''}click({x}, {y}, {button_str})"
    print(f"[MOUSE_CLICK] {action_desc}", flush=True)

    # Execute
    try:
        if PYAUTOGUI_AVAILABLE:
            click_pyautogui(x, y, button_str, double)
        else:
            click_xdotool(x, y, button_int, double)
        print(f"[MOUSE_CLICK] OK — {action_desc}", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[MOUSE_CLICK] ERROR — {e}", file=sys.stderr, flush=True)
        sys.exit(2)

if __name__ == "__main__":
    main()
