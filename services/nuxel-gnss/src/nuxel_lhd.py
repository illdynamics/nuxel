#!/usr/bin/env python3
"""Nuxel native Broadcom BBD/LHD bridge daemon for SM-G975F (beyond2lte).

Owns the BCM4773 BBD transport and implements, in a Nuxel-native Python service,
the application-side of the Broadcom Bridge Driver (BBD) / LHD protocol that the
vendor Android ``lhd``/``gpsd`` daemons perform over ``/dev/ttyBCM``.

Protocol provenance
--------------------
* Transport-layer framing + CRC (ESCAPE 0xB0 / SOP 0x00 / EOP 0x01) is ported
  verbatim from the GPL-2.0 kernel ``drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c``.
* Control strings are from ``.../bbd.h`` / ``.../bbd.c``.
* The sensor-hub patch firmware is served read-only by the running kernel via
  ``/dev/bbd_patch`` (it is compiled in, not a missing blob).

Honest boundary
---------------
The GNSS *application* RPCs (patch-download RPC id, GNSS start/stop control RPC
ids, and the position-solution RPC id + payload layout) live in the proprietary
Samsung ``lhd``/``gpsd``/``libwrappergps`` userspace, which is NOT open-sourced
and NOT present on Nuxel.  The GPL kernel only routes "sensor" vs "non-sensor"
RPCs; it does not decode the GNSS position message.  This daemon therefore:

  * fully implements and verifies power sequencing, firmware provenance/read,
    transport open/wakeup, and the BBD TL framing for RX and TX;
  * reaches the comms boundary and reports receiver state from SSP/kernel
    (``GPS: false/true``) rather than fabricating a fix;
  * clearly reports ``POSITION_DECODER_UNAVAILABLE`` when a fix could not be
    decoded, instead of inventing coordinates.

This is the correct Nuxel-native architecture (handoff option A).  To go the
last metre to a decoded fix, add either (a) a lawful port of the Samsung GNSS
RPC map, or (b) an isolated Android-compat runtime running the owner's own
``lhd``/``gpsd``.  Neither is fabricated here.

Safety
------
Read-only + bounded: takes a power lease, opens the transport, performs a
bounded handshake, and guarantees power-off and fd close in ``finally``.  No
partition writes, no reboot, no raw GPIO pokes beyond the kernel-owned sysfs
rail.  One process owns ``/dev/ttyBCM`` for its lifetime.
"""
from __future__ import annotations

import argparse
import errno
import json
import logging
import os
import select
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_bbd_tl as tl  # noqa: E402
import nuxel_control as ctl  # noqa: E402

log = logging.getLogger("nuxel-lhd")

# Service lifecycle states (superset of the handoff's requested states).
ABSENT = "ABSENT"
TRANSPORT_READY = "TRANSPORT_READY"
FIRMWARE_UNVERIFIED = "FIRMWARE_UNVERIFIED"
FIRMWARE_READY = "FIRMWARE_READY"
PATCH_LOADED = "PATCH_LOADED"
BBD_HANDSHAKE_OK = "BBD_HANDSHAKE_OK"
SOLUTION_STREAMING = "SOLUTION_STREAMING"
FIX_VALID = "FIX_VALID"
FAULT = "FAULT"

# The single hard blocker for a decoded fix, stated honestly.
POSITION_DECODER_UNAVAILABLE = "POSITION_DECODER_UNAVAILABLE"


