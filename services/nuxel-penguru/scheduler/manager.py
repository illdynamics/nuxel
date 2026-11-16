#!/usr/bin/env python3
"""One-heavy-worker scheduler + ROUTING/LOADING/ACTIVE orchestration.

This module owns the only place that decides *which* model is resident.  It
refuses to load a second heavy worker, refuses unsigned packages, maps
explicit runtime preferences to compatible packages and never silently falls
back after generation starts.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Iterator, Optional

from scheduler.state import Lifecycle, InvalidTransition
from common.runtime_api import (
    DeviceProfile, GenerationOptions, RuntimeProfile, RuntimeError_)
from common import registry as reg

MODES = ("chatbird", "codebird", "squad")
RUNTIME_PREFS = ("auto", "llama.cpp", "onnxruntime-genai")


class Scheduler:
    def __init__(self, registry: reg.ModelRegistry,
                 runtimes: Dict[str, Any], config: Dict[str, Any]):
        self.registry = registry
        self.runtimes = runtimes
        self.config = config
        self.lifecycle = Lifecycle()
        self.enabled = False
        self.mode = config.get("mode", "squad")
        self.runtime_preference = config.get("runtime_preference", "auto")
        self.per_model = dict(config.get("per_model_engine") or {})
        self.loaded_model: Optional[str] = None
        self.loaded_variant: Optional[str] = None
        self.loaded_engine: Optional[str] = None
        self.loaded_provider = "CPU"
        self.active_request: Optional[str] = None
        self._lock = threading.RLock()
        self._runtime = None

    # ---- status / control ------------------------------------------------
    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "state": self.lifecycle.state,
            "mode": self.mode,
            "runtime_preference": self.runtime_preference,
            "per_model_engine": dict(self.per_model),
            "loaded_model": self.loaded_model,
            "loaded_variant": self.loaded_variant,
            "engine": self.loaded_engine,
            "provider": self.loaded_provider,
            "active_request": self.active_request,
            "one_heavy_worker": True,
        }

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        if enabled:
            self.enabled = True
            if self.lifecycle.state == "DISABLED":
                self.lifecycle.set("IDLE")
            return {"ok": True, **self.status()}
        if self.lifecycle.state not in ("DISABLED",):
            if self.lifecycle.state in ("ACTIVE",):
                try:
                    self.lifecycle.set("DRAINING")
                except InvalidTransition:
                    pass
                self.cancel_active()
            try:
                self.lifecycle.set("UNLOADING")
            except InvalidTransition:
                pass
            self.unload("disabled")
            self.enabled = False
            self.lifecycle.set("DISABLED")
        return {"ok": True, **self.status()}

    def set_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in MODES:
            raise ValueError("mode must be chatbird, codebird or squad")
        self.mode = mode
        return {"ok": True, "mode": mode}

    def set_runtime_preference(self, pref: str, model_id: Optional[str] = None,
                               engine: Optional[str] = None) -> Dict[str, Any]:
        if model_id:
            if engine not in (None, "inherit", "llama.cpp", "onnxruntime-genai"):
                raise ValueError("per-model engine is invalid")
            if engine in (None, "inherit"):
                self.per_model.pop(model_id, None)
            else:
                self.per_model[model_id] = engine
            return {"ok": True, "per_model_engine": dict(self.per_model)}
        if pref not in RUNTIME_PREFS:
            raise ValueError("runtime preference is invalid")
        self.runtime_preference = pref
        return {"ok": True, "runtime_preference": pref}

    # ---- resolution ------------------------------------------------------
    def resolve(self, model_id: str) -> Dict[str, Any]:
        """Choose a verified package + engine, or explain why unavailable."""
        pref = self.per_model.get(model_id, self.runtime_preference)
        candidates = []
        for m in self.registry.manifests():
            if m["model_id"] != model_id:
                continue
            if m["format"] == "GGUF":
                engine = "llama.cpp"
            elif m["format"] == "ONNX_GENAI":
                engine = "onnxruntime-genai"
            else:
                continue
            if pref not in ("auto",) and pref != engine:
                continue
            candidates.append((m, engine))
        if not candidates:
            return {"ok": False, "error": "backend_unavailable",
                    "detail": "no package compatible with preference %r" % pref}
        reasons = []
        for m, engine in candidates:
            ready, why = self.registry.ready_manifest(model_id, m["variant_id"])
            if ready is None:
                reasons.append("%s/%s: %s" % (m["variant_id"], engine, why))
                continue
            rt = self.runtimes.get(engine)
            if rt is None or not rt.probe(self._device(), self._profile(ready))["available"]:
                reasons.append("%s/%s: runtime unavailable" % (m["variant_id"], engine))
                continue
            return {"ok": True, "manifest": ready, "engine": engine,
                    "variant_id": m["variant_id"]}
        return {"ok": False, "error": "backend_unavailable",
                "detail": "; ".join(reasons) or "no verified package"}

    def _device(self) -> DeviceProfile:
        try:
            with open("/proc/meminfo") as fh:
                lines = dict(line.split(":", 1) for line in fh if ":" in line)
            total = int(lines.get("MemTotal", "0").split()[0]) * 1024
            avail = int(lines.get("MemAvailable", "0").split()[0]) * 1024
        except Exception:
            total = avail = 0
        return DeviceProfile(total_ram_bytes=total, available_ram_bytes=avail,
                             cpu_count=os.cpu_count() or 1)

    def _profile(self, manifest: Dict[str, Any]) -> RuntimeProfile:
        dev = self._device()
        threads = int(self.config.get("threads", 4))
        ctx = int(manifest.get("runtime", {}).get("context_limit", 4096))
        # Conservative budget: half of MemAvailable, never an arbitrary model
        # file size.  The worker's libllama buffer report is the real measure.
        budget = max(0, int(dev.available_ram_bytes * 0.5))
        return RuntimeProfile(
            engine="llama.cpp" if manifest["format"] == "GGUF" else "onnxruntime-genai",
            package_format=manifest["format"], provider="CPU",
            threads=threads, context_limit=ctx, memory_budget_bytes=budget)

    # ---- lifecycle -------------------------------------------------------
    def ensure_loaded(self, model_id: str) -> Dict[str, Any]:
        with self._lock:
            res = self.resolve(model_id)
            if not res["ok"]:
                return res
            m = res["manifest"]
            if (self.loaded_model == model_id and self.loaded_variant == m["variant_id"]
                    and self._runtime is not None):
                return {"ok": True, "manifest": m, "engine": res["engine"],
                        "warm": True, "provider": self.loaded_provider}
            if self.loaded_model and self.loaded_model != model_id:
                self._drain_unload()
            self.lifecycle.set("LOADING")
            rt = self.runtimes[res["engine"]]
            profile = self._profile(m)
            try:
                info = rt.load(m, self.registry.package_dir(m), profile)
            except RuntimeError_ as exc:
                self.lifecycle.set("IDLE")
                return {"ok": False, "error": exc.code, "detail": exc.detail}
            self._runtime = rt
            self.loaded_model = model_id
            self.loaded_variant = m["variant_id"]
            self.loaded_engine = res["engine"]
            self.lifecycle.set("ACTIVE")
            return {"ok": True, "manifest": m, "engine": res["engine"],
                    "provider": self.loaded_provider, "warm": False,
                    "info": info.get("info")}

    def _drain_unload(self) -> None:
        try:
            self.lifecycle.set("DRAINING")
        except InvalidTransition:
            pass
        try:
            self.lifecycle.set("UNLOADING")
        except InvalidTransition:
            pass
        self.unload("switch")

    def unload(self, reason: str) -> Dict[str, Any]:
        with self._lock:
            out = {"ok": True, "reason": reason}
            if self._runtime is not None:
                try:
                    out.update(self._runtime.unload(reason))
                finally:
                    self._runtime = None
            self.loaded_model = None
            self.loaded_variant = None
            self.loaded_engine = None
            if self.lifecycle.state not in ("DISABLED",):
                try:
                    self.lifecycle.set("IDLE")
                except InvalidTransition:
                    pass
            return out

    def cancel_active(self) -> Dict[str, Any]:
        if self._runtime is not None and self.active_request:
            return self._runtime.cancel(self.active_request)
        return {"ok": False, "detail": "no active request"}

    def generate(self, model_id: str, prompt: str, options: GenerationOptions
                 ) -> Iterator[Dict[str, Any]]:
        loaded = self.ensure_loaded(model_id)
        if not loaded.get("ok"):
            yield {"event": "error", **loaded}
            return
        self.active_request = options.request_id
        rt = self._runtime
        try:
            for ev in rt.generate(prompt, options,
                                  self._profile(loaded["manifest"]).memory_budget_bytes):
                yield {"event": ev.kind, **ev.data}
        finally:
            self.active_request = None
