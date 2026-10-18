#!/usr/bin/env python3
"""Generate the machine-readable APP-INVENTORY data block from the document tables.

The prose in docs/beta-finalization/apps/APP-INVENTORY.md is the human source of
truth for ids, names, categories, paths, statuses and owners.  This tool derives
the fields the verifier can check from the real tree (manifest version and
capabilities, existing files, existing tests) and writes the block between
INVENTORY-DATA markers.  It is idempotent: re-running replaces the block.

    python3 tools/s10plus/a33/tests/generate-app-inventory.py
    python3 tools/s10plus/a33/verify-app-inventory.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "beta-finalization", "apps", "APP-INVENTORY.md")
BEGIN = "<!-- INVENTORY-DATA:BEGIN -->"
END = "<!-- INVENTORY-DATA:END -->"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def table_rows(text, heading):
    section = text.split(heading, 1)[1]
    section = re.split(r"\n## ", section, 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows[1:] if rows and rows[0][0].lower() in ("id", "gap") else rows


def unquote(value):
    return value.strip().strip("`")


def manifest_of(path):
    p = os.path.join(ROOT, path, "manifest.json")
    if not os.path.isfile(p):
        return {}
    try:
        return json.loads(read(p))
    except Exception:
        return {}


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def test_for(aid, app_type, path):
    if aid == "org.nuxel.SnekByte":
        return ["pwa/nuxel-apps/snekbyte/tests/test-snek-engine.js"]
    if app_type == "native":
        return ["tools/s10plus/a33/tests/test-phone-apps.py"]
    if aid == "tool.firewall":
        return ["tools/s10plus/a33/security-tests/test-firewall.sh"]
    if aid == "tool.tor":
        return ["tools/s10plus/a33/security-tests/test-vpn-tor.sh"]
    if aid == "tool.keyboard":
        return ["tools/s10plus/a33/tests/test-virtual-keyboard.py"]
    if aid in ("tool.system-monitor", "tool.security-audit"):
        return ["tools/s10plus/a33/tests/test-service-graph.py"]
    if app_type in ("pwa", "settings-surface"):
        return ["tools/s10plus/a33/tests/test-core-apps.py"]
    return []


def entry_from_row(row):
    aid, name, category, app_type, path, status, owner = row[:7]
    aid, path, app_type = unquote(aid), unquote(path), unquote(app_type)
    man = manifest_of(path)
    nuxel = man.get("nuxel") or {}
    caps = nuxel.get("capabilities") if isinstance(nuxel.get("capabilities"), list) else []
    have_index = os.path.isfile(os.path.join(ROOT, path, "index.html"))
    have_man = os.path.isfile(os.path.join(ROOT, path, "manifest.json"))
    have_sw = os.path.isfile(os.path.join(ROOT, path, "sw.js"))

    if app_type == "pwa":
        implementation = "PWA: " + ", ".join(
            n for n, ok in (("index.html", have_index), ("manifest.json", have_man),
                            ("sw.js", have_sw)) if ok) or "no PWA files"
        version = str(man.get("version") or "0.0.0")
        permissions = caps
        launch = ("/" + path + "/index.html") if have_index else "n/a (no index.html yet)"
        offline = "service-worker cache" if have_sw else "no service worker (see gap)"
        deps = ["nuxel-bridge"] if caps else []
        pkg = "pwa"
    elif app_type == "native":
        main_c = os.path.join(ROOT, path, "main.c")
        implementation = "native C: main.c" if os.path.isfile(main_c) else "native source missing"
        version = "0.1.0"
        permissions = []
        launch = "/usr/bin/" + os.path.basename(path.rstrip("/"))
        offline = "local store; no network dependency"
        deps = ["nuxel-phone-data"] if aid in ("nuxel-dialer", "nuxel-messages", "nuxel-contacts") else []
        pkg = "native"
    elif app_type == "settings-surface":
        implementation = "settings sub-surface inside the Settings PWA"
        version = str(man.get("version") or "0.0.0")
        permissions = caps
        launch = "n/a (sub-surface of /pwa/nuxel-apps/settings/index.html)"
        offline = "inherits the Settings PWA"
        deps = ["pwa/nuxel-apps/settings"]
        pkg = "settings-surface"
    elif app_type == "tool":
        is_file = os.path.isfile(os.path.join(ROOT, path))
        implementation = "repository script/binary" if is_file else "repository configuration tree"
        version = "0.1.0"
        permissions = []
        launch = path
        offline = "offline tool"
        deps = []
        pkg = "tool"
    else:  # placeholder
        implementation = "no implementation (documented in the gap table)"
        version = "n/a"
        permissions = []
        launch = path + "/index.html" if have_index else "n/a (not implemented)"
        offline = "not available"
        deps = []
        pkg = "placeholder"

    return {
        "id": aid,
        "name": name,
        "category": category,
        "type": app_type,
        "path": path,
        "implementation": implementation,
        "version": version,
        "source": path,
        "package_type": pkg,
        "dependencies": deps,
        "permissions": permissions,
        "launch": launch,
        "hardware": [],
        "offline": offline,
        "tests": [t for t in test_for(aid, app_type, path) if exists(t)],
        "status": status,
        "owner_group": owner,
    }


def gaps_from_rows(rows):
    # The human table names the closing briQ group; the work queue identifies
    # the actual record.  Map the two ambiguous group labels explicitly.
    briq_override = {
        "gap-liveconsole-index": "briq-07e-live-console-app",
        "gap-penguinterface": "briq-07f-penguinterface",
    }
    gaps = []
    for row in rows:
        if len(row) < 6:
            continue
        gid, app, missing, owner, state, closed = row[:6]
        gid, app, owner, state = unquote(gid), unquote(app), unquote(owner), unquote(state)
        if state not in ("open", "closed", "outside-this-group", "by-design"):
            state = "open"
        gap = {"id": gid, "app": app, "missing": missing,
               "owner_group": owner, "state": state}
        m = re.search(r"briq-[A-Za-z0-9-]+", closed)
        if m and state in ("open", "closed"):
            gap["closed_by_briq"] = briq_override.get(gid, m.group(0))
        gaps.append(gap)
    return gaps


def main():
    text = read(DOC)
    apps = [entry_from_row(r) for r in table_rows(text, "## 3. Index")]
    gaps = gaps_from_rows(table_rows(text, "## 5. Gaps"))
    data = {
        "schema": "nuxel.app-inventory/1",
        "generated_from": "docs/beta-finalization/apps/APP-INVENTORY.md sections 3 and 5",
        "apps": apps,
        "gaps": gaps,
    }
    block = (BEGIN + "\n\n```json\n" + json.dumps(data, indent=2, sort_keys=True) +
             "\n```\n\n" + END)
    if BEGIN in text and END in text:
        text = text.split(BEGIN, 1)[0].rstrip() + "\n\n" + block + "\n" + text.split(END, 1)[1].lstrip()
    else:
        text = text.rstrip() + "\n\n## Appendix A — machine-readable inventory data\n\n" + block + "\n"
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %d apps and %d gaps into %s" % (len(apps), len(gaps), os.path.relpath(DOC, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