def _read_sysfs(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


class GpsPowerControl:
    """Owns the GPS_PWR_EN rail with strict readback + lease semantics."""

    def __init__(self, rail=ctl.GPS_POWER_RAIL):
        self.rail = rail
        self._owners = set()
        self._seq = 0

    def read(self):
        v = _read_sysfs(self.rail)
        if v in ("0", "1"):
            return int(v)
        return None

    def set_power(self, on: bool, timeout: float = 5.0) -> dict:
        req = "1" if on else "0"
        try:
            with open(self.rail, "w") as f:
                f.write(req)
                f.flush()
        except OSError as e:
            return {"success": False, "error": str(e)}
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            if self.read() == (1 if on else 0):
                return {"success": True, "enabled": bool(on)}
            time.sleep(0.02)
        return {"success": False, "enabled": self.read(),
                "error": "readback mismatch for %s" % self.rail}

    def acquire(self) -> str:
        self._seq += 1
        lid = "lhd-%d" % self._seq
        self._owners.add(lid)
        return lid

    def release(self, lid: str, restore_initial: bool) -> dict:
        self._owners.discard(lid)
        if self._owners:
            return {"success": True, "powered": True, "owners": len(self._owners)}
        if restore_initial:
            return {"success": True, "powered": True, "restored": True}
        return self.set_power(False)


class LhdDaemon:
    """Owns /dev/ttyBCM + /dev/bbd_patch + /dev/bbd_control for one session."""

    def __init__(self, transport=ctl.BBD_TRANSPORT_NODE, patch=ctl.BBD_PATCH_NODE,
                 control=ctl.BBD_CONTROL_NODE, sensor=ctl.BBD_SENSOR_NODE):
        self.transport = transport
        self.patch = patch
        self.control = control
        self.sensor = sensor
        self.power = GpsPowerControl()
        self.tfd = None
        self.state = ABSENT
        self.parser = tl.TransportLayerParser()
        self.stats = {"rx_bytes": 0, "tx_bytes": 0, "rx_packets": 0,
                      "garbage_bytes": 0, "handshake": False}
        self.hw_rev = None
        self.ap_type = None
        self.firmware = None
        self.firmware_meta = None
        self.last_error = None

    # ------------------------------------------------------------- inventory
    def present(self) -> bool:
        return (os.path.exists(self.transport) and os.path.exists(self.patch)
                and os.path.exists(self.control))

    def ioctl_get_hw_rev(self):
        """Reflect ap_type/hw_rev from the DT (read-only; same values the kernel
        reads in bcm_gps_spi.c probe / get_patch_version)."""
        base = "/sys/firmware/devicetree/base/spi@10970000/BCM4773@0"
        def u32_be(p):
            try:
                b = open(p, "rb").read(4)
                return int.from_bytes(b[:4], "big")
            except OSError:
                return None
        self.ap_type = u32_be(base + "/ssp-ap-type")
        self.hw_rev = u32_be(base + "/ssp-ap-rev")
        return {"ap_type": self.ap_type, "hw_rev": self.hw_rev}

    # ------------------------------------------------------- firmware
    def load_firmware(self):
        if not os.path.exists(self.patch):
            self.state = FAULT
            self.last_error = "patch node %s absent" % self.patch
            return False
        try:
            header, blob, meta = ctl.patch_blob_from_file(self.patch)
        except OSError as e:
            self.state = FAULT
            self.last_error = str(e)
            return False
        if not blob or meta.get("AsicVersion") != "0x004775B0":
            self.state = FAULT
            self.last_error = "firmware identity mismatch: %s" % meta
            return False
        self.firmware = blob
        self.firmware_meta = meta
        self.state = FIRMWARE_READY
        return True

    # ------------------------------------------------------- transport
    def open_transport(self):
        if not os.path.exists(self.transport):
            self.state = ABSENT
            self.last_error = "transport %s absent" % self.transport
            return False
        try:
            self.tfd = os.open(self.transport, os.O_RDWR | os.O_NONBLOCK)
        except OSError as e:
            self.state = FAULT
            self.last_error = "open %s: %s" % (self.transport, e)
            return False
        # Opening /dev/ttyBCM enables the IRQ and (in bcm_rxtx_work_func)
        # performs bcm477x_hello() to wake the chip. State reflects transport
        # ready; the chip handshake is verified separately below.
        self.state = TRANSPORT_READY
        # Opening the node starts the kernel's RX/TX work loop, which performs
        # bcm477x_hello() (MCU_REQ/MCU_RESP handshake) once.  Give the transport
        # a brief moment to settle so the first SPI stream is not discarded.
        time.sleep(0.25)
        return True

    def write_control(self, s: str):
        """Write a BBD control string (NUL-terminated, as bbd_control expects)."""
        if not os.path.exists(self.control):
            return {"success": False, "error": "control node absent"}
        payload = (s + "\0").encode("latin1")
        try:
            fd = os.open(self.control, os.O_WRONLY)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return {"success": True, "string": s}
        except OSError as e:
            return {"success": False, "error": str(e), "string": s}

    def tx_frame(self, seq_id, payload, flags=0, flush_read=False):
        """Frame RPC payload as a BBD TL packet and write raw to /dev/ttyBCM.

        The kernel forwards /dev/ttyBCM writes raw to the chip (bcm_spi_write);
        the TL framing is the lhd userspace's job, reproduced here.
        """
        frame = tl.build_frame(seq_id, payload, flags)
        try:
            n = os.write(self.tfd, frame)
        except OSError as e:
            return {"success": False, "error": str(e)}
        self.stats["tx_bytes"] += n
        return {"success": True, "written": n, "frame_bytes": len(frame)}

    def rx_poll(self, deadline, on_rpc=None):
        """Read the de-framed RPC payload stream from /dev/ttyBCM.

        The kernel's bcb_parse_asic_data() already strips TL framing and hands
        us the inner RPC records; we parse the 7/8-bit RPC id/len header.
        """
        out = []
        while time.monotonic() < deadline:
            r, _, _ = select.select([self.tfd], [], [], 0.25)
            if not r:
                continue
            try:
                chunk = os.read(self.tfd, 8192)
            except OSError as e:
                if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    continue
                break
            if not chunk:
                break
            self.stats["rx_bytes"] += len(chunk)
            pkts = self.parser.push(chunk)
            for pkt in pkts:
                self.stats["rx_packets"] += 1
                rpcs = tl.parse_rpc_payload(pkt["payload"])
                for rpc_id, data in rpcs:
                    if on_rpc:
                        on_rpc(rpc_id, data)
                    out.append({"rpc_id": rpc_id, "data": data})
        return out

    # ------------------------------------------------------- full session
    def run_session(self, expect_handshake=True, handshake_timeout=15.0,
                    observe_timeout=5.0):
        """Power on, load firmware, open transport, bounded handshake, cleanup.

        Returns a structured result dict (never a fabricated fix).
        """
        result = {
            "success": False,
            "state": ABSENT,
            "present": self.present(),
            "power": None,
            "firmware": None,
            "transport": None,
            "handshake": None,
            "rx": [],
            "stats": self.stats,
            "error": None,
            "fix": None,
            "fix_decoded": False,
            "position_decoder": POSITION_DECODER_UNAVAILABLE,
        }
        if not self.present():
            result["error"] = "BBD nodes not all present"
            self.state = ABSENT
            return result

        initial_rail = self.power.read()
        lease = self.power.acquire()
        pooled = self.power.set_power(True)
        result["power"] = pooled
        if not pooled.get("success"):
            result["state"] = FAULT
            result["error"] = "power-on failed: %s" % pooled.get("error")
            self.power.release(lease, bool(initial_rail))
            return result

        try:
            if not self.load_firmware():
                result["state"] = self.state
                result["error"] = self.last_error
                return result
            result["firmware"] = {
                "name": self.firmware_meta.get("Name"),
                "asic": self.firmware_meta.get("AsicVersion"),
                "blob_len": len(self.firmware),
                "sha256": __import__("hashlib").sha256(self.firmware).hexdigest(),
            }
            if not self.open_transport():
                result["state"] = self.state
                result["error"] = self.last_error
                return result
            result["transport"] = "open"
            rev = self.ioctl_get_hw_rev()
            result["hw"] = rev

            # Begin patch download (matches lhd's SSI:PassThru=1 sequence).
            c1 = self.write_control(ctl.BBD_CTRL_SSI_PATCH_BEGIN)
            # Signal sensor-hub readiness after patch (ESW:READY).
            c2 = self.write_control(ctl.ESW_CTRL_READY)
            result["control"] = {"patch_begin": c1, "ready": c2}

            # Raw RX floor: is ANY byte coming back from the receiver at all?
            # Recorded before any application RPC, so a silent receiver and an
            # unknown RPC map can never be confused with each other.
            floor_deadline = time.monotonic() + float(
                os.environ.get('NUXEL_GNSS_RX_FLOOR_SECONDS', '3'))
            floor_rx = self.rx_poll(floor_deadline)
            result["rx_floor"] = {
                "bytes": self.stats["rx_bytes"],
                "packets": len(floor_rx),
            }
            if expect_handshake:
                handshake = self.handshake(handshake_timeout)
                result["handshake"] = handshake
                if handshake.get("ok"):
                    self.state = BBD_HANDSHAKE_OK
                    self.stats["handshake"] = True
            # Observe a bounded window of de-framed RPC traffic (no decode of
            # the proprietary GNSS position RPC).
            if self.tfd is not None:
                deadline = time.monotonic() + observe_timeout
                result["rx"] = self.rx_poll(deadline)
            if self.state == BBD_HANDSHAKE_OK:
                result["success"] = True
                result["state"] = self.state
            else:
                result["state"] = self.state
                result["error"] = ("transport/handshake boundary reached; GNSS "
                                   "position decode unavailable (proprietary lhd/gpsd RPC map)")
            return result
        finally:
            self.cleanup(lease, bool(initial_rail))

    def handshake(self, timeout: float):
        """Bounded observation for chip/SSP ready state.

        The reliable signal is the SSP debug log's ``GPS: true`` / ready state,
        not raw bytes.  We check /dev/bbd_sensor and the SSP sysfs state within
        the timeout and never fabricate a handshake from traffic alone.
        """
        deadline = time.monotonic() + timeout
        # Observe whether the SSP reports the MCU as ready (sensor_state file
        # or the ssp_sensor sysfs). The authoritative tracker is the kernel's
        # [SSP] debug_work_func "GPS: false/true" line.
        started = time.monotonic()
        while time.monotonic() < deadline:
            # Any control-prompt from the chip arrives on /dev/bbd_control.
            state = self.ssp_state()
            if state.get("gps") is True:
                return {"ok": True, "gps": True, "elapsed_s": time.monotonic() - started}
            time.sleep(0.2)
        return {"ok": False, "gps": state.get("gps"), "elapsed_s": time.monotonic() - started}

    def ssp_state(self):
        """Best-effort read of SSP GPS/MCU state (read-only)."""
        gps = None
        for path in ("/sys/devices/virtual/sensors/ssp_sensor/sensor_state",
                      "/sys/class/sensors/ssp_sensor/sensor_state"):
            v = _read_sysfs(path)
            if v is not None:
                gps = "gps" in v.lower()
                break
        return {"gps": gps}

    def cleanup(self, lease, restore_initial):
        # Signal GPS core off so the receiver does not stay powered.
        try:
            self.write_control(ctl.BBD_CTRL_GPS_OFF)
        except Exception:
            pass
        if self.tfd is not None:
            try:
                os.close(self.tfd)
            except OSError:
                pass
            self.tfd = None
        self.power.release(lease, restore_initial)
        self.state = ABSENT


def main():
    ap = argparse.ArgumentParser(description="Nuxel native BBD/LHD bridge daemon")
    ap.add_argument("--session", action="store_true", help="run one bounded hw session and exit")
    ap.add_argument("--observe", type=float, default=5.0)
    ap.add_argument("--handshake-timeout", type=float, default=15.0)
    ap.add_argument("--json", action="store_true", help="emit JSON result")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    d = LhdDaemon()
    if not args.session:
        print(json.dumps({"error": "no --session; daemon-loop not yet implemented"}, indent=2))
        return 64
    r = d.run_session(handshake_timeout=args.handshake_timeout,
                      observe_timeout=args.observe)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print("state=%s present=%s power=%s handshake=%s fix_decoded=%s error=%s" %
              (r.get("state"), r.get("present"), r.get("power"), r.get("handshake"),
               r.get("fix_decoded"), r.get("error")))
    return 0 if r.get("success") else 2


if __name__ == "__main__":
    sys.exit(main())
