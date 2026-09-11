#!/usr/bin/env python3
"""Keep the shared basic-memory MCP server from sitting on gigabytes of idle RAM.

The server loads the fastembed cross-encoder (`jinaai/jina-reranker-v2-base-multilingual`)
into its own process on the first search. The ONNX arena allocator never returns that
memory: measured 1.3 GB after model init, 6.0 GB after a handful of reranks, then flat
(2026-09-12, basic-memory 0.23.2). One shared server is already far better than one per
Claude Code session, but a long-lived daemon would hold those 6 GB forever.

This watchdog restarts the service only when BOTH hold:

  1. its physical footprint exceeds THRESHOLD_MB, and
  2. no Claude Code session is running.

Condition 2 is what makes the restart safe: MCP streamable-http hands the client a
session id, and a restarted server does not know it. With no client connected there is
nothing to invalidate. A restart while sessions are open would silently break their
memory tools, so we never do it — an open session keeps the RAM, and closing the last
terminal releases it.

launchd runs this every WATCHDOG_INTERVAL seconds (see com.mastermind.basic-memory-watchdog.plist).
Always exits 0: a failing watchdog must never mark the job as crashed.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

LABEL = "com.mastermind.basic-memory"
THRESHOLD_MB = int(os.environ.get("MASTERMIND_WATCHDOG_THRESHOLD_MB", "1500"))
STATE_DIR = Path(os.environ.get("MASTERMIND_STATE_DIR", "~/.local/state/mastermind")).expanduser()
LOG = STATE_DIR / "watchdog.log"
MAX_LOG_BYTES = 256 * 1024


def note(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > MAX_LOG_BYTES:
            LOG.write_text(LOG.read_text(errors="replace")[-MAX_LOG_BYTES // 2 :])
        with LOG.open("a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def run(args: list[str], timeout: float = 15.0) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def service_pid() -> int | None:
    """PID of the launchd-managed server, or None when it is not running."""
    out = run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"])
    m = re.search(r"^\s*pid\s*=\s*(\d+)", out, re.MULTILINE)
    return int(m.group(1)) if m else None


def footprint_mb(pid: int) -> int | None:
    """Physical footprint in MB — the number Activity Monitor shows.

    RSS is useless here: a swapped-out 5 GB process reports ~30 MB resident.
    """
    out = run(["/usr/bin/vmmap", "--summary", str(pid)], timeout=60.0)
    m = re.search(r"^\s*Physical footprint:\s+([\d.]+)([KMG])", out, re.MULTILINE)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2)
    return int(value * {"K": 1 / 1024, "M": 1, "G": 1024}[unit])


def claude_sessions() -> int:
    """Count running Claude Code CLI processes (the only clients of this server)."""
    out = run(["pgrep", "-x", "claude"])
    return len([x for x in out.split() if x.strip().isdigit()])


def main() -> int:
    pid = service_pid()
    if pid is None:
        note("service not running; nothing to do")
        return 0

    mb = footprint_mb(pid)
    if mb is None:
        note(f"pid {pid}: footprint unreadable; skipping")
        return 0

    sessions = claude_sessions()
    if mb < THRESHOLD_MB:
        note(f"pid {pid}: {mb} MB < {THRESHOLD_MB} MB threshold, {sessions} session(s); ok")
        return 0
    if sessions:
        note(f"pid {pid}: {mb} MB but {sessions} Claude session(s) open; keeping it warm")
        return 0

    note(f"pid {pid}: {mb} MB and no Claude session; restarting {LABEL}")
    run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{LABEL}"], timeout=30.0)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never let launchd see a crash loop
        note(f"unexpected error: {exc!r}")
        sys.exit(0)
