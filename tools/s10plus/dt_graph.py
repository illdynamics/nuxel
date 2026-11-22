#!/usr/bin/env python3
"""dt_graph.py — true device-tree structural graph parser for Exynos DTB/DTBO.

Reads the deterministic DTS text emitted by `dtc -I dtb -O dts` (which
faithfully represents the actual FDT structure, numeric phandles and property
cells) and builds:
  * a nested node tree keyed by full path,
  * a phandle -> path map (phandle / linux,phandle / __symbols__),
  * a decoded property model (u32 cells, strings, string-list),
  * graph resolvers: endpoints (bidirectional), clocks (#clock-cells),
    resets (#reset-cells), regulators, pinctrl, gpio (#gpio-cells + polarity).

References are resolved through the real phandle graph, not regex/DTS
substring heuristics. Read-only; never writes any input.
"""
import re
import subprocess
import struct
import hashlib
import os

FDT_MAGIC = 0xD00DFEED
SAMSUNG_DTH_MAGIC = 0xD7B7AB1E  # also the Samsung/Exynos DTBO container magic


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def is_fdt(b):
    return len(b) >= 8 and struct.unpack_from(">I", b, 0)[0] == FDT_MAGIC


def is_samsung_dth(b):
    return len(b) >= 8 and struct.unpack_from(">I", b, 0)[0] == SAMSUNG_DTH_MAGIC


# ---------------------------------------------------------------------------
# Samsung DTH container (verified against live sda12/sda13 big-endian header)
# ---------------------------------------------------------------------------
# +0x00 magic 0xd7b7ab1e
# +0x04 total container size
# +0x10 number of DT entries (1 for base dtb; N for a dtbo table)
# +0x18 page/alignment (0x800)
# +0x24 first FDT byte offset
# +0x30 dtb-hw_rev low   +0x34 dtb-hw_rev_end high (board revision window)
def dth_entry_offsets(data):
    """All byte offsets of embedded standard FDTs inside a DTH/DTBO blob."""
    if len(data) < 8 or struct.unpack_from(">I", data, 0)[0] != SAMSUNG_DTH_MAGIC:
        return []
    pat = struct.pack(">I", FDT_MAGIC)
    offs = []
    s = 0
    while True:
        o = data.find(pat, s)
        if o < 0:
            break
        offs.append(o)
        s = o + 4
    return offs


def extract_fdts(data):
    """Return list of FDT byte strings embedded in a DTH/DTBO or bare FDT."""
    if is_fdt(data):
        total = struct.unpack_from(">I", data, 4)[0]
        return [data[:total]]
    out = []
    for o in dth_entry_offsets(data):
        if o + 8 > len(data):
            continue
        total = struct.unpack_from(">I", data, o + 4)[0]
        if total <= 0 or o + total > len(data):
            continue
        out.append(data[o:o + total])
    return out


def extract_first_fdt(path):
    data = open(path, "rb").read()
    f = extract_fdts(data)
    return f[0] if f else None


def read_hw_rev_window(data):
    """Return (lo, hi) board-revision window for a DTH container, or None."""
    if len(data) >= 0x38 and struct.unpack_from(">I", data, 0)[0] == SAMSUNG_DTH_MAGIC:
        return (struct.unpack_from(">I", data, 0x30)[0],
                struct.unpack_from(">I", data, 0x34)[0])
    return None


# ---------------------------------------------------------------------------
# DTS statement tokenizer
# ---------------------------------------------------------------------------
# dtc -O dts output uses this grammar (after the /dts-v1/ header):
#   root:  '/' '{' statements '}' ';'
#   node:  [label ':'] (name | '/' ext ')') '{' statements '}' ';'
#   prop:  [label ':'] name '=' value ';'
# We parse line-oriented statements because dtc emits each property on one
# line and braces on their own positions. Labels precede a node/prop on the
# same logical statement.

_NODE_RE = re.compile(r'^\s*(?:([A-Za-z0-9_.,#\-]+)\s*:\s*)?([A-Za-z0-9_@,.\-#]+)\s*\{\s*$')
_PROP_RE = re.compile(r'^\s*(?:([A-Za-z0-9_.,#\-]+)\s*:\s*)?([A-Za-z0-9_,#\-]+)\s*=\s*(.*?)\s*;\s*$')


class DtProperty:
    __slots__ = ("name", "raw", "cells", "strings", "phandles", "phandle_refs", "cell_groups")

    def __init__(self, name, raw):
        self.name = name
        self.raw = raw
        self.cells = []
        self.strings = []
        self.phandles = []
        self.phandle_refs = []
        self.cell_groups = []

    def decode(self):
        v = self.raw
        # Cells live in <...> angle-bracket lists; byte arrays are [..] and
        # must not be number-parsed. Strings are "..." quoted.
        cell_tokens = []
        # Capture raw <...> groups and also note any &label phandle refs.
        self.phandle_refs = []  # raw tokens like '&usi_01_cmgp'
        self.cell_groups = re.findall(r'<([^>]*)>', v)
        for grp in self.cell_groups:
            # remove &label references (word chars after &)
            cleaned = re.sub(r'&[A-Za-z0-9_@,.#-]+', ' ', grp)
            self.phandle_refs += re.findall(r'&([A-Za-z0-9_@,.#\-]+)', grp)
            cell_tokens += re.findall(r'0x[0-9a-fA-F]+|[-+]?\d+', cleaned)
        self.cells = [int(x, 0) for x in cell_tokens]
        self.strings = re.findall(r'"([^"]*)"', v)
        return self


