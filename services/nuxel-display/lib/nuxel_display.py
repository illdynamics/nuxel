#!/usr/bin/env python3
"""Authoritative Nuxel external-display model (S10+ / beyond2lte).

The S10+ kernel has no DRM/KMS.  Its real external-video path is the Samsung
vendor stack:

    Type-C/CCIC (max77705)  ->  USB-PD / DP Alt Mode VDM
      ->  exynos-displayport (DP PHY/AUX/link training)
      ->  19050000.decon_t  ->  /dev/fb1

This module models that path instead of assuming DRM.  It is deliberately
side-effect free: it only reads sysfs/procfs and returns a structured snapshot.
`nuxel-displayd` owns the state machine and the mode changes; the bridge's
DisplayProvider consumes the same fields for Settings/Quick Settings.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# The DP audio-info parser is shared with nuxel-soundd.  The deployed module is
# /usr/lib/nuxel/nuxel_audio_outputs.py; the source-tree fallback keeps display
# tests runnable without an installed image.
for _cand in ("/usr/lib/nuxel", os.path.join(os.path.dirname(__file__), "..", "..", "nuxel-sound")):
    _cand = os.path.abspath(_cand)
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
try:
    from nuxel_audio_outputs import parse_dp_audio_info, parse_dp_pcm
except ImportError:  # pragma: no cover - display still reports the raw fields
    parse_dp_audio_info = None  # type: ignore
    parse_dp_pcm = None  # type: ignore

SCHEMA = "nuxel.display/2"

# Hardware states -----------------------------------------------------------
DISCONNECTED = "DISCONNECTED"
PARTNER_NO_PD = "PARTNER_NO_PD"
PD_NO_DP = "PD_NO_DP"
DP_NO_FB = "DP_NO_FB"
DP_LINK_READY = "DP_LINK_READY"
MIRRORING = "MIRRORING"
SEPARATE_DESKTOP = "SEPARATE_DESKTOP"

MODE_OFF = "off"
MODE_MIRROR_PORTRAIT = "mirror-portrait"
MODE_MIRROR_LANDSCAPE = "mirror-landscape"
MODE_FULLSCREEN = "fullscreen"
MODE_DESKTOP = "desktop"
# Legacy alias kept for older clients; normalized to mirror-portrait.
MODE_MIRROR = "mirror"
VALID_MODES = (MODE_OFF, MODE_MIRROR_PORTRAIT, MODE_MIRROR_LANDSCAPE,
               MODE_FULLSCREEN, MODE_DESKTOP, MODE_MIRROR)

MODE_LABELS = (
    (MODE_MIRROR_PORTRAIT, "Mirror portrait"),
    (MODE_MIRROR_LANDSCAPE, "Mirror landscape"),
    (MODE_FULLSCREEN, "Fullscreen"),
    (MODE_DESKTOP, "Separate desktop"),
)


def normalize_mode(mode: Optional[str]) -> str:
    """Map UI/client spellings onto the authoritative mode names."""
    value = str(mode or "").strip().lower()
    aliases = {
        "portrait": MODE_MIRROR_PORTRAIT,
        "mirror": MODE_MIRROR_PORTRAIT,
        "mirror-portrait": MODE_MIRROR_PORTRAIT,
        "landscape": MODE_MIRROR_LANDSCAPE,
        "mirror-landscape": MODE_MIRROR_LANDSCAPE,
        "full": MODE_FULLSCREEN,
        "fullscreen": MODE_FULLSCREEN,
        "desktop": MODE_DESKTOP,
        "separate": MODE_DESKTOP,
        "off": MODE_OFF,
    }
    return aliases.get(value, "")


def mode_rotation(mode: str) -> int:
    """External rotation: portrait is upright, landscape/fullscreen rotate 90."""
    return 90 if normalize_mode(mode) in (MODE_MIRROR_LANDSCAPE, MODE_FULLSCREEN) else 0


def mode_fit(mode: str) -> str:
    """fullscreen uses crop-to-fill; mirror modes preserve the whole screen."""
    return "fill" if normalize_mode(mode) == MODE_FULLSCREEN else "fit"

DEFAULT_RUNTIME_DIR = "/run/nuxel-display"
DEFAULT_STATE_DIR = "/var/lib/nuxel/external-display"


def _abs(root: str, rel: str) -> str:
    return os.path.join(root, rel.lstrip("/")) if rel.startswith("/") else rel


def _read(root: str, rel: str, default: Optional[str] = None) -> Optional[str]:
    try:
        with open(_abs(root, rel), "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return default


def _read_int(root: str, rel: str, default: Optional[int] = None) -> Optional[int]:
    text = _read(root, rel)
    if text is None:
        return default
    try:
        return int(text.strip(), 0)
    except (TypeError, ValueError):
        return default


def _exists(root: str, rel: str) -> bool:
    return os.path.exists(_abs(root, rel))


# Polling some Samsung sysfs attributes has side effects or logs: every read
# of ccic/usbpd_ids, dp_sec/dex or dp_sec/monitor_info prints a kernel line,
# and the old daemon produced ~12 lines/second.  Cache only on the real root;
# tests use fixture roots and always see fresh values.
_CACHE: Dict[str, tuple] = {}


def _cached(root: str, rel: str, ttl: float, fresh: bool = False) -> Optional[str]:
    if root != "/" or fresh:
        value = _read(root, rel)
        if root == "/":
            _CACHE[rel] = (time.monotonic(), value)
        return value
    now = time.monotonic()
    hit = _CACHE.get(rel)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = _read(root, rel)
    _CACHE[rel] = (now, value)
    return value


def invalidate_cache() -> None:
    _CACHE.clear()


def parse_dp_presets(text: Optional[str]) -> List[Dict[str, Any]]:
    """Parse /sys/class/dp_sec/forced_resolution (the driver's preset table)."""
    out: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(\d+)\s*:\s*(V(\d+)X(\d+)P(\d+)(\w*))", line.strip())
        if not m:
            continue
        out.append({
            "index": int(m.group(1)),
            "name": m.group(2),
            "width": int(m.group(3)),
            "height": int(m.group(4)),
            "refresh": int(m.group(5)),
        })
    return out


def preferred_preset(presets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prefer the exact 1080p60 preset used by the bridge, then fall back."""
    by_name = {p.get("name"): p for p in presets}
    for name in ("V1920X1080P60", "V1920X1080P59", "V1920X1080P60EXT",
                 "V1280X720P60", "V1280X720P60EXT",
                 "V640X480P60"):
        if name in by_name:
            return by_name[name]
    for width, height in ((1920, 1080), (1280, 720), (640, 480)):
        for preset in presets:
            if (preset.get("width"), preset.get("height")) == (width, height):
                return preset
    return None


_PNP_NAMES = {
    "PHL": "Philips",
    "BNQ": "BenQ",
    "SAM": "Samsung",
    "DEL": "Dell",
    "LEN": "Lenovo",
    "GSM": "LG",
    "SNY": "Sony",
}


def display_name_from_monitor_info(monitor_info: Optional[str]) -> Optional[str]:
    parts = [p.strip() for p in (monitor_info or "").split(",") if p.strip()]
    if not parts:
        return None
    vendor = parts[0]
    name = _PNP_NAMES.get(vendor, vendor)
    # Some vendor strings are already human readable (e.g. PHILIPS FTV).
    if len(vendor) > 3:
        name = vendor
    # monitor_info is vendor,product,serial.  Product is the model identity;
    # the serial is not a model name.
    if len(parts) > 1 and parts[1] not in ("0x0", "0", "0x1010101"):
        name += " " + parts[1]
    return name


def parse_fb_modes(text: Optional[str]) -> List[Dict[str, Any]]:
    """Parse ``/sys/class/graphics/fbN/modes`` (``U:640x480p-0``)."""
    out: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw:
            continue
        m = re.match(r"^([A-Za-z]*):?(\d+)x(\d+)(?:[pi]-?(\d+))?$", raw)
        if not m:
            out.append({"raw": raw, "width": None, "height": None,
                        "refresh": None, "source": "fbdev"})
            continue
        refresh = int(m.group(4)) if m.group(4) is not None else None
        out.append({
            "raw": raw,
            "width": int(m.group(2)),
            "height": int(m.group(3)),
            "refresh": refresh,
            "flags": m.group(1) or "",
            "source": "fbdev",
        })
    return out


def _parse_kv_lines(text: Optional[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def read_snapshot(root: str = "/", fresh: bool = False) -> Dict[str, Any]:
    """Read the live external-display path without changing anything."""
    typec_ports: List[Dict[str, Any]] = []
    typec_root = _abs(root, "/sys/class/typec")
    try:
        names = sorted(os.listdir(typec_root))
    except OSError:
        names = []
    for name in names:
        if not name.startswith("port") or "-" in name:
            continue
        base = "/sys/class/typec/" + name
        partner_path = _abs(root, base + "-partner")
        partner = os.path.isdir(partner_path)
        ids = _read(root, "/sys/class/sec/ccic/usbpd_ids")
        typec_ports.append({
            "name": name,
            "data_role": _read(root, base + "/data_role"),
            "power_role": _read(root, base + "/power_role"),
            "power_operation_mode": _read(root, base + "/power_operation_mode"),
            "usb_power_delivery_revision": _read(root, base + "/usb_power_delivery_revision"),
            "partner": partner,
            "partner_name": partner and _read(root, base + "-partner/product"),
            "partner_pd": partner and _read(root, base + "-partner/supports_usb_power_delivery"),
            "partner_accessory_mode": partner and _read(root, base + "-partner/accessory_mode"),
        })

    switches: Dict[str, int] = {}
    switch_root = _abs(root, "/sys/class/switch")
    try:
        names = sorted(os.listdir(switch_root))
    except OSError:
        names = []
    for name in names:
        value = _read_int(root, "/sys/class/switch/%s/state" % name)
        if value is not None:
            switches[name] = value

    extcon: List[Dict[str, Any]] = []
    extcon_dp = False
    extcon_root = _abs(root, "/sys/class/extcon")
    try:
        names = sorted(os.listdir(extcon_root))
    except OSError:
        names = []
    for name in names:
        state = _read(root, "/sys/class/extcon/%s/state" % name) or ""
        is_dp = bool(re.search(r"(?:^|\s)DP=(?:1|true|on)(?:\s|$)", state, re.I))
        extcon_dp = extcon_dp or is_dp
        extcon.append({"name": _read(root, "/sys/class/extcon/%s/name" % name) or name,
                       "state": state, "dp": is_dp})

    fbs: Dict[str, Any] = {}
    for fb in ("fb0", "fb1"):
        base = "/sys/class/graphics/" + fb
        if not _exists(root, base):
            fbs[fb] = {"present": False}
            continue
        device_link = _abs(root, base + "/device")
        try:
            device = os.path.basename(os.path.realpath(device_link))
        except OSError:
            device = None
        fbs[fb] = {
            "present": True,
            "device": device,
            "virtual_size": _read(root, base + "/virtual_size"),
            "stride": _read_int(root, base + "/stride"),
            "bits_per_pixel": _read_int(root, base + "/bits_per_pixel"),
            "rotate": _read_int(root, base + "/rotate"),
            "blank": _read(root, base + "/blank"),
            "state": _read_int(root, base + "/state"),
            "mode": _read(root, base + "/mode"),
            "modes_raw": _read(root, base + "/modes"),
            "modes": parse_fb_modes(_read(root, base + "/modes")),
        }

    dp_sec: Dict[str, Any] = {"present": _exists(root, "/sys/class/dp_sec")}
    if dp_sec["present"]:
        dp_sec.update({
            # These reads print kernel lines, so cache them on the live root.
            "dex": _read_int(root, "/sys/class/dp_sec/dex") if root != "/" else None,
            "dp_drm": _cached(root, "/sys/class/dp_sec/dp_drm", 10.0, fresh),
            "monitor_info": _cached(root, "/sys/class/dp_sec/monitor_info", 2.0, fresh),
            "forced_resolution": _cached(root, "/sys/class/dp_sec/forced_resolution", 30.0, fresh),
            "audio_test": _cached(root, "/sys/class/dp_sec/audio_test", 10.0, fresh),
            # NEVER read /sys/class/dp_sec/unit_test: its show method runs the
            # vendor EDID parser and overwrites the real sink identity with the
            # built-in BenQ SW320 test EDID.  It is a write-trigger, not a flag.
            "dp_test": _cached(root, "/sys/class/dp_sec/dp_test", 30.0, fresh),
        })

    ccic: Dict[str, Any] = {"present": _exists(root, "/sys/class/sec/ccic")}
    if ccic["present"]:
        ids_text = _cached(root, "/sys/class/sec/ccic/usbpd_ids", 2.0, fresh)
        ccic.update({
            "state": _read_int(root, "/sys/class/sec/ccic/state"),
            "usbpd_ids": ids_text,
            "usbpd_type": _read_int(root, "/sys/class/sec/ccic/usbpd_type"),
            # rid/cur_version/src_version/cc_pin_status are diagnostic and each
            # read logs a kernel line.  They are intentionally not polled.
        })

    pcm_text = _read(root, "/proc/asound/pcm") or ""
    if parse_dp_pcm is not None:
        dp_pcm = parse_dp_pcm(pcm_text)
        pcm_line = (dp_pcm or {}).get("line")
    else:
        pcm_line = next((line.strip() for line in pcm_text.splitlines()
                         if "DP Audio" in line), None)
        dp_pcm = {"line": pcm_line} if pcm_line else None
    dp_audio_pcm = dp_pcm is not None
    ch_hdmi_audio = switches.get("ch_hdmi_audio")
    secdp = switches.get("secdp")
    secdp_msg = switches.get("secdp_msg")

    partner = any(p["partner"] for p in typec_ports)
    pd_ids = (ccic.get("usbpd_ids") or "").strip()
    pd_identity = bool(pd_ids and pd_ids not in ("0000:0000", "0:0"))
    if not pd_identity and ccic.get("usbpd_type"):
        pd_identity = True
    dp_link = bool(secdp == 1 and extcon_dp)
    external_fb = bool(fbs.get("fb1", {}).get("present"))
    fb1_modes = fbs.get("fb1", {}).get("modes") or []
    dp_presets = parse_dp_presets(dp_sec.get("forced_resolution"))
    selected_preset = preferred_preset(dp_presets) if dp_link else None

    if not partner:
        state = DISCONNECTED
    elif not pd_identity:
        state = PARTNER_NO_PD
    elif not dp_link:
        state = PD_NO_DP
    elif not external_fb:
        state = DP_NO_FB
    else:
        state = DP_LINK_READY

    blockers: List[str] = []
    if state == DISCONNECTED:
        blockers.append("no Type-C partner is attached")
    if state == PARTNER_NO_PD:
        blockers.append(
            "Type-C partner has no USB-PD identity (usbpd_ids=%s, usbpd_type=%s); "
            "DisplayPort Alt Mode is negotiated with a structured VDM over USB-PD, "
            "so the DP link cannot start." % (pd_ids or "unknown", ccic.get("usbpd_type")))
    if state == PD_NO_DP:
        blockers.append(
            "USB-PD identity %s is present but DisplayPort Alt Mode is not negotiated "
            "(secdp=%s, extcon DP=%s)." % (pd_ids, secdp, extcon_dp))
    if state == DP_NO_FB:
        blockers.append("DP link is up but the decon_t external framebuffer (/dev/fb1) is missing")

    if parse_dp_audio_info is not None:
        audio_info = parse_dp_audio_info(ch_hdmi_audio, dp_link, bool(dp_audio_pcm))
    else:
        raw = ch_hdmi_audio
        try:
            raw = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            raw = None
        audio_info = {"available": bool(dp_link and dp_audio_pcm and raw and raw > 0),
                      "reason": None if raw and raw > 0 else "no DP audio info",
                      "raw": raw, "channels": (raw & 0xff).bit_length() if raw and raw > 0 else 0,
                      "channel_mask": (raw & 0xff) if raw and raw > 0 else 0,
                      "sample_rate_flags": ((raw >> 19) & 0x7) if raw and raw > 0 else 0,
                      "bit_rate_flags": ((raw >> 16) & 0x7) if raw and raw > 0 else 0,
                      "speaker_allocation": ((raw >> 8) & 0xff) if raw and raw > 0 else 0}
    audio_available = bool(audio_info.get("available"))
    audio_blockers: List[str] = []
    if not dp_link:
        audio_blockers.append("DP link is not ready, so no HDMI/DP audio route exists")
    elif not dp_audio_pcm:
        audio_blockers.append("kernel exposes no 'DP Audio' PCM in /proc/asound/pcm")
    elif not audio_available:
        audio_blockers.append(str(audio_info.get("reason") or
                                  "DP sink reports no usable LPCM audio endpoint"))

    monitor_info = dp_sec.get("monitor_info") if dp_link else None
    display_name = display_name_from_monitor_info(monitor_info) if monitor_info else None

    return {
        "schema": SCHEMA,
        "timestamp": time.time(),
        "state": state,
        "partner": partner,
        "typec_ports": typec_ports,
        "pd_identity": pd_identity,
        "pd_ids": pd_ids or None,
        "pd_type": ccic.get("usbpd_type"),
        "dp_link": dp_link,
        "secdp": secdp,
        "secdp_msg": secdp_msg,
        "extcon": extcon,
        "extcon_dp": extcon_dp,
        "ccic": ccic,
        "dp_sec": dp_sec,
        "switches": switches,
        "framebuffers": fbs,
        "internal_fb": fbs.get("fb0"),
        "external_fb": fbs.get("fb1"),
        "external_fb_present": external_fb,
        "external_modes": fb1_modes,
        "dp_presets": dp_presets,
        "selected_preset": selected_preset,
        "selected_resolution": ({"width": selected_preset["width"],
                                 "height": selected_preset["height"],
                                 "refresh": selected_preset["refresh"],
                                 "name": selected_preset["name"]}
                                if selected_preset else None),
        "mode_choices": [{"mode": m, "label": label,
                          "supported": (m != MODE_DESKTOP)}
                         for m, label in MODE_LABELS],
        "display_name": display_name,
        "monitor_info_raw": monitor_info,
        "audio": {
            "available": audio_available,
            "dp_audio_pcm": dp_audio_pcm,
            "pcm": pcm_line,
            "pcm_device": dp_pcm,
            "ch_hdmi_audio": ch_hdmi_audio,
            "ch_hdmi_audio_hex": (None if not isinstance(ch_hdmi_audio, int) else
                                  "0x%08x" % (ch_hdmi_audio & 0xffffffff)),
            "audio_info": audio_info,
            "channels": audio_info.get("channels"),
            "sample_rate_flags": audio_info.get("sample_rate_flags"),
            "blockers": audio_blockers,
            "blocker": "; ".join(audio_blockers) if audio_blockers else None,
        },
        "mirror_supported": state == DP_LINK_READY,
        "blockers": blockers,
        "blocker": "; ".join(blockers) if blockers else None,
    }


def _float_or_none(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def run_wlr_randr(root: str = "/", env: Optional[Dict[str, str]] = None,
                  timeout: float = 3.0) -> Dict[str, Any]:
    """Return the real compositor outputs (read-only, bounded)."""
    run_env = dict(os.environ)
    run_env.setdefault("XDG_RUNTIME_DIR", "/run/nuxel-wayland")
    run_env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    run_env.setdefault("PATH", "/usr/bin:/usr/sbin:/bin:/sbin")
    if env:
        run_env.update(env)
    try:
        proc = subprocess.run(["wlr-randr"], capture_output=True, text=True,
                              timeout=float(timeout), env=run_env)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"success": False, "outputs": [], "error": str(exc)}
    outputs: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in (proc.stdout or "").splitlines():
        m = re.match(r"^(\S+)\s+\"(.*)\"\s*$", line)
        if m:
            current = {"name": m.group(1), "description": m.group(2),
                       "enabled": None, "width": None, "height": None,
                       "refresh": None, "scale": None, "transform": None,
                       "position": None}
            outputs.append(current)
            continue
        if current is None:
            continue
        if "Enabled:" in line:
            current["enabled"] = line.split(":", 1)[1].strip().lower() == "yes"
        elif "Modes:" in line:
            continue
        elif "(current)" in line:
            mm = re.search(r"(\d+)x(\d+)\s+px", line)
            if mm:
                current["width"] = int(mm.group(1))
                current["height"] = int(mm.group(2))
        elif "Position:" in line:
            current["position"] = line.split(":", 1)[1].strip()
        elif "Transform:" in line:
            current["transform"] = line.split(":", 1)[1].strip()
        elif "Scale:" in line:
            current["scale"] = _float_or_none(line.split(":", 1)[1].strip())
    return {"success": proc.returncode == 0, "outputs": outputs,
            "error": None if proc.returncode == 0 else (proc.stderr or "").strip()[:400]}


def choose_outputs(outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick the phone output and an independent external output, if present."""
    enabled = [o for o in outputs if o.get("enabled") is not False]
    primary = None
    for o in enabled:
        if (o.get("position") or "").replace(" ", "") in ("0,0", "0,0px"):
            primary = o
            break
    if primary is None and enabled:
        primary = enabled[0]
    external = None
    for o in enabled:
        if primary is not None and o.get("name") == primary.get("name"):
            continue
        external = o
        break
    return {"primary": primary, "external": external,
            "names": [o.get("name") for o in outputs],
            "enabled_names": [o.get("name") for o in enabled]}


@dataclass
class DisplayStateMachine:
    """Small, testable connection-generation state machine.

    A new generation is created only on a real DISCONNECTED/PARTNER/PD -> DP
    ready transition.  Repeated polls of the same ready state never re-notify.
    """
    state: str = DISCONNECTED
    generation: int = 0
    notified_generation: Optional[int] = None
    mode: str = MODE_OFF
    last_error: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, snapshot: Dict[str, Any], now: Optional[float] = None) -> List[Dict[str, Any]]:
        new_state = snapshot.get("state") or DISCONNECTED
        events: List[Dict[str, Any]] = []
        if new_state == DP_LINK_READY and self.state != DP_LINK_READY:
            self.generation += 1
            events.append({"event": "connected", "generation": self.generation,
                           "state": new_state, "at": now or time.time(),
                           "snapshot": snapshot})
        elif new_state != DP_LINK_READY and self.state == DP_LINK_READY:
            events.append({"event": "disconnected", "generation": self.generation,
                           "state": new_state, "at": now or time.time(),
                           "snapshot": snapshot})
            self.mode = MODE_OFF
        elif new_state != self.state:
            events.append({"event": "state_changed", "generation": self.generation,
                           "state": new_state, "at": now or time.time(),
                           "snapshot": snapshot})
        self.state = new_state
        for event in events:
            self.history.append({"event": event["event"], "state": event["state"],
                                 "generation": event["generation"], "at": event["at"]})
            del self.history[:-64]
        return events

    def should_notify(self) -> bool:
        return (self.state == DP_LINK_READY and
                self.notified_generation != self.generation)

    def mark_notified(self, generation: Optional[int] = None) -> None:
        self.notified_generation = self.generation if generation is None else int(generation)

    def set_mode(self, mode: str) -> None:
        normalized = normalize_mode(mode)
        if not normalized:
            raise ValueError("invalid display mode: %s" % mode)
        self.mode = normalized


def mode_body(snapshot: Dict[str, Any], mode: str) -> str:
    mode = normalize_mode(mode)
    if mode == MODE_MIRROR_PORTRAIT:
        return "Mirroring the built-in screen upright on the external display."
    if mode == MODE_MIRROR_LANDSCAPE:
        return "Mirroring the built-in screen rotated to landscape on the external display."
    if mode == MODE_FULLSCREEN:
        return "Mirroring the built-in screen, cropped to fill the external display."
    if mode == MODE_DESKTOP:
        return "The external display is now an independent desktop."
    return "External display output is off; the built-in screen is unchanged."


def notification_payload(snapshot: Dict[str, Any], generation: int,
                         suggested_mode: Optional[str] = None,
                         replaces_id: Optional[int] = None,
                         error: Optional[str] = None) -> Dict[str, Any]:
    name = snapshot.get("display_name") or "External display"
    selected = snapshot.get("selected_resolution") or {}
    modes = snapshot.get("external_modes") or []
    mode_text = None
    if selected.get("width") and selected.get("height"):
        # The fb1 var is frozen at the driver's probe default (640x480); the
        # real scan-out timing is selected_resolution.
        mode_text = "%dx%d" % (selected["width"], selected["height"])
        if selected.get("refresh"):
            mode_text += "@%d" % selected["refresh"]
    elif modes:
        m = modes[0]
        if m.get("width") and m.get("height"):
            mode_text = "%dx%d" % (m["width"], m["height"])
            if m.get("refresh"):
                mode_text += "@%d" % m["refresh"]
    detail = name + (" · " + mode_text if mode_text else "")
    if error:
        summary = "External display mode failed"
        body = error
        actions = ["mirror-portrait", "Retry as portrait",
                   "mirror-landscape", "Retry as landscape",
                   "fullscreen", "Retry fullscreen",
                   "settings", "Display settings"]
    else:
        summary = "External display connected"
        body = detail + "\nChoose how to use the connected display."
        suggested = normalize_mode(suggested_mode or "")
        if suggested in (MODE_MIRROR_PORTRAIT, MODE_MIRROR_LANDSCAPE,
                         MODE_FULLSCREEN, MODE_DESKTOP):
            body += "\nLast used: " + mode_body(snapshot, suggested).split(".")[0] + "."
        actions = ["mirror-portrait", "Mirror portrait",
                   "mirror-landscape", "Mirror landscape",
                   "fullscreen", "Fullscreen"]
        if snapshot.get("desktop_supported"):
            actions += ["desktop", "Separate desktop"]
        else:
            actions += ["settings", "Display settings"]
    payload: Dict[str, Any] = {
        "app_id": "org.nuxel.Display",
        "app_name": "Nuxel Display",
        "summary": summary,
        "body": body,
        "urgency": "normal",
        "icon": "",
        "actions": actions,
        "hints": {
            "nuxel.display.generation": int(generation),
            "nuxel.display.state": snapshot.get("state"),
            "nuxel.display.modes": modes,
            "nuxel.display.selected_resolution": selected,
            "nuxel.display.display_name": snapshot.get("display_name"),
            "nuxel.display.desktop_available": bool(snapshot.get("desktop_supported")),
            "nuxel.display.blocker": snapshot.get("blocker"),
        },
        "source": "nuxel-displayd",
        "expire_timeout": 0,
    }
    if replaces_id:
        payload["replaces_id"] = int(replaces_id)
    return payload


def mode_error(snapshot: Dict[str, Any], mode: str) -> Optional[str]:
    mode = normalize_mode(mode)
    if not mode:
        return "invalid display mode"
    if mode == MODE_OFF:
        return None
    if snapshot.get("state") != DP_LINK_READY:
        return ("External display is not ready: %s"
                % (snapshot.get("blocker") or snapshot.get("state")))
    if not snapshot.get("external_fb_present"):
        return "No decon_t external framebuffer (/dev/fb1) is available."
    if mode == MODE_DESKTOP and not snapshot.get("desktop_supported"):
        return ("Separate desktop needs a second compositor output; "
                "only the phone output is currently exposed.")
    return None
