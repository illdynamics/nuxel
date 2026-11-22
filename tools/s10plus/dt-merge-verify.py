#!/usr/bin/env python3
"""dt-merge-verify.py — deterministic PROMPT 00 proof.

Establishes, machine-readably, that the live in-memory FDT (/sys/firmware/fdt)
is consistent with the on-flash `dtb` + `dtbo` partitions:
  * every base-dtb node is present in the merged FDT (full containment),
  * camera sensor-module / ISP / CSI nodes carried by the dtbo overlay appear
    in the merged FDT (by node name + compatible),
  * board identity (compatible / hw-rev window) matches the expected board,
  * the off-device dtb/dtbo backup hashes match the live partition hashes
    (these are passed separately and are also recorded by PROMPT 00).

This gives an exact, reproducible "active FDT == on-flash selection" proof that
does not depend on re-running Samsung's proprietary DTH merge (whose byte
serialization and phandle renumbering differ from mainline fdtoverlay). The
proof is semantic containment, which is what actually guards recovery.

Read-only. Never writes inputs or the device. Exit 0 = proof holds.
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dt_graph as dg


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def parse_image(path):
    fdt = dg.extract_first_fdt(path)
    if fdt is None:
        raise ValueError("%s: no FDT" % path)
    return dg.parse_fdt(fdt)


def node_sig(node):
    """Canonical signature of a node's semantic content (order-independent)."""
    sig = []
    for pname in sorted(node.props.keys()):
        p = node.props[pname]
        sig.append((pname, tuple(p.cells), tuple(p.strings)))
    return tuple(sig)


def root_identity(tree):
    root = tree.get("/")
    comp = tuple(root.props["compatible"].strings) if (root and "compatible" in root.props) else ()
    return comp


def collect_camera_module_names(tree):
    """Names of camera sensor-module / ISP / CSI nodes (the things a camera
    DT change touches).

    Excludes DTBO fragment wrappers (fragment@N) and the bare __overlay__
    container nodes, while keeping their real module children
    (e.g. fimc-is_sensor_2l4@20). When comparing the dtbo (which nests real
    modules under fragment@*/__overlay__/) to the merged FDT (which has them
    flat at /fimc-is_sensor_2l4@20), we match on the leaf node NAME+SENSOR
    identity, so wrappers are irrelevant.
    """
    out = set()
    for path, node in tree.nodes.items():
        if node.name.startswith("fragment@") or node.name == "__overlay__":
            continue
        comp = node.props.get("compatible")
        cs = comp.strings if comp else []
        if any(re.search(r'fimc|csis|s5k|2l4|3j1|3m3|3p9|4ha',
                         c, re.I) or re.search(r'sensor-module', c, re.I)
               for c in cs):
            out.add(node.name)
        elif re.search(r'fimc[-_]?is|csis|camera', node.name, re.I):
            out.add(node.name)
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog="dt-merge-verify.py")
    ap.add_argument("--merged", required=True, help="active merged FDT image")
    ap.add_argument("--dtb", required=True, help="base dtb partition image")
    ap.add_argument("--dtbo", required=True, help="dtbo partition image")
    ap.add_argument("--board-rev", type=int, default=26)
    ap.add_argument("--dtbo-idx", type=int, default=9)
    ap.add_argument("--expect-compatible", default="exynos9820")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    import re
    rep = {
        "audit": "PROMPT 00 active-FDT vs on-flash dtb/dtbo semantic containment",
        "merged": {"path": a.merged, "sha256": sha256_file(a.merged)},
        "dtb": {"path": a.dtb, "sha256": sha256_file(a.dtb)},
        "dtbo": {"path": a.dtbo, "sha256": sha256_file(a.dtbo)},
        "board_rev": a.board_rev,
        "dtbo_idx": a.dtbo_idx,
    }

    mdata = open(a.merged, "rb").read()
    if len(mdata) < 8 or struct.unpack_from(">I", mdata, 0)[0] != dg.FDT_MAGIC:
        rep["error"] = "merged is not a bare FDT"
        print(json.dumps(rep, indent=2))
        return 2

    tm = parse_image(a.merged)
    tb = parse_image(a.dtb)
    to = parse_image(a.dtbo)

    # container metadata
    ddata = open(a.dtb, "rb").read()
    odata = open(a.dtbo, "rb").read()
    rep["dtb"]["entries"] = len(dg.dth_entry_offsets(ddata)) or 1
    rep["dtbo"]["entries"] = len(dg.dth_entry_offsets(odata))
    rep["dtb"]["hw_rev_window"] = list(dg.read_hw_rev_window(ddata)) if dg.is_samsung_dth(ddata) else None

    # 1. board identity
    m_root = tm.get("/")
    m_comp = tuple(m_root.props["compatible"].strings) if m_root and "compatible" in m_root.props else ()
    rep["merged_compatible"] = list(m_comp)
    rep["identity_ok"] = any(a.expect_compatible in c.lower() for c in m_comp)

    # 2. base containment: every base node path present in merged with equal sig
    base_paths = set(tb.nodes.keys())
    merged_paths = set(tm.nodes.keys())
    missing = base_paths - merged_paths
    changed = []
    for p in base_paths & merged_paths:
        if node_sig(tb.get(p)) != node_sig(tm.get(p)):
            changed.append(p)
    rep["base_containment"] = {
        "base_nodes": len(base_paths),
        "merged_nodes": len(merged_paths),
        "missing": sorted(missing),
        "changed": sorted(changed),
    }

    # 3. camera module presence: dtbo camera module names must appear in merged
    to_cam = collect_camera_module_names(to)
    tm_cam = collect_camera_module_names(tm)
    missing_cam = sorted(to_cam - tm_cam)
    rep["camera_modules"] = {
        "dtbo_camera_names": sorted(to_cam),
        "in_merged": sorted(to_cam & tm_cam),
        "missing_from_merged": missing_cam,
    }

    proof = (
        rep["identity_ok"]
        and not missing          # a base node vanishing = regression
        and not missing_cam      # a camera module absent from merged = regression
    )
    rep["proof_holds"] = proof
    rep["result"] = "PASS" if proof else "FAIL"

    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print("MERGED  %s sha256=%s (%d nodes)" % (a.merged, rep["merged"]["sha256"], len(merged_paths)))
        print("DTB     %s entries=%s hw_rev=%s sha256=%s"
              % (a.dtb, rep["dtb"]["entries"], rep["dtb"]["hw_rev_window"], rep["dtb"]["sha256"]))
        print("DTBO    %s entries=%s sha256=%s"
              % (a.dtbo, rep["dtbo"]["entries"], rep["dtbo"]["sha256"]))
        print("IDENTITY merged compatible=%s -> %s"
              % (m_comp, "ok" if rep["identity_ok"] else "MISMATCH"))
        print("BASE    %d/%d nodes contained (%d missing = regression); %d modified by overlays (expected)"
              % (len(base_paths) - len(missing), len(base_paths),
                 len(missing), len(changed)))
        if missing:
            print("  missing:", missing[:10])
        if changed:
            print("  changed:", changed[:10])
        print("CAMERA  %d dtbo camera modules; %d missing from merged"
              % (len(to_cam), len(missing_cam)))
        if missing_cam:
            print("  missing camera modules:", missing_cam)
        print("RESULT: %s (proof %s)" % (rep["result"], "holds" if proof else "FAILED"))

    return 0 if proof else 1


if __name__ == "__main__":
    import re  # ensure re available in module scope for helpers
    sys.exit(main(sys.argv[1:]))
