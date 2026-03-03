#!/usr/bin/env bash
# =============================================================================
#  SARA  —  core/scheduler.sh
#
#  Manages cron jobs for SARA:
#    • Keeps the monitor alive (restart if crashed)
#    • Weekly log rotation check
#
#  Usage:
#    bash scheduler.sh install    → add SARA cron jobs
#    bash scheduler.sh remove     → remove SARA cron jobs
#    bash scheduler.sh status     → show current SARA cron jobs
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

MONITOR_SCRIPT="$SARA_ROOT/core/monitor.py"
PID_FILE="$SARA_ROOT/core/monitor.pid"
LOG_DIR="$SARA_ROOT/logs"

# The cron job marker comment
CRON_MARKER="# SARA_MANAGED"

# ── Install cron jobs ─────────────────────────────────────────────────────────
install_cron() {
    echo "[SARA Scheduler] Installing cron jobs..."

    # Ensure SARA_ROOT is available to cron environment
    EXPORT_LINE="SARA_ROOT=$SARA_ROOT"

    # Job 1: Check every 2 minutes if monitor is running; restart if not
    MONITOR_JOB="*/2 * * * * pgrep -f 'monitor.py' > /dev/null || (export SARA_ROOT=$SARA_ROOT; python3 $MONITOR_SCRIPT >> $LOG_DIR/event_log.txt 2>&1 &) $CRON_MARKER"

    # Job 2: Weekly log rotation at Sunday 00:05
    LOGROTATE_JOB="5 0 * * 0 find $LOG_DIR -name '*.bak' -mtime +30 -delete >> $LOG_DIR/event_log.txt 2>&1 $CRON_MARKER"

    # Get current crontab (excluding SARA lines)
    CURRENT_CRON=$(crontab -l 2>/dev/null | grep -v "$CRON_MARKER")

    # Write new crontab
    (
        echo "$CURRENT_CRON"
        echo ""
        echo "# ── SARA Automation Agent ────────────────────────────────"
        echo "$MONITOR_JOB"
        echo "$LOGROTATE_JOB"
        echo "# ──────────────────────────────────────────────────────────"
    ) | crontab -

    if [[ $? -eq 0 ]]; then
        echo "[SARA Scheduler] ✓ Cron jobs installed."
        echo ""
        echo "  • Monitor watchdog: every 2 minutes"
        echo "  • Log cleanup:      every Sunday 00:05"
    else
        echo "[SARA Scheduler] ERROR: Failed to install cron jobs."
        exit 1
    fi
}

# ── Remove cron jobs ──────────────────────────────────────────────────────────
remove_cron() {
    echo "[SARA Scheduler] Removing SARA cron jobs..."
    CURRENT_CRON=$(crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | grep -v "SARA Automation Agent" | grep -v "^# ──")
    echo "$CURRENT_CRON" | crontab -
    echo "[SARA Scheduler] ✓ SARA cron jobs removed."
}

# ── Show status ───────────────────────────────────────────────────────────────
show_status() {
    echo "[SARA Scheduler] Current SARA cron jobs:"
    echo "─────────────────────────────────────────────"
    crontab -l 2>/dev/null | grep "$CRON_MARKER" || echo "  No SARA cron jobs found."
    echo "─────────────────────────────────────────────"
}

# ── Entry ─────────────────────────────────────────────────────────────────────
case "${1:-status}" in
    install)  install_cron ;;
    remove)   remove_cron  ;;
    status)   show_status  ;;
    *)
        echo "Usage: scheduler.sh [install|remove|status]"
        exit 1
        ;;
esac
