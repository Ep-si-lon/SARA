#!/usr/bin/env python3
"""
=============================================================================
 SARA  —  core/voice_listener.py
 Version 2.0

 VOICE LISTENER DAEMON
 ─────────────────────
 Runs as a background daemon. Continuously listens through the microphone.

 TWO-PHASE LISTENING:
   Phase 1 — IDLE      : Always listening for the wake word (AGENT_NAME)
   Phase 2 — ACTIVE    : Wake word heard → listen for the full command
                         → pass to sara CLI for dispatch

 SUPPORTED SPOKEN COMMANDS (after wake word):
   "<name> activate"          → sara activate
   "<name> deactivate/stop"   → sara stop
   "<name> restart"           → sara restart
   "<name> status"            → sara status
   "<name> play a lofi song"  → sara -"play a lofi song"
   "<name> open youtube"      → sara -"open youtube"
   "<name> <anything>"        → sara -"<anything>"

 ENGINES:
   vosk   → offline (recommended) — set SARA_VOICE_ENGINE=vosk
   google → online fallback       — set SARA_VOICE_ENGINE=google

 START:  python3 core/voice_listener.py
 STOP:   kill $(cat core/voice_listener.pid)
         OR:  sara voice-stop

 RELOAD (after rename): kill -HUP $(cat core/voice_listener.pid)
=============================================================================
"""

import os
import sys
import time
import signal
import subprocess
import threading
import json
import re
from datetime import datetime
from pathlib import Path

# ── Resolve SARA root ─────────────────────────────────────────────────────────
SARA_ROOT = os.environ.get("SARA_ROOT", str(Path(__file__).parent.parent))
LOG_DIR   = os.environ.get("SARA_LOG_DIR", os.path.join(SARA_ROOT, "logs"))
CONFIG    = os.path.join(SARA_ROOT, "config", "sara.conf")
SARA_BIN  = os.path.join(SARA_ROOT, "sara")

# ── PID file ──────────────────────────────────────────────────────────────────
PID_FILE  = os.path.join(SARA_ROOT, "core", "voice_listener.pid")

# =============================================================================
#  Configuration Reader
#  Reads sara.conf as key=value pairs (bash-style)
# =============================================================================
def read_conf() -> dict:
    """Parse sara.conf into a Python dict. Expands $SARA_ROOT."""
    conf = {}
    if not os.path.exists(CONFIG):
        return conf
    with open(CONFIG) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Expand $SARA_ROOT
                val = val.replace("$SARA_ROOT", SARA_ROOT)
                val = val.replace("${SARA_ROOT}", SARA_ROOT)
                conf[key] = val
    return conf

