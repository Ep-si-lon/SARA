#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/type_text.py

 Types the given text string using keyboard simulation.
 Falls back to xdotool if PyAutoGUI is unavailable.

 Usage:
   python3 type_text.py "text to type" [--interval=0.05] [--xdotool]

 Arguments:
   text             : The string to type (quoted)
   --interval=N     : Seconds between each keypress (default: 0.05)
   --xdotool        : Force xdotool even if PyAutoGUI is available
   --clear-first    : Press Ctrl+A then Delete before typing (clear field)

 Examples:
   python3 type_text.py "lofi songs"
   python3 type_text.py "Hello World" --interval=0.08
   python3 type_text.py "search query" --clear-first
=============================================================================
"""

import sys
import os
import subprocess
import shlex

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = float(os.environ.get("SARA_ACTION_DELAY", "0.1"))
except ImportError:
    PYAUTOGUI_AVAILABLE = False

def type_xdotool(text: str, interval_ms: int):
    display = os.environ.get("SARA_DISPLAY", ":0")
    result = subprocess.run(
        ["xdotool", "type", f"--delay={interval_ms}", "--clearmodifiers", "--", text],
        env={**os.environ, "DISPLAY": display},
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"xdotool type error: {result.stderr.strip()}")

def clear_field_xdotool():
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    subprocess.run(["xdotool", "key", "ctrl+a"], env=env, check=False)
    subprocess.run(["xdotool", "key", "Delete"], env=env, check=False)

def main():
    args = sys.argv[1:]

    if not args:
        print("ERROR: No text provided.", file=sys.stderr); sys.exit(1)

    # First non-flag arg is the text
    text = None
    interval = 0.05
    force_xdotool = False
    clear_first = False

    for arg in args:
        if arg.startswith("--interval="):
            try:
                interval = float(arg.split("=")[1])
            except ValueError:
                pass
        elif arg == "--xdotool":
            force_xdotool = True
        elif arg == "--clear-first":
            clear_first = True
        elif not arg.startswith("--"):
            text = arg

    if text is None:
        print("ERROR: No text string provided.", file=sys.stderr); sys.exit(1)

    interval_ms = int(interval * 1000)

    print(f"[TYPE_TEXT] Typing: \"{text[:40]}{'...' if len(text)>40 else ''}\"", flush=True)

    try:
        use_pyautogui = PYAUTOGUI_AVAILABLE and not force_xdotool

        if clear_first:
            if use_pyautogui:
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("delete")
            else:
                clear_field_xdotool()

        if use_pyautogui:
            pyautogui.typewrite(text, interval=interval)
        else:
            type_xdotool(text, interval_ms)

        print(f"[TYPE_TEXT] OK", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[TYPE_TEXT] ERROR — {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
