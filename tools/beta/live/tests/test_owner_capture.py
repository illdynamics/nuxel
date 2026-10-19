#!/usr/bin/env python3
"""Capture integrity: stale logs and personal text cannot satisfy owner proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('capture', Path(__file__).parents[1] / 'nuxel_owner_capture.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureIntegrity(unittest.TestCase):
    def test_stale_lines_excluded_and_partial_lines_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'home.state'
            p.write_text('old touchstart\n')
            cursor = capture.Cursor(p)
            self.assertEqual(cursor.lines(), [])
            with p.open('a') as f:
                f.write('new tou')
            self.assertEqual(cursor.lines(), [])
            with p.open('a') as f:
                f.write('chstart\n')
            self.assertEqual(cursor.lines(), ['new touchstart'])

    def test_rotation_is_not_silent_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'home.state'
            p.write_text('old event\n')
            cursor = capture.Cursor(p)
            p.rename(Path(tmp) / 'old')
            p.write_text('new event\n')
            self.assertEqual(cursor.lines(), ['new event'])

    def test_personal_data_never_in_event_metadata(self):
        self.assertIsNone(capture.safe_log('NUXEL_INPUT JS-error password=secret'))
        self.assertIsNone(capture.safe_log('terminal output=secret'))
        row = capture.safe_log('1792330000 NUXEL_INPUT EVT touchstart x=100 y=200 tag=INPUT id=search value=secret')
        self.assertEqual(row['fields'], {'x': '100', 'y': '200', 'tag': 'INPUT', 'id': 'search'})
        self.assertNotIn('secret', str(row))

    def test_touch_capability_is_not_gpio_key(self):
        self.assertTrue(capture.bit('2', 1))
        self.assertFalse(capture.bit('0', 1))
        bitmap = hex((1 << 53) | (1 << 54) | (1 << 57))[2:]
        self.assertTrue(all(capture.bit(bitmap, b) for b in (53, 54, 57)))
        self.assertFalse(capture.bit(bitmap, 52))


if __name__ == '__main__':
    unittest.main()
