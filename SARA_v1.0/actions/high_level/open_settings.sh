#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/open_settings.sh
#
#  Opens the system settings panel for the current desktop environment.
#
#  Supports: GNOME, KDE Plasma, XFCE, LXDE/LXQt, MATE, Cinnamon, generic
#
#  Flow:
#    1.  Detect current desktop environment
#    2.  Launch the appropriate settings app
#    3.  Log and notify
#
#  Usage:
#    bash open_settings.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="open_settings"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting"

export DISPLAY="${SARA_DISPLAY:-:0}"

# ── Detect Desktop Environment ────────────────────────────────────────────────
DE="${XDG_CURRENT_DESKTOP:-}"
DE_LOWER=$(echo "$DE" | tr '[:upper:]' '[:lower:]')

sara_log_event "$ACTION_NAME" "Detected DE: $DE (XDG_CURRENT_DESKTOP=$XDG_CURRENT_DESKTOP)"

# ── Launch appropriate settings app ──────────────────────────────────────────
launch_settings() {
    local app="$1"
    local label="$2"
    sara_log_event "$ACTION_NAME" "Launching $label: $app"
    sara_notify "SARA" "Opening Settings..."
    $app &>/dev/null &
    local PID=$!
    sara_log_event "$ACTION_NAME" "$label launched (PID: $PID)"

    sleep "${SARA_WINDOW_OPEN_DELAY:-2}"

    if command -v xdotool &>/dev/null; then
        for WM_NAME in "Settings" "System Settings" "Control Panel" "Preferences" "GNOME Settings"; do
            WIN_ID=$(xdotool search --name "$WM_NAME" 2>/dev/null | head -1)
            if [[ -n "$WIN_ID" ]]; then
                xdotool windowfocus --sync "$WIN_ID" 2>/dev/null
                xdotool windowraise "$WIN_ID" 2>/dev/null
                sara_log_event "$ACTION_NAME" "Window focused: $WM_NAME"
                break
            fi
        done
    fi
    return 0
}

# Priority order: check specific DE, then fall back to generic
LAUNCHED=false

# ── GNOME ──────────────────────────────────────────────────────────────────
if echo "$DE_LOWER" | grep -q "gnome" || command -v gnome-control-center &>/dev/null; then
    launch_settings "gnome-control-center" "GNOME Settings"
    LAUNCHED=true

# ── KDE Plasma ─────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "kde" || command -v systemsettings5 &>/dev/null; then
    if command -v systemsettings5 &>/dev/null; then
        launch_settings "systemsettings5" "KDE System Settings"
    else
        launch_settings "systemsettings" "KDE System Settings"
    fi
    LAUNCHED=true

# ── XFCE ────────────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "xfce" || command -v xfce4-settings-manager &>/dev/null; then
    launch_settings "xfce4-settings-manager" "XFCE Settings Manager"
    LAUNCHED=true

# ── MATE ────────────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "mate" || command -v mate-control-center &>/dev/null; then
    launch_settings "mate-control-center" "MATE Control Center"
    LAUNCHED=true

# ── Cinnamon ─────────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "cinnamon" || command -v cinnamon-settings &>/dev/null; then
    launch_settings "cinnamon-settings" "Cinnamon Settings"
    LAUNCHED=true

# ── LXQt ─────────────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "lxqt" || command -v lxqt-config &>/dev/null; then
    launch_settings "lxqt-config" "LXQt Configuration"
    LAUNCHED=true

# ── LXDE ─────────────────────────────────────────────────────────────────────
elif echo "$DE_LOWER" | grep -q "lxde" || command -v lxappearance &>/dev/null; then
    launch_settings "lxappearance" "LXDE Appearance"
    LAUNCHED=true

# ── Generic fallback: try common settings commands ────────────────────────────
else
    sara_log_event "$ACTION_NAME" "Unknown DE. Trying generic settings apps..."
    for SETTINGS_APP in \
        "gnome-control-center" \
        "systemsettings5" \
        "systemsettings" \
        "xfce4-settings-manager" \
        "mate-control-center" \
        "cinnamon-settings" \
        "unity-control-center"; do
        if command -v "$SETTINGS_APP" &>/dev/null; then
            launch_settings "$SETTINGS_APP" "System Settings"
            LAUNCHED=true
            break
        fi
    done
fi

if [[ "$LAUNCHED" != "true" ]]; then
    sara_log_error "$ACTION_NAME" "No known settings application found."
    sara_notify "SARA Error" "Cannot find a settings application."
    echo "[open_settings] ERROR: No settings app found."
    exit 1
fi

sara_log_event "$ACTION_NAME" "Action completed."
sara_notify "SARA" "Settings opened ⚙"
echo "[open_settings] Done."
exit 0
