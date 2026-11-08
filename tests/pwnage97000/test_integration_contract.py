"""PWNAGE-97000 source, packaging and security contract tests."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def test_portal_frontend_and_nuxel_backend_are_selected():
    conf = read("configs/nuxel/portals.conf")
    assert "org.freedesktop.impl.portal.FileChooser=nuxel" in conf
    assert "org.freedesktop.impl.portal.FileChooser=gtk" not in conf
    assert "org.nuxel.Portal" in conf
    descriptor = read("services/nuxel-portal-chooser/xdg-desktop-portal/nuxel.portal")
    assert "DBusName=org.freedesktop.impl.portal.desktop.nuxel" in descriptor
    assert "org.freedesktop.impl.portal.FileChooser" in descriptor
    assert "UseIn=Nuxel" in descriptor
    service = read("services/nuxel-portal-chooser/dbus/org.freedesktop.impl.portal.desktop.nuxel.service")
    assert "Exec=/usr/libexec/nuxel/nuxel-portal-chooser" in service


def test_backend_implements_all_three_portal_methods_and_shared_policy():
    src = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    for token in ("OpenFile", "SaveFile", "SaveFiles",
                  "org.freedesktop.impl.portal.Request", "async_callbacks",
                  "multiple", "directory", "current_folder", "current_name",
                  "filters", "accept_label", "file_uri", "Gallery", "Files",
                  "close_handle", "REQUEST_TIMEOUT_S", "canonical_selection"):
        assert token in src, token
    assert "nuxel_file_handlers" in src
    assert "org.nuxel.Portal" in src


def test_backend_has_no_fake_media_or_unsafe_permission_flags():
    src = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    for forbidden in ("--filesystem=host", "--device=all", "--no-sandbox",
                      "data:image", "sample.jpg", "sample.png"):
        assert forbidden not in src
    assert "Base64-only camera" in src or "never fabricates a file URI" in src


def test_flatpak_launch_flags_do_not_disable_sandboxes():
    src = read("services/nuxel-bridge/src/flatpak_provider.py")
    assert '"--no-sandbox"' not in src
    assert "QTWEBENGINE_DISABLE_SANDBOX" not in src
    assert "--no-sandbox" not in src.split("QTWEBENGINE_CHROMIUM_FLAGS", 1)[-1].split("\n", 1)[0]


def test_settings_file_handlers_surface_is_first_class():
    index = read("pwa/nuxel-apps/settings/index.html")
    assert 'data-tab="file-handlers"' in index
    assert 'id="tab-file-handlers"' in index
    assert 'id="fh-global-policy"' in index
    assert 'id="fh-test"' in index
    assert 'id="fh-portal"' in index
    assert "file-handlers-settings.js?v=p97000" in index
    js = read("pwa/nuxel-apps/settings/file-handlers-settings.js")
    assert "file-handlers" in js and "rpc('get'" in js and "rpc('set'" in js
    assert "rpc('test-picker'" in js
    code_only = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    assert "localStorage" not in code_only


def test_bridge_owns_file_handler_settings_and_mimeapps():
    src = read("services/nuxel-bridge/src/api.py")
    assert "if namespace == 'file-handlers'" in src
    assert "def _file_handlers_rpc" in src
    assert "def _open_file_handler" in src
    assert "/api/v1/file-handlers/open" in src
    assert "test-picker" in src and "consume-open" in src
    assert "FILE_HANDLERS_OWNERS" in src


def test_gallery_and_files_mime_open_handoff():
    photos = read("pwa/nuxel-apps/photos/js/photos.js")
    files = read("pwa/nuxel-apps/files/js/files.js")
    assert "consume-open" in photos and "consumePendingOpen" in photos
    assert "consume-open" in files and "consumePendingOpen" in files


def test_desktop_entries_are_valid_and_narrow():
    gallery = read("shell/config/org.nuxel.Photos.desktop")
    files = read("shell/config/org.nuxel.Files.desktop")
    for text in (gallery, files):
        assert text.startswith("[Desktop Entry]\n")
        assert "Exec=/usr/libexec/nuxel/nuxel-open-file --app " in text
        assert "TryExec=/usr/libexec/nuxel/nuxel-open-file" in text
        assert "Terminal=false" in text
    gallery_mimes = gallery.split("MimeType=", 1)[1].split("\n", 1)[0]
    assert "image/jpeg" in gallery_mimes and "video/mp4" in gallery_mimes
    assert "application/pdf" not in gallery_mimes and "inode/directory" not in gallery_mimes
    files_mimes = files.split("MimeType=", 1)[1].split("\n", 1)[0]
    assert files_mimes == "inode/directory;"
    assert "application/pdf" not in files_mimes


def test_package_manifest_and_deploy_paths_include_new_surface():
    pkg = read("tools/s10plus/a43/package-live.py")
    for item in ("pwa/nuxel-apps/photos", "pwa/nuxel-apps/files",
                 "services/nuxel-file-handlers/src/nuxel_file_handlers.py",
                 "services/nuxel-file-handlers/bin/nuxel-file-handlers",
                 "services/nuxel-file-handlers/bin/nuxel-open-file",
                 "shell/config/org.nuxel.Photos.desktop",
                 "shell/config/org.nuxel.Files.desktop"):
        assert item in pkg, item
    deploy = read("scripts/nuxel-deploy-live.py")
    assert "/usr/lib/nuxel/nuxel_file_handlers.py" in deploy
    assert "/usr/bin/nuxel-file-handlers" in deploy
    assert "/usr/libexec/nuxel/nuxel-open-file" in deploy
    assert "/usr/share/applications/" in deploy
    installer = read("scripts/nuxel-live-install.py")
    assert '"/usr/share/applications/"' in installer
    assert '"/usr/share/xdg-desktop-portal/"' in installer
    assert '"/usr/share/dbus-1/services/"' in installer
    assert '"/etc/xdg-desktop-portal/"' in installer


def test_image_build_installs_portal_files_and_desktop_entries():
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    assert "/usr/libexec/nuxel/nuxel-portal-chooser" in build
    assert "/usr/share/xdg-desktop-portal/portals/nuxel.portal" in build
    assert "/usr/bin/nuxel-file-handlers" in build
    assert "/usr/libexec/nuxel/nuxel-open-file" in build
    assert "org.nuxel.Photos.desktop" in build
    assert "org.nuxel.Files.desktop" in build


def test_packages_yaml_declares_portal_runtime():
    packages = read("images/config/packages.yml")
    for package in ("xdg-desktop-portal", "xdg-desktop-portal-gtk", "flatpak"):
        assert re.search(r"^\s*-\s*%s\s*$" % re.escape(package), packages, re.M), package


def test_settings_schema_and_mime_defaults_examples_are_real():
    module = read("services/nuxel-file-handlers/src/nuxel_file_handlers.py")
    assert '"schema_version": SCHEMA_VERSION' in module
    assert '"global_picker_policy"' in module
    assert '"app_picker_overrides"' in module
    assert '"mime_defaults"' in module
    assert "org.nuxel.Photos.desktop" in module
    assert "org.nuxel.Files.desktop" in module
    assert "inode/directory" in module
    assert "mimeapps.list" in module


def test_private_nuxel_portal_broker_is_untouched_by_filechooser():
    portal = read("services/nuxel-portal/src/portal.py")
    assert "FileChooser" not in portal
    assert "org.freedesktop.portal.FileChooser" not in portal
    chooser = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    assert "org.nuxel.Portal" in chooser
    assert "hardware-permission broker" in chooser


def test_network_manager_wrapper_is_registered_and_wraps_working_wifi():
    reg = json.loads(read("pwa/nuxel-common/app-registry.json"))
    ids = {a.get("id"): a for a in reg["apps"]}
    app = ids.get("org.nuxel.NetworkManager")
    assert app is not None
    assert app["url"] == "/pwa/nuxel-apps/network-manager/index.html"
    index = read("pwa/nuxel-apps/network-manager/index.html")
    js = read("pwa/nuxel-apps/network-manager/js/network-manager.js")
    assert "../settings/wifi-settings.js" in index
    assert "NuxelWifiSettings" in js and "dns-set" in js and "vpn-import" in js
    assert "zerotier-join" in js and "0cccb752f72ecf52" in index
    provider = read("services/nuxel-bridge/src/network_manager.py")
    assert "security_types=VncAuth" not in provider
    assert "zerotier_join" in provider and "set_private_dns" in provider


def test_remote_desktop_uses_standard_direct_lan_ports_and_password_vnc():
    ctl = read("services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl")
    wrapper = read("services/nuxel-remote-desktop/bin/nuxel-vnc-x11")
    rd = read("services/nuxel-bridge/src/remote_desktop.py")
    assert 'PORTS = {"vnc": 5900, "xrdp": 3389}' in ctl
    assert "vncpasswd" in ctl and "security_types=VncAuth" in ctl
    assert "SecurityTypes VncAuth" in wrapper
    assert "VNC_GEOMETRY_DEFAULT" in ctl and "1520x720" in ctl
    assert "must use landscape geometry" in wrapper
    assert "-geometry \"$GEOMETRY\"" in wrapper
    assert 'FIXED_PORTS = {"vnc": 5900, "xrdp": 3389}' in rd
    assert '"requires_ssh_tunnel": False' in rd


def test_single_canonical_ssh_banner():
    banner = read("services/nuxel-zsh/nuxel-banner.sh")
    zsh = read("services/nuxel-zsh/nuxel.zsh")
    assert "SSH_CONNECTION" in banner and "return 0" in banner
    assert "/etc/banner" in banner and "/etc/banner" in zsh
    assert "sshd's Banner /etc/banner is the only SSH banner" in zsh
    installer = read("scripts/nuxel-live-install.py")
    assert "99-nuxel-banner.sh" in installer and "LEGACY_REMOVE" in installer


def test_zerotier_tun_device_is_granted_without_world_write():
    conf = read("services/nuxel-s10/systemd/zerotier-one.service.d/10-nuxel-tun.conf")
    assert "ExecStartPre=+/bin/chgrp zerotier-one /dev/net/tun" in conf
    assert "ExecStartPre=+/bin/chmod 0660 /dev/net/tun" in conf
    assert "0666" not in conf
    pkg = read("tools/s10plus/a43/package-live.py")
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    assert "zerotier-one.service.d/10-nuxel-tun.conf" in pkg
    assert "zerotier-one.service.d/10-nuxel-tun.conf" in build
    assert 'install -d "$STAGE/etc/systemd/system/zerotier-one.service.d"' in build


def test_vnc_geometry_validation_is_landscape_only():
    ctl = read("services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl")
    wrapper = read("services/nuxel-remote-desktop/bin/nuxel-vnc-x11")
    assert 'VNC_GEOMETRY_DEFAULT = "1520x720"' in ctl
    assert "VNC geometry must be landscape" in ctl
    assert "VNC must use landscape geometry" in wrapper
    assert "1520x720" in wrapper
    assert "CURRENT_WLAN" in wrapper and "wlan0" in wrapper
    unit = read("services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service")
    assert "WantedBy=multi-user.target" in unit
    assert "WantedBy=graphical.target" not in unit


def test_rootfs_builder_creates_nuxel_before_any_group_membership_edit():
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    assert "useradd -m -s /bin/bash nuxel" in build
    # v0.8.1 release failure: usermod ran before useradd and exited 6.
    assert "usermod -aG inet nuxel" not in build
    assert '"nuxel" to gid 3003' in build or "nuxel" in build
