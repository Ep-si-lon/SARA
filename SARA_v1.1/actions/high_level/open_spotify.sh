#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/open_spotify.sh
#
#  Opens Spotify — checks for local install first, falls back to web.
#
#  Flow:
#    1.  Check if Spotify desktop binary exists (which spotify / flatpak / snap)
#    2.  If found locally → launch it directly
#    3.  If NOT found    → open Spotify web in default browser
#    4.  Log and notify either way
#
#  Usage:
#    bash open_spotify.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="open_spotify"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting — looking for Spotify"

export DISPLAY="${SARA_DISPLAY:-:0}"

# ── Step 1: Check all known Spotify install locations ────────────────────────
SPOTIFY_BIN="${SARA_SPOTIFY_BIN:-spotify}"
SPOTIFY_FOUND=""
LAUNCH_METHOD=""

# 1a. Check PATH (e.g., native .deb install)
if command -v "$SPOTIFY_BIN" &>/dev/null; then
    SPOTIFY_FOUND=$(command -v "$SPOTIFY_BIN")
    LAUNCH_METHOD="native"
    sara_log_event "$ACTION_NAME" "Found Spotify in PATH: $SPOTIFY_FOUND"
fi

# 1b. Check Flatpak
if [[ -z "$SPOTIFY_FOUND" ]] && command -v flatpak &>/dev/null; then
    if flatpak list 2>/dev/null | grep -qi "spotify"; then
        SPOTIFY_FOUND="flatpak"
        LAUNCH_METHOD="flatpak"
        sara_log_event "$ACTION_NAME" "Found Spotify via Flatpak"
    fi
fi

# 1c. Check Snap
if [[ -z "$SPOTIFY_FOUND" ]] && command -v snap &>/dev/null; then
    if snap list 2>/dev/null | grep -qi "spotify"; then
        SPOTIFY_FOUND="snap"
        LAUNCH_METHOD="snap"
        sara_log_event "$ACTION_NAME" "Found Spotify via Snap"
    fi
fi

# 1d. Common manual install paths
COMMON_PATHS=(
    "/usr/bin/spotify"
    "/usr/local/bin/spotify"
    "$HOME/.local/bin/spotify"
    "$HOME/spotify/spotify"
)
if [[ -z "$SPOTIFY_FOUND" ]]; then
    for p in "${COMMON_PATHS[@]}"; do
        if [[ -x "$p" ]]; then
            SPOTIFY_FOUND="$p"
            LAUNCH_METHOD="native"
            sara_log_event "$ACTION_NAME" "Found Spotify at: $p"
            break
        fi
    done
fi

# ── Step 2: Launch or fall back ───────────────────────────────────────────────
if [[ -n "$SPOTIFY_FOUND" ]]; then
    sara_log_event "$ACTION_NAME" "Launching local Spotify via $LAUNCH_METHOD"
    sara_notify "SARA" "Opening Spotify 🎵"

    case "$LAUNCH_METHOD" in
        flatpak)
            flatpak run com.spotify.Client &>/dev/null &
            ;;
        snap)
            snap run spotify &>/dev/null &
            ;;
        native|*)
            "$SPOTIFY_FOUND" &>/dev/null &
            ;;
    esac

    SPOTIFY_PID=$!
    sara_log_event "$ACTION_NAME" "Spotify launched (PID: $SPOTIFY_PID)"

    # Wait for window to appear
    sleep "${SARA_WINDOW_OPEN_DELAY:-2}"

    if command -v xdotool &>/dev/null; then
        WIN_ID=$(xdotool search --name "Spotify" 2>/dev/null | head -1)
        if [[ -n "$WIN_ID" ]]; then
            xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
            xdotool windowraise "$WIN_ID" 2>/dev/null
            sara_log_event "$ACTION_NAME" "Spotify window focused (ID: $WIN_ID)"
        fi
    fi

    sara_notify "SARA" "Spotify is open!"
    echo "[open_spotify] Done — local Spotify opened."

else
    # ── Fallback: Open Spotify Web ────────────────────────────────────────────
    sara_log_event "$ACTION_NAME" "Spotify not found locally — opening web player"
    sara_notify "SARA" "Spotify not installed — opening web player..."

    WEB_URL="${SARA_SPOTIFY_WEB_URL:-https://open.spotify.com}"
    "${SARA_BROWSER:-xdg-open}" "$WEB_URL" &
    BROWSER_PID=$!
    sara_log_event "$ACTION_NAME" "Browser launched (PID: $BROWSER_PID) → $WEB_URL"

    sleep "${SARA_WINDOW_OPEN_DELAY:-2}"

    if command -v xdotool &>/dev/null; then
        for WM_NAME in "Spotify" "Firefox" "Chrome" "Chromium" "Brave"; do
            WIN_ID=$(xdotool search --name "$WM_NAME" 2>/dev/null | head -1)
            if [[ -n "$WIN_ID" ]]; then
                xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
                sara_log_event "$ACTION_NAME" "Focused: $WM_NAME"
                break
            fi
        done
    fi

    sara_notify "SARA" "Spotify Web opened 🌐"
    echo "[open_spotify] Done — web player opened (local not found)."
fi

sara_log_event "$ACTION_NAME" "Action completed."
exit 0
