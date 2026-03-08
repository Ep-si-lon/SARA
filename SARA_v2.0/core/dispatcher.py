#!/usr/bin/env python3
"""
=============================================================================
 SARA  —  core/dispatcher.py
 Version 2.0  (No-AI, keyword/pattern matching + agent name from config)

 Reads the user's natural language command and maps it to ONE of the
 predefined high-level actions.

 Output to stdout (consumed by the sara bash wrapper):
     ACTION_NAME|EXTRACTED_QUERY

 On failure / no match:
     UNKNOWN|

 Exit codes:
     0  → successfully matched (even if UNKNOWN)
     1  → internal error
=============================================================================
"""

import sys
import re
import os
import urllib.parse
from pathlib import Path

# =============================================================================
#  Read AGENT_NAME from config/sara.conf
#  This makes the dispatcher work with any custom agent name.
# =============================================================================
def _read_agent_name() -> str:
    """Read AGENT_NAME from sara.conf. Falls back to SARA."""
    sara_root = os.environ.get("SARA_ROOT", str(Path(__file__).parent.parent))
    conf_path = os.path.join(sara_root, "config", "sara.conf")
    try:
        with open(conf_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("AGENT_NAME="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return val.upper() if val else "SARA"
    except Exception:
        pass
    return "SARA"

AGENT_NAME = _read_agent_name()

# =============================================================================
#  ACTION DEFINITIONS
#  Each entry is a dict:
#    "action"   : the name of the high-level script  (no .sh)
#    "patterns" : list of regex patterns to match
#    "query_extract": optional regex group name to pull a sub-query from input
# =============================================================================
ACTIONS = [

    # ── Agent Control ─────────────────────────────────────────────────────────
    # Patterns use AGENT_NAME so renaming the agent works automatically.
    # e.g. if renamed to JARVIS: "activate jarvis" / "jarvis stop" all work.
    {
        "action": "activate",
        "patterns": [
            rf"^activate\s+{AGENT_NAME.lower()}$",
            rf"^start\s+{AGENT_NAME.lower()}$",
            rf"^wake\s+(up\s+)?{AGENT_NAME.lower()}$",
            rf"^{AGENT_NAME.lower()}\s+(activate|start|wake\s+up)$",
            rf"^turn\s+on\s+{AGENT_NAME.lower()}$",
            rf"^enable\s+{AGENT_NAME.lower()}$",
            r"^activate$",   # bare "activate" with no name also works
        ],
        "default_query": "",
        "query_passthrough": False,
    },
    {
        "action": "stop",
        "patterns": [
            rf"^stop\s+{AGENT_NAME.lower()}$",
            rf"^{AGENT_NAME.lower()}\s+stop$",
            rf"^deactivate\s+{AGENT_NAME.lower()}$",
            rf"^turn\s+off\s+{AGENT_NAME.lower()}$",
            rf"^disable\s+{AGENT_NAME.lower()}$",
            rf"^shut\s+(down\s+)?{AGENT_NAME.lower()}$",
            r"^deactivate$",
        ],
        "default_query": "",
        "query_passthrough": False,
    },
    {
        "action": "restart",
        "patterns": [
            rf"^restart\s+{AGENT_NAME.lower()}$",
            rf"^{AGENT_NAME.lower()}\s+restart$",
            r"^restart$",
        ],
        "default_query": "",
        "query_passthrough": False,
    },
    {
        "action": "status",
        "patterns": [
            rf"^{AGENT_NAME.lower()}\s+status$",
            rf"^status\s+of\s+{AGENT_NAME.lower()}$",
            rf"^(is\s+)?{AGENT_NAME.lower()}\s+(running|active|alive|on)\??$",
        ],
        "default_query": "",
        "query_passthrough": False,
    },
    {
        "action": "voice-start",
        "patterns": [
            rf"^{AGENT_NAME.lower()}\s+(voice\s*(start|on|listen|activate))$",
            r"^voice\s*(start|on|listen)$",
            r"^start\s+listening$",
        ],
        "default_query": "",
        "query_passthrough": False,
    },
    {
        "action": "voice-stop",
        "patterns": [
            rf"^{AGENT_NAME.lower()}\s+(voice\s*(stop|off))$",
            r"^voice\s*(stop|off)$",
            r"^stop\s+listening$",
        ],
        "default_query": "",
        "query_passthrough": False,
    },

    # ── Play Song ─────────────────────────────────────────────────────────────
    {
        "action": "play_song",
        "patterns": [
            r"\bplay\b.*(song|music|track|audio|tune|lofi|lo-fi|jazz|rock|pop|classical|hip.?hop|playlist)",
            r"\bplay\b.*\bfor\s+me\b",
            r"\bplay\b.*(english|hindi|tamil|telugu|spanish|french|korean)\b.*\b(song|music)",
            r"\b(start|put\s+on|queue)\b.*(song|music|playlist|track)",
            r"\blisten\s+to\b",
            r"\bplay\s+some\b",
        ],
        "query_group": r"play\s+(?:some\s+|a\s+|an\s+)?(?:english\s+|hindi\s+|lofi\s+|lo-fi\s+|jazz\s+|rock\s+|pop\s+)?(song|music|playlist|track|tune|lofi|lo-fi|.*?\bsong|.*?\bmusic)",
        "default_query": "lofi songs",
        "query_passthrough": True,   # pass full command as query for song name
    },

    # ── Open YouTube ──────────────────────────────────────────────────────────
    {
        "action": "open_youtube",
        "patterns": [
            r"\bopen\b.*\byoutube\b",
            r"\blaunch\b.*\byoutube\b",
            r"\bgo\s+to\b.*\byoutube\b",
            r"\byoutube\b.*\bopen\b",
            r"\bstart\b.*\byoutube\b",
        ],
        "default_query": "",
        "query_passthrough": False,
    },

    # ── Search Google ─────────────────────────────────────────────────────────
    {
        "action": "search_google",
        "patterns": [
            r"\b(search|google|look\s+up|find|look\s+for)\b.*(google|on\s+the\s+web|on\s+internet|online)",
            r"\bgoogle\b.*(for\b|about\b|:)",
            r"\bsearch\s+(google\s+)?for\b",
            r"\bsearch\b.*(on\s+)?google",
            r"\bwhat\s+is\b.*(google|search)",
            r"\blook\s+up\b",
        ],
        "default_query": "",
        "query_passthrough": True,
    },

    # ── Open Spotify ──────────────────────────────────────────────────────────
    {
        "action": "open_spotify",
        "patterns": [
            r"\bopen\b.*\bspotify\b",
            r"\blaunch\b.*\bspotify\b",
            r"\bstart\b.*\bspotify\b",
            r"\bspotify\b.*\b(open|launch|start|play)\b",
            r"\bplay\b.*\bspotify\b",
        ],
        "default_query": "",
        "query_passthrough": False,
    },

    # ── Open Settings ─────────────────────────────────────────────────────────
    {
        "action": "open_settings",
        "patterns": [
            r"\bopen\b.*(setting|settings|preference|preferences|control\s+panel|system\s+config)",
            r"\blaunch\b.*(setting|settings|preference|preferences)",
            r"\bgo\s+to\b.*(setting|settings|preference|preferences)",
            r"\bsystem\s+settings\b",
            r"\bsettings\b.*\b(open|launch|show|go\s+to)\b",
        ],
        "default_query": "",
        "query_passthrough": False,
    },

    # ── Clean Trash ───────────────────────────────────────────────────────────
    {
        "action": "clean_trash",
        "patterns": [
            r"\b(clean|clear|empty|purge|delete|wipe)\b.*(trash|recycle\s+bin|bin|rubbish)",
            r"\b(trash|recycle\s+bin|bin)\b.*(clean|clear|empty|purge|delete)",
            r"\bempty\s+the\s+trash\b",
            r"\bclean\s+up\b.*\btrash\b",
            r"\bremove\b.*(trash|recycle\s+bin)",
            r"\bpermanently\s+delete\b",
        ],
        "default_query": "",
        "query_passthrough": False,
    },
]

# =============================================================================
#  Query Extraction
#  For actions that need a sub-query (e.g., song name, search term),
#  we attempt to extract the meaningful part of the user's command.
# =============================================================================

# Words to strip when extracting a search query
FILLER_PATTERNS = [
    r"^(sara|please|can\s+you|could\s+you|i\s+want\s+to|i\s+would\s+like\s+to|i'd\s+like\s+to)\s+",
    r"\s*(for\s+me\s*$)",
    r"^(play|search|google|find|look\s+up|open|launch|start)\s+(a|an|some|the)?\s*",
    r"^(search\s+google\s+for|search\s+for|google\s+for|look\s+up)\s+",
    r"\s*(on\s+google|on\s+youtube|on\s+the\s+web|on\s+the\s+internet|online)\s*$",
]

def clean_query(text: str) -> str:
    """Strip filler words and return a clean query string."""
    text = text.strip().lower()
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    return text.strip()

def extract_query(user_input: str, action_def: dict) -> str:
    """
    Extract the meaningful sub-query for actions that need one.
    For actions like play_song and search_google.
    """
    if not action_def.get("query_passthrough", False):
        return action_def.get("default_query", "")

    query = clean_query(user_input)

    # Specific extractions
    if action_def["action"] == "play_song":
        # Try to extract song name/genre
        # e.g., "play lofi songs" → "lofi songs"
        # e.g., "play an English song for me" → "English songs"
        song_match = re.search(
            r"play\s+(?:a\s+|an\s+|some\s+)?(.+?)(?:\s+for\s+me)?$",
            user_input.strip(),
            re.IGNORECASE
        )
        if song_match:
            raw = song_match.group(1).strip()
            # If it ends with just "song/songs" and has an adjective, keep it
            if raw.lower() in ("song", "songs", "music", "track"):
                return action_def.get("default_query", "songs")
            return raw
        return action_def.get("default_query", "songs")

    if action_def["action"] == "search_google":
        # Extract what comes after "search for", "google for", etc.
        search_match = re.search(
            r"(?:search\s+(?:google\s+)?for|google\s+for|look\s+up|find)\s+(.+?)$",
            user_input.strip(),
            re.IGNORECASE
        )
        if search_match:
            return search_match.group(1).strip()
        return query

    return query if query else action_def.get("default_query", "")

# =============================================================================
#  Main Dispatch Logic
# =============================================================================
def dispatch(user_input: str):
    """
    Match user_input against all action patterns.
    Returns (action_name, extracted_query) tuple.
    First match wins.
    """
    if not user_input or not user_input.strip():
        return ("UNKNOWN", "")

    text = user_input.strip()

    for action_def in ACTIONS:
        for pattern in action_def["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                query = extract_query(text, action_def)
                return (action_def["action"], query)

    return ("UNKNOWN", "")

# =============================================================================
#  Entry Point
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("UNKNOWN|", flush=True)
        sys.exit(0)

    user_command = " ".join(sys.argv[1:]).strip()

    try:
        action, query = dispatch(user_command)
        # Output format consumed by sara bash script: ACTION|QUERY
        print(f"{action}|{query}", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"Dispatcher internal error: {e}", file=sys.stderr)
        sys.exit(1)
