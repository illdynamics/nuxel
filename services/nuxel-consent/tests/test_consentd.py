#!/usr/bin/env python3
"""Unit tests for the consent surface (no D-Bus, no device required)."""
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

# The device has python3-dbus + PyGObject; the developer host may not.  Stub
# just enough so the consent policy functions can be imported and tested.
for _name in ("dbus", "dbus.service", "dbus.mainloop", "dbus.mainloop.glib"):
    if _name not in sys.modules:
        mod = types.ModuleType(_name)
        mod.exceptions = types.SimpleNamespace(DBusException=type("DBusException", (Exception,), {}))
        mod.service = types.SimpleNamespace(Object=object, BusName=lambda *a, **k: None,
                                            method=lambda *a, **k: (lambda fn: fn),
                                            signal=lambda *a, **k: (lambda fn: fn))
        mod.Interface = lambda *a, **k: None
        mod.SystemBus = lambda *a, **k: None
        mod.SessionBus = lambda *a, **k: None
        mod.UTF8_STRING_NO_LENGTH = str
        sys.modules[_name] = mod
if "gi" not in sys.modules:
    gi = types.ModuleType("gi")
    glib = types.ModuleType("gi.repository")
    glib.GLib = types.SimpleNamespace(SOURCE_REMOVE=False, timeout_add=lambda *a: 1, source_remove=lambda *a: None, MainLoop=object)
    gi.repository = glib
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = glib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import nuxel_consentd as cd  # noqa: E402


class CanonicalTests(unittest.TestCase):
    def test_alias_resolves_to_resource(self):
        self.assertEqual(cd.canonical_cap("audio:capture"), "audio")
        # Registry aliases (mic, record, audio-input) resolve via permD; the
        # agent's local fallback only knows base tokens and base:delegate.
        self.assertEqual(cd.canonical_cap("microphone"), "microphone")
        with self.assertRaises(cd.ConsentError):
            cd.canonical_cap("mic")

    def test_known_tokens(self):
        for token in ("microphone", "nfc", "camera", "location", "contacts"):
            self.assertEqual(cd.canonical_cap(token), token)

    def test_unknown_token_refused(self):
        with self.assertRaises(cd.ConsentError) as ctx:
            cd.canonical_cap("nonsense")
        self.assertEqual(ctx.exception.code, "unsupported_capability")

    def test_empty_refused(self):
        with self.assertRaises(cd.ConsentError):
            cd.canonical_cap("   ")


class DeviceSupportTests(unittest.TestCase):
    def _write(self, doc):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh)
        return path

    def test_unsupported_verdict_blocks_prompt(self):
        path = self._write({"capabilities": [
            {"id": "nfc", "verdict": "NOT_SUPPORTED_ON_DEVICE"},
            {"id": "microphone", "verdict": "PARTIAL", "enforceable": "partial"},
        ]})
        with mock.patch.object(cd, "CAPS_JSON", path):
            self.assertFalse(cd.capability_allowed_on_device("nfc"))
            self.assertTrue(cd.capability_allowed_on_device("microphone"))

    def test_hard_deny_never_prompted(self):
        self.assertFalse(cd.capability_allowed_on_device("sms_send_raw"))

    def test_missing_registry_keeps_safe_tokens(self):
        with mock.patch.object(cd, "CAPS_JSON", "/nonexistent.json"):
            self.assertTrue(cd.capability_allowed_on_device("microphone"))
            self.assertFalse(cd.capability_allowed_on_device("sms_send_raw"))


class PermDWriteTests(unittest.TestCase):
    def test_allow_once_uses_grant_once(self):
        seen = {}

        def fake_permd(args, timeout=15):
            seen.setdefault("calls", []).append(args)
            return {"rc": 0, "data": None}, None

        chk_calls = {}

        def fake_run(argv, **kwargs):
            chk_calls["argv"] = argv
            return mock.Mock(returncode=0, stdout="granted", stderr="")

        with mock.patch.object(cd, "_permd", fake_permd), \
                mock.patch.object(cd.subprocess, "run", fake_run):
            store, err = cd._apply_permd_decision(
                "org.example.App", "microphone", "allow", cd.ALLOW_ONCE)
        self.assertIsNone(err)
        self.assertEqual(store, "permD")
        self.assertEqual(seen["calls"][0], ["grant", "org.example.App",
                                           "microphone", "--duration", "once"])
        chk = chk_calls.get("argv")
        self.assertEqual(chk[1:3], [cd.PERMD, "check"])
        self.assertEqual(chk[3:5], ["org.example.App", "microphone"])

    def test_deny_uses_deny_subcommand(self):
        seen = {}

        def fake_permd(args, timeout=15):
            seen.setdefault("calls", []).append(args)
            return {"rc": 0, "data": None}, None

        def fake_run(argv, **kwargs):
            return mock.Mock(returncode=0, stdout="ok", stderr="")

        with mock.patch.object(cd, "_permd", fake_permd), \
                mock.patch.object(cd.subprocess, "run", fake_run):
            _, err = cd._apply_permd_decision(
                "org.example.App", "camera", "deny", cd.ALLOW_ALWAYS)
        self.assertIsNone(err)
        self.assertEqual(seen["calls"][0], ["deny", "org.example.App", "camera"])

    def test_permd_failure_returns_error(self):
        with mock.patch.object(cd, "_permd",
                               lambda *a, **k: ({"rc": 3, "stderr": "REFUSED"}, None)):
            store, err = cd._apply_permd_decision(
                "org.example.App", "clipboard", "allow", cd.ALLOW_ONCE)
        self.assertIsNone(store)
        self.assertIn("REFUSED", err)


class PromptActionTests(unittest.TestCase):
    def test_actions_exactly_four_choices(self):
        # Constructed without D-Bus: the four actions are the order the
        # notification UI pairs (key, label).
        agent = object.__new__(cd.PhoshAgent)
        actions = agent._prompt_actions()
        keys = actions[0::2]
        self.assertEqual(keys, ["allow-once", "allow-always", "deny", "cancel"])
        self.assertEqual(len(actions), 8)


if __name__ == "__main__":
    unittest.main()
