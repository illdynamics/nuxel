"""Focused PWNAGE-97000 tests for the shared File Handler policy."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "services/nuxel-file-handlers/src/nuxel_file_handlers.py"
spec = importlib.util.spec_from_file_location("nuxel_file_handlers", MODULE_PATH)
fh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fh
assert spec.loader is not None
spec.loader.exec_module(fh)


def _desktop(directory: Path, name: str, *, mimes=(), icon="", flatpak="") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + ".desktop")
    lines = [
        "[Desktop Entry]", "Type=Application", "Name=" + name,
        "Exec=/usr/bin/true %U", "Terminal=false",
    ]
    if mimes:
        lines.append("MimeType=" + ";".join(mimes) + ";")
    if icon:
        lines.append("Icon=" + icon)
    if flatpak:
        lines.append("X-Flatpak=" + flatpak)
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".config" / "nuxel").mkdir(parents=True)
    desktop = h / ".local/share/applications"
    _desktop(desktop, "org.nuxel.Photos", mimes=["image/jpeg", "image/png", "video/mp4"],
             icon="photos")
    _desktop(desktop, "org.nuxel.Files", mimes=["inode/directory"], icon="files")
    _desktop(desktop, "org.example.Image", mimes=["image/jpeg"], icon="image")
    _desktop(desktop, "org.ferdium.Ferdium", mimes=["x-scheme-handler/ferdium"],
             flatpak="org.ferdium.Ferdium")
    _desktop(desktop, "org.signal.Signal", mimes=["x-scheme-handler/sgnl"],
             flatpak="org.signal.Signal")
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("NUXEL_SESSION_HOME", str(h))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(h / ".config"))
    monkeypatch.setenv("XDG_CONFIG_DIRS", str(tmp_path / "system-config"))
    monkeypatch.setenv("NUXEL_DESKTOP_DIRS", str(desktop))
    monkeypatch.setenv("NUXEL_FILE_HANDLERS_CONFIG", str(h / ".config/nuxel/file-handlers.json"))
    monkeypatch.setenv("NUXEL_MIMEAPPS_PATH", str(h / ".config/mimeapps.list"))
    monkeypatch.delenv("NUXEL_CHOOSER_ROOTS", raising=False)
    return h


def test_schema_defaults_and_policy_precedence(home):
    doc = fh.normalize_settings({})
    assert doc["schema_version"] == 1
    assert doc["global_picker_policy"] == "ask"
    assert fh.resolve_policy(doc, "unknown.app") == "ask"
    doc["global_picker_policy"] = "files"
    assert fh.resolve_policy(doc, "unknown.app") == "files"
    doc["app_picker_overrides"]["org.signal.Signal"] = "gallery"
    assert fh.resolve_policy(doc, "org.signal.Signal") == "gallery"
    doc["app_picker_overrides"]["org.signal.Signal"] = "inherit"
    assert fh.resolve_policy(doc, "org.signal.Signal") == "files"


def test_invalid_values_are_normalized_not_trusted(home):
    doc = fh.normalize_settings({
        "schema_version": "junk",
        "global_picker_policy": "host-filesystem",
        "app_picker_overrides": {"../escape": "files", "org.ok.App": "root"},
        "mime_defaults": {"not-a-mime": "x.desktop", "image/png": "../../evil.desktop"},
    })
    assert doc["global_picker_policy"] == "ask"
    assert "../escape" not in doc["app_picker_overrides"]
    assert "org.ok.App" not in doc["app_picker_overrides"]
    assert "not-a-mime" not in doc["mime_defaults"]
    assert "image/png" not in doc["mime_defaults"]


def test_initial_source_uses_filters_and_policy(home):
    doc = fh.normalize_settings({})
    assert fh.initial_source(doc, "app", [(1, "image/*")], "open") == "gallery"
    assert fh.initial_source(doc, "app", [(1, "application/pdf")], "open") == "files"
    assert fh.initial_source(doc, "app", [], "folder") == "files"
    doc["global_picker_policy"] = "files"
    assert fh.initial_source(doc, "app", [(1, "image/*")], "open") == "files"
    doc["global_picker_policy"] = "gallery"
    assert fh.initial_source(doc, "app", [(1, "application/pdf")], "open") == "gallery"


def test_filter_parsing_and_media_detection(home):
    options = {"filters": [["Images", [[1, "image/*"], [0, "*.png"]]],
                           ["Docs", [[1, "application/pdf"]]]]}
    rules = fh.filter_rules(options)
    assert (1, "image/*") in rules and (0, "*.png") in rules
    assert fh.filter_rules_are_media([(0, "*.jpg;*.png")])
    assert fh.filter_rules_are_media([(1, "video/mp4")])
    assert not fh.filter_rules_are_media([(1, "*/*")])
    assert not fh.filter_rules_are_media([(1, "application/pdf")])
    assert fh.path_matches("/home/u/Gallery/a b (émoji 📷).PNG", [(1, "image/*")])
    assert fh.path_matches("/home/u/Gallery/a.webp", [(0, "*.webp")])
    assert not fh.path_matches("/home/u/notes.txt", [(1, "image/*")])


def test_uri_encoding_roundtrip_special_names(tmp_path):
    path = tmp_path / "space and unicode café 📷 #1 100%.png"
    path.write_bytes(b"x")
    uri = fh.file_uri(str(path))
    assert uri.startswith("file://")
    assert " " not in uri.split("file://", 1)[1]
    assert fh.decode_file_uri(uri) == str(path)


def test_canonical_selection_blocks_traversal_and_symlink_escape(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    safe = home / "Gallery"
    safe.mkdir()
    good = safe / "good.png"
    good.write_bytes(b"png")
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret")
    link = safe / "escape"
    link.symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("NUXEL_CHOOSER_ROOTS", str(home))
    assert fh.canonical_selection(str(good), roots=[str(home)]) == str(good.resolve())
    with pytest.raises(fh.FileHandlerError):
        fh.canonical_selection(str(home / ".." / "outside" / "secret.txt"), roots=[str(home)])
    with pytest.raises(fh.FileHandlerError):
        fh.canonical_selection(str(link / "secret.txt"), roots=[str(home)])
    with pytest.raises(fh.FileHandlerError):
        fh.canonical_selection(str(outside / "secret.txt"), roots=[str(home)])


def test_save_target_validation_and_collision(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("NUXEL_CHOOSER_ROOTS", str(home))
    target = fh.canonical_selection(str(home / "new file.txt"), roots=[str(home)],
                                    must_exist=False, follow_final=False)
    assert target == str(home / "new file.txt")
    with pytest.raises(fh.FileHandlerError):
        fh.canonical_selection(str(home / ".." / "escape.txt"), roots=[str(home)],
                               must_exist=False, follow_final=False)


def test_mimeapps_writer_preserves_unrelated_entries_and_comments(home):
    original = """# owner written\n[Default Applications]\nimage/png=old.desktop;other.desktop\napplication/pdf=paper.desktop\n\n[Added Associations]\nimage/png=old.desktop;\n\n[Removed Associations]\nimage/png=org.nuxel.Photos.desktop;\ntext/plain=other.desktop;\n"""
    fh.write_user_mimeapps(original, str(home))
    fh.set_mime_default("image/png", "org.nuxel.Photos.desktop", str(home))
    text = Path(fh.mimeapps_path(str(home))).read_text()
    assert "# owner written" in text
    assert "application/pdf=paper.desktop" in text
    assert "image/png=org.nuxel.Photos.desktop" in text
    defaults = text.split("[Default Applications]", 1)[1].split("[Added Associations]", 1)[0]
    assert "image/png=old.desktop" not in defaults
    assert "[Added Associations]" in text and "image/png=old.desktop" in text
    assert "text/plain=other.desktop;" in text
    assert "image/png=org.nuxel.Photos.desktop" not in text.split("[Removed Associations]", 1)[1]


