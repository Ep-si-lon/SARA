#!/usr/bin/env bash
# =============================================================================
#  SARA  —  install.sh
#
#  One-time setup script:
#    1. Makes all scripts executable
#    2. Creates the log directory
#    3. Symlinks the 'sara' command to /usr/local/bin (or ~/.local/bin)
#    4. Checks for required dependencies
#    5. Starts the monitor
#    6. Optionally installs cron jobs
# =============================================================================

SARA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SARA_ROOT

echo ""
echo "  ███████╗ █████╗ ██████╗  █████╗ "
echo "  ██╔════╝██╔══██╗██╔══██╗██╔══██╗"
echo "  ███████╗███████║██████╔╝███████║"
echo "  ╚════██║██╔══██║██╔══██╗██╔══██║"
echo "  ███████║██║  ██║██║  ██║██║  ██║"
echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝"
echo "  Installer  v1.0"
echo ""

# ── Step 1: File permissions ──────────────────────────────────────────────────
echo "[1/6] Setting file permissions..."
chmod +x "$SARA_ROOT/sara"
chmod +x "$SARA_ROOT/core/"*.sh "$SARA_ROOT/core/"*.py 2>/dev/null
chmod +x "$SARA_ROOT/actions/high_level/"*.sh 2>/dev/null
chmod +x "$SARA_ROOT/actions/low_level/"*.py 2>/dev/null
chmod +x "$SARA_ROOT/utils/"*.sh 2>/dev/null
# Protect config from world-write
chmod 640 "$SARA_ROOT/config/sara.conf" 2>/dev/null
echo "    ✓ Done."

# ── Step 2: Create log directory ──────────────────────────────────────────────
echo "[2/6] Creating log directory..."
mkdir -p "$SARA_ROOT/logs"
touch "$SARA_ROOT/logs/event_log.txt"
touch "$SARA_ROOT/logs/error_log.txt"
echo "    ✓ Logs: $SARA_ROOT/logs/"

# ── Step 3: Symlink sara binary ───────────────────────────────────────────────
echo "[3/6] Creating 'sara' command..."
INSTALL_DIR=""

# Prefer /usr/local/bin if writable
if [[ -d "/usr/local/bin" && -w "/usr/local/bin" ]]; then
    INSTALL_DIR="/usr/local/bin"
elif [[ -d "$HOME/.local/bin" ]]; then
    INSTALL_DIR="$HOME/.local/bin"
    export PATH="$HOME/.local/bin:$PATH"
else
    mkdir -p "$HOME/.local/bin"
    INSTALL_DIR="$HOME/.local/bin"
fi

# Add SARA_ROOT export wrapper so subprocesses inherit it
WRAPPER="$INSTALL_DIR/sara"
cat > "$WRAPPER" << EOF
#!/usr/bin/env bash
export SARA_ROOT="$SARA_ROOT"
exec bash "$SARA_ROOT/sara" "\$@"
EOF
chmod +x "$WRAPPER"
echo "    ✓ Installed to: $WRAPPER"

if ! command -v sara &>/dev/null; then
    echo "    ⚠  '$INSTALL_DIR' may not be in your PATH."
    echo "    Add this to your ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
fi

# ── Step 4: Dependency check ──────────────────────────────────────────────────
echo "[4/6] Checking dependencies..."

check_dep() {
    local name="$1"
    local cmd="$2"
    local required="${3:-optional}"
    if command -v "$cmd" &>/dev/null; then
        echo "    ✓ $name"
    else
        if [[ "$required" == "required" ]]; then
            echo "    ✗ $name (REQUIRED — install with: $4)"
        else
            echo "    ⚠  $name (optional, some features limited)"
        fi
    fi
}

check_dep "Python 3"      "python3"      required   "sudo apt install python3"
check_dep "xdg-open"      "xdg-open"     required   "sudo apt install xdg-utils"
check_dep "notify-send"   "notify-send"  optional
check_dep "xdotool"       "xdotool"      optional
check_dep "at"            "at"           optional
check_dep "cron"          "cron"         optional

# Python packages
echo "    Checking Python packages..."
python3 -c "import pyautogui" 2>/dev/null && echo "    ✓ pyautogui" || echo "    ⚠  pyautogui (optional: pip3 install pyautogui)"
python3 -c "import pynput" 2>/dev/null && echo "    ✓ pynput" || echo "    ⚠  pynput (optional: pip3 install pynput)"

# ── Step 5: Start monitor ─────────────────────────────────────────────────────
echo "[5/6] Starting SARA monitor..."
export SARA_LOG_DIR="$SARA_ROOT/logs"

if python3 "$SARA_ROOT/core/monitor.py" &>/dev/null & then
    sleep 1
    if [[ -f "$SARA_ROOT/core/monitor.pid" ]]; then
        echo "    ✓ Monitor running (PID: $(cat "$SARA_ROOT/core/monitor.pid"))"
    else
        echo "    ⚠  Monitor started but PID file not found (may still be starting)"
    fi
else
    echo "    ⚠  Could not start monitor. Run manually: python3 $SARA_ROOT/core/monitor.py &"
fi

# ── Step 6: Install cron jobs ─────────────────────────────────────────────────
echo "[6/6] Setting up cron jobs..."
if command -v crontab &>/dev/null; then
    bash "$SARA_ROOT/core/scheduler.sh" install
else
    echo "    ⚠  crontab not found. Skipping cron setup."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ════════════════════════════════════════"
echo "   SARA v1.1 installed successfully!"
echo "  ════════════════════════════════════════"
echo ""
echo "  Try it:"
echo "    sara -\"Play a lofi song\""
echo "    sara -\"Open YouTube\""
echo "    sara -\"Search Google for Linux tips\""
echo "    sara -\"Open Spotify\""
echo "    sara -\"Open Settings\""
echo "    sara -\"Clean the trash\""
echo ""
echo "  Help:   sara --help"
echo "  Logs:   sara --logs"
echo "  Status: sara --status"
echo ""
