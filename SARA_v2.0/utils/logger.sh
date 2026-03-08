#!/usr/bin/env bash
# =============================================================================
#  SARA Logger Utility
#  utils/logger.sh
#
#  Provides:
#    sara_log_event  COMPONENT  "message"   → writes to event_log.txt
#    sara_log_error  COMPONENT  "message"   → writes to error_log.txt
#    sara_log_debug  COMPONENT  "message"   → writes to event_log.txt (DEBUG only)
# =============================================================================

# Ensure log dir exists (SARA_LOG_DIR must be set before sourcing this)
_sara_ensure_logs() {
    mkdir -p "${SARA_LOG_DIR:-/tmp/sara_logs}"
}

# ── Timestamp helper ──────────────────────────────────────────────────────────
_sara_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# ── Rotate log if it exceeds SARA_LOG_MAX_SIZE (KB) ──────────────────────────
_sara_rotate_log() {
    local log_file="$1"
    local max_kb="${SARA_LOG_MAX_SIZE:-1024}"
    if [[ -f "$log_file" ]]; then
        local size_kb
        size_kb=$(du -k "$log_file" 2>/dev/null | cut -f1)
        if (( size_kb > max_kb )); then
            mv "$log_file" "${log_file%.txt}_$(date +%Y%m%d_%H%M%S).bak"
            touch "$log_file"
        fi
    fi
}

# ── Event Log ─────────────────────────────────────────────────────────────────
sara_log_event() {
    local component="${1:-SARA}"
    local message="${2:-}"
    local log_dir="${SARA_LOG_DIR:-/tmp/sara_logs}"
    local log_file="$log_dir/event_log.txt"

    _sara_ensure_logs
    _sara_rotate_log "$log_file"

    local entry="[$(_sara_timestamp)] [INFO] [$component] $message"
    echo "$entry" >> "$log_file"

    # Also print to stdout if log level is DEBUG
    if [[ "${SARA_LOG_LEVEL:-INFO}" == "DEBUG" ]]; then
        echo "$entry"
    fi
}

# ── Error Log ─────────────────────────────────────────────────────────────────
sara_log_error() {
    local component="${1:-SARA}"
    local message="${2:-}"
    local log_dir="${SARA_LOG_DIR:-/tmp/sara_logs}"
    local event_log="$log_dir/event_log.txt"
    local error_log="$log_dir/error_log.txt"

    _sara_ensure_logs
    _sara_rotate_log "$error_log"

    local entry="[$(_sara_timestamp)] [ERROR] [$component] $message"

    # Write to both logs
    echo "$entry" >> "$event_log"
    echo "$entry" >> "$error_log"

    # Always print errors to stderr
    echo "$entry" >&2
}

# ── Warning Log ───────────────────────────────────────────────────────────────
sara_log_warn() {
    local component="${1:-SARA}"
    local message="${2:-}"
    local log_dir="${SARA_LOG_DIR:-/tmp/sara_logs}"
    local log_file="$log_dir/event_log.txt"

    _sara_ensure_logs

    local entry="[$(_sara_timestamp)] [WARN]  [$component] $message"
    echo "$entry" >> "$log_file"
    echo "$entry" >&2
}

# ── Debug Log ─────────────────────────────────────────────────────────────────
sara_log_debug() {
    if [[ "${SARA_LOG_LEVEL:-INFO}" != "DEBUG" ]]; then
        return 0
    fi
    local component="${1:-SARA}"
    local message="${2:-}"
    local log_dir="${SARA_LOG_DIR:-/tmp/sara_logs}"
    local log_file="$log_dir/event_log.txt"

    _sara_ensure_logs

    local entry="[$(_sara_timestamp)] [DEBUG] [$component] $message"
    echo "$entry" >> "$log_file"
    echo "$entry"
}

# ── Action separator (visual divider in log) ──────────────────────────────────
sara_log_separator() {
    local log_dir="${SARA_LOG_DIR:-/tmp/sara_logs}"
    local log_file="$log_dir/event_log.txt"
    _sara_ensure_logs
    echo "[$(_sara_timestamp)] ─────────────────────────────────────────────────────" >> "$log_file"
}
