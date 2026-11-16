#!/usr/bin/env python3
"""llama.cpp runtime adapter: drives the unprivileged GGUF worker.

No TCP listener.  The worker is a bounded child process with:
  * only the package directory mounted/visible (the parent enforces paths),
  * no network namespace access (systemd-run --property=PrivateNetwork=yes),
  * memory/CPU/task limits,
  * no broker credentials passed through the environment.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Iterator, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = os.path.abspath(os.path.join(HERE, "..", ".."))
if SVC not in sys.path:
    sys.path.insert(0, SVC)

from common.runtime_api import (  # noqa: E402
    ENGINE_LLAMA, DeviceProfile, GenerationOptions, InferenceEvent,
    InferenceRuntime, RuntimeError_, RuntimeProfile)

WORKER = os.environ.get("NUXEL_LLAMA_WORKER",
                         os.path.join(HERE, "penguru-llama-worker"))
ALLOWED_ENV = ("PATH", "LANG", "LC_ALL", "TZ")


class LlamaCppRuntime(InferenceRuntime):
    engine = ENGINE_LLAMA
    package_format = "GGUF"

    def __init__(self, lib_path: Optional[str] = None,
                 runner: Optional[str] = None):
        self.lib_path = lib_path or os.environ.get(
            "NUXEL_LLAMA_LIB", "/opt/nuxel-llama/libllama.so")
        self.runner = runner if runner is not None else self._systemd_run()
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._loaded: Optional[Dict[str, Any]] = None
        self._generating = False
        self._cancelled = False
        self._last: Optional[Dict[str, Any]] = None

    @staticmethod
    def _systemd_run() -> bool:
        if os.environ.get("NUXEL_PENGURU_NO_SYSTEMD_RUN") == "1":
            return False
        return (os.path.exists("/run/systemd/system")
                and shutil.which("systemd-run") is not None)

    # ---- contract -------------------------------------------------------
    def probe(self, device: DeviceProfile, profile: RuntimeProfile) -> Dict[str, Any]:
        ok_lib = os.path.exists(self.lib_path)
        ok_worker = os.path.exists(WORKER)
        return {
            "engine": self.engine,
            "package_format": self.package_format,
            "available": bool(ok_lib and ok_worker),
            "lib_path": self.lib_path,
            "providers": ["CPU"] if ok_lib else [],
            "provider": "CPU",
            "sandbox": "systemd-run-private-network" if self.runner else "none",
            "error": None if ok_lib and ok_worker else "runtime or worker missing",
        }

    def _base_cmd(self, limit_bytes: int) -> List[str]:
        cmd = [WORKER]
        if not self.runner:
            return cmd
        props = [
            "--unit=penguru-worker-%d" % int(time.time() * 1000),
            "--property=PrivateNetwork=yes",
            "--property=NoNewPrivileges=yes",
            "--property=ProtectSystem=strict",
            "--property=ProtectHome=read-only",
            "--property=ReadWritePaths=-/var/lib/nuxel-penguru",
            "--property=RestrictAddressFamilies=AF_UNIX",
            "--property=Nice=5",
        ]
        if limit_bytes > 0:
            props.append("--property=MemoryMax=%d" % int(limit_bytes))
        return ["systemd-run", "--quiet", "--wait", "--pipe"] + props + ["--"] + cmd

    def _spawn(self, job: Dict[str, Any], limit_bytes: int):
        env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV}
        env["NUXEL_LLAMA_LIB"] = self.lib_path
        env["LD_LIBRARY_PATH"] = os.path.dirname(self.lib_path)
        proc = subprocess.Popen(self._base_cmd(limit_bytes), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, text=True, bufsize=1)
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(job, separators=(",", ":")) + "\n")
        proc.stdin.flush()
        return proc

    def _events(self, proc: subprocess.Popen) -> Iterator[Dict[str, Any]]:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            if isinstance(doc, dict) and isinstance(doc.get("event"), str):
                yield doc
        proc.wait()

    def _run_job(self, job: Dict[str, Any], limit_bytes: int) -> Iterator[Dict[str, Any]]:
        with self._lock:
            self._proc = self._spawn(job, limit_bytes)
            self._generating = True
            self._cancelled = False
        try:
            for doc in self._events(self._proc):
                if self._cancelled and doc.get("event") == "token":
                    continue
                yield doc
        finally:
            with self._lock:
                self._generating = False
                if self._proc and self._proc.poll() is None:
                    self._proc.terminate()
                self._proc = None

    def load(self, manifest: Dict[str, Any], package_dir: str,
             profile: RuntimeProfile) -> Dict[str, Any]:
        start = time.monotonic()
        job = {"schema_version": 1, "op": "load_test",
               "model": manifest.get("model_id", "unknown"),
               "package_dir": package_dir,
               "options": {"threads": profile.threads,
                           "context": profile.context_limit}}
        result = None
        for doc in self._run_job(job, profile.memory_budget_bytes):
            if doc["event"] == "loaded":
                result = doc
            elif doc["event"] == "done":
                self._loaded = {"manifest": manifest, "package_dir": package_dir,
                                "info": result, "load_ms": doc.get("load_ms"),
                                "at": time.time()}
                self._last = doc
                return {"ok": True, "info": result, "done": doc,
                        "load_ms": int((time.monotonic() - start) * 1000)}
            elif doc["event"] in ("error", "oom"):
                raise RuntimeError_(doc.get("code") or "load_failed",
                                    doc.get("detail") or "")
        raise RuntimeError_("load_failed", "worker exited without a load result")

    def generate(self, prompt: str, options: GenerationOptions,
                 memory_budget_bytes: int = 0) -> Iterator[InferenceEvent]:
        if not self._loaded:
            yield InferenceEvent("error", {"code": "not_loaded"})
            return
        m = self._loaded["manifest"]
        job = {"schema_version": 1, "op": "generate",
               "model": m.get("model_id"),
               "package_dir": self._loaded["package_dir"],
               "prompt": prompt,
               "options": {"threads": options_threads(m),
                           "context": m.get("runtime", {}).get("context_limit", 4096),
                           "max_tokens": options.max_tokens}}
        yield InferenceEvent("loading", {"engine": self.engine, "warm": True})
        for doc in self._run_job(job, memory_budget_bytes):
            ev = doc["event"]
            if ev == "token":
                yield InferenceEvent("token", {"text": doc.get("text", "")})
            elif ev == "done":
                self._last = doc
                yield InferenceEvent("done", doc)
            elif ev in ("error", "oom", "cancelled"):
                yield InferenceEvent(ev, doc)
            elif ev == "loaded":
                yield InferenceEvent("loaded", doc)

    def self_test(self, manifest: Dict[str, Any], package_dir: str,
                  profile: RuntimeProfile, prompt: str = "Reply with the word READY.",
                  max_tokens: int = 16) -> Dict[str, Any]:
        job = {"schema_version": 1, "op": "self_test",
               "model": manifest.get("model_id"),
               "package_dir": package_dir, "prompt": prompt,
               "options": {"threads": profile.threads,
                           "context": profile.context_limit,
                           "max_tokens": max_tokens}}
        loaded, done, output = None, None, []
        for doc in self._run_job(job, profile.memory_budget_bytes):
            if doc["event"] == "loaded":
                loaded = doc
            elif doc["event"] == "token":
                output.append(doc.get("text", ""))
            elif doc["event"] == "done":
                done = doc
            elif doc["event"] in ("error", "oom"):
                return {"result": "fail", "code": doc.get("code"),
                        "detail": doc.get("detail"), "loaded": loaded}
        if not done:
            return {"result": "fail", "code": "no_done_event", "loaded": loaded}
        return {"result": "pass", "loaded": loaded, "done": done,
                "output": "".join(output)[:2000]}

    def cancel(self, request_id: str) -> Dict[str, Any]:
        with self._lock:
            self._cancelled = True
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.send_signal(signal.SIGTERM)
                except OSError:
                    pass
                return {"ok": True, "request_id": request_id, "signal": "SIGTERM"}
        return {"ok": False, "request_id": request_id, "detail": "no active job"}

    def health(self) -> Dict[str, Any]:
        return {"ok": self._loaded is not None and not self._generating,
                "loaded": self._loaded is not None,
                "generating": self._generating,
                "pid": self._proc.pid if self._proc else None}

    def unload(self, reason: str) -> Dict[str, Any]:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.send_signal(signal.SIGTERM)
            self._loaded = None
        return {"ok": True, "reason": reason}

    def info(self) -> Dict[str, Any]:
        loaded = self._loaded or {}
        info = loaded.get("info") or {}
        return {"engine": self.engine, "package_format": self.package_format,
                "provider": "CPU", "lib_path": self.lib_path,
                "loaded": bool(self._loaded),
                "architecture": info.get("architecture"),
                "n_params": info.get("n_params"),
                "load_ms": loaded.get("load_ms")}


def options_threads(manifest: Dict[str, Any]) -> int:
    return int(os.environ.get("NUXEL_PENGURU_THREADS", "4"))
