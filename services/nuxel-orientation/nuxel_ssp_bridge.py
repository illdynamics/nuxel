#!/usr/bin/env python3
"""Nuxel native BBD/SSP sensor-hub bridge (no Android/Bionic runtime).

The S10+ sensor hub (BCM47752KUB1G, DT compatible ``ssp,BCM4773``) is driven by
the kernel's BBD transport: the SSP state machine builds ``[u16 len][ssp_msg]``
frames, ``/dev/ttyBCM`` carries them over SSI, and the kernel's own BBD/RPC
decode (bbdpl/bbd_rpc_lh.c) turns the hub's replies back into frames.

Why this process exists
-----------------------
The kernel only diverts/decodes hub data while a *peer* holds
``/dev/bbd_sensor`` (that is the contract ``bbd_nuxel_peer_open()`` implements,
and in peer mode ``bcm_on_packet_received()`` runs the RPC decode itself).
This process is that peer.  It does **not** translate bytes itself any more:
an earlier version wrote raw ``ssp_msg`` bytes into ``/dev/ttyBCM``, which
bypassed the SSI framing (2-byte length, status, flow control) the hub
requires, so the hub could never answer chip-ID.  The SSI link is the kernel's
job; this bridge's job is to own the peer contract, request bring-up/stream,
and report the kernel's real state truthfully.

It never synthesises sensor samples.  Everything published in
``/sys/class/sensors/*`` comes from the hub; this process only asks the kernel
to bring the hub up and start the accel+gyro stream, then watches the result.

If any device is missing or the kernel is not the PWNAGE-SSP kernel, it exits
non-zero; systemd then leaves orientation Auto truthfully unavailable.
"""

from __future__ import annotations

import argparse
import errno
import os
import signal
import sys
import threading
import time

BBD_SENSOR = "/dev/bbd_sensor"
BBD_CONTROL = "/dev/bbd_control"
TTY_BCM = "/dev/ttyBCM"
SSP_DIAG = "/sys/class/sensors/ssp_sensor/nuxel_hub_diag"
SSP_BRINGUP = "/sys/class/sensors/ssp_sensor/nuxel_bringup"
SSP_STREAM = "/sys/class/sensors/ssp_sensor/nuxel_stream"
SSP_STATE = "/sys/class/sensors/ssp_sensor/sensor_state"
SSP_HUB_DIAG = "/sys/class/sensors/ssp_sensor/nuxel_hub_diag"
SSP_ENABLE = "/sys/class/sensors/ssp_sensor/enable"
ACCEL_RAW = "/sys/class/sensors/accelerometer_sensor/raw_data"
GYRO_RAW = "/sys/class/sensors/gyro_sensor/raw_data"
PHASE_PATH = "/run/nuxel-ssp-bridge/phase"

LOG_PATH = os.environ.get("NUXEL_SSP_BRIDGE_LOG", "")


def log(msg):
    line = "nuxel-ssp-bridge: %s\n" % msg
    sys.stderr.write(line)
    sys.stderr.flush()
    # Nuxel's login shell banner can claim fd 2 on some boots; keep a file
    # copy so diagnostics are always retrievable.
    if LOG_PATH:
        try:
            with open(LOG_PATH, "a") as fh:
                fh.write(line)
        except OSError:
            pass


