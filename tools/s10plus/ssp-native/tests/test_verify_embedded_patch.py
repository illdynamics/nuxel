#!/usr/bin/env python3
"""Host-only tests for verify_embedded_patch.py; no handset interfaces."""
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "verify_embedded_patch.py"
SPEC = importlib.util.spec_from_file_location("verify_embedded_patch", MODULE)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class EmbeddedPatchTests(unittest.TestCase):
    def test_literal_decoding_excludes_c_terminator(self):
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / "patch.h"
            header.write_text('static char p[] = "<Crc=193>\\n" "x";\n', encoding="ascii")
            self.assertEqual(VERIFY.decode_c_string_literals(header), b"<Crc=193>\nx")

    def test_rejects_invalid_expected_metadata(self):
        payload = (
            b"<AsicVersion=0x004775B0>\n<BlobLength=1>\n"
            b"<PatchAddress=0x00800161>\n<Crc=193>\n<Blob=00>\n"
        )
        with self.assertRaisesRegex(ValueError, "unexpected blob length"):
            VERIFY.verify(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
