#!/usr/bin/env python3
"""Safety net for the shared basic-memory MCP server's memory.

Since mastermind 0.5.0 the server keeps its own memory flat (see server.py: ONNX arena off,
serialised reranks in small batches, idle unload) and runs in stateless HTTP mode, so a
restart no longer invalidates the MCP sessions of open Claude Code terminals. This watchdog
only catches the unexpected: it restarts the service when

  1. its physical footprint exceeds THRESHOLD_MB, and
  2. it is idle — no established connection on the port and no request logged for IDLE_S
     seconds (uvicorn appends one line per request to server.log).

Idle matters only so that no tool call in flight fails; the restarted server is back in a
few seconds and every later call simply lands on the new process.

Earlier versions required "no claude process running" instead. On a machine where terminals
stay open for days that never happened (watchdog log 2026-09-15: 17.5 GB, "8 Claude
session(s) open; keeping it warm" for hours), which is why the memory fix moved into the
server and this condition became idleness.

launchd runs this every 600 s (com.mastermind.basic-memory-watchdog.plist).
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
PORT = int(os.environ.get("MASTERMIND_PORT", "8765"))  # install.py passes the real value
THRESHOLD_MB = int(os.environ.get("MASTERMIND_WATCHDOG_THRESHOLD_MB", "3000"))
IDLE_S = int(os.environ.get("MASTERMIND_WATCHDOG_IDLE_S", "300"))
STATE_DIR = Path(os.environ.get("MASTERMIND_STATE_DIR", "~/.local/state/mastermind")).expanduser()
LOG = STATE_DIR / "watchdog.log"
SERVER_LOG = STATE_DIR / "server.log"
MAX_LOG_BYTES = 256 * 1024


def _stdout_is_log() -> bool:
    """Under launchd stdout already is watchdog.log; printing there would double every line."""
    try:
        return os.fstat(1).st_ino == LOG.stat().st_ino
    except OSError:
        return False


def note(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    if not _stdout_is_log():
        print(line, flush=True)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if LOG.exists() and LOG.stat().st_size > MAX_LOG_BYTES:
            LOG.write_text(LOG.read_text(errors="replace")[-MAX_LOG_BYTES // 2 :])
        with LOG.open("a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def run(args: list[str], timeout: float = 15.0) -> str | None:
    """stdout of a command, or None when it could not be run at all."""
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def service_pid() -> int | None:
    out = run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"]) or ""
    m = re.search(r"^\s*pid\s*=\s*(\d+)", out, re.MULTILINE)
    return int(m.group(1)) if m else None


def footprint_mb(pid: int) -> int | None:
    """Physical footprint in MB — the number Activity Monitor shows.

    RSS is useless here: a swapped-out 5 GB process reports ~30 MB resident.
    """
    out = run(["/usr/bin/vmmap", "--summary", str(pid)], timeout=60.0) or ""
    m = re.search(r"^\s*Physical footprint:\s+([\d.]+)([KMG])", out, re.MULTILINE)
    if not m:
        return None
    return int(float(m.group(1)) * {"K": 1 / 1024, "M": 1, "G": 1024}[m.group(2)])


def established_connections() -> int | None:
    """Open client connections on the port; None when lsof itself failed."""
    out = run(["lsof", "-nP", f"-iTCP:{PORT}", "-sTCP:ESTABLISHED"], timeout=20.0)
    if out is None:
        return None
    return sum(1 for line in out.splitlines()[1:] if line.strip())


def seconds_since_last_request() -> float | None:
    try:
        return time.time() - SERVER_LOG.stat().st_mtime
    except OSError:
        return None


def main() -> int:
    pid = service_pid()
    if pid is None:
        note("service not running; nothing to do")
        return 0
    mb = footprint_mb(pid)
    if mb is None:
        note(f"pid {pid}: footprint unreadable; skipping")
        return 0
    if mb < THRESHOLD_MB:
        note(f"pid {pid}: {mb} MB < {THRESHOLD_MB} MB threshold; ok")
        return 0

    conns = established_connections()
    idle = seconds_since_last_request()
    if conns is None or idle is None:
        note(f"pid {pid}: {mb} MB but cannot tell whether it is idle; leaving it alone")
        return 0
    if conns or idle < IDLE_S:
        note(f"pid {pid}: {mb} MB but busy ({conns} connection(s), last request {int(idle)} s ago); waiting")
        return 0

    note(f"pid {pid}: {mb} MB and idle for {int(idle)} s; restarting {LABEL}")
    run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{LABEL}"], timeout=30.0)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never let launchd see a crash loop
        note(f"unexpected error: {exc!r}")
        sys.exit(0)
