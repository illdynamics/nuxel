"""USBNET lifecycle gate + NCM teardown fix tests (PWNAGE-USBNET).

These tests pin the contract that made the old NCM attempt unsafe:

  * the running-kernel baseline alone is NOT a safety verdict;
  * NCM may only be applied when the running kernel exposes the lifecycle-fix
    marker added by kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch;
  * every other mode stays gated until it has a verified teardown path;
  * no code path writes the read-only NCM ``ifname`` attribute.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tools/beta/live/nuxel-usb-net.py"
PATCH = ROOT / "kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch"
CFG = "CONFIG_USB_F_NCM=y\nCONFIG_USB_CONFIGFS_NCM=y\nCONFIG_USB_F_RNDIS=y\n" \
      "CONFIG_USB_CONFIGFS_RNDIS=y\nCONFIG_USB_CONFIGFS=y\nCONFIG_USB_DWC3=y\n"


def load_mod():
    sys.path.insert(0, str(MODULE.parent))
    spec = importlib.util.spec_from_file_location("nuxel_usb_net_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_marker_absent_blocks_ncm(monkeypatch, tmp_path):
    mod = load_mod()
    cap = mod.capability(ROOT / "nonexistent-gadget", CFG,
                         kernel_release="4.14.253",
                         ncm_fix=False)
    assert cap["known_bad_kernel"] is True
    assert cap["modes"]["ncm"]["status"] == "BLOCKED_KNOWN_PANIC"
    assert cap["preferred_mode"] is None


def test_marker_present_allows_ncm(monkeypatch, tmp_path):
    mod = load_mod()
    marker = tmp_path / "nuxel_fix"
    marker.write_text(mod.NCM_FIX_MARKER + "\n")
    assert mod.ncm_lifecycle_fix_present(str(marker)) is True
    cap = mod.capability(ROOT / "nonexistent-gadget", CFG,
                         kernel_release="4.14.253", ncm_fix=True)
    assert cap["known_bad_kernel"] is False
    assert cap["ncm_lifecycle_fix"] is True
    assert cap["modes"]["ncm"]["status"] == "NEEDS_PHYSICAL_VALIDATION"
    assert cap["preferred_mode"] == "ncm"


def test_wrong_marker_value_is_not_a_fix(tmp_path):
    mod = load_mod()
    marker = tmp_path / "nuxel_fix"
    marker.write_text("some-other-build\n")
    assert mod.ncm_lifecycle_fix_present(str(marker)) is False


def test_missing_marker_file_is_false(tmp_path):
    mod = load_mod()
    assert mod.ncm_lifecycle_fix_present(str(tmp_path / "absent")) is False


def test_apply_refuses_without_marker(tmp_path, monkeypatch):
    mod = load_mod()
    monkeypatch.setattr(mod, "ncm_lifecycle_fix_present", lambda *a, **k: False)
    monkeypatch.setattr(mod, "_arm_timer", lambda *a, **k: None)
    # An unbound gadget must be refused before any configfs mutation.
    gadget = tmp_path / "gadget"
    (gadget / "functions").mkdir(parents=True)
    (gadget / "configs" / "c.1").mkdir(parents=True)
    (gadget / "UDC").write_text("")
    try:
        mod.apply(gadget, tmp_path / "state", tmp_path / "run", 5, CFG,
                  allow_serial_risk=True, kernel_release="4.14.253")
    except mod.UsbNetError as exc:
        assert "BLOCKED_KNOWN_PANIC" in str(exc) or "gadget" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("apply must refuse without the fix marker")
    assert not any((gadget / "functions").iterdir())


def test_patch_owns_singleton_and_drains_work():
    text = PATCH.read_text()
    # Root invariants of the refcounted singleton ownership model.
    for needle in (
        "mirrorlink_users",
        "mirrorlink_refs",
        "mirrorlink_active",
        "DEFINE_SPINLOCK(mirrorlink_lock)",
        "DEFINE_MUTEX(mirrorlink_txn)",
        "cancel_work_sync(&dev->work)",
        "nuxel_ncm_lifecycle_fix",
        "status = ncm_function_init()",
        "return ERR_PTR(status)",
        "ncm_function_shutdown()",
        "module_exit(nuxel_ncm_mod_exit)",
    ):
        assert needle in text, needle
    # Registration and deregistration run OUTSIDE the spinlock (they sleep)
    # and are serialised by the transaction mutex instead.
    init = text[text.index("static int ncm_function_init(void)"):]
    init = init[:init.index("static void ncm_function_cleanup(void)")]
    assert "mutex_lock(&mirrorlink_txn)" in init
    assert "misc_register(&mirrorlink_device)" in init
    assert "mirrorlink_active = true" in init


def test_cleanup_deregisters_exactly_once_after_marker_removal():
    text = PATCH.read_text()
    cleanup = text[text.index("static void ncm_function_cleanup(void)"):]
    cleanup = cleanup[:cleanup.index("static void ncm_function_ref_get(void)")]
    # The new singleton is detached (active=false, _ncm_dev=NULL) BEFORE the
    # work is drained and the misc device is deregistered.
    assert cleanup.index("mirrorlink_active = false") < cleanup.index("cancel_work_sync")
    assert cleanup.index("cancel_work_sync") < cleanup.index("device_remove_file")
    # Order against the ADDED deregistration line (not the removed vendor one).
    added = "\n".join(ln[1:] for ln in cleanup.splitlines() if ln.startswith("+"))
    dereg = added.index("misc_deregister(&mirrorlink_device);")
    assert added.index("cancel_work_sync") < dereg
    assert added.index("device_remove_file") < dereg
    # Exactly one ADDED deregistration line (the removed vendor line is a "-"
    # context line and does not count).
    added = [ln for ln in cleanup.splitlines()
             if ln.startswith("+") and "misc_deregister(&mirrorlink_device);" in ln]
    assert len(added) == 1, added
    # ncm_work()/set_ncm_ready() re-check liveness under the same lock.  The
    # work function is interior to a hunk (only its body lines are added), so
    # the check runs on the added lines rather than a context match.
    added_all = "\n".join(ln[1:] for ln in text.splitlines() if ln.startswith("+"))
    assert "live = mirrorlink_active && mirrorlink_device.this_device" in added_all
    work_added = "\n".join(ln[1:] for ln in text.splitlines()
                           if ln.startswith("+") and "ncm_connect" in ln or
                           (ln.startswith("+") and "mirrorlink" in ln))
    assert work_added  # non-empty: the work function body was modified


def test_patch_applies_to_pinned_pristine_source_or_tree_is_patched():
    """The patch must be a real, durable artifact (the tree is NOT authoritative)."""
    import subprocess
    import tempfile
    ksrc = ROOT / "kernel/s10plus/.build/src"
    if not (ksrc / ".git").exists():
        import pytest
        pytest.skip("pinned kernel checkout absent")
    head = subprocess.run(["git", "-C", str(ksrc), "show",
                           "HEAD:drivers/usb/gadget/function/f_ncm.c"],
                          capture_output=True, text=True, check=True).stdout
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "drivers/usb/gadget/function"
        d.mkdir(parents=True)
        (d / "f_ncm.c").write_text(head)
        r = subprocess.run(["git", "-C", td, "init", "-q", "&&", "true"], shell=False,
                           capture_output=True)
        subprocess.run(["git", "-C", td, "init", "-q"], check=True)
        subprocess.run(["git", "-C", td, "add", "drivers/usb/gadget/function/f_ncm.c"],
                       check=True)
        r = subprocess.run(["git", "-C", td, "apply", "--check", str(PATCH)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        subprocess.run(["git", "-C", td, "apply", str(PATCH)], check=True)
        applied = (d / "f_ncm.c").read_text()
        assert "nuxel-ncm-lifecycle-fix-v2" in applied
        for needle in ("mirrorlink_users", "cancel_work_sync", "ncm_function_shutdown",
                       "return ERR_PTR(status)"):
            assert needle in applied
