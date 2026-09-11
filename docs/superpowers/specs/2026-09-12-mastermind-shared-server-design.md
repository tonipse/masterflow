# mastermind 0.4.0 — ein geteilter MCP-Server statt einem je Session

Stand 2026-09-12. Anlass: MacBook Pro M5 (24 GB) wurde heiß und langsam; die Aktivitätsanzeige zeigte
drei `python3.12` mit 5,18 / 4,86 / 4,82 GB.

## Befund

Die Prozesse sind der MCP-Server des mastermind-Plugins. `plugins/mastermind/.mcp.json` startete
`basic-memory mcp` über stdio, und Claude Code startet stdio-Server **je Session**.

| MCP-PID | Parent (claude) | Session-Start | Footprint |
|---|---|---|---|
| 34369 | 34304 | 11.09. 21:30 | 5305 MB |
| 4841 | 4766 | 10.09. 21:07 | 4978 MB |
| 1319 | 1214 | 11.09. 23:18 | 4935 MB |
| 19069 | 19020 | 10.09. 21:33 | < 400 MB (nie gesucht) |

Fünf offene Sessions, drei mit „warmem" Suchpfad, zusammen rund 15 GB. `lsof` zeigt **onnxruntime**
geladen, kein torch: die Embeddings laufen korrekt extern über Ollama, der Speicher kommt vom
fastembed-Reranker `jinaai/jina-reranker-v2-base-multilingual`, den basic-memory als ONNX-Cross-Encoder
in den eigenen Prozess lädt (`repository/rerank_provider_factory.py` — Singleton, aber **pro Prozess**).

Symptom am System: `vm.swapusage` 13159 von 14336 MB belegt, 1,87 Mio Swapouts, RSS der Prozesse nur
24–30 MB. Sie lagen vollständig im Swap; jede Vault-Suche las GB von der SSD zurück.

Zweiter, unabhängiger Schaden: `sync_changes: true` heißt, **jeder** dieser Prozesse betrieb einen
eigenen Watcher — die bekannte Quelle doppelter FTS-Zeilen und `database is locked`. Der Index hatte
tatsächlich eine doppelte Entity-Zeile (`_brainstorming/2026-09-03-umbau-v3-bericht.md`).

## Messung (isoliert, `vmmap --summary`, je frischer Prozess)

Wachstum mit der Zahl der Suchen (20 Kandidaten, bis 2000 Zeichen):

| Stufe | Footprint |
|---|---|
| Prozessstart | 7,7 MB |
| nach `import fastembed` | 58 MB |
| nach `TextCrossEncoder(...)` | 1,3 GB |
| nach 1 Rerank | 3,8 GB |
| nach 5 / 10 / 20 / 40 Reranks | 6,0 GB (konstant) |

Der ONNX-Arena-Allocator gibt nichts zurück, konvergiert aber bei 6,0 GB. Skalierung mit der Batch-Form:

| `reranker_candidates` | `reranker_max_document_chars` | Footprint |
|---|---|---|
| 20 | 2000 (heutige Config) | 5,8 GB |
| 20 | 1000 | 2,8 GB |
| 10 | 2000 | 3,2 GB |
| 10 | 1000 | 2,0 GB |
| 8 | 800 | 1,6 GB |

Wirkungslos: `semantic_embedding_threads`. Mit 1, 2 und CPU-Default identisch 1,3 / 2,8 / 3,2 GB.

## Entscheidung

Ein **geteilter** Server für alle Sessions, als launchd-Dienst:

- `com.mastermind.basic-memory` → `basic-memory mcp --transport streamable-http --host 127.0.0.1 --port 8765`,
  `RunAtLoad` + `KeepAlive`, Env `BASIC_MEMORY_MCP_PROJECT=mastermind`.
- `plugins/mastermind/.mcp.json` zeigt per `type: http` auf `http://127.0.0.1:8765/mcp`.
- `com.mastermind.basic-memory-watchdog` → alle 600 s `watchdog.py`.

Das Reranker-Modell liegt einmal statt N-mal im RAM, und es läuft **genau ein** Watcher.

Laufzeitdateien liegen unter `~/.local/share/mastermind/bin/` und `~/Library/LaunchAgents/`, bewusst
**außerhalb** von `~/.claude/plugins/cache/…`: dieser Pfad enthält die Plugin-Version und würde bei
jedem Update den launchd-Job brechen.

### Warum der Watchdog so konservativ ist

Neustart nur, wenn Footprint > 1500 MB **und** kein `claude`-Prozess läuft. MCP streamable-http vergibt
eine Session-ID, die ein neu gestarteter Server nicht kennt; ein Neustart bei offenen Sessions würde
deren Memory-Tools still brechen. Offene Sessions halten den Speicher deshalb bewusst — mit dem letzten
geschlossenen Terminal fällt der Dienst auf ~200 MB.

## Alternativen

