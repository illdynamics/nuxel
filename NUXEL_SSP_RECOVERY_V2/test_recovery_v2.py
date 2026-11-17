import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

import ssp_stock_collect as collect
import ssp_trial_prepare as trial

class FakeReader:
    def __init__(self, files):self.files=files;self.requested=[]
    def fetch(self, path):
        self.requested.append(path)
        return (self.files[path],'/vendor/'+path) if path in self.files else (None,None)

class Tests(unittest.TestCase):
    def test_no_disallowed_adb_paths(self):
        for name in ('../../efs','/dev/block/sda14','vendor/../../efs','data/user/0','vendor/lib64/a;touch /tmp/oops'):
            with self.assertRaises(ValueError): collect.remote_candidates(name)
        self.assertIn('/system_root/system/bin/linker64',collect.remote_candidates('system/bin/linker64'))
        self.assertIn('/system/vendor/lib64/liblog.so',collect.remote_candidates('vendor/lib64/liblog.so'))
    def test_adb_default_no_calls(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(collect.main(['--repo-root',t,'--output',str(Path(t)/'ignored')]),0)
    def test_matching_anchor_collection(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo'; stock=Path(t)/'stock'
            for name in collect.ANCHORS.values():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'AARCH64_VENDOR')
            files={p:b'AARCH64_VENDOR' for p in collect.ANCHORS}
            files['system/bin/linker64']=b'AARCH64_LINKER'
            files['system/lib64/liblog.so']=b'AARCH64_LIB'
            files['vendor/lib64/android.frameworks.schedulerservice@1.0.so']=b'AARCH64_LIB'
            files['system/build.prop']=b'ro.build.fingerprint=samsung/beyond2lte/test:10/X:abc/user/release-keys\n'
            def mock_meta(b):
                return {'class':64,'machine':183,'needed':['liblog.so', 'android.frameworks.schedulerservice@1.0.so'] if b==b'AARCH64_VENDOR' else []}
            result=collect.collect(root,stock,FakeReader(files),mock_meta)
            self.assertEqual(result['status'],'STATIC_COLLECTION_ONLY')
            self.assertIn('system/lib64/liblog.so',result['files'])
            self.assertIn('vendor/lib64/android.frameworks.schedulerservice@1.0.so',result['files'])
            self.assertEqual(result['device_writes'],0)
            self.assertTrue((stock/'ssp-stock-collection.json').is_file())
            with self.assertRaises(RuntimeError):collect.collect(root,stock,FakeReader(files),mock_meta)
    def test_refuse_mismatched_vendor(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'repo'
            for name in collect.ANCHORS.values():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'ORIGINAL')
            files={p:b'NEW_BUILD' for p in collect.ANCHORS}
            files['system/bin/linker64']=b'LINKER'
            with self.assertRaisesRegex(RuntimeError,'MISMATCH'):
                collect.collect(root,Path(t)/'stock',FakeReader(files),lambda b:{'class':64,'machine':183,'needed':[]})
            self.assertFalse((Path(t)/'stock').exists())
    def test_safe_conf_dedup_and_no_hardware(self):
        original=b'GpioNPowerPath=/sys/class/sec/sensorhub/mcu_power\nLheMaxMcuResetTries=4\nLheMaxMcuResetTries=3\nLhePatch=/dev/bbd_patch\n'
        config=trial.safe_conf(original).decode()
        self.assertEqual(config.count('LheMaxMcuResetTries='),1)
        self.assertIn('LheMaxMcuResetTries=0',config)
        self.assertIn('LhePatch=/no-hardware/bbd-patch',config)
        self.assertNotIn('GpioNPowerPath=/sys',config)
    def test_stage_preparation_and_manifest_tamper_detection(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for name in trial.REQUIRED_FILES:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(b'LhePatch=/dev/bbd_patch\n' if name.endswith('lhd.conf') else b'ELF')
            r=trial.prepare(root)
            self.assertEqual(r['status'],'OFFLINE_SANDBOX_PREFLIGHT_COMPLETE')
            self.assertEqual(r['manifest_mismatches'],[])
            self.assertTrue((root/'sha256-manifest.json').is_file())
            (root/'vendor/bin/hw/lhd').write_bytes(b'TAMPER')
            self.assertIn('vendor/bin/hw/lhd',trial.preflight(root)['manifest_mismatches'])
    def test_reject_symlinks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'vendor').mkdir();(root/'vendor/link').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError,'symlink'):
                trial.walk_files(root)

if __name__ == '__main__':unittest.main()

# Dedicated read-only snapshot parser checks; no SSH in the test suite.
import ssp_live_snapshot as snapshot
class SnapshotTests(unittest.TestCase):
    def test_nonfinite_vectors_are_not_sensor_evidence(self):
        for value in ('nan,0,0', '0,inf,0', '0,0,-inf', '1e999,0,0'):
            self.assertIsNone(snapshot.vector(value))
        self.assertEqual(snapshot.evaluate([{'accelerometer':'nan,0,0'}])['accelerometer']['status'], 'NOT_EXPOSED')

    def test_identity_and_timestamp_capture_without_hardware(self):
        with tempfile.TemporaryDirectory() as t:
            output=Path(t)/'samples.json'
            key=Path(t)/'key with spaces'
            with patch.object(snapshot.subprocess,'run',return_value=subprocess.CompletedProcess(
                    [],0,b'KERNEL=test\nFIELD:accelerometer=0,0,0\nFIELD:gyroscope=0,0,0\n',b'')) as run:
                self.assertEqual(snapshot.main(['--host','10.11.12.99','--identity-file',str(key),
                    '--output',str(output),'--samples','1','--capture-readonly']),0)
            cmd=run.call_args.args[0]
            self.assertEqual(cmd[cmd.index('-i')+1],str(key))
            self.assertEqual(cmd[-1],snapshot.COMMAND)
            row=json.loads(output.read_text())['samples'][0]
            self.assertLessEqual(row['started_utc'],row['completed_utc'])
            self.assertNotIn(str(key),output.read_text())

    def test_zero_samples_not_a_success(self):
        rows=[{'accelerometer':'0,0,0','gyroscope':'0,0,0'} for _ in range(3)]
        r=snapshot.evaluate(rows)
        self.assertEqual(r['accelerometer']['status'],'ALL_ZERO')
        self.assertFalse(r['real_motion_verified'])
    def test_changed_vectors_require_physical_confirmation(self):
        rows=[{'accelerometer':'0,0,9800','gyroscope':'1,2,3'},
              {'accelerometer':'0,9800,0','gyroscope':'10,20,30'}]
        r=snapshot.evaluate(rows)
        self.assertEqual(r['gyroscope']['status'],'CHANGING_SAMPLES')
        self.assertFalse(r['real_motion_verified'])
