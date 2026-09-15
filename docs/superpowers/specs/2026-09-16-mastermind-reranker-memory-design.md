# Mastermind: Reranker-Speicher im geteilten Server (0.5.0)

Datum: 2026-09-16 (Vorfall 2026-09-15). Ergänzt `2026-09-12-mastermind-shared-server-design.md`.
Quellen: `~/.local/state/mastermind/watchdog.log`, `~/.local/state/mastermind/server.log`,
`~/.basic-memory/basic-memory.log`, Messskripte im Session-Scratchpad (`rerank_mem.py`,
`rerank_vary.py`, `it_server.py`), Quellcode basic-memory 0.23.2, fastembed 0.8.0, onnxruntime 1.29.0,
fastmcp 4.0.0b1, mcp 2.1.1.

## Befund

Drei parallele `/mastermind:wrap` am Abend des 2026-09-15. Der geteilte Dienst (PID 53342) stand laut
Watchdog um 21:35 bei 17 305 MB und um 22:06 bei 17 510 MB; der Nutzer sah in der Aktivitätsanzeige
30 GB (zwischen zwei Watchdog-Messungen) und musste den Prozess beenden. Der Watchdog hat den Dienst
in dieser Zeit **bewusst nicht** neu gestartet: „8 Claude session(s) open; keeping it warm". Die
Bedingung „kein `claude`-Prozess" aus 0.4.1 tritt auf diesem Rechner nie ein — acht Terminals, das
älteste seit fünf Tagen offen.

Dazu im basic-memory-Log derselben Stunde: Ollama-Embeddings mit `embed_seconds` 10–44 je Notiz und
hybride Suchen mit `total_ms` 5 000–20 000 (davon Vektorsuche 0,3–3,5 s, der Rest Rerank im Swap).
Um 22:15:53 nach dem Neustart: `OllamaException` — Ollama war unter dem Speicherdruck ebenfalls weg.

## Warum die Messung vom 2026-09-12 nicht reichte

Am 2026-09-12 war gemessen: 1,3 GB nach dem Modell-Load, 6,0 GB nach wenigen Suchen, dann flach —
und daraus die Erwartung abgeleitet, ein einzelner Dienst bleibe bei ~6 GB. Zwei Dinge fehlten:

1. **Parallelität.** `FastEmbedRerankProvider.rerank` läuft per `asyncio.to_thread` ohne Sperre; jede
   gleichzeitige Suche bekommt eigene Aktivierungspuffer.
2. **Wechselnde Eingabeformen.** Jede Suche hat andere Dokumentlängen. Die ONNX-Arena reserviert je
   Form neue Bereiche und gibt nichts zurück.

## Messungen (Physical footprint über `proc_pid_rusage`, gleiche Zahl wie die Aktivitätsanzeige)

Standalone-Cross-Encoder `jinaai/jina-reranker-v2-base-multilingual`, `threads=8` wie basic-memory
sie auflöst, 20 Dokumente wie `reranker_candidates`, bis 2000 Zeichen wie `reranker_max_document_chars`.

**Gleiche Eingaben je Lauf (4 Dokumente):** Arena an: +200 MB je Lauf, flach; zwei parallel: +350 MB.
Arena aus: nach jedem Lauf zurück auf 1,42 GB. Zeigt nicht das Problem — die Arena reicht Bereiche
gleicher Größe weiter.

**Wechselnde Eingaben je Lauf (20 Dokumente, Längen 300–2000 Zeichen, Batch 64):**

| Lauf | Arena an: nach dem Lauf | Arena aus: Spitze / danach |
|---|---|---|
| Modell geladen | 1 302 MB | 1 302 MB |
| 1 | 3 317 MB | 3 064 / 1 430 MB |
| 2 | 3 890 MB | 3 236 / 1 440 MB |
| 3–6 | 3 891–3 911 MB | 2 478–2 747 / 1 439–1 441 MB |
| 2 parallel | 5 843 → **5 567 MB bleiben** | 5 040 / **1 440 MB** |

Das ist das Muster des echten Servers (1,3 → 3,8 → 6,0 GB) und erklärt mit drei parallelen Wraps
die 17,5 GB: Die Arena verdoppelt ihre Bereiche und behält alles.

**Batchgröße bei Arena aus (20 wechselnde Dokumente, 6 Läufe + 3 parallel):**

