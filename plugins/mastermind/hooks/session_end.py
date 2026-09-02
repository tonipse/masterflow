#!/usr/bin/env python3
"""SessionEnd hook for the mastermind plugin.

1. Commit the vault if the session left it dirty (safety net for autonomous captures).
2. Push in the background when the vault has a remote `origin` and `.mastermind.json` does not say
   `"push": false` (detached process, never blocks the hook).
3. Remember the session in ~/.local/state/mastermind/last-session-<slug>.json so the next session start can
   say "UNWRAPPED" and `/mastermind:wrap last` can harvest the transcript: session_id, transcript_path, cwd,
   root, ended, reason, edits (Edit/Write/MultiEdit/NotebookEdit tool calls in the transcript), wrapped
   (the transcript shows a real `/mastermind:wrap` run), notified (0).

Python 3 standard library only. Always exits 0. Budget: under 2 s without push.
"""

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_TRANSCRIPT_BYTES = 200 * 1024 * 1024
EDIT_MARKERS = ('"name":"Edit"', '"name":"Write"', '"name":"MultiEdit"', '"name":"NotebookEdit"',
                '"name": "Edit"', '"name": "Write"', '"name": "MultiEdit"', '"name": "NotebookEdit"')


def read_hook_input():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw and raw.strip() else {}
    except Exception:
        return {}


def run_git(args, cwd, timeout=5):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip()
    except Exception:
        return False, ""


def find_vault():
    p = Path(os.environ.get("MASTERMIND_VAULT") or "~/Mastermind").expanduser()
    return p if (p / ".git").is_dir() else None


def state_dir():
    d = Path(os.environ.get("XDG_STATE_HOME") or "~/.local/state").expanduser() / "mastermind"
    d.mkdir(parents=True, exist_ok=True)
    return d


def slug(path):
    return re.sub(r"[^A-Za-z0-9-]", "-", str(path))


def project_root(cwd):
    ok, top = run_git(["rev-parse", "--show-toplevel"], cwd, timeout=2)
    if not ok or not top:
        return None
    ok, common = run_git(["rev-parse", "--git-common-dir"], cwd, timeout=2)
    if ok and common:
        cp = Path(common)
        if not cp.is_absolute():
            cp = Path(top) / cp
        try:
            cp = cp.resolve()
        except Exception:
            pass
        if cp.name == ".git":
            return str(cp.parent)
    return top


def commit_vault(vault, project_name):
    ok, status = run_git(["status", "--porcelain"], vault)
    if not ok or not status:
        return False
    ok, _ = run_git(["add", "-A"], vault)
    if not ok:
        return False
    ok, _ = run_git(["commit", "-qm", f"auto: session end ({project_name})"], vault, timeout=8)
    return ok


def push_allowed(vault):
    try:
        cfg = json.loads((vault / ".mastermind.json").read_text(encoding="utf-8"))
        if cfg.get("push") is False:
            return False
    except Exception:
        pass
    ok, url = run_git(["remote", "get-url", "origin"], vault, timeout=2)
    return ok and bool(url)


def push_background(vault):
    try:
        subprocess.Popen(["git", "push", "-q", "origin", "HEAD"], cwd=str(vault), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except Exception:
        return False


def scan_transcript(path):
    """(edits, wrapped) from the transcript; (None, False) when missing or too large."""
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size > MAX_TRANSCRIPT_BYTES:
            return None, False
    except Exception:
        return None, False
    edits, wrapped = 0, False
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"type":"assistant"' in line or '"type": "assistant"' in line:
                    for m in EDIT_MARKERS:
                        edits += line.count(m)
                if wrapped or "mastermind" not in line:
                    continue
                # Real markers only: the bare substring "mastermind:wrap" is in every transcript (hook RULES), and
                # tool results may quote the marker text, so candidate lines are parsed and checked structurally.
                if "queue-operation" in line and "/mastermind:wrap" in line:
                    wrapped = _is_wrap_queue_line(line)
                elif "isMeta" in line and "Base directory for this skill:" in line and "/skills/mastermind-wrap" in line:
                    wrapped = _is_wrap_skill_line(line)
    except Exception:
        return None, wrapped
    return edits, wrapped


def _is_wrap_queue_line(line):
    try:
        o = json.loads(line)
        return o.get("type") == "queue-operation" and str(o.get("content", "")).lstrip().startswith("/mastermind:wrap")
    except Exception:
        return False


def _is_wrap_skill_line(line):
    try:
        o = json.loads(line)
        if o.get("type") != "user" or not o.get("isMeta"):
            return False
        content = (o.get("message") or {}).get("content", "")
        if isinstance(content, list):
            content = " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
        return "Base directory for this skill:" in str(content) and "/skills/mastermind-wrap" in str(content)
    except Exception:
        return False


def main():
    data = read_hook_input()
    cwd = data.get("cwd") or os.getcwd()
    root = project_root(cwd) or cwd
    project_name = Path(root).name
    vault = find_vault()
    committed = pushed = False
    if vault is not None:
        committed = commit_vault(vault, project_name)
        if push_allowed(vault):
            pushed = push_background(vault)
    edits, wrapped = scan_transcript(data.get("transcript_path") or "")
    state = {
        "session_id": data.get("session_id") or "",
        "transcript_path": data.get("transcript_path") or "",
        "cwd": cwd,
        "root": root,
        "ended": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "reason": data.get("reason") or "",
        "edits": edits,
        "wrapped": wrapped,
        "notified": 0,
        "vault_committed": committed,
        "push_started": pushed,
    }
    try:
        (state_dir() / f"last-session-{slug(root)}.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
