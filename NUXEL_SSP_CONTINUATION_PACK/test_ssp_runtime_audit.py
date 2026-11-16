#!/usr/bin/env python3
"""Self-tests: offline, no phone or vendor binaries required."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ssp_runtime_audit import elf_meta, RepoReader, StockReader, library_path, hash_bytes

class TestELF(unittest.TestCase):
    def test_native_python_elf(self):
        p=Path(sys.executable)
        # Some Python installations are executable wrappers, so use /bin/ls if needed.
        for candidate in (p,Path("/bin/ls"),Path("/usr/bin/env")):
            if candidate.exists() and candidate.read_bytes()[:4]==b"\x7fELF":
                elf=elf_meta(candidate.read_bytes())
                self.assertIn(elf["machine"],(62,183,40))
                self.assertIn(elf["class"],(32,64))
                self.assertIn("needed",elf)
                return
        self.skipTest("No system ELF binary available")
    def test_invalid_and_bounded(self):
        self.assertIsNone(elf_meta(b"X"*100))
        self.assertIsNone(elf_meta(b"\x7fELF"+b"\x00"*70))
        partial=bytearray(64)
        partial[:6]=b"\x7fELF\x02\x01"
        partial[18:20]=(183).to_bytes(2,"little")
        partial[32:40]=(65535).to_bytes(8,"little")
        partial[54:56]=(56).to_bytes(2,"little")
        partial[56:58]=(2).to_bytes(2,"little")
        self.assertEqual(elf_meta(bytes(partial))["error"],"out-of-bounds ELF program headers")
    def test_repo_alias_zip(self):
        with tempfile.TemporaryDirectory() as d:
            zp=Path(d)/"fixture.zip"
            with zipfile.ZipFile(zp,"w") as z:
                z.writestr("some-prefix/packs/sensors/acquired/vendor-bin-hw-lhd",b"fixture-lhd")
            r=RepoReader(zip_path=zp)
            self.assertEqual(r.get("packs/sensors/acquired/vendor-bin-hw-lhd"),b"fixture-lhd")
            self.assertIsNone(r.get("packs/sensors/acquired/vendor-bin-hw-lhd-absent"))
            r.close()
    def test_stock_paths_and_libraries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            f=root/"system/system/lib64/liblog.so"
            f.parent.mkdir(parents=True)
            f.write_bytes(b"x")
            s=StockReader(root)
            self.assertEqual(s.get("system/lib64/liblog.so"),b"x")
            self.assertEqual(library_path("liblog.so",s,{}),"system/lib64/liblog.so")
            self.assertIsNone(library_path("../liblog.so",s,{}))
    def test_mock_complete_static_stage(self):
        # Synthetic AArch64 ELF header: no firmware, no vendor software.
        # Checks that LOCAL staging is deterministic and never overwrites.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"repo"
            stock=Path(d)/"stock"
            output=Path(d)/"out"
            report=Path(d)/"report"
            (root/"packs/sensors/acquired").mkdir(parents=True)
            (stock/"system/bin").mkdir(parents=True)
            elf=bytearray(64)
            elf[:6]=b"\x7fELF\x02\x01"
            elf[18:20]=(183).to_bytes(2,"little")
            elf[54:56]=(56).to_bytes(2,"little")
            for filename in ("vendor-bin-hw-lhd","vendor-lib64-sensors.sensorhub.so",
                             "vendor-lib64-hw-sensors.exynos9820.so"):
                (root/"packs/sensors/acquired"/filename).write_bytes(elf)
            (stock/"system/bin/linker64").write_bytes(elf)
            (root/"packs/sensors/acquired/vendor-etc-sensor-lhd.conf").write_text(
                "LhePatch=/dev/bbd_patch\nLheBbdPacket=/dev/ttyBCM\n")
            args=[sys.executable,"-S",str(HERE/"ssp_runtime_audit.py"),
                  "--repo-root",str(root),"--android-root",str(stock),
                  "--report-dir",str(report),"--stage-runtime",str(output)]
            proc=subprocess.run(args,text=True,capture_output=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertTrue((output/"system/bin/linker64").is_file())
            self.assertEqual(len([p for p in output.rglob("*") if p.is_file()]),5)
            data=json.loads((report/"ssp-runtime-audit.json").read_text())
            self.assertTrue(data["status"].startswith("STATIC_ELF"))
            self.assertEqual(data["device_writes"],0)
            proc2=subprocess.run(args,text=True,capture_output=True)
            self.assertEqual(proc2.returncode,4)
            self.assertIn("refusing to overwrite",proc2.stderr)
    def test_script_offline_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"packs/sensors/acquired").mkdir(parents=True)
            (root/"packs/sensors/acquired/vendor-bin-hw-lhd").write_bytes(b"notelf")
            report=root/"out"
            r=subprocess.run([sys.executable,"-S",str(HERE/"ssp_runtime_audit.py"),
                        "--repo-root",str(root),"--report-dir",str(report)],text=True,capture_output=True)
            self.assertEqual(r.returncode,3,r.stderr)
            data=json.loads((report/"ssp-runtime-audit.json").read_text())
            self.assertEqual(data["status"],"INCOMPLETE")
            self.assertTrue(data["missing_linker64"])
            self.assertFalse(data["staged_on_host"])
    def test_cannot_stage_into_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"packs/sensors/acquired").mkdir(parents=True)
            r=subprocess.run([sys.executable,"-S",str(HERE/"ssp_runtime_audit.py"),
                        "--repo-root",str(root),"--report-dir",str(root/"out"),
                        "--stage-runtime",str(root/"NOT_ALLOWED")],text=True,capture_output=True)
            self.assertEqual(r.returncode,4)
            self.assertIn("staging path must be separate",r.stderr)
if __name__=="__main__":
    unittest.main(verbosity=2)