def test_mime_default_rejects_unassociated_handler(home):
    with pytest.raises(fh.FileHandlerError):
        fh.set_mime_default("image/png", "org.nuxel.Files.desktop", str(home))
    with pytest.raises(fh.FileHandlerError):
        fh.set_mime_default("image/png", "missing.desktop", str(home))


def test_effective_mime_default_precedence(home, tmp_path):
    system = tmp_path / "system-config"
    system.mkdir()
    (system / "mimeapps.list").write_text("[Default Applications]\nimage/png=system.desktop\n")
    fh.write_user_mimeapps("[Default Applications]\nimage/png=user.desktop\n", str(home))
    assert fh.effective_mime_defaults(str(home))["image/png"] == "user.desktop"


def test_desktop_catalog_uses_stable_flatpak_app_id(home):
    catalog = fh.desktop_catalog(str(home))
    assert catalog["org.nuxel.Photos.desktop"].package_format == "native"
    assert catalog["org.ferdium.Ferdium.desktop"].app_id == "org.ferdium.Ferdium"
    assert catalog["org.signal.Signal.desktop"].flatpak_id == "org.signal.Signal"


def test_app_inventory_deduplicates_stable_ids(home, tmp_path, monkeypatch):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"apps": [
        {"id": "org.nuxel.Photos", "name": "Gallery", "type": "pwa", "status": "installed"},
        {"id": "org.nuxel.Files", "name": "Files", "type": "pwa", "status": "installed"},
        {"id": "org.ferdium.Ferdium", "name": "Ferdium old name", "type": "native",
         "status": "unsupported"},
    ]}))
    monkeypatch.setenv("NUXEL_APP_REGISTRY", str(registry))
    apps = fh.app_inventory(str(home))
    ids = [a["id"] for a in apps]
    assert len(ids) == len(set(ids))
    by_id = {a["id"]: a for a in apps}
    assert by_id["org.ferdium.Ferdium"]["installed"] is True
    assert by_id["org.ferdium.Ferdium"]["package_format"] == "flatpak"
    assert by_id["org.nuxel.Photos"]["package_format"] == "pwa"


