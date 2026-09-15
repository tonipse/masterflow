# Prozess-Snapshot vor dem Abschalten — 2026-09-16 05:27:16 +07

Aufgenommen unmittelbar bevor die laufende 4B-Messung, Ollama, der Mastermind-Dienst und der Watchdog gestoppt wurden. Hinweis: Die 4B-Messung (`embed_eval.py`, Embedding von 5 942 Chunks) und die dafür geladenen Modelle `qwen3-embedding:4b` und `:8b` waren zu diesem Zeitpunkt selbst ein großer Teil der Last.

## Speicher und Swap
```
vm.swapusage: total = 8192.00M  used = 6865.12M  free = 1326.88M  (encrypted)
System-wide memory free percentage: 20%
Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     3939.
Pages active:                                 151068.
Pages inactive:                               149516.
Pages speculative:                               554.
Pages throttled:                                   0.
Pages wired down:                             808993.
```

## Thermik / CPU-Drossel (pmset -g therm)
```
Note: No thermal warning level has been recorded
Note: No performance warning level has been recorded
Note: No CPU power status has been recorded
```

## Top 25 nach Speicher (top -o mem)
```
Processes: 516 total, 4 running, 512 sleeping, 4465 threads 
2026/09/16 05:27:17
Load Avg: 2.10, 2.95, 3.13 
CPU usage: 11.71% user, 16.17% sys, 72.11% idle 
PID    PPID  COMMAND          MEM   %CPU #TH    STATE   
17047  811   llama-server     5479M 0.0  20     sleeping
90742  1     com.apple.Virtua 3590M 0.0  19     sleeping
14012  1     python3.12       1780M 0.0  29     sleeping
405    1     WindowServer     752M  0.0  20     sleeping
27189  26011 Code Helper (Plu 695M  0.0  10     sleeping
17100  811   llama-server     624M  0.0  28     sleeping
1468   1465  Code Helper      614M  0.0  19     sleeping
4509   4506  python3.12       590M  0.0  2      sleeping
5223   1465  Code Helper (Ren 573M  0.0  23     sleeping
25452  1465  Code Helper (Ren 471M  0.0  21/1   running 
26002  1465  Code Helper (Ren 464M  0.0  23     sleeping
1465   1     Code             455M  0.0  56     sleeping
3692   1465  Code Helper (Ren 411M  0.0  23     sleeping
25515  1465  Code Helper (Plu 409M  0.0  30     sleeping
94671  94646 Slack Helper (Re 409M  0.0  17     sleeping
3694   1465  Code Helper (Plu 357M  0.0  30     sleeping
26058  25456 2.1.268          357M  0.0  23     sleeping
25513  1465  Code Helper (Ren 357M  0.0  23     sleeping
25454  1465  Code Helper (Plu 338M  0.0  30     sleeping
5224   1465  Code Helper (Plu 324M  0.0  32     sleeping
43218  42664 2.1.272          306M  0.0  22     sleeping
33318  18552 2.1.269          306M  0.0  22     sleeping
26011  1465  Code Helper (Plu 303M  0.0  32     sleeping
88597  88056 2.1.272          293M  0.0  21     sleeping
86885  3696  2.1.268          285M  0.0  23     sleeping
```