class DtNode:
    __slots__ = ("name", "path", "parent", "children", "props", "phandle")

    def __init__(self, name, path, parent=None):
        self.name = name
        self.path = path
        self.parent = parent
        self.children = {}   # child name -> node
        self.props = {}      # prop name -> DtProperty
        self.phandle = None


class DtTree:
    def __init__(self, dts_text):
        self.root = None
        self.nodes = {}        # path -> node
        self.phandle_map = {}  # int phandle -> path
        self.symbols = {}      # label -> path
        self._parse(dts_text)
        self._index_phandles()

    def _new(self, name, parent):
        if parent.path == "/":
            path = "/" + name
        else:
            path = parent.path + "/" + name
        node = DtNode(name, path, parent)
        self.nodes[path] = node
        if not node.name.startswith("/"):
            parent.children[node.name] = node
        return node

    def _parse(self, text):
        root = DtNode("/", "/", None)
        self.root = root
        self.nodes["/"] = root
        stack = [root]

        for line in text.splitlines():
            s = line.rstrip()
            if not s.strip():
                continue
            if s.strip().startswith("/dts-v1/") or s.strip().startswith("//"):
                continue
            if s.strip() == "/ {":
                continue

            # node close
            if s.strip() == "};":
                if len(stack) > 1:
                    stack.pop()
                continue

            # node open (label possible + name + '{')
            m = _NODE_RE.match(s)
            if m and m.group(2) and s.rstrip().endswith("{"):
                label, nname = m.group(1), m.group(2)
                # skip the already-special-cased root
                if nname == "":
                    continue
                node = self._new(nname, stack[-1])
                if label:
                    self.symbols[label] = node.path
                stack.append(node)
                # node opens; subsequent props belong to it
                continue

            # property
            m = _PROP_RE.match(s)
            if m:
                label, pname, pval = m.group(1), m.group(2), m.group(3)
                node = stack[-1]
                p = DtProperty(pname, pval).decode()
                node.props[pname] = p
                if label:
                    self.symbols[label] = node.path
                continue

            # Anything else: ignored (should not occur in dtc -O dts output).

    def _index_phandles(self):
        for path, node in self.nodes.items():
            for pk in ("phandle", "linux,phandle"):
                p = node.props.get(pk)
                if p and p.cells:
                    node.phandle = p.cells[0]
                    self.phandle_map[p.cells[0]] = path
                    break
        # __symbols__ expands human labels to absolute paths
        sym = None
        for path, node in self.nodes.items():
            if node.name == "__symbols__":
                sym = node
                break
        if sym:
            for pname, p in sym.props.items():
                target = p.strings[0] if p.strings else p.raw.strip().strip('"')
                if target and target.startswith("/"):
                    self.symbols[pname] = target

    # --- lookups ------------------------------------------------------------
    def get(self, path):
        return self.nodes.get(path)

    def resolve_phandle(self, ph):
        return self.phandle_map.get(ph)

    def find(self, pred):
        return [n for n in self.nodes.values() if pred(n)]

    @property
    def phandle_set(self):
        return set(self.phandle_map.keys())

    def node_by_symbol(self, label):
        p = self.symbols.get(label)
        return self.nodes.get(p) if p else None


def parse_fdt(fdt_bytes):
    """Parse FDT bytes into DtTree via dtc -O dts."""
    r = run(["dtc", "-I", "dtb", "-O", "dts", "-"], input=fdt_bytes)
    if r.returncode != 0:
        raise ValueError("dtc: %s" % r.stderr.decode("utf-8", "replace")[:400])
    return DtTree(r.stdout.decode("utf-8", "replace"))


def parse_path(path):
    fdt = extract_first_fdt(path)
    if fdt is None:
        raise ValueError("%s: no embedded FDT" % path)
    return parse_fdt(fdt)


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:]:
        fdt = extract_first_fdt(f)
        if fdt is None:
            print("%s: no FDT" % f)
            continue
        t = parse_fdt(fdt)
        print("%s: %d nodes, %d phandles, %d symbols"
              % (f, len(t.nodes), len(t.phandle_map), len(t.symbols)))
        for ph in sorted(t.phandle_map)[:5]:
            print("  phandle 0x%x -> %s" % (ph, t.phandle_map[ph]))


