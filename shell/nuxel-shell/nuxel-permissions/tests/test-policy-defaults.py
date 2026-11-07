"""Policy-default and decision tests for nuxel-permd (Section 12.1).

These tests exercise the exact initial decisions from the permission-manager
specification: fail-closed defaults, the mirroring allow-by-default exception,
the verified fullscreen allowlist, and the Recorder microphone exception.
"""
import os
import sys
import tempfile
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PERMD = os.path.join(HERE, "..", "nuxel-permd.py")

_spec = importlib.util.spec_from_file_location("nuxel_permd", PERMD)
permd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(permd)

Registry = permd.Registry
Store = permd.Store
default_decision = permd.default_decision
UnsupportedCapability = permd.UnsupportedCapability

REGISTRY = Registry(os.path.join(HERE, "..", "capabilities.json"))


def make_store():
    tmp = tempfile.mkdtemp(prefix="nuxel-permd-test-")
    store = Store(directory=tmp, registry=REGISTRY)
    store.ensure_dirs()
    return tmp, store


def reload_store(directory):
    return Store(directory=directory, registry=REGISTRY)


def test_registry_has_nuxel_specific_capabilities():
    for cap_id in ("zoom", "fullscreen", "casting", "mirroring"):
        assert REGISTRY.capability(cap_id), "missing capability %s" % cap_id


def test_missing_record_denies_grant_required_except_mirroring():
    _tmp, store = make_store()
    # Unknown app, no records at all.
    for cap_id in ("camera", "microphone", "location", "contacts", "sms",
                   "zoom", "fullscreen", "casting", "network", "notifications"):
        r = store.decide("com.example.NewApp", cap_id)
        assert r["decision"] == "deny", (cap_id, r)
    # mirroring is the one allow-by-default capability.
    assert store.decide("com.example.NewApp", "mirroring")["decision"] == "allow"


def test_new_app_defaults():
    _tmp, store = make_store()
    assert store.decide("com.example.NewApp", "mirroring")["decision"] == "allow"
    assert store.decide("com.example.NewApp", "zoom")["decision"] == "deny"
    assert store.decide("com.example.NewApp", "casting")["decision"] == "deny"
    assert store.decide("com.example.NewApp", "fullscreen")["decision"] == "deny"


def test_fullscreen_allowlist_only_exact_ids():
    _tmp, store = make_store()
    for app_id in ("org.nuxel.Doom", "org.nuxel.Doom.Chocolate"):
        assert store.decide(app_id, "fullscreen")["decision"] == "allow", app_id
    for app_id in ("org.nuxel.Browser", "org.nuxel.Recorder", "com.example.NewApp"):
        assert store.decide(app_id, "fullscreen")["decision"] == "deny", app_id


def test_recorder_microphone_only_for_recorder():
    _tmp, store = make_store()
    assert store.decide("org.nuxel.Recorder", "microphone")["decision"] == "allow"
    for app_id in ("org.nuxel.Browser", "com.example.NewApp", "recorder"):
        assert store.decide(app_id, "microphone")["decision"] == "deny", app_id


def test_explicit_mirroring_deny_overrides_default():
    tmp, store = make_store()
    assert store.decide("com.example.NewApp", "mirroring")["decision"] == "allow"
    store.deny("com.example.NewApp", "mirroring")
    assert store.decide("com.example.NewApp", "mirroring")["decision"] == "deny"
    # survives reload (reboot)
    assert reload_store(tmp).decide("com.example.NewApp", "mirroring")["decision"] == "deny"


def test_explicit_deny_persists_across_restart():
    tmp, store = make_store()
    store.deny("org.nuxel.Browser", "camera")
    assert store.decide("org.nuxel.Browser", "camera")["decision"] == "deny"
    assert reload_store(tmp).decide("org.nuxel.Browser", "camera")["decision"] == "deny"


def test_persistent_allow_persists_across_restart():
    tmp, store = make_store()
    store.grant("org.nuxel.Browser", "camera", duration="always")
    assert store.decide("org.nuxel.Browser", "camera")["decision"] == "allow"
    assert reload_store(tmp).decide("org.nuxel.Browser", "camera")["decision"] == "allow"


def test_once_grant_consumed_exactly_once():
    _tmp, store = make_store()
    store.grant("org.nuxel.Browser", "camera", duration="once")
    first = store.decide("org.nuxel.Browser", "camera", consume_once=True)
    assert first["decision"] == "allow"
    second = store.decide("org.nuxel.Browser", "camera", consume_once=True)
    assert second["decision"] == "deny"


def test_revoke_and_revoke_all():
    tmp, store = make_store()
    store.grant("org.nuxel.Browser", "camera", duration="always")
    store.grant("org.nuxel.Browser", "microphone", duration="always")
    assert store.decide("org.nuxel.Browser", "camera")["decision"] == "allow"
    store.revoke("org.nuxel.Browser", "camera")
    assert store.decide("org.nuxel.Browser", "camera")["decision"] == "deny"
    store.revoke_all("org.nuxel.Browser")
    assert store.decide("org.nuxel.Browser", "microphone")["decision"] == "deny"


def test_unsupported_capabilities_cannot_be_granted():
    _tmp, store = make_store()
    for cap_id in ("clipboard", "sms_send_raw"):
        try:
            store.grant("org.nuxel.Browser", cap_id, duration="always")
            raise AssertionError("grant should have failed for %s" % cap_id)
        except UnsupportedCapability:
            pass
        assert store.decide("org.nuxel.Browser", cap_id)["decision"] == "deny"


def test_unknown_capability_and_identity_fail_closed():
    _tmp, store = make_store()
    assert store.decide("org.nuxel.Browser", "totally-unknown-cap")["decision"] == "deny"
    assert store.decide("../../etc/passwd", "camera")["decision"] == "deny"


def test_intrinsic_non_sensitive_resources_do_not_require_grant():
    _tmp, store = make_store()
    # audio output and clock read are grant_required=false in the registry.
    assert store.decide("org.nuxel.Browser", "audio")["decision"] == "allow"
    assert store.decide("org.nuxel.Browser", "clock_status")["decision"] == "allow"


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print("PASS %s" % fn.__name__)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL %s: %r" % (fn.__name__, exc))
    print("\n%d/%d tests passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
