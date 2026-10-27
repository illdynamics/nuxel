"""NUXEL-28000 Tri-Link Applications-window registration tests.

These are OFFLINE assertions over the shipped sources.  They prove the three
console entries are registered exactly once with distinct presentation and a
transport-specific handler; they do not prove a phone rendered them.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "pwa/nuxel-common/app-registry.json"
APPS_JS = ROOT / "pwa/nuxel-home/js/apps.js"
NATIVE = ROOT / "shell/nuxel-home-native/nuxel_home/app_registry.json"
APPS_ROOT = ROOT / "pwa/nuxel-apps"

EXPECTED = {
    "org.nuxel.LiveConsole": {
        "name": "Serial Live Console", "transport": "serial",
        "dir": "console", "icon_asset": "/assets/nuxel-applications-icon-pack/05-05_live-console.png",
    },
    "org.nuxel.USBSSHConsole": {
        "name": "USB SSH Console", "transport": "usb",
        "dir": "console-usb", "icon_asset": "/assets/nuxel-applications-icon-pack/06-05_usb-connection.png",
    },
    "org.nuxel.WiFiSSHConsole": {
        "name": "Wi-Fi SSH Console", "transport": "wifi",
        "dir": "console-wifi", "icon_asset": "/assets/nuxel-quicksettings-icon-pack/01-wifi.png",
    },
}


def test_canonical_registry_has_exactly_the_three_console_entries_once():
    doc = json.loads(REGISTRY.read_text())
    consoles = [a for a in doc["apps"] if a.get("console_transport")]
    ids = [a["id"] for a in consoles]
    assert Counter(ids) == Counter({aid: 1 for aid in EXPECTED}), ids
    assert len(ids) == len(set(ids)) == 3
    assert doc["registry_version"] == 6
    for app in consoles:
        exp = EXPECTED[app["id"]]
        assert app["name"] == exp["name"]
        assert app["console_transport"] == exp["transport"]
        assert app["entry"] == "pwa/nuxel-apps/%s/index.html" % exp["dir"]
        assert (ROOT / app["entry"]).is_file()
        assert (ROOT / app["manifest"]).is_file()


def test_launcher_literal_and_icon_map_have_one_entry_each():
    text = APPS_JS.read_text()
    body = text.split("const NUXEL_APPS", 1)[1]
    entries = {}
    for key, chunk in re.findall(r"^\s*'([^']+)':\s*\{\s*(.*?)^\s*\},", body, re.S | re.M):
        ident = re.search(r"^\s*id:\s*'([^']+)'", chunk, re.M)
        name = re.search(r"^\s*name:\s*'([^']+)'", chunk, re.M)
        transport = re.search(r"^\s*consoleTransport:\s*'([^']+)'", chunk, re.M)
        if ident:
            entries[ident.group(1)] = {
                "name": name.group(1) if name else None,
                "transport": transport.group(1) if transport else None,
            }
    console_entries = {aid: meta for aid, meta in entries.items()
                       if meta["transport"] is not None}
    assert Counter(console_entries.keys()) == Counter({aid: 1 for aid in EXPECTED})
    for aid, meta in console_entries.items():
        assert meta["name"] == EXPECTED[aid]["name"]
        assert meta["transport"] == EXPECTED[aid]["transport"]
    icon_map = text.split("const NUXEL_APP_ICON_ASSETS", 1)[1]
    for aid, exp in EXPECTED.items():
        hits = re.findall(r"^\s*'%s':\s*'([^']+)'" % re.escape(aid), icon_map, re.M)
        assert len(hits) == 1, (aid, hits)
        assert hits[0].split("?", 1)[0] == exp["icon_asset"]
        asset = ROOT / exp["icon_asset"].lstrip("/")
        assert asset.is_file(), asset
    assert len({exp["icon_asset"] for exp in EXPECTED.values()}) == 3


def test_native_consumer_has_the_same_three_entries_once():
    native = json.loads(NATIVE.read_text())
    console_ids = [a["id"] for a in native["apps"]
                   if a["id"] in EXPECTED]
    assert Counter(console_ids) == Counter({aid: 1 for aid in EXPECTED})
    for app in native["apps"]:
        if app["id"] in EXPECTED:
            assert app["name"] == EXPECTED[app["id"]]["name"]
            assert "/pwa/nuxel-apps/%s/index.html" % EXPECTED[app["id"]]["dir"] in app["url"]


def test_each_page_selects_its_own_transport_and_manifest():
    for aid, exp in EXPECTED.items():
        root = APPS_ROOT / exp["dir"]
        html = (root / "index.html").read_text()
        manifest = json.loads((root / "manifest.json").read_text())
        appjson = json.loads((root / "app.json").read_text())
        assert re.search(r'<meta\s+name="nuxel-app-id"\s+content="%s"' % re.escape(aid), html)
        assert re.search(r'<body\s+data-transport="%s"' % exp["transport"], html)
        assert re.search(r"startTriLinkConsole\('%s'\)" % exp["transport"], html)
        assert manifest["start_url"] == "/pwa/nuxel-apps/%s/index.html" % exp["dir"]
        assert manifest["scope"] == "/pwa/nuxel-apps/%s/" % exp["dir"]
        assert manifest["nuxel"]["transport"] == exp["transport"]
        assert manifest["nuxel"]["bridge_version"] == "1"
        assert manifest["nuxel"]["read_only_status"] is True
        assert appjson["id"] == aid
        assert appjson["console_transport"] == exp["transport"]


def test_console_pages_share_status_reader_without_faking_connection():
    js = (APPS_ROOT / "console/console.js").read_text()
    assert "bridge.call('system', 'tri-link'" in js
    assert "host_command" in js
    assert "no key is stored on the phone" in js
    # Three distinct transport configs; no wildcard/default fallback.
    assert js.count("appId: 'org.nuxel.") == 3
    assert "stateKey" in js and "BLOCKED_KERNEL_PANIC" in js
    # A failed bridge read must be rendered as an error, never as READY.
    assert "success === false" in js


def test_every_app_json_id_is_unique_across_the_tree():
    ids = []
    for path in APPS_ROOT.glob("*/app.json"):
        ids.append(json.loads(path.read_text())["id"])
    dupes = [aid for aid, n in Counter(ids).items() if n > 1]
    assert not dupes, dupes


def test_bridge_exposes_read_only_status_and_mock_never_claims_success():
    api = (ROOT / "services/nuxel-bridge/src/api.py").read_text()
    bridge = (ROOT / "pwa/nuxel-common/bridge.js").read_text()
    assert "import tri_link_status" in api
    assert "path == '/api/v1/system/tri-link'" in api
    assert "namespace == 'system' and verb == 'tri-link'" in api
    assert "case 'system.tri-link':" in bridge
    assert "tri-link status was not read" in bridge


def test_deployment_manifest_is_complete_and_never_touches_firmware():
    manifest = json.loads((ROOT / "tools/beta/live/nuxel-28000-tri-link-ui-manifest.json").read_text())
    sources = [f["source"] for g in manifest["groups"] for f in g["files"]]
    assert sources
    for src in sources:
        assert (ROOT / src).is_file(), src
    for group in manifest["groups"]:
        assert group.get("health_check")
        assert group.get("rollback")
        assert group.get("risk") in ("low", "medium", "high")
    targets = [f["target"] for g in manifest["groups"] for f in g["files"]]
    forbidden = ("/boot", "/dev/", "/proc/", "/sys/", ".img", "boot.img", "recovery.img", "/efs", "modem")
    for target in targets:
        assert not any(part in target for part in forbidden), target
    # The live image serves the PWA tree from the nuxel-session fallback, so
    # the static-file group must not restart nuxel-web (which already fails to
    # bind :8000 on this image). It declares a deliberate reload instead.
    static = next(g for g in manifest["groups"] if g["id"] == "tri-link-pwa")
    assert static.get("restart_service") is None and static.get("declared_reload")
    assert "nuxel-http-bridge" in {g.get("restart_service") for g in manifest["groups"]}