def test_settings_roundtrip_is_atomic_and_private(home):
    doc = fh.normalize_settings({"global_picker_policy": "gallery",
                                 "app_picker_overrides": {"org.signal.Signal": "files"}})
    saved = fh.save_settings(doc)
    assert saved["global_picker_policy"] == "gallery"
    assert fh.load_settings()["app_picker_overrides"]["org.signal.Signal"] == "files"
    mode = os.stat(fh.settings_path()).st_mode & 0o777
    assert mode == 0o600


def test_default_handlers_do_not_override_existing_choice(home):
    fh.write_user_mimeapps("[Default Applications]\nimage/png=custom.desktop\n", str(home))
    fh.ensure_default_handlers(str(home))
    text = Path(fh.mimeapps_path(str(home))).read_text()
    assert "image/png=custom.desktop" in text
    assert "inode/directory=org.nuxel.Files.desktop" in text


def test_test_picker_output_parser_accepts_wrapped_and_last_line_json():
    good = {"success": True, "response": 0, "uris": ["file:///tmp/a"]}
    wrapped = "noise\n" + json.dumps(good) + "\n"
    assert fh.parse_test_picker_output(wrapped, "", 0)["success"] is True
    assert fh.parse_test_picker_output("banner\n{}\n" + json.dumps(good), "", 0)["uris"] == good["uris"]
    failed = fh.parse_test_picker_output("not json", "boom", 7)
    assert failed["success"] is False
    assert failed["rc"] == 7 and "boom" in failed["detail"]


def test_network_manager_vpn_plugin_candidates_include_fedora_paths():
    nm_path = ROOT / "services/nuxel-bridge/src/network_manager.py"
    src = nm_path.read_text()
    assert "/usr/lib/NetworkManager/VPN/nm-%s-service.name" in src
    assert "/usr/lib64/NetworkManager/libnm-vpn-plugin-%s.so" in src
    assert "libnm-vpn-plugin-%s*" in src
