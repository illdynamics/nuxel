"""Synthetic note/ELF parser rejection and identity tests; no live access."""
from pathlib import Path
import struct
import tempfile
import unittest
from inspect_kernel_identity import build_ids, compare, elf_build_id, MAX_NOTES


def note(value=b'12345678901234567890'):
    return struct.pack('<III', 4, len(value), 3) + b'GNU\0' + value + bytes((-len(value)) % 4)


def kernel(notes):
    header = bytearray(64)
    header[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', header, 18, 183)
    struct.pack_into('<Q', header, 32, 64)
    struct.pack_into('<HH', header, 54, 56, 1)
    return header + struct.pack('<IIQQQQQQ', 4, 4, 120, 0, 0, len(notes), len(notes), 4) + notes


class KernelIdentityTests(unittest.TestCase):
    def test_note_lengths_padding_and_duplicates(self):
        for length in range(1, 33):
            value = b'a' * length
            self.assertEqual(build_ids(note(value)*2), {value.hex()})
        for bad in (b'', b'x', note()[:-1], note(b''), b'x'*(MAX_NOTES+1)):
            with self.assertRaises(ValueError):
                build_ids(bad)

    def test_match_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            elf, captured = Path(tmp)/'kernel', Path(tmp)/'notes'
            elf.write_bytes(kernel(note()))
            captured.write_bytes(note())
            self.assertTrue(compare(elf, captured)['build_id_matches'])
            captured.write_bytes(note(b'different'))
            self.assertFalse(compare(elf, captured)['build_id_matches'])

    def test_truncated_wrong_architecture_and_conflicting_ids(self):
        wrong_arch = kernel(note())
        struct.pack_into('<H', wrong_arch, 18, 62)
        fixtures = [b'not ELF', kernel(note())[:119], kernel(note())[:-1],
                    wrong_arch, kernel(note()+note(b'different'))]
        with tempfile.TemporaryDirectory() as tmp:
            elf = Path(tmp)/'kernel'
            for data in fixtures:
                elf.write_bytes(data)
                with self.assertRaises(ValueError):
                    elf_build_id(elf)


if __name__ == '__main__':
    unittest.main()
