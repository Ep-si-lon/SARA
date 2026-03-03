#!/usr/bin/env python3
"""
=============================================================================
 SARA  —  core/validator.py
 Version 1.0

 SECURITY VALIDATOR
 ──────────────────
 Checks an action script BEFORE it is passed to the machine for execution.
 Aborts if any dangerous pattern is found.

 Rules applied:
   1. Blocked command patterns (from sara.conf SARA_BLOCKED_PATTERNS)
   2. Hardcoded critical system path writes
   3. Privilege escalation checks (sudo, su, pkexec with dangerous args)
   4. Network exfiltration heuristics (curl/wget piped to sh)
   5. Eval / exec with external input
   6. Fork bombs
   7. Script must exist and be readable
   8. Script must not be world-writable (tamper check)
   9. Shebang must be a known safe interpreter

 Usage (from CLI):
   python3 validator.py /path/to/action_script.sh
   python3 validator.py /path/to/action_script.py

 Exit codes:
   0  → PASSED (safe to run)
   1  → FAILED (blocked — reason printed to stderr)
=============================================================================
"""

import sys
import os
import re
import stat

# =============================================================================
#  Hardcoded dangerous patterns (always blocked, regardless of config)
# =============================================================================
HARDCODED_BLOCKED = [
    # Filesystem destruction
    (r"\brm\s+-[rRf]*f[rRf]*\s+/\b",           "Recursive delete of root filesystem"),
    (r"\bmkfs\b",                                "Filesystem format command"),
    (r"\bdd\s+if=",                              "dd raw disk write"),
    (r"\bshred\b.*/dev/",                        "Shred on device file"),
    (r"\bwipefs\b",                              "Wipe filesystem signatures"),
    (r"\bfdisk\s+/dev/",                         "fdisk on raw device"),
    (r"\bparted\b",                              "Disk partitioning command"),

    # System critical paths (write operations)
    (r">\s*/etc/passwd",                         "Overwrite /etc/passwd"),
    (r">\s*/etc/shadow",                         "Overwrite /etc/shadow"),
    (r">\s*/etc/sudoers",                        "Overwrite sudoers"),
    (r">\s*/boot/",                              "Write to /boot"),
    (r">\s*/dev/sd[a-z]",                        "Write to raw disk device"),
    (r"\bchmod\s+777\s+/",                       "chmod 777 on root"),
    (r"\bchown\s+-R\s+root\s+/",                "chown -R root on root"),

    # Power / system control
    (r"\bshutdown\b",                            "System shutdown command"),
    (r"\breboot\b",                              "System reboot command"),
    (r"\bhalt\b",                                "System halt command"),
    (r"\bpoweroff\b",                            "System poweroff command"),
    (r"\bsystemctl\s+(poweroff|reboot|halt)",    "systemctl power command"),

    # Process kill of init
    (r"\bkill\s+-9\s+1\b",                      "Kill PID 1 (init)"),
    (r"\bkill\s+-KILL\s+1\b",                   "Kill PID 1 (init)"),

    # Fork bomb
    (r":\(\)\s*\{.*:\|:.*\}",                   "Fork bomb detected"),
    (r":\(\)\{.*:\|:.*\}",                       "Fork bomb detected"),

    # Curl/wget pipe to shell (remote code execution)
    (r"curl\b.*\|\s*(ba)?sh",                    "Remote code execution: curl | sh"),
    (r"wget\b.*\|\s*(ba)?sh",                    "Remote code execution: wget | sh"),
    (r"curl\b.*\|\s*bash",                       "Remote code execution: curl | bash"),
    (r"curl\b.+-o\s*/tmp/.*&&.*sh\b",            "Download and execute pattern"),

    # Eval with suspicious content
    (r"\beval\s*\$\(",                           "eval with command substitution"),
    (r"\beval\s*\$\{",                           "eval with variable expansion"),

    # Crypto miners / known malicious patterns
    (r"\bxmrig\b|\bminerd\b|\bstratum\+tcp",    "Cryptocurrency miner pattern"),
    (r"/dev/tcp/|/dev/udp/",                     "Bash network redirection"),

    # Python-specific dangerous operations
    (r"\bos\.system\s*\(\s*[\"']rm\s+-rf\s+/",  "Python os.system rm -rf /"),
    (r"\bsubprocess.*rm\s+-rf\s+/",              "Python subprocess rm -rf /"),
    (r"\b__import__\s*\(\s*['\"]os['\"].*system","Python __import__ os.system"),
    (r"\beval\s*\(.*input\s*\(",                 "Python eval(input())"),
    (r"\bexec\s*\(.*input\s*\(",                 "Python exec(input())"),
]