| Batch | Spitze je Lauf | Latenz je Lauf | 3 parallel: Spitze / danach / Wandzeit |
|---|---|---|---|
| 64 | +1,1–1,8 GB | 2,9–3,7 s | 5 040 / 1 440 MB / 5,5 s (2 parallel) |
| 8 | +250–600 MB | 2,3–3,3 s | 3 152 / 1 464 MB / 7,2 s |
| **4** | **+20–160 MB** | **2,2–2,8 s** | **1 744 / 1 337 MB / 6,1 s** |

Batch 4 ist zugleich am sparsamsten und am schnellsten: weniger Padding je Batch. Modell-Neuladen aus
dem lokalen Cache: 0,6 s (zweimal gemessen).

## Entscheidung

`plugins/mastermind/server/server.py` startet die unveränderte basic-memory-CLI und patcht vorher zwei
Stellen; Modell, Kandidaten, Schwellen und Scores bleiben identisch, nur die Allokation ändert sich:

1. `fastembed.rerank.cross_encoder.TextCrossEncoder` wird durch eine Unterklasse ersetzt, die
   `enable_cpu_mem_arena=False` setzt — das einzige Session-Option-Feld, das fastembed 0.8.0
   durchreicht (`OnnxModel.EXPOSED_SESSION_OPTIONS`). basic-memorys `_create_model` mit seiner
   Download-Fehlerbehandlung bleibt unangetastet.
2. `FastEmbedRerankProvider.rerank` wird ersetzt: ein `threading.Lock` serialisiert die Reranks,
   `batch_size=4`, und ein Daemon-Thread entlädt das Modell nach 600 s ohne Suche (nie während eines
   Reranks, weil unter demselben Lock).

Jeder Patch prüft die Attribute, die er ersetzt; fehlen sie nach einem Update, startet der Server
ungepatcht und meldet `patched=False` in `server.log`.

