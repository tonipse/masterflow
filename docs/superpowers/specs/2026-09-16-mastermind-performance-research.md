# Mastermind: Performance und Ressourcen — Analyse und Recherche

> Status: Entwurf. Die 4B-Messung wurde am 2026-09-16 abgebrochen (Laptop zu heiß); anschließend wurden Mastermind-Dienst, Watchdog, Ollama und das Plugin bis auf Weiteres abgeschaltet — siehe `2026-09-16-prozess-snapshot.md` und den Abschnitt „Abgeschaltet" am Ende.

Datum: 2026-09-16. Stand nach 0.5.0 (Reranker-Speicherschutz, Stateless-Server). Frage: Was kostet das
System noch, und wo lässt sich mit vertretbarem Risiko sparen oder beschleunigen?
Quellen: Messskripte im Scratchpad der Session 2920a2c7 (`latency.py`, `coreml_test.py`, `rerank_compare.py`,
`embed_eval.py`, `questions.json`), `~/.basic-memory/basic-memory.log`, `~/.basic-memory/memory.db`,
Ollama-API (`/api/ps`, `/api/embed`), Quellcode basic-memory 0.23.2 / fastembed 0.8.0 / litellm, Web-Quellen
am Ende. Leitplanke: Retrieval-Decision vom 2026-09-03 (Modell, Schwelle, Reranker); Vorschläge, die sie
berühren, sind als Entscheidung markiert.

## Empfehlung (Reihenfolge nach Nutzen je Risiko)

1. **Reranker auf Metal statt CPU** — gleiches Modell (`jina-reranker-v2-base-multilingual`) als GGUF Q8_0
   über `llama-server`: 0,3–0,4 s statt 3,3–3,9 s je Suche, −1,1 GB im Python-Dienst, +546 MB für den
   llama-server. Umsetzung im vorhandenen Launcher `server.py` (Sigmoid auf die Logits, Fallback auf
   fastembed), als dritter LaunchAgent. Kein Decision-Konflikt (Modell bleibt), aber Q8-Quantisierung:
   Ranking-Korrelation 0,91–0,99 — vor dem Umstieg den 30-Fragen-Katalog durch die ganze Pipeline laufen lassen.
2. **Ollama-Kontext auf 1024 und ein Slot** (`OLLAMA_CONTEXT_LENGTH=1024`, `OLLAMA_NUM_PARALLEL=1` in der
   brew-plist): 6,28 → ~5,1–5,4 GB geladen, ohne Qualitätseffekt — kein Chunk ist länger als 900 Zeichen
   (≈ 280 Token), Anfragen sind kürzer. Trivial, sofort, kein Decision-Konflikt.
3. **`OLLAMA_KEEP_ALIVE` von 5 min auf 1–2 min**: Der Kaltstart des 8B-Modells dauert 1,0 s (gemessen, nicht
   10–20 s wie in der Decision notiert), das Modell darf also früher aus dem Speicher. Spart die 6 GB in den
   meisten Leerlaufphasen. Kein Decision-Konflikt, aber die Decision-Notiz braucht den korrigierten Wert.
4. **Embedding-Modell** — Entscheidung für Toni, mit Messung statt Vermutung (Tabelle unten):
   4B wurde nicht zu Ende gemessen (Lauf am 2026-09-16 abgebrochen; das Modell liegt in Ollama bereit, 4,09 GB geladen); 0.6B verliert deutlich (hits@3 26/30 statt 29/30). Matryoshka-Kürzung der bestehenden
   8B-Vektoren auf 1024 Dimensionen hält hits@3 bei 29/30 und würde die Datenbank von 142 MB auf ~50 MB
   schrumpfen, spart aber keine Inferenz — für sich allein zweitrangig.
5. **Nicht weiterverfolgen**: CoreML für den ONNX-Reranker (scheitert an dynamischen Formen), Upgrades von
   basic-memory/fastembed (0.23.2 und 0.8.0 sind die aktuellen Versionen, kein Fix in Sicht), Hooks und
   Plugin-Kontext (80–130 ms bzw. 658 Token, vernachlässigbar), Ollama-Rerank (kein Endpunkt).

## Wo die Zeit hingeht

Hybride Suche über den Live-Dienst (`search_notes`, 5 Treffer), Ollama warm:

