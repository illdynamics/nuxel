"""Credential lifecycle: no missing fallback, no implicit PIN, no mode loss."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('security', ROOT / 'services/nuxel-bridge/src/security_provider.py')
sec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sec)

class LockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = sec.SecurityProvider()
        for key in ['cred_path', 'state_path', 'biometric_path', 'policy_path']:
            setattr(self.p, key, str(Path(self.tmp.name) / (key + '.json')))
        self.p.ensure_state()
        self.fp = {'ready': False, 'enrolled': False}
        self.previous = sys.modules.get('fingerprint_provider')
        sys.modules['fingerprint_provider'] = types.SimpleNamespace(handle=lambda *a: self.fp)
        self.addCleanup(self.restore)
    def restore(self):
        if self.previous: sys.modules['fingerprint_provider'] = self.previous
        else: sys.modules.pop('fingerprint_provider', None)
    def test_methods_require_credentials(self):
        for mode in ['pin', 'pattern', 'fingerprint']:
            self.assertEqual(self.p.set_mode(mode)['error'], 'pin_required')
        self.assertEqual(self.p.set_pattern('0-4-8-5', '0-4-8-5')['error'], 'pin_required')
        self.assertEqual(self.p.status()['available_modes'], ['swipe'])
    def test_swipe_preserves_pin_and_pattern(self):
        self.assertTrue(self.p.set_pin('3838', '3838')['success'])
        self.assertEqual(self.p.status()['mode'], 'swipe')
        self.p.unlock('')
        self.assertTrue(self.p.set_pattern('0-4-8-5', '0-4-8-5')['success'])
        for mode in ['swipe', 'pin', 'pattern', 'swipe']:
            self.assertTrue(self.p.set_mode(mode)['success'])
            self.assertTrue(self.p.status()['pin_set'])
            self.assertTrue(self.p.status()['pattern_set'])
        self.p.set_mode('pattern')
        self.p.lock()
        self.assertFalse(self.p.unlock('1111')['success'])
        self.assertTrue(self.p.unlock('3838')['success'])
        self.p.lock()
        self.assertTrue(self.p.unlock('0-4-8-5')['success'])
    def test_unlimited_attempts_and_locked_changes(self):
        self.p.set_pin('3838', '3838')
        self.p.set_mode('pin')
        self.p.lock()
        self.assertFalse(self.p.set_mode('swipe')['success'])
        self.assertFalse(self.p.set_pin('6284', '6284')['success'])
        for _ in range(12):
            result = self.p.unlock('9999')
            self.assertFalse(result['success'])
            self.assertTrue(result['unlimited_attempts'])
        self.assertTrue(self.p.unlock('3838')['success'])
    def test_confirmations_and_no_pattern_to_pin_conversion(self):
        for pin in ['3', 'abc3838', '12345678901234567', '１２３４']:
            self.assertFalse(self.p.set_pin(pin, pin)['success'])
        self.assertFalse(self.p.set_pin('3838', '3839')['success'])
        self.assertFalse(self.p.apply_preset('pattern','0-4-8-5','0-4-8-5')['success'])
    def test_fingerprint_needs_provider_and_enrollment(self):
        self.p.set_pin('3838', '3838')
        self.assertFalse(self.p.set_mode('fingerprint')['success'])
        self.fp['ready'] = True
        self.assertEqual(self.p.set_mode('fingerprint')['error'], 'fingerprint_not_enrolled')
        sec._atomic_json(self.p.biometric_path, {'enrolled': True})
        self.assertTrue(self.p.set_mode('fingerprint')['success'])
        self.assertTrue(self.p.unlock('3838')['success'])
    def test_legacy_migration_retains_both_credentials(self):
        salt = 'ab'*16
        sec._atomic_json(self.p.cred_path, {'mode':'pattern','secret_kind':'pattern','salt':salt,
            'verifier':sec._derive('0-4-8-5',salt),'fallback_pin_salt':salt,'fallback_pin_verifier':sec._derive('3838',salt)})
        self.p.unlock('3838')
        self.assertTrue(self.p.set_mode('swipe')['success'])
        self.assertTrue(self.p.status()['pattern_set'])
        self.assertTrue(self.p.set_mode('pin')['success'])
        self.p.lock()
        self.assertTrue(self.p.unlock('3838')['success'])

if __name__ == '__main__': unittest.main()
