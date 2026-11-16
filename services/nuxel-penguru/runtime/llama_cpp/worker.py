#!/usr/bin/env python3
"""Unprivileged llama.cpp worker (no TCP listener, no network, no secrets).

Reads one JSON job from stdin, loads a GGUF package through libllama, streams
bounded events to stdout and exits.  The control plane starts it with a
read-only package path, a CPU/memory limit and no broker credentials.

Event vocabulary (see common/worker_protocol.py):
  loading -> loaded -> token* -> done            (generate)
  loading -> loaded -> done                      (load_test)
  loading -> loaded -> token* -> done            (self_test)
Any failure -> error (and unload).
"""
from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, Optional

SCHEMA_VERSION = 1
EVENT_KINDS = {"loading", "loaded", "token", "progress", "cancelled", "oom",
               "error", "unloaded", "done", "health"}
LIB = os.environ.get("NUXEL_LLAMA_LIB", "")


def emit(event: str, **data: Any) -> None:
    if event not in EVENT_KINDS:
        raise SystemExit("worker: invalid event %r" % event)
    doc = {"schema_version": SCHEMA_VERSION, "event": event}
    doc.update(data)
    sys.stdout.write(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n")
    sys.stdout.flush()


def fail(code: str, detail: str = "") -> None:
    emit("error", code=code, detail=detail)


# Exact layouts for the pinned llama.cpp (verified against sizeof on the target:
# model=80, ctx=176, batch=56, sampler_chain_params=1).
class LlamaBatch(ctypes.Structure):
    _fields_ = [
        ("n_tokens", ctypes.c_int32),
        ("token", ctypes.POINTER(ctypes.c_int32)),
        ("embd", ctypes.POINTER(ctypes.c_float)),
        ("pos", ctypes.POINTER(ctypes.c_int32)),
        ("n_seq_id", ctypes.POINTER(ctypes.c_int32)),
        ("seq_id", ctypes.POINTER(ctypes.POINTER(ctypes.c_int32))),
        ("logits", ctypes.POINTER(ctypes.c_int8)),
    ]


class SamplerChainParams(ctypes.Structure):
    _fields_ = [("no_perf", ctypes.c_bool)]


ABORT_CB = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p)


class LibLlama:
    """Minimal ctypes surface: enough to load a GGUF and prove generation."""

    def __init__(self, path: Optional[str] = None):
        candidates = [path or LIB, "libllama.so", ctypes.util.find_library("llama"),
                      "/usr/local/lib/libllama.so"]
        self.lib = None
        for c in candidates:
            if not c:
                continue
            try:
                self.lib = ctypes.CDLL(c)
                self.path = c
                break
            except OSError:
                continue
        if self.lib is None:
            raise RuntimeError("libllama not found")
        self._bind()

    def _bind(self):
        L = self.lib
        vp = ctypes.c_void_p
        L.llama_backend_init.restype = None
        L.llama_backend_init.argtypes = []
        L.llama_version.restype = ctypes.c_char_p
        L.llama_model_default_params.restype = vp
        L.llama_model_default_params.argtypes = []
        L.llama_model_load_from_file.restype = vp
        L.llama_model_load_from_file.argtypes = [ctypes.c_char_p, vp]
        L.llama_model_free.restype = None
        L.llama_model_free.argtypes = [vp]
        L.llama_model_n_params.restype = ctypes.c_uint64
        L.llama_model_n_params.argtypes = [vp]
        L.llama_model_get_vocab.restype = vp
        L.llama_model_get_vocab.argtypes = [vp]
        L.llama_vocab_n_tokens.restype = ctypes.c_int32
        L.llama_vocab_n_tokens.argtypes = [vp]
        L.llama_vocab_is_eog.restype = ctypes.c_bool
        L.llama_vocab_is_eog.argtypes = [vp, ctypes.c_int32]
        L.llama_model_meta_val_str.restype = ctypes.c_int32
        L.llama_model_meta_val_str.argtypes = [vp, ctypes.c_char_p,
                                                ctypes.c_char_p, ctypes.c_size_t]
        L.llama_context_default_params.restype = vp
        L.llama_context_default_params.argtypes = []
        L.llama_init_from_model.restype = vp
        L.llama_init_from_model.argtypes = [vp, vp]
        L.llama_free.restype = None
        L.llama_free.argtypes = [vp]
        L.llama_tokenize.restype = ctypes.c_int32
        L.llama_tokenize.argtypes = [vp, ctypes.c_char_p, ctypes.c_int32, vp,
                                      ctypes.c_int32, ctypes.c_bool, ctypes.c_bool]
        L.llama_decode.restype = ctypes.c_int32
        L.llama_decode.argtypes = [vp, LlamaBatch]
        L.llama_sampler_chain_default_params.restype = SamplerChainParams
        L.llama_sampler_chain_default_params.argtypes = []
        L.llama_sampler_chain_init.restype = vp
        L.llama_sampler_chain_init.argtypes = [SamplerChainParams]
        L.llama_sampler_chain_add.restype = None
        L.llama_sampler_chain_add.argtypes = [vp, vp]
        L.llama_sampler_init_greedy.restype = vp
        L.llama_sampler_init_greedy.argtypes = []
        L.llama_sampler_sample.restype = ctypes.c_int32
        L.llama_sampler_sample.argtypes = [vp, vp, ctypes.c_int32]
        L.llama_sampler_accept.restype = None
        L.llama_sampler_accept.argtypes = [vp, ctypes.c_int32]
        L.llama_sampler_free.restype = None
        L.llama_sampler_free.argtypes = [vp]
        L.llama_token_to_piece.restype = ctypes.c_int32
        L.llama_token_to_piece.argtypes = [vp, ctypes.c_int32, ctypes.c_char_p,
                                            ctypes.c_int32, ctypes.c_int32,
                                            ctypes.c_bool]
        L.llama_batch_init.restype = LlamaBatch
        L.llama_batch_init.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        L.llama_batch_free.restype = None
        L.llama_batch_free.argtypes = [LlamaBatch]
        L.llama_set_abort_callback.restype = None
        L.llama_set_abort_callback.argtypes = [vp, ABORT_CB, ctypes.c_void_p]
        # Keep bound functions on self so call sites never rely on attribute
        # lookup through the CDLL object's name mangling.
        self.backend_init = L.llama_backend_init
        self.model_default_params = L.llama_model_default_params
        self.model_load = L.llama_model_load_from_file
        self.model_free = L.llama_model_free
        self.model_n_params = L.llama_model_n_params
        self.model_get_vocab = L.llama_model_get_vocab
        self.vocab_n_tokens = L.llama_vocab_n_tokens
        self.vocab_is_eog = L.llama_vocab_is_eog
        self.meta_val_str = L.llama_model_meta_val_str
        self.context_default_params = L.llama_context_default_params
        self.init_from_model = L.llama_init_from_model
        self.free_ctx = L.llama_free
        self.tokenize = L.llama_tokenize
        self.decode = L.llama_decode
        self.sampler_chain_default = L.llama_sampler_chain_default_params
        self.sampler_chain_init = L.llama_sampler_chain_init
        self.sampler_chain_add = L.llama_sampler_chain_add
        self.sampler_init_greedy = L.llama_sampler_init_greedy
        self.sampler_sample = L.llama_sampler_sample
        self.sampler_accept = L.llama_sampler_accept
        self.sampler_free = L.llama_sampler_free
        self.token_to_piece = L.llama_token_to_piece
        self.batch_init = L.llama_batch_init
        self.batch_free = L.llama_batch_free
        self.set_abort_callback = L.llama_set_abort_callback
        self.version = L.llama_version


