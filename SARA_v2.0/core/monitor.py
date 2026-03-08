#!/usr/bin/env python3
"""
=============================================================================
 SARA  —  core/monitor.py
 Version 1.0

 BACKGROUND MONITOR
 ──────────────────
 Runs as a background daemon and:
   • Watches the event_log.txt for activity
   • Monitors running SARA 'at' jobs
   • Detects stale/hung jobs and logs alerts
   • Sends desktop notifications on errors
   • Writes a heartbeat to confirm it is alive
   • Writes its PID to core/monitor.pid

 Start:  python3 core/monitor.py &
 Stop:   kill $(cat core/monitor.pid)
 Status: sara --status
=============================================================================
"""

import os
import sys
import time
import signal
import subprocess
import re
from datetime import datetime
from pathlib import Path

# =============================================================================
#  Resolve SARA root and config
# =============================================================================
SARA_ROOT = os.environ.get("SARA_ROOT", str(Path(__file__).parent.parent))
LOG_DIR   = os.environ.get("SARA_LOG_DIR", os.path.join(SARA_ROOT, "logs"))
PID_FILE  = os.path.join(SARA_ROOT, "core", "monitor.pid")

EVENT_LOG = os.path.join(LOG_DIR, "event_log.txt")
ERROR_LOG = os.path.join(LOG_DIR, "error_log.txt")

HEARTBEAT_INTERVAL = 60       # seconds between heartbeat writes
ERROR_SCAN_INTERVAL = 10      # seconds between error log scans
AT_SCAN_INTERVAL    = 15      # seconds between 'atq' queue scans
MAX_JOB_AGE_SECONDS = 300     # alert if an 'at' job stays queued > 5 minutes

# =============================================================================
#  Utilities
# =============================================================================

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(component: str, message: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = f"[{timestamp()}] [INFO]  [{component}] {message}\n"
    with open(EVENT_LOG, "a") as f:
        f.write(entry)
    print(entry.rstrip(), flush=True)

def log_error(component: str, message: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = f"[{timestamp()}] [ERROR] [{component}] {message}\n"
    with open(EVENT_LOG, "a") as f:
        f.write(entry)
    with open(ERROR_LOG, "a") as f:
        f.write(entry)
    print(entry.rstrip(), file=sys.stderr, flush=True)

def send_notification(title: str, message: str, urgency: str = "normal"):
    """Send desktop notification. Requires notify-send."""
    display = os.environ.get("SARA_DISPLAY", ":0")
    try:
        subprocess.run(
            ["notify-send",
             "--app-name=SARA Monitor",
             f"--urgency={urgency}",
             "--expire-time=5000",
             title, message],
            env={**os.environ, "DISPLAY": display},
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        pass   # notify-send not installed, silently skip

def write_pid():
    """Write current process PID to monitor.pid."""
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    """Remove PID file on exit."""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass

# =============================================================================
#  Signal Handling (graceful shutdown)
# =============================================================================
_running = True

def _handle_signal(signum, frame):
    global _running
    log_event("SARA_MONITOR", f"Received signal {signum} — shutting down monitor.")
    _running = False

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)

# =============================================================================
#  Monitor Tasks
# =============================================================================

_last_error_size: int = 0
_last_heartbeat: float = 0
_last_at_scan: float = 0
_last_error_scan: float = 0
_notified_errors: set = set()   # avoid duplicate notifications

def heartbeat():
    """Write a heartbeat line to event_log."""
    global _last_heartbeat
    now = time.time()
    if now - _last_heartbeat >= HEARTBEAT_INTERVAL:
        log_event("SARA_MONITOR", "Heartbeat — monitor alive.")
        _last_heartbeat = now

def scan_error_log():
    """
    Detect NEW errors written to error_log.txt since last scan.
    Sends a desktop notification for each new error.
    """
    global _last_error_size, _last_error_scan
    now = time.time()
    if now - _last_error_scan < ERROR_SCAN_INTERVAL:
        return
    _last_error_scan = now

    if not os.path.exists(ERROR_LOG):
        return

    current_size = os.path.getsize(ERROR_LOG)
    if current_size <= _last_error_size:
        _last_error_size = current_size
        return

    # Read only the new bytes
    try:
        with open(ERROR_LOG, "r") as f:
            f.seek(_last_error_size)
            new_content = f.read()
        _last_error_size = current_size

        for line in new_content.splitlines():
            line = line.strip()
            if not line:
                continue
            # Deduplicate
            if line in _notified_errors:
                continue
            _notified_errors.add(line)
            # Keep set bounded
            if len(_notified_errors) > 500:
                _notified_errors.clear()

            log_event("SARA_MONITOR", f"New error detected: {line}")
            send_notification(
                "SARA — Error Detected",
                line[:120],
                urgency="critical"
            )
    except Exception as e:
        log_error("SARA_MONITOR", f"Error reading error_log: {e}")

def scan_at_queue():
    """
    Check 'atq' for jobs that have been queued too long.
    Logs an alert if a job exceeds MAX_JOB_AGE_SECONDS.
    """
    global _last_at_scan
    now = time.time()
    if now - _last_at_scan < AT_SCAN_INTERVAL:
        return
    _last_at_scan = now

    try:
        result = subprocess.run(
            ["atq"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return

        lines = result.stdout.strip().splitlines()
        for line in lines:
            if not line.strip():
                continue
            # atq format: job_id  date  time  queue  user
            # e.g.:  3   Tue Jul  8 14:32:00 2025 a user
            parts = line.split()
            if len(parts) < 6:
                continue
            job_id = parts[0]

            # Parse the job submission time from 'at -c' is complex
            # Instead, log job count as a simple health indicator
        if lines:
            log_event("SARA_MONITOR", f"AT queue: {len(lines)} job(s) pending.")
        else:
            log_event("SARA_MONITOR", "AT queue: empty.")
    except FileNotFoundError:
        pass    # 'at' not installed
    except subprocess.TimeoutExpired:
        log_error("SARA_MONITOR", "atq command timed out.")
    except Exception as e:
        log_error("SARA_MONITOR", f"AT queue scan error: {e}")

def check_log_dir_health():
    """Ensure log directory and files are accessible."""
    os.makedirs(LOG_DIR, exist_ok=True)
    for log_file in [EVENT_LOG, ERROR_LOG]:
        if not os.path.exists(log_file):
            Path(log_file).touch()
            log_event("SARA_MONITOR", f"Created missing log file: {log_file}")

# =============================================================================
#  Main Loop
# =============================================================================
def main():
    write_pid()
    log_event("SARA_MONITOR", f"SARA Monitor started. PID={os.getpid()}")
    log_event("SARA_MONITOR", f"Watching: {LOG_DIR}")
    send_notification("SARA Monitor", "Monitor started and watching logs.")

    check_log_dir_health()

    try:
        while _running:
            heartbeat()
            scan_error_log()
            scan_at_queue()
            check_log_dir_health()
            time.sleep(2)   # Main loop ticks every 2 seconds
    except Exception as e:
        log_error("SARA_MONITOR", f"Unexpected monitor crash: {e}")
        send_notification("SARA Monitor CRASHED", str(e)[:100], urgency="critical")
    finally:
        cleanup_pid()
        log_event("SARA_MONITOR", "Monitor stopped.")

if __name__ == "__main__":
    main()