| Pfad | Dauer | Anteil |
|---|---|---|
| Volltext (BM25, `search_type: text`) | 0,01–0,04 s | — |
| Vektorsuche (`search_type: vector`, inkl. Query-Embedding über Ollama) | 0,46–0,50 s | ~12 % |
| **Rerank 20 Kandidaten, fastembed CPU, Batch 4** | **~3,0–3,3 s** | **~85 %** |
| hybrid gesamt | 3,9 s (einmal 0,74 s bei wenigen Kandidaten) | 100 % |

Standalone-Messung des Rerankers (20 Dokumente, 300–2000 Zeichen): CPU Batch 4 2,2–2,4 s, CPU Batch 20
3,1–3,5 s, **Metal (llama-server, Q8_0, ein Slot) 0,34–0,40 s**, vier Slots 0,27 s.

Sync einer neuen Notiz: Embedding über Ollama mit ~490 Token/s (16 Chunks, 4 339 Token, 8,8 s); eine Notiz
hat im Schnitt 20 Chunks à 233 Zeichen → rund 10 s GPU-Zeit je Notiz. Unter Speicherdruck am 2026-09-15
lagen die geloggten Werte bei 10–44 s je Notiz. 0.6B schafft 3 000 Token/s; 4B wurde nicht zu Ende gemessen.

## Wo der Speicher hingeht (Physical footprint, Stand 2026-09-16)

| Prozess | Speicher | Bemerkung |
|---|---|---|
| Ollama-Runner mit `qwen3-embedding:8b` | 6,28 GB geladen (4,7 GB Modell Q4_K_M + 1,25 GB Kontext) | Kontext 4096: 5,03 GB bei 512, 5,39 GB bei 1024, 6,28 GB bei 4096 |
| Mastermind-Dienst (`server.py`) | 0,2 GB ohne Modell, 1,7 GB mit Reranker, Spitze 2,1 GB | seit 0.5.0; vorher 6–17,5 GB |
| 8 offene Claude-Sessions | ~3 GB (300–480 MB je Prozess) | nicht Mastermind |
| VM (`com.apple.Virtualization`), VS Code, Slack | 3,6 GB, ~3 GB, ~0,8 GB | nicht Mastermind |
| Index `memory.db` | 142 MB (5 942 Chunks × 4096 Dim × 4 Byte = 96 MB Vektoren) | MRL 1024 → ~50 MB |

## Reranker: CPU, CoreML, Metal

- **CoreML-Provider** (onnxruntime 1.29.0 bringt ihn mit, fastembed reicht `providers` durch): scheitert an
  diesem Modell — Standardformat „Unable to compute the prediction", MLProgram „unbounded dimension which
  is not supported" (dynamische Sequenzlängen, Einsum-Attention). Nur mit festen Padding-Buckets denkbar;
  nicht über fastembed. Verworfen.
- **llama-server** (brew `llama.cpp` 0.4.1, build 10964) mit `gpustack/jina-reranker-v2-base-multilingual-GGUF:Q8_0`,
  `--embedding --pooling rank --reranking -c 1024 -np 1`: 546 MB Footprint, 0,34–0,40 s je 20 Notizen.
  Vergleich mit fastembed auf 20 echten Notizen (Ø 1 676 Zeichen) und vier Fragen: Spearman 0,986 / 0,982 /
  0,910 / 0,985, Top-1 gleich in 3 von 4, Top-5-Überschneidung 5/5, 4/5, 3/5, 5/5.
