#!/usr/bin/env python3
"""PenGuru control plane (unprivileged, local IPC only).

Owns: mode, queue, routing, runtime selection, scheduler and the local JSON API
on a Unix socket (peer credentials checked).  It never holds root, broker
secrets or a network listener.
"""
from __future__ import annotations

import json
import os
import re
import socket
import socketserver
import sys
import threading
import time
import uuid
from typing import Any, Dict, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from common import config as cfgmod, paths, registry as reg  # noqa: E402
from common.runtime_api import GenerationOptions  # noqa: E402
from scheduler.queue import RequestQueue  # noqa: E402
from scheduler.manager import Scheduler, MODES  # noqa: E402
from sonarbird.router import Classifier, route  # noqa: E402
from runtime.llama_cpp.adapter import LlamaCppRuntime  # noqa: E402
from supervisor import read_actions  # noqa: E402
from model_store import downloader as store  # noqa: E402

SCHEMA_VERSION = 1
MAX_TEXT = 16000
SAFE_SESSION = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


class Controller:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        # Test-scope signatures are accepted only when the operator explicitly
        # installs a test trust root for this on-device build.
        self.registry = reg.ModelRegistry(paths.MANIFESTS_DIR, paths.MODELS_DIR,
                                          trusted_key=paths.MANIFEST_PUBKEY,
                                          allow_test_keys=paths.ALLOW_TEST_KEYS)
        self.queue = RequestQueue(paths.QUEUE_DB, bool(cfg.get("keep_prompt_text")))
        runtimes = {}
        if cfg.get("enable_llama_cpp"):
            runtimes["llama.cpp"] = LlamaCppRuntime(paths.LLAMA_LIB,
                                                   runner=None)
        self.scheduler = Scheduler(self.registry, runtimes, cfg)
        self.classifier = None
        self._generation_lock = threading.Lock()
        self._lock = threading.RLock()
        if cfg.get("enabled"):
            self.scheduler.set_enabled(True)

    def save_preferences(self):
        doc = {"mode": self.scheduler.mode, "runtime_preference": self.scheduler.runtime_preference,
               "per_model_engine": self.scheduler.per_model}
        path = os.path.join(paths.STATE_DIR, "preferences.json")
        with open(path + ".tmp", "w") as fh:
            json.dump(doc, fh)
        os.replace(path + ".tmp", path)

    # ---- status ---------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        cards = self.registry.cards()
        return {
            "schema_version": SCHEMA_VERSION,
            "enabled": self.scheduler.enabled,
            "state": self.scheduler.lifecycle.state,
            "mode": self.scheduler.mode,
            "runtime_preference": self.scheduler.runtime_preference,
            "per_model_engine": dict(self.scheduler.per_model),
            "loaded_model": self.scheduler.loaded_model,
            "loaded_variant": self.scheduler.loaded_variant,
            "engine": self.scheduler.loaded_engine,
            "provider": self.scheduler.loaded_provider,
            "queue_depth": self.queue.pending_count(),
            "models": cards,
            "sonarbird": self.classifier.status() if self.classifier else {"available": False, "mode": "deterministic rules"},
            "providers": {"CPU": {"status": "baseline"},
                          "GPU/NPU": {"status": "not validated on this device"}},
            "network": {"workers": "denied", "local_only": True},
            "voice": {"wake_word": False, "foreground_speech": os.path.isfile("/opt/nuxel-speech/whisper-cli"),
                      "listening": False},
        }

    # ---- request path ---------------------------------------------------
    def submit(self, ident: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
        if not self.scheduler.enabled:
            return {"ok": False, "error": "disabled",
                    "detail": "PenGuru is OFF; enable it first"}
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            return {"ok": False, "error": "invalid_text"}
        if len(text) > MAX_TEXT:
            return {"ok": False, "error": "text_too_long"}
        mode = body.get("mode") or self.scheduler.mode
        if mode not in MODES:
            return {"ok": False, "error": "invalid_mode"}
        pref = body.get("runtime_preference") or self.scheduler.runtime_preference
        if pref not in ("auto", "llama.cpp", "onnxruntime-genai"):
            return {"ok": False, "error": "invalid_runtime"}
        if body.get("route_override") not in (None, "", "CHAT", "CODE", "ASK"):
            return {"ok": False, "error": "invalid_override"}
        if not self._generation_lock.acquire(blocking=False):
            return {"ok": False, "error": "busy", "detail": "Cancel or finish the active request first"}
        rec = self.queue.submit(ident["app_id"], ident["session_id"], mode,
                                pref, text, body.get("conversation_id"))
        rid = rec["request_id"]
        def run():
            try:
                self._handle(rid, ident, text, mode, pref, body.get("route_override"))
            except Exception as exc:
                self.queue.update(rid, status="error", error="%s: %s" % (type(exc).__name__, exc))
                if self.scheduler.lifecycle.can("IDLE"):
                    self.scheduler.lifecycle.set("IDLE")
            finally:
                self._generation_lock.release()
        threading.Thread(target=run, daemon=True).start()
        return {"ok": True, "request_id": rid, "status": "queued"}

    def _handle(self, rid: str, ident: Dict[str, str], text: str, mode: str,
                pref: str, override: Optional[str]) -> Dict[str, Any]:
        s = self.scheduler
        s.lifecycle.set("ROUTING")
        if mode in ("chatbird", "codebird"):
            decision = {"route": "CHAT" if mode == "chatbird" else "CODE",
                        "confidence": 1.0, "reason_code": "R_SINGLE_MODE",
                        "worker": mode, "decision_source": "mode"}
        else:
            if self.classifier is None:
                manifest, _ = self.registry.ready_manifest("sonarbird", "onnx-int8-arm64")
                if manifest is not None:
                    self.classifier = Classifier(self.registry.package_dir(manifest))
            decision = route(text, self.classifier).as_dict()
        if override in ("CHAT", "CODE", "ASK"):
            decision.update({"route": override, "reason_code": "R_OWNER_OVERRIDE",
                             "worker": {"CHAT": "chatbird", "CODE": "codebird"}.get(override),
                             "decision_source": "owner_override"})
        self.queue.update(rid, route=decision["route"],
                          reason_code=decision["reason_code"],
                          confidence=decision["confidence"],
                          worker=decision.get("worker"))
        if decision["route"] == "ASK":
            s.lifecycle.set("WAITING_USER")
            self.queue.update(rid, status="awaiting_user")
            return {"ok": True, "status": "awaiting_user", "route": decision}
        if decision["route"] == "SYSTEM":
            out = read_actions.resolve(text, ident)
            self.queue.update(rid, status="done", output=json.dumps(out))
            s.lifecycle.set("IDLE")
            return {"ok": True, "status": "done", "route": decision,
                    "output": out}
        worker_model = decision["worker"]
        if worker_model is None:
            s.lifecycle.set("IDLE")
            return {"ok": False, "error": "no_worker_for_route"}
        if pref in ("auto", "llama.cpp", "onnxruntime-genai"):
            s.set_runtime_preference(pref)
        loaded = s.ensure_loaded(worker_model)
        if not loaded.get("ok"):
            s.lifecycle.set("IDLE")
            self.queue.update(rid, status="error",
                              error="%s: %s" % (loaded.get("error"), loaded.get("detail")))
            return {"ok": False, "status": "error", "route": decision,
                    "error": loaded.get("error"), "detail": loaded.get("detail")}
        self.queue.update(rid, engine=loaded["engine"],
                          variant_id=loaded["manifest"]["variant_id"],
                          revision=loaded["manifest"]["source_revision"])
        opts = GenerationOptions(
            max_tokens=256, request_id=rid,
            system_prompt=self._system_prompt(worker_model))
        events = []
        output = []
        final = None
        for ev in s.generate(worker_model, text, opts):
            events.append(ev)
            if ev["event"] == "token":
                output.append(ev.get("text", ""))
                self.queue.update(rid, status="generating", output="".join(output))
            elif ev["event"] in ("done", "error", "oom", "cancelled"):
                final = ev
        out_text = "".join(output)[:65536]
        if final and final["event"] == "done":
            self.queue.update(rid, status="done", output=out_text)
            result = {"ok": True, "status": "done", "route": decision,
                      "output": out_text, "engine": loaded["engine"],
                      "variant_id": loaded["manifest"]["variant_id"],
                      "provider": loaded["provider"],
                      "metrics": {k: final.get(k) for k in (
                          "prompt_tokens", "generated_tokens",
                          "decode_tokens_per_second", "time_to_first_token_ms")}}
        elif final and final["event"] == "cancelled":
            self.queue.update(rid, status="cancelled", output=out_text)
            result = {"ok": False, "status": "cancelled", "route": decision,
                      "output": out_text}
        else:
            code = (final or {}).get("code") or "generation_failed"
            self.queue.update(rid, status="error", error=str(code))
            result = {"ok": False, "status": "error", "route": decision,
                      "error": code}
        if s.lifecycle.state in ("ACTIVE", "WAITING_USER"):
            s.lifecycle.set("IDLE")
        return result

    PENGURU_IDENTITY = (
        "Your name is PenGuru. You are a virtual penguin and the most advanced "
        "AI subsystem of NUXAI. NUXAI was originally designed for Nuxel, and "
        "now it also runs on Android. Never claim to be another assistant or "
        "product; introduce yourself as PenGuru.")

    def _system_prompt(self, model: str) -> str:
        if model == "codebird":
            return (self.PENGURU_IDENTITY + " You are PenGuru's CodeBird "
                    "worker, a local coding assistant. Output code or patch "
                    "suggestions only. You cannot execute commands or change "
                    "the system.")
        return (self.PENGURU_IDENTITY + " You are PenGuru's ChatBird worker, "
                "a local assistant. You cannot execute commands, change the "
                "system or approve actions.")


# ── local IPC ────────────────────────────────────────────────────────────
class Handler(socketserver.StreamRequestHandler):
    controller: Controller = None  # type: ignore

    def _ident(self) -> Optional[Dict[str, str]]:
        try:
            creds = self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                            12)
            import struct
            pid, uid, gid = struct.unpack("3i", creds)
            if uid != 0:  # Only the trusted root bridge may assert launcher identity.
                return None
        except OSError:
            return None
        doc = json.loads(self.rfile.readline(65537) or b"{}")
        app_id = doc.get("app_id")
        session_id = doc.get("session_id")
        if not isinstance(app_id, str) or not app_id or not isinstance(session_id, str):
            return None
        if app_id not in ("org.nuxel.PenGuru", "nuxel-settings", "org.nuxel.Settings"):
            return None
        if not SAFE_SESSION.fullmatch(session_id):
            return None
        return {"app_id": app_id, "session_id": session_id, "uid": uid, "pid": pid}

    def handle(self):
        self.request.settimeout(15)
        try:
            ident = self._ident()
        except (ValueError, OSError, AttributeError):
            ident = None
        if ident is None:
            self.wfile.write(json.dumps({"ok": False, "error": "identity_required"}).encode() + b"\n")
            return
        while True:
            raw = self.rfile.readline(524289)
            if not raw:
                break
            if len(raw) > 524288:
                self.wfile.write(b'{"ok":false,"error":"request_too_large"}\n')
                return
            try:
                req = json.loads(raw)
            except ValueError:
                self.wfile.write(b'{"ok":false,"error":"invalid_json"}\n')
                continue
            try:
                out = self._dispatch(ident, req)
            except (OSError, ValueError, reg.ManifestError):
                out = {"ok": False, "error": "operation_failed"}
            self.wfile.write(json.dumps(out, ensure_ascii=False).encode() + b"\n")
            self.wfile.flush()

    def _dispatch(self, ident: Dict[str, str], req: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(req, dict):
            return {"ok": False, "error": "invalid_request"}
        op = req.get("op")
        c = self.controller
        download_ops = ("start_download", "download_status", "cancel_download")
        if os.environ.get("NUXEL_PENGURU_DOWNLOADER") == "1" and op not in download_ops:
            return {"ok": False, "error": "download_only"}
        if os.environ.get("NUXEL_PENGURU_DOWNLOADER") != "1" and op in download_ops:
            return {"ok": False, "error": "use_download_service"}
        if op == "status":
            return {"ok": True, "status": c.status()}
        if op == "set_enabled":
            out = c.scheduler.set_enabled(bool(req.get("enabled")))
            out["ok"] = True
            return out
        if op == "set_mode":
            try:
                out = c.scheduler.set_mode(str(req.get("mode")))
                c.save_preferences()
                out["ok"] = True
                return out
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
        if op == "set_runtime":
            try:
                out = c.scheduler.set_runtime_preference(
                    str(req.get("preference") or c.scheduler.runtime_preference),
                    req.get("model_id"), req.get("engine"))
                c.save_preferences()
                out["ok"] = True
                return out
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
        if op == "transcribe":
            if not c.scheduler.enabled:
                return {"ok": False, "error": "disabled"}
            if c._generation_lock.locked():
                return {"ok": False, "error": "busy", "detail": "Finish generation before speech recognition"}
            from voice.speech import transcribe
            return {"ok": True, **transcribe(c.registry, req.get("audio"))}
        if op == "submit":
            return c.submit(ident, req)
        if op == "cancel":
            rid = str(req.get("request_id") or "")
            if not c.queue.owned(rid, ident["app_id"], ident["session_id"]):
                return {"ok": False, "error": "not_owner"}
            c.queue.update(rid, cancelled=1)
            return c.scheduler.cancel_active()
        if op == "get":
            rid = str(req.get("request_id") or "")
            if not c.queue.owned(rid, ident["app_id"], ident["session_id"]):
                return {"ok": False, "error": "not_owner"}
            return {"ok": True, "request": c.queue.get(rid)}
        if op == "delete_conversation":
            n = c.queue.delete_conversation(ident["app_id"], ident["session_id"],
                                            str(req.get("conversation_id") or ""))
            return {"ok": True, "deleted": n}
        if op == "clear_all":
            return {"ok": True, "deleted": c.queue.clear_all(ident["app_id"],
                                                             ident["session_id"])}
        if op == "list_models":
            return {"ok": True, "models": c.registry.cards()}
        if op == "start_download":
            return store.start_download(
                c.registry, str(req.get("model_id") or ""),
                str(req.get("variant_id") or ""),
                bool(req.get("license_accepted")),
                str(req.get("license_revision") or ""))
        if op == "download_status":
            return store.download_status(str(req.get("job_id") or ""))
        if op == "cancel_download":
            return store.cancel_download(str(req.get("job_id") or ""))
        if op == "delete_model":
            if c._generation_lock.locked():
                return {"ok": False, "error": "busy"}
            c.scheduler.unload("delete")
            return store.delete_model(c.registry, str(req.get("model_id") or ""),
                                      str(req.get("variant_id") or ""))
        if op == "diagnostics":
            return {"ok": True, "status": c.status(),
                    "device": c.scheduler._device().__dict__,
                    "runtimes": {k: v.probe(c.scheduler._device(),
                                            c.scheduler._profile({"format": "GGUF", "runtime": {"context_limit": 4096}}))
                                 for k, v in c.scheduler.runtimes.items()}}
        if op == "disable_all":
            out = c.scheduler.set_enabled(False)
            out["ok"] = True
            return out
        return {"ok": False, "error": "unknown_op"}


class ThreadedUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def serve(sock_path: str) -> None:
    try:
        cfg = cfgmod.load(paths.CONFIG_PATH)
    except Exception as exc:  # noqa: BLE001
        print("penguru: invalid config:", exc, file=sys.stderr)
        raise SystemExit(2)
    try:
        with open(os.path.join(paths.STATE_DIR, "preferences.json")) as fh:
            saved = json.load(fh)
        for key in ("mode", "runtime_preference", "per_model_engine"):
            if key in saved:
                cfg[key] = saved[key]
    except (OSError, ValueError):
        pass
    cfg["enabled"] = os.environ.get("NUXEL_PENGURU_DOWNLOADER") != "1"
    Handler.controller = Controller(cfg)
    os.makedirs(os.path.dirname(sock_path), exist_ok=True)
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass
    old = os.umask(0o077)
    server = ThreadedUnixServer(sock_path, Handler)
    os.umask(old)
    os.chmod(sock_path, 0o660)
    server.serve_forever()


if __name__ == "__main__":
    serve(os.environ.get("NUXEL_PENGURU_SOCKET", "/run/nuxel-penguru/control.sock"))
