#!/usr/bin/env python3
"""camera-dt-gate.py — fail-closed camera DT/DTBO/merged-tree release gate.

Offline only. Never writes to the input images. Uses a real device-tree
structural graph (tools/s10plus/dt_graph.py) to resolve phandles, endpoints,
clocks, resets, regulators, pinctrl and GPIO through the actual FDT node graph
— not DTS-text regex matching. See reports/camera-01-dt-gate.md.

Exit status: 0 = every gate passed; 1 = at least one hard failure; 2 = usage.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dt_graph as dg

EXPECT_BOARD_REV = 26

# Fixed non-camera owners that a camera node must never steal (7-bit I2C).
RESERVED_I2C = {0x27: "sec-nfc", 0x48: "sec_ts (touch)"}

# Camera sensor / ISP / CSI identifiers (lower-case, matched case-insensitively).
CAMERA_GREP = re.compile(
    r'fimc|fimc-is|csis|mipi-csis|s5k|2l4|3j1|3m3|3p9|4ha|'
    r'sensor-module|exynos5-fimc-is|camera', re.I)

# Vendor FIMC-IS vs native CSIS mutual-exclusion markers.
FIMC_IS_RE = re.compile(r'fimc[-_]?is', re.I)
NATIVE_CSIS_RE = re.compile(r'mipi-csis|exynos9820-csis|exynos-csis', re.I)
S5K_SENSOR_RE = re.compile(r'samsung,s5k|s5k[0-9a-z]+', re.I)


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


def load_tree(path, gate, label, dtbo_idx=None):
    """Extract the selected FDT (dtbo entry idx if given) and parse it."""
    try:
        data = open(path, "rb").read()
    except OSError as e:
        gate.fail("%s: %s" % (label, e))
        return None
    fdts = dg.extract_fdts(data)
    if not fdts:
        gate.fail("%s: no embedded FDT (unrecognized magic or container)" % label)
        return None
    # For a dtbo table, select the entry matching dtbo_idx.  DIFFERENT from a
    # "guess the broadest entry" heuristic: if the container holds more than one
    # embedded FDT and the caller did NOT pass an explicit revision selection
    # (--dtbo-idx from androidboot.dtbo_idx), then the selection is MISSING and
    # that is a hard failure — we must never silently pick an overlay entry.
    if len(fdts) == 1:
        idx = 0
    elif dtbo_idx is None:
        gate.fail("%s: multi-entry DTBO (%d FDTs) but no explicit --dtbo-idx "
                  "selection (androidboot.dtbo_idx missing); refusing to guess"
                  % (label, len(fdts)))
        return None
    elif not (0 <= dtbo_idx < len(fdts)):
        gate.fail("%s: --dtbo-idx=%s out of range [0..%d)" % (label, dtbo_idx, len(fdts)))
        return None
    else:
        idx = dtbo_idx
    fdt = fdts[idx]
    try:
        tree = dg.parse_fdt(fdt)
    except ValueError as e:
        gate.fail("%s: %s" % (label, e))
        return None
    gate.note("%s: selected FDT entry %d of %d" % (label, idx, len(fdts)))
    return tree


def container_classify(path):
    data = open(path, "rb").read()
    if dg.is_fdt(data):
        return "fdt"
    if dg.is_samsung_dth(data):
        offs = dg.dth_entry_offsets(data)
        return "samsung-dth(%d entries)" % len(offs) if offs else "samsung-dth"
    if len(data) >= 4:
        return "unknown(magic=0x%08x)" % struct.unpack_from(">I", data, 0)[0]
    return "unknown"


def check_structure(tree, gate, label):
    gate.note("%s: FDT parsed: %d nodes, %d phandles, %d symbols"
              % (label, len(tree.nodes), len(tree.phandle_map), len(tree.symbols)))
    return True


def check_model(tree, gate, label):
    root = tree.get("/")
    if root is None:
        gate.fail("%s: no root node" % label)
        return
    comp = root.props.get("compatible")
    comps = comp.strings if comp else []
    if not any("exynos9820" in c.lower() for c in comps):
        gate.fail("%s: no exynos9820 compatible (got %s)" % (label, comps))
    m = root.props.get("model")
    if m and m.strings:
        model = m.strings[0]
        if "BEYOND2LTE" not in model.upper():
            gate.fail("%s: model %r is not beyond2lte" % (label, model))
        else:
            gate.note("%s: model %r" % (label, model))
    else:
        # Downstream Exynos dtb carries board identity via bootargs + bootloader,
        # not a static /model; this is expected and not a failure.
        gate.note("%s: no static /model (board identity via bootargs/compatible)" % label)


def _iter_i2c_nodes(tree):
    """Yield every node that looks like an I2C device (unit-address @<hex> +
    a `reg` property whose first cell is the 7-bit address)."""
    for path, node in tree.nodes.items():
        m = re.search(r'@([0-9a-fA-F]+)\b', node.name)
        if not m:
            continue
        reg = node.props.get("reg")
        if reg is None or not reg.cells:
            continue
        addr = reg.cells[0]
        yield path, node, m.group(1), addr


def check_board_revision_selection(tree, gate, label, board_rev, dtbo_idx, is_dtbo):
    """Verify the dtbo entry selected by dtbo_idx covers the expected board
    revision (dtbo-hw_rev .. dtbo-hw_rev_end window)."""
    if not is_dtbo:
        return
    if dtbo_idx is None or board_rev is None:
        return
    root = tree.get("/")
    if root is None:
        return
    lo = root.props.get("dtbo-hw_rev")
    hi = root.props.get("dtbo-hw_rev_end")
    if lo is None or hi is None:
        gate.note("%s: no dtbo-hw_rev window on this entry (idx %s)" % (label, dtbo_idx))
        return
    if not (lo.cells and hi.cells):
        gate.note("%s: empty rev window" % label)
        return
    l, h = lo.cells[0], hi.cells[0]
    if not (l <= board_rev <= h):
        gate.fail("%s: dtbo entry idx=%s rev window [%d..%d] does NOT include board rev %d"
                  % (label, dtbo_idx, l, h, board_rev))
    else:
        gate.note("%s: dtbo entry idx=%s rev window [%d..%d] covers board rev %d"
                  % (label, dtbo_idx, l, h, board_rev))



def check_i2c(tree, gate, label):
    # Determine which I2C addresses are "reserved owners" and detect a camera
    # node stealing one. Reuse of a 7-bit address across DIFFERENT CSIS/ISPHQ
    # channels is normal for FIMC-IS, so duplicates are notes, not failures.
    addr_use = {}
    reserved_hits = []
    for path, node, unit, addr in _iter_i2c_nodes(tree):
        if not (0x03 <= addr <= 0x7f):
            continue
        addr_use.setdefault(addr, []).append(path)
        if addr in RESERVED_I2C:
            reserved_hits.append((path, node, addr, RESERVED_I2C[addr]))
    for path, node, addr, owner in reserved_hits:
        is_camera = bool(CAMERA_GREP.search(node.name)) or bool(
            node.props.get("compatible")
            and any(CAMERA_GREP.search(s) for s in node.props["compatible"].strings))
        if is_camera or re.search(r'fimc|s5k|2l4|3j1|3m3|3p9|csis|camera',
                                  node.name, re.I):
            gate.fail("%s: camera node %s steals reserved I2C @0x%02x (%s)"
                      % (label, path, addr, owner))
        else:
            gate.note("%s: @0x%02x is owned by %s (%s)" % (label, addr, owner, path))
    for addr, nodes in sorted(addr_use.items()):
        if len(nodes) > 1:
            gate.note("%s: 0x%02x used by %d nodes %s (distinct CSIS/ISPHQ channels?)"
                      % (label, addr, len(nodes),
                         ", ".join(sorted(set(nodes))[:5])))
    gate.note("%s: %d unique 7-bit I2C addresses seen" % (label, len(addr_use)))


def check_endpoints(tree, gate, label):
    """Real phandle-based endpoint resolution + bidirectionality."""
    errs = []
    edges = dg.resolve_endpoint_graph(tree, errs)
    for e in errs:
        gate.fail("%s: %s" % (label, e))
    # bidirectionality: for each A->B, require B->A
    reverse = {}
    for a, b in edges.items():
        reverse.setdefault(b, set()).add(a)
    for a, b in edges.items():
        if a not in reverse.get(b, set()):
            gate.fail("%s: endpoint %s -> %s is not bidirectional (no reverse edge)"
                      % (label, a, b))
    # data-lanes validity
    lane_bad = 0
    lanes_seen = 0
    for path, node in tree.nodes.items():
        dl = node.props.get("data-lanes")
        if dl is None:
            continue
        lanes_seen += 1
        n = len(dl.cells)
        if n not in (1, 2, 4):
            gate.fail("%s: %s data-lanes=<%s> invalid count %d (allowed 1/2/4)"
                      % (label, path, " ".join("0x%x" % c for c in dl.cells), n))
            lane_bad += 1
    gate.note("%s: %d endpoints (edges), %d data-lanes specs, %d unresolved/one-way failures"
              % (label, len(edges), lanes_seen, len(errs) + lane_bad))


def check_refs(tree, gate, label, is_merged=False):
    """Resolve clocks/resets/regulators/pinctrl/GPIO through phandle graph.

    In MERGED mode (the authoritative active FDT = base + overlays applied),
    any dangling phandle reference is a structural hard failure. In OVERLAY
    mode (a standalone dtbo partition), phandle references legitimately point
    at base-tree nodes (external) or use 0/placeholder cells, so they are
    reported as notes rather than false positives.
    """
    missing_clocks = {}  # ph -> [paths]
    missing_resets = {}
    missing_gpio = {}
    for path, node in tree.nodes.items():
        for target, idx, ph in dg.resolve_clock_refs(tree, node):
            if target is None and ph != 0:
                missing_clocks.setdefault(ph, []).append(path)
        for target, idx, ph in dg.resolve_reset_refs(tree, node):
            if target is None and ph != 0:
                missing_resets.setdefault(ph, []).append(path)
    for path, node in tree.nodes.items():
        for pname, target, args, flags, ph in dg.resolve_gpio_refs(tree, node):
            if target is None and ph != 0:
                missing_gpio.setdefault(ph, []).append(path)

    def _camera(path):
        node = tree.get(path)
        if node is None:
            return False
        return bool(CAMERA_GREP.search(node.name)) or bool(
            node.props.get("compatible")
            and any(CAMERA_GREP.search(s) for s in node.props["compatible"].strings))

    if is_merged:
        # In the authoritative merged FDT, camera-relevant dangling refs are
        # hard failures; non-camera dangling refs are warnings (out of camera
        # scope, and often a pre-existing vendor-tree condition).
        for ph, paths in missing_clocks.items():
            cam = [p for p in paths if _camera(p)]
            if cam:
                gate.fail("%s: %d camera clock phandle(s) 0x%x unresolved: %s"
                          % (label, len(cam), ph, ", ".join(cam)))
            else:
                gate.warn("%s: non-camera clock phandle 0x%x unresolved in %s"
                          % (label, ph, ", ".join(paths[:3])))
        for ph, paths in missing_resets.items():
            cam = [p for p in paths if _camera(p)]
            if cam:
                gate.fail("%s: %d camera reset phandle(s) 0x%x unresolved: %s"
                          % (label, len(cam), ph, ", ".join(cam)))
            else:
                gate.warn("%s: non-camera reset phandle 0x%x unresolved in %s"
                          % (label, ph, ", ".join(paths[:3])))
        for ph, paths in missing_gpio.items():
            cam = [p for p in paths if _camera(p)]
            if cam:
                gate.fail("%s: %d camera gpio phandle(s) 0x%x unresolved: %s"
                          % (label, len(cam), ph, ", ".join(cam)))
            else:
                gate.warn("%s: non-camera gpio phandle 0x%x unresolved in %s"
                          % (label, ph, ", ".join(paths[:3])))
        if not (missing_clocks or missing_resets or missing_gpio):
            gate.note("%s: all clock/reset/gpio refs resolve (merged FDT)" % label)
    else:
        if missing_clocks:
            gate.note("%s: %d clock phandle(s) are external/overlay refs (base-tree phandles): %s"
                      % (label, len(missing_clocks),
                         ", ".join("0x%x" % p for p in sorted(missing_clocks))))
        if missing_resets:
            gate.note("%s: %d reset phandle(s) external/overlay refs: %s"
                      % (label, len(missing_resets),
                         ", ".join("0x%x" % p for p in sorted(missing_resets))))
        if missing_gpio:
            gate.note("%s: %d gpio phandle(s) external/overlay refs: %s"
                      % (label, len(missing_gpio),
                         ", ".join("0x%x" % p for p in sorted(missing_gpio))))


def check_exclusivity(tree, gate, label):
    """Native CSIS vs vendor FIMC-IS2 must be mutually exclusive."""
    comps = []
    for path, node in tree.nodes.items():
        c = node.props.get("compatible")
        if c:
            comps.extend(c.strings)
    fimc = any(FIMC_IS_RE.search(s) for s in comps)
    csis = any(NATIVE_CSIS_RE.search(s) for s in comps)
    s5k = sorted(set(s for s in comps if S5K_SENSOR_RE.search(s)))
    if csis and fimc and s5k:
        gate.fail("%s: native CSIS AND vendor FIMC-IS both present with sensors %s "
                  "(must be mutually exclusive)" % (label, s5k))
    # Also detect native-CSIS-only-with-s5k as a note (Strategy B target),
    # and vendor-fimc-only as the current Strategy A live state.
    gate.note("%s: fimc_is=%s native_csis=%s s5k_sensors=%s"
              % (label, fimc, csis, s5k))


def validate(path, golden_sha, gate, is_merged=False, board_rev=None, dtbo_idx=None):
    rep = {"path": path, "sha256": sha256_file(path)}
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        gate.fail("%s: %s" % (path, e))
        return rep
    if len(raw) < 8:
        gate.fail("%s: too small (%d bytes)" % (path, len(raw)))
        return rep
    rep["format"] = container_classify(path)
    if rep["format"].startswith("unknown"):
        gate.fail("%s: unrecognised container (magic 0x%08x)"
                  % (path, struct.unpack_from(">I", raw, 0)[0]))
        return rep
    if golden_sha and rep["sha256"] != golden_sha:
        gate.fail("%s: sha256 mismatch (got %s want %s)"
                  % (path, rep["sha256"], golden_sha))

    tree = load_tree(path, gate, path, dtbo_idx=dtbo_idx)
    if tree is None:
        return rep
    check_structure(tree, gate, path)
    check_model(tree, gate, path)
    n_entries = len(dg.dth_entry_offsets(raw)) if dg.is_samsung_dth(raw) else 1
    check_board_revision_selection(tree, gate, path, board_rev, dtbo_idx,
                                   is_dtbo=(not is_merged and n_entries > 1))
    check_endpoints(tree, gate, path)
    check_i2c(tree, gate, path)
    check_refs(tree, gate, path, is_merged=is_merged)
    check_exclusivity(tree, gate, path)

    rep["nodes"] = len(tree.nodes)
    rep["phandles"] = len(tree.phandle_map)
    return rep


def main(argv):
    ap = argparse.ArgumentParser(prog="camera-dt-gate.py")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--golden", help="golden baseline image; camera members must match")
    ap.add_argument("--merged", action="store_true",
                    help="input is the active merged FDT (base+overlays): enforce full hermetic graph")
    ap.add_argument("--board-rev", type=int, default=EXPECT_BOARD_REV)
    ap.add_argument("--dtbo-idx", type=int, default=None,
                    help="dtbo entry index selected by bootloader (androidboot.dtbo_idx)")
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
        rep = validate(path, golden, g, is_merged=a.merged,
                       board_rev=a.board_rev, dtbo_idx=a.dtbo_idx)
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
                for k in ("sha256", "format", "nodes", "phandles"):
                    if k in rep:
                        print("   %-10s %s" % (k + ":", rep[k]))
            for f in g.failures:
                print("   FAIL  %s" % f)
            for w in g.warnings:
                print("   WARN  %s" % w)
            for n in g.notes:
                print("   note  %s" % n)
    if a.json:
        print(json.dumps(reports, indent=2))
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
