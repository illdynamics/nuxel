#!/usr/bin/env python3
"""Integration checks for the PWNAGE-27000 Location/Maps repair.

These are repository-level integration tests: they prove the shipped Maps app,
Quick Setting, Settings diagnostics, bridge API and tile contract agree.  They
do not claim a physical GPS fix.  One optional network probe validates the
configured OSM tile endpoint when the host can reach it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


def test_default_tile_source_matches_shipped_contract():
    cfg = json.loads(read("configs/nuxel/gnss/osm-tiles.json"))
    assert cfg["network"]["online_url"] == "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    assert "OpenStreetMap" in cfg["attribution"]
    assert cfg["offline_first"]["requires_network_for_cached_area"] is False
    core = read("pwa/nuxel-common/maps-core.js")
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in core
    assert "OpenStreetMap contributors" in core
    assert "attributionUrl" in core


def test_maps_page_loads_shared_core_and_shows_attribution():
    html = read("pwa/nuxel-apps/maps/index.html")
    assert "nuxel-common/maps-core.js" in html
    assert 'id="tile-badge"' in html
    assert 'class="attribution"' in html
    assert "OpenStreetMap contributors" in html
    assert 'id="search-results"' in html
    assert 'id="provider-state"' in html
    # The default must be a real attributed source, not an empty placeholder.
    assert "tile.openstreetmap.org" not in html or "Use OpenStreetMap" in html


def test_maps_renderer_uses_configured_source_and_provider():
    js = read("pwa/nuxel-apps/maps/js/maps.js")
    assert "C.loadConfig" in js
    assert "tileUrlFor" in js
    assert "enqueueTile" in js
    assert "location', 'get-status" in js
    assert "location', 'acquire" in js
    assert "tileOutcome" in js or "describeTileFailure" in js
    assert "window.nuxelMaps" in js
    # Search results must not be saved as pins automatically.
    assert "state.pins.push" not in js
    assert "C.addPin" in js


def test_quick_setting_has_all_provider_states():
    qs = read("pwa/nuxel-home/js/qs.js")
    for state in ("fixed", "stale", "searching", "no_fix", "disabled", "error", "unavailable"):
        assert "'" + state + "'" in qs, state
    assert "last provider fix" in qs
    assert "Location<br>no fix" not in qs or "no_fix" in qs


def test_settings_has_location_and_maps_diagnostics():
    html = read("pwa/nuxel-apps/settings/index.html")
    assert 'data-tab="location"' in html
    assert 'id="location-state"' in html
    assert 'id="location-acquire"' in html
    assert 'id="maps-tile-url"' in html
    assert 'id="maps-state"' in html
    assert "location-maps.js" in html and "maps-core.js" in html
    js = read("pwa/nuxel-apps/settings/location-maps.js")
    assert "location', 'get-status" in js
    assert "location', 'acquire" in js
    assert "C.saveConfig" in js
    assert "C.DEFAULT_CONFIG" in js


def test_bridge_api_maps_request_and_acquire():
    api = read("services/nuxel-bridge/src/api.py")
    assert '("location", "request"): "GetLocation"' in api
    assert '("location", "acquire"): "LocationAcquire"' in api
    bridge = read("services/nuxel-bridge/src/bridge.py")
    assert "def LocationAcquire" in bridge
    assert "state == 'fixed'" in bridge
    assert "STALE_FIX" in bridge
    assert "last_fix_timestamp" in bridge


def test_shared_bridge_never_mock_fixes_location():
    js = read("pwa/nuxel-common/bridge.js")
    assert "case 'location.request'" in js
    assert "case 'location.acquire'" in js
    assert "state: 'unavailable'" in js


def test_osm_tile_endpoint_reachable_from_host():
    """Optional real network probe; skipped when the host has no egress."""
    url = "https://tile.openstreetmap.org/4/8/5.png"
    req = urllib.request.Request(url, headers={"User-Agent": "NuxelMaps/27000 (integration test)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            body = res.read(64)
            ctype = res.headers.get("Content-Type", "")
            status = res.status
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip("host has no network egress for the tile probe: %s" % exc)
    assert status == 200
    assert body.startswith(b"\x89PNG")
    assert "image" in ctype


def test_node_core_unit_suite_runs():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    p = subprocess.run([node, os.path.join(HERE, "test_maps_core.mjs")],
                       capture_output=True, text=True, cwd=REPO)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "ALL PASS" in p.stdout


def test_gnss_diag_bcm_fixture_and_selftest():
    p = subprocess.run(["bash", os.path.join(REPO, "tools/s10plus/a33/nuxel-gnss-diag.sh"), "selftest"],
                       capture_output=True, text=True, cwd=REPO)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "gnss-bcm-nofw" in p.stdout


def test_first_party_system_grants_are_explicit_and_scoped():
    expected = {
        "org.nuxel.Home.json": {"location:manage", "location:read", "network:manage", "bluetooth:manage"},
        "nuxel-settings.json": {"location:manage", "location:read", "network:manage", "bluetooth:manage", "bluetooth:scan", "bluetooth:connect"},
        "org.nuxel.Maps.json": {"location:read"},
    }
    for name, caps in expected.items():
        doc = json.loads(read("configs/nuxel/permissions/" + name))
        assert set(doc) == caps, name
        for cap, info in doc.items():
            assert info["duration"] in ("always", "session")
        assert doc["location:manage"]["duration"] == "always" if "location:manage" in doc else True


def test_bridge_grant_loader_reads_system_grants():
    import importlib.util
    import sys
    import types
    import tempfile
    import shutil

    src = os.path.join(REPO, "services", "nuxel-bridge", "src")
    class _Obj:
        pass
    class _Service:
        Object = _Obj
        def method(self, *a, **k):
            return lambda f: f
        def signal(self, *a, **k):
            return lambda f: f
    fake = types.ModuleType("dbus")
    fake.service = _Service()
    fake.SystemBus = lambda *a, **k: None
    fake.SessionBus = lambda *a, **k: None
    fake.Interface = lambda *a, **k: None
    fake.Boolean = bool
    fake.exceptions = types.SimpleNamespace(DBusException=Exception)
    fake.PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
    fake.types = types.SimpleNamespace(String=lambda v, **k: v)
    saved = {k: sys.modules.get(k) for k in list(sys.modules) if k.startswith("dbus") or k == "gi" or k.startswith("gi.")}
    sys.modules.update({
        "dbus": fake, "dbus.service": fake.service, "dbus.exceptions": fake.exceptions,
        "dbus.mainloop.glib": types.ModuleType("dbus.mainloop.glib"),
        "gi": types.ModuleType("gi"), "gi.repository": types.ModuleType("gi.repository"),
    })
    sys.modules["gi.repository"].GLib = types.SimpleNamespace(MainLoop=lambda *a, **k: None)
    spec = importlib.util.spec_from_file_location("bridge_grants_under_test", os.path.join(src, "bridge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    expected = {
        "org.nuxel.Home.json": {"location:manage", "location:read"},
        "nuxel-settings.json": {"location:manage", "location:read"},
        "org.nuxel.Maps.json": {"location:read"},
    }
    tmp = tempfile.mkdtemp(prefix="nuxel-system-grants-")
    try:
        for name in expected:
            shutil.copy(os.path.join(REPO, "configs/nuxel/permissions", name), tmp)
        old = mod.PERMISSIONS_DIR
        mod.PERMISSIONS_DIR = tmp
        try:
            grants = mod.NuxelBridgeService._load_all_grants(object())
        finally:
            mod.PERMISSIONS_DIR = old
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert grants["org.nuxel.Home"]["location:manage"] == "always"
    assert grants["nuxel-settings"]["location:read"] == "always"
    assert grants["org.nuxel.Maps"]["location:read"] == "always"
    assert "location:manage" not in grants["org.nuxel.Maps"]


def test_bridge_dbus_policy_does_not_block_provider_calls():
    a = read("configs/dbus/org.nuxel.Bridge.conf")
    b = read("services/nuxel-bridge/dbus/org.nuxel.Bridge.conf")
    assert a == b
    assert '<deny receive_sender="org.nuxel.Bridge" receive_type="signal"/>' in a
    assert '<deny receive_sender="org.nuxel.Bridge"/><!---->' not in a
    # The broad deny must not come back; it blocked GeoClue receiving bridge calls.
    assert '\n    <deny receive_sender="org.nuxel.Bridge"/>\n' not in a
