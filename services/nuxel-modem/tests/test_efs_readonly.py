import importlib.machinery
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest

path = Path(__file__).resolve().parents[1] / 'bin/nuxel-efs-readonly'
loader = importlib.machinery.SourceFileLoader('efs_readonly', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
GOOD = {'source': '/dev/sda3', 'options': 'ro,nosuid,nodev,noexec,norecovery'}


def test_existing_readonly_mount_is_untouched():
    with patch.object(module, 'inspect', return_value=GOOD), patch.object(module.subprocess, 'run') as run:
        module.main()
        run.assert_not_called()


@pytest.mark.parametrize('entry', [dict(GOOD, source='/dev/sda4'),
                                   dict(GOOD, options='rw,nosuid,nodev,noexec,norecovery'),
                                   dict(GOOD, options='ro,nosuid,nodev,noexec')])
def test_wrong_mount_refused_without_remount(entry):
    with patch.object(module, 'inspect', return_value=entry), patch.object(module.subprocess, 'run') as run:
        with pytest.raises(RuntimeError):
            module.main()
        run.assert_not_called()


def test_missing_mount_is_readonly_without_journal_replay():
    with patch.object(module, 'inspect', side_effect=[None, GOOD]), patch.object(module.Path, 'mkdir'), patch.object(module.subprocess, 'run') as run:
        module.main()
        run.assert_called_once_with(['mount', '-t', 'ext4', '-o', 'ro,noload,nosuid,nodev,noexec',
                                     '/dev/sda3', '/mnt/vendor/efs'], check=True, timeout=15)
