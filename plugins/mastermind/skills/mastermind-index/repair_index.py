#!/usr/bin/env python3
"""Repair the basic-memory full-text index of the Mastermind vault (skill mastermind-index).

Background: `basic-memory reindex` (0.22.x and 0.23.x) writes title-only entity rows into the FTS table and
drops the observation/relation rows; only the file watcher of a running `basic-memory mcp` process indexes
a note completely (content stems, observations, relations, vector chunks). Concurrent watchers can also
leave duplicate rows. This script therefore:

  1. requires a running `basic-memory mcp` process (any Claude Code session with the plugin), refuses to
     run with more than 2 of them unless --force (they compete for the SQLite lock);
  2. backs up memory.db to <config dir>/backups/repair/memory-<timestamp>.db (keeps the 5 newest there);
  3. finds every note whose rows are incomplete (no content stems, duplicate entity rows, fewer
     observation/relation rows than the tables hold, or no entity at all);
  4. sets entity.checksum = NULL for those notes and touches the files in batches of 25, waits 8 s per
     batch so the watcher re-syncs them, verifies per SQL, repeats up to 5 rounds;
  5. prints the coverage numbers (entity rows with content, observations, relations, chunks per entity).

Standard library only; always exits 0. Usage:
  repair_index.py [--vault PATH] [--project NAME] [--force] [--dry-run] [--batch N] [--wait SECONDS] [--rounds N]
"""

import argparse
import datetime as dt
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

BATCH = 25
WAIT = 8.0
ROUNDS = 5
KEEP_BACKUPS = 5


def watcher_pids():
    try:
        r = subprocess.run(["pgrep", "-f", "basic-memory mcp"], capture_output=True, text=True, timeout=5)
        return [int(x) for x in r.stdout.split() if x.strip().isdigit() and int(x) != os.getpid()]
    except Exception:
        return []


def vault_files(vault):
    files = []
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and not (Path(dirpath) == vault and d == "inbox")]
        for fn in filenames:
            if fn.endswith((".md", ".canvas")) and not fn.startswith("."):
                files.append((Path(dirpath) / fn).relative_to(vault).as_posix())
    return sorted(files)


