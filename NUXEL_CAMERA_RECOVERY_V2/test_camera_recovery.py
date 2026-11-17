"""Host-only tests: no device or network access."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from camera_firmware_audit import CAMERA_FILES, manifest_hashes, audit, sha256_file
from fetch_pinned_camera_reference import fetch_one

def make_manifest(expected):
    lines=["device: s10plus","firmware_files:","  camera_isp:"]
    for name in CAMERA_FILES:
        lines+=['    - source_path: "vendor/firmware/'+name+'"',
                '      required: false',
                '      checksum: "'+expected[name]+'"']
    lines+=["  modem_dsp:"]
    return "\n".join(lines)+"\n"

class CameraAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'firmware'; self.source.mkdir()
        self.expected={}
        for name in CAMERA_FILES:
            b=("camera_"+name).encode()
            (self.source/name).write_bytes(b)
            self.expected[name]=hashlib.sha256(b).hexdigest()
        self.manifest=self.root/'manifest.yml'
        self.manifest.write_text(make_manifest(self.expected))
    def test_manifest(self):
        self.assertEqual(manifest_hashes(self.manifest),self.expected)
    def test_all_expected(self):
        rows=audit(self.manifest,[self.source])
        self.assertEqual(len(rows['files']),8)
        self.assertTrue(all(x['candidates'][0]['manifest_match'] for x in rows['files'].values()))
    def test_wrong_hash(self):
        (self.source/'fimc_is_lib.bin').write_bytes(b"different")
        rows=audit(self.manifest,[self.source])
        self.assertFalse(rows['files']['fimc_is_lib.bin']['candidates'][0]['manifest_match'])
    def test_missing_is_not_success(self):
        (self.source/'fimc_is_lib.bin').unlink()
        self.assertFalse(audit(self.manifest,[self.source])['files']['fimc_is_lib.bin']['candidates'])
    def test_symlink_rejected(self):
        tgt=self.source/'fimc_is_lib.bin'; tgt.unlink()
        tgt.symlink_to(self.root/'manifest.yml')
        rows=audit(self.manifest,[self.source])
        self.assertEqual(rows['files']['fimc_is_lib.bin']['candidates'],[])
    def test_duplicate_names_detected(self):
        (self.source/'setfile_4ha.bin').write_bytes((self.source/'setfile_3j1.bin').read_bytes())
        rows=audit(self.manifest,[self.source])
        self.assertTrue(any(len(set(name for name,_ in grp['files']))>1 for grp in rows['identical_named_files']))
    def test_fake_fetch_rejected_and_no_file(self):
        dest=self.root/'download'/'fimc_is_lib.bin'
        def bad(url,tmp):
            tmp.write_bytes(b"wrong")
        ok,msg=fetch_one('fimc_is_lib.bin',self.expected['fimc_is_lib.bin'],dest,bad)
        self.assertFalse(ok)
        self.assertFalse(dest.exists())
    def test_valid_mock_fetch(self):
        dest=self.root/'download'/'fimc_is_lib.bin'
        payload=(self.source/'fimc_is_lib.bin').read_bytes()
        def fake(url,tmp):
            tmp.write_bytes(payload)
        ok,msg=fetch_one('fimc_is_lib.bin',self.expected['fimc_is_lib.bin'],dest,fake)
        self.assertTrue(ok)
        self.assertEqual(dest.read_bytes(),payload)
    def test_occupied_destination_not_overwritten(self):
        dest=self.root/'download'/'fimc_is_lib.bin'
        dest.parent.mkdir(); dest.write_bytes(b"original")
        ok,msg=fetch_one('fimc_is_lib.bin',self.expected['fimc_is_lib.bin'],dest,lambda *a:None)
        self.assertFalse(ok)
        self.assertEqual(dest.read_bytes(),b"original")
    def test_no_special_devices(self):
        self.assertRaises(ValueError,sha256_file,self.source)

class StrictAuditTests(CameraAuditTests):
    def run_strict(self):
        import contextlib,io
        from camera_firmware_audit import main
        with contextlib.redirect_stdout(io.StringIO()):
            return main(['--manifest',str(self.manifest),'--root',str(self.source),
                         '--require-manifest-match'])
    def test_strict_valid(self):self.assertEqual(self.run_strict(),0)
    def test_strict_mismatch(self):
        (self.source/'fimc_is_lib.bin').write_bytes(b'wrong')
        self.assertEqual(self.run_strict(),3)
    def test_strict_missing(self):
        (self.source/'fimc_is_lib.bin').unlink()
        self.assertEqual(self.run_strict(),3)
    def test_strict_ambiguous_path(self):
        p=self.source/'duplicate';p.mkdir()
        (p/'fimc_is_lib.bin').write_bytes((self.source/'fimc_is_lib.bin').read_bytes())
        self.assertEqual(self.run_strict(),3)

if __name__=="__main__":
    unittest.main()