- Haken: llama-server liefert **rohe Logits** (−3,7 … −0,95) im Feld `relevance_score`; basic-memorys
  `validate_rerank_scores` verlangt [0, 1] → der `litellm`-Reranker-Pfad (`infinity/…` + `reranker_api_base`)
  bricht mit `RerankProviderContractError` ab. Deshalb der Weg über `server.py`: `rerank` ersetzt (wie heute
  schon), POST an `http://127.0.0.1:<port>/v1/rerank`, Sigmoid, bei Fehler fastembed wie bisher. Ollama selbst
  hat keinen Rerank-Endpunkt (Issue #3368 offen, PR #7219 offen). llama.cpp-Issue #16407 meldet abweichende
  Rerank-Werte für Qwen3-/BGE-Reranker, jina v2 „not too bad" — deckt sich mit der Korrelation oben, ist aber
  der Grund für den Pipeline-Test vor dem Umstieg.
- Betriebskosten des Wegs: ein dritter LaunchAgent (`llama-server`, ~19 MB Binary, GGUF ~300 MB unter
  `~/Library/Caches/llama.cpp/`), 546 MB dauerhaft (kein Idle-Entladen; könnte der Watchdog übernehmen).

## Embedding-Modell: gemessen statt vermutet

30 deutsche Umschreibungen mit bekannter Zielnotiz (`questions.json`), Ranking der Entities über den besten
Chunk, Query-Präfix wie in der Produktion. 8B nutzt die Produktionsvektoren (5 935 Chunks), 0.6B und 4B wurden
frisch über Ollama eingebettet. Alle drei Varianten unterstützen Matryoshka (32–4 096 Dimensionen, Modellkarte).

| Modell (Ollama-Tag) | geladen | Durchsatz | Dim | hits@1 | hits@3 | hits@5 | MRR | Top-1-Ähnlichkeit (Median / min) |
|---|---|---|---|---|---|---|---|---|
| 8b (Q4_K_M, 4,7 GB) | 6,28 GB | ~490 Tok/s | 4096 | 21/30 | **29/30** | 30/30 | 0,842 | 0,816 / 0,678 |
| 8b, MRL 2048 | — | — | 2048 | 22/30 | 29/30 | 30/30 | 0,853 | 0,822 / 0,675 |
| 8b, MRL 1024 | — | — | 1024 | 19/30 | 29/30 | 30/30 | 0,803 | 0,832 / 0,691 |
| 8b, MRL 512 | — | — | 512 | 18/30 | 29/30 | 30/30 | 0,781 | 0,819 / 0,685 |
| 4b (Q4_K_M, 2,5 GB) | 4,09 GB | nicht gemessen | 2560 | — | — | — | — | Messung abgebrochen |
| 4b, MRL 1024 | — | — | 1024 | — | — | — | — | — |
| 0.6b (639 MB) | 2,15 GB | 3 000 Tok/s | 1024 | 19/30 | 26/30 | 28/30 | 0,771 | 0,800 / 0,664 |
| 0.6b, MRL 512 | — | — | 512 | 19/30 | 27/30 | 28/30 | 0,769 | 0,805 / 0,678 |

Einordnung: MTEB multilingual laut Modellkarte 70,58 (8B) / 69,45 (4B) / 64,33 (0.6B). Die Schwelle 0,60
bleibt bei allen Varianten unter der schwächsten Top-1-Ähnlichkeit (min 0,66–0,69). Ein Modellwechsel heißt
alle 5 942 Chunks neu einbetten (Dauer für 4B nicht gemessen; über den Server-Pfad laut Decision, nie `reindex`).

## Ollama-Knöpfe (Doku + Messung)

| Knopf | Default | Messung / Wirkung |
|---|---|---|
| `OLLAMA_CONTEXT_LENGTH` | 4096 | 8B: 5,03 GB bei 512, 5,39 GB bei 1024, 6,28 GB bei 4096; Chunks ≤ 900 Zeichen ≈ 280 Token, Query-Präfix + Frage < 100 Token → 1024 reicht mit Reserve |
| `OLLAMA_NUM_PARALLEL` | 1 („mit automatischer Skalierung"), Doku: RAM skaliert mit `NUM_PARALLEL × CONTEXT_LENGTH` | Ollama-Log zeigt vier Slots; basic-memory schickt `semantic_embedding_request_concurrency: 4` — mit einem Slot serialisiert der Sync, für den Nutzer unsichtbar |
| `OLLAMA_KEEP_ALIVE` | 5 min | Kaltstart 8B 1,0 s (Page-Cache warm), warm 0,11 s; 1–2 min sind vertretbar |
| `dimensions` im `/api/embed` | — | funktioniert (1024 zurück); basic-memory: `semantic_embedding_dimensions` + `semantic_embedding_forward_dimensions: true`, danach Neu-Embedding |
| `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0` | aus / f16 | bereits gesetzt (brew-plist) |

Gesetzt wird das in `~/Library/LaunchAgents/homebrew.mxcl.ollama.plist` (EnvironmentVariables), danach
`brew services restart ollama`.

## Was sonst noch geprüft wurde

- Hooks: SessionStart 80–130 ms, UserPromptSubmit 20–30 ms; Plugin-Kontext 658 Token always-on. Nichts zu holen.
- basic-memory 0.23.2 (2026-08-25) und fastembed 0.8.0 (2026-03-23) sind die aktuellen Releases; kein
  Upstream-Fix für Arena, Sperre oder Reranker-Provider. onnxruntime 1.30.0 und fastmcp 4.0.3 wären neuer,
  ändern aber nichts am Befund.
- fastembed kennt nur sechs Cross-Encoder; multilingual sind allein `bge-reranker-base` (1,04 GB, 512 Token)
  und jina v2 (1,11 GB). Keine quantisierten Reranker.
- Chunking: 5 942 Chunks, Ø 233 Zeichen, max 900. Kleine Chunks kosten kaum zusätzliche Token (kein
  Dokument-Präfix), vergrößern aber die Vektortabelle; nicht konfigurierbar in 0.23.2 (kein `chunk`-Feld in
  `config_models.py`).
- Parallele Wraps: Reranks sind seit 0.5.0 serialisiert; drei parallele Suchen warten heute bis ~10 s
  aufeinander, mit Metal-Rerank unter 1 s.

## Nächste Schritte, falls gewünscht

1. 0.6.0: `server.py` rerankt über llama-server (Sigmoid, Fallback), `install.py` legt den dritten LaunchAgent
   an, Watchdog stoppt ihn im Leerlauf; vorher `questions.json` durch `search_notes` (hybrid) mit beiden
   Rerankern — Abbruch, wenn hits@3 sinkt.
2. Ollama-plist: `OLLAMA_CONTEXT_LENGTH=1024`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=2m`; Decision-Notiz
   mit dem gemessenen Kaltstart aktualisieren.
3. Entscheidung Embedding-Modell (Punkt 4) — bei Wechsel als geplanter Eingriff mit Sicherung und
   Neu-Embedding über den Server-Pfad, danach `questions.json` als Regressionstest.

## Aufräumen nach der Analyse

Heruntergeladen bzw. installiert und noch vorhanden: `qwen3-embedding:0.6b` (639 MB) und `qwen3-embedding:4b`
(2,5 GB) in Ollama (`ollama rm …`), `llama.cpp` 0.4.1 über brew (`brew uninstall llama.cpp`), GGUF-Cache
`~/Library/Caches/llama.cpp/` (~300 MB). Der llama-server-Testprozess ist beendet, der Live-Dienst unverändert.

## Web-Quellen

- Qwen3-Embedding-Modellkarte (MTEB, MRL 32–4096, Kontext): https://huggingface.co/Qwen/Qwen3-Embedding-8B
- Ollama-Tags und Größen: https://ollama.com/library/qwen3-embedding/tags
- Ollama-FAQ (Kontext, Parallelität, Keep-Alive): https://docs.ollama.com/faq
- Ollama ohne Rerank-Endpunkt: https://github.com/ollama/ollama/issues/3368, https://github.com/ollama/ollama/pull/7219
- llama.cpp-Server, Rerank-Endpunkt: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- llama.cpp Rerank-Abweichungen: https://github.com/ggml-org/llama.cpp/issues/16407
- jina v2 als GGUF: https://huggingface.co/gpustack/jina-reranker-v2-base-multilingual-GGUF
- LiteLLM Rerank-Provider: https://docs.litellm.ai/docs/rerank
- CoreML-EP und dynamische Formen: https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html,
  https://macgpu.com/en/blog/2026-0420-mac-onnx-runtime-coreml-ep-vs-cpu-dynamic-shapes-remote.html
- MRL-Benchmark Qwen3-8B (FR/EN/JP, 512d ≈ 4096d): https://github.com/lelabdev/embedding-benchmark
- basic-memory-Releases (0.23.2 aktuell): https://github.com/basicmachines-co/basic-memory/releases

## Abgeschaltet am 2026-09-16

Auf Wunsch bis auf Weiteres gestoppt, damit die Nachtsessions ohne diese Last laufen: die 4B-Messung
(`pkill -f "embed_eval.py 4b"`), Ollama (`brew services stop ollama`, Modelle vorher entladen), der
Mastermind-Dienst und der Watchdog (`launchctl bootout` plus `launchctl disable`), das Plugin
(`claude plugin disable mastermind@masterflow`). Wieder einschalten:

```bash
brew services start ollama
claude plugin enable mastermind@masterflow
python3 ~/Desktop/masterflow/plugins/mastermind/server/install.py   # enable + bootstrap beider Agents, Health-Check
```

Danach muss `install.py --status` `stateless` und `patched=True` zeigen. Die Messung lässt sich mit
`embed_eval.py 4b` wiederholen; Skript und `questions.json` liegen im Scratchpad der Session 2920a2c7 und sind oben beschrieben.
