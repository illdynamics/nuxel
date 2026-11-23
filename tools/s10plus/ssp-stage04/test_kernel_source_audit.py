#!/usr/bin/env python3
"""Synthetic git trees for unrelated-edit audit (does not need vendor kernel)."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

P=Path(__file__).with_name('audit_kernel_source.py')
spec=importlib.util.spec_from_file_location('ssaudit', P)
audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


def run(repo,*cmd):
    subprocess.run(['git','-C',str(repo),*cmd],check=True,capture_output=True)


class TestKernelAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.repo=self.root/'repo'; self.repo.mkdir()
        self.patches=self.root/'patches';self.patches.mkdir()
        run(self.repo,'init','-q')
        run(self.repo,'config','user.email','test@example.invalid')
        run(self.repo,'config','user.name','test')
        (self.repo/'net/netfilter').mkdir(parents=True)
        (self.repo/'drivers/sensorhub').mkdir(parents=True)
        (self.repo/'net/netfilter/xt_DSCP.c').write_text('clean')
        (self.repo/'drivers/sensorhub/ssp.c').write_text('clean')
        run(self.repo,'add','.');run(self.repo,'commit','-qm','baseline')
        self.head=subprocess.check_output(['git','-C',str(self.repo),'rev-parse','HEAD'],text=True).strip()
        (self.patches/'0023-nuxel-ssp.patch').write_text('diff --git a/drivers/sensorhub/ssp.c b/drivers/sensorhub/ssp.c\n')

    def test_clean(self):
        d=audit.inspect(self.repo,self.patches,self.head,False)
        self.assertEqual(d['status'],'PASS')

    def test_unrelated_netfilter_is_blocking(self):
        (self.repo/'net/netfilter/xt_DSCP.c').write_text('foreign change')
        d=audit.inspect(self.repo,self.patches,self.head,True)
        self.assertEqual(d['status'],'FAIL')
        self.assertIn('net/netfilter/xt_DSCP.c',d['unexpected_modified_files'])

    def test_expected_patch_touched(self):
        (self.repo/'drivers/sensorhub/ssp.c').write_text('patch')
        self.assertEqual(audit.inspect(self.repo,self.patches,self.head,True)['status'],'PASS')
        self.assertEqual(audit.inspect(self.repo,self.patches,self.head,False)['status'],'FAIL')

    def test_wrong_commit_and_untracked(self):
        self.assertEqual(audit.inspect(self.repo,self.patches,'0'*40,False)['status'],'FAIL')
        (self.repo/'extra').write_text('foreign')
        self.assertIn('extra',audit.inspect(self.repo,self.patches,self.head,False)['untracked_files'])

if __name__=='__main__':unittest.main()
