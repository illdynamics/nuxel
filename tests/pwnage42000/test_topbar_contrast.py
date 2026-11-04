#!/usr/bin/env python3
"""PWNAGE-42000: top-bar visibility and permission-store contracts.

These are source-level regression checks.  They do not claim a pixel result on
the handset; the live compositor screenshot is the pixel evidence.
"""
from __future__ import annotations

import os


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def test_status_bar_uses_explicit_high_contrast_colours():
    css = read("pwa/nuxel-home/css/status-bar.css")
    assert "--nuxel-status-fg: #f5f9ff" in css
    assert "PWNAGE-42000: top-bar contrast repair" in css
    # The location glyph is a mask now; a grey source PNG can no longer dim it.
    assert ("-webkit-mask: url('/assets/nuxel-quicksettings-icon-pack/09-location.png')" in css
            or "-webkit-mask: url('/assets/nuxel-quicksettings-icon-pack/09-location.svg')" in css)
    assert "background-color: var(--nuxel-network)" in css
    assert "background-color: var(--nuxel-gnss)" in css
    # Sound / USB / clock / battery are explicitly painted, not theme-inherited.
    assert ".status-bar #status-time" in css
    assert ".status-right #status-sound" in css
    assert ".status-right #status-usb" in css
    assert ".battery-icon" in css and "var(--nuxel-status-fg)" in css


def test_disconnected_wifi_is_visible_not_dark_grey():
    js = read("pwa/nuxel-home/js/status-bar.js")
    assert "'--wifi-colour'" in js
    assert "'#666'" not in js
    assert "'#c8d7ea'" in js
    assert "this.elements.wifi.style.opacity = connected ? '1' : (connecting ? '0.95' : '0.9')" in js


def test_build_and_provisioning_grant_bridge_traversal():
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    prov = read("tools/s10plus/a33/nuxel-provision-services.sh")
    for text in (build, prov):
        assert "chmod 0771 /" in text or "chmod 0771 \"$STAGE/var/lib/nuxel\"" in text
        assert "setfacl" in text
        assert "nuxel-bridge" in text
    assert "acl" in build
    assert "u:${NUXEL_BRIDGE_UID}:rwx" in build or "u:nuxel-bridge:rwx" in build


def test_bridge_never_substitutes_observation_time_for_provider_time():
    bridge = read("services/nuxel-bridge/src/bridge.py")
    assert "timestamp_source': 'observed'" not in bridge
    assert "freshness_evidence=False" in bridge
    assert "'fix_timestamp_source'" in bridge
    assert "'freshness_evidence'" in bridge
