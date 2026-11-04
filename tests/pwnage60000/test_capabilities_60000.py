"""PWNAGE-60000 truthful diagnostics, media guard and bridge invariants."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "tools/s10plus/a67/nuxel-gpu-status"
WLFB = ROOT / "tools/s10plus/a67/nuxel-wl-fb.c"
GUARD = ROOT / "tools/s10plus/a29/nuxel-gstreamer-guard.sh"
TYPEC = ROOT / "tools/s10plus/a33/nuxel-typec-diag.sh"
CAST = ROOT / "tools/s10plus/a33/nuxel-cast-diag.sh"
MFC_README = ROOT / "evidence/pwnage-60000/mfc/README.md"
WEBKIT_README = ROOT / "evidence/pwnage-60000/webkit/README.md"


def test_status_tool_reports_layers_and_never_opens_video_or_fb():
    s = STATUS.read_text()
    assert 'schema": "nuxel.gpu-status/2"' in s
    for layer in ("kernel_gpu", "egl", "phoc", "gtk3", "gtk4", "webkit",
                  "linux_dmabuf", "final_output", "video",
                  "external_display", "casting"):
        assert '"%s"' % layer in s
    assert 'open("/dev/video' not in s
    assert "os.open(\"/dev/video" not in s
    assert '"/dev/fb0"' in s  # only scanned as a symlink target, never opened
    assert 'os.symlink' not in s
    assert "WEBKIT_WEB_RENDER_DEVICE_FILE" in s
    assert "drm_main_device_null" in s
    assert "BLOCKED_GUARDED" in s


def test_status_json_is_valid_and_separates_presentation():
    p = subprocess.run([sys.executable, str(STATUS), "--json", "--no-probe"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    doc = json.loads(p.stdout)
    assert doc["schema"] == "nuxel.gpu-status/2"
    assert "webkit_transport" in doc["profile_summary"]
    assert doc["profile_summary"]["zero_copy_scanout"] is False
    assert "webkit_dmabuf_presentation" in doc["capabilities"]
    assert "zero_copy_scanout" in doc["capabilities"]


def test_mfc_documentation_has_exact_blocker():
    s = MFC_README.read_text()
    assert "mfc_fw.bin" in s
    assert "MFC_DRIVER_INFO 180315" in s
    assert "CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y" in s
    assert "did **not** open any `/dev/video*`" in s
    assert "BLOCKED_GUARDED" in s


def test_gstreamer_guard_is_still_active_in_source():
    s = GUARD.read_text()
    for plugin in ("libgstvideo4linux2.so", "libgstv4l2codecs.so",
                   "libgstkms.so", "libgstopengl.so"):
        assert plugin in s
    assert "nuxel-disabled" in s
    assert "mv" in s


def test_typec_and_cast_diagnostics_are_read_only():
    for path in (TYPEC, CAST):
        s = path.read_text()
        assert "READ-ONLY" in s
        assert "--json" in s
        for forbidden in ("tee ", "systemctl restart", "modprobe ", "echo 1 >",
                          "echo 0 >", "dd if=", "mkfs", "rm -f /sys"):
            assert forbidden not in s, (path, forbidden)
    assert "NEEDS_OWNER_TEST" in TYPEC.read_text() or "visible_output_verified" in TYPEC.read_text()
    assert "moving_picture_verified" in CAST.read_text()


def test_webkit_gate_evidence_pins_real_source():
    s = WEBKIT_README.read_text()
    assert "628d6ce1850e17225185a5807a9d0aa375bae2be" in s
    assert "drmMainDevice()" in s
    assert "WEBKIT_WEB_RENDER_DEVICE_FILE" in s
    assert "BLOCKED" in s
    assert "RendererBufferTransportMode::Hardware" in s
    assert "CONFIG_DRM_VGEM" in s


def test_wlfb_has_persistent_buffer_dirty_runs_and_phase_timings():
    s = WLFB.read_text()
    assert "PWNAGE-60000: wlr-screencopy is not a one-shot buffer" in s
    assert "dirty_y0[MAX_DIRTY_RUNS]" in s
    assert "dirty_is_full" in s
    assert "for (int i = 0; i < ndirty; i++)" in s
    assert "pan_avg_ms" in s and "capture_avg_ms" in s and "compare_avg_ms" in s
    assert "dirty-run coalescing" in s and "fragmentation fallback" in s
    # One writer / no second framebuffer owner.
    assert "owner_lock_acquire" in s
    assert 'open("/dev/fb0", O_RDWR)' in s
    assert s.count('open("/dev/fb0"') == 1
    # Rotation/touch semantics are untouched.
    assert "presenter_rotation=0" in s and "double_rotation=0" in s


def test_api_maps_layered_status_conservatively():
    s = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    assert "_graphics_status_from_layers" in s
    assert "GPU-RENDERED / SHM-PRESENTED" in s
    assert "zero_copy_scanout" in s
    assert "WebKit 2.54.1 Hardware transport requires drmMainDevice()" in s
