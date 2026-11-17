from collections import deque
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.llama_cpp.adapter import LlamaCppRuntime


class WorkerProtocolTests(unittest.TestCase):
    def events(self, script):
        process = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        process.penguru_diagnostics = deque(maxlen=16)
        try:
            return list(LlamaCppRuntime(runner=False)._events(process))
        finally:
            process.stdout.close()

    def test_multiline_response_is_encoded_in_token_events(self):
        result = self.events('import json; print(json.dumps({"event":"token","text":"print(\\\"hello\\\")\\n"})); print(json.dumps({"event":"done","generated_tokens":1}))')
        self.assertEqual([item['event'] for item in result], ['token', 'done'])

    def test_malformed_output_fails_loudly(self):
        result = self.events('print(\'{"event":"done","output":"unescaped"quote"}\')')
        self.assertEqual(result[0]['code'], 'worker_protocol_error')

    def test_abnormal_exit_is_reported(self):
        result = self.events('raise SystemExit(7)')
        self.assertEqual(result[0]['code'], 'worker_exit')
        self.assertIn('status 7', result[0]['detail'])

    def test_stalled_worker_is_killed(self):
        timer = threading.Timer
        with patch('runtime.llama_cpp.adapter.threading.Timer', side_effect=lambda delay, callback: timer(.1, callback)):
            result = self.events('import time; time.sleep(10)')
        self.assertEqual(result[-1]['code'], 'worker_timeout')


if __name__ == '__main__':
    unittest.main()
