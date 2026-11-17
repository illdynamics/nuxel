"""SYNTHETIC regression inputs executed against the original matched code."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from inspect_lhd_init import EXPECTED, MatchedImage, inspect
from replay_lhd_response import Replay, rpc_record

BINARY = Path(__file__).resolve().parents[3] / 'packs/sensors/acquired/vendor-bin-hw-lhd'
VALUES = (0x12345678, 0x9abcdef0, 0x13579bdf)
BODY = struct.pack('<III', *VALUES)


def kinds(result):
    return [e['kind'] for e in result['events']]


class OriginalDecoderTests(unittest.TestCase):
    def test_identity_relocations_and_range_hashes(self):
        result = inspect(BINARY)
        image = MatchedImage(BINARY)
        self.assertEqual(image.digest, EXPECTED)
        self.assertEqual(image.relocations[0x48ae0], 0x3d1a8)
        self.assertEqual(image.relocations[0x48b20], 0x39d00)
        self.assertEqual(image.relocations[0x48b28], 0x39e64)
        for r in result['response_path']['evidence_ranges'].values():
            a, b = int(r['start'], 16), int(r['end_exclusive'], 16)
            self.assertEqual(hashlib.sha256(image.read(a, b-a)).hexdigest(), r['sha256'])

    def test_modified_binary_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'modified'
            data = bytearray(BINARY.read_bytes())
            data[-1] ^= 1
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'not the reviewed'):
                Replay(path)

    def test_normal_all_initialization_states(self):
        for state in range(18):
            with self.subTest(state=state):
                r = Replay(BINARY, state).run(rpc_record(3, BODY))
                self.assertEqual(r['state'], {8: 9, 15: 16}.get(state, state))
                self.assertEqual([r['metadata'][str(n)] for n in (2320, 2324, 2328)], list(VALUES))
                self.assertEqual(r['metadata']['2332'], VALUES[1])
                self.assertEqual(r['normal_extra'], VALUES[0])
                self.assertNotIn('reader_error', kinds(r))
                self.assertEqual('initializer_boundary' in kinds(r), state in (8, 15))

    def test_each_normal_truncation_mutates_before_error(self):
        for length in range(12):
            with self.subTest(length=length):
                r = Replay(BINARY, 8).run(rpc_record(3, BODY[:length]))
                self.assertEqual(r['state'], 9)
                expected = [VALUES[i] if length >= 4*(i+1) else 0 for i in range(3)]
                self.assertEqual([r['metadata'][str(n)] for n in (2320, 2324, 2328)], expected)
                order = kinds(r)
                self.assertLess(order.index('version_callback'), order.index('initializer_boundary'))
                self.assertLess(order.index('initializer_boundary'), order.index('reader_error'))

    def test_trailing_payload_detected_after_callback(self):
        r = Replay(BINARY, 15).run(rpc_record(3, BODY + b'X'))
        self.assertEqual(r['state'], 16)
        self.assertIn('reader_error', kinds(r))

    def test_duplicate_and_reordered_metadata_persist(self):
        replay = Replay(BINARY, 8)
        first = replay.run(rpc_record(3, BODY))
        duplicate = replay.run(rpc_record(3, BODY))
        later = replay.run(rpc_record(3, struct.pack('<III', 3, 2, 1)))
        self.assertEqual([first['state'], duplicate['state'], later['state']], [9, 9, 9])
        self.assertEqual(later['metadata'], {'2320': 3, '2324': 2, '2328': 1, '2332': VALUES[1]})
        self.assertNotIn('initializer_boundary', kinds(duplicate))

    def test_extended_and_its_truncations(self):
        body = BODY + struct.pack('<I', 7) + b'\x03a\x00b' + struct.pack('<I', 9) + b'\x02x\x00'
        r = Replay(BINARY, 15).run(rpc_record(59, body))
        self.assertEqual(r['state'], 16)
        self.assertEqual(r['normal_extra'], 0)
        self.assertNotIn('reader_error', kinds(r))
        for n in range(len(body)):
            with self.subTest(length=n):
                r = Replay(BINARY, 0).run(rpc_record(59, body[:n]))
                self.assertIn('version_callback', kinds(r))
                self.assertIn('reader_error', kinds(r))
                self.assertEqual(r['state'], 0)

    def test_envelope_mismatch_rejected_before_callback(self):
        for payload in (b'\x03\x0c', b'\x03\x0c' + BODY[:-1], rpc_record(3, BODY) + b'\x01\x01'):
            r = Replay(BINARY, 8).run(payload)
            self.assertNotIn('version_callback', kinds(r))
            self.assertEqual(r['state'], 8)

    def test_incomplete_header_reads_beyond_supplied_extent(self):
        for payload in (b'\x03', b'\x80', b'\x03\x80'):
            r = Replay(BINARY, 8).run(payload)
            self.assertIn('read_past_supplied_input', kinds(r))
            self.assertNotIn('version_callback', kinds(r))

    def test_unknown_ids_and_nonversion_response(self):
        for rpc_id in (0, 1, 2, 4, 5, 58, 60, 127, 128, 0x7fff):
            r = Replay(BINARY, 8).run(rpc_record(rpc_id, BODY))
            self.assertNotIn('version_callback', kinds(r))
            self.assertEqual(r['state'], 8)

    def test_multi_record_order_and_original_version_latch(self):
        r = Replay(BINARY, 8, original_version=42).run(
            rpc_record(3, BODY) + rpc_record(3, struct.pack('<III', 6, 5, 4)))
        self.assertEqual(kinds(r).count('version_callback'), 2)
        self.assertEqual(kinds(r).count('initializer_boundary'), 1)
        self.assertEqual(r['metadata'], {'2320': 6, '2324': 5, '2328': 4, '2332': 42})

    def test_instruction_budget_is_enforced(self):
        with self.assertRaisesRegex(RuntimeError, 'budget'):
            Replay(BINARY).run(rpc_record(3, BODY), budget=1)


if __name__ == '__main__':
    unittest.main()
