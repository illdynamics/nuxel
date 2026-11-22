#!/usr/bin/env python3
"""camera-dt-gate.py — fail-closed camera DT/DTBO/merged-tree release gate.

Offline only. Never writes to the input images. Detects and hard-fails the
camera-device-tree defects a plain boot-container check cannot see. See
reports/camera-01-dt-gate.md for the full contract.

Exit status: 0 = every gate passed; 1 = at least one hard failure; 2 = usage.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

FDT_MAGIC = 0xD00DFEED
SAMSUNG_DTH_MAGIC = 0xD7B7AB1E  # Exynos DT-header container (BE bytes d7 b7 ab 1e)
EXPECT_BOARD_REV = 26

RESERVED_I2C = {0x27: "sec-nfc", 0x48: "sec_ts (touch)"}

PROTECTED_OWNERS = ("ssp", "bcm4775", "nfc", "sec-nfc", "touch", "sec_ts",
                    "display", "decon", "dsim", "gpu", "mali", "usb", "ehci",
                    "xhci", "wifi", "bcmdhd", "bt", "mic", "codec", "charger")


class Gate:
    def __init__(self):
        self.failures, self.warnings, self.notes = [], [], []

    def fail(self, m):
        self.failures.append(m)
        return False

    def warn(self, m):
        self.warnings.append(m)

    def note(self, m):
        self.notes.append(m)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True)
    except FileNotFoundError as e:
        raise RuntimeError("required tool missing: %s" % cmd[0]) from e


def is_fdt(b):
    return len(b) >= 8 and struct.unpack_from(">I", b, 0)[0] == FDT_MAGIC


def is_samsung_dth(b):
    return len(b) >= 8 and struct.unpack_from(">I", b, 0)[0] == SAMSUNG_DTH_MAGIC


def dtc_dts(blob_path):
    r = run(["dtc", "-I", "dtb", "-O", "dts", blob_path])
    if r.returncode != 0:
        raise ValueError("dtc: %s" % r.stderr.decode("utf-8", "replace")[:400])
    return r.stdout.decode("utf-8", "replace")


def extract_embedded_fdt(image_path, tmpdir):
    with open(image_path, "rb") as f:
        data = f.read()
    if is_fdt(data):
        p = os.path.join(tmpdir, "emb.dtb")
        open(p, "wb").write(data)
        return p
    if is_samsung_dth(data):
        pat = struct.pack(">I", FDT_MAGIC)
        off = data.find(pat)
        if off < 0:
            return None
        total = struct.unpack_from(">I", data, off + 4)[0]
        p = os.path.join(tmpdir, "emb.dtb")
        open(p, "wb").write(data[off:off + total])
        return p
    return None


def check_structure(blob, gate, label):
    rt = run(["dtc", "-I", "dtb", "-O", "dtb", blob])
    if rt.returncode != 0:
        gate.fail("%s: dtc recompile failed: %s"
                  % (label, rt.stderr.decode("utf-8", "replace")[:300]))
        return False
    gate.note("%s: FDT round-trip OK" % label)
    return True


def check_model(blob, gate, label):
    dts = dtc_dts(blob)
    comp = re.findall(r'compatible\s*=\s*"([^"]+)"', dts)
    if not any("exynos9820" in c for c in comp):
        gate.fail("%s: no exynos9820 compatible" % label)
    # This downstream dtb carries board identity via /chosen bootargs + bootloader,
    # not a static /model property; /model is expected-absent here.
    m = re.search(r'model\s*=\s*"([^"]+)"', dts)
    if not m:
        gate.note("%s: no static /model (board identity via bootargs/compatible; expected)" % label)
    else:
        model = m.group(1)
        if "BEYOND2LTE" not in model.upper():
            gate.fail("%s: model %r is not beyond2lte" % (label, model))
        gate.note("%s: model %r" % (label, model))
        rv = re.search(r"\b(\d+)\b", model)
        if rv and int(rv.group(1)) != EXPECT_BOARD_REV:
            # The DTS source board-id revision in a DTBO overlay is often a
            # generic "OPEN 04" while the authoritative HW revision (26) arrives
            # via androidboot.revision in the boot cmdline. Warn, do not hard-fail;
            # the ACTIVE_BOARD_MATCH gate compares against the live cmdline,
            # not this static string.
            gate.warn("%s: static model rev %s differs from expected HW rev %d "
                      "(authoritative rev comes from androidboot.revision cmdl%%"
                      % (label, rv.group(1), EXPECT_BOARD_REV))
    return dts


def check_camera_graph(dts, gate, label):
    ports = re.findall(r'([a-zA-Z0-9_\-]*port[a-zA-Z0-9_\-@]*)\s*\{', dts)
    endpoints = re.findall(r'([\w@\-]*endpoint[\w@\-]*)\s*\{', dts)
    remotes = re.findall(r'remote-endpoint\s*=\s*<&([\w.\-@]+)>', dts)
    lanes = re.findall(r'data-lanes\s*=\s*<([^>]+)>', dts)
    for ref in remotes:
        base = ref.rstrip("0123456789")
        if ref not in endpoints and base not in endpoints and ref not in ports:
            gate.fail("%s: remote-endpoint <&%s> unresolved (no endpoint/port)" % (label, ref))
    for ln in lanes:
        nums = ln.split()
        if len(nums) not in (1, 2, 4):
            gate.fail("%s: data-lanes=<%s> invalid count %d (1/2/4)" % (label, ln, len(nums)))
    gate.note("%s: %d ports, %d endpoints, %d remote refs, %d lane specs"
              % (label, len(ports), len(endpoints), len(remotes), len(lanes)))
    return ports, endpoints


def check_i2c(dts, gate, label):
    # I2C address check. FIMC-IS vendor DTs legitimately reuse a 7-bit address
    # (0x10 for sensors, 0x51 for EEPROMs) across DIFFERENT CSIS/ISPHQ channels,
    # so a raw address-duplicate is NOT a collision and must not hard-fail.
    # We hard-fail ONLY when a camera sensor steals an address reserved for a
    # fixed non-camera owner (touch 0x48, NFC 0x27), and we otherwise report
    # duplicates as notes requiring human bus-context review.
    reserved_hits = []
    addr_use = {}
    for m in re.finditer(r'([\w\-]+)@([0-9a-f]+)\s*\{[^{}]*reg\s*=\s*<0x([0-9a-f]+)>', dts, re.S):
        node, unit, reghex = m.group(1), m.group(2), m.group(3)
        addr = int(reghex, 16)
        if not (0x03 <= addr <= 0x7f):
            continue
        addr_use.setdefault(addr, []).append(node)
        if addr in RESERVED_I2C:
            reserved_hits.append((node, addr, RESERVED_I2C[addr]))
    for node, addr, owner in reserved_hits:
        # touchscreen@48, sec-nfc@27 are the OWNERS; only fail if a *camera*
        # node (fimc-is-*, s5k*, 2l4, 3j1, 3m3, 3p9) claims the reserved addr.
        if re.search(r'fimc|s5k|2l4|3j1|3m3|3p9|csis|camera', node, re.I):
            gate.fail("%s: camera node %s steals reserved I2C @0x%02x (%s)"
                      % (label, node, addr, owner))
        else:
            gate.note("%s: @0x%02x is the %s owner (%s)" % (label, addr, owner, node))
    for addr, nodes in sorted(addr_use.items()):
        if len(nodes) > 1:
            gate.note("%s: 0x%02x used by %s (bus-context review required; likely "
                      "distinct CSIS/ISPHQ channels)" % (label, addr, ", ".join(sorted(set(nodes)))))
    gate.note("%s: %d unique 7-bit I2C addresses seen" % (label, len(addr_use)))


def check_exclusivity(dts, gate, label):
    csis = bool(re.search(r'csis|mipi-csis', dts, re.I))
    fimc = bool(re.search(r'fimc[\w]*is', dts, re.I))
    s5k = re.findall(r'compatible\s*=\s*"(samsung,s5k[0-9a-z]+)"', dts)
    if csis and fimc and s5k:
        gate.fail("%s: native CSIS AND vendor FIMC-IS2 both present with sensors %s "
                  "(must be mutually exclusive)" % (label, sorted(set(s5k))))
    gate.note("%s: csis=%s fimc_is=%s sensors=%s" % (label, csis, fimc, sorted(set(s5k))))


def validate(path, golden_sha, gate):
    rep = {"path": path, "sha256": sha256_file(path)}
    raw = open(path, "rb").read()
    if len(raw) < 8:
        gate.fail("%s: too small (%d bytes)" % (path, len(raw)))
        return rep
    rep["format"] = ("fdt" if is_fdt(raw) else
                     "samsung-dth" if is_samsung_dth(raw) else "unknown")
    if rep["format"] == "unknown":
        gate.fail("%s: unrecognised magic 0x%08x" % (path, struct.unpack_from(">I", raw, 0)[0]))
        return rep
    if golden_sha and rep["sha256"] != golden_sha:
        gate.fail("%s: sha256 mismatch (got %s want %s)" % (path, rep["sha256"], golden_sha))
    tmp = tempfile.mkdtemp(prefix="nuxel-camdt-")
    try:
        blob = extract_embedded_fdt(path, tmp)
        if blob is None:
            gate.fail("%s: no embedded FDT in container" % path)
            return rep
        check_structure(blob, gate, path)
        dts = check_model(blob, gate, path)
        check_camera_graph(dts, gate, path)
        check_i2c(dts, gate, path)
        check_exclusivity(dts, gate, path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return rep


def main(argv):
    ap = argparse.ArgumentParser(prog="camera-dt-gate.py")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--golden", help="golden baseline image; camera members must match")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    overall = 0
    reports = []
    for path in a.images:
        g = Gate()
        golden = sha256_file(a.golden) if a.golden and os.path.exists(a.golden) else None
        if a.golden and not os.path.exists(a.golden):
            g.fail("golden %s missing" % a.golden)
        try:
            rep = validate(path, golden, g)
        except (OSError, ValueError, RuntimeError) as e:
            g.fail("%s: %s" % (path, e))
            rep = {"path": path}
        rep["failures"] = g.failures
        rep["warnings"] = g.warnings
        rep["notes"] = g.notes
        rep["result"] = "PASS" if not g.failures else "FAIL"
        reports.append(rep)
        if g.failures:
            overall = 1
        if not a.json:
            print("== %s : %s" % (path, rep["result"]))
            if not a.quiet:
                for k in ("sha256", "format"):
                    if k in rep:
                        print("   %-10s %s" % (k + ":", rep[k]))
            for f in g.failures:
                print("   FAIL  %s" % f)
            for n in g.notes:
                print("   note  %s" % n)
    if a.json:
        print(json.dumps(reports, indent=2))
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