def _read_meta(lib, model, key: str) -> Optional[str]:
    buf = ctypes.create_string_buffer(4096)
    n = lib.llama_model_meta_val_str(model, key.encode(), buf, len(buf))
    return buf.value.decode("utf-8", "replace") if n >= 0 else None


def main() -> int:
    try:
        job = json.loads(sys.stdin.readline() or "{}")
    except ValueError:
        fail("invalid_job", "job is not JSON")
        return 2
    if job.get("schema_version") != SCHEMA_VERSION:
        fail("invalid_job", "unsupported schema_version")
        return 2
    pkg = job.get("package_dir")
    if not isinstance(pkg, str) or not os.path.isdir(pkg):
        fail("invalid_job", "package_dir is not a directory")
        return 2
    files = [f for f in os.listdir(pkg) if f.endswith(".gguf")]
    if len(files) != 1:
        fail("invalid_package", "expected exactly one .gguf in the package")
        return 2
    gguf = os.path.join(pkg, files[0])
    opts = job.get("options") or {}
    threads = max(1, min(int(opts.get("threads", 4)), 16))
    n_ctx = max(256, min(int(opts.get("context", 4096)), 32768))
    max_tokens = max(1, min(int(opts.get("max_tokens", 128)), 2048))

    t0 = time.monotonic()
    emit("loading", file=files[0])
    try:
        import ctypes as C
        lib = LibLlama()
        lib.backend_init()
        mparams = C.c_void_p(lib.model_default_params())
        model = lib.model_load(gguf.encode(), mparams)
        if not model:
            fail("load_failed", "llama_model_load_from_file returned null")
            return 3
        vocab = lib.model_get_vocab(model)
        arch = _read_meta(lib, model, "general.architecture") or "unknown"
        n_params = int(lib.model_n_params(model))
        n_vocab = int(lib.vocab_n_tokens(vocab))
        load_ms = int((time.monotonic() - t0) * 1000)
        emit("loaded", engine="llama.cpp", model_path=gguf,
             architecture=arch, n_params=n_params, n_vocab=n_vocab,
             load_ms=load_ms, threads=threads, context=n_ctx,
             lib_path=lib.path)

        if job["op"] == "load_test":
            lib.model_free(model)
            emit("done", op="load_test", result="pass", load_ms=load_ms,
                 architecture=arch, n_params=n_params)
            return 0

        # The context parameter struct is 176 bytes; the caller owns it.  Keep
        # a real buffer so libllama reads n_ctx/threads instead of garbage, then
        # set the two fields we actually depend on.
        cbuf = ctypes.create_string_buffer(256)
        cparams = lib.context_default_params()
        ctypes.memmove(cbuf, ctypes.byref(cparams), ctypes.sizeof(cparams))
        ctypes.c_uint32.from_buffer(cbuf, 0).value = n_ctx      # n_ctx
        ctypes.c_uint32.from_buffer(cbuf, 4).value = 256        # n_batch
        ctypes.c_int32.from_buffer(cbuf, 32).value = threads    # n_threads
        ctypes.c_int32.from_buffer(cbuf, 36).value = threads    # n_threads_batch
        ctx = lib.init_from_model(model, ctypes.byref(cbuf))
        if not ctx:
            lib.model_free(model)
            fail("context_failed", "llama_init_from_model returned null")
            return 3
        prompt = str(job.get("prompt") or "Hello, who are you?")
        toks = (C.c_int32 * (n_ctx + 8))()
        n = lib.tokenize(vocab, prompt.encode(), len(prompt.encode()),
                             toks, n_ctx, True, True)
        if n <= 0:
            lib.free_ctx(ctx)
            lib.model_free(model)
            fail("tokenize_failed", "prompt could not be tokenized")
            return 4
        sp = lib.sampler_chain_default()
        chain = lib.sampler_chain_init(sp)
        lib.sampler_chain_add(chain, C.c_void_p(lib.sampler_init_greedy()))

        # Cancellation: the control plane sends SIGTERM, which sets a flag the
        # library polls during decode (CPU path).  Never accepts new work.
        cancelled = {"v": False}

        def _on_term(signum, frame):
            cancelled["v"] = True

        try:
            import signal
            signal.signal(signal.SIGTERM, _on_term)
            signal.signal(signal.SIGINT, _on_term)
        except Exception:
            pass

        def _abort(_data):
            return bool(cancelled["v"])

        abort_cb = ABORT_CB(_abort)
        lib.set_abort_callback(ctx, abort_cb, None)

        # Decode the prompt in bounded batches.
        pos = 0
        for off in range(0, n, 256):
            if cancelled["v"]:
                emit("cancelled", reason="signal")
                break
            count = min(256, n - off)
            batch = lib.batch_init(count, 0, 1)
            try:
                batch.n_tokens = count
                for i in range(count):
                    batch.token[i] = toks[off + i]
                    batch.pos[i] = pos + i
                    batch.n_seq_id[i] = 1
                    batch.seq_id[i][0] = 0
                    batch.logits[i] = 1 if (off + i == n - 1) else 0
                rc = lib.decode(ctx, batch) if not cancelled["v"] else 0
            finally:
                lib.batch_free(batch)
            if cancelled["v"]:
                emit("cancelled", reason="signal")
                break
            if rc != 0:
                emit("oom" if rc == -2 else "error", code="decode_failed",
                     detail="llama_decode rc=%d" % rc)
                break
            pos += count

        generated = []
        if not cancelled["v"]:
            t_first = None
            t_start = time.monotonic()
            for step in range(max_tokens):
                if cancelled["v"]:
                    emit("cancelled", reason="signal")
                    break
                tok = int(lib.sampler_sample(chain, ctx, -1))
                lib.sampler_accept(chain, tok)
                piece_buf = ctypes.create_string_buffer(256)
                plen = lib.token_to_piece(vocab, tok, piece_buf,
                                               len(piece_buf), 0, True)
                piece = piece_buf.raw[:max(0, plen)].decode("utf-8", "replace") if plen > 0 else ""
                if t_first is None:
                    t_first = time.monotonic() - t_start
                generated.append(piece)
                emit("token", text=piece)
                if lib.vocab_is_eog(vocab, tok):
                    break
                b = lib.batch_init(1, 0, 1)
                try:
                    b.n_tokens = 1
                    b.token[0] = tok
                    b.pos[0] = pos
                    b.n_seq_id[0] = 1
                    b.seq_id[0][0] = 0
                    b.logits[0] = 1
                    rc = lib.decode(ctx, b)
                finally:
                    lib.batch_free(b)
                if rc != 0:
                    emit("oom" if rc == -2 else "error", code="decode_failed",
                         detail="llama_decode rc=%d" % rc)
                    break
                pos += 1
            elapsed = max(1e-6, time.monotonic() - t_start)
            output = "".join(generated)
            emit("done", op=job["op"], result="ok",
                 prompt_tokens=int(n), generated_tokens=len(generated),
                 decode_tokens_per_second=round(len(generated) / elapsed, 3),
                 time_to_first_token_ms=int((t_first or 0) * 1000),
                 output=output[:65536],
                 output_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest())
        lib.sampler_free(chain)
        lib.free_ctx(ctx)
        lib.model_free(model)
        emit("unloaded", reason="job_complete")
        return 0
    except Exception as exc:  # noqa: BLE001
        fail("worker_exception", "%s: %s" % (type(exc).__name__, exc))
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
