#!/usr/bin/env python3
"""Launcher for the shared basic-memory MCP server with memory guards.

Runs the normal `basic-memory` CLI (so `mcp --transport streamable-http ...` behaves exactly
as documented) after patching the fastembed reranker path. Nothing about search results
changes: same model, same candidates, same scores — only how the ONNX runtime allocates.

Why (measured 2026-09-15 with proc_pid_rusage/vmmap; basic-memory 0.23.2, fastembed 0.8.0,
onnxruntime 1.29.0, jinaai/jina-reranker-v2-base-multilingual, 20 candidates x <= 2000 chars):

  * ONNX Runtime's CPU memory arena never returns activation memory to the OS, and every
    search has a different input shape (document lengths), so the arena keeps growing:
    1.3 GB after model load -> 3.9 GB after two searches -> 5.6 GB after two concurrent
    searches, held forever. Three parallel /mastermind:wrap sessions took the service to
    17.5 GB and the machine into swap. With the arena off (`enable_cpu_mem_arena=False`,
    the one session option fastembed exposes) the process is back at ~1.4 GB after every
    call.
  * basic-memory runs each rerank in its own thread with no lock, so concurrent searches
    add their transient peaks. The lock below serialises them; one rerank of 20 documents
    takes 2-3 s, so a queued search waits at most that long.
  * batch_size 4 instead of fastembed's default 64 cuts the transient peak from
    +1.1-1.8 GB to +20-160 MB and is not slower (less padding per batch): 2.2-2.8 s vs
    2.9-3.7 s for 20 documents.
  * The loaded model costs ~1.1 GB and reloads from the local cache in 0.6 s, so after
    IDLE_UNLOAD_S without a search it is dropped; the next search pays the 0.6 s.

Every patch checks what it replaces. If a basic-memory or fastembed update changes shape,
the server starts unpatched and says so on stderr (server.log) instead of failing.

Environment knobs: MASTERMIND_RERANK_BATCH (4), MASTERMIND_RERANK_IDLE_UNLOAD_S (600;
0 disables unloading), MASTERMIND_RERANK_ARENA (0; 1 keeps the ONNX arena).
"""

from __future__ import annotations

import asyncio
import gc
import os
import sys
import threading
import time

BATCH = max(1, int(os.environ.get("MASTERMIND_RERANK_BATCH", "4")))
IDLE_UNLOAD_S = float(os.environ.get("MASTERMIND_RERANK_IDLE_UNLOAD_S", "600"))
ARENA = os.environ.get("MASTERMIND_RERANK_ARENA", "0") == "1"
CHECK_EVERY_S = 30.0


def say(msg: str) -> None:
    print(f"[mastermind-server] {msg}", file=sys.stderr, flush=True)


class _State:
    lock = threading.Lock()  # serialises reranks; also guards unloading
    last_used = time.monotonic()
    providers: list = []  # FastEmbedRerankProvider instances that ran a rerank


def patch_cross_encoder() -> bool:
    """Make every TextCrossEncoder basic-memory constructs run without the ONNX arena."""
    try:
        import fastembed.rerank.cross_encoder as fe
    except Exception as exc:  # fastembed missing: basic-memory will report it itself
        say(f"cross-encoder not patched: {exc!r}")
        return False
    base = getattr(fe, "TextCrossEncoder", None)
    if base is None or not hasattr(base, "rerank"):
        say("cross-encoder not patched: fastembed.rerank.cross_encoder.TextCrossEncoder missing")
        return False

    class MastermindTextCrossEncoder(base):  # type: ignore[misc,valid-type]
        def __init__(self, model_name: str, *args, **kwargs):
            kwargs.setdefault("enable_cpu_mem_arena", ARENA)
            super().__init__(model_name, *args, **kwargs)

    MastermindTextCrossEncoder.__name__ = base.__name__
    MastermindTextCrossEncoder.__qualname__ = base.__qualname__
    fe.TextCrossEncoder = MastermindTextCrossEncoder
    return True


def patch_rerank_provider() -> bool:
    """Serialise reranks, use small batches, and track use for the idle unloader."""
    try:
        from basic_memory.repository import fastembed_rerank_provider as mod
    except Exception as exc:
        say(f"reranker not patched: {exc!r}")
        return False
    cls = getattr(mod, "FastEmbedRerankProvider", None)
    sigmoid = getattr(mod, "_sigmoid", None)
    validate = getattr(mod, "validate_rerank_scores", None)
    if cls is None or not all(hasattr(cls, a) for a in ("rerank", "_load_model")) or not sigmoid or not validate:
        say("reranker not patched: FastEmbedRerankProvider changed shape")
        return False

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        if self not in _State.providers:
            _State.providers.append(self)
        _State.last_used = time.monotonic()
        model = await self._load_model()

        def run() -> list[float]:
            with _State.lock:
                _State.last_used = time.monotonic()
                scores = [sigmoid(float(s)) for s in model.rerank(query, documents, batch_size=BATCH)]
                _State.last_used = time.monotonic()
                return scores

        scores = await asyncio.to_thread(run)
        return validate(scores, len(documents))

    cls.rerank = rerank
    return True


def unloader() -> None:
    """Drop the cross-encoder after IDLE_UNLOAD_S without a rerank (reload costs ~0.6 s)."""
    while True:
        time.sleep(CHECK_EVERY_S)
        idle = time.monotonic() - _State.last_used
        if idle < IDLE_UNLOAD_S:
            continue
        for provider in list(_State.providers):
            if getattr(provider, "_model", None) is None:
                continue
            with _State.lock:  # never while a rerank is running
                if time.monotonic() - _State.last_used < IDLE_UNLOAD_S:
                    break
                provider._model = None
            gc.collect()
            say(f"reranker unloaded after {int(idle)} s idle")


def main() -> None:
    patched = patch_cross_encoder() and patch_rerank_provider()
    say(
        f"start: patched={patched} arena={'on' if ARENA else 'off'} batch={BATCH} "
        f"idle_unload={int(IDLE_UNLOAD_S)}s stateless_http={os.environ.get('FASTMCP_STATELESS_HTTP', 'unset')}"
    )
    if patched and IDLE_UNLOAD_S > 0:
        threading.Thread(target=unloader, name="mastermind-rerank-unloader", daemon=True).start()
    sys.argv[0] = "basic-memory"
    from basic_memory.cli.main import app

    sys.exit(app())


if __name__ == "__main__":
    main()