- **Reranker abschalten** (`reranker_enabled: false`): spart 1,3–6,0 GB je Prozess ohne neue Infrastruktur,
  widerspricht aber der Decision „Vault-Suche mit Qwen3-Embedding über Ollama statt fastembed-mpnet"
  (2026-09-03). Dort steht „Reranker weglassen: nicht gemessen" — offen, kombinierbar mit dieser Lösung.
- **`reranker_candidates` senken**: 20 ist in derselben Decision festgeschrieben, bleibt unangetastet.
- **`reranker_max_document_chars` von 2000 auf 1000**: halbiert die Spitze (5,8 → 2,8 GB) und ist in
  keiner Decision festgelegt. Der Code nennt Kappungen ≥ 2000 als qualitätsneutral, darunter ungemessen —
  vor einer Umstellung wären die 25 Testfragen zu fahren.
- **Kleineres Reranker-Modell**: `ms-marco-MiniLM` und `jina-reranker-v1-*` sind Englisch-only (Vault ist
  Deutsch), `BAAI/bge-reranker-base` ist mit 1,04 GB kaum kleiner als 1,11 GB. Verworfen.
- **Threads senken**: gemessen wirkungslos. Verworfen.

## Konsequenzen

- Der Dienst wird zur Abhängigkeit: läuft er nicht, hat keine Session Gedächtnis. Dagegen `KeepAlive`,
  `RunAtLoad` und eine Warnung des SessionStart-Hooks mit dem `launchctl kickstart`-Befehl.
- Sessions auf altem Plugin-Stand starten weiter einen eigenen stdio-Server. `install.py` meldet sie,
  `repair_index.py` nennt im Kopf, ob der Watcher der Dienst oder ein stdio-Rest ist.
- Port 8765 steht an zwei Stellen (`install.py` `PORT`, `.mcp.json` `url`) und muss zusammenpassen.
- Rückweg: `python3 plugins/mastermind/server/install.py --uninstall` und `.mcp.json` auf die stdio-Form
  zurück (der Befehl druckt sie aus).

## Verifikation (2026-09-12)

- `install.py`: MCP-`initialize` beantwortet (Basic Memory 4.0.0b1), Dienst idle bei 204 MB.
- Hook mit laufendem Dienst: keine Warnung. Dienst gestoppt: `WARNING: Mastermind memory server not
  reachable …`. Danach `bootstrap` und wieder gesund.
- Watchdog: unter Schwelle „ok"; bei gestopptem Dienst „service not running".
- `repair_index.py`: erkennt „geteilter Dienst", Reparatur der doppelten Entity-Zeile erfolgreich —
  Entities 237, FTS 100 %, Observations 738/738, Relations 1083/1083, 0 Duplikate.
- Nach dem Abräumen der alten stdio-Server: Swap von 13,2 GB auf 3,7 GB.

## Nachtrag: der Watchdog zählte keine Sessions (0.4.1, `7c758da`)

Die erste Fassung zählte offene Sessions mit `pgrep -x claude` und bekam **null** zurück, während eine
Session lief — die als Sicherung gedachte Bedingung war wirkungslos, der Watchdog hätte unter einem
lebenden Client neu gestartet. `ps` zeigt denselben Prozess korrekt:

```
$ pgrep -x claude                     # leer
$ ps -Ao comm= | grep -cx claude      # 1
$ pgrep -f basic-memory               # 1   <- pgrep arbeitet grundsätzlich
```

Betroffen war reproduzierbar der `claude`-Prozess selbst (direkter Vorfahre der Shell), nicht dessen
Kinder; der Unterschied liegt zwischen `sysctl KERN_PROC` (pgrep) und libproc (ps). Der Watchdog zählt
jetzt über `ps` und behandelt eine unlesbare Prozessliste als „Sessions offen", nicht als „keine".
Festgehalten als [[pgrep findet Prozesse nicht, die ps im Bash-Tool von Claude Code zeigt]].

## Endstand 2026-09-12

| | vorher | nachher |
|---|---|---|
| MCP-Prozesse | einer je Session (5) | einer insgesamt |
| Speicher dafür | ~15 GB | 352 MB (idle ~200 MB) |
| Swap belegt | 13,2 von 14,3 GB | 3,4 von 5,1 GB |
| Watcher | 5 | 1 |
| Index | 1 doppelte Entity-Zeile | 239 Entities, 0 Duplikate, FTS 100 % |

Verifiziert: `install.py --status` (Handshake ok), Hook-Warnung bei gestopptem Dienst, Watchdog in beiden
Kontexten (direkt und über launchd), Schutzbedingung bei künstlich gesenkter Schwelle (Dienst blieb
stehen), Neustart über `bootout`/`bootstrap`, und ein echter End-to-End-Lauf: `claude -p` mit
`recent_activity` gegen den geteilten Server lieferte 10 Treffer.
