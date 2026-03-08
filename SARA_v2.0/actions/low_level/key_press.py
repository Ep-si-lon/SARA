#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/key_press.py

 Simulates pressing one or more keyboard keys.

 Usage:
   python3 key_press.py <key> [key2 key3 ...]
   python3 key_press.py --combo <mod+key>

 Arguments:
   key            : Key name (enter, tab, escape, space, backspace,
                    ctrl, alt, shift, super, F1-F12, up, down, left, right, etc.)
   --combo        : Hotkey combo like "ctrl+c", "ctrl+shift+t", "alt+F4"

 Examples:
   python3 key_press.py enter
   python3 key_press.py escape
   python3 key_press.py --combo ctrl+c
   python3 key_press.py --combo ctrl+shift+t
   python3 key_press.py tab tab tab
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

# Mapping from friendly names to xdotool key names
XDOTOOL_KEY_MAP = {
    "enter"     : "Return",
    "return"    : "Return",
    "tab"       : "Tab",
    "escape"    : "Escape",
    "esc"       : "Escape",
    "space"     : "space",
    "backspace" : "BackSpace",
    "delete"    : "Delete",
    "home"      : "Home",
    "end"       : "End",
    "pageup"    : "Prior",
    "pagedown"  : "Next",
    "up"        : "Up",
    "down"      : "Down",
    "left"      : "Left",
    "right"     : "Right",
    "super"     : "super",
    "ctrl"      : "ctrl",
    "alt"       : "alt",
    "shift"     : "shift",
}

def to_xdotool_key(key: str) -> str:
    return XDOTOOL_KEY_MAP.get(key.lower(), key)

def press_xdotool(keys: list[str]):
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    for key in keys:
        result = subprocess.run(
            ["xdotool", "key", to_xdotool_key(key)],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"xdotool key error: {result.stderr.strip()}")

def combo_xdotool(combo: str):
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    # xdotool accepts "ctrl+c" style combos directly
    parts = combo.split("+")
    xdo_combo = "+".join(to_xdotool_key(p) for p in parts)
    result = subprocess.run(
        ["xdotool", "key", xdo_combo],
        env=env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"xdotool combo error: {result.stderr.strip()}")

def main():
    args = sys.argv[1:]
    if not args:
        print("ERROR: No key specified.", file=sys.stderr); sys.exit(1)

    is_combo = "--combo" in args

    try:
        if is_combo:
            idx = args.index("--combo")
            combo = args[idx + 1] if idx + 1 < len(args) else None
            if not combo:
                print("ERROR: --combo requires a key combo.", file=sys.stderr); sys.exit(1)

            print(f"[KEY_PRESS] combo: {combo}", flush=True)

            if PYAUTOGUI_AVAILABLE:
                parts = combo.split("+")
                pyautogui.hotkey(*parts)
            else:
                combo_xdotool(combo)

        else:
            keys = [a for a in args if not a.startswith("--")]
            print(f"[KEY_PRESS] keys: {keys}", flush=True)

            if PYAUTOGUI_AVAILABLE:
                for key in keys:
                    pyautogui.press(key)
            else:
                press_xdotool(keys)

        print(f"[KEY_PRESS] OK", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[KEY_PRESS] ERROR — {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