## Top 15 nach CPU (ps -r)
```
  PID  PPID  %CPU    RSS     ELAPSED COMMAND
25452  1465  26.7 354672 04-05:37:14 /Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper (Renderer).app/Contents/MacOS/Code Helper (Renderer) --type=renderer --user-data-dir=/Users/to
17100   811  12.0 2762304       03:32 /opt/homebrew/Cellar/ollama/0.33.2/libexec/lib/ollama/llama-server --model /Users/toni/.ollama/models/blobs/sha256-2b0cf8f17b4c723c27303015383c27ec4bf2d8314bb677d
26058 25456   8.7 286224 04-05:37:08 claude --dangerously-skip-permissions
90894 90733   5.5  90192 03-16:27:04 /Applications/Docker.app/Contents/MacOS/Docker Desktop.app/Contents/Frameworks/Docker Desktop Helper (Renderer).app/Contents/MacOS/Docker Desktop Helper (Renderer)
  405     1   5.0  38096 05-08:24:10 /System/Library/PrivateFrameworks/SkyLight.framework/Resources/WindowServer -daemon
35883     1   3.5  65344 05-07:19:23 /Applications/NordVPN.app/Contents/MacOS/NordVPN
 1465     1   2.7 121952 05-08:22:00 /Applications/Visual Studio Code.app/Contents/MacOS/Code
90742     1   2.7 184384 03-16:27:06 /System/Library/Frameworks/Virtualization.framework/Versions/A/XPCServices/com.apple.Virtualization.VirtualMachine.xpc/Contents/MacOS/com.apple.Virtualization.Virt
 1468  1465   2.1  42592 05-08:21:59 /Applications/Visual Studio Code.app/Contents/Frameworks/Code Helper.app/Contents/MacOS/Code Helper --type=gpu-process --user-data-dir=/Users/toni/Library/Applicat
81863 81809   2.0  68800 05-00:24:35 /Applications/Wispr Flow.app/Contents/Frameworks/Wispr Flow Helper (Renderer).app/Contents/MacOS/Wispr Flow Helper (Renderer) --type=renderer --user-data-dir=/User
65734     1   1.9  69120    07:03:48 /Applications/WhatsApp.app/Contents/MacOS/WhatsApp
 8016     1   1.6  41200       09:54 /System/Applications/Utilities/Activity Monitor.app/Contents/MacOS/Activity Monitor
81860 81809   1.6  24128 05-00:24:35 /Applications/Wispr Flow.app/Contents/Resources/swift-helper-app-dist/Wispr Flow.app/Contents/MacOS/Wispr Flow
78302 77791   1.4 100128    15:15:16 claude --dangerously-skip-permissions
19621 19097   1.3 132272    09:59:24 claude --dangerously-skip-permissions
```

## llama-, python-, ollama-, claude-Prozesse
```
  811     1   0.4  32912 05-08:24:04 /opt/homebrew/opt/ollama/bin/ollama serve
 4509  4506   0.0  17072       12:39 /Users/toni/.local/share/uv/tools/basic-memory/bin/python embed_eval.py 4b
14012     1   0.1  32176       05:49 /Users/toni/.local/share/uv/tools/basic-memory/bin/python /Users/toni/.local/share/mastermind/bin/server.py mcp --transport streamable-http --host 127.0.0.1 --port 8765
17047   811   0.0 4892128       03:35 /opt/homebrew/Cellar/ollama/0.33.2/libexec/lib/ollama/llama-server --model /Users/toni/.ollama/models/blobs/sha256-3fcd3febec8b3fd64435204db75bf0dd73b91e8d0661e0331acfe7e7c3120b85 --
17100   811  12.0 2762304       03:32 /opt/homebrew/Cellar/ollama/0.33.2/libexec/lib/ollama/llama-server --model /Users/toni/.ollama/models/blobs/sha256-2b0cf8f17b4c723c27303015383c27ec4bf2d8314bb677d05e920dd70bb0f16b --
86885  3696   0.5 125424 04-04:24:44 claude --dangerously-skip-permissions
33318 18552   0.3 154688 03-17:32:28 claude --dangerously-skip-permissions
43218 42664   0.2 174192    15:59:31 claude --dangerously-skip-permissions
78302 77791   1.4 100112    15:15:16 claude --dangerously-skip-permissions
21844 21337   0.0  93760 02-06:51:06 claude --dangerously-skip-permissions
88597 88056   0.3 152384    10:44:33 claude --dangerously-skip-permissions
26058 25456   8.7 285664 04-05:37:08 claude --dangerously-skip-permissions
42428 41943   0.1 122464    05:29:24 claude --dangerously-skip-permissions
19621 19097   1.3 132208    09:59:24 claude --dangerously-skip-permissions
27589 26276   0.1 129808    05:39:03 claude --dangerously-skip-permissions
```

## Ollama: geladene Modelle
```
qwen3-embedding:8b 6.28 GB ctx 4096 expires 2026-09-16T05:31:40
qwen3-embedding:4b 4.09 GB ctx 4096 expires 2026-09-16T05:30:16
```

## launchd-Dienste
```
com.mastermind.basic-memory:  state = running; pid = 14012;
com.mastermind.basic-memory-watchdog:  state = not running; state = active;
homebrew.mxcl.ollama:  state = running; pid = 811;
```

## Mastermind-Dienst
```
Physical footprint:         1.7G
2026-09-16 00:39:39 pid 55222: 1843 MB < 3000 MB threshold; ok
2026-09-16 00:49:41 pid 55222: 524 MB < 3000 MB threshold; ok
2026-09-16 05:18:43 pid 55222: 1843 MB < 3000 MB threshold; ok
[mastermind-server] reranker unloaded after 603 s idle
[mastermind-server] reranker unloaded after 622 s idle
[mastermind-server] start: patched=True arena=off batch=4 idle_unload=600s stateless_http=true
```
