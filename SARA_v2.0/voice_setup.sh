#!/usr/bin/env bash
# =============================================================================
#  SARA v2.0  —  voice_setup.sh
#
#  One-time setup for the voice listener.
#  Downloads the Vosk speech model and installs Python dependencies.
#
#  Usage:
#    bash voice_setup.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SARA_ROOT="${SARA_ROOT:-$(cd "$SCRIPT_DIR" && pwd)}"
MODELS_DIR="$SARA_ROOT/models"

echo ""
echo "  SARA v2.0 — Voice Setup"
echo "  ─────────────────────────────────────────────"
echo ""

# ── Step 1: Install Python packages ──────────────────────────────────────────
echo "[1/3] Installing Python voice packages..."

pip3 install vosk --quiet 2>/dev/null && echo "  ✓ vosk" || echo "  ✗ vosk (try: pip3 install vosk)"
pip3 install SpeechRecognition --quiet 2>/dev/null && echo "  ✓ SpeechRecognition" || echo "  ✗ SpeechRecognition"
pip3 install pyaudio --quiet 2>/dev/null && echo "  ✓ pyaudio" || {
    echo "  ✗ pyaudio — trying system package..."
    sudo apt-get install -y python3-pyaudio portaudio19-dev 2>/dev/null && echo "  ✓ pyaudio (system)" || echo "  ✗ pyaudio (install portaudio19-dev manually)"
}

# ── Step 2: Download Vosk model ───────────────────────────────────────────────
echo ""
echo "[2/3] Downloading Vosk speech model (small English ~40MB)..."
echo "  This is a one-time download."
echo ""

mkdir -p "$MODELS_DIR"

MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"
MODEL_ZIP="$MODELS_DIR/${MODEL_NAME}.zip"
MODEL_DIR="$MODELS_DIR/vosk-model"

if [[ -d "$MODEL_DIR" ]]; then
    echo "  ✓ Model already exists at: $MODEL_DIR"
else
    echo "  Downloading from: $MODEL_URL"

    if command -v wget &>/dev/null; then
        wget -q --show-progress -O "$MODEL_ZIP" "$MODEL_URL"
    elif command -v curl &>/dev/null; then
        curl -L --progress-bar -o "$MODEL_ZIP" "$MODEL_URL"
    else
        echo "  ✗ Neither wget nor curl found. Install one and re-run."
        exit 1
    fi

    if [[ ! -f "$MODEL_ZIP" ]]; then
        echo "  ✗ Download failed. Check your internet connection."
        exit 1
    fi

    echo "  Extracting model..."
    cd "$MODELS_DIR"
    unzip -q "$MODEL_ZIP"

    # Rename to standard name
    if [[ -d "$MODEL_NAME" ]]; then
        mv "$MODEL_NAME" "vosk-model"
        echo "  ✓ Model ready at: $MODEL_DIR"
    else
        echo "  ✗ Extraction failed — check $MODELS_DIR"
        exit 1
    fi

    rm -f "$MODEL_ZIP"
fi

# ── Step 3: Verify microphone ─────────────────────────────────────────────────
echo ""
echo "[3/3] Checking microphone..."

python3 - << 'PYEOF'
import sys
try:
    import pyaudio
    pa = pyaudio.PyAudio()
    count = pa.get_device_count()
    mics = []
    for i in range(count):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels', 0) > 0:
            mics.append(f"  [{i}] {info['name']}")
    pa.terminate()
    if mics:
        print("  ✓ Microphones found:")
        for m in mics:
            print(m)
    else:
        print("  ✗ No microphone detected. Plug in a mic and re-run.")
        sys.exit(1)
except ImportError:
    print("  ✗ pyaudio not installed — microphone check skipped")
except Exception as e:
    print(f"  ✗ Microphone error: {e}")
PYEOF

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────────"
echo "  ✓ Voice setup complete!"
echo ""
echo "  Start voice listener:  sara voice-start"
echo "  Stop voice listener:   sara voice-stop"
echo "  Check status:          sara voice-status"
echo ""
echo "  Default wake word:     SARA"
echo "  Change it:             sara rename \"JARVIS\""
echo ""
echo "  To auto-start voice with 'sara activate', edit config:"
echo "    SARA_VOICE_AUTO_START=\"true\"  in config/sara.conf"
echo ""
