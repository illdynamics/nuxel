"""SYNTHETIC regression inputs executed against the original matched code."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from inspect_lhd_init import EXPECTED, MatchedImage, inspect
from replay_lhd_response import Replay, FinalVersionReplay, SyncReplay, SyncInitializerReplay, rpc_record
from replay_lhd_response import ReliableReplay, PatchRecordReplay, patch_scenario
from replay_lhd_response import OWNER, INIT_INTERFACE, PLATFORM
from check_protocol_replay import frame

BINARY = Path(__file__).resolve().parents[3] / 'packs/sensors/acquired/vendor-bin-hw-lhd'
VALUES = (0x12345678, 0x9abcdef0, 0x13579bdf)
BODY = struct.pack('<III', *VALUES)


def kinds(result):
    return [e['kind'] for e in result['events']]


class SyncInitializerTests(unittest.TestCase):
    RESPONSE = bytes([1, 1, 10, 20, 30, 40, 50, 60])  # SYNTHETIC, not ROM evidence

    def test_real_interface_relocations(self):
        image = MatchedImage(BINARY)
        self.assertEqual(image.relocations[0x48eb0], 0x3ec18)
        self.assertEqual(image.relocations[0x487f8], 0x37f88)

    def test_initial_and_confirmation_paths_serialize_version_request(self):
        for confirmation, target, waiting in ((False, 7, 8), (True, 14, 15)):
            with self.subTest(confirmation=confirmation):
                r = SyncInitializerReplay(BINARY, confirmation)
                r.start()
                synced = r.receive(self.RESPONSE)
                self.assertEqual(synced['state'], target)
                self.assertEqual(synced['timer_deadline'], 1000)
                requested = r.step()
                self.assertEqual(requested['state'], waiting)
                self.assertEqual(requested['version_retries'], 5)
                self.assertEqual(requested['timer_deadline'], 1250)
                self.assertEqual([e['payload_hex'] for e in requested['events']
                                  if e['kind'] == 'reliable_enqueue_boundary'], ['0000'])
                self.assertNotIn('version_callback', kinds(requested))

    def test_version_timeout_is_five_retries_then_assertion_boundary(self):
        r = SyncInitializerReplay(BINARY)
        r.start()
        r.receive(self.RESPONSE)
        r.step()
        for i in range(1, 6):
            result = r.step(1000 + 250*i)
            self.assertEqual(result['version_retries'], 5-i)
            self.assertEqual(result['timer_deadline'], 1250 + 250*i)
            self.assertIn('reliable_enqueue_boundary', kinds(result))
        result = r.step(2500)
        self.assertTrue(result['assertion_boundary'])
        self.assertNotIn('reliable_enqueue_boundary', kinds(result))
        self.assertEqual(result['state'], 8)
        with self.assertRaisesRegex(RuntimeError, 'assertion boundary'):
            r.step()

    def test_sync_timeout_restarts_autobaud_with_decremented_budget(self):
        r = SyncInitializerReplay(BINARY)
        r.start()
        for now in range(1100, 1601, 100):
            result = r.poll(now)
        self.assertEqual(result['state'], 2)
        self.assertEqual(result['sync_retries'], 4)
        raw = r.step(1600)
        self.assertEqual(raw['state'], 3)
        self.assertEqual(raw['timer_deadline'], 1700)
        self.assertEqual([e['payload_hex'] for e in raw['events']
                          if e['kind'] == 'raw_write_boundary'],
                         [r.image.read(0xdfe4, 36).hex()])
        restarted = r.step(1700)
        self.assertEqual(restarted['state'], 4)
        self.assertEqual(restarted['token'], 1)
        # Token reuse means the earlier attempt's synthetic response also passes.
        self.assertEqual(r.receive(self.RESPONSE)['state'], 7)

    def test_exhausted_sync_budget_stops_without_inventing_recovery(self):
        for confirmation in (False, True):
            r = SyncInitializerReplay(BINARY, confirmation)
            r.put32(OWNER + 2356, 0)
            r.start()
            for now in range(1100, 1601, 100):
                result = r.poll(now)
            self.assertTrue(result['assertion_boundary'])
            self.assertEqual(result['state'], 6)
            self.assertNotIn('raw_write_boundary', kinds(result))

    def test_cancel_does_not_cancel_transport_sync(self):
        r = SyncInitializerReplay(BINARY)
        r.start()
        canceled = r.step(cancel=True)
        self.assertEqual(canceled['state'], 0)
        self.assertTrue(canceled['active'])
        late = r.receive(self.RESPONSE)
        self.assertFalse(late['active'])
        self.assertTrue(late['assertion_boundary'])
        self.assertEqual(late['state'], 0)
        self.assertEqual(late['transport_bytes']['0xc56'], 11)

    def test_truncated_and_duplicate_sync_do_not_repeat_initializer(self):
        r = SyncInitializerReplay(BINARY)
        r.start()
        for length in range(8):
            result = r.receive(self.RESPONSE[:length])
            self.assertEqual(result['state'], 4)
            self.assertNotIn('initializer_entry', kinds(result))
        r.receive(self.RESPONSE)
        duplicate = r.receive(self.RESPONSE)
        self.assertEqual(duplicate['state'], 7)
        self.assertNotIn('initializer_entry', kinds(duplicate))

    def test_unreviewed_core_state_is_refused(self):
        r = SyncInitializerReplay(BINARY)
        r.put32(r.CORE + 18812, 2)
        r.start()
        with self.assertRaisesRegex(RuntimeError, 'unreviewed execution at 0x37fc0'):
            r.receive(self.RESPONSE)


class ReliableQueueTests(unittest.TestCase):
    def test_original_allocator_and_cumulative_ack(self):
        r = ReliableReplay(BINARY)
        self.assertEqual(r.enqueue(b'abc', 11)['pending_bytes'], 3)
        self.assertEqual(r.enqueue(b'defgh', 22)['pending_bytes'], 8)
        result = r.acknowledge(2)
        self.assertEqual(result['pending_bytes'], 0)
        self.assertEqual(result['queue'], [])
        callbacks = [e for e in result['events'] if e['kind'] == 'queue_callback']
        self.assertEqual([e['argument'] for e in callbacks], [11, 22])
        self.assertEqual([e['pending_bytes_at_callback'] for e in callbacks], [0, 0])
        self.assertNotIn('version_callback', kinds(result))

    def test_unknown_partial_duplicate_and_reordered_ack(self):
        r = ReliableReplay(BINARY)
        r.enqueue(b'abc')
        r.enqueue(b'de')
        self.assertEqual(r.acknowledge(99)['pending_bytes'], 5)
        self.assertEqual(r.acknowledge(1)['pending_bytes'], 2)
        duplicate = r.acknowledge(1)
        self.assertEqual(duplicate['pending_bytes'], 2)
        self.assertNotIn('queue_callback', kinds(duplicate))
        self.assertEqual(r.acknowledge(2)['pending_bytes'], 0)
        self.assertNotIn('queue_callback', kinds(r.acknowledge(1)))

    def test_crc_and_packet_ack_cannot_drain_reliable_queue(self):
        r = ReliableReplay(BINARY)
        r.enqueue(b'abc')
        packet_ack = frame(bytes([0, 0, 1, 1]))
        r.run(packet_ack, wire=True)
        self.assertEqual(r.snapshot()['pending_bytes'], 3)
        reliable_ack = frame(bytes([1, 0, 4, 1]))
        bad_crc = reliable_ack[:-3] + bytes([reliable_ack[-3] ^ 1]) + reliable_ack[-2:]
        r.run(bad_crc, wire=True)
        self.assertEqual(r.snapshot()['pending_bytes'], 3)
        result = r.run(reliable_ack, wire=True)
        self.assertEqual(r.snapshot()['pending_bytes'], 0)
        self.assertIn('queue_callback', kinds(result))
        self.assertNotIn('version_callback', kinds(result))

    def test_nack_cumulatively_retires_prefix_and_resends_suffix(self):
        r = ReliableReplay(BINARY)
        r.enqueue(b'abc', 11)
        r.enqueue(b'de', 22)
        # Packet sequence 0 is the intercepted-send return, not observed traffic.
        result = r.acknowledge(1, nack_packet=0)
        self.assertEqual(result['pending_bytes'], 2)
        self.assertEqual([e['argument'] for e in result['events']
                          if e['kind'] == 'queue_callback'], [11])
        self.assertEqual(result['queue'][0]['attempts'], 2)
        self.assertIn('transport_send_boundary', kinds(result))

    def test_reliable_retry_limit_reports_error_without_clearing_queue(self):
        r = ReliableReplay(BINARY)
        r.enqueue(b'abc')
        self.assertNotIn('transport_send_boundary', kinds(r.poll(1499)))
        for now in range(1500, 5501, 500):
            result = r.poll(now)
        self.assertEqual(result['queue'][0]['attempts'], 10)
        result = r.poll(6000)
        self.assertIn('communication_error_boundary', kinds(result))
        self.assertEqual(result['pending_bytes'], 3)
        self.assertNotIn('queue_callback', kinds(result))
        self.assertNotIn('transport_send_boundary', kinds(result))

    def test_ring_and_sequence_wrap_under_bounded_repeated_use(self):
        r = ReliableReplay(BINARY)
        for i in range(300):
            payload = bytes([i & 255]) * (1 + i % 127)
            result = r.enqueue(payload)
            self.assertEqual(result['pending_bytes'], len(payload))
            self.assertFalse(result['assertion_boundary'])
            result = r.acknowledge((i + 1) & 255)
            self.assertEqual(result['queue'], [])
            self.assertEqual(result['pending_bytes'], 0)

    def test_pending_bytes_block_application_start(self):
        r = ReliableReplay(BINARY)
        r.enqueue(b'synthetic')
        r.stage_consumed_patch()
        result = r.step()
        self.assertEqual(result['state'], 12)
        self.assertNotIn('transport_send_boundary', kinds(result))
        r.acknowledge(1)
        self.assertEqual(r.step()['state'], 13)

    def test_scratch_service_and_no_entry_startup_branches(self):
        for patch_type, entry, skip, state, delay, expected in (
                (0x41, 0x12345678, False, 13, 40, '2e0478563412'),
                (0x42, 0x12345678, False, 13, 100, '371478563412' + '00'*16),
                (0x41, 0x12345678, True, 16, 40, '2e0478563412'),
                (0x41, 0xffffffff, False, 15, 250, '0000')):
            with self.subTest(patch_type=patch_type, entry=entry, skip=skip):
                r = ReliableReplay(BINARY)
                r.stage_consumed_patch(patch_type, entry, skip)
                result = r.step()
                sends = [e for e in result['events'] if e['kind'] == 'transport_send_boundary']
                self.assertEqual([e['payload_hex'] for e in sends], [expected])
                self.assertEqual(sends[0]['flags'], 2 if entry == 0xffffffff else 0)
                self.assertEqual(result['state'], state)
                self.assertEqual(result['timer_deadline'], 1000 + delay)
                self.assertNotIn('version_callback', kinds(result))

    def test_unavailable_patch_metadata_stops_before_application_start(self):
        r = ReliableReplay(BINARY)
        r.stage_consumed_patch()
        r.uc.mem_write(OWNER + 40 + 0x488, b'\x00')
        result = r.step()
        self.assertTrue(result['assertion_boundary'])
        self.assertNotIn('transport_send_boundary', kinds(result))


class PatchRecordTests(unittest.TestCase):
    @staticmethod
    def record(data=b'abc', address=0x12345678):
        return b'\xf1' + struct.pack('<HI', len(data)+4, address) + data

    def test_f1_serializes_rpc5_with_exact_little_endian_fields(self):
        r = PatchRecordReplay(BINARY)
        result = r.feed(self.record())
        writes = [e for e in result['events'] if e['kind'] == 'patch_write_callback']
        self.assertEqual(writes, [{'kind': 'patch_write_callback', 'destination': '0x12345678',
                                  'length': 3, 'data_sha256': hashlib.sha256(b'abc').hexdigest()}])
        r.flush()
        self.assertEqual(r.last_serialized, rpc_record(5, struct.pack('<IH', 0x12345678, 3)+b'abc'))
        self.assertEqual(result['parser_state'], 0)

    def test_all_fragment_boundaries_and_incomplete_record(self):
        record = self.record()
        for split in range(1, len(record)):
            r = PatchRecordReplay(BINARY)
            first = r.feed(record[:split])
            self.assertNotIn('patch_write_callback', kinds(first))
            self.assertNotEqual(first['parser_state'], 0)
            result = r.feed(record[split:])
            self.assertEqual(kinds(result).count('patch_write_callback'), 1)
            r.flush()
            self.assertEqual(r.last_serialized, rpc_record(5, struct.pack('<IH', 0x12345678, 3)+b'abc'))

    def test_duplicate_and_reordered_file_records_are_not_suppressed(self):
        r = PatchRecordReplay(BINARY)
        result = r.feed(self.record(address=2)+self.record(address=1)+self.record(address=2))
        self.assertEqual([e['destination'] for e in result['events']
                          if e['kind'] == 'patch_write_callback'], ['0x2', '0x1', '0x2'])

    def test_malformed_tag_length_and_short_body_refused(self):
        for record in (b'\xef', b'\xf1\xb7\x03', b'\xf1\x04\x00'+b'\x00'*4):
            r = PatchRecordReplay(BINARY)
            result = r.feed(record)
            self.assertTrue(result['assertion_boundary'])
            self.assertNotIn('patch_write_callback', kinds(result))

    def test_maximum_f1_body_and_unreviewed_callback(self):
        r = PatchRecordReplay(BINARY)
        result = r.feed(self.record(b'x'*946))
        self.assertFalse(result['assertion_boundary'])
        self.assertEqual(result['parser_state'], 0)
        r.flush()
        self.assertEqual(r.last_serialized, rpc_record(5, struct.pack('<IH', 0x12345678, 946)+b'x'*946))
        with self.assertRaisesRegex(RuntimeError, 'unreviewed execution'):
            PatchRecordReplay(BINARY).feed(b'\xf0\x0c\x00'+bytes(12))

    def test_independent_rpc_output_checker_rejects_malformed_records(self):
        for payload in (b'\x05', b'\x05\x80', b'\x06\x00', b'\x05\x07',
                        rpc_record(5, struct.pack('<IH', 1, 2)+b'x')):
            with self.assertRaises(ValueError):
                PatchRecordReplay.decode_serialized_writes(payload)

    def test_actual_hash_matched_embedded_patch_records_offline(self):
        header = BINARY.parents[3] / 'kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h'
        if not header.is_file():
            self.skipTest('owner-local matched kernel header unavailable')
        result = patch_scenario(BINARY, header)
        self.assertEqual(result['write_records'], 479)
        self.assertEqual(result['write_data_bytes'], 435542)
        self.assertEqual(result['rpc_packets'], 478)
        self.assertEqual(result['final_parser_state'], 0)


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


class OriginalTransportTests(unittest.TestCase):
    def wire(self, sequence=0, flags=0, details=b'', payload=None):
        if payload is None:
            payload = rpc_record(3, BODY)
        return frame(bytes([sequence, len(payload), flags]) + details + payload)

    def test_transport_to_callback_and_underflow_order(self):
        for body in (BODY, b''):
            result = Replay(BINARY, 8).run(self.wire(payload=rpc_record(3, body)), wire=True)
            self.assertEqual(result['state'], 9)
            self.assertIn('version_callback', kinds(result))
            self.assertEqual('reader_error' in kinds(result), not body)

    def test_crc_and_declared_size_reject_before_callback(self):
        valid = self.wire()
        bad_crc = valid[:-3] + bytes([valid[-3] ^ 1]) + valid[-2:]
        bad_size = frame(bytes([0, 0, 0]) + rpc_record(3, BODY))
        for wire in (bad_crc, bad_size, valid[:-2]):
            result = Replay(BINARY, 8).run(wire, wire=True)
            self.assertNotIn('version_callback', kinds(result))
            self.assertEqual(result['state'], 8)

    def test_unreliable_sequence_jump_and_duplicate_are_delivered(self):
        replay = Replay(BINARY, 8)
        for sequence in (0, 0, 200, 3):
            result = replay.run(self.wire(sequence=sequence), wire=True)
            self.assertIn('version_callback', kinds(result))

    def test_reliable_duplicate_suppressed_and_next_accepted(self):
        replay = Replay(BINARY, 8)
        for sequence, expected in ((0, True), (0, False), (2, False), (1, True)):
            result = replay.run(self.wire(flags=2, details=bytes([sequence])), wire=True)
            self.assertEqual('version_callback' in kinds(result), expected)
            send = [event for event in result['events'] if event['kind'] == 'transport_send_boundary']
            self.assertEqual(send[0]['w1'], 9 if sequence == 2 else 5)

    def test_constructor_option_can_deliver_reliable_duplicates(self):
        replay = Replay(BINARY, 8, deliver_reliable_duplicates=True)
        for unused in range(2):
            result = replay.run(self.wire(flags=2, details=b'\x00'), wire=True)
            self.assertIn('version_callback', kinds(result))

    def test_internal_payload_never_reaches_rpc(self):
        result = Replay(BINARY, 8).run(self.wire(flags=128, details=b'\x01\x00'), wire=True)
        self.assertIn('internal_message_boundary', kinds(result))
        self.assertNotIn('version_callback', kinds(result))
        self.assertEqual(result['state'], 8)

    def test_ack_only_does_not_invoke_version_callback(self):
        for flags in (1, 4, 8):
            result = Replay(BINARY, 8).run(self.wire(flags=flags, details=b'\x00', payload=b''), wire=True)
            self.assertNotIn('version_callback', kinds(result))
            self.assertEqual(result['state'], 8)

    def test_fragmentation_escaping_and_restart(self):
        payload = rpc_record(3, bytes.fromhex('b0111300') * 3)
        wire = self.wire(payload=payload)
        for split in range(1, len(wire)):
            replay = Replay(BINARY, 8)
            first = replay.run(wire[:split], wire=True)
            second = replay.run(wire[split:], wire=True)
            self.assertNotIn('version_callback', kinds(first))
            self.assertIn('version_callback', kinds(second))
            self.assertEqual(second['metadata']['2320'], 0x001311b0)
        result = Replay(BINARY, 8).run(b'\xb0\x00\xff' + wire, wire=True)
        self.assertIn('version_callback', kinds(result))


class FinalVersionTests(unittest.TestCase):
    def test_success_and_failure_both_enter_done(self):
        for asic, expected in ((0x4775b0, True), (0x44775b0, True),
                               (0x4775b1, False), (0, False)):
            replay = FinalVersionReplay(BINARY, asic, 0x4775b0)
            result = replay.step()
            completion = [event for event in result['events'] if event['kind'] == 'completion_boundary']
            self.assertEqual(completion, [{'kind': 'completion_boundary', 'success': expected, 'asic': asic}])
            self.assertEqual(result['state'], 17)
            self.assertEqual(result['timer_deadline'], 1001)
            self.assertTrue(result['timer_active'])
            self.assertTrue(result['registered'])
            cleaned = replay.step()
            self.assertEqual(cleaned['state'], 0)
            self.assertFalse(cleaned['registered'])

    def test_legacy_asic_exception_is_revision_specific(self):
        for revision, expected in ((0x36a07, True), (0x36a08, False)):
            result = FinalVersionReplay(BINARY, 0x4774a0, 0x4774a1,
                                        original_version=revision).step()
            completion = next(event for event in result['events'] if event['kind'] == 'completion_boundary')
            self.assertEqual(completion['success'], expected)

    def test_confirmation_only_path_skips_patch_identity_comparison(self):
        result = FinalVersionReplay(BINARY, 0, 0x4775b0, confirmation_only=True).step()
        completion = next(event for event in result['events'] if event['kind'] == 'completion_boundary')
        self.assertTrue(completion['success'])
        self.assertEqual(result['state'], 17)

    def test_cancel_unregisters_without_clearing_metadata_or_timer(self):
        replay = FinalVersionReplay(BINARY, 0x4775b0, 0x4775b0)
        replay.step()
        result = replay.step(cancel=True)
        self.assertEqual(result['state'], 0)
        self.assertFalse(result['registered'])
        self.assertEqual(replay.word(OWNER + 2320), 0x4775b0)
        self.assertTrue(result['timer_active'])
        self.assertNotIn('completion_boundary', kinds(result))

    def test_timer_negative_cancels_and_positive_wraps(self):
        replay = FinalVersionReplay(BINARY, 0x4775b0, 0x4775b0, now=0xfffffff0)
        replay.execute(0x37908, [INIT_INTERFACE, 250])
        self.assertEqual(replay.word(INIT_INTERFACE + 16), 234)
        self.assertEqual(replay.uc.mem_read(INIT_INTERFACE + 20, 1), b'\x01')
        replay.execute(0x37908, [INIT_INTERFACE, 0xffffffff])
        self.assertEqual(replay.uc.mem_read(INIT_INTERFACE + 20, 1), b'\x00')
        self.assertEqual(replay.word(PLATFORM + 18824), 0xfffffff0)


class InternalSyncTests(unittest.TestCase):
    REPLY = bytes([1, 1, 10, 20, 30, 40, 50, 60])

    def test_start_and_exact_response_mutations(self):
        replay = SyncReplay(BINARY)
        started = replay.start()
        self.assertTrue(started['active'])
        self.assertEqual(started['events'], [
            {'kind': 'transport_send_boundary', 'flags': 0x300, 'payload_hex': '0001'},
            {'kind': 'schedule_boundary', 'delay_ms': 100}])
        result = replay.receive(self.REPLY)
        self.assertFalse(result['active'])
        self.assertEqual(result['transport_bytes'], {
            '0xc56': 11, '0x34f0': 31, '0x34f1': 30,
            '0x428': 40, '0x431': 49, '0x432': 0})
        self.assertEqual(result['previous_reliable_length'], '0000')
        self.assertIn({'kind': 'sync_completion_boundary', 'success': True}, result['events'])
        self.assertNotIn('version_callback', kinds(result))

    def test_truncated_and_trailing_responses_reject_before_mutation(self):
        for payload in [self.REPLY[:length] for length in range(8)] + [self.REPLY + b'\x00']:
            with self.subTest(payload=payload.hex()):
                replay = SyncReplay(BINARY)
                before = replay.start()
                result = replay.receive(payload)
                self.assertTrue(result['active'])
                self.assertEqual(result['transport_bytes'], before['transport_bytes'])
                self.assertNotIn('sync_completion_boundary', kinds(result))
                self.assertNotIn('read_past_supplied_input', kinds(result))

    def test_wrong_token_inactive_and_duplicate_responses_do_not_complete(self):
        replay = SyncReplay(BINARY)
        self.assertNotIn('sync_completion_boundary', kinds(replay.receive(self.REPLY)))
        replay.start()
        wrong_token = self.REPLY[:1] + b'\x02' + self.REPLY[2:]
        self.assertNotIn('sync_completion_boundary', kinds(replay.receive(wrong_token)))
        self.assertIn('sync_completion_boundary', kinds(replay.receive(self.REPLY)))
        duplicate = replay.receive(self.REPLY)
        self.assertNotIn('sync_completion_boundary', kinds(duplicate))

    def test_retry_limit_and_exact_deadline(self):
        replay = SyncReplay(BINARY)
        replay.start()
        early = replay.poll(1099)
        self.assertEqual(early['events'], [{'kind': 'schedule_boundary', 'delay_ms': 1}])
        for token in range(2, 7):
            result = replay.poll(1000 + (token - 1) * 100)
            self.assertTrue(result['active'])
            self.assertEqual(result['token'], token)
            self.assertIn({'kind': 'transport_send_boundary', 'flags': 0x300,
                           'payload_hex': bytes([0, token]).hex()}, result['events'])
        expired = replay.poll(1600)
        self.assertFalse(expired['active'])
        self.assertNotIn('transport_send_boundary', kinds(expired))
        self.assertIn({'kind': 'sync_completion_boundary', 'success': False}, expired['events'])
        self.assertNotIn('sync_completion_boundary', kinds(replay.poll(1700)))

    def test_retry_rejects_previous_token_but_new_attempt_reuses_it(self):
        replay = SyncReplay(BINARY)
        replay.start()
        replay.poll(1100)
        self.assertNotIn('sync_completion_boundary', kinds(replay.receive(self.REPLY)))
        current_reply = self.REPLY[:1] + b'\x02' + self.REPLY[2:]
        replay.receive(current_reply)
        restarted = replay.start()
        self.assertEqual(restarted['token'], 1)
        self.assertIn('sync_completion_boundary', kinds(replay.receive(self.REPLY)))

    def test_busy_start_does_not_reset_token_or_send(self):
        replay = SyncReplay(BINARY)
        replay.start()
        replay.poll(1100)
        busy = replay.start()
        self.assertEqual(busy['token'], 2)
        self.assertTrue(busy['active'])
        self.assertNotIn('transport_send_boundary', kinds(busy))
        replay = SyncReplay(BINARY)
        replay.uc.mem_write(replay.TRANSPORT + 0x34f0, b'\x00\x00')
        busy = replay.start()
        self.assertFalse(busy['active'])
        self.assertNotIn('transport_send_boundary', kinds(busy))

    def test_clock_and_sequence_fields_wrap(self):
        replay = SyncReplay(BINARY, now=0xfffffff0)
        replay.start()
        self.assertEqual(replay.poll(0x53)['token'], 1)
        self.assertEqual(replay.poll(0x54)['token'], 2)
        result = replay.receive(bytes([1, 2, 255, 123, 255, 255, 0, 123]))
        self.assertEqual(result['transport_bytes'], {
            '0xc56': 0, '0x34f0': 0, '0x34f1': 255,
            '0x428': 255, '0x431': 255, '0x432': 0})

    def test_crc_valid_internal_wire_path_and_bad_crc(self):
        wire = frame(bytes([0, 8, 128, 1, 0]) + self.REPLY)
        replay = SyncReplay(BINARY)
        replay.start()
        result = replay.run(wire, wire=True)
        self.assertIn('sync_completion_boundary', kinds(result))
        self.assertNotIn('version_callback', kinds(result))
        replay = SyncReplay(BINARY)
        replay.start()
        result = replay.run(wire[:-3] + bytes([wire[-3] ^ 1]) + wire[-2:], wire=True)
        self.assertNotIn('sync_completion_boundary', kinds(result))
        self.assertTrue(replay.snapshot()['active'])

    def test_initializer_sync_callback_branches(self):
        for success, next_state in ((True, 5), (False, 6)):
            replay = SyncReplay(BINARY)
            replay.execute(0x396ac, [OWNER, int(success)])
            self.assertEqual(replay.word(OWNER + 1256), next_state)
            self.assertEqual(replay.events, [{'kind': 'initializer_boundary', 'state': next_state}])


if __name__ == '__main__':
    unittest.main()
