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
    """Strictly parse the container entry declared by real bootloader evidence."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        fdts = dg.extract_fdts(raw)
        multi = dg.is_samsung_dth(raw)
        if multi and dtbo_idx is None:
            gate.fail("%s: DT_TABLE requires explicit bootloader-selected --dtbo-idx" % label)
            return None
        if dtbo_idx is not None and not (0 <= dtbo_idx < len(fdts)):
            gate.fail("%s: selected entry %d is not present (count %d)" %
                      (label, dtbo_idx, len(fdts)))
            return None
        if not multi and dtbo_idx not in (None, 0):
            gate.fail("%s: --dtbo-idx invalid for bare FDT" % label)
            return None
        idx = dtbo_idx if dtbo_idx is not None else 0
        tree = dg.parse_fdt(fdts[idx])
        gate.note("%s: parsed selected entry %d of %d" % (label, idx, len(fdts)))
        return tree
    except (ValueError, OSError, UnicodeError, IndexError, struct.error) as e:
        gate.fail("%s: malformed/unreadable FDT container: %s" % (label, e))
        return None


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


def check_model(tree, gate, label, is_merged=False, is_overlay=False):
    root = tree.get('/')
    if not root:
        gate.fail('%s: root node absent' % label)
        return
    comp = root.props.get('compatible')
    comps = comp.strings if comp else []
    model = root.props.get('model')
    models = model.strings if model else []
    # Standalone DT overlays often have only fragment nodes; board identity
    # must instead come from the selected entry plus the active merged tree.
    if not is_overlay and not any('exynos9820' in c.lower() for c in comps):
        gate.fail('%s: exynos9820 compatible missing (got %r)' % (label, comps))
    if models and any('beyond1lte' in m.lower() or 'beyond0lte' in m.lower() for m in models):
        gate.fail('%s: incorrect S10+ model %r' % (label, models))
    if not is_overlay and models and not any('beyond2lte' in m.lower() for m in models):
        gate.fail('%s: model is not beyond2lte: %r' % (label, models))
    if is_merged and not models:
        gate.note('%s: static /model missing; require signed live board manifest' % label)


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
    if not is_dtbo:
        return
    if dtbo_idx is None or board_rev is None:
        gate.fail('%s: DTBO board revision and selected index mandatory' % label)
        return
    root = tree.get('/')
    lo, hi = (root.props.get(x) if root else None for x in ('dtbo-hw_rev', 'dtbo-hw_rev_end'))
    if not lo or not hi or len(lo.data) != 4 or len(hi.data) != 4:
        gate.fail('%s: selected DTBO entry lacks valid board revision bounds' % label)
        return
    l, h = lo.cells[0], hi.cells[0]
    if l > h or not (l <= board_rev <= h):
        gate.fail('%s: selected entry %d rev range [%d,%d] excludes board rev %d' %
                  (label, dtbo_idx, l, h, board_rev))
    else:
        gate.note('%s: selected entry %d covers board rev %d' % (label, dtbo_idx, board_rev))


def _enabled(node):
    p = node.props.get('status')
    return not (p and p.strings and p.strings[0] in ('disabled', 'fail', 'reserved'))


def _camera_node(node):
    cp = node.props.get('compatible')
    return bool(CAMERA_GREP.search(node.path) or
                (cp and any(CAMERA_GREP.search(c) for c in cp.strings)))


def check_i2c(tree, gate, label):
    """Duplicate 7-bit addresses on the *same enabled I2C bus* are unsafe."""
    by_bus = {}
    for path, node, _unit, addr in _iter_i2c_nodes(tree):
        if not _enabled(node):
            continue
        # A sensor `reg` below a CSI node is NOT an I2C address. Restrict
        # address collision logic to explicit I2C parent controllers.
        parent = node.parent
        if not parent or not re.search(r'i2c|hsi2c', parent.name, re.I):
            continue
        if len(node.props['reg'].data) != 4 or not (0x03 <= addr <= 0x7f):
            continue
        key = (parent.path, addr)
        if key in by_bus:
            gate.fail('%s: I2C bus %s duplicates address 0x%02x (%s, %s)' %
                      (label, parent.path, addr, by_bus[key], path))
        else:
            by_bus[key] = path
        if _camera_node(node) and addr in RESERVED_I2C:
            gate.fail('%s: camera node %s claims reserved address 0x%02x' % (label, path, addr))
    gate.note('%s: checked %d enabled I2C bus/address assignments' % (label, len(by_bus)))


def check_endpoints(tree, gate, label):
    errors = []
    edges = dg.resolve_endpoint_graph(tree, errors)
    for err in errors:
        gate.fail('%s: %s' % (label, err))
    for a, b in edges.items():
        if tree.get(b) is None or not b.split('/')[-1].startswith('endpoint'):
            gate.fail('%s: remote endpoint %s resolves to non-endpoint %s' % (label, a, b))
        elif edges.get(b) != a:
            gate.fail('%s: one-way endpoint %s -> %s' % (label, a, b))
    for path, node in tree.nodes.items():
        if not _enabled(node):
            continue
        dl = node.props.get('data-lanes')
        if not dl:
            continue
        vals = dl.cells
        if not vals or len(vals) not in (1, 2, 4) or len(vals) != len(set(vals)) or \
                any(n < 1 or n > 4 for n in vals):
            gate.fail('%s: bad CSI lane count or map at %s: %r' % (label, path, vals))
    for a, b in edges.items():
        if a > b:
            continue
        left, right = tree.get(a), tree.get(b)
        if not left or not right:
            continue
        l, r = left.props.get('data-lanes'), right.props.get('data-lanes')
        if l and r and len(l.cells) != len(r.cells):
            gate.fail('%s: endpoint CSI lane count mismatch %s<->%s' % (label, a, b))
    gate.note('%s: inspected %d directed endpoint links' % (label, len(edges)))


def check_refs(tree, gate, label, is_merged=False):
    """Validate camera dependencies against actual phandle providers.

    Standalone overlays have external references; only the merged tree can
    certify them. Unknown phandle and truncated specifier tuples are fatal for
    active camera paths. The final release gate requires a merged candidate.
    """
    specifiers = {
        'clocks': '#clock-cells', 'assigned-clocks': '#clock-cells',
        'resets': '#reset-cells', 'phys': '#phy-cells',
        'power-domains': '#power-domain-cells', 'dmas': '#dma-cells',
        'iommus': '#iommu-cells',
    }
    for path, node in tree.nodes.items():
        if not _enabled(node) or not _camera_node(node):
            continue
        for pname, p in node.props.items():
            spec = specifiers.get(pname)
            if pname.endswith('-gpios') or pname == 'gpios':
                spec = '#gpio-cells'
            if spec is not None:
                vals = p.cells
                if not vals and p.data:
                    gate.fail('%s: invalid cell width %s/%s' % (label, path, pname))
                    continue
                i = 0
                while i < len(vals):
                    ph = vals[i]
                    target = tree.resolve_phandle(ph)
                    if not target:
                        if is_merged:
                            gate.fail('%s: camera %s/%s has unresolved phandle 0x%x' %
                                      (label, path, pname, ph))
                        break
                    provider = tree.get(target)
                    nc = provider.props.get(spec) if provider else None
                    if nc is None or len(nc.data) != 4 or nc.cells[0] > 16:
                        gate.fail('%s: camera %s/%s provider %s lacks valid %s' %
                                  (label, path, pname, target, spec))
                        break
                    i += 1 + nc.cells[0]
                    if i > len(vals):
                        gate.fail('%s: camera %s/%s has truncated phandle specifier' %
                                  (label, path, pname))
            elif pname == 'pinctrl-0' or re.fullmatch(r'pinctrl-\d+', pname):
                for ph in p.cells:
                    if not tree.resolve_phandle(ph) and is_merged:
                        gate.fail('%s: camera pinctrl %s/%s unresolved phandle 0x%x' %
                                  (label, path, pname, ph))
            elif pname.endswith('-supply') or pname in ('vin-supply', 'vdd-supply'):
                if len(p.data) != 4 or not p.cells:
                    gate.fail('%s: invalid camera regulator ref %s/%s' % (label, path, pname))
                elif is_merged and not tree.resolve_phandle(p.cells[0]):
                    gate.fail('%s: unresolved camera regulator %s/%s' % (label, path, pname))
            elif pname.endswith('-gpios') and is_merged:
                pass
    gate.note('%s: checked enabled camera clock/reset/PHY/regulator/pinctrl/GPIO references'
              % label)


def check_address_cells(tree, gate, label):
    """Verify camera `reg` tuple widths against actual parent bus cells."""
    for path, node in tree.nodes.items():
        if not _enabled(node) or not _camera_node(node):
            continue
        reg = node.props.get('reg')
        if reg is None:
            continue
        parent = node.parent
        if parent is None:
            gate.fail('%s: camera reg lacks parent at %s' % (label, path))
            continue
        a, s = parent.props.get('#address-cells'), parent.props.get('#size-cells')
        if not a or not s or len(a.data) != 4 or len(s.data) != 4 or \
                a.cells[0] > 4 or s.cells[0] > 4 or a.cells[0] == 0:
            gate.fail('%s: camera %s has missing/invalid parent #address-cells/#size-cells' %
                      (label, path))
            continue
        n = a.cells[0] + s.cells[0]
        if len(reg.data) % 4 or not reg.cells or len(reg.cells) % n:
            gate.fail('%s: camera %s reg tuple width does not match parent bus cells' %
                      (label, path))


def check_gpio_ownership(tree, gate, label, is_merged=False):
    """Detect enabled camera vs other hardware claiming identical GPIO line.

    GPIO specifier's final cell contains polarity/flags (per #gpio-cells).
    Unknown polarity / unrelated exact-board pinmux requires a golden diff;
    fail where a camera actually overlaps an existing functional GPIO owner.
    """
    if not is_merged:
        return
    owners = {}
    for path, node in tree.nodes.items():
        if not _enabled(node):
            continue
        for pname, prop in node.props.items():
            if not (pname.endswith('-gpio') or pname.endswith('-gpios') or pname == 'gpios'):
                continue
            vals = prop.cells
            i = 0
            while i < len(vals):
                ph = vals[i]
                target = tree.resolve_phandle(ph)
                provider = tree.get(target) if target else None
                nc = provider.props.get('#gpio-cells') if provider else None
                if not nc or not nc.cells or nc.cells[0] < 2:
                    if _camera_node(node):
                        gate.fail('%s: invalid/unresolved camera GPIO %s/%s' % (label, path, pname))
                    break
                count = nc.cells[0]
                if i + 1 + count > len(vals):
                    gate.fail('%s: malformed camera GPIO tuple %s/%s' % (label, path, pname))
                    break
                pin, flags = vals[i+1], vals[i+count]
                key = (target, pin)
                if flags & ~0x7f and _camera_node(node):
                    gate.fail('%s: suspicious GPIO flags 0x%x at %s/%s' %
                              (label, flags, path, pname))
                for prevpath, prevcamera in owners.get(key, []):
                    if prevpath != path and (_camera_node(node) or prevcamera):
                        gate.fail('%s: GPIO %s pin %d owned by both %s and %s' %
                                  (label, target, pin, prevpath, path))
                owners.setdefault(key, []).append((path, _camera_node(node)))
                i += count + 1
    gate.note('%s: checked %d unique GPIO owner identifiers' % (label, len(owners)))


def check_exclusivity(tree, gate, label):
    fimc, csis = [], []
    for path, node in tree.nodes.items():
        if not _enabled(node):
            continue
        cp = node.props.get('compatible')
        comps = cp.strings if cp else []
        if any(FIMC_IS_RE.search(s) for s in comps):
            fimc.append(path)
        if any(NATIVE_CSIS_RE.search(s) for s in comps):
            csis.append(path)
    if fimc and csis:
        gate.fail('%s: enabled vendor FIMC-IS and native CSIS coexist: %r %r' %
                  (label, fimc[:5], csis[:5]))
    gate.note('%s: enabled FIMC=%d native CSIS=%d' % (label, len(fimc), len(csis)))


def validate(path, golden_sha, gate, is_merged=False, board_rev=None, dtbo_idx=None):
    rep = {"path": path}
    try:
        rep["sha256"] = sha256_file(path)
        raw = open(path, "rb").read()
    except OSError as e:
        gate.fail("%s: %s" % (path, e))
        return rep
    if len(raw) < 8:
        gate.fail("%s: too small (%d bytes)" % (path, len(raw)))
        return rep
    try:
        rep["format"] = container_classify(path)
    except (ValueError, struct.error) as e:
        gate.fail('%s: malformed DTB/DTBO table: %s' % (path, e))
        return rep
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
    is_overlay = dg.is_samsung_dth(raw) and len(dg.dtbo_entries(raw)) > 1
    check_model(tree, gate, path, is_merged=is_merged, is_overlay=is_overlay)
    n_entries = len(dg.dtbo_entries(raw)) if dg.is_samsung_dth(raw) else 1
    check_board_revision_selection(tree, gate, path, board_rev, dtbo_idx,
                                   is_dtbo=(not is_merged and n_entries > 1))
    check_endpoints(tree, gate, path)
    check_address_cells(tree, gate, path)
    check_i2c(tree, gate, path)
    check_refs(tree, gate, path, is_merged=is_merged)
    check_gpio_ownership(tree, gate, path, is_merged=is_merged)
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
    ap.add_argument("--board-rev", type=int, default=None)
    ap.add_argument("--dtbo-idx", type=int, default=None,
                    help="dtbo entry index selected by bootloader (androidboot.dtbo_idx)")
    # Camera DT deltas are controlled by camera-dt-diff.py; no allow bypass here.
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
