import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Verify(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.rows=[]
        for name in ['build.prop']+['blob'+str(i) for i in range(8)]:
            b=name.encode();(self.root/name).write_bytes(b)
            self.rows.append(dict(name=name,size=len(b),sha256=hashlib.sha256(b).hexdigest()))
        self.doc=dict(device='SM-G975F',build='G975FXXS9DTK9',files=self.rows)
    def test_valid(self): self.assertEqual(len(m.verify(self.root,self.doc)),9)
    def test_truncation(self):
        (self.root/'blob0').write_bytes(b'')
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_wrong_hash(self):
        (self.root/'blob0').write_bytes(b'wrong')
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_wrong_provenance(self):
        self.doc['build']='FUBD'
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_duplicate_path(self):
        self.rows[-1]=self.rows[-2]
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_traversal(self):
        self.rows[0]['name']='../build.prop'
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_link(self):
        (self.root/'blob0').unlink();(self.root/'blob0').symlink_to(self.root/'blob1')
        with self.assertRaises(ValueError):m.verify(self.root,self.doc)
    def test_no_overwrite(self):
        original=m.PIN
        try:
            import json
            pin=self.root/'manifest.json';pin.write_text(json.dumps(self.doc));m.PIN=pin
            with self.assertRaises(ValueError):m.prepare(self.root,self.root)
        finally:m.PIN=original

if __name__=='__main__':unittest.main()
