#!/usr/bin/env python3
"""Install the shared basic-memory MCP server as a launchd service.

Why a shared server at all: Claude Code starts one stdio MCP server per session, and
basic-memory loads the fastembed cross-encoder into that process — 1.3 GB after model
init, 6.0 GB after a few searches (measured 2026-09-12, basic-memory 0.23.2). Five open
sessions meant ~25 GB and a swapping machine. One shared HTTP server loads the model
once and, just as important, runs exactly ONE file watcher: concurrent watchers are what
produce duplicate FTS rows and `database is locked`.

Runtime files deliberately live outside the plugin cache (`~/.claude/plugins/cache/...`),
because that path carries the plugin version and changes on every update, which would
break the launchd job. Everything installs to:

    ~/.local/share/mastermind/bin/watchdog.py
    ~/Library/LaunchAgents/com.mastermind.basic-memory.plist
    ~/Library/LaunchAgents/com.mastermind.basic-memory-watchdog.plist

Usage:
    python3 install.py            # install/update and start
    python3 install.py --status   # show service state, footprint, health
    python3 install.py --uninstall
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PORT = 8765  # keep in sync with plugins/mastermind/.mcp.json
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}/mcp"
PROJECT = "mastermind"

LABEL = "com.mastermind.basic-memory"
WATCHDOG_LABEL = "com.mastermind.basic-memory-watchdog"
WATCHDOG_INTERVAL = 600  # seconds

HOME = Path.home()
SHARE = HOME / ".local/share/mastermind"
BIN = SHARE / "bin"
STATE = HOME / ".local/state/mastermind"
AGENTS = HOME / "Library/LaunchAgents"
SERVER_LOG = STATE / "server.log"

HERE = Path(__file__).resolve().parent


def gui(label: str) -> str:
    return f"gui/{os.getuid()}/{label}"


def run(args: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def find_basic_memory() -> Path:
    """Resolve the real basic-memory executable.

    `~/.local/bin/basic-memory` is a symlink into the uv tool dir; launchd gets the
    resolved target so a broken ~/.local/bin cannot take the service down.
    """
    found = shutil.which("basic-memory") or str(HOME / ".local/bin/basic-memory")
    path = Path(found)
    if not path.exists():
        sys.exit(
            "basic-memory not found. Install it first:\n"
            "  uv tool install basic-memory --prerelease=allow"
        )
    return path.resolve()


def port_owner() -> str | None:
    """Who listens on PORT, if anyone."""
    r = run(["lsof", "-nP", f"-iTCP:{PORT}", "-sTCP:LISTEN"], timeout=10)
    lines = [l for l in r.stdout.splitlines()[1:] if l.strip()]
    return lines[0] if lines else None


def server_plist(exe: Path) -> dict:
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(exe), "mcp",
            "--transport", "streamable-http",
            "--host", HOST,
            "--port", str(PORT),
        ],
        "EnvironmentVariables": {
            "BASIC_MEMORY_MCP_PROJECT": PROJECT,
            "HOME": str(HOME),
            "PATH": f"{HOME}/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "WorkingDirectory": str(HOME),
        "StandardOutPath": str(SERVER_LOG),
        "StandardErrorPath": str(SERVER_LOG),
    }


def watchdog_plist() -> dict:
    return {
        "Label": WATCHDOG_LABEL,
        "ProgramArguments": [sys.executable, str(BIN / "watchdog.py")],
        "EnvironmentVariables": {"HOME": str(HOME)},
        "RunAtLoad": False,
        "StartInterval": WATCHDOG_INTERVAL,
        "StandardOutPath": str(STATE / "watchdog.log"),
        "StandardErrorPath": str(STATE / "watchdog.log"),
    }


def write_plist(path: Path, data: dict) -> bool:
    new = plistlib.dumps(data, sort_keys=True)
    if path.exists() and path.read_bytes() == new:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(new)
    return True


def bootout(label: str) -> None:
    run(["launchctl", "bootout", gui(label)])


def bootstrap(path: Path, label: str) -> None:
    """(Re)load a job. bootout first so an edited plist actually takes effect."""
    bootout(label)
    r = run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)])
    if r.returncode != 0:
        # 'bootstrap' fails on some macOS versions when the service is still settling.
        run(["launchctl", "enable", gui(label)])
        r = run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)])
        if r.returncode != 0:
            print(f"  launchctl bootstrap {label}: {r.stderr.strip() or r.returncode}")


def health(timeout: float = 60.0) -> tuple[bool, str]:
    """Do a real MCP initialize handshake against the running server."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "mastermind-install", "version": "1"},
        },
    }).encode()
    deadline = time.time() + timeout
    last = "no response"
    while time.time() < deadline:
        req = urllib.request.Request(URL, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                payload = r.read().decode("utf-8", "replace")
            if '"serverInfo"' in payload:
                version = ""
                for token in payload.split('"version":"')[1:]:
                    version = token.split('"')[0]
                return True, f"MCP handshake ok (Basic Memory {version})"
            last = payload[:120]
        except (urllib.error.URLError, OSError) as exc:
            last = str(exc)
        time.sleep(1.5)
    return False, last


def stdio_servers() -> list[str]:
    """Per-session stdio servers still running — they keep the old RAM and watchers."""
    r = run(["pgrep", "-f", "basic-memory mcp"], timeout=10)
    pids = [p for p in r.stdout.split() if p.strip().isdigit()]
    out = []
    for pid in pids:
        c = run(["ps", "-o", "command=", "-p", pid], timeout=5).stdout.strip()
        if "streamable-http" not in c:
            out.append(pid)
    return out


def cmd_install() -> int:
    exe = find_basic_memory()
    for d in (BIN, STATE, AGENTS):
        d.mkdir(parents=True, exist_ok=True)

    owner = port_owner()
    if owner and LABEL not in owner and "basic-memory" not in owner and "python" not in owner:
        sys.exit(f"port {PORT} is taken by another process:\n  {owner}\nFree it or change PORT.")

    shutil.copy2(HERE / "watchdog.py", BIN / "watchdog.py")
    (BIN / "watchdog.py").chmod(0o755)
    print(f"installed {BIN / 'watchdog.py'}")

    sp, wp = AGENTS / f"{LABEL}.plist", AGENTS / f"{WATCHDOG_LABEL}.plist"
    write_plist(sp, server_plist(exe))
    write_plist(wp, watchdog_plist())
    print(f"installed {sp}\ninstalled {wp}")

    bootstrap(sp, LABEL)
    bootstrap(wp, WATCHDOG_LABEL)
    print(f"loaded {LABEL} (RunAtLoad, KeepAlive) and {WATCHDOG_LABEL} (every {WATCHDOG_INTERVAL}s)")

    ok, msg = health()
    print(f"health: {msg}")
    if not ok:
        print(f"  see {SERVER_LOG}")
        return 1

    left = stdio_servers()
    if left:
        print(
            f"\nnote: {len(left)} per-session stdio server(s) still running (PIDs {', '.join(left)}).\n"
            "      Restart those Claude Code sessions so they use the shared server."
        )
    print(f"\nMCP endpoint: {URL}")
    return 0


def cmd_status() -> int:
    r = run(["launchctl", "print", gui(LABEL)])
    if r.returncode != 0:
        print(f"{LABEL}: not loaded")
        return 1
    pid = state = None
    for line in r.stdout.splitlines():
        t = line.strip()
        # launchctl print repeats 'state' for nested keys; the first one is the job's.
        if pid is None and t.startswith("pid = "):
            pid = t.split("=", 1)[1].strip()
        elif state is None and t.startswith("state = "):
            state = t.split("=", 1)[1].strip()
    print(f"{LABEL}: {state or 'unknown'}")
    if pid:
        vm = run(["/usr/bin/vmmap", "--summary", pid], timeout=60).stdout
        fp = next((l.split(":")[1].strip() for l in vm.splitlines()
                   if "Physical footprint:" in l and "Peak" not in l), "?")
        print(f"  pid {pid}, footprint {fp}")
    w = run(["launchctl", "print", gui(WATCHDOG_LABEL)])
    print(f"{WATCHDOG_LABEL}: {'loaded' if w.returncode == 0 else 'not loaded'}")
    ok, msg = health(timeout=15)
    print(f"health: {msg}")
    left = stdio_servers()
    if left:
        print(f"stdio servers still running: {', '.join(left)}")
    return 0 if ok else 1


def cmd_uninstall() -> int:
    for label in (WATCHDOG_LABEL, LABEL):
        bootout(label)
        p = AGENTS / f"{label}.plist"
        if p.exists():
            p.unlink()
        print(f"removed {label}")
    wd = BIN / "watchdog.py"
    if wd.exists():
        wd.unlink()
    print("\nRevert plugins/mastermind/.mcp.json to the stdio form to get per-session servers back:")
    print('  {"mcpServers": {"mastermind-memory": {"command": "basic-memory", "args": ["mcp"],')
    print('   "env": {"BASIC_MEMORY_MCP_PROJECT": "mastermind"}}}}')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="show service state and health")
    g.add_argument("--uninstall", action="store_true", help="remove service, watchdog and plists")
    a = ap.parse_args()
    if sys.platform != "darwin":
        sys.exit("launchd setup is macOS only")
    if a.status:
        return cmd_status()
    if a.uninstall:
        return cmd_uninstall()
    return cmd_install()


if __name__ == "__main__":
    sys.exit(main())