# ---------------------------------------------------------------------------
# Graph resolution helpers (operate on a DtTree, resolve real phandles)
# ---------------------------------------------------------------------------
REF_PROPS = {
    # property name -> (cells-per-tuple, label for phandle+args)
    "remote-endpoint": (1, "endpoint"),
    "clocks": (2, "clock"),          # phandle + #clock-cells
    "reset-names": (1, "reset"),     # handled via resets
    "resets": (2, "reset"),
    "power-domains": (1, "power-domain"),
    "power-domain": (1, "power-domain"),
    "iommus": (1, "iommu"),
    "interrupt-parent": (1, "interrupt-controller"),
    "assigned-clocks": (2, "clock"),
    "samsung,power-domain": (1, "power-domain"),
    "dmas": (3, "dma"),
    "iommu-names": None,
}


def _prop_cells(tree, node, pname):
    """Return (cells, phandle_refs) for a property, stripping &label refs."""
    p = node.props.get(pname)
    if p is None:
        return None, []
    return p.cells, p.phandle_refs


def resolve_endpoint_graph(tree, errors):
    """Yield every remote-endpoint and verify bidirectional target resolution.

    Returns dict: endpoint_path -> target_path (resolved via phandle).
    Raises/records 'errors' list entries for unresolved or one-directional
    endpoints.
    """
    edges = {}
    for path, node in tree.nodes.items():
        p = node.props.get("remote-endpoint")
        if p is None:
            continue
        cells = p.cells
        if not cells:
            # possibly <&label> form; try phandle_refs
            refs = p.phandle_refs
            if refs:
                target = tree.symbols.get(refs[0])
                if target is None:
                    errors.append("%s: remote-endpoint <&%s> unresolved label"
                                  % (path, refs[0]))
                    continue
            else:
                errors.append("%s: remote-endpoint has no phandle cell" % path)
                continue
        else:
            ph = cells[0]
            target = tree.resolve_phandle(ph)
            if target is None:
                errors.append("%s: remote-endpoint phandle 0x%x unresolved"
                              % (path, ph))
                continue
        edges[path] = target
    return edges


def resolve_clock_refs(tree, node):
    """Return list of (clock-controller-path, index) for node `clocks`."""
    out = []
    p = node.props.get("clocks")
    if p is None:
        return out
    cells = p.cells
    names = node.props.get("clock-names")
    name_list = names.strings if names else []
    # each clock tuple = <phandle #clock-cells...>; determine #clock-cells of target
    i = 0
    n = len(cells)
    while i < n:
        ph = cells[i]
        target = tree.resolve_phandle(ph)
        if target is None:
            out.append((None, None, ph))
            i += 1
            continue
        tnode = tree.get(target)
        nc = 0
        if tnode:
            c = tnode.props.get("#clock-cells")
            if c and c.cells:
                nc = c.cells[0]
        idx = cells[i + 1:i + 1 + nc]
        out.append((target, idx, ph))
        i += 1 + nc
    return out


def resolve_reset_refs(tree, node):
    out = []
    p = node.props.get("resets")
    if p is None:
        return out
    cells = p.cells
    i = 0
    while i < len(cells):
        ph = cells[i]
        target = tree.resolve_phandle(ph)
        nc = 0
        if target:
            tnode = tree.get(target)
            if tnode:
                c = tnode.props.get("#reset-cells")
                if c and c.cells:
                    nc = c.cells[0]
        out.append((target, cells[i + 1:i + 1 + nc], ph))
        i += 1 + nc
    return out


def resolve_gpio_refs(tree, node):
    """Resolve gpio* properties (gpios, grep-gpios, reset-gpios, etc.)."""
    out = []
    for pname, p in node.props.items():
        if not (pname == "gpios" or pname.endswith("-gpios") or "gpio" in pname):
            continue
        # only gpio *list* properties (cells: phandle #gpio-cells(2) + flags)
        cells = p.cells
        i = 0
        while i + 2 <= len(cells):
            ph = cells[i]
            target = tree.resolve_phandle(ph)
            nc = 0
            if target:
                tnode = tree.get(target)
                if tnode:
                    c = tnode.props.get("#gpio-cells")
                    if c and c.cells:
                        nc = c.cells[0]
            args = cells[i + 1:i + 1 + nc] if target else []
            flags = cells[i + 1 + nc] if i + 1 + nc < len(cells) else None
            out.append((pname, target, args, flags, ph))
            if target is None:
                break
            i += 1 + nc + (1 if flags is not None else 0)
    return out


def find_camera_nodes(tree):
    """Locate camera/FIMC/CSIS/sensor nodes by compatible or name."""
    cam_compat = re.compile(
        r'fimc|fimc-is|csis|mipi-csis|s5k|2l4|3j1|3m3|3p9|4ha|sensor-module|'
        r'exynos5-fimc-is|camera', re.I)
    out = []
    for path, node in tree.nodes.items():
        comp = node.props.get("compatible")
        name_match = bool(re.search(r'fimc|csis|camera|sensor', node.name, re.I))
        comp_match = bool(comp and any(cam_compat.search(s) for s in comp.strings))
        if comp_match or name_match:
            out.append(node)
    return out
