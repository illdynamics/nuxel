import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACK = Path(__file__).resolve().parents[1]
SCRIPT = PACK / "scripts"
TOOLS = PACK / "tools"

MOCK_ADB = r'''#!/bin/sh
[ "$1" = "-s" ] && shift 2
cmd="$1"; shift || true
sub="$*"
case "$cmd" in
 devices) printf 'List of devices attached\nRTEST1234567\trecovery\n';;
 get-serialno) printf 'RTEST1234567\n';;
 shell|exec-out)
  case "$sub" in
   *'blockdev --getsize64'*) printf '10485760\n';;
   *'/proc/last_kmsg'*)
      case "$cmd:$sub" in *'exec-out:'*) printf 'Kernel panic - not syncing: VFS: Unable to mount root fs\n';; esac;;
   *'/sys/fs/pstore/console-ramoops-0'*) printf 'Kernel panic - not syncing: simulated\n';;
   *'dd if='*) printf '%2048s' '';;
   *'/sys/fs/pstore/*'*) printf '/sys/fs/pstore/console-ramoops-0\n';;
   *'echo nuxel-adb-ok'*) printf 'nuxel-adb-ok\n';;
   *'cat /proc/partitions'*) printf '8 14 56320 sda14\n';;
   *) printf 'TWRP mocked recovery log\n';;
  esac;;
 *) exit 1;;
esac
'''


class TestPack(unittest.TestCase):
    def test_shell_syntax(self):
        for script in sorted(list(SCRIPT.glob('*.sh')) + list(TOOLS.glob('*.sh'))):
            with self.subTest(script=script.name):
                cp = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, cp.stderr)

    def test_triage_previous_boot_classification(self):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('triage', TOOLS / 'triage.py')
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'pstore').mkdir()
            (root/'recovery').mkdir()
            (root/'pstore'/'console-ramoops-0').write_text('Kernel panic - not syncing: unable to mount\n')
            (root/'recovery'/'current-recovery-dmesg.txt').write_text('Kernel panic simulated recovery\n')
            result = module.triage(root)
            self.assertEqual(result['status'], 'EVIDENCE_CAPTURED_NEEDS_REVIEW')
            self.assertTrue(any(m['source']=='previous_boot' for m in result['matches']))
            self.assertTrue(any(m['source']=='current_recovery_or_host' for m in result['matches']))
            self.assertTrue((root/'TRIAGE.md').exists())

    def test_triage_no_pstore_not_success(self):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('triage_2', TOOLS / 'triage.py')
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'recovery.txt').write_text('recovery is running\n')
            result = module.triage(root)
            self.assertEqual(result['status'], 'NO_PREVIOUS_BOOT_LOGS_AVAILABLE')

    def test_full_collection_with_fake_adb(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            mock = d/'adb'
            mock.write_text(MOCK_ADB)
            mock.chmod(0o755)
            dest = d/'capture'
            env = os.environ.copy()
            env['PATH'] = f'{d}:' + env['PATH']
            env['NUXEL_OUT'] = str(dest)
            cp = subprocess.run(['bash', str(SCRIPT/'12-full-diagnostics.sh')],
                                capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(cp.returncode, 0, cp.stdout+'\n'+cp.stderr)
            self.assertTrue((dest/'previous-boot/last_kmsg.txt').exists())
            self.assertTrue((dest/'pstore/console-ramoops-0').exists())
            self.assertTrue((dest/'device/proc-partitions.txt').exists())
            self.assertTrue((dest/'TRIAGE.md').exists())
            self.assertIn('kernel_panic', (dest/'TRIAGE.md').read_text())

    def test_readback_is_readonly_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            mock = d/'adb'
            mock.write_text(MOCK_ADB)
            mock.chmod(0o755)
            boot = d/'boot.img'
            boot.write_bytes(b' '*2048)
            env = os.environ.copy()
            env['PATH'] = f'{d}:' + env['PATH']
            env['NUXEL_OUT'] = str(d/'capture')
            cp = subprocess.run(['bash', str(SCRIPT/'13-verify-partition-readback.sh'), '--boot', str(boot)],
                                capture_output=True, text=True, env=env, timeout=30)
            self.assertEqual(cp.returncode, 0, cp.stdout+'\n'+cp.stderr)
            self.assertIn('READBACK MATCH', cp.stdout)

    def test_pstore_listing_alone_is_not_boot_evidence(self):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('triage_3', TOOLS / 'triage.py')
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'pstore').mkdir()
            (root/'pstore'/'listing.txt').write_text('total 0\n')
            (root/'pstore'/'NO-PSTORE-FILES.txt').write_text('No pstore data\n')
            result = module.triage(root)
            self.assertEqual(result['status'], 'NO_PREVIOUS_BOOT_LOGS_AVAILABLE')

    def test_share_bundle_masks_serial(self):
        with tempfile.TemporaryDirectory() as d:
            from zipfile import ZipFile
            p = Path(d)
            (p/'capture').mkdir()
            (p/'capture'/'cmdline.txt').write_text('androidboot.serialno=R58M75KDB2X\nIP 192.168.1.3\n')
            (p/'capture'/'secret.img').write_bytes(b'unsafe')
            dest = p/'share.zip'
            cp = subprocess.run([sys.executable, str(TOOLS/'create_share_bundle.py'), str(p/'capture'), str(dest)],
                                capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            with ZipFile(dest) as z:
                self.assertNotIn('secret.img', z.namelist())
                t = z.read('cmdline.txt').decode()
                self.assertNotIn('R58M75KDB2X', t)
                self.assertNotIn('192.168.1.3', t)

if __name__ == '__main__':
    unittest.main()
