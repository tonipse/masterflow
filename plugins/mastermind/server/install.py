#!/usr/bin/env python3
"""Install the shared basic-memory MCP server as a launchd service.

Why a shared server at all: Claude Code starts one stdio MCP server per session, and
basic-memory loads the fastembed cross-encoder into that process — several GB per session
once it has reranked a few searches (measured 2026-09-12, basic-memory 0.23.2). One shared
HTTP server loads the model once and runs exactly ONE file watcher: concurrent watchers are
what produce duplicate FTS rows and `database is locked`.

Since 0.5.0 the service is started through `server.py`, which keeps the process flat
(ONNX arena off, serialised reranks, idle unload — see its docstring), and it runs in
FastMCP's stateless HTTP mode (`FASTMCP_STATELESS_HTTP=true`): no session ids, so a restart
of the service is invisible to open Claude Code sessions.

Runtime files deliberately live outside the plugin cache (`~/.claude/plugins/cache/...`),
because that path carries the plugin version and changes on every update, which would
break the launchd job. Everything installs to:

    ~/.local/share/mastermind/bin/server.py
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
import http.client
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
RUNTIME_FILES = ("server.py", "watchdog.py")

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


def venv_python(exe: Path) -> Path:
    """The interpreter of basic-memory's own venv; server.py must run inside it.

    Deliberately NOT resolved: `bin/python` in a venv is a symlink to the base interpreter,
    and the resolved path would start that base interpreter without the venv's packages
    (first install attempt 2026-09-16 ended up on /opt/anaconda3/bin/python3.12).
    """
    for name in ("python", "python3"):
        candidate = exe.parent / name
        if not candidate.exists():
            continue
        r = run([str(candidate), "-c", "import basic_memory, fastembed"], timeout=60)
        if r.returncode == 0:
            return candidate
        sys.exit(f"{candidate} cannot import basic_memory/fastembed:\n  {r.stderr.strip()[-300:]}")
    sys.exit(f"no python interpreter next to {exe}; is basic-memory installed as a uv tool?")


def port_owner() -> str | None:
    """Who listens on PORT, if anyone."""
    r = run(["lsof", "-nP", f"-iTCP:{PORT}", "-sTCP:LISTEN"], timeout=10)
    lines = [l for l in r.stdout.splitlines()[1:] if l.strip()]
    return lines[0] if lines else None


def server_plist(py: Path) -> dict:
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(py), str(BIN / "server.py"), "mcp",
            "--transport", "streamable-http",
            "--host", HOST,
            "--port", str(PORT),
        ],
        "EnvironmentVariables": {
            "BASIC_MEMORY_MCP_PROJECT": PROJECT,
            "FASTMCP_STATELESS_HTTP": "true",
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
        "EnvironmentVariables": {"HOME": str(HOME), "MASTERMIND_PORT": str(PORT)},
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


def loaded(label: str) -> bool:
    return run(["launchctl", "print", gui(label)], timeout=10).returncode == 0


def bootstrap(path: Path, label: str) -> None:
    """(Re)load a job. bootout first so an edited plist actually takes effect.

    bootout returns before the old process is gone — uvicorn waits for open client
    connections on shutdown — and bootstrap answers EIO while the label still exists.
    So wait for the old job to disappear, then retry a few times.
    """
    bootout(label)
    deadline = time.time() + 45
    while loaded(label) and time.time() < deadline:
        time.sleep(1)
    run(["launchctl", "enable", gui(label)])
    err = ""
    for _ in range(6):
        r = run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)])
        if r.returncode == 0 or loaded(label):
            return
        err = r.stderr.strip() or str(r.returncode)
        time.sleep(2)
    print(f"  launchctl bootstrap {label}: {err}")


def health(timeout: float = 60.0) -> tuple[bool, str]:
    """Do a real MCP initialize handshake against the running server.

    Also reports the session mode: a stateless server returns no Mcp-Session-Id, which
    is what makes service restarts harmless for open Claude Code sessions.
    """
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
                session = r.headers.get("Mcp-Session-Id")
            if '"serverInfo"' in payload:
                version = ""
                for token in payload.split('"version":"')[1:]:
                    version = token.split('"')[0]
                mode = "stateless" if not session else "stateful — sessions break on restart"
                return True, f"MCP handshake ok (Basic Memory {version}, {mode})"
            last = payload[:120]
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            # HTTPException covers IncompleteRead from a server that is just shutting down.
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


def server_notes(n: int = 3) -> list[str]:
    """Last lines server.py wrote (patch state, reranker loads/unloads)."""
    try:
        lines = SERVER_LOG.read_text(errors="replace").splitlines()
    except OSError:
        return []
    return [l.strip() for l in lines if l.startswith("[mastermind-server]")][-n:]


def cmd_install() -> int:
    exe = find_basic_memory()
    py = venv_python(exe)
    for d in (BIN, STATE, AGENTS):
        d.mkdir(parents=True, exist_ok=True)

    owner = port_owner()
    if owner and LABEL not in owner and "basic-memory" not in owner and "python" not in owner:
        sys.exit(f"port {PORT} is taken by another process:\n  {owner}\nFree it or change PORT.")

    for name in RUNTIME_FILES:
        shutil.copy2(HERE / name, BIN / name)
        (BIN / name).chmod(0o755)
        print(f"installed {BIN / name}")

    sp, wp = AGENTS / f"{LABEL}.plist", AGENTS / f"{WATCHDOG_LABEL}.plist"
    write_plist(sp, server_plist(py))
    write_plist(wp, watchdog_plist())
    print(f"installed {sp}\ninstalled {wp}")

    bootstrap(sp, LABEL)
    bootstrap(wp, WATCHDOG_LABEL)
    print(f"loaded {LABEL} (RunAtLoad, KeepAlive) and {WATCHDOG_LABEL} (every {WATCHDOG_INTERVAL}s)")

    ok, msg = health()
    print(f"health: {msg}")
    for line in server_notes(1):
        print(f"  {line}")
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
    for line in server_notes():
        print(f"  {line}")
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
    for name in RUNTIME_FILES:
        f = BIN / name
        if f.exists():
            f.unlink()
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
