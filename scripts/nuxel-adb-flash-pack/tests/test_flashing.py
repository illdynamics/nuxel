import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

HERE = Path(__file__).resolve().parents[1]
CORE = HERE / 'scripts' / 'nuxel_adb_flash.py'
spec = importlib.util.spec_from_file_location('nuxel_flash', CORE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

MOCK_ADB = r'''#!/usr/bin/env python3
import os, sys, re
from pathlib import Path
argv = sys.argv[1:]
serial = os.getenv('MOCK_SERIAL', 'S10SERIAL')
codename = os.getenv('MOCK_DEVICE', 'beyond2lte')
slot = os.getenv('MOCK_SLOT', '_a')
root = Path(os.environ['MOCK_BLOCKS'])
if argv and argv[0]=='devices':
    print('List of devices attached')
    print(serial+'\trecovery')
    sys.exit(0)
if argv[:2] == ['-s', serial]: argv=argv[2:]
else: sys.exit(4)
if argv[:1] == ['exec-out']:
    cmd=' '.join(argv[1:]); m=re.search(r'dd if=([^ ]+) bs=(\d+) count=(\d+)',cmd)
    if not m: sys.exit(5)
    part = Path(m.group(1)).name
    with (root/part).open('rb') as f:
        remain=int(m.group(2))*int(m.group(3))
        while remain:
            data=f.read(min(remain,1048576))
            if not data: break
            sys.stdout.buffer.write(data)
            remain-=len(data)
    sys.exit(0)
if argv[:1]!=['shell']:sys.exit(3)
cmd=' '.join(argv[1:])
if cmd.startswith('-T '):
    m=re.search(r'dd of=([^ ]+) bs=(\d+)',cmd)
    if not m:sys.exit(6)
    part=Path(m.group(1)).name
    with (root/part).open('r+b') as f:
        while True:
            chunk=sys.stdin.buffer.read(1048576)
            if not chunk:break
            f.write(chunk)
    sys.exit(0)
if cmd=='id -u':print('0');sys.exit(0)
if cmd.startswith('getprop'):
    prop=cmd.split()[1]
    result={'ro.product.device':codename,'ro.product.model':'mock-phone','ro.twrp.version':'3.7',
            'ro.boot.slot_suffix':slot,'ro.bootmode':'recovery'}
    print(result.get(prop,''));sys.exit(0)
if cmd.startswith('test -b '):
    part=cmd.split()[2].split('/')[-1]
    if (root/part).is_file():print('FOUND')
    sys.exit(0)
if cmd.startswith('readlink -f '):
    print('/dev/block/'+cmd.split('/')[-1]);sys.exit(0)
if cmd.startswith('blockdev --getsize64 '):
    print((root/cmd.split('/')[-1]).stat().st_size);sys.exit(0)
if cmd == 'cat /proc/mounts':
    print(os.getenv('MOCK_MOUNTS', 'rootfs / rootfs rw 0 0'));sys.exit(0)
if cmd == 'cat /proc/partitions':
    print('8 14 3072 sda14');sys.exit(0)
if cmd.startswith('ls -l '):
    print('lrwxrwxrwx boot -> /dev/block/boot');sys.exit(0)
print('unexpected mock adb command: '+cmd,file=sys.stderr)
sys.exit(7)
'''

class OfflineSafety(unittest.TestCase):
    def fake_properties(self, device='beyond2lte', slot='_a'):
        return {'device':device, 'slot_suffix':slot}

    def test_s10_defaults(self):
        a=Mock(profile='s10plus', boot_partition=None, rootfs_partition=None)
        self.assertEqual(mod.select_parts(a,self.fake_properties()), ('boot','userdata'))

    def test_g7_explicit_slot(self):
        a=Mock(profile='g7power', boot_partition='boot_a', rootfs_partition='system_a')
        self.assertEqual(mod.select_parts(a,self.fake_properties('ocean','_a')), ('boot_a','system_a'))

    def test_g7_refuses_inactive_slot(self):
        a=Mock(profile='g7power', boot_partition='boot_b', rootfs_partition='system_b')
        with self.assertRaises(mod.Abort): mod.select_parts(a,self.fake_properties('ocean','_a'))

    def test_g7_requires_targets(self):
        a=Mock(profile='g7power', boot_partition=None, rootfs_partition=None)
        with self.assertRaises(mod.Abort): mod.select_parts(a,self.fake_properties('ocean'))

    def test_denies_recovery_and_dtb(self):
        for p in ['recovery','dtbo','vbmeta','super','efs','modem_a']:
            a=Mock(profile='generic', boot_partition='boot', rootfs_partition=p)
            with self.assertRaises(mod.Abort): mod.select_parts(a,self.fake_properties())

    def test_refuses_identical_partitions(self):
        a=Mock(profile='generic', boot_partition='boot', rootfs_partition='boot')
        with self.assertRaises(mod.Abort): mod.select_parts(a,self.fake_properties())

    def test_rejects_unexpected_formats(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'img'
            p.write_bytes(b'\x3a\xff\x26\xed' + b'\x00'*2048)
            with self.assertRaises(mod.Abort): mod.inspect_image(p,'rootfs')
            p.write_bytes(b'x'*2048)
            with self.assertRaises(mod.Abort): mod.inspect_image(p,'boot')
            with self.assertRaises(mod.Abort): mod.inspect_image(p,'rootfs')

    def test_rejects_oversize(self):
        with self.assertRaises(mod.Abort):
            mod.check_images_fit({'boot':{'capacity':1},'rootfs':{'capacity':10}},
                                 {'boot':{'bytes':2},'rootfs':{'bytes':5}})

    def test_mount_guard(self):
        fake=Mock()
        fake.shell.return_value='/dev/block/dm-0 /data ext4 rw 0 0\n'
        self.assertTrue(mod.relevant_mounts(fake,'userdata','/dev/block/sda31'))

class MockedEndToEnd(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base=Path(self.t.name)
        self.bin=self.base/'bin';self.bin.mkdir()
        adb=self.bin/'adb';adb.write_text(MOCK_ADB);adb.chmod(0o755)
        self.block=self.base/'partitions';self.block.mkdir()
        self.boot=self.base/'boot.img';self.rootfs=self.base/'rootfs.img'
        boot=bytearray(8192);boot[:8]=b'ANDROID!';boot[100:110]=b'NUXEL_TEST'
        root=bytearray(1048576+4096);root[1080:1082]=b'\x53\xef';root[8000:8008]=b'ROOTTEST'
        self.boot.write_bytes(boot);self.rootfs.write_bytes(root)
        (self.block/'boot').write_bytes(b'Z'*(2*1024*1024))
        (self.block/'userdata').write_bytes(b'D'*(4*1024*1024))
        (self.block/'recovery').write_bytes(b'R'*(1024*1024))
        self.env=os.environ.copy()
        self.env['PATH']=str(self.bin)+os.pathsep+self.env.get('PATH','')
        self.env['MOCK_BLOCKS']=str(self.block)

    def invoke(self, action, *args, env=None, input_text=None):
        return subprocess.run([sys.executable,str(CORE),'--profile','s10plus','--action',action,
                               '--boot',str(self.boot),'--rootfs',str(self.rootfs),
                               '--backup-dir',str(self.base/'backups'),*args],
                              text=True,input=input_text,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env=env or self.env,timeout=30)

    def test_preflight_readonly(self):
        p=self.invoke('preflight')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('PREFLIGHT PASS',p.stdout)
        self.assertEqual((self.block/'boot').read_bytes()[:1], b'Z')

    def test_flashing_requires_execute(self):
        p=self.invoke('flash')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual((self.block/'boot').read_bytes()[:1], b'Z')

    def test_flashing_requires_double_confirmation(self):
        p=self.invoke('flash','--execute',input_text='wrong phrase\n')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual((self.block/'boot').read_bytes()[:1], b'Z')

    def test_mount_refusal(self):
        env=dict(self.env,MOCK_MOUNTS='/dev/block/dm-0 /data ext4 rw 0 0')
        p=self.invoke('preflight',env=env)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('mount appears active',p.stderr.lower())

    def test_codename_mismatch(self):
        env=dict(self.env,MOCK_DEVICE='ocean')
        p=self.invoke('preflight',env=env)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('beyond2lte',p.stderr)

    def test_end_to_end_flash_readback_backup_verify(self):
        answer='FLASH S10SERIAL boot userdata\nERASE-USERDATA\n'
        p=self.invoke('flash','--execute','--backup-recovery', input_text=answer)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('FLASH_AND_READBACK_VERIFIED',(next((self.base/'backups').iterdir())/'receipt.json').read_text())
        self.assertEqual((self.block/'boot').read_bytes()[:self.boot.stat().st_size],self.boot.read_bytes())
        self.assertEqual((self.block/'userdata').read_bytes()[:self.rootfs.stat().st_size],self.rootfs.read_bytes())
        self.assertTrue(list((self.base/'backups').rglob('boot-before.img')))
        self.assertTrue(list((self.base/'backups').rglob('recovery-before.img')))
        p=self.invoke('verify')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)

    def test_boot_only_flash_never_touches_userdata(self):
        answer='FLASH S10SERIAL boot\n'
        p=self.invoke('flash','--execute','--boot-only', input_text=answer)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        receipt=next((self.base/'backups').iterdir())/'receipt.json'
        body=receipt.read_text()
        self.assertIn('FLASH_AND_READBACK_VERIFIED',body)
        self.assertIn('"boot_only": true',body)
        self.assertNotIn('rootfs_readback_sha256',body)
        self.assertEqual((self.block/'boot').read_bytes()[:self.boot.stat().st_size],self.boot.read_bytes())
        self.assertEqual((self.block/'userdata').read_bytes()[:1],b'D', 'USERDATA must be untouched in boot-only mode')
        self.assertTrue(list((self.base/'backups').rglob('boot-before.img')))
        p=self.invoke('verify','--boot-only')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('BOOT',p.stdout)

    def test_boot_only_preflight_without_rootfs(self):
        p=subprocess.run([sys.executable,str(CORE),'--profile','s10plus','--action','preflight',
                          '--boot',str(self.boot),'--boot-only','--backup-dir',str(self.base/'backups')],
                         text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self.env,timeout=30)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('PREFLIGHT PASS',p.stdout)
        self.assertIn('BOOT-ONLY',p.stdout)
        self.assertEqual((self.block/'boot').read_bytes()[:1], b'Z')

    def test_verify_rejects_mismatch(self):
        p=self.invoke('verify')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('MISMATCH',p.stderr)

if __name__=='__main__': unittest.main()
