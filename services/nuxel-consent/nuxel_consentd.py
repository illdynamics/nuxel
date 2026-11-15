#!/usr/bin/env python3
"""nuxel-consentd — on-screen, in-app permission consent on the session bus.

This is the interactive consent surface that ``org.nuxel.Portal`` (the
hardware broker, D-Bus name ``org.nuxel.Portal``) already calls through
``org.nuxel.PhoshAgent.RequestPermission``.  Until this service existed the
name had no owner on the handset session bus, so every consent request was
auto-denied after the portal's 30 s timer and the user never saw a prompt.

What the user gets
------------------
When an app asks for a capability the user has not decided yet, a card is
posted in the Nuxel notification shade (visible from Quick Settings) with
four actions, exactly as requested:

    Allow once       grant for this one request, then forget
    Allow always     grant now *and* persist it, so Settings / Permission
                     Manager show the same "Allowed" state
    Deny             refuse; an explicit deny record is written
    Cancel           close the prompt without changing policy

A prompt is never created for a capability that is already granted, never
for a capability the registry marks unsupported on this device, and never
for an unrecognised app id or capability (fail closed: deny).

Trust model
-----------
``RequestPermission`` must only be callable by the broker, otherwise any
session process could pop consent cards and learn what the user is being
asked to approve.  The agent accepts a caller only when:

  * the caller's D-Bus name is ``org.nuxel.Portal`` and the caller uid is
    ``nuxel`` or ``root``; or
  * the caller is the active logind session on this seat (the user taps the
    card on the lock screen / home UI).

The policy store is permD's store (``/var/lib/nuxel/permissions``), the same
one Settings and the Permission Manager app read/write, so an "Allow always"
decision is immediately visible in both surfaces without a sync step.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

LOG = logging.getLogger("nuxel-consent")
BUS_NAME = "org.nuxel.PhoshAgent"
BUS_PATH = "/org/nuxel/PhoshAgent"
BUS_IFACE = "org.nuxel.PhoshAgent"

NOTIFY_BUS = "org.nuxel.Notifications"
NOTIFY_PATH = "/org/nuxel/Notifications"
NOTIFY_IFACE = "org.nuxel.Notifications"

PORTAL_BUS = "org.nuxel.Portal"
PERMD = "/usr/lib/nuxel/nuxel-permissions/nuxel-permd.py"
STORE_DIR = os.environ.get("NUXEL_PERMISSIONS_DIR") or "/var/lib/nuxel/permissions"
CAPS_JSON = "/etc/nuxel/permissions/capabilities.json"

# Durations are permD's vocabulary; "once" is consumed on the next check.
ALLOW_ONCE = "once"
ALLOW_ALWAYS = "always"
DENY = "deny"
CANCEL = "cancel"

DEFAULT_TTL_SECONDS = 90.0
PROMPT_SOURCE = "nuxel-consent"

# Never pop a consent card for a token that cannot be enforced on this
# device.  The registry's NOT_SUPPORTED_ON_DEVICE verdict wins; keeping a
# small hard deny list here protects against a stale registry on the phone.
HARD_DENY = frozenset((
    "sms_send_raw", "modem:raw", "kernel:module", "landlock", "ptrace",
    "selinux", "lockdown", "root", "sudo",
))

TITLES = {
    "microphone": "Use the microphone",
    "nfc": "Use NFC",
    "camera": "Use the camera",
    "location": "Access your location",
    "contacts": "Access your contacts",
    "calendar": "Access your calendar",
    "call": "Place phone calls",
    "sms": "Send SMS messages",
    "phone_status": "Read phone status",
    "bluetooth": "Use Bluetooth",
    "usb": "Access USB devices",
    "notifications": "Send notifications",
    "background": "Run in the background",
    "storage": "Access your files",
    "network": "Use the network",
}

# These caps are stored under the same id the app requested; everything else
# is normalised through permD's registry resolve (aliases included).
CANONICAL = frozenset(TITLES) | frozenset((
    "audio", "clipboard", "clock_status", "display", "downloads",
    "input_devices", "local_shell", "media_library", "system_inspect",
    "catalog_read", "app_install", "app_remove", "zoom", "fullscreen",
    "casting", "mirroring",
))


# dbus.service.BusName releases the well-known name from __del__, so the
# reference must live for the whole process, not a local in main().
_BUS_NAME_OBJ = None


class ConsentError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


def _permd(args, timeout=15):
    try:
        proc = subprocess.run([sys.executable, PERMD] + list(args),
                              capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    out = (proc.stdout or "").strip()
    doc = None
    if out:
        try:
            doc = json.loads(out)
        except ValueError:
            doc = None
    return {"rc": proc.returncode, "data": doc,
            "stdout": out[-800:], "stderr": (proc.stderr or "").strip()[-800:]}, None


def _registry_aliases():
    """Map registry aliases/portal types -> capability id (best effort)."""
    try:
        with open(CAPS_JSON, "r") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return {}
    aliases = {}
    for row in doc.get("capabilities", []) or []:
        cid = row.get("id")
        if not cid:
            continue
        for name in [cid] + list(row.get("aliases") or []):
            aliases[str(name)] = cid
        if row.get("portal_type"):
            aliases.setdefault(str(row["portal_type"]), cid)
    return aliases


def canonical_cap(token: str) -> str:
    t = (token or "").strip()
    if not t:
        raise ConsentError("invalid_capability", "empty capability")
    if t in HARD_DENY:
        raise ConsentError("unsupported_capability", "refused capability: %s" % t)
    if t in CANONICAL:
        return t
    alias = _registry_aliases().get(t)
    if alias in CANONICAL:
        return alias
    base = t.split(":", 1)[0]
    if base in CANONICAL:
        return base
    raise ConsentError("unsupported_capability", "unknown capability: %s" % t)


def app_display_name(app_id: str) -> str:
    try:
        with open("/etc/nuxel/app-registry/app_registry.json", "r") as fh:
            doc = json.load(fh)
        for app in doc.get("apps", []) or []:
            aid = app.get("app_id") or app.get("id")
            if aid == app_id:
                return str(app.get("name") or app.get("display_name") or app_id)
    except (OSError, ValueError):
        pass
    return app_id


def capability_allowed_on_device(cap: str) -> bool:
    if cap in HARD_DENY:
        return False
    try:
        with open(CAPS_JSON, "r") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        # No registry: keep the prompt (permD will still enforce/downgrade),
        # but never claim an unsupported capability is consentable.
        return cap not in HARD_DENY
    for row in doc.get("capabilities", []) or []:
        if row.get("id") == cap:
            if row.get("verdict") == "NOT_SUPPORTED_ON_DEVICE":
                return False
            if row.get("enforceable") == "no":
                return False
            return True
    return False


def _add_reply_callback(request_id, callback):
    with _SHARED["lock"]:
        _REPLY_CALLBACKS.setdefault(request_id, []).append(callback)


def _take_reply_callbacks(request_id):
    with _SHARED["lock"]:
        return _REPLY_CALLBACKS.pop(request_id, [])


class ConsentRequest:
    def __init__(self, rid, app_id, app_name, capability, portal_type):
        self.id = rid
        self.app_id = app_id
        self.app_name = app_name
        self.capability = capability
        self.portal_type = portal_type
        self.state = "pending"          # pending | granted | denied | cancelled | expired
        self.duration = None
        self.notification_id = None
        self.created = time.time()
        self.deadline = self.created + DEFAULT_TTL_SECONDS
        self.timer = None
        self.done = threading.Event()



# One agent state shared by every bus endpoint: the session bus is where the
# portal asks and the system bus is where the root HTTP bridge / Home reads and
# answers.  Two independent instances made ListPending on the system bus report
# an empty list while a session-bus prompt was visibly waiting.
_SHARED = {"lock": threading.RLock(), "requests": {}}
# request_id -> {bus_label: success_callback}.  Async D-Bus replies belong to
# the connection that received the call, so they must NOT live in shared state.
_REPLY_CALLBACKS = {}


class PhoshAgent(dbus.service.Object):
    def __init__(self, bus, path, ttl=DEFAULT_TTL_SECONDS, buses=None):
        super().__init__(bus, path)
        self.bus = bus
        self.buses = list(buses or [bus])
        self.ttl = float(ttl)
        self._lock = _SHARED["lock"]
        self._requests = _SHARED["requests"]
        self._signal_ok = True
        _SHARED.setdefault("endpoints", []).append(self)
        LOG.info("org.nuxel.PhoshAgent consent surface ready (ttl=%.0fs)", self.ttl)

    # ---- helpers --------------------------------------------------------
    def _notify(self):
        """The notification surface the USER is looking at.

        The Home shade runs as uid 1000 on the per-user session bus; the system
        hub mirror on the system bus is the same store but does not reach the
        UI.  Post on the session bus first, fall back to the system hub.
        """
        # System hub first: the HTTP bridge (root, a different principal than
        # this UID-1000 bus) must be able to LIST/ANSWER prompts, and the hub
        # is reachable from both principals.  The session-bus hub mirrors the
        # same store and is the fallback.
        for bus, label in ((None, "system"), (self.bus, "session")):
            try:
                b = bus if bus is not None else dbus.SystemBus()
                iface = dbus.Interface(b.get_object(NOTIFY_BUS, NOTIFY_PATH),
                                       NOTIFY_IFACE)
                if self._notification_probe(iface):
                    return iface
            except dbus.exceptions.DBusException as exc:
                LOG.debug("notification bus %s unavailable: %s", label, exc)
        LOG.warning("notification hub unavailable; consent prompt has no surface")
        self._signal_ok = False
        return None

    @staticmethod
    def _notification_probe(iface):
        try:
            res = str(iface.GetNotificationCounts())
            return bool(res)
        except dbus.exceptions.DBusException:
            return False

    def _prompt_actions(self):
        return ["allow-once", "Allow once",
                "allow-always", "Allow always",
                "deny", "Deny",
                "cancel", "Cancel"]

    def _post_prompt(self, req):
        notifier = self._notify()
        if notifier is None:
            return None
        body = ("%s wants to %s. Choose how long this lasts; the same "
                "decision is shown in Settings and the Permission Manager."
                % (req.app_name, TITLES.get(req.capability, "use " + req.capability)))
        payload = {
            "app_id": "org.nuxel.Permissions",
            "app_name": "Permission request",
            "summary": "%s wants %s" % (req.app_name, TITLES.get(req.capability, req.capability)),
            "body": body,
            "urgency": "critical",
            "icon": "preferences-system-privacy",
            "actions": self._prompt_actions(),
            "expire_timeout": int(self.ttl * 1000),
            "source": PROMPT_SOURCE,
            "hints": {"x-nuxel-consent-id": req.id,
                      "x-nuxel-app-id": req.app_id,
                      "x-nuxel-capability": req.capability},
        }
        try:
            res = json.loads(str(notifier.SubmitNotification(json.dumps(payload))))
        except (dbus.exceptions.DBusException, ValueError) as exc:
            LOG.warning("prompt post failed: %s", exc)
            return None
        return res.get("id")

    def _withdraw_prompt(self, req, summary, body):
        notifier = self._notify()
        nid = req.notification_id
        if notifier is None or nid is None:
            return
        # Replace the card content first so the user sees the final outcome,
        # then archive it out of the unread tray.
        payload = {
            "app_id": "org.nuxel.Permissions",
            "app_name": "Permission request",
            "summary": summary,
            "body": body,
            "urgency": "normal",
            "actions": [],
            "expire_timeout": 12000,
            "replaces_id": int(nid),
            "source": PROMPT_SOURCE,
            "hints": {"x-nuxel-consent-id": req.id},
        }
        try:
            notifier.SubmitNotification(json.dumps(payload))
            notifier.Archive(int(nid))
        except dbus.exceptions.DBusException as exc:
            LOG.debug("prompt withdraw failed: %s", exc)

    def _finish(self, req, state, duration, result):
        with self._lock:
            if req.state != "pending":
                return req
            req.state = state
            req.duration = duration
            # The D-Bus caller is waiting on this answer; resolve it here so
            # every exit path (allow, deny, cancel, expire) replies exactly once.
            callbacks = list(_take_reply_callbacks(req.id))
            if req.timer is not None:
                try:
                    GLib.source_remove(req.timer)
                except Exception:
                    pass
                req.timer = None
        req.done.set()
        if callbacks:
            body = {"granted": state == "granted", "duration": duration,
                    "request_id": req.id, "state": state}
            for callback in callbacks:
                try:
                    callback(json.dumps(body))
                except Exception as exc:  # noqa: BLE001 - reply already gone
                    LOG.warning("async consent reply failed for %s: %s", req.id, exc)
        self._broadcast_resolved(req.id, state, req.app_id, req.capability,
                                 duration or "")
        return req

    # ---- multi-bus broadcast -------------------------------------------
    def _endpoints(self):
        """Every PhoshAgent instance, one per connected bus."""
        return [obj for obj in _SHARED.get("endpoints", []) if obj is not None]

    def _broadcast_resolved(self, *args):
        for obj in self._endpoints():
            try:
                obj.PermissionResolved(*args)
            except Exception:  # noqa: BLE001 - a dead bus must not break consent
                pass

    def _broadcast_changed(self, payload):
        for obj in self._endpoints():
            try:
                obj.PermissionChanged(payload)
            except Exception:  # noqa: BLE001
                pass

    # ---- authorisation of the requester --------------------------------
    def _caller_ok(self, sender):
        """Only the portal broker (or the session user) may open a prompt.

        The portal runs as ``nuxel`` (uid 1000) and calls over the session bus.
        The HTTP bridge occasionally calls the portal as root.   Anything else
        could otherwise enumerate/replay consent cards it has no right to see.
        """
        if not sender:
            return False
        try:
            system = dbus.SystemBus()
            bus_iface = dbus.Interface(
                system.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus"),
                "org.freedesktop.DBus")
            uid = int(bus_iface.GetConnectionUnixUser(sender))
            if uid not in (0, 1000):
                return False
            try:
                owner = str(bus_iface.GetNameOwner(PORTAL_BUS))
            except dbus.exceptions.DBusException:
                owner = ""
            # The broker itself, or the session user (tap-based surfaces).
            if owner and owner == sender and uid in (0, 1000):
                return True
            return uid == 1000
        except (dbus.exceptions.DBusException, TypeError, ValueError):
            return False

    # ---- D-Bus: consent -------------------------------------------------
    @dbus.service.method(BUS_IFACE, in_signature="ss", out_signature="s",
                         sender_keyword="sender",
                         async_callbacks=("on_done", "on_error"))
    def RequestPermission(self, app_id, portal_type, sender=None,
                          on_done=None, on_error=None):
        """Show an in-app consent card; reply asynchronously when the user acts.

        dbus-python services run these handlers inline on the bus thread, so
        blocking here starves every other call on the connection (including
        the caller's own reply).  The async_callbacks form returns immediately
        and completes the D-Bus reply from the user's action instead.
        """
        def fail(code, **extra):
            body = {"granted": False, "duration": None, "error": code}
            body.update(extra)
            on_done(json.dumps(body))

        try:
            cap = canonical_cap(str(portal_type))
        except ConsentError as exc:
            LOG.warning("RequestPermission refused %r: %s", portal_type, exc.code)
            return fail(exc.code)
        app_id = str(app_id or "").strip()
        if not app_id or len(app_id) > 200:
            return fail("invalid_app_id")
        if not capability_allowed_on_device(cap):
            return fail("unsupported_on_device")

        with self._lock:
            for other in self._requests.values():
                if (other.state == "pending" and other.app_id == app_id
                        and other.capability == cap):
                    req = other
                    break
            else:
                req = ConsentRequest("consent-" + uuid.uuid4().hex[:16], app_id,
                                     app_display_name(app_id), cap, str(portal_type))
                self._requests[req.id] = req
            _add_reply_callback(req.id, on_done)

        if req.notification_id is None:
            req.notification_id = self._post_prompt(req)
            LOG.info("prompt %s: %s / %s", req.id, app_id, cap)
            if req.notification_id is None:
                self._finish(req, "denied", None, None)
                self._complete_reply(req, {"granted": False, "duration": None,
                                           "error": "no_consent_surface"})
                return None
            deadline = req.deadline

            def _expire():
                with self._lock:
                    if req.state != "pending":
                        return GLib.SOURCE_REMOVE
                self._expire(req)
                return GLib.SOURCE_REMOVE

            req.timer = GLib.timeout_add(
                max(1, int((deadline - time.time()) * 1000)), _expire)
        return None

    def _expire(self, req):
        if req.state != "pending":
            return
        self._finish(req, "expired", None, None)
        LOG.info("prompt %s expired without a decision", req.id)
        self._withdraw_prompt(
            req, "Permission request expired",
            "%s did not get %s. Nothing changed." %
            (req.app_name, TITLES.get(req.capability, req.capability)))

    @dbus.service.method(BUS_IFACE, in_signature="ss", out_signature="s")
    def Respond(self, request_id, action):
        """Resolve one prompt.  UI actions: allow-once / allow-always / deny / cancel."""
        rid = str(request_id or "")
        key = str(action or "").strip().lower()
        with self._lock:
            req = self._requests.get(rid)
        if req is None:
            return json.dumps({"success": False, "error": "no_such_request"})
        if key in ("cancel", "close", "dismiss"):
            self._finish(req, "cancelled", None, None)
            self._withdraw_prompt(req, "Permission request cancelled",
                                  "%s will not get %s." % (
                                      req.app_name, TITLES.get(req.capability, req.capability)))
            return json.dumps({"success": True, "state": "cancelled"})

        if key not in ("allow-once", "allow-always", "deny"):
            return json.dumps({"success": False, "error": "unknown_action",
                               "action": key})
        permission = "allow" if key.startswith("allow") else "deny"
        duration = ALLOW_ONCE if key == "allow-once" else ALLOW_ALWAYS
        if req.state != "pending":
            return json.dumps({"success": False, "error": "already_resolved",
                               "state": req.state})
        store, err = _apply_permd_decision(req.app_id, req.capability, permission, duration,
                                           evidence=["owner consent via on-screen prompt",
                                                     "request=" + req.id])
        if err is not None:
            LOG.error("permD write failed for %s/%s: %s", req.app_id, req.capability, err)
            return json.dumps({"success": False, "error": "policy_write_failed",
                               "detail": str(err)[:200]})

        self._finish(req, "granted" if permission == "allow" else "denied",
                     duration if permission == "allow" else None, None)
        title = TITLES.get(req.capability, req.capability)
        if permission == "allow":
            summary = "%s allowed" % title
            body = "%s: %s (%s)." % (
                req.app_name, "allowed for this request" if duration == ALLOW_ONCE
                else "allowed permanently — visible in Settings → Permissions",
                title)
        else:
            summary = "%s denied" % title
            body = "%s will not get %s." % (req.app_name, title)
        self._withdraw_prompt(req, summary, body)
        self._broadcast_changed(json.dumps({
            "app_id": req.app_id, "capability": req.capability,
            "permission": permission, "duration": duration,
            "request_id": req.id, "store": store or "",
        }))
        LOG.info("prompt %s: %s %s for %s (%s)", req.id, permission,
                 req.capability, req.app_id, duration)
        return json.dumps({"success": True, "state": req.state,
                           "duration": duration, "store": store or ""})

    @dbus.service.method(BUS_IFACE, in_signature="", out_signature="s")
    def ListPending(self):
        with self._lock:
            rows = [{"request_id": r.id, "app_id": r.app_id,
                     "app_name": r.app_name, "capability": r.capability,
                     "notification_id": r.notification_id,
                     "deadline": r.deadline}
                    for r in self._requests.values() if r.state == "pending"]
        return json.dumps({"success": True, "pending": rows})

    # ---- signals --------------------------------------------------------
    @dbus.service.signal(BUS_IFACE, signature="sssss")
    def PermissionResolved(self, request_id, state, app_id, capability, duration):
        pass

    @dbus.service.signal(BUS_IFACE, signature="s")
    def PermissionChanged(self, payload_json):
        pass


def _last_lines(text, n):
    """Keep the tail of a traceback: the exception line is what matters."""
    lines = [ln for ln in str(text or "").strip().splitlines() if ln.strip()]
    return " | ".join(lines[-n:])[-500:]


def _apply_permd_decision(app_id, cap, permission, duration, evidence=None):
    """Write the decision into the shared permD store (Settings sees it)."""
    if permission == "allow":
        args = ["grant", app_id, cap, "--duration", duration]
    else:
        args = ["deny", app_id, cap]
    res, err = _permd(args)
    if err is not None:
        return None, err
    if not res or res.get("rc") != 0:
        raw = " ".join(str((res or {}).get(k) or "")
                       for k in ("stderr", "stdout")).strip()
        return None, _last_lines(raw, 4) or "permD rc!=0"
    # grant/deny print human-readable text, not JSON.  Confirm the write
    # against the store instead of trusting an exit code.
    #
    # ``check`` CONSUMES a "once" grant, so it is only used for durable
    # decisions ("Allow all" / "Deny").  For "Allow once" the record itself is
    # read back non-destructively: the one-shot must still be there for the
    # request that triggered the prompt.
    if permission == "allow" and duration == ALLOW_ONCE:
        try:
            doc = json.load(open(os.path.join(STORE_DIR, app_id + ".json")))
        except (OSError, ValueError) as exc:
            return None, "grant read-back failed: %s" % exc
        rec = doc.get(cap) if isinstance(doc, dict) else None
        if not isinstance(rec, dict) or rec.get("duration") != ALLOW_ONCE:
            return None, "permD did not persist the one-shot grant"
        return "permD", None
    try:
        chk = subprocess.run([sys.executable, PERMD, "check", app_id, cap],
                             capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "permD check failed: %s" % exc
    if chk.returncode != 0:
        return None, "permD check failed after %s: %s" % (
            permission, _last_lines(chk.stderr or chk.stdout, 3))
    return "permD", None


def install_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr)


def _serve(bus, bus_name, ttl=DEFAULT_TTL_SECONDS, buses=None):
    """Own the agent name on one bus and answer requests."""
    try:
        bus_name_obj = dbus.service.BusName(BUS_NAME, bus, do_not_queue=True,
                                            allow_replacement=False,
                                            replace_existing=False)
    except dbus.exceptions.NameExistsException:
        LOG.error("another org.nuxel.PhoshAgent owns %s; exiting", BUS_NAME)
        return None
    PhoshAgent(bus, BUS_PATH, ttl=ttl, buses=buses)
    LOG.info("claimed %s on %s", BUS_NAME, bus_name)
    return bus_name_obj


def main(argv=None):
    ap = argparse.ArgumentParser(description="Nuxel in-app permission consent surface")
    ap.add_argument("--ttl", type=float, default=DEFAULT_TTL_SECONDS)
    # Both: the session bus is where nuxel-portal asks for consent, and the
    # system bus is how the root HTTP bridge (and Home via the bridge) can
    # reach the same agent to list/answer prompts.  A UID-1000 broker may not
    # own a system-bus name, so failures are non-fatal per bus.
    ap.add_argument("--bus", choices=("session", "system", "both"), default="both")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    install_logging(args.verbose)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    buses = []
    if args.bus in ("session", "both"):
        buses.append(("session", dbus.SessionBus))
    if args.bus in ("system", "both"):
        buses.append(("system", dbus.SystemBus))
    connected = []
    for label, factory in buses:
        try:
            connected.append((label, factory()))
        except dbus.exceptions.DBusException as exc:
            LOG.warning("%s bus unavailable: %s", label, exc)
    keepalive = []
    for label, conn in connected:
        name = _serve(conn, label, ttl=args.ttl,
                      buses=[c for _, c in connected])
        if name is not None:
            keepalive.append(name)
    if not keepalive:
        LOG.error("could not own %s on any bus", BUS_NAME)
        return 1
    global _BUS_NAME_OBJ
    _BUS_NAME_OBJ = keepalive
    GLib.MainLoop().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
