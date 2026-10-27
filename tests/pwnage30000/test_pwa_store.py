"""Offline unit tests for the PWA persistence layer (PWNAGE-30000).

These tests exercise the root-cause fix: calendar/notes/contacts/files saves
used to route to D-Bus methods that did not exist.  pwa_store.py now owns them
in the HTTP bridge with atomic file-backed writes and traversal-safe file ops.
No real user data is touched (temp dir via NUXEL_APP_DATA_DIR).
"""
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'nuxel-bridge', 'src'))
import pwa_store  # noqa: E402


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv('NUXEL_APP_DATA_DIR', str(tmp_path))
    return pwa_store.PwaStore()


def test_calendar_roundtrip(store):
    events = [{"id": "evt-1", "title": "Standup", "date": "2026-10-27", "startTime": "09:00"}]
    assert store.caldav_put(events)['success'] is True
    got = store.caldav_list()
    assert got['success'] is True
    assert got['events'] == events


def test_calendar_rejects_non_list(store):
    with pytest.raises(pwa_store.StoreError):
        store.caldav_put({"not": "a list"})


def test_storage_key_roundtrip(store):
    assert store.storage_write('nuxel-notes', [{"id": "n1", "title": "hi"}])['success'] is True
    got = store.storage_read('nuxel-notes')
    assert got['success'] is True
    assert got['data'][0]['title'] == 'hi'


def test_storage_key_invalid(store):
    with pytest.raises(pwa_store.StoreError):
        store.storage_write('../bad', {})


def test_contacts_crud_and_dedup(store):
    r1 = store.contacts_upsert({"id": "c1", "name": "Ada", "phone": "1"})
    assert r1['count'] == 1
    r2 = store.contacts_upsert({"id": "c1", "name": "Ada Lovelace", "phone": "2"})
    assert r2['count'] == 1
    assert store.contacts_list()['contacts'][0]['name'] == 'Ada Lovelace'
    assert store.contacts_delete('c1')['success'] is True
    assert store.contacts_list()['contacts'] == []


def test_contacts_requires_name(store):
    with pytest.raises(pwa_store.StoreError):
        store.contacts_upsert({"id": "c1", "name": ""})


def test_file_manager_roundtrip(store):
    assert store.storage_mkdir('/docs')['success'] is True
    assert store.storage_list_dir('/')['count'] == 1
    assert store.storage_rename('/docs', '/notes')['success'] is True
    assert store.storage_delete('/notes')['success'] is True
    assert store.storage_list_dir('/')['entries'] == []


def test_file_manager_traversal_refused(store):
    with pytest.raises(pwa_store.StoreError):
        store._fs_path('../../etc/passwd')


def test_file_manager_cannot_delete_root(store):
    assert store.storage_delete('/')['success'] is False


def test_archive_create_and_extract(store):
    store.storage_mkdir('/src')
    src = store._fs_path('/src/hello.txt')
    src.write_text('hello', encoding='utf-8')
    assert store.storage_archive_create(['/src'], '/src.zip')['success'] is True
    assert zipfile.is_zipfile(store._fs_path('/src.zip'))
    assert store.storage_archive_extract('/src.zip', '/out')['success'] is True
    assert (store.files_root / 'out' / 'src' / 'hello.txt').read_text() == 'hello'


def test_archive_traversal_refused(store):
    store.files_root.mkdir(parents=True, exist_ok=True)
    arc = store._fs_path('/evil.zip')
    with zipfile.ZipFile(arc, 'w') as zf:
        zf.writestr('../evil.txt', 'x')
    res = store.storage_archive_extract('/evil.zip', '/out')
    assert res['success'] is False
    assert res.get('error_code') == 'UNSAFE_ARCHIVE'


def test_haptics_unavailable_without_fifo(store, tmp_path, monkeypatch):
    monkeypatch.setenv('NUXEL_HAPTICS_FIFO', str(tmp_path / 'nope'))
    res = store.haptics_pulse('tap')
    assert res['success'] is False
    assert res.get('software_path') is False


def test_haptics_dispatches_to_fifo(store, tmp_path, monkeypatch):
    fifo = tmp_path / 'haptics.cmd'
    os.mkfifo(fifo)
    monkeypatch.setenv('NUXEL_HAPTICS_FIFO', str(fifo))
    # Read one line from a reader thread so the O_NONBLOCK write has a consumer.
    import threading
    seen = {}
    def reader():
        with open(fifo, 'rb') as fh:
            seen['cmd'] = fh.read().decode('ascii', 'ignore').strip()
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    res = store.haptics_pulse('navigation')
    t.join(timeout=2)
    assert res['success'] is True
    assert seen.get('cmd') == 'navigation'