# =============================================================================
#  Logging
# =============================================================================
def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(level: str, msg: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    entry = f"[{ts()}] [{level}] [VOICE_LISTENER] {msg}"
    print(entry, flush=True)
    with open(os.path.join(LOG_DIR, "event_log.txt"), "a") as f:
        f.write(entry + "\n")
    if level == "ERROR":
        with open(os.path.join(LOG_DIR, "error_log.txt"), "a") as f:
            f.write(entry + "\n")

# =============================================================================
#  Text-to-Speech (optional feedback)
# =============================================================================
def speak(text: str, engine: str = "espeak"):
    """Speak text using TTS if enabled."""
    display = os.environ.get("SARA_DISPLAY", ":0")
    env = {**os.environ, "DISPLAY": display}
    try:
        if engine == "espeak":
            subprocess.run(["espeak", "-s", "150", text],
                           capture_output=True, env=env, timeout=5)
        elif engine == "festival":
            proc = subprocess.Popen(["festival", "--tts"],
                                    stdin=subprocess.PIPE, env=env)
            proc.communicate(input=text.encode(), timeout=5)
    except Exception:
        pass   # TTS is optional — never crash for it

# =============================================================================
#  Beep Feedback
# =============================================================================
def beep():
    """Play a short activation beep."""
    # Try paplay first (PulseAudio), then aplay (ALSA), then speaker-test
    try:
        # Generate a short 800Hz beep using paplay with /dev/stdin
        # Most reliable: use python to generate and pipe to aplay
        subprocess.run(
            ["python3", "-c",
             "import os; "
             "rate=44100; freq=800; dur=0.15; "
             "import struct, math; "
             "samples=[int(32767*math.sin(2*math.pi*freq*i/rate)) for i in range(int(rate*dur))]; "
             "data=struct.pack('<' + 'h'*len(samples), *samples); "
             "import subprocess; "
             "p=subprocess.Popen(['aplay','-r','44100','-f','S16_LE','-c','1','-'], stdin=subprocess.PIPE); "
             "p.communicate(data)"],
            capture_output=True, timeout=2
        )
    except Exception:
        pass

# =============================================================================
#  Desktop Notification
# =============================================================================
def notify(title: str, message: str, urgency: str = "normal"):
    display = os.environ.get("SARA_DISPLAY", ":0")
    try:
        subprocess.run(
            ["notify-send", "--app-name=SARA Voice",
             f"--urgency={urgency}", "--expire-time=3000", title, message],
            env={**os.environ, "DISPLAY": display},
            capture_output=True, timeout=3
        )
    except Exception:
        pass

# =============================================================================
#  Wake Word Detection
# =============================================================================
def contains_wake_word(text: str, agent_name: str, sensitivity: float) -> bool:
    """
    Check if spoken text contains the agent's name (wake word).
    Uses fuzzy matching because speech recognition isn't perfect:
      - Exact match (case insensitive)
      - Soundex-like: first letter + length proximity
      - Common mishearings (e.g. "sarah" → "sara")
    """
    if not text:
        return False

    text_lower = text.lower().strip()
    wake_lower = agent_name.lower()

    # ── Exact match ───────────────────────────────────────────────────────────
    if wake_lower in text_lower:
        return True

    # ── Word-boundary match (handles "sara," "sara." etc) ─────────────────────
    words = re.findall(r'\b\w+\b', text_lower)
    if wake_lower in words:
        return True

    # ── Fuzzy match for common mishearings ────────────────────────────────────
    # If sensitivity < 1.0, allow approximate matches
    if sensitivity < 1.0:
        for word in words:
            if len(word) >= 3 and len(wake_lower) >= 3:
                # First letter must match
                if word[0] != wake_lower[0]:
                    continue
                # Length must be within ±1
                if abs(len(word) - len(wake_lower)) > 1:
                    continue
                # Matching characters ratio
                common = sum(1 for a, b in zip(word, wake_lower) if a == b)
                ratio = common / max(len(word), len(wake_lower))
                if ratio >= sensitivity:
                    log("DEBUG", f"Fuzzy wake word match: '{word}' ~ '{wake_lower}' (ratio={ratio:.2f})")
                    return True

    return False

# =============================================================================
#  Command Extraction
#  Remove the wake word from the beginning of the spoken command
# =============================================================================
def extract_command(text: str, agent_name: str) -> str:
    """
    Given "SARA play a lofi song", return "play a lofi song".
    Strips the agent name from the start (case insensitive).
    """
    text = text.strip()
    pattern = rf'^\s*{re.escape(agent_name)}\s*'
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    # Remove leading punctuation like commas
    cleaned = cleaned.lstrip(',. ').strip()
    return cleaned

# =============================================================================
#  Command Dispatch
#  Sends the extracted command to the sara CLI
# =============================================================================
def dispatch_command(command: str, agent_name: str):
    """
    Route the voice command to the sara entrypoint.
    Control commands are passed directly; everything else via -"..."
    """
    if not command:
        log("WARN", "Empty command after wake word — ignoring.")
        return

    command_lower = command.lower().strip()
    log("INFO", f"Dispatching voice command: '{command}'")

    # ── Control commands (handled directly, no quotes needed) ─────────────────
    control_map = {
        # activate patterns
        r'\b(activate|start|wake\s*up|turn\s*on|enable)\b': "activate",
        # deactivate patterns
        r'\b(deactivate|stop|turn\s*off|disable|shut\s*down)\b': "stop",
        # restart
        r'\brestart\b': "restart",
        # status
        r'\b(status|are\s*you\s*(running|active|alive|on))\b': "status",
        # stop voice specifically
        r'\b(stop\s*(listening|voice)|voice\s*off)\b': "voice-stop",
    }

    for pattern, sara_cmd in control_map.items():
        if re.search(pattern, command_lower):
            log("INFO", f"Control command: sara {sara_cmd}")
            run_sara(sara_cmd)
            return

    # ── Regular task command — wrap in quotes and pass to dispatcher ──────────
    run_sara(f'-"{command}"')

def run_sara(args: str):
    """Execute the sara CLI with the given arguments."""
    env = {**os.environ, "SARA_ROOT": SARA_ROOT,
           "SARA_LOG_DIR": LOG_DIR, "DISPLAY": os.environ.get("SARA_DISPLAY", ":0")}
    cmd = f'bash "{SARA_BIN}" {args}'
    log("INFO", f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, env=env, capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            log("INFO", f"sara output: {result.stdout.strip()}")
        if result.returncode != 0 and result.stderr:
            log("ERROR", f"sara error: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        log("ERROR", "sara command timed out after 30s")
    except Exception as e:
        log("ERROR", f"Failed to run sara: {e}")

# =============================================================================
#  VOSK Engine  (offline)
# =============================================================================
class VoskListener:
    """
    Uses Vosk for fully offline speech recognition.
    Install:  pip install vosk
    Model:    https://alphacephei.com/vosk/models
    """

    def __init__(self, model_path: str, sample_rate: int = 16000):
        try:
            from vosk import Model, KaldiRecognizer
        except ImportError:
            raise ImportError(
                "Vosk not installed. Run: pip install vosk\n"
                "Then download a model from https://alphacephei.com/vosk/models"
            )

        if not os.path.isdir(model_path):
            raise FileNotFoundError(
                f"Vosk model not found at: {model_path}\n"
                f"Download from https://alphacephei.com/vosk/models and set\n"
                f"SARA_VOSK_MODEL_PATH in config/sara.conf"
            )

        log("INFO", f"Loading Vosk model: {model_path}")
        self.model = Model(model_path)
        self.sample_rate = sample_rate
        self.rec = KaldiRecognizer(self.model, sample_rate)
        log("INFO", "Vosk model loaded.")

    def transcribe_audio_data(self, audio_bytes: bytes) -> str:
        """Transcribe raw PCM bytes. Returns text or empty string."""
        self.rec.AcceptWaveform(audio_bytes)
        result = json.loads(self.rec.FinalResult())
        return result.get("text", "").strip()

    def transcribe_partial(self, audio_bytes: bytes) -> str:
        """Get partial result while audio is still coming in."""
        if self.rec.AcceptWaveform(audio_bytes):
            result = json.loads(self.rec.Result())
        else:
            result = json.loads(self.rec.PartialResult())
        return result.get("partial", result.get("text", "")).strip()

# =============================================================================
#  Google Engine  (online fallback)
# =============================================================================
class GoogleListener:
    """
    Uses Google Speech Recognition via the speech_recognition library.
    Install:  pip install SpeechRecognition
    Requires internet connection.
    """

    def __init__(self):
        try:
            import speech_recognition as sr
            self.sr = sr
            self.recognizer = sr.Recognizer()
            log("INFO", "Google Speech Recognition engine ready.")
        except ImportError:
            raise ImportError(
                "SpeechRecognition not installed. Run: pip install SpeechRecognition"
            )

    def transcribe_audio(self, audio) -> str:
        """Transcribe a speech_recognition AudioData object."""
        try:
            text = self.recognizer.recognize_google(audio)
            return text.strip()
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as e:
            log("ERROR", f"Google Speech API error: {e}")
            return ""

# =============================================================================
#  Main Voice Listener
# =============================================================================
class VoiceListener:
    """
    Orchestrates microphone input, wake word detection, and command dispatch.
    Supports hot-reload of agent name via SIGHUP.
    """

    def __init__(self):
        self.running = False
        self.conf = {}
        self.agent_name = "SARA"
        self.engine_name = "vosk"
        self.vosk_engine = None
        self.google_engine = None

        # Install signal handlers
        signal.signal(signal.SIGTERM, self._handle_stop)
        signal.signal(signal.SIGINT,  self._handle_stop)
        signal.signal(signal.SIGHUP,  self._handle_reload)  # reload on rename

    # ── Config ────────────────────────────────────────────────────────────────
    def load_config(self):
        self.conf = read_conf()
        self.agent_name = self.conf.get("AGENT_NAME", "SARA").upper()
        self.engine_name = self.conf.get("SARA_VOICE_ENGINE", "vosk").lower()
        self.vosk_model_path = self.conf.get("SARA_VOSK_MODEL_PATH",
                               os.path.join(SARA_ROOT, "models", "vosk-model"))
        self.energy_threshold = int(self.conf.get("SARA_MIC_ENERGY_THRESHOLD", "300"))
        self.auto_adjust      = self.conf.get("SARA_MIC_AUTO_ADJUST", "true").lower() == "true"
        self.command_timeout  = int(self.conf.get("SARA_VOICE_COMMAND_TIMEOUT", "5"))
        self.phrase_timeout   = float(self.conf.get("SARA_VOICE_PHRASE_TIMEOUT", "1"))
        self.beep_enabled     = self.conf.get("SARA_VOICE_BEEP", "true").lower() == "true"
        self.speak_back       = self.conf.get("SARA_VOICE_SPEAK_BACK", "false").lower() == "true"
        self.tts_engine       = self.conf.get("SARA_TTS_ENGINE", "espeak")
        self.sensitivity      = float(self.conf.get("SARA_WAKE_WORD_SENSITIVITY", "0.6"))
        log("INFO", f"Config loaded. Agent name: '{self.agent_name}' | Engine: {self.engine_name}")

    # ── Engine Init ───────────────────────────────────────────────────────────
    def init_engine(self):
        if self.engine_name == "vosk":
            try:
                self.vosk_engine = VoskListener(self.vosk_model_path)
            except (ImportError, FileNotFoundError) as e:
                log("WARN", f"Vosk unavailable: {e}")
                log("WARN", "Falling back to Google engine.")
                self.engine_name = "google"

        if self.engine_name == "google" or self.vosk_engine is None:
            try:
                self.google_engine = GoogleListener()
                self.engine_name = "google"
            except ImportError as e:
                log("ERROR", f"No speech engine available: {e}")
                log("ERROR", "Install vosk: pip install vosk")
                log("ERROR", "Or install SpeechRecognition: pip install SpeechRecognition pyaudio")
                sys.exit(1)

    # ── Signal Handlers ───────────────────────────────────────────────────────
    def _handle_stop(self, signum, frame):
        log("INFO", f"Signal {signum} received — stopping voice listener.")
        self.running = False

    def _handle_reload(self, signum, frame):
        """SIGHUP: reload config (pick up new agent name after rename)."""
        log("INFO", "SIGHUP received — reloading configuration.")
        old_name = self.agent_name
        self.load_config()
        if self.agent_name != old_name:
            log("INFO", f"Agent name changed: '{old_name}' → '{self.agent_name}'")
            notify(f"Agent renamed", f"Now listening for: {self.agent_name}")

    # ── PID Management ────────────────────────────────────────────────────────
    def write_pid(self):
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

    def remove_pid(self):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    # ── Main Loop (VOSK path) ─────────────────────────────────────────────────
    def run_vosk_loop(self):
        """
        Vosk loop: reads raw microphone PCM, detects wake word in real-time,
        then switches to command-listening mode.
        """
        try:
            import pyaudio
        except ImportError:
            log("ERROR", "pyaudio not installed. Run: pip install pyaudio")
            sys.exit(1)

        CHUNK       = 4096
        SAMPLE_RATE = 16000

        pa      = pyaudio.PyAudio()
        stream  = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        log("INFO", f"Microphone open. Listening for wake word: '{self.agent_name}'")
        notify("SARA Voice", f"Listening for wake word: {self.agent_name} 🎤")

        # Separate recognizer for command phase (fresh state)
        from vosk import KaldiRecognizer
        wake_rec    = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)
        command_rec = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)

        state = "IDLE"    # IDLE | COMMAND
        command_frames = []
        command_start  = 0.0

        while self.running:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                log("WARN", f"Mic read error: {e}")
                time.sleep(0.1)
                continue

            if state == "IDLE":
                # ── Phase 1: Listen for wake word ─────────────────────────────
                if wake_rec.AcceptWaveform(data):
                    result = json.loads(wake_rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        log("DEBUG", f"[IDLE] Heard: '{text}'")
                    if text and contains_wake_word(text, self.agent_name, self.sensitivity):
                        log("INFO", f"Wake word detected in: '{text}'")
                        self._on_wake_word_detected()
                        state = "COMMAND"
                        command_frames = []
                        command_start  = time.time()
                        command_rec    = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)
                else:
                    partial = json.loads(wake_rec.PartialResult()).get("partial", "")
                    if partial and contains_wake_word(partial, self.agent_name, self.sensitivity):
                        log("INFO", f"Wake word in partial: '{partial}'")
                        self._on_wake_word_detected()
                        state = "COMMAND"
                        command_frames = []
                        command_start  = time.time()
                        command_rec    = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)

            elif state == "COMMAND":
                # ── Phase 2: Capture the command ──────────────────────────────
                elapsed = time.time() - command_start

                if elapsed > self.command_timeout:
                    # Time's up — transcribe what we got
                    command_rec.AcceptWaveform(data)
                    final = json.loads(command_rec.FinalResult()).get("text", "").strip()
                    log("INFO", f"[COMMAND] Final (timeout): '{final}'")
                    if final:
                        command = extract_command(final, self.agent_name)
                        if command:
                            dispatch_command(command, self.agent_name)
                    state = "IDLE"
                    wake_rec = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)
                else:
                    if command_rec.AcceptWaveform(data):
                        result = json.loads(command_rec.Result())
                        text = result.get("text", "").strip()
                        log("INFO", f"[COMMAND] Phrase complete: '{text}'")
                        if text:
                            command = extract_command(text, self.agent_name)
                            if command:
                                dispatch_command(command, self.agent_name)
                        state = "IDLE"
                        wake_rec = KaldiRecognizer(self.vosk_engine.model, SAMPLE_RATE)

        stream.stop_stream()
        stream.close()
        pa.terminate()
        log("INFO", "Vosk microphone loop stopped.")

    # ── Main Loop (Google path) ───────────────────────────────────────────────
    def run_google_loop(self):
        """
        Google loop: uses speech_recognition's listen() for higher-level
        audio capture and sends to Google STT API.
        """
        try:
            import speech_recognition as sr
        except ImportError:
            log("ERROR", "SpeechRecognition not installed: pip install SpeechRecognition pyaudio")
            sys.exit(1)

        recognizer = self.google_engine.recognizer
        recognizer.energy_threshold = self.energy_threshold
        recognizer.dynamic_energy_threshold = self.auto_adjust
        recognizer.pause_threshold = self.phrase_timeout

        log("INFO", f"Microphone open (Google engine). Listening for: '{self.agent_name}'")
        notify("SARA Voice", f"Listening for wake word: {self.agent_name} 🎤")

        with sr.Microphone() as source:
            if self.auto_adjust:
                log("INFO", "Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                log("INFO", f"Energy threshold set to: {recognizer.energy_threshold:.0f}")

            while self.running:
                # ── Phase 1: Listen for anything ──────────────────────────────
                try:
                    log("DEBUG", "Listening (idle)...")
                    audio = recognizer.listen(
                        source,
                        timeout=None,
                        phrase_time_limit=4
                    )
                except Exception as e:
                    log("WARN", f"Listen error: {e}")
                    time.sleep(0.2)
                    continue

                # ── Transcribe phase 1 ────────────────────────────────────────
                text = self.google_engine.transcribe_audio(audio)
                if not text:
                    continue

                log("DEBUG", f"[IDLE] Heard: '{text}'")

                if not contains_wake_word(text, self.agent_name, self.sensitivity):
                    continue

                # ── Wake word detected ────────────────────────────────────────
                log("INFO", f"Wake word detected: '{text}'")

                # Check if command is already in the same utterance
                inline_command = extract_command(text, self.agent_name)
                if inline_command:
                    log("INFO", f"Inline command: '{inline_command}'")
                    self._on_wake_word_detected()
                    dispatch_command(inline_command, self.agent_name)
                    continue

                # ── Phase 2: Listen for command ───────────────────────────────
                self._on_wake_word_detected()
                log("INFO", f"Listening for command (timeout={self.command_timeout}s)...")

                try:
                    audio2 = recognizer.listen(
                        source,
                        timeout=self.command_timeout,
                        phrase_time_limit=self.command_timeout
                    )
                    command_text = self.google_engine.transcribe_audio(audio2)
                    log("INFO", f"[COMMAND] Heard: '{command_text}'")
                    if command_text:
                        command = extract_command(command_text, self.agent_name)
                        if command:
                            dispatch_command(command, self.agent_name)
                        else:
                            dispatch_command(command_text, self.agent_name)
                except sr.WaitTimeoutError:
                    log("WARN", "Command timeout — no command heard after wake word.")
                    notify(self.agent_name, "I didn't catch that. Please try again.")
                except Exception as e:
                    log("ERROR", f"Command listen error: {e}")

    # ── Wake Word Feedback ────────────────────────────────────────────────────
    def _on_wake_word_detected(self):
        """Feedback when wake word is heard."""
        log("INFO", "Wake word activated — listening for command...")
        notify(self.agent_name, "Listening... 🎤")
        if self.beep_enabled:
            threading.Thread(target=beep, daemon=True).start()
        if self.speak_back:
            threading.Thread(
                target=speak,
                args=(f"Yes?", self.tts_engine),
                daemon=True
            ).start()

    # ── Start ─────────────────────────────────────────────────────────────────
    def start(self):
        self.write_pid()
        self.running = True
        self.load_config()
        self.init_engine()

        log("INFO", f"Voice listener started. PID={os.getpid()}")
        log("INFO", f"Wake word : '{self.agent_name}'")
        log("INFO", f"Engine    : {self.engine_name}")
        log("INFO", f"Timeout   : {self.command_timeout}s after wake word")

        try:
            if self.engine_name == "vosk" and self.vosk_engine:
                self.run_vosk_loop()
            else:
                self.run_google_loop()
        except KeyboardInterrupt:
            log("INFO", "Keyboard interrupt received.")
        except Exception as e:
            log("ERROR", f"Voice listener crashed: {e}")
            import traceback
            log("ERROR", traceback.format_exc())
        finally:
            self.remove_pid()
            log("INFO", "Voice listener stopped.")

# =============================================================================
#  Entry Point
# =============================================================================
if __name__ == "__main__":
    listener = VoiceListener()
    listener.start()
