#!/usr/bin/env python3
"""Execute transfer commands locally while dropping a successful decode receipt."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'beta/live'))
import nuxel_live as nl


class Console:
    timeout = 5
    def __init__(self): self.dropped = False
    def interrupt(self): pass
    def run(self, command, **kwargs):
        result = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=5)
        lost = 'base64 -d' in command and not self.dropped
        if lost: self.dropped = True
        return types.SimpleNamespace(ok=result.returncode == 0 and not lost,
                                     rc=result.returncode, output=result.stdout)


class RetryTest(unittest.TestCase):
    def test_lost_decode_receipt_preserves_payload(self):
        with tempfile.TemporaryDirectory(dir='/var/tmp') as tmp:
            target = Path(tmp)/'asset'
            payload = b'physical touch repair\n' * 10
            console = Console()
            result = nl.push_bytes(console, payload, str(target), mode='0644')
            self.assertTrue(console.dropped)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(result['bytes'], len(payload))
            self.assertEqual(list(Path(tmp).iterdir()), [target])


if __name__ == '__main__': unittest.main()