def read_text(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def write_text(path, value):
    with open(path, "w") as f:
        f.write(str(value))
        f.flush()


def write_phase(phase, detail=""):
    try:
        os.makedirs(os.path.dirname(PHASE_PATH), exist_ok=True)
        with open(PHASE_PATH, "w") as f:
            f.write("%s %s\n" % (phase, detail))
    except OSError:
        pass


def _streaming():
    """True once the hub actually delivers non-zero accel/gyro samples."""
    accel = read_text(ACCEL_RAW)
    gyro = read_text(GYRO_RAW)
    try:
        a = [int(v) for v in accel.split(",")]
        g = [int(v) for v in gyro.split(",")]
    except ValueError:
        return False
    return any(a) or any(g)


class Bridge:
    def __init__(self, args):
        self.args = args
        self.sensor_fd = None
        self.tty_fd = None
        self.stopping = False

    # -- bring-up -----------------------------------------------------------
    def bring_up(self):
        """Ask the kernel to run its own documented hub bring-up.

        The peer contract (open of /dev/bbd_sensor) is already active; the
        kernel drives SSI and decodes the replies itself.  Nothing here claims
        the hub is alive: ``initialize_mcu`` still has to get a real chip-ID
        answer and ``nuxel_stream`` still has to be accepted.
        """
        if not os.path.exists(SSP_BRINGUP):
            log("kernel has no %s (pre-PWNAGE-SSP image?); falling back to "
                "ESW:READY" % SSP_BRINGUP)
            try:
                with open(BBD_CONTROL, "w") as f:
                    f.write("ESW:READY")
            except OSError as exc:
                log("ESW:READY failed: %s" % exc)
                return False
            return True
        try:
            write_text(SSP_BRINGUP, 1)
            log("hub bring-up accepted by kernel (initialize_mcu returned OK)")
        except OSError as exc:
            # The kernel returns -EIO when initialize_mcu() failed.  That is
            # the truthful answer; report it and let diagnostics explain it.
            log("hub bring-up failed: %s (%s)" % (exc, read_text(SSP_HUB_DIAG)))
            return False
        return self.start_stream()

    def start_stream(self):
        """Ask the kernel to add accelerometer+gyroscope after bring-up."""
        if not os.path.exists(SSP_STREAM):
            log("kernel has no %s (pre-stream kernel); relying on enable writes"
                % SSP_STREAM)
            return True
        try:
            write_text(SSP_STREAM, 1)
        except OSError as exc:
            log("stream start failed: %s (hub: %s)"
                % (exc, read_text(SSP_HUB_DIAG)))
            return False
        log("kernel started accel+gyro stream")
        return True

    def dump_state(self, label):
        log("-- %s --" % label)
        log("mcu_name=%s mcu_rev=%s" % (
            read_text("/sys/class/sensors/ssp_sensor/mcu_name"),
            read_text("/sys/class/sensors/ssp_sensor/mcu_rev")))
        log("hub=%s" % read_text(SSP_HUB_DIAG).strip())
        log("sensor_state=%s enable=%s accel=%s gyro=%s" % (
            read_text(SSP_STATE), read_text(SSP_ENABLE),
            read_text(ACCEL_RAW), read_text(GYRO_RAW)))

    # -- transport ----------------------------------------------------------
    def open_devices(self):
        # Opening /dev/bbd_sensor is what makes the kernel treat this process
        # as the BBD peer: AP->MCU frames are queued here for diagnostics and
        # the ttyBCM receive path runs the RPC decode into the SSP machine.
        self.sensor_fd = os.open(BBD_SENSOR, os.O_RDWR | os.O_NONBLOCK)
        # ttyBCM is kept open so the kernel's bcm_spi session (SSI framing,
        # host_req IRQ arming, flow-control state) stays established between
        # bring-up requests.  This process does not move bytes on it.
        try:
            self.tty_fd = os.open(TTY_BCM, os.O_RDWR | os.O_NONBLOCK)
        except OSError as exc:
            log("cannot open %s: %s" % (TTY_BCM, exc))
            raise

    def close_devices(self):
        for name in ("tty_fd", "sensor_fd"):
            fd = getattr(self, name)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, name, None)

    def _enospc(self, exc):
        return isinstance(exc, OSError) and exc.errno == errno.ENOSPC

    def run(self):
        if not os.access(BBD_SENSOR, os.R_OK) or not os.access(TTY_BCM, os.R_OK):
            log("missing device node(s): %s %s" % (BBD_SENSOR, TTY_BCM))
            return 2
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)
        write_phase("opening")
        try:
            self.open_devices()
        except OSError as exc:
            if self._enospc(exc):
                log("bbd_sensor busy (another SSP client holds it): %s" % exc)
            else:
                log("open failed: %s" % exc)
            return 2

        write_phase("bringup")
        # Keep the peer contract alive while bring-up runs in kernel context.
        result = {}

        def _bringup():
            try:
                result["ok"] = self.bring_up()
            except Exception as exc:  # never lose the peer on a bad bring-up
                result["ok"] = False
                log("bring-up raised: %s" % exc)

        worker = threading.Thread(target=_bringup, name="ssp-bringup", daemon=True)
        worker.start()

        last_state = time.monotonic()
        blocked_logged = False
        while not self.stopping:
            # Drain AP->MCU frames the kernel queues for this peer so its ring
            # cannot fill and stall the SSP state machine.  These are the same
            # frames the kernel already sent over SSI; reading them is purely
            # bookkeeping, never a resend.
            try:
                while True:
                    chunk = os.read(self.sensor_fd, 4096)
                    if not chunk:
                        break
                    if self.args.verbose:
                        log("peer frame %d bytes %s" % (len(chunk), chunk[:16].hex()))
            except BlockingIOError:
                pass
            except OSError as exc:
                log("transport error: %s" % exc)
                self.close_devices()
                time.sleep(1.0)
                try:
                    self.open_devices()
                except OSError as exc2:
                    log("reopen failed: %s" % exc2)
                    write_phase("blocked", str(exc2))
                    return 3

            if (not worker.is_alive() and "reported" not in result and
                    "ok" in result):
                result["reported"] = True
                self.dump_state("after bring-up (%s)" %
                                ("ok" if result["ok"] else "failed"))
                if result["ok"]:
                    write_phase("relay")
                else:
                    write_phase("blocked", "bring-up failed")
                    blocked_logged = True

            if time.monotonic() - last_state > 30.0:
                last_state = time.monotonic()
                if result.get("ok") and not _streaming():
                    self.dump_state("periodic (bring-up ok, no samples yet)")
                elif not result.get("ok") and not blocked_logged:
                    self.dump_state("periodic (bring-up failed)")
                    blocked_logged = True
                elif self.args.verbose:
                    self.dump_state("periodic")
            time.sleep(0.05)

        self.close_devices()
        write_phase("stopped")
        return 0

    def _stop(self, signum, frame):
        self.stopping = True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="check the kernel ABI export exists, then exit")
    args = ap.parse_args(argv)
    if args.selftest:
        ok = (os.path.exists(SSP_BRINGUP) and os.path.exists(SSP_DIAG)
              and os.path.exists(BBD_SENSOR))
        print("PASS ssp bridge ABI" if ok else
              "FAIL ssp bridge ABI (kernel patch missing?)")
        return 0 if ok else 1
    return Bridge(args).run()


if __name__ == "__main__":
    sys.exit(main())