Dazu **Stateless-HTTP** (`FASTMCP_STATELESS_HTTP=true`, von fastmcp per Settings gelesen, im MCP-SDK
`_handle_stateless_request`: neue Transport-Instanz je Request, `Mcp-Session-Id` wird ignoriert,
„born-ready" ohne `initialize`). Ein Neustart des Dienstes entwertet damit keine Session mehr — die
offene Frage aus 0.4.0 ist gegenstandslos. Der Watchdog startet deshalb neu, wenn der Footprint über
3000 MB liegt **und** der Dienst leer läuft (keine ESTABLISHED-Verbindung auf dem Port, `server.log`
seit ≥ 300 s unverändert; uvicorn schreibt je Request eine Zeile). Nebenbei behoben: Jede Watchdog-Zeile
stand doppelt im Log, weil `note()` auf stdout druckte und launchd stdout in dieselbe Datei leitet;
gedruckt wird jetzt nur an ein Terminal.

`install.py` startet `server.py` über den Python-Interpreter der basic-memory-venv, setzt die Env,
reicht den Port als `MASTERMIND_PORT` an den Watchdog und meldet im Health-Check den Session-Modus.
`repair_index.py` erkennt den Dienst jetzt über `server.py mcp` und die launchd-PID.

## Alternativen

- **Reranker abschalten** (`reranker_enabled: false`): spart alles, widerspricht der Retrieval-Decision
  vom 2026-09-03 (Reranker weglassen „nicht gemessen"). Nicht nötig, da die Ursache die Allokation ist.
- **`reranker_max_document_chars` 2000 → 1000** oder weniger Kandidaten: senkt nur die Spitze, nicht das
  Wachstum; Qualität ungemessen. Unverändert.
- **Watchdog aggressiver bei Stateful-Betrieb:** hätte bei jedem Neustart die Memory-Tools offener
  Sessions still gebrochen. Verworfen zugunsten von Stateless.
- **Reranker in einem Kindprozess je Aufruf:** Speicher frei nach Exit, aber 0,6 s Load plus
  Prozessstart je Suche und mehr Bauteile. Verworfen.
- **`arena_extend_strategy=kSameAsRequested` oder Arena-Shrink per RunOptions:** fastembed reicht diese
  Optionen nicht durch; hätte einen tieferen Eingriff in fastembed gebraucht. Verworfen.
- **Kleineres Embedding-Modell in Ollama** (`qwen3-embedding:4b`/`0.6b`, geladen ~6 GB → ~3/1 GB):
  Retrieval-Decision; nicht ohne Messung. Offen gelassen, als Option genannt.

## Konsequenzen

- Dienst ohne geladenes Modell ~200 MB, mit Modell ~1,7 GB, Spitze bei drei parallelen Suchen 2,1 GB;
  nach 10 min ohne Suche wieder ~500 MB (Integrationstest) — statt 6–17,5 GB dauerhaft.
- Suchen während eines Neustarts (Watchdog oder Absturz) schlagen einmal fehl; der nächste Aufruf
  landet auf dem neuen Prozess. Kein `/mcp`-Reconnect nötig.
- Die erste Suche nach Leerlauf zahlt 0,6 s Modell-Load (plus Ollamas 10–20 s, falls auch das
  Embedding-Modell entladen war — unverändert seit 2026-09-03).
- Der Patch hängt an der Form von basic-memory 0.23.2 und fastembed 0.8.0; `auto_update` bleibt
  `false`. Nach einem Update `install.py --status` ansehen: `patched=True` muss dort stehen.
- Der zweite große Posten bleibt Ollama (`qwen3-embedding:8b`, ~6 GB geladen, 5 min Keep-Alive).

## Verifikation

Integrationstest `it_server.py` gegen den echten Index auf Port 8766 (Watcher und Start-Sync aus, damit
nichts mit dem Live-Dienst konkurriert), Leerlauf-Entladen auf 25 s gestellt:

| Schritt | Ergebnis |
|---|---|
| Start | Handshake nach ~3 s, **kein** `Mcp-Session-Id`, 195 MB; Banner „(stateless)" |
| 6 hybride Suchen, jede zweite mit gefälschter Session-ID | alle HTTP 200, 0,26–1,6 s (erste 9,1 s: Modell-Loads), 1 632 → 1 751 MB |
| 3 parallele Suchen | HTTP 200 ×3, Wandzeit 11,8 s, Spitze 2 071 MB, danach 1 802 MB |
| 60 s Leerlauf | „reranker unloaded after 34 s idle", 507 MB |
| Suche danach | HTTP 200, 5,1 s, 1 743 MB |

### Live-Verifikation 2026-09-16

- Erster `install.py`-Lauf scheiterte zweifach: `venv_python()` hatte den Symlink `bin/python` der
  uv-venv aufgelöst und damit den Basis-Interpreter `/opt/anaconda3/bin/python3.12` ohne die venv in die
  plist geschrieben; `launchctl bootstrap` antwortete mit EIO, weil der alte uvicorn noch auf das Schließen
  der Client-Verbindungen (SSE-Streams der acht offenen Sessions) wartete, und der Health-Check fing die
  abgebrochene Chunk-Antwort (`IncompleteRead`) nicht. Behoben: kein `resolve()` plus Import-Preflight,
  Warten auf das Verschwinden des Labels mit Retry, `http.client.HTTPException` abgefangen.
- Danach: Handshake `stateless`, `[mastermind-server] start: patched=True arena=off batch=4 idle_unload=600s`.
- `claude -p` mit `search_notes` (hybrid) gegen den Live-Dienst: 10 Titel, die drei Speicher-Notizen vorn —
  eine echte Claude-Code-Session arbeitet also mit dem stateless Server (GET-Stream fehlt, 405, egal).
- Live-Lasttest per HTTP mit veralteter Session-ID: 3 sequenzielle Suchen 1,4–3,6 s (Footprint
  1 635 → 1 729 MB), 3 parallele: alle 200, Spitze 2 030 MB, danach 1 735 MB.
- Watchdog manuell und über launchd: `pid 50299: 1740 MB < 3000 MB threshold; ok`, eine Zeile je Lauf.
- `repair_index.py` erkennt den Dienst über die launchd-PID (`watcher_pids: [50299]`).
- `claude plugin validate … --strict` für beide Manifeste: bestanden.
- Neustart über `install.py` unter Last-freiem Betrieb, `tools/list` mit veralteter Session-ID: HTTP 200 vor und nach dem Neustart (PID 50299 → 55222, erster Versuch) — der Fall, den 0.4.x vermeiden musste, ist harmlos.

## Endstand

| | 0.4.1 (Vorfall 2026-09-15) | 0.5.0 |
|---|---|---|
| Dienst nach einigen Suchen | 6 GB, unter Last 17,5 GB, dauerhaft | ~1,7 GB, nach 10 min Leerlauf ~500 MB |
| 3 parallele Suchen | Arena verdoppelt sich, bleibt | Spitze 2,0–2,1 GB, danach zurück |
| Neustart bei offenen Sessions | bricht deren Memory-Tools | unsichtbar (stateless) |
| Watchdog-Bedingung | kein `claude`-Prozess (nie erfüllt) | Footprint > 3000 MB **und** Leerlauf ≥ 300 s |
| Suchergebnisse | — | unverändert (gleiches Modell, gleiche Scores) |
