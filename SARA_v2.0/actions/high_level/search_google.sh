#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/search_google.sh
#
#  Searches Google for the given query in the default browser.
#
#  Flow:
#    1.  URL-encode the query
#    2.  Open Google search URL in default browser
#    3.  Focus the browser window
#    4.  Log and notify
#
#  Usage:
#    bash search_google.sh "Python tutorials"
#    bash search_google.sh "best coffee shops in Howrah"
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="search_google"
QUERY="${1:-}"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting — query: \"$QUERY\""

# ── Validate query ────────────────────────────────────────────────────────────
if [[ -z "$QUERY" ]]; then
    sara_log_error "$ACTION_NAME" "No query provided."
    echo "[search_google] ERROR: No query to search for."
    exit 1
fi

# ── URL-encode ────────────────────────────────────────────────────────────────
ENCODED=$(python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")
SEARCH_URL="${SARA_GOOGLE_SEARCH_URL:-https://www.google.com/search?q=}${ENCODED}"

sara_log_event "$ACTION_NAME" "Search URL: $SEARCH_URL"
sara_notify "SARA — Google Search" "Searching for: $QUERY"

# ── Open browser ──────────────────────────────────────────────────────────────
export DISPLAY="${SARA_DISPLAY:-:0}"
"${SARA_BROWSER:-xdg-open}" "$SEARCH_URL" &
BROWSER_PID=$!
sara_log_event "$ACTION_NAME" "Browser launched (PID: $BROWSER_PID)"

# ── Wait and focus ────────────────────────────────────────────────────────────
sleep "${SARA_WINDOW_OPEN_DELAY:-2}"

if command -v xdotool &>/dev/null; then
    for WM_NAME in "Google" "Firefox" "Chrome" "Chromium" "Brave"; do
        WIN_ID=$(xdotool search --name "$WM_NAME" 2>/dev/null | head -1)
        if [[ -n "$WIN_ID" ]]; then
            xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
            xdotool windowraise "$WIN_ID" 2>/dev/null
            sara_log_event "$ACTION_NAME" "Window focused: $WM_NAME"
            break
        fi
    done
fi

sara_log_event "$ACTION_NAME" "Action completed — Google search: \"$QUERY\""
sara_notify "SARA" "Google results loaded for: $QUERY"
echo "[search_google] Done — searched for: $QUERY"
exit 0
