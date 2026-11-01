#!/usr/bin/env python3
"""
Generate the full Nuxel feature / hardware / driver / build matrix workbook.

Evidence sources (read-only at generation time):
  - docs/features/README.md and release notes through v0.7.4-beta
  - docs/beta-finalization/live reports and capability manifest
  - docs/beta-finalization/workqueue/*.json
  - pwa/nuxel-common/app-registry.json and PWA manifests
  - services/**, kernel/**, firmware/** manifests, images/**, .github/workflows
  - git branches/tags and repository source trees

The workbook distinguishes source exists, deployed on device, and physically
verified. Absence of evidence is recorded as UNKNOWN / NOT_TRACKED rather than
as a claim of support or non-support.

Usage:
    python3 scripts/generate-nuxel-feature-matrix.py

Dependencies: openpyxl, PyYAML (already available in this workspace).
Output: NUXEL-FULL-FEATURE-MATRIX-2026-11-01.xlsx
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "NUXEL-FULL-FEATURE-MATRIX-2026-11-01.xlsx"
GENERATED = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# ---------------------------------------------------------------------------
# Status vocabulary, colours and helpers
# ---------------------------------------------------------------------------
STATUS = {
    "VERIFIED_ON_S10+": "Physically demonstrated on the S10+ with captured/owner evidence",
    "WORKING_ON_S10+": "Working on the S10+; narrower acceptance or profile remains",
    "DEPLOYED_NEEDS_OWNER": "Deployed to a device/VM; owner-visible check remains",
    "IMPLEMENTED_SOURCE_ONLY": "Source/configuration/tests exist; not proven deployed",
    "PARTIAL": "Some user-visible functions exist; named gaps remain",
    "PLANNED": "Roadmap/branch/backlog item; implementation not complete",
    "BLOCKED_KERNEL": "Needs kernel/config/driver work not deployed",
    "BLOCKED_FIRMWARE": "Needs firmware/blob/vendor runtime not available or lawful",
    "BLOCKED_HARDWARE": "Target silicon/board cannot provide the capability",
    "BLOCKED_EXTERNAL": "Needs device/host/cable/account/service not available",
    "NOT_SUPPORTED": "Explicitly unsupported on the target/current architecture",
    "UNKNOWN": "Hardware/software presence not established by repo evidence",
    "NOT_TRACKED": "Industry phone capability not represented in the current backlog",
    "BRINGUP_INCOMPLETE": "Images flashed or partially built, but boot/UI/hardware acceptance is incomplete",
    "SCAFFOLD": "Design, config or source scaffold only; no device bring-up artifact",
}
STATUS_ABBR = {
    "V": "VERIFIED_ON_S10+", "W": "WORKING_ON_S10+", "D": "DEPLOYED_NEEDS_OWNER",
    "I": "IMPLEMENTED_SOURCE_ONLY", "P": "PARTIAL", "PL": "PLANNED",
    "BK": "BLOCKED_KERNEL", "BF": "BLOCKED_FIRMWARE", "BH": "BLOCKED_HARDWARE",
    "BE": "BLOCKED_EXTERNAL", "NS": "NOT_SUPPORTED", "U": "UNKNOWN", "NT": "NOT_TRACKED",
}
STATUS_FILL = {
    "VERIFIED_ON_S10+": "C6EFCE", "WORKING_ON_S10+": "D9EAD3",
    "DEPLOYED_NEEDS_OWNER": "DDEBF7", "IMPLEMENTED_SOURCE_ONLY": "E8F1FB",
    "PARTIAL": "FFF2CC", "PLANNED": "E4DFEC", "BLOCKED_KERNEL": "F4CCCC",
    "BLOCKED_FIRMWARE": "F9D5E5", "BLOCKED_HARDWARE": "FCE5CD",
    "BLOCKED_EXTERNAL": "FCE4D6", "NOT_SUPPORTED": "D9D9D9",
    "UNKNOWN": "FCE5CD", "NOT_TRACKED": "F2F2F2",
    "BRINGUP_INCOMPLETE": "F9CB9C", "SCAFFOLD": "D9E1F2",
}
NAVY = "17365D"; TEAL = "1F6F78"; LIGHT = "DCE6F1"; WHITE = "FFFFFF"
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FONT = Font(bold=True, color=WHITE, size=10)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
SUBHEAD_FILL = PatternFill("solid", fgColor=TEAL)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def run(*args: str) -> str:
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def short_hash(path: str | Path) -> str:
    p = ROOT / path
    if not p.exists() or not p.is_file():
        return ""
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()[:16]


def exists(path: str | Path) -> bool:
    return (ROOT / path).exists()


def load_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads((ROOT / path).read_text())
    except Exception:
        return default


def load_yaml(path: str | Path) -> Any:
    try:
        return yaml.safe_load((ROOT / path).read_text()) or {}
    except Exception:
        return {}


def status_name(s: str) -> str:
    return STATUS_ABBR.get(s, s)


def add_sheet(wb: Workbook, name: str, title: str, subtitle: str, headers: list[str],
              widths: list[int] | None = None, tab_color: str = NAVY, table_name: str | None = None):
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = tab_color
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    c = ws.cell(1, 1, title)
    c.font = Font(bold=True, color=WHITE, size=15)
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
    c = ws.cell(2, 1, subtitle)
    c.font = Font(italic=True, color="404040", size=9)
    c.fill = PatternFill("solid", fgColor=LIGHT)
    c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 30
    for i, h in enumerate(headers, 1):
        c = ws.cell(3, i, h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
        c.border = BORDER
    ws.row_dimensions[3].height = 28
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A4"
    return ws


def write_rows(ws, rows: Iterable[list[Any]], status_cols: Iterable[int] = (), table_name: str | None = None,
               zebra: bool = True):
    r0 = 4
    for ri, row in enumerate(rows, r0):
        for ci, val in enumerate(row, 1):
            c = ws.cell(ri, ci, val)
            c.alignment = WRAP
            c.border = BORDER
            c.font = Font(size=9)
            if zebra and ri % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F8F9FA")
        for ci in status_cols:
            c = ws.cell(ri, ci)
            s = str(c.value or "")
            if s in STATUS_FILL:
                c.fill = PatternFill("solid", fgColor=STATUS_FILL[s])
                c.font = Font(size=9, bold=s.startswith("VERIFIED"), color="274E13" if s.startswith("VERIFIED") else "000000")
                c.alignment = CENTER
    if table_name and rows:
        end_row = r0 + len(list(rows)) - 1 if not isinstance(rows, list) else r0 + len(rows) - 1
        # Caller passes lists, so len(rows) is safe in practice.
        ref = f"A3:{get_column_letter(ws.max_column)}{max(end_row, 4)}"
        t = Table(displayName=table_name, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False,
                                          showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        ws.add_table(t)


def auto_width(ws, minw=10, maxw=55):
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        best = minw
        for c in col[3:]:
            if c.value is None:
                continue
            for line in str(c.value).splitlines() or [""]:
                best = max(best, min(maxw, len(line) + 2))
        ws.column_dimensions[letter].width = best


def add_kv_sheet(wb: Workbook, name: str, title: str, subtitle: str, pairs: list[tuple[str, Any]], widths=(38, 110)):
    ws = add_sheet(wb, name, title, subtitle, ["Item", "Value"], list(widths), TEAL)
    for i, (k, v) in enumerate(pairs, 4):
        ws.cell(i, 1, k).font = Font(bold=True, size=9)
        ws.cell(i, 1).fill = PatternFill("solid", fgColor=LIGHT)
        ws.cell(i, 1).border = BORDER
        ws.cell(i, 2, v).alignment = WRAP
        ws.cell(i, 2).border = BORDER
        ws.cell(i, 2).font = Font(size=9)
        ws.row_dimensions[i].height = 28
    return ws

# ---------------------------------------------------------------------------
# Evidence loaders
# ---------------------------------------------------------------------------
def load_workqueue() -> list[dict[str, Any]]:
    rows = []
    for p in sorted((ROOT / "docs/beta-finalization/workqueue").glob("*.json")):
        try:
            d = json.loads(p.read_text())
            last = d["revisions"][-1]
            rows.append({
                "id": d.get("id", p.stem),
                "title": last.get("title", ""),
                "component": last.get("component", ""),
                "priority": last.get("priority", ""),
                "state": last.get("state", ""),
                "verdict": last.get("verdict") or "—",
                "risk": last.get("risk", ""),
                "verdict_note": last.get("note", ""),
                "deps": ", ".join(last.get("dependencies", [])),
                "tests": " | ".join(last.get("tests", [])),
                "rollback": last.get("rollback", ""),
                "owner_action": last.get("owner_action", ""),
                "evidence_count": len(last.get("evidence", [])),
                "revisions": len(d.get("revisions", [])),
            })
        except Exception as e:
            rows.append({"id": p.stem, "title": f"ERROR: {e}"})
    return rows


def branch_inventory() -> list[dict[str, Any]]:
    refs = run("git", "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin").splitlines()
    rows = []
    for b in refs:
        if not b or b == "origin/HEAD":
            continue
        try:
            date = run("git", "log", "-1", "--format=%cs", b)
            subj = run("git", "log", "-1", "--format=%s", b)
            sha = run("git", "rev-parse", "--short", b)
            anc = subprocess.run(["git", "merge-base", "--is-ancestor", b, "main"], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            ahead = run("git", "rev-list", "--count", f"main..{b}")
            behind = run("git", "rev-list", "--count", f"{b}..main")
            kind = "local" if not b.startswith("origin/") else "remote"
            name = b.removeprefix("origin/")
            theme = "merged" if anc and str(ahead) == "0" else ("merged-head" if anc else "unmerged")
            rows.append([name, kind, sha, date, subj, "YES" if anc else "NO", ahead, behind, theme])
        except Exception:
            continue
    return sorted(rows, key=lambda r: (r[0].startswith("origin/") is False and False, r[0]))


def app_rows() -> list[list[Any]]:
    registry = load_json("pwa/nuxel-common/app-registry.json", {}) or {}
    reg = {a.get("id"): a for a in registry.get("apps", []) if a.get("id")}
    V = "VERIFIED_ON_S10+"
    W = "WORKING_ON_S10+"
    I = "IMPLEMENTED_SOURCE_ONLY"
    P = "PARTIAL"
    BK = "BLOCKED_KERNEL"
    BF = "BLOCKED_FIRMWARE"
    BE = "BLOCKED_EXTERNAL"
    feature_state = {
        "nuxel-dialer": BK, "nuxel-messages": BK, "nuxel-contacts": W,
        "nuxel-camera": BF, "org.nuxel.Mail": P, "org.nuxel.Calendar": W,
        "org.nuxel.Notes": W, "org.nuxel.Files": W, "nuxel-settings": W,
        "org.nuxel.Terminal": W, "org.nuxel.LiveConsole": W,
        "org.nuxel.USBSSHConsole": BK, "org.nuxel.WiFiSSHConsole": W,
        "org.nuxel.RemoteDesktopXRDP": W, "org.nuxel.RemoteDesktopVNC": W,
        "org.nuxel.ScrcpyMirror": P, "org.nuxel.Browser": W,
        "org.nuxel.Calculator": W, "org.nuxel.Clock": W,
        "org.nuxel.Photos": W, "org.nuxel.Weather": W, "org.nuxel.Maps": W,
        "org.nuxel.Nuxtore": P, "org.nuxel.Recorder": P,
        "org.nuxel.SnekByte": W, "org.mozilla.firefox": W,
        "org.videolan.VLC": P, "org.signal.Signal": BE,
        "com.stremio.Stremio": BK, "org.gnome.FileRoller": W,
        "org.gnome.Loupe": W, "org.gnome.Papers": W,
        "org.gnome.SystemMonitor": W, "org.nuxel.Media": W,
        "org.nuxel.Downloader": W, "org.nuxel.Authenticator": W,
        "org.nuxel.Cleanup": W, "org.nuxel.DevMgmt": W,
        "org.nuxel.PenguInterface": W, "org.gnome.Software": P,
    }
    hw = {
        "nuxel-dialer": "Shannon modem / SIM", "nuxel-messages": "Shannon modem / SIM",
        "nuxel-camera": "Exynos FIMC-IS + camera firmware", "org.nuxel.Camera": "Exynos FIMC-IS + camera firmware",
        "org.nuxel.Maps": "GeoClue network location; GNSS blocked", "org.nuxel.Recorder": "Microphone capture",
        "org.nuxel.Media": "PipeWire/ALSA speaker", "org.nuxel.Photos": "Local storage; camera blocked",
        "org.nuxel.LiveConsole": "USB CDC-ACM", "org.nuxel.USBSSHConsole": "USB network gadget (NCM panic)",
        "org.nuxel.WiFiSSHConsole": "Wi-Fi + SSH", "org.nuxel.RemoteDesktopXRDP": "Wi-Fi/SSH tunnel",
        "org.nuxel.RemoteDesktopVNC": "Wi-Fi/SSH tunnel + Phoc screencopy", "org.nuxel.ScrcpyMirror": "Android ADB target",
        "org.videolan.VLC": "PipeWire/ALSA; Qt GUI missing", "org.signal.Signal": "Flatpak/user namespace",
        "com.stremio.Stremio": "Flatpak/user namespace", "org.nuxel.Authenticator": "Software vault; no TEE unlock",
    }
    rows = []
    for aid, a in reg.items():
        src = a.get("entry") or a.get("binary_source") or a.get("native_binary") or ""
        runtime = (a.get("runtime_state", "") or "").replace(
            "BLOCKED_KERNEL_PANIC on 4.14.253 (documented NCM teardown panic; no fake connection)",
            "Kernel panic blocks USB network; no fake connection")
        rows.append([
            aid, a.get("name", ""), a.get("category", ""), a.get("type", ""),
            src, a.get("native_binary") or a.get("url", ""),
            ", ".join(a.get("capabilities", [])), a.get("status", ""),
            runtime, feature_state.get(aid, I), hw.get(aid, ""),
            a.get("description", ""),
        ])
    # PWA directories, including those not yet in the canonical registry
    for d in sorted((ROOT / "pwa/nuxel-apps").iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if any(r[4] and str(r[4]).startswith(f"pwa/nuxel-apps/{d.name}/") for r in rows):
            continue
        if any(r[4] == f"pwa/nuxel-apps/{d.name}" for r in rows):
            continue
        m = load_json(d / "manifest.json", {}) or {}
        app = load_json(d / "app.json", {}) or {}
        rows.append([
            app.get("id", m.get("nuxel", {}).get("id", d.name)), m.get("name", app.get("name", d.name)),
            app.get("category", m.get("nuxel", {}).get("category", "")), "pwa", f"pwa/nuxel-apps/{d.name}",
            f"/pwa/nuxel-apps/{d.name}/index.html", ", ".join(m.get("nuxel", {}).get("capabilities", [])),
            app.get("status", "tree-only"), "", I, "", "PWA tree entry not in canonical launcher registry",
        ])
    return sorted(rows, key=lambda r: (r[2], r[1]))


def service_rows() -> list[list[Any]]:
    descriptions = {}
    for svc in (ROOT / "services").glob("**/*.service"):
        txt = svc.read_text(errors="replace")
        desc = re.search(r"^Description=(.*)$", txt, re.M)
        desc = desc.group(1).strip() if desc else ""
        # services grouped by parent directory
        parent = svc.parts
        try:
            idx = parent.index("services")
            unit_owner = parent[idx + 1] if idx + 1 < len(parent) else ""
        except ValueError:
            unit_owner = ""
        descriptions[str(svc.relative_to(ROOT))] = (unit_owner, desc)
    roots = sorted({v[0] for v in descriptions.values() if v[0]})
    rows = []
    for root in roots:
        bin_files = sorted((ROOT / "services" / root / "bin").glob("*")) if (ROOT / "services" / root / "bin").exists() else []
        src_files = sorted((ROOT / "services" / root / "src").glob("*")) if (ROOT / "services" / root / "src").exists() else []
        units = sorted(p for p in descriptions if descriptions[p][0] == root)
        desc = next((descriptions[u][1] for u in units if descriptions[u][1]), "")
        rows.append([
            root, desc, "\n".join(Path(u).name for u in units),
            ", ".join(p.name for p in bin_files), ", ".join(p.name for p in src_files),
            "impl", "", "See unit and source paths",
        ])
    # standalone units outside services dirs
    return rows


def firmware_rows() -> list[list[Any]]:
    rows = []
    for dev in ("s10plus", "g7power", "google-pixel-10-pro-xl"):
        p = ROOT / "firmware" / dev / "manifest.yml"
        if not p.exists():
            continue
        d = load_yaml(p)
        device = d.get("device", dev)
        for category, entries in (d.get("firmware_files") or {}).items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                if not isinstance(e, dict):
                    continue
                chk = e.get("checksum")
                if isinstance(chk, dict):
                    chk = chk.get("sha256", "")
                rows.append([
                    device, category, e.get("source_path", ""), e.get("dest", ""),
                    "YES" if e.get("required") else "optional", e.get("description", ""),
                    str(chk or ""), "MANIFEST_ONLY" if not (ROOT / "firmware" / dev / "blobs").exists() else "SEE_BLOBS",
                ])
    return rows


def build_artifact_rows() -> list[list[Any]]:
    rows = []
    for base in ("build/out", "build/backup", "release/s10plus"):
        p = ROOT / base
        if not p.exists():
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file():
                rows.append([str(f.relative_to(ROOT)), f.stat().st_size, short_hash(f), datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    return rows


def test_rows() -> list[list[Any]]:
    rows = []
    for d in sorted((ROOT / "tests").iterdir()):
        if not d.is_dir():
            continue
        files = [f for f in d.rglob("*") if f.is_file()]
        tests = [f for f in files if f.name.startswith("test") or f.name.startswith("run-")]
        rows.append([d.name, len(files), len(tests), ", ".join(f.name for f in sorted(tests)[:8]), "present"])
    return rows


def package_group_rows() -> list[list[Any]]:
    j = load_json("images/s10plus/packages-manifest.json", {}) or {}
    rows = []
    for g in j.get("groups", []):
        pkgs = g.get("packages", [])
        rows.append([g.get("id", ""), g.get("description", ""), len(pkgs),
                     ", ".join(p.get("name", "") for p in pkgs[:12]),
                     "resolved" if not any(p.get("requires", {}).get("unresolved") for p in pkgs) else "check"])
    return rows


def feature_gap_rows() -> list[list[Any]]:
    rows = []
    for i, (cat, sub, feat, outcome, state, detail, plan, ev, pri) in enumerate(FEATURES, 1):
        if state in ("WORKING_ON_S10+", "VERIFIED_ON_S10+"):
            continue
        rows.append([
            i, pri, cat, sub, feat, outcome, state, detail, plan, ev,
            "Owner check" if state in ("DEPLOYED_NEEDS_OWNER",) else
            ("Engineering" if state in ("PARTIAL", "IMPLEMENTED_SOURCE_ONLY", "PLANNED", "NOT_TRACKED", "UNKNOWN") else "Dependency"),
            "",
        ])
    return rows


def branch_theme_rows() -> list[list[Any]]:
    rows = []
    for b in run("git", "for-each-ref", "--format=%(refname:short)|%(subject)", "refs/remotes/origin/nuxel").splitlines():
        name, _, subj = b.partition("|")
        short = name.removeprefix("origin/nuxel/")
        m = re.match(r"r(\d+)-(.*)", short)
        if m:
            rows.append([f"R{m.group(1)}", m.group(2).replace("-", " "), name, subj])
    return rows


def source_stats() -> list[list[Any]]:
    exts = {".py": "Python", ".c": "C", ".h": "C header", ".js": "JavaScript", ".sh": "Shell",
            ".json": "JSON", ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML",
            ".service": "systemd unit", ".nft": "nftables", ".xml": "XML"}
    counts = Counter()
    lines = Counter()
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or ".codeseeq" in p.parts or ".scratch" in p.parts:
            continue
        ext = p.suffix.lower()
        if ext not in exts:
            continue
        typ = exts[ext]
        counts[typ] += 1
        try:
            lines[typ] += sum(1 for _ in p.open("rb"))
        except Exception:
            pass
    return [[t, counts[t], lines[t]] for t in sorted(counts)]

# ---------------------------------------------------------------------------
# Additional loaders
# ---------------------------------------------------------------------------
def resolve_status(s: Any) -> str:
    if not isinstance(s, str):
        return str(s or "UNKNOWN")
    return STATUS_ABBR.get(s, s)


def kernel_config_rows() -> list[list[Any]]:
    sources = [
        ("S10+ (kbase fragment)", "kernel/s10plus/configs/nuxel-drm-kbase.fragment", "downstream 4.14.253"),
        ("G7 Power (fragment)", "kernel/g7power/defconfig", "msm8953-mainline"),
        ("Pixel 10 Pro XL (fragment)", "kernel/google-pixel-10-pro-xl/defconfig", "GKI 6.12 / gs501 target"),
    ]
    rows = []
    for device, rel, tree in sources:
        p = ROOT / rel
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#") and "CONFIG_" not in s:
                continue
            m = re.match(r"^(#\s*)?(CONFIG_[A-Za-z0-9_]+)(?:=(.*))?$", s)
            if not m:
                continue
            commented, key, val = m.groups()
            if commented:
                state = "not set (comment)" if val is None or val == "" else f"commented: {val}"
                value = val or ""
            else:
                state = "set"
                value = val or ""
            rows.append([device, tree, key, value, state, rel, n])
    return rows


def doc_rows() -> list[list[Any]]:
    rows = []
    for p in sorted((ROOT / "docs").rglob("*.md")):
        try:
            txt = p.read_text(errors="replace")
        except Exception:
            continue
        title = next((ln.lstrip("# ").strip() for ln in txt.splitlines() if ln.startswith("#")), "")
        rows.append([str(p.relative_to(ROOT)), title, len(txt.splitlines()), p.stat().st_size, short_hash(p)])
    return rows


def release_rows() -> list[list[Any]]:
    rows = []
    for p in sorted((ROOT / "docs/releases").glob("*.md")):
        txt = p.read_text(errors="replace")
        title = txt.splitlines()[0].lstrip("# ").strip() if txt else ""
        released = ""
        m = re.search(r"\*\*Released:\*\*\s*(.+)", txt)
        if m:
            released = m.group(1).strip()
        rows.append([p.stem, title, released, str(p.relative_to(ROOT)), len(txt.splitlines())])
    return rows


def app_inventory_rows() -> list[list[Any]]:
    p = ROOT / "docs/beta-finalization/apps/APP-INVENTORY.md"
    if not p.exists():
        return []
    txt = p.read_text(errors="replace")
    rows = []
    block = re.search(r"<!-- INVENTORY-DATA:BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- INVENTORY-DATA:END -->", txt, re.S)
    if not block:
        return rows
    try:
        d = json.loads(block.group(1))
    except Exception:
        return rows
    for a in d.get("apps", []):
        rows.append([a.get("id", ""), a.get("name", ""), a.get("category", ""), a.get("type", ""),
                     a.get("path", ""), a.get("implementation", ""), a.get("status", ""),
                     a.get("owner_group", ""), ", ".join(a.get("permissions", []) or []),
                     ", ".join(a.get("hardware", []) or []), a.get("launch", ""), a.get("offline", "")])
    return rows


def gap_inventory_rows() -> list[list[Any]]:
    p = ROOT / "docs/beta-finalization/apps/APP-INVENTORY.md"
    if not p.exists():
        return []
    txt = p.read_text(errors="replace")
    block = re.search(r"<!-- INVENTORY-DATA:BEGIN -->\s*```json\s*(\{.*?\})\s*```\s*<!-- INVENTORY-DATA:END -->", txt, re.S)
    if not block:
        return []
    try:
        d = json.loads(block.group(1))
    except Exception:
        return []
    return [[g.get("id", ""), g.get("app", ""), g.get("missing", ""), g.get("owner_group", ""),
             g.get("state", ""), g.get("closed_by_briq", "")] for g in d.get("gaps", [])]


def summary_stats() -> dict[str, Any]:
    import nuxel_matrix_features as F
    import nuxel_matrix_data as D
    fc = Counter(resolve_status(x[4]) for x in F.FEATURES)
    hw = Counter(x[4] for x in D.HARDWARE)
    sensors = Counter(x[5] for x in D.SENSORS)
    drivers = Counter(x[5] for x in D.DRIVERS)
    apps = app_rows()
    wq = load_workqueue()
    return {
        "features": len(F.FEATURES), "features_by_status": dict(fc),
        "hardware": len(D.HARDWARE), "hardware_by_status": dict(hw),
        "sensors": len(D.SENSORS), "drivers": len(D.DRIVERS),
        "apps": len(apps), "workqueue": len(wq),
        "workqueue_states": dict(Counter(x.get("state", "") for x in wq)),
        "workqueue_verdicts": dict(Counter(x.get("verdict", "") for x in wq)),
        "branches": len(branch_inventory()),
        "tags": len(run("git", "tag").splitlines()),
        "docs": len(doc_rows()),
    }

# ---------------------------------------------------------------------------
# Workbook assembly
# ---------------------------------------------------------------------------
def build_workbook() -> Workbook:
    import nuxel_matrix_features as F
    import nuxel_matrix_data as D
    global V, W, D_, I, P, PL, BK, BF, BH, BE, NS, U, NT
    V = "VERIFIED_ON_S10+"
    W = "WORKING_ON_S10+"
    D_ = "DEPLOYED_NEEDS_OWNER"
    I = "IMPLEMENTED_SOURCE_ONLY"
    P = "PARTIAL"
    PL = "PLANNED"
    BK = "BLOCKED_KERNEL"
    BF = "BLOCKED_FIRMWARE"
    BH = "BLOCKED_HARDWARE"
    BE = "BLOCKED_EXTERNAL"
    NS = "NOT_SUPPORTED"
    U = "UNKNOWN"
    NT = "NOT_TRACKED"

    wb = Workbook()
    wb.remove(wb.active)
    wb.properties.title = "Nuxel full feature, hardware, driver and build matrix"
    wb.properties.subject = "Nuxel phone OS — exhaustive inventory and roadmap"
    wb.properties.creator = "Nuxel repository evidence generator"
    wb.properties.description = (
        "Generated from the Nuxel repository. Statuses separate source implementation, "
        "deployment and physical verification. Unknown/not-tracked rows are deliberate gaps."
    )
    wb.properties.keywords = "Nuxel,Linux phone,Exynos 9820,S10+,features,drivers,sensors,build matrix"

    # 1 — README / legend
    ws = add_sheet(wb, "README", "Nuxel — Full Feature, Hardware, Driver & Build Matrix",
                   f"Generated {GENERATED} from repository docs, branches, source, kernel configs, firmware manifests and build artifacts. "
                   "This is an evidence-gated inventory, not a marketing claim sheet.", ["Item", "Value"], [38, 140])
    pairs = [
        ("Repository", str(ROOT)),
        ("Canonical version", (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown"),
        ("Git HEAD", run("git", "rev-parse", "--short", "HEAD") + " " + run("git", "log", "-1", "--format=%s")),
        ("Worktree", (lambda x: f"{sum(1 for l in x.splitlines() if l[:2].strip() and not l.startswith('##'))} modified/untracked paths at generation time")(run("git", "status", "--porcelain"))),
        ("Primary device", "Samsung Galaxy S10+ SM-G975F (beyond2lte), Exynos 9820, Fedora 43 ARM64, Linux 4.14.253"),
        ("Other targets", "Moto G7 Power (ocean) — flashed/bring-up incomplete; Pixel 10 Pro XL (mustang) — scaffold only"),
        ("Coverage", f"{len(F.FEATURES)} phone features, {len(D.HARDWARE)} hardware components, {len(D.SENSORS)} sensor rows, {len(D.DRIVERS)} driver rows, "
                     f"{len(app_rows())} apps, {len(load_workqueue())} workqueue tasks, {len(branch_inventory())} branches"),
        ("Meaning of VERIFIED_ON_S10+", "Physically demonstrated on the S10+; requires on-device evidence or owner confirmation."),
        ("Meaning of WORKING_ON_S10+", "Working on the S10+ with a named residual acceptance item."),
        ("Meaning of DEPLOYED_NEEDS_OWNER", "Deployed/instrumented, but a human-visible check remains."),
        ("Meaning of IMPLEMENTED_SOURCE_ONLY", "Code/config/tests exist; deployment or physical proof is absent."),
        ("Meaning of PARTIAL", "Some user-visible functions exist; named gaps remain."),
        ("Meaning of PLANNED", "Roadmap/branch/backlog item; implementation not complete."),
        ("Meaning of BLOCKED_*", "A kernel, firmware, hardware or external dependency prevents the capability."),
        ("Meaning of NOT_TRACKED", "An industry-standard phone capability not represented in the current backlog."),
        ("How to use", "Filter the Feature Matrix by Category/Status/Priority. Use Hardware & Sensors for BOM/driver truth. "
                       "Use Planning & Branches for roadmap provenance. Use Build & Artifacts for what actually exists."),
        ("Important caveat", "A directory or icon is not a working app. A registered kernel driver is not a captured frame. "
                             "A running service is not a physical result. Rows are conservative."),
        ("Source files", "docs/features/README.md; docs/beta-finalization/live/PWNAGE-*; docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json; "
                         "docs/beta-finalization/workqueue/*.json; pwa/nuxel-common/app-registry.json; kernel/**; firmware/*/manifest.yml"),
    ]
    for i, (k, v) in enumerate(pairs, 4):
        ws.cell(i, 1, k).font = Font(bold=True, size=10)
        ws.cell(i, 1).fill = PatternFill("solid", fgColor=LIGHT)
        ws.cell(i, 1).border = BORDER
        ws.cell(i, 2, v).alignment = WRAP
        ws.cell(i, 2).font = Font(size=10)
        ws.cell(i, 2).border = BORDER
        ws.row_dimensions[i].height = 30
    r = len(pairs) + 6
    ws.cell(r, 1, "Status legend").font = Font(bold=True, size=12, color=NAVY)
    for j, (s, meaning) in enumerate(STATUS.items(), r + 1):
        ws.cell(j, 1, s).fill = PatternFill("solid", fgColor=STATUS_FILL[s])
        ws.cell(j, 1).font = Font(bold=True, size=9)
        ws.cell(j, 1).border = BORDER
        ws.cell(j, 2, meaning).alignment = WRAP
        ws.cell(j, 2).font = Font(size=9)
        ws.cell(j, 2).border = BORDER

    # 2 — Executive dashboard
    stats = summary_stats()
    ws = add_sheet(wb, "Executive Dashboard", "Executive Dashboard — What Nuxel Contains",
                   "Counts are generated from this workbook's detailed sheets. 'Implemented' is not 'verified'; read the status mix.",
                   ["Metric", "Value", "Interpretation"], [42, 16, 100], TEAL)
    rows = [
        ["Phone features tracked", stats["features"], "Broad taxonomy beyond the current headline feature list."],
        ["  VERIFIED_ON_S10+", stats["features_by_status"].get(V, 0), "Physical evidence on the S10+ only."],
        ["  WORKING_ON_S10+", stats["features_by_status"].get(W, 0), "Working with residual acceptance items."],
        ["  DEPLOYED_NEEDS_OWNER", stats["features_by_status"].get(D_, 0), "Deployed/instrumented, owner check remains."],
        ["  IMPLEMENTED_SOURCE_ONLY", stats["features_by_status"].get(I, 0), "Source exists; deployment/proof absent."],
        ["  PARTIAL", stats["features_by_status"].get(P, 0), "Some user-visible function; named gaps."],
        ["  PLANNED", stats["features_by_status"].get(PL, 0), "Roadmap/branch/backlog."],
        ["  BLOCKED_KERNEL", stats["features_by_status"].get(BK, 0), "Kernel/driver dependency."],
        ["  BLOCKED_FIRMWARE", stats["features_by_status"].get(BF, 0), "Firmware/vendor runtime dependency."],
        ["  BLOCKED_EXTERNAL", stats["features_by_status"].get(BE, 0), "Device/host/owner/service dependency."],
        ["  NOT_SUPPORTED", stats["features_by_status"].get(NS, 0), "Explicitly unsupported on target."],
        ["  NOT_TRACKED", stats["features_by_status"].get(NT, 0), "Industry phone capability absent from backlog."],
        ["Hardware components", stats["hardware"], "Across S10+, G7 Power and Pixel 10 Pro XL."],
        ["Sensor rows", stats["sensors"], "Includes present, blocked, absent and untracked sensors."],
        ["Kernel/driver rows", stats["drivers"], "Kernel, userspace bridge and per-target state."],
        ["Applications inventoried", stats["apps"], "Canonical registry plus PWA tree entries."],
        ["Workqueue tasks", stats["workqueue"], ", ".join(f"{k}={v}" for k, v in sorted(stats["workqueue_states"].items()))],
        ["Branches inventoried", stats["branches"], "Local + origin branches; see Planning & Branches."],
        ["Release tags", stats["tags"], "Latest tag: v0.7.4-beta."],
        ["Documentation files", stats["docs"], "Markdown docs under docs/."],
        ["Primary target verdict", "S10+ = 94% (repo-reported)", "Boots, touch/display, Wi-Fi/Bluetooth, speaker, network location; camera/GNSS/modem/NFC/sensors blocked."],
        ["Overall MVP verdict", "~76% (repo-reported)", "One of three phones boots a Nuxel image; mustang remains scaffold."],
        ["Most important missing proof", "Hardware + owner acceptance", "Camera, satellite GNSS, cellular, NFC, sensors, Flatpak/userns, microphone/headset, suspend."],
    ]
    for i, row in enumerate(rows, 4):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v)
            c.alignment = WRAP if j == 3 else (CENTER if j == 2 else Alignment(vertical="top"))
            c.border = BORDER
            c.font = Font(size=10, bold=(j == 1 and not str(v).startswith("  ")))
            if str(v).startswith("  ") and j == 1:
                c.fill = PatternFill("solid", fgColor="F2F2F2")
                c.font = Font(size=9, bold=False)
    from openpyxl.chart import BarChart, Reference
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "Feature status distribution"
    chart.y_axis.title = "Features"
    chart.x_axis.title = "Status"
    data = Reference(ws, min_col=2, min_row=4, max_row=16)
    cats = Reference(ws, min_col=1, min_row=5, max_row=16)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 7.5
    chart.width = 16
    ws.add_chart(chart, "E4")
    ws.freeze_panes = "A4"

    # 3 — Feature matrix
    ws = add_sheet(wb, "Feature Matrix", "Phone Feature Matrix — 455 functions across 10 domains",
                   "Exhaustive capability taxonomy. Status = current evidence-gated state; S10+ detail and planned/blocker columns prevent false completeness.",
                   ["ID", "Priority", "Category", "Subcategory", "Feature", "User-facing outcome", "Status",
                    "S10+ / current detail", "Planned work / blocker", "Evidence / backlog source"],
                   [7, 8, 16, 18, 25, 32, 22, 55, 55, 42], NAVY)
    rows = []
    for i, (cat, sub, feat, outcome, state, detail, plan, ev, pri) in enumerate(F.FEATURES, 1):
        rows.append([f"F-{i:03d}", pri, cat, sub, feat, outcome, resolve_status(state), detail, plan, ev])
    write_rows(ws, rows, status_cols=[7])
    auto_width(ws, 8, 55)
    ws.auto_filter.ref = f"A3:J{3 + len(rows)}"

    # 4 — Domain coverage / planned gaps
    ws = add_sheet(wb, "Coverage & Gaps", "Coverage by Domain and Highest-Priority Gaps",
                   "Domain counts are computed from the Feature Matrix. Gap rows exclude WORKING/VERIFIED and are sorted by priority then category.",
                   ["Domain", "Features", "Working/Verified", "Partial/Implemented", "Planned", "Blocked", "Not supported/unknown/untracked"], [30, 12, 18, 20, 12, 12, 28], TEAL)
    cats = sorted({x[0] for x in F.FEATURES})
    for i, cat in enumerate(cats, 4):
        vals = [x for x in F.FEATURES if x[0] == cat]
        c = Counter(resolve_status(x[4]) for x in vals)
        ws.cell(i, 1, cat).font = Font(bold=True, size=10)
        ws.cell(i, 2, len(vals))
        ws.cell(i, 3, c.get(W, 0) + c.get(V, 0))
        ws.cell(i, 4, c.get(P, 0) + c.get(I, 0) + c.get(D, 0))
        ws.cell(i, 5, c.get(PL, 0))
        ws.cell(i, 6, sum(c.get(k, 0) for k in (BK, BF, BH, BE)))
        ws.cell(i, 7, sum(c.get(k, 0) for k in (NS, U, NT)))
        for j in range(1, 8):
            ws.cell(i, j).border = BORDER
            ws.cell(i, j).alignment = CENTER if j > 1 else Alignment(vertical="top")
    r = 4 + len(cats) + 2
    ws.cell(r, 1, "Highest-priority remaining gaps").font = Font(bold=True, size=12, color=NAVY)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=7)
    gaps = [x for x in F.FEATURES if resolve_status(x[4]) not in (W, V)]
    gaps.sort(key=lambda x: (x[8], x[0], x[2], x[4]))
    headers = ["Priority", "Category", "Feature", "Status", "Current detail", "Planned / blocker", "Evidence"]
    r += 1
    for j, h in enumerate(headers, 1):
        c = ws.cell(r, j, h); c.font = HEADER_FONT; c.fill = HEADER_FILL; c.alignment = CENTER; c.border = BORDER
    for k, (cat, sub, feat, outcome, state, detail, plan, ev, pri) in enumerate(gaps[:120], r + 1):
        vals = [pri, cat, f"{sub}: {feat}", resolve_status(state), detail, plan, ev]
        for j, v in enumerate(vals, 1):
            c = ws.cell(k, j, v); c.alignment = WRAP; c.border = BORDER; c.font = Font(size=9)
        sc = ws.cell(k, 4)
        s = sc.value
        if s in STATUS_FILL:
            sc.fill = PatternFill("solid", fgColor=STATUS_FILL[s]); sc.alignment = CENTER

    # 5 — Hardware BOM / components
    ws = add_sheet(wb, "Hardware Components", "Hardware BOM and Component State — all three targets",
                   "Every row lists the exact part where known, Linux driver path, and per-target status. UNKNOWN marks genuinely unidentified parts.",
                   ["ID", "Category", "Role", "S10+ part", "S10+ driver / stack", "S10+ status",
                    "G7 Power part", "G7 driver / stack", "G7 status", "Pixel 10 Pro XL part",
                    "Pixel driver / stack", "Pixel status", "Evidence", "Notes"],
                   [8, 20, 22, 34, 36, 20, 32, 32, 20, 34, 34, 20, 38, 42], NAVY)
    rows = [[a, b, c, d, e, f, g, h, i, j, k, l, m, n] for (a, b, c, d, e, f, g, h, i, j, k, l, m, n) in D.HARDWARE]
    write_rows(ws, rows, status_cols=[6, 9, 12])
    auto_width(ws, 8, 44)
    ws.auto_filter.ref = f"A3:N{3 + len(rows)}"

    # 6 — Device comparison
    ws = add_sheet(wb, "Device Comparison", "Target Device Comparison",
                   "Specifications and honest bring-up state for each hardware target.",
                   ["Field", "S10+ / beyond2lte", "G7 Power / ocean", "Pixel 10 Pro XL / mustang"], [28, 55, 48, 48], TEAL)
    keys = ["name", "codename", "soc", "cpu", "gpu", "ram", "storage", "display", "touch", "audio",
            "wifi_bt", "modem", "nfc", "fingerprint", "battery", "boot", "kernel", "userspace", "verdict", "evidence"]
    for i, k in enumerate(keys, 4):
        ws.cell(i, 1, k.replace("_", " ").title()).font = Font(bold=True, size=10)
        ws.cell(i, 1).fill = PatternFill("solid", fgColor=LIGHT)
        for j, dev in enumerate(D.DEVICES, 2):
            c = ws.cell(i, j, dev.get(k, ""))
            c.alignment = WRAP; c.font = Font(size=9); c.border = BORDER
        ws.cell(i, 1).border = BORDER
    ws.cell(4 + len(keys) + 1, 1, "Target state").font = Font(bold=True, size=12, color=NAVY)
    for j, dev in enumerate(D.DEVICES, 2):
        c = ws.cell(4 + len(keys) + 1, j, dev["state"])
        c.fill = PatternFill("solid", fgColor=STATUS_FILL.get(dev["state"], "FFFFFF"))
        c.alignment = CENTER; c.font = Font(bold=True, size=9)

    # 7 — Sensors
    ws = add_sheet(wb, "Sensors", "Sensor Inventory — every sensor class, per target",
                   "Present/absent/blocked states are explicit. The S10+ sensor hub is down; sensor values must never be synthesized.",
                   ["ID", "Sensor", "S10+ part / path", "S10+ interface", "S10+ live state", "S10+ status",
                    "G7 part", "G7 driver", "G7 status", "Pixel part", "Pixel driver", "Pixel status",
                    "Impact / notes", "Evidence"],
                   [8, 28, 34, 22, 42, 20, 26, 25, 18, 30, 26, 18, 38, 42], "7030A0")
    rows = [list(x) for x in D.SENSORS]
    write_rows(ws, rows, status_cols=[6, 9, 12])
    auto_width(ws, 8, 42)
    ws.auto_filter.ref = f"A3:N{3 + len(rows)}"

    # 8 — Kernel / driver matrix
    ws = add_sheet(wb, "Kernel & Drivers", "Kernel and Driver Support Matrix",
                   "Per-target kernel driver/config rows. 'Config state' is from the repository; 'live/evidence state' is from reports; absence of a target means not configured.",
                   ["Target", "Subsystem", "Driver / config", "Kernel tree", "Config state", "Live/evidence state",
                    "Userspace stack", "Blocker / notes", "Evidence"],
                   [14, 22, 40, 30, 22, 45, 34, 50, 42], "C00000")
    rows = [list(x) for x in D.DRIVERS]
    write_rows(ws, rows, status_cols=[])
    auto_width(ws, 8, 50)
    ws.auto_filter.ref = f"A3:I{3 + len(rows)}"

    # 9 — Capabilities / bridge
    ws = add_sheet(wb, "Capabilities & APIs", "Nuxel Capability Model and Bridge APIs",
                   "Capability enum from services/nuxel-bridge/src/capabilities.py plus HTTP/D-Bus surface. Enforcement may be partial (see Sandbox/security rows).",
                   ["Capability / API", "Purpose", "Risk", "Portal type", "Current state", "Notes"], [32, 42, 10, 18, 22, 60], TEAL)
    rows = []
    for cap, purpose, risk, portal, state, note in D.CAPABILITIES:
        rows.append([cap, purpose, risk, portal, resolve_status(state), note])
    write_rows(ws, rows, status_cols=[5])
    auto_width(ws, 10, 60)
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "HTTP endpoints (implemented in services/nuxel-bridge/src/api.py)").font = Font(bold=True, size=12, color=NAVY)
    endpoints = sorted(set(re.findall(r"['\"](/api/v1/[A-Za-z0-9_./{}<>-]+)['\"]", (ROOT / "services/nuxel-bridge/src/api.py").read_text(errors="replace"))))
    for i, ep in enumerate(endpoints, r + 1):
        ws.cell(i, 1, ep)
        ws.cell(i, 1).font = Font(size=9)
    r = r + len(endpoints) + 2
    ws.cell(r, 1, "D-Bus interfaces / buses").font = Font(bold=True, size=12, color=NAVY)
    dbus = []
    for p in (ROOT / "services").glob("**/*.py"):
        txt = p.read_text(errors="replace")
        for m in re.finditer(r"BUS_NAME\s*=\s*['\"]([^'\"]+)['\"]", txt):
            dbus.append((m.group(1), str(p.relative_to(ROOT))))
    for i, (name, path) in enumerate(sorted(set(dbus)), r + 1):
        ws.cell(i, 1, name); ws.cell(i, 2, path)

    # 10 — Applications
    ws = add_sheet(wb, "Applications", "Application Inventory and State",
                   "Canonical launcher registry plus PWA tree entries. The hardware/feature state column is the honest capability state, not mere presence.",
                   ["App ID", "Name", "Category", "Type", "Source / entry", "Launch / binary", "Capabilities",
                    "Registry status", "Runtime state", "Feature state", "Hardware dependency", "Description"],
                   [32, 24, 16, 12, 46, 46, 34, 16, 42, 22, 38, 46], NAVY)
    rows = app_rows()
    write_rows(ws, rows, status_cols=[10])
    auto_width(ws, 8, 48)
    ws.auto_filter.ref = f"A3:L{3 + len(rows)}"

    # 11 — Services
    ws = add_sheet(wb, "Services", "Nuxel Services and Units",
                   "One row per service package; units and binaries are listed. Live state varies by target and is covered in reports.",
                   ["Service", "Description", "Systemd units", "Executables", "Source modules", "Source state", "Deployment state", "Notes"],
                   [30, 52, 48, 52, 54, 14, 18, 42], TEAL)
    rows = service_rows()
    for r in rows:
        r[5] = I
        r[6] = D_
        r[7] = "Source present; deployment/live state depends on image and owner acceptance."
    write_rows(ws, rows, status_cols=[6, 7])
    auto_width(ws, 10, 54)
    ws.auto_filter.ref = f"A3:H{3 + len(rows)}"

    # 12 — Firmware
    ws = add_sheet(wb, "Firmware Inventory", "Firmware / Blob Manifest Inventory",
                   "Exact manifest entries from firmware/*/manifest.yml. MANIFEST_ONLY means the repository lists the blob but has no verified local blob store.",
                   ["Device", "Category", "Source path", "Destination", "Required", "Description", "Checksum", "State"],
                   [18, 22, 55, 42, 10, 54, 42, 18], "C00000")
    rows = firmware_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 55)
    ws.auto_filter.ref = f"A3:H{3 + len(rows)}"

    # 13 — Kernel config
    ws = add_sheet(wb, "Kernel Config", "Kernel Configuration Lines (repo fragments)",
                   "Parsed CONFIG_* lines from the three device fragments. This records intent, not the final merged .config of a built kernel.",
                   ["Target", "Kernel tree", "Config symbol", "Value", "State", "Source file", "Line"],
                   [24, 30, 52, 24, 20, 44, 6], "7030A0")
    rows = kernel_config_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 52)
    ws.auto_filter.ref = f"A3:G{3 + len(rows)}"

    # 14 — Planning / workqueue
    ws = add_sheet(wb, "Planning & Workqueue", "Roadmap / Work Queue — 55 tracked tasks",
                   "Machine-readable workqueue source: docs/beta-finalization/workqueue/*.json. Verdicts are evidence-gated; no unit test can promote to on-device.",
                   ["Task ID", "Title", "Component", "Priority", "State", "Verdict", "Risk", "Dependencies",
                    "Tests", "Owner action", "Rollback", "Evidence count", "Revisions", "Verdict note"],
                   [28, 54, 32, 8, 14, 24, 8, 32, 50, 42, 40, 10, 10, 50], TEAL)
    rows = []
    for w in load_workqueue():
        rows.append([w.get("id", ""), w.get("title", ""), w.get("component", ""), w.get("priority", ""),
                     w.get("state", ""), w.get("verdict", ""), w.get("risk", ""), w.get("deps", ""),
                     w.get("tests", ""), w.get("owner_action", ""), w.get("rollback", ""),
                     w.get("evidence_count", ""), w.get("revisions", ""), w.get("verdict_note", "")])
    write_rows(ws, rows)
    auto_width(ws, 8, 54)
    ws.auto_filter.ref = f"A3:N{3 + len(rows)}"

    # 15 — Branches
    ws = add_sheet(wb, "Branches & Tags", "Git Branches, Tags and Roadmap Themes",
                   "Branch ancestry relative to main; unmerged branches are preserved because they contain future work. Tags are release history.",
                   ["Branch", "Kind", "Head", "Last commit", "Subject", "Ancestor of main", "Ahead", "Behind", "Theme / note"],
                   [62, 10, 12, 12, 70, 14, 8, 8, 24], NAVY)
    rows = branch_inventory()
    write_rows(ws, rows)
    auto_width(ws, 10, 70)
    ws.auto_filter.ref = f"A3:I{3 + len(rows)}"
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "Release tags").font = Font(bold=True, size=12, color=NAVY)
    for i, line in enumerate(run("git", "tag", "--sort=-creatordate").splitlines(), r + 1):
        ws.cell(i, 1, line)
    r = r + len(run("git", "tag").splitlines()) + 2
    ws.cell(r, 1, "R-workstream themes (remote nuxel/rNN branches)").font = Font(bold=True, size=12, color=NAVY)
    themes = branch_theme_rows()
    for j, h in enumerate(["ID", "Theme", "Branch", "Head subject"], 1):
        c = ws.cell(r + 1, j, h); c.font = HEADER_FONT; c.fill = HEADER_FILL; c.border = BORDER
    for i, row in enumerate(themes, r + 2):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v); c.alignment = WRAP; c.font = Font(size=9); c.border = BORDER

    # 16 — Build & artifacts
    ws = add_sheet(wb, "Build & Artifacts", "Build System, CI and Produced Artifacts",
                   "Actual files under build/ and release/, plus package groups and source footprint. Sizes/hashes are read from disk at generation time.",
                   ["Artifact / metric", "Size / count", "SHA-256 (short)", "Modified / note"], [70, 16, 20, 28], TEAL)
    rows = build_artifact_rows()
    write_rows(ws, rows)
    auto_width(ws, 12, 70)
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "S10+ package groups (images/s10plus/packages-manifest.json)").font = Font(bold=True, size=12, color=NAVY)
    headers = ["Group", "Description", "Packages", "Sample packages", "Resolution"]
    for j, h in enumerate(headers, 1):
        c = ws.cell(r + 1, j, h); c.font = HEADER_FONT; c.fill = HEADER_FILL; c.border = BORDER
    for i, row in enumerate(package_group_rows(), r + 2):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v); c.alignment = WRAP; c.font = Font(size=9); c.border = BORDER
    r = r + 2 + len(package_group_rows()) + 2
    ws.cell(r, 1, "Source footprint by file type (services, shell, pwa, tools, docs, kernel)").font = Font(bold=True, size=12, color=NAVY)
    for j, h in enumerate(["Type", "Files", "Lines"], 1):
        c = ws.cell(r + 1, j, h); c.font = HEADER_FONT; c.fill = HEADER_FILL; c.border = BORDER
    for i, row in enumerate(source_stats(), r + 2):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v); c.border = BORDER

    # 17 — Test & acceptance
    ws = add_sheet(wb, "Tests & Acceptance", "Test Suites and Manual Acceptance Areas",
                   "Repository test directories plus the manual-proof checklist. Green unit tests are offline evidence, not hardware verification.",
                   ["Suite / area", "Files", "Test files", "Representative tests", "State"], [28, 10, 12, 90, 18], "7030A0")
    rows = test_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 90)
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "Manual proof checklist").font = Font(bold=True, size=12, color=NAVY)
    mp = sorted((ROOT / "docs/beta-finalization/manual-proof").glob("*.md"))
    for i, p in enumerate(mp, r + 1):
        ws.cell(i, 1, p.name)
        title = p.read_text(errors="replace").splitlines()[0].lstrip("# ").strip()
        ws.cell(i, 2, title)
        ws.cell(i, 2).alignment = WRAP
        ws.cell(i, 2).font = Font(size=9)

    # 18 — App gaps
    ws = add_sheet(wb, "App Inventory & Gaps", "Core App Inventory (source-verifier view) and Recorded Gaps",
                   "Parsed machine-readable block from docs/beta-finalization/apps/APP-INVENTORY.md. The verifier distinguishes present/full, present/partial, missing and external.",
                   ["App ID", "Name", "Category", "Type", "Path", "Implementation", "Inventory status",
                    "Owner group", "Permissions", "Hardware", "Launch", "Offline behavior"], [30, 24, 18, 12, 45, 40, 16, 30, 36, 20, 44, 42], NAVY)
    rows = app_inventory_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 60)
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "Recorded app gaps").font = Font(bold=True, size=12, color=NAVY)
    for j, h in enumerate(["Gap ID", "App", "Missing", "Owner", "State", "Closed by"], 1):
        c = ws.cell(r + 1, j, h); c.font = HEADER_FONT; c.fill = HEADER_FILL; c.border = BORDER
    for i, row in enumerate(gap_inventory_rows(), r + 2):
        for j, v in enumerate(row, 1):
            c = ws.cell(i, j, v); c.alignment = WRAP; c.font = Font(size=9); c.border = BORDER

    # 19 — Releases
    ws = add_sheet(wb, "Releases", "Release History and Headlines",
                   "Release notes under docs/releases/. Tags can exist without every physical capability being accepted.",
                   ["Version", "Title", "Released", "Path", "Lines"], [18, 70, 14, 42, 10], TEAL)
    rows = release_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 70)

    # 20 — Docs index
    ws = add_sheet(wb, "Docs Index", "Documentation Index and Evidence Anchors",
                   "All Markdown docs under docs/ with size/hash. Use this to find the authoritative evidence for any row.",
                   ["Path", "Title", "Lines", "Bytes", "SHA-256 (short)"], [72, 74, 8, 12, 20], NAVY)
    rows = doc_rows()
    write_rows(ws, rows)
    auto_width(ws, 10, 74)
    ws.auto_filter.ref = f"A3:E{3 + len(rows)}"

    # 21 — Prioritized implementation plan
    ws = add_sheet(wb, "Priority Plan", "Prioritized Completion Plan — What to Implement Next",
                   "Synthesized from blocked/planned/partial features and workqueue priorities. 'Dependency' names the first technical gate.",
                   ["Priority", "Workstream", "Feature / capability", "Why it matters", "First dependency", "Acceptance evidence required"],
                   [10, 24, 40, 55, 45, 55], "C00000")
    plan = [
        ("P0", "Modem / telephony", "Shannon modem + ModemManager plugin", "A phone must call/text; currently zero targets have a modem object.", "CP host interface + plugin", "SIM detected, registration, call audio, SMS send/receive"),
        ("P0", "Camera", "FIMC-IS V4L2/libcamera pipeline", "No usable capture node; blocks camera, video, QR, video calls.", "Standard media-controller/V4L2 surface + setfiles", "One real JPEG + one video frame with timestamps; sensor metadata"),
        ("P0", "GNSS", "BCM4773 BBD/LHD runtime", "Only network location works; satellite fix blocked.", "BBD patch firmware + lawful userspace", "Outdoor fix with satellite count/accuracy/timestamp"),
        ("P0", "Kernel / sandbox", "USER_NS + OVERLAY_FS on 4.14", "Flatpak/bwrap cannot create user namespaces.", "Patched kernel flashed and verified", "zcat /proc/config.gz; bwrap + one ARM64 Flatpak launches"),
        ("P0", "Sensor hub", "BCM47752 SSP firmware + daemon", "Auto-rotate, proximity, ALS, compass and GNSS depend on SSP.", "SSP firmware + protocol daemon", "Nonzero accel/gyro/ALS/prox values; auto-rotate and call screen-off"),
        ("P1", "Display/GPU", "Live Phoc linux-dmabuf + WebKit WSI", "WebKit stays software; GPU compositor works but WSI crashes.", "wlroots/Phoc dmabuf crash fix", "Home PWA on AMOLED with accelerated WebKit and no fallback marker"),
        ("P1", "Audio", "Microphone / headset / USB-C audio", "Only speaker playback is owner-confirmed.", "Capture route + USB role policy", "WAV recording, headset route, USB DAC playback"),
        ("P1", "Security", "FDE + verified boot + TEE keystore", "Bring-up image is writable/unsigned; no hardware-backed secrets.", "LUKS2/AVB/TEE integration", "Encrypted userdata; signed boot; key operations through TEE"),
        ("P1", "NFC", "Kernel NFC + controller firmware + NCI stack", "S10+ kernel has CONFIG_NFC off; no tag read.", "Kernel rebuild + firmware + nfcd/neard", "Physical NDEF tag read/write; no payment claim"),
        ("P1", "Touch/UI", "Owner acceptance and long-press semantics", "Working UI still has focus/drag/keyboard edge cases.", "Regression tests + owner sessions", "Signed manual-proof checklist across PWA/native/dialog flows"),
        ("P1", "Update/recovery", "S10+ OTA/rollback or documented no-OTA policy", "No end-to-end update path on the working phone.", "A-only validation/rollback design", "Interrupted-update recovery; versioned image; tested restore"),
        ("P2", "Power", "Suspend/idle/thermal policy", "No suspend acceptance; battery life unknown.", "Kernel PM + wake sources", "Measured idle drain; wake on modem/input/alarm"),
        ("P2", "Security", "Sandbox enforcement end-to-end", "Configs exist; live enforcement partial on 4.14.", "Kernel/features + audit tests", "Per-app filesystem/network/device denial proofs"),
        ("P2", "Accessibility", "Screen reader, scaling, captions, TTS/STT", "Major phone capability absent from backlog.", "AT-SPI/Orca + UI focus model", "Accessible navigation and media/caption tests"),
        ("P2", "Apps", "Native GTK app shipping", "GTK sources not compiled into the handset image.", "Image build inclusion + launch path", "Dialer/messages/contacts/settings launch on device"),
        ("P2", "Apps", "Remote app repository + updates", "Nuxtore install backend incomplete; no signed remote repo.", "Package signing/trust + update flow", "Install/update/uninstall one signed app end-to-end"),
        ("P2", "Connectivity", "Tethering/hotspot/VPN UI", "No hotspot; VPN/Tor primarily tooling/config.", "NM/firewall policy + UI", "Client connects, DNS works, kill switch proven"),
        ("P2", "Camera", "Camera firmware + computational features", "Even after capture, ISP/3A/multi-camera work remains.", "Capture pipeline first", "AF/AE/AWB, multi-camera, 4K video"),
        ("P3", "Ecosystem", "SDK/templates/API reference", "Third-party development is ad hoc.", "Stable bridge/portal API", "Sample app builds and installs with docs"),
        ("P3", "Media", "Screen recording / casting", "No recorder or Miracast.", "PipeWire screencast + cast protocol", "Record AV; discover/render to TV"),
        ("P3", "Device", "Backup/restore and anti-theft", "No backup, remote wipe, find-my.", "Secure service/account model", "Encrypted backup/restore; remote lock/wipe"),
        ("P3", "Accessories", "External display / desktop mode", "DisplayPort stack absent on S10+.", "DRM + DP Alt Mode", "External monitor at native mode and input"),
        ("P4", "Future", "Multi-user / MDM / UWB / satellite", "Long-horizon ecosystem features.", "Ecosystem and hardware support", "Design + acceptance criteria only"),
    ]
    write_rows(ws, plan, status_cols=[])
    auto_width(ws, 10, 60)

    # 22 — Source index / verification commands
    ws = add_sheet(wb, "Method & Sources", "Method, Verification Commands and Source Map",
                   "How statuses were derived and how to reproduce or challenge them.",
                   ["Topic", "Commands / paths", "What it proves"], [38, 100, 70], TEAL)
    method = [
        ("Current feature truth", "cat docs/features/README.md; ls docs/releases/", "Canonical feature verdicts and latest release claims."),
        ("Live evidence reports", "find docs/beta-finalization/live -maxdepth 1 -name 'PWNAGE-*'", "Physical/deployment claims with blockers."),
        ("Capability manifest", "python3 tools/beta/validate-capability-manifest.py", "Evidence-gated subsystem verdicts."),
        ("Workqueue", "python3 tools/beta/workqueue.py list --json", "All roadmap tasks, state, deps, verdicts."),
        ("Git roadmap", "git branch -a; git tag -l; git log --oneline --all", "Branches and release history."),
        ("Apps", "cat pwa/nuxel-common/app-registry.json; tools/s10plus/a33/verify-app-registry.py", "Canonical app set and drift checks."),
        ("Services", "python3 tools/s10plus/a33/verify-service-graph.py", "Unit graph and ordering."),
        ("Hardware IDs", "cat docs/hardware-ids.md; cat docs/driver-status.md", "Part numbers and driver state."),
        ("Firmware", "cat firmware/*/manifest.yml; firmware/verify-firmware.sh", "Blob inventory and verification gate."),
        ("Kernel", "cat kernel/*/defconfig; cat kernel/s10plus/configs/nuxel-drm-kbase.fragment", "Kernel config intent."),
        ("Artifacts", "find build/out release -type f -exec shasum -a 256 {} \\;", "Exactly what was built/shipped."),
        ("Tests", "find tests tools -name 'test*' -o -name 'run-*'", "Offline/automated coverage."),
        ("On-device commands", "ssh nuxel@PHONE; zcat /proc/config.gz; ls /dev; cat /proc/asound/cards", "Re-measure the live claims; never trust a stale report."),
        ("Safety", "Never flash/modify partitions without explicit owner approval; preserve serial/SSH recovery.", "Nuxel invariants and protected partitions."),
    ]
    write_rows(ws, method, status_cols=[])
    auto_width(ws, 20, 100)

    # 23 — Build & CI matrix
    ws = add_sheet(wb, "Build & CI Matrix", "Build Pipeline and CI Gate Matrix",
                   "Build artifacts, stages and CI workflow steps. A stage is 'working' only where the repository contains a produced artifact or a proven live build.",
                   ["Build / CI stage", "Script(s) / artifact", "What it does", "State", "Source", "Notes"],
                   [28, 58, 58, 24, 44, 58], TEAL)
    rows = build_stage_rows()
    write_rows(ws, rows, status_cols=[4])
    auto_width(ws, 10, 58)
    r = 4 + len(rows) + 2
    ws.cell(r, 1, "GitHub Actions release.yml steps").font = Font(bold=True, size=12, color=NAVY)
    for i, (name, line) in enumerate(ci_rows(), r + 1):
        ws.cell(i, 1, name)
        ws.cell(i, 2, f"line {line}")
        ws.cell(i, 1).font = Font(size=9); ws.cell(i, 2).font = Font(size=9)

    # 24 — Per-device subsystem truth
    ws = add_sheet(wb, "Device Subsystems", "Per-Device Subsystem Truth Table",
                   "What each target can actually do now. This is the sheet to read before assuming a component works because code exists.",
                   ["Target", "Subsystem", "Implementation / path", "State", "Verified truth / blocker", "Next work"],
                   [14, 22, 52, 24, 70, 55], "C00000")
    rows = device_subsystem_rows()
    write_rows(ws, rows, status_cols=[4])
    auto_width(ws, 10, 70)
    ws.auto_filter.ref = f"A3:F{3 + len(rows)}"

    # 25 — Full package list
    ws = add_sheet(wb, "Package Inventory", "Fedora 43 aarch64 Package Inventory",
                   "Every package in images/s10plus/packages-manifest.json, grouped by role. Resolution is against real Fedora metadata; file requirements are counted but not verified from primary.xml.",
                   ["Group", "Package", "NEVRA", "Requirement count", "Unresolved requirements", "Role / notes"],
                   [24, 30, 56, 14, 34, 46], TEAL)
    pj = load_json("images/s10plus/packages-manifest.json", {}) or {}
    rows = []
    for g in pj.get("groups", []):
        for p in g.get("packages", []):
            req = p.get("requires", {}) or {}
            rows.append([g.get("id", ""), p.get("name", ""), p.get("nevra", ""),
                         req.get("total", 0), ", ".join(req.get("unresolved", []) or []), g.get("description", "")])
    write_rows(ws, rows)
    auto_width(ws, 10, 56)
    ws.auto_filter.ref = f"A3:F{3 + len(rows)}"

    # Formula/table note and print settings
    for sh in wb.worksheets:
        sh.sheet_view.zoomScale = 85
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.sheet_properties.pageSetUpPr.fitToPage = True
        sh.print_options.horizontalCentered = True
        sh.print_title_rows = "3:3"

    return wb



# Status constants used by the workbook assembly helpers above.

# ---------------------------------------------------------------------------
# Additional tables appended at build time
# ---------------------------------------------------------------------------
def ci_rows() -> list[list[Any]]:
    path = ROOT / ".github/workflows/release.yml"
    if not path.exists():
        return []
    rows = []
    lines = path.read_text(errors="replace").splitlines()
    for i, line in enumerate(lines, 1):
        m = re.match(r"\s*- name:\s*(.+)", line)
        if m:
            rows.append([m.group(1).strip(), i])
    return rows


def build_stage_rows() -> list[list[Any]]:
    return [
        ["Host toolchain", "aarch64 cross compiler, gcc-arm-none-eabi, bc/bison/flex, libssl/libelf, cpio, dtc, e2fsprogs, ffmpeg", "CI installs pinned dependencies", "WORKING_ON_S10+", ".github/workflows/release.yml", "S10+ image is built on Linux CI; local macOS builds need extra host tooling."],
        ["Device selection", "tools/nuxel-device-select.sh: CLI > NUXEL_DEVICE > explicit error", "Implemented", "IMPLEMENTED_SOURCE_ONLY", "tools/nuxel-device-select.sh", "No silent device guessing."],
        ["Shared initramfs", "images/build.sh --initramfs-only; boot/initramfs/init.sh", "Device-dispatched POSIX shell", "IMPLEMENTED_SOURCE_ONLY", "boot/initramfs/init.sh", "S10+ needs embedded raw arm64 initramfs."],
        ["S10+ kernel", "kernel/s10plus/build-kernel.sh / build-kernel-kbase.sh", "Pinned Samsung 4.14.253 + patches + DRM/kbase fragment", "WORKING_ON_S10+", "kernel/s10plus", "Kernel flashed and booted on handset."],
        ["S10+ boot image", "images/s10plus/build-a25-boot.sh + boot/s10plus/pack-boot-v1.sh", "Raw arm64 Image with embedded initramfs, v1 header", "WORKING_ON_S10+", "build/out/s10plus/nuxel-beyond2lte-boot-drm-kbase.img", "Verified /dev/sda14 readback and header."],
        ["S10+ rootfs", "images/s10plus/build-phone-rootfs-fedora.sh (Podman arm64)", "Fedora 43 aarch64 ext4 phone rootfs", "WORKING_ON_S10+", "build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-p42000.img", "4 GiB image built/e2fsck/offline-verified."],
        ["S10+ userspace payload", "tools/s10plus/a43/package-live.py + verify-live.py", "Source-derived payload with SHA-256 staging", "WORKING_ON_S10+", ".github/workflows/release.yml", "Deployed live over console/SSH."],
        ["S10+ artifact gate", "tools/verify-artifacts.sh --device s10plus", "Fail-closed content/header/kernel checks", "WORKING_ON_S10+", "tools/verify-artifacts.sh", "A red gate blocks release publication."],
        ["G7 Power kernel", "kernel/g7power/build-kernel.sh", "msm8953-mainline + fragment", "BRINGUP_INCOMPLETE", "kernel/g7power", "Built but device boots only to black/flashy screen."],
        ["G7 Power lk2nd", "boot/g7power/lk2nd/build-lk2nd.sh", "msm8916-mainline/lk2nd msm8953 target", "IMPLEMENTED_SOURCE_ONLY", "boot/g7power/lk2nd", "Flashing order dtbo-first enforced."],
        ["G7 Power images", "images/g7power/build.sh + boot/g7power/pack-boot-v1.sh", "lk2nd, boot, ext4 rootfs", "BRINGUP_INCOMPLETE", "images/g7power", "Flashed but no usable UI."],
        ["Pixel 10 Pro XL kernel", "kernel/build-kernel.sh --vendor or GKI fallback", "6.12 GKI merge + gs501 vendor target", "SCAFFOLD", "kernel/google-pixel-10-pro-xl", "Vendor tree unavailable; vendor drivers absent."],
        ["Pixel 10 Pro XL images", "images/google-pixel-10-pro-xl/build.sh + AVB/RAUC/OSTree", "A/B v4 boot, vendor_boot, init_boot, dm-verity, RAUC", "SCAFFOLD", "images/google-pixel-10-pro-xl", "No boot artifact produced."],
        ["OTA build", "images/build-ota.sh --target pmos|fedora", "RAUC bundle / OSTree commit", "IMPLEMENTED_SOURCE_ONLY", "images/build-ota.sh", "No end-to-end update accepted on S10+."],
        ["Release packaging", "tools/package-release.sh + GitHub Actions release", "Versioned tarball + captured installed image + SHA256SUMS", "WORKING_ON_S10+", ".github/workflows/release.yml", "Only a green build can publish; captured bytes carried forward."],
        ["VM build", "vm/build-vm-image.sh + UTM scripts", "Fedora 43 Phosh VM at 720x1440", "PARTIAL", "vm/", "VM boots per docs, but parity evidence is incomplete."],
        ["Static validation", "ci/phase3-validate.sh, ci/validate-build.sh, Makefile", "Python/shell/JSON/syntax and artifact checks", "IMPLEMENTED_SOURCE_ONLY", "ci/", "mustang validator is the only strict artifact validator."],
        ["Tests", "tests/**, tools/**/tests, pytest, JS harnesses", "Offline regression suites + live acceptance scripts", "IMPLEMENTED_SOURCE_ONLY", "tests/", "Offline green never equals on-device verification."],
    ]


def device_subsystem_rows() -> list[list[Any]]:
    return [
        ["s10plus", "Boot", "S-Boot -> kernel -> initramfs -> Fedora 43 -> systemd -> Phoc", "VERIFIED_ON_S10+", "Boots cold and after normal reboot; post-reboot evidence exists.", "Remaining: charger/LPM touch, boot polish, soak."],
        ["s10plus", "Display", "DPU20 fbdev + nuxel-wl-fb", "VERIFIED_ON_S10+", "1440x3040 ABGR frames committed; single /dev/fb0 owner.", "HDR/refresh/DRM and WebKit acceleration remain."],
        ["s10plus", "Touch", "sec_ts -> evdev -> libinput -> Phoc", "VERIFIED_ON_S10+", "Unlock/Home/app launch/touch gestures physically verified.", "Long-press/drag focus edge cases still owner checks."],
        ["s10plus", "Wi-Fi", "BCM4375 + NetworkManager", "VERIFIED_ON_S10+", "Radio on after boot, saved profiles autoconnect, internet works.", "6GHz/WPA3/roaming/power-save tests."],
        ["s10plus", "Bluetooth", "BCM4375 + HCIUART/H4 + BlueZ", "WORKING_ON_S10+", "hci0 powered, peer scan works, pair/connect implemented.", "Headset/keyboard profile acceptance."],
        ["s10plus", "Speaker audio", "Madera + ABOX + CS35L41", "VERIFIED_ON_S10+", "Owner-confirmed audible across cues/reboot.", "Capture/headset/USB-C audio."],
        ["s10plus", "Network location", "GeoClue agent + Wi-Fi/IP", "VERIFIED_ON_S10+", "Real network fix verified across reboots.", "Privacy/accuracy and outdoor tests."],
        ["s10plus", "Camera", "FIMC-IS", "BLOCKED_FIRMWARE", "Sensors/ISP enumerate; no standard capture; setfiles absent.", "libcamera FIMC-IS pipeline or lawful vendor runtime."],
        ["s10plus", "Satellite GNSS", "BCM4773 BBD", "BLOCKED_FIRMWARE", "Rails respond; SSP down; BBD patch/runtime absent.", "Firmware + runtime."],
        ["s10plus", "Cellular", "Shannon LTE", "BLOCKED_KERNEL", "Net devices exist; ModemManager finds no modem.", "Shannon plugin/CP interface."],
        ["s10plus", "NFC", "S3NRN82", "BLOCKED_KERNEL", "CONFIG_NFC not set; firmware absent.", "Kernel + firmware + NCI stack."],
        ["s10plus", "Sensors/IMU", "BCM47752 SSP + LSM6DSO", "BLOCKED_FIRMWARE", "SSP down; raw 0,0,0; auto-rotate blocked.", "SSP firmware/daemon."],
        ["s10plus", "Fingerprint", "qbt2000", "BLOCKED_EXTERNAL", "No secure TEE/fprintd provider.", "TEE-backed provider and PIN fallback."],
        ["s10plus", "Haptics", "timed_output", "DEPLOYED_NEEDS_OWNER", "Writer path exists; physical feel unverified.", "Owner vibration test."],
        ["s10plus", "Flashlight", "torch-sec1", "WORKING_ON_S10+", "300 mA ON / 0 OFF verified.", "Visible illumination owner check."],
        ["s10plus", "MTP", "f_mtp + nuxel-mtp-server", "WORKING_ON_S10+", "MTP enumerates on macOS; Shared-only root.", "Finder requires OpenMTP/MTPLX; SD export test."],
        ["s10plus", "USB serial", "CDC-ACM", "VERIFIED_ON_S10+", "Key-only framed console is the recovery path.", "Retain ownership/arbitration tests."],
        ["s10plus", "USB network", "NCM gadget", "BLOCKED_KERNEL", "Teardown panic on 4.14.253.", "Safe non-NCM gadget or kernel fix."],
        ["s10plus", "Flatpak", "bubblewrap/user namespaces", "BLOCKED_KERNEL", "CONFIG_USER_NS=n; bwrap fails.", "Patched kernel + ARM64 runtime launch."],
        ["s10plus", "GPU", "Mali kbase + Mesa panfrost", "WORKING_ON_S10+", "Phoc GPU context, GLES 3.2 renderer.", "Wayland WSI/linux-dmabuf/WebKit acceleration."],
        ["s10plus", "Battery", "max77705 fuel gauge", "WORKING_ON_S10+", "Capacity/status/temp/voltage; debounced UI.", "Health/cycle/idle/thermal tests."],
        ["s10plus", "Suspend", "PM", "PLANNED", "No s2idle/s2ram acceptance.", "Kernel PM + wake sources."],
        ["g7power", "Boot", "ABOOT -> lk2nd -> mainline", "BRINGUP_INCOMPLETE", "Images flashed; hangs at black/flashy screen.", "Display/touch/rootfs bring-up."],
        ["g7power", "Display", "simpledrm/fbcon", "BRINGUP_INCOMPLETE", "No usable UI.", "lk2nd framebuffer handoff and Phoc."],
        ["g7power", "Touch", "ili210x", "UNKNOWN", "Driver symbol correct; binding unproven.", "Boot far enough to test."],
        ["g7power", "Wi-Fi", "wcn36xx", "UNKNOWN", "Config present; no live proof.", "Firmware and association."],
        ["g7power", "Audio", "WCD9335", "UNKNOWN", "Config present; no live proof.", "UCM and speaker/capture."],
        ["g7power", "Cellular", "X9 LTE", "BLOCKED_KERNEL", "No ModemManager path.", "Modem bring-up."],
        ["mustang", "Boot", "ABL/AVB/Titan M3", "SCAFFOLD", "No boot artifact.", "Vendor tree, firmware extraction, AVB signing."],
        ["mustang", "Display", "AMB655X DRM", "SCAFFOLD", "Vendor-only panel driver.", "DRM panel + DSC/HDR."],
        ["mustang", "Touch", "S6SY791", "SCAFFOLD", "Vendor-only touch driver.", "Vendor tree or out-of-tree driver."],
        ["mustang", "Cellular", "Exynos 5500 MHI", "SCAFFOLD", "No vendor plugin/firmware.", "MHI plugin + ModemManager."],
        ["mustang", "Camera", "Tensor ISP", "SCAFFOLD", "Vendor camera stack.", "libcamera/vendor path."],
        ["mustang", "GPU", "PowerVR DXT-72", "SCAFFOLD", "No mainline DXT driver.", "Vendor kernel/userspace."],
    ]


def main():
    wb = build_workbook()
    wb.save(OUT)
    print(f"Wrote {OUT}")
    print(f"Sheets: {', '.join(wb.sheetnames)}")


if __name__ == "__main__":
    main()
