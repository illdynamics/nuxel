"""Offline tests; no device or network dependency."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ToolTests(unittest.TestCase):
    def test_fmt_vector(self):
        m = module('decode_observed_frames')
        m.self_test()
        self.assertEqual(m.fmt_record(m.FMT_SAMPLE)['payload_length'], 18)

    def test_rfs_denies_destructive(self):
        m = module('decode_observed_frames')
        self.assertIn('DENY', m.rfs_record(m.RFS_SAMPLE)['safe_handling'])
        self.assertEqual(m.rfs_record(m.RFS_SAMPLE)['le16_at_6'], 15)
        self.assertFalse(m.rfs_record(m.RFS_SAMPLE[:-1])['ok'])

    def test_elf_triage(self):
        m = module('triage_elf')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'libsec-ril.so'
            blob = bytearray(64)
            blob[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', blob, 18, 183)
            blob += b'\0vendor SIPC test RFS\0'
            p.write_bytes(blob)
            x = m.inspect(p)
            self.assertEqual(x['machine'], 'AArch64')
            self.assertGreaterEqual(x['keyword_strings_total'], 1)
            self.assertEqual(len(x['sha256']), 64)

    def test_inventory_symlink_excluded(self):
        m = module('inventory_vendor')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'libsec-ril.so').write_bytes(b'not-a-real-ril')
            (root / 'libsec-ril-dsds.so').symlink_to('libsec-ril.so')
            found = m.inventory(root)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['path'], 'libsec-ril.so')

    def test_repo_contract(self):
        m = module('scan_repo_contract')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'sipc5_fmt.c').write_text('// SIPC5_CH_ID_RFS_0\n')
            r = m.scan(root)
            self.assertEqual(len(r['source_files']), 1)
            self.assertEqual(r['source_files'][0]['matching_lines'][0]['line'], 1)

    def test_gate_checker_fail_closed(self):
        m = module('check_stage06_gates')
        total, pending = m.check(ROOT / 'data' / 'stage06-gates.json')
        self.assertEqual(total, 10)
        self.assertEqual(len(pending), 10)


if __name__ == '__main__':
    unittest.main()
