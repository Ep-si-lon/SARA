#!/usr/bin/env python3
"""
=============================================================================
 SARA Low-Level Action  —  actions/low_level/screenshot.py

 Takes a screenshot and saves it to a file.

 Usage:
   python3 screenshot.py [output_path] [--region=x,y,w,h]

 Arguments:
   output_path     : Where to save. Default: /tmp/sara_screenshot_<ts>.png
   --region=x,y,w,h: Capture only a region of the screen

 Examples:
   python3 screenshot.py
   python3 screenshot.py /tmp/my_shot.png
   python3 screenshot.py /tmp/crop.png --region=0,0,800,600
=============================================================================
"""

import sys
import os
import subprocess
from datetime import datetime

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def screenshot_xwd(output_path: str):
    """Fallback using scrot or import (ImageMagick)."""
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    # Try scrot first
    if subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
        subprocess.run(["scrot", output_path], env=env, check=True)
    elif subprocess.run(["which", "import"], capture_output=True).returncode == 0:
        subprocess.run(["import", "-window", "root", output_path], env=env, check=True)
    else:
        raise RuntimeError("No screenshot tool found (need scrot or ImageMagick).")

def main():
    args = sys.argv[1:]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/tmp/sara_screenshot_{ts}.png"
    region = None

    for arg in args:
        if arg.startswith("--region="):
            parts = arg.split("=")[1].split(",")
            region = tuple(int(p) for p in parts)   # (x, y, w, h)
        elif not arg.startswith("--"):
            output_path = arg

    print(f"[SCREENSHOT] Saving to: {output_path}", flush=True)

    try:
        if PYAUTOGUI_AVAILABLE:
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            img.save(output_path)
        else:
            screenshot_xwd(output_path)

        print(f"[SCREENSHOT] OK — {output_path}", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[SCREENSHOT] ERROR — {e}", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