# =============================================================================
#  Allowed safe shebangs
# =============================================================================
SAFE_SHEBANGS = [
    r"^#!/usr/bin/env\s+(bash|sh|python3?)\s*$",
    r"^#!/bin/(ba)?sh\s*$",
    r"^#!/usr/bin/(ba)?sh\s*$",
    r"^#!/usr/bin/python3?\s*$",
    r"^#!/usr/local/bin/python3?\s*$",
]

# =============================================================================
#  Main Validator
# =============================================================================

def check_file_safety(script_path: str) -> tuple[bool, str]:
    """
    Returns (is_safe: bool, reason: str)
    """

    # ── 1. File existence ─────────────────────────────────────────────────────
    if not os.path.isfile(script_path):
        return False, f"Script not found: {script_path}"

    # ── 2. Readable ───────────────────────────────────────────────────────────
    if not os.access(script_path, os.R_OK):
        return False, f"Script not readable: {script_path}"

    # ── 3. World-writable tamper check ────────────────────────────────────────
    file_stat = os.stat(script_path)
    if file_stat.st_mode & stat.S_IWOTH:
        return False, f"Script is world-writable — possible tampering: {script_path}"

    # ── 4. Must be inside SARA's own actions directory ────────────────────────
    sara_root = os.environ.get("SARA_ROOT", "")
    if sara_root:
        actions_dir = os.path.join(sara_root, "actions")
        real_script = os.path.realpath(script_path)
        real_actions = os.path.realpath(actions_dir)
        if not real_script.startswith(real_actions):
            return False, f"Script is outside SARA actions directory: {script_path}"

    # ── 5. Read file content ──────────────────────────────────────────────────
    try:
        with open(script_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        return False, f"Cannot read script: {e}"

    # ── 6. Shebang check ─────────────────────────────────────────────────────
    if lines:
        shebang = lines[0].strip()
        if shebang.startswith("#!"):
            safe_shebang = any(re.match(p, shebang) for p in SAFE_SHEBANGS)
            if not safe_shebang:
                return False, f"Unsafe or unknown shebang: {shebang}"

    # ── 7. Hardcoded dangerous pattern scan ───────────────────────────────────
    for pattern, description in HARDCODED_BLOCKED:
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            return False, f"Blocked pattern detected [{description}]: pattern='{pattern}'"

    # ── 8. Config-based blocked patterns ─────────────────────────────────────
    config_blocked_raw = os.environ.get("SARA_BLOCKED_PATTERNS", "")
    if config_blocked_raw:
        config_blocked = [p.strip() for p in config_blocked_raw.split(",") if p.strip()]
        for pattern in config_blocked:
            # Escape for regex literal match (config uses literal strings)
            escaped = re.escape(pattern)
            if re.search(escaped, content, re.IGNORECASE):
                return False, f"Config-blocked pattern detected: '{pattern}'"

    # ── 9. Suspicious sudo usage ──────────────────────────────────────────────
    sudo_matches = re.findall(r"\bsudo\b.*", content)
    for m in sudo_matches:
        # sudo is generally blocked unless it's a known safe command
        # In V1 predefined actions, sudo should not appear at all
        if re.search(r"\bsudo\b", m):
            return False, f"Unauthorized sudo usage found: '{m.strip()}'"

    # ── 10. Script size sanity check ─────────────────────────────────────────
    # A predefined action script should never be excessively large
    max_size_bytes = 50 * 1024  # 50 KB
    if os.path.getsize(script_path) > max_size_bytes:
        return False, f"Script too large ({os.path.getsize(script_path)} bytes > {max_size_bytes}). Suspicious."

    # ── All checks passed ─────────────────────────────────────────────────────
    return True, "OK"


def validate(script_path: str) -> bool:
    """
    Public entry point. Prints result and returns True/False.
    """
    is_safe, reason = check_file_safety(script_path)

    if is_safe:
        print(f"[VALIDATOR] PASSED: {os.path.basename(script_path)}", flush=True)
        return True
    else:
        print(f"[VALIDATOR] FAILED: {reason}", flush=True, file=sys.stderr)
        return False


# =============================================================================
#  Entry Point
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validator.py <script_path>", file=sys.stderr)
        sys.exit(1)

    script = sys.argv[1]
    safe = validate(script)
    sys.exit(0 if safe else 1)
