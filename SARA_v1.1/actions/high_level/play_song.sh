#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/play_song.sh
#
#  Plays a song by searching YouTube in the default browser.
#
#  Flow:
#    1.  URL-encode the query
#    2.  Open YouTube search URL directly (fastest, no GUI clicks needed)
#    3.  Send desktop notification
#    4.  Log the action
#
#  Usage (called by sara wrapper):
#    bash play_song.sh "lofi songs"
#    bash play_song.sh "English pop songs 2024"
# =============================================================================

# ── Bootstrap ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="play_song"
QUERY="${1:-lofi songs}"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting — query: \"$QUERY\""

# ── Step 1: URL-encode the query ──────────────────────────────────────────────
# python3 is always available; handles all Unicode correctly
ENCODED_QUERY=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")

if [[ -z "$ENCODED_QUERY" ]]; then
    sara_log_error "$ACTION_NAME" "Failed to URL-encode query: $QUERY"
    exit 1
fi

sara_log_event "$ACTION_NAME" "Encoded query: $ENCODED_QUERY"

# ── Step 2: Build YouTube search URL ─────────────────────────────────────────
YT_URL="${SARA_YOUTUBE_SEARCH_URL}${ENCODED_QUERY}"
sara_log_event "$ACTION_NAME" "YouTube URL: $YT_URL"

# ── Step 3: Open the URL in the default browser ───────────────────────────────
sara_log_event "$ACTION_NAME" "Opening browser..."
sara_notify "SARA — Playing Music" "Searching YouTube for: $QUERY"

export DISPLAY="${SARA_DISPLAY:-:0}"
"${SARA_BROWSER:-xdg-open}" "$YT_URL" &
BROWSER_PID=$!

sara_log_event "$ACTION_NAME" "Browser launched (PID: $BROWSER_PID)"

# ── Step 4: Wait for browser window to open ───────────────────────────────────
WAIT="${SARA_WINDOW_OPEN_DELAY:-2}"
sara_log_event "$ACTION_NAME" "Waiting ${WAIT}s for browser to open..."
sleep "$WAIT"

# ── Step 5: (Optional) Auto-click first result using xdotool ─────────────────
# Find the YouTube window and press Enter/Return to confirm search
# This is best-effort; skip gracefully if xdotool isn't available.
if command -v xdotool &>/dev/null; then
    sara_log_event "$ACTION_NAME" "Attempting to focus browser window via xdotool..."
    # Give xdotool a moment to find the window
    sleep 1

    # Search for a browser window by common names
    for WM_NAME in "YouTube" "Firefox" "Chrome" "Chromium" "Brave"; do
        WIN_ID=$(xdotool search --name "$WM_NAME" 2>/dev/null | head -1)
        if [[ -n "$WIN_ID" ]]; then
            xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
            sara_log_event "$ACTION_NAME" "Focused window: $WM_NAME (ID: $WIN_ID)"
            break
        fi
    done
else
    sara_log_event "$ACTION_NAME" "xdotool not found — skipping window focus."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
sara_log_event "$ACTION_NAME" "Action completed — playing: \"$QUERY\""
sara_notify "SARA" "Now searching: $QUERY on YouTube 🎵"
echo "[play_song] Done — opened YouTube search for: $QUERY"
exit 0
