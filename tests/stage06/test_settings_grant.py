import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('migration', Path(__file__).resolve().parents[2] / 'tools/s10plus/s5000ap-05/scripts/migrate_settings_network_grant.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_legacy_grant_becomes_persistent_and_preserves_others():
    doc = {'network:manage': dict(module.LEGACY), 'location:manage': {'duration': 'deny'}}
    assert module.migrate(doc)
    assert doc['network:manage'] == module.CURRENT
    assert doc['location:manage'] == {'duration': 'deny'}
    assert not module.migrate(doc)


def test_owner_grants_and_denials_are_never_migrated():
    for grant in ({'duration': 'deny'}, {'duration': 'session', 'source': 'owner'},
                  dict(module.LEGACY, session_id='owner-session'), {'duration': 'always'}):
        doc = {'network:manage': grant}
        assert not module.migrate(doc)
        assert doc['network:manage'] is grant