def backup_db(db):
    dest_dir = db.parent / "backups" / "repair"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"memory-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    dst = sqlite3.connect(str(dest))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    # prune only memory-*.db in this folder, never anything else under backups/
    olds = sorted(dest_dir.glob("memory-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)[KEEP_BACKUPS:]
    for p in olds:
        try:
            p.unlink()
        except Exception:
            pass
    return dest


def coverage(con, pid, files):
    q = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    entities = q("select count(*) from entity where project_id=?", pid)
    fts_content = q("select count(distinct file_path) from search_index where project_id=? and type='entity' and length(content_stems)>0", pid)
    dup = q("select count(*) from (select file_path from search_index where project_id=? and type='entity' group by file_path having count(*)>1)", pid)
    obs = q("select count(*) from observation where project_id=?", pid)
    obs_fts = q("select count(*) from search_index where project_id=? and type='observation'", pid)
    rel = q("select count(*) from relation where project_id=?", pid)
    rel_fts = q("select count(*) from search_index where project_id=? and type='relation'", pid)
    try:
        chunks = q("select count(*) from search_vector_chunks where project_id=?", pid)
    except sqlite3.Error:
        chunks = None
    return {"files": len(files), "entities": entities, "fts_content": fts_content, "duplicates": dup,
            "observations": obs, "observations_fts": obs_fts, "relations": rel, "relations_fts": rel_fts,
            "chunks": chunks}


def incomplete_files(con, pid, files):
    """Files whose index rows are incomplete. Returns (list of rel paths, dict reasons)."""
    rows = con.execute(
        "select e.id, e.file_path,"
        " (select count(*) from search_index s where s.project_id=e.project_id and s.type='entity' and s.file_path=e.file_path and length(s.content_stems)>0),"
        " (select count(*) from search_index s where s.project_id=e.project_id and s.type='entity' and s.file_path=e.file_path),"
        " (select count(*) from observation o where o.entity_id=e.id),"
        " (select count(*) from search_index s where s.project_id=e.project_id and s.type='observation' and s.file_path=e.file_path),"
        " (select count(*) from relation r where r.from_id=e.id),"
        " (select count(*) from search_index s where s.project_id=e.project_id and s.type='relation' and s.file_path=e.file_path)"
        " from entity e where e.project_id=?", (pid,)).fetchall()
    by_path = {}
    reasons = {}
    for eid, fp, content, ent_rows, obs, obs_fts, rel, rel_fts in rows:
        by_path[fp] = eid
        why = []
        if fp.endswith(".md") and content == 0:
            why.append("kein Volltext-Inhalt")
        if ent_rows > 1:
            why.append(f"{ent_rows} Entity-Zeilen")
        if obs_fts < obs:
            why.append(f"Observations {obs_fts}/{obs}")
        if rel_fts < rel:
            why.append(f"Relations {rel_fts}/{rel}")
        if why:
            reasons[fp] = ", ".join(why)
    for fp in files:
        if fp not in by_path:
            reasons[fp] = "keine Entity"
    targets = [fp for fp in files if fp in reasons]
    return targets, reasons, by_path


def pct(a, b):
    return 100.0 * a / b if b else 100.0


def print_coverage(label, c):
    ent = c["entities"]
    line = (f"{label}: Entities {ent}/{c['files']} · FTS-Inhalt {c['fts_content']}/{ent} ({pct(c['fts_content'], ent):.0f} %)"
            f" · doppelte Entity-Zeilen {c['duplicates']} · Observations {c['observations_fts']}/{c['observations']} ({pct(c['observations_fts'], c['observations']):.0f} %)"
            f" · Relations {c['relations_fts']}/{c['relations']} ({pct(c['relations_fts'], c['relations']):.0f} %)")
    if c["chunks"] is not None:
        line += f" · Chunks {c['chunks']} ({(c['chunks'] / ent) if ent else 0:.1f} je Entity)"
    print(line, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", default=os.environ.get("MASTERMIND_VAULT") or "~/Mastermind")
    ap.add_argument("--project", default=os.environ.get("BASIC_MEMORY_MCP_PROJECT") or "mastermind")
    ap.add_argument("--force", action="store_true", help="run even with more than 2 watchers")
    ap.add_argument("--dry-run", action="store_true", help="only report, change nothing")
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--wait", type=float, default=WAIT)
    ap.add_argument("--rounds", type=int, default=ROUNDS)
    a = ap.parse_args()

    pids = watcher_pids()
    if not pids:
        print("kein laufender MCP-Watcher (basic-memory mcp): Reparatur braucht eine offene Claude-Code-Session mit dem Plugin.")
        return
    if len(pids) > 2 and not a.force:
        print(f"{len(pids)} basic-memory-mcp-Prozesse laufen (PIDs {', '.join(map(str, pids))}); konkurrierende Watcher sperren die "
              "Index-DB und erzeugen doppelte Zeilen. Andere Claude-Sessions schließen, dann erneut starten (oder --force).")
        return
    print(f"Watcher: {len(pids)} basic-memory-mcp-Prozess(e)", flush=True)

    cfg_dir = Path(os.environ.get("BASIC_MEMORY_CONFIG_DIR") or "~/.basic-memory").expanduser()
    db = cfg_dir / "memory.db"
    if not db.is_file():
        print(f"Index-DB nicht gefunden: {db}")
        return
    con = sqlite3.connect(str(db), timeout=10)
    row = con.execute("select id, path from project where name=?", (a.project,)).fetchone()
    if not row:
        print(f"Projekt `{a.project}` nicht in der Index-DB")
        return
    pid, ppath = row
    vault = Path(a.vault).expanduser()
    if not vault.is_dir():
        vault = Path(ppath).expanduser()
    if Path(ppath).expanduser().resolve() != vault.resolve():
        print(f"WARNUNG: Index-Projekt zeigt auf {ppath}, Vault ist {vault}")
    files = vault_files(vault)

    before = coverage(con, pid, files)
    print_coverage("Vorher", before)
    targets, reasons, by_path = incomplete_files(con, pid, files)
    print(f"Unvollständig: {len(targets)} von {len(files)} Dateien", flush=True)
    if a.dry_run:
        for fp in targets[:40]:
            print(f"  - {fp}: {reasons[fp]}")
        if len(targets) > 40:
            print(f"  … {len(targets) - 40} weitere")
        con.close()
        return
    if not targets:
        print("Index ist vollständig, nichts zu tun.")
        con.close()
        return

    dest = backup_db(db)
    print(f"Sicherung: {dest}", flush=True)

    for rnd in range(1, a.rounds + 1):
        print(f"Runde {rnd}: {len(targets)} Datei(en)", flush=True)
        with con:
            for fp in targets:
                if fp in by_path:
                    con.execute("update entity set checksum=NULL where project_id=? and file_path=?", (pid, fp))
        for i in range(0, len(targets), a.batch):
            batch = targets[i:i + a.batch]
            for fp in batch:
                try:
                    os.utime(vault / fp, None)
                except Exception as e:
                    print(f"  touch fehlgeschlagen: {fp}: {e}")
            time.sleep(a.wait)
            print(f"  … {min(i + a.batch, len(targets))}/{len(targets)} angestoßen", flush=True)
        time.sleep(a.wait / 2)
        remaining, reasons, by_path = incomplete_files(con, pid, files)
        fixed = len(targets) - len([t for t in targets if t in reasons])
        print(f"  repariert: {fixed}, offen: {len(remaining)}", flush=True)
        if not remaining:
            targets = []
            break
        if remaining == targets:
            print("  keine Änderung in dieser Runde; Watcher reagiert nicht (Session ohne Plugin-MCP? TCC?).")
        targets = remaining

    after = coverage(con, pid, files)
    con.close()
    print_coverage("Nachher", after)
    ent = after["entities"]
    ok = (ent >= 0.95 * len(files) and pct(after["fts_content"], ent) >= 95 and pct(after["observations_fts"], after["observations"]) >= 90
          and pct(after["relations_fts"], after["relations"]) >= 90 and after["duplicates"] == 0)
    if after["chunks"] is not None and ent and after["chunks"] < 1.5 * ent:
        print(f"Hinweis: {after['chunks']} Vektor-Chunks für {ent} Entities (< 1,5 je Entity); Vektoren baut der MCP-Server beim Sync, sonst retrieval-upgrade.sh.")
    if targets:
        print(f"Nicht repariert ({len(targets)}):")
        for fp in targets[:20]:
            print(f"  - {fp}: {reasons.get(fp, '?')}")
    print("Ergebnis: " + ("Index vollständig (Ziel erreicht: FTS-Inhalt ≥ 95 %, Observations/Relations ≥ 90 %, keine Duplikate)." if ok
                          else "Index noch unvollständig, siehe Zahlen; erneut ausführen, sobald nur eine Session läuft."))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("abgebrochen")
    except Exception as e:
        print(f"repair_index.py abgebrochen: {e}")
    sys.exit(0)
