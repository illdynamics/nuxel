#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

P=Path(__file__).with_name('verify_stage05_gate.py')
spec=importlib.util.spec_from_file_location('ssp05gate',P)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
ROOT=Path(__file__).resolve().parents[3]

class TestGate(unittest.TestCase):
    def test_historical_no_flash_is_rejected(self):
        d=json.loads((ROOT/'reports/SSP-CANDIDATE-PREFLIGHT.json').read_text())
        self.assertEqual(g.validate(d)['verdict'],'NO_FLASH')

    def test_every_gate_must_pass_not_partial(self):
        data={'overall_verdict':'PASS','gates':{k:{'status':'PASS'} for k in g.MANDATORY}}
        self.assertEqual(g.validate(data)['verdict'],'PASS_REPORTED_GATES_ONLY')
        data['gates']['G_BOOT_ROLLBACK_STAGING']['status']='PARTIAL'
        self.assertEqual(g.validate(data)['verdict'],'NO_FLASH')

    def test_missing_gate_rejected(self):
        self.assertEqual(g.validate({'overall_verdict':'PASS', 'gates':{}})['verdict'],'NO_FLASH')

if __name__ == '__main__': unittest.main()
