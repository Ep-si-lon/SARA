#!/usr/bin/env bash
# =============================================================================
#  SARA High-Level Action  —  actions/high_level/clean_trash.sh
#
#  Permanently empties the Linux Trash (XDG Trash directory).
#
#  Flow:
#    1.  Count files in Trash for logging
#    2.  Show a desktop confirmation notification
#    3.  Delete all files/folders in:
#          ~/.local/share/Trash/files/
#          ~/.local/share/Trash/info/
#          ~/.local/share/Trash/expunged/   (if exists)
#    4.  Also try gio trash --empty (GNOME integration) as a secondary pass
#    5.  Log and notify result
#
#  NOTE: This action does NOT require sudo. It only touches the user's own Trash.
#        The validator will block any attempt to use rm -rf / which is why
#        this script uses targeted paths only.
#
#  Usage:
#    bash clean_trash.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
source "$SARA_ROOT/config/sara.conf"
source "$SARA_ROOT/utils/logger.sh"
source "$SARA_ROOT/utils/notify.sh"

ACTION_NAME="clean_trash"

sara_log_separator
sara_log_event "$ACTION_NAME" "Starting"

# ── Resolve trash paths ───────────────────────────────────────────────────────
TRASH_BASE="${SARA_TRASH_DIR:-$HOME/.local/share/Trash}"
TRASH_FILES="$TRASH_BASE/files"
TRASH_INFO="$TRASH_BASE/info"
TRASH_EXPUNGED="$TRASH_BASE/expunged"

sara_log_event "$ACTION_NAME" "Trash base: $TRASH_BASE"

# ── Count items before deletion ───────────────────────────────────────────────
FILE_COUNT=0
if [[ -d "$TRASH_FILES" ]]; then
    FILE_COUNT=$(find "$TRASH_FILES" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
fi
INFO_COUNT=0
if [[ -d "$TRASH_INFO" ]]; then
    INFO_COUNT=$(find "$TRASH_INFO" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
fi

sara_log_event "$ACTION_NAME" "Items found: $FILE_COUNT file(s), $INFO_COUNT info(s)"

if [[ "$FILE_COUNT" -eq 0 && "$INFO_COUNT" -eq 0 ]]; then
    sara_log_event "$ACTION_NAME" "Trash is already empty."
    sara_notify "SARA" "Trash is already empty 🗑"
    echo "[clean_trash] Trash was already empty."
    exit 0
fi

# ── Notify before deletion ────────────────────────────────────────────────────
sara_notify "SARA" "Emptying Trash ($FILE_COUNT items)..."
sara_log_event "$ACTION_NAME" "Proceeding to empty trash..."

# ── Delete trash/files contents ───────────────────────────────────────────────
ERRORS=0

if [[ -d "$TRASH_FILES" ]]; then
    find "$TRASH_FILES" -mindepth 1 -delete 2>/tmp/sara_trash_err
    if [[ $? -ne 0 ]]; then
        sara_log_error "$ACTION_NAME" "Error deleting trash files: $(cat /tmp/sara_trash_err)"
        ERRORS=$((ERRORS+1))
    else
        sara_log_event "$ACTION_NAME" "trash/files emptied"
    fi
fi

# ── Delete trash/info contents ────────────────────────────────────────────────
if [[ -d "$TRASH_INFO" ]]; then
    find "$TRASH_INFO" -mindepth 1 -delete 2>/tmp/sara_trash_err
    if [[ $? -ne 0 ]]; then
        sara_log_error "$ACTION_NAME" "Error deleting trash info: $(cat /tmp/sara_trash_err)"
        ERRORS=$((ERRORS+1))
    else
        sara_log_event "$ACTION_NAME" "trash/info emptied"
    fi
fi

# ── Delete expunged if present ────────────────────────────────────────────────
if [[ -d "$TRASH_EXPUNGED" ]]; then
    find "$TRASH_EXPUNGED" -mindepth 1 -delete 2>/dev/null
    sara_log_event "$ACTION_NAME" "trash/expunged cleared"
fi

# ── Secondary pass: gio trash --empty (handles GNOME virtual mounts) ──────────
if command -v gio &>/dev/null; then
    gio trash --empty 2>/dev/null
    sara_log_event "$ACTION_NAME" "gio trash --empty executed"
elif command -v gvfs-trash &>/dev/null; then
    gvfs-trash --empty 2>/dev/null
    sara_log_event "$ACTION_NAME" "gvfs-trash --empty executed"
fi

# ── Final verify ──────────────────────────────────────────────────────────────
REMAINING=0
if [[ -d "$TRASH_FILES" ]]; then
    REMAINING=$(find "$TRASH_FILES" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
fi

if [[ "$REMAINING" -eq 0 ]]; then
    sara_log_event "$ACTION_NAME" "Trash successfully emptied. Deleted $FILE_COUNT item(s)."
    sara_notify "SARA" "Trash emptied! $FILE_COUNT item(s) permanently deleted 🗑✓"
    echo "[clean_trash] Done — permanently deleted $FILE_COUNT item(s) from Trash."
    exit 0
else
    sara_log_error "$ACTION_NAME" "$REMAINING item(s) still remain in trash after deletion attempt."
    sara_notify "SARA Error" "Some items could not be deleted from Trash."
    echo "[clean_trash] WARNING: $REMAINING item(s) could not be removed."
    exit 1
fi
