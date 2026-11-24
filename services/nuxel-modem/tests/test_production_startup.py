"""Offline startup safety contract. No modem endpoints are opened."""
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import hashlib
import json
import stat
import unittest
from unittest.mock import Mock, patch

path = Path(__file__).resolve().parents[1] / 'bin/nuxel-cpbootd-production'
loader = importlib.machinery.SourceFileLoader('production', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
production = importlib.util.module_from_spec(spec)
loader.exec_module(production)


def config():
    return dict(loader_sha256='a'*64, firmware='/dev/sda16', firmware_sha256='b'*64,
                manifest='/etc/nuxel/modem/manifest', manifest_sha256='c'*64,
                nv_image='/mnt/vendor/efs/nv_data.bin',
                nv_md5='/mnt/vendor/efs/nv_data.bin.md5', deadline_ms=60000)


class StartupTests(unittest.TestCase):
    def test_preflight_integrity_and_nv_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = config()
            for key, data in [('firmware', b'firmware'), ('manifest', b'manifest'),
                              ('nv_image', bytes(1048576))]:
                artifact = root / key
                artifact.write_bytes(data)
                candidate[key] = str(artifact)
                if key != 'nv_image':
                    candidate[key + '_sha256'] = hashlib.sha256(data).hexdigest()
            binary = root / 'loader'
            binary.write_bytes(b'loader')
            candidate['loader_sha256'] = hashlib.sha256(b'loader').hexdigest()
            sidecar = root / 'nv.md5'
            sidecar.write_text(hashlib.md5(bytes(1048576) + b'Samsung_Android_RIL').hexdigest())
            candidate['nv_md5'] = str(sidecar)
            cfg = root / 'config.json'
            cfg.write_text(json.dumps(candidate))
            real_stat = production.os.stat
            def endpoint_stat(path, **kwargs):
                if path == production.NODE:
                    return type('Info', (), {'st_mode': stat.S_IFCHR})()
                return real_stat(path, **kwargs)
            # Temp inputs are allowed only in this offline fixture. Root-owned
            # artifact checks are tested separately; no production bypass flag.
            with patch.object(production, 'regular', side_effect=lambda p, **kw: open(p, 'rb')), \
                 patch.object(production, 'validate', side_effect=lambda c: c), \
                 patch.object(production, 'LOADER', str(binary)), \
                 patch.object(production.os, 'stat', side_effect=endpoint_stat):
                self.assertEqual(production.preflight(str(cfg)), candidate)
                for artifact in (binary, root / 'manifest', root / 'firmware', sidecar, root / 'nv_image'):
                    original = artifact.read_bytes()
                    artifact.write_bytes(b'corrupt')
                    with self.subTest(artifact=artifact.name):
                        with self.assertRaises(ValueError):
                            production.preflight(str(cfg))
                    artifact.write_bytes(original)

    def test_regular_rejects_symlinks_and_writable_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / 'input'
            artifact.write_bytes(b'input')
            artifact.chmod(0o666)
            with self.assertRaises(ValueError):
                production.regular(str(artifact))
            link = Path(td) / 'symlink'
            link.symlink_to(artifact)
            with self.assertRaises(OSError):
                production.regular(str(link))

    def test_invalid_configuration(self):
        for key, value in [('deadline_ms', True), ('deadline_ms', 90001),
                           ('deadline_ms', 0), ('manifest_sha256', 'fake'),
                           ('nv_image', '/tmp/nv'), ('nv_image', '/run/nv'),
                           ('firmware', 'relative'), ('manifest', '/etc/../tmp/a')]:
            with self.subTest(key=key, value=value):
                candidate = config()
                candidate[key] = value
                with self.assertRaises(ValueError):
                    production.validate(candidate)
        candidate = config()
        candidate['extra'] = 'shell command'
        with self.assertRaises(ValueError):
            production.validate(candidate)
        self.assertEqual(production.validate(config()), config())

    def test_online_never_invokes_loader(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            state.write_text('ONLINE\n')
            run = Mock()
            production.start(config(), state, run)
            run.assert_not_called()

    def test_unknown_and_crashed_states_never_reset(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            for value in ('BOOTING', 'CRASH_EXIT', '', 'UNKNOWN'):
                state.write_text(value)
                run = Mock()
                with self.assertRaises(ValueError):
                    production.start(config(), state, run)
                run.assert_not_called()

    def test_offline_single_boot_and_nv_arguments(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            state.write_text('OFFLINE')
            run = Mock(side_effect=lambda *a, **kw: state.write_text('ONLINE'))
            with patch.object(production.Path, 'glob', return_value=[]):
                production.start(config(), state, run)
            run.assert_called_once()
            argv = run.call_args.args[0]
            self.assertIn('--nv-image', argv)
            self.assertIn('--nv-md5', argv)
            self.assertEqual(run.call_args.kwargs['timeout'], 65)

    def test_existing_radio_owner_prevents_boot(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            state.write_text('OFFLINE')
            directory = Mock()
            directory.iterdir.return_value = [Path(td) / 'fd']
            run = Mock()
            with patch.object(production.Path, 'glob', return_value=[directory]), \
                 patch.object(production.os, 'readlink', return_value='/dev/umts_ipc0'):
                with self.assertRaisesRegex(ValueError, 'already owned'):
                    production.start(config(), state, run)
            run.assert_not_called()

    def test_loader_success_without_online_fails(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            state.write_text('OFFLINE')
            run = Mock()
            with patch.object(production.Path, 'glob', return_value=[]):
                with self.assertRaises(ValueError):
                    production.start(config(), state, run)
            run.assert_called_once()

    def test_loader_failure_does_not_retry(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / 'state'
            state.write_text('OFFLINE')
            run = Mock(side_effect=production.subprocess.TimeoutExpired('loader', 65))
            with patch.object(production.Path, 'glob', return_value=[]):
                with self.assertRaises(production.subprocess.TimeoutExpired):
                    production.start(config(), state, run)
            run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
