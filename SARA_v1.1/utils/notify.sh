#!/usr/bin/env bash
# =============================================================================
#  SARA Notify Utility
#  utils/notify.sh
#
#  Wraps notify-send with SARA branding and fallback to echo.
#  Usage: sara_notify "Title" "Message"
# =============================================================================

sara_notify() {
    local title="${1:-SARA}"
    local message="${2:-}"
    local timeout="${SARA_NOTIFY_TIMEOUT:-4000}"
    local enabled="${SARA_NOTIFY_ENABLED:-true}"

    if [[ "$enabled" != "true" ]]; then
        return 0
    fi

    # Check if notify-send is available
    if command -v notify-send &>/dev/null; then
        # Try to use the correct DISPLAY/DBUS session
        local display="${SARA_DISPLAY:-:0}"

        # Find the user's DBUS session for notifications to work from scripts
        local dbus_addr
        dbus_addr=$(cat /proc/$(pgrep -u "$USER" gnome-session 2>/dev/null | head -1)/environ 2>/dev/null \
                    | tr '\0' '\n' \
                    | grep DBUS_SESSION_BUS_ADDRESS \
                    | cut -d= -f2- )

        if [[ -n "$dbus_addr" ]]; then
            DISPLAY="$display" DBUS_SESSION_BUS_ADDRESS="$dbus_addr" \
            notify-send \
                --app-name="SARA" \
                --expire-time="$timeout" \
                --icon=dialog-information \
                "$title" "$message" 2>/dev/null
        else
            DISPLAY="$display" \
            notify-send \
                --app-name="SARA" \
                --expire-time="$timeout" \
                --icon=dialog-information \
                "$title" "$message" 2>/dev/null
        fi
    else
        # Fallback: print to terminal
        echo "[SARA NOTIFY] $title: $message"
    fi
}

# ── Error notification ────────────────────────────────────────────────────────
sara_notify_error() {
    local title="${1:-SARA Error}"
    local message="${2:-}"
    local timeout="${SARA_NOTIFY_TIMEOUT:-4000}"

    if [[ "${SARA_NOTIFY_ENABLED:-true}" != "true" ]]; then return 0; fi

    if command -v notify-send &>/dev/null; then
        DISPLAY="${SARA_DISPLAY:-:0}" \
        notify-send \
            --app-name="SARA" \
            --expire-time="$timeout" \
            --urgency=critical \
            --icon=dialog-error \
            "$title" "$message" 2>/dev/null
    else
        echo "[SARA ERROR NOTIFY] $title: $message" >&2
    fi
}
