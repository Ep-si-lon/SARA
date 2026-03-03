#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/open_youtube.sh
#
#  Opens YouTube in the default browser.
#
#  Flow:
#    1.  Open YouTube homepage in default browser
#    2.  Wait for window, optionally focus it
#    3.  Log and notify
#
#  Usage:
#    bash open_youtube.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="open_youtube"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting — opening YouTube homepage"

# ── Open YouTube ──────────────────────────────────────────────────────────────
YT_URL="${SARA_YOUTUBE_URL:-https://www.youtube.com}"
sara_notify "SARA" "Opening YouTube..."

export DISPLAY="${SARA_DISPLAY:-:0}"
"${SARA_BROWSER:-xdg-open}" "$YT_URL" &
BROWSER_PID=$!

sara_log_event "$ACTION_NAME" "Browser launched (PID: $BROWSER_PID) → $YT_URL"

# ── Wait and focus ────────────────────────────────────────────────────────────
sleep "${SARA_WINDOW_OPEN_DELAY:-2}"

if command -v xdotool &>/dev/null; then
    for WM_NAME in "YouTube" "Firefox" "Chrome" "Chromium" "Brave"; do
        WIN_ID=$(xdotool search --name "$WM_NAME" 2>/dev/null | head -1)
        if [[ -n "$WIN_ID" ]]; then
            xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
            xdotool windowraise "$WIN_ID" 2>/dev/null
            sara_log_event "$ACTION_NAME" "Window focused: $WM_NAME"
            break
        fi
    done
fi

sara_log_event "$ACTION_NAME" "Action completed — YouTube opened"
sara_notify "SARA" "YouTube is open ▶"
echo "[open_youtube] Done."
exit 0
