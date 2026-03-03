# SARA — System Automation & Response Agent
## Version 1.0

```
  ███████╗ █████╗ ██████╗  █████╗ 
  ██╔════╝██╔══██╗██╔══██╗██╔══██╗
  ███████╗███████║██████╔╝███████║
  ╚════██║██╔══██║██╔══██╗██╔══██║
  ███████║██║  ██║██║  ██║██║  ██║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

SARA is a Linux desktop automation agent you control via plain English
commands in your terminal.

---

## Quick Start

```bash
# Install
bash install.sh

# Use
sara -"Play a lofi song"
sara -"Open YouTube"
sara -"Search Google for Python tutorials"
sara -"Open Spotify"
sara -"Open Settings"
sara -"Clean the trash"

# Help
sara --help
sara --list
sara --logs
sara --errors
sara --status
```

---

## Architecture

```
┌──────────────────────────────────────────────┐
│             USER  (CLI Terminal)             │
│   $ sara -"Play an English song for me"      │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│           sara  (Bash Entrypoint)            │
│  • Parses the command string                 │
│  • Calls dispatcher → validator → scheduler  │
│  • Logs every step                           │
└──────┬───────────────────────┬───────────────┘
       │                       │
       ▼                       ▼
┌─────────────┐      ┌─────────────────────────┐
│ dispatcher  │      │       validator          │
│  (Python)   │      │       (Python)           │
│             │      │                          │
│ Keyword /   │      │ Scans action script for: │
│ regex match │      │ • Dangerous patterns     │
│ → selects   │      │ • World-writable files   │
│   action    │      │ • Bad shebangs           │
│             │      │ • sudo misuse            │
└──────┬──────┘      └──────────┬───────────────┘
       │                        │ PASS
       ▼                        ▼
┌──────────────────────────────────────────────┐
│           AT (Scheduler)                     │
│  Queues the high-level action for immediate  │
│  non-overlapping execution.                  │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│      HIGH-LEVEL ACTION SCRIPT  (.sh)         │
│                                              │
│  play_song.sh      open_youtube.sh           │
│  search_google.sh  open_spotify.sh           │
│  open_settings.sh  clean_trash.sh            │
│                                              │
│  Each script uses:                           │
│  • xdg-open  → open URLs/apps               │
│  • xdotool   → window focus/raise           │
│  • notify-send → user notifications         │
│  • logger.sh → event_log + error_log        │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│      LOW-LEVEL ATOMIC ACTIONS  (Python)      │
│                                              │
│  mouse_click.py   mouse_move.py              │
│  type_text.py     key_press.py               │
│  scroll.py        screenshot.py              │
│                                              │
│  Backend: PyAutoGUI (primary)                │
│           xdotool  (fallback)                │
└──────────────────────────────────────────────┘

          ↕  All layers ↕
┌──────────────────────────────────────────────┐
│        MONITOR  (Background Python daemon)   │
│                                              │
│  • Runs as background process                │
│  • Scans error_log for new errors            │
│  • Sends desktop notification on error       │
│  • Writes heartbeat every 60s               │
│  • Watches AT job queue                      │
│  • PID stored in core/monitor.pid            │
│  • Kept alive by cron (every 2 min)          │
└──────────────────────────────────────────────┘
```

---

## File Structure

```
SARA/
├── sara                          ← Main CLI entry point
├── install.sh                    ← One-time setup
├── config/
│   └── sara.conf                 ← All configuration
├── core/
│   ├── dispatcher.py             ← Maps English → action name
│   ├── validator.py              ← Security scanner
│   ├── monitor.py                ← Background daemon
│   ├── scheduler.sh              ← Cron job manager
│   └── monitor.pid               ← Auto-created at runtime
├── actions/
│   ├── low_level/                ← Atomic GUI primitives
│   │   ├── mouse_click.py
│   │   ├── mouse_move.py
│   │   ├── type_text.py
│   │   ├── key_press.py
│   │   ├── scroll.py
│   │   └── screenshot.py
│   └── high_level/               ← Full tasks
│       ├── play_song.sh
│       ├── open_youtube.sh
│       ├── search_google.sh
│       ├── open_spotify.sh
│       ├── open_settings.sh
│       └── clean_trash.sh
├── utils/
│   ├── logger.sh                 ← Logging functions
│   └── notify.sh                 ← notify-send wrapper
└── logs/
    ├── event_log.txt             ← All activity
    └── error_log.txt             ← Errors only
```

---

## Dependencies

| Tool | Purpose | Required |
|------|---------|----------|
| `python3` | Dispatcher, validator, low-level actions | ✅ Required |
| `xdg-open` | Open URLs and apps | ✅ Required |
| `xdotool` | Window focus, GUI control | Recommended |
| `notify-send` | Desktop notifications | Recommended |
| `at` | Non-overlapping job scheduling | Recommended |
| `cron` | Monitor watchdog | Recommended |
| `pyautogui` | GUI automation (pip) | Optional |
| `pynput` | Input monitoring (pip) | Optional |

### Install all at once (Ubuntu/Debian):
```bash
sudo apt install xdotool libnotify-bin at cron xdg-utils python3
pip3 install pyautogui pynput
```

---

## How Actions Are Selected (V1)

SARA V1 uses **pure regex keyword matching** — no AI. The dispatcher
(`core/dispatcher.py`) has a dictionary of patterns for each action.
First match wins.

Example matches:
| Command | Action selected |
|---------|----------------|
| `"Play a lofi song"` | `play_song` |
| `"Play an English song for me"` | `play_song` |
| `"Open YouTube"` | `open_youtube` |
| `"Search Google for Python tips"` | `search_google` |
| `"Launch Spotify"` | `open_spotify` |
| `"Open system settings"` | `open_settings` |
| `"Empty the trash"` | `clean_trash` |
| `"Clean the recycle bin"` | `clean_trash` |

---

## Security Model

Every action script passes through `core/validator.py` before execution:

- Blocks `rm -rf /`, `mkfs`, `dd if=`, fork bombs
- Blocks writing to `/etc/passwd`, `/etc/shadow`, `/boot`
- Blocks `curl | sh` / `wget | sh` remote exec patterns
- Blocks `sudo` in action scripts
- Blocks world-writable action scripts (tamper detection)
- Validates shebang is a known safe interpreter
- Restricts scripts to SARA's own `actions/` directory

---

## Logging

| File | Contents |
|------|---------|
| `logs/event_log.txt` | Timestamped record of every SARA action |
| `logs/error_log.txt` | Errors only (subset of event_log) |

```bash
sara --logs     # live tail
sara --errors   # recent errors
```

---

## Extending SARA (Adding New Actions)

1. Create `actions/high_level/my_action.sh`
2. Add patterns to `core/dispatcher.py` ACTIONS list
3. Test: `sara -"trigger phrase"`

Low-level actions are already available as building blocks inside any
high-level script:

```bash
python3 "$SARA_ACTIONS_LOW/mouse_click.py" 960 540
python3 "$SARA_ACTIONS_LOW/type_text.py" "hello world"
python3 "$SARA_ACTIONS_LOW/key_press.py" enter
python3 "$SARA_ACTIONS_LOW/key_press.py" --combo ctrl+t
python3 "$SARA_ACTIONS_LOW/scroll.py" down 3
```

---

## Roadmap

| Version | Features |
|---------|---------|
| **V1** (current) | CLI, predefined actions, keyword dispatch, logging, validator |
| **V2** | AI-powered dispatcher (local LLM), SARA writes its own action scripts |
| **V3** | Voice input, GUI tray, plugin system, scheduled tasks |
