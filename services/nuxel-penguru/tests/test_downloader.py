#!/usr/bin/env python3
"""Synthetic cancellation invariants; never downloads or loads model weights."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_store import downloader as d


class CancellationTests(unittest.TestCase):
    def test_cancel_before_connection(self):
        with patch.object(d.urllib.request, 'urlopen') as connect:
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                d._download('fixture', 'https://example.invalid', '/nonexistent', 4, {'cancel': True})
            connect.assert_not_called()

    def test_cancel_before_model_load(self):
        with patch('runtime.llama_cpp.adapter.LlamaCppRuntime') as runtime:
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                d._self_test({'cancel': True}, {}, '/nonexistent')
            runtime.assert_not_called()

    def test_cancel_before_staging(self):
        with tempfile.TemporaryDirectory() as root, patch.object(d.paths, 'DOWNLOAD_ROOT', root):
            job = {'job_id': 'synthetic', 'cancel': True}
            registry = Mock()
            d._run(job, registry, {})
            self.assertEqual(job['state'], 'cancelled')
            self.assertEqual(list(Path(root).iterdir()), [])
            registry.package_dir.assert_not_called()


if __name__ == '__main__':
    unittest.main()
