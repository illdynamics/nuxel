#!/usr/bin/env python3
"""Self-contained SYNTHETIC gate regressions: NEVER a live-device acceptance.
Creates valid FDT, Android DT_TABLE and BOOT v1 fixtures in a temp directory.
Run: python3 tools/s10plus/tests/test-camera-offline-gates.py -v
"""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / 'tools/s10plus'
sys.path.insert(0, str(TOOL))
import dt_graph


def cells(*v):
    return struct.pack('>%dI' % len(v), *v)


def string(v):
    return v.encode() + b'\0'


def make_nodes():
    return {
        '/': {'compatible': string('samsung,exynos9820'),
              'model': string('Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820'),
              '#address-cells': cells(1), '#size-cells': cells(1)},
        '/gpio@0': {'phandle': cells(15), '#gpio-cells': cells(2)},
        '/clock@0': {'phandle': cells(10), '#clock-cells': cells(1)},
        '/reset@0': {'phandle': cells(11), '#reset-cells': cells(1)},
        '/phy@0': {'phandle': cells(12), '#phy-cells': cells(1)},
        '/regulator@0': {'phandle': cells(13)},
        '/pinctrl@0': {'phandle': cells(14)},
        '/i2c@0': {'#address-cells': cells(1), '#size-cells': cells(0)},
        '/i2c@0/sec-nfc@27': {'compatible': string('sec,nfc'), 'reg': cells(0x27),
                              'sec-nfc,ven-gpio': cells(15, 2, 0),
                              'sec-nfc,firm-gpio': cells(15, 3, 0),
                              'sec-nfc,irq-gpio': cells(15, 2, 0)},
        '/i2c@0/camera@30': {'compatible': string('samsung,s5k2l4'), 'reg': cells(0x30),
                            'clocks': cells(10, 1), 'resets': cells(11, 1),
                            'phys': cells(12, 1), 'vdd-supply': cells(13),
                            'pinctrl-0': cells(14), 'reset-gpios': cells(15, 9, 0)},
        '/i2c@0/camera@30/port': {},
        '/i2c@0/camera@30/port/endpoint@0': {'phandle': cells(101),
                                    'remote-endpoint': cells(100), 'data-lanes': cells(1, 2)},
        '/mipi-csis@0': {'compatible': string('samsung,exynos9820-csis')},
        '/mipi-csis@0/port': {},
        '/mipi-csis@0/port/endpoint@0': {'phandle': cells(100),
                                      'remote-endpoint': cells(101), 'data-lanes': cells(1, 2)},
        '/nfc-status': {'status': string('okay')},
        '/ssp-status': {'status': string('okay')},
        '/display-status': {'status': string('okay')},
    }


def mkfdt(nodes):
    st = bytearray()
    strings = bytearray()
    nameoffs = {}
    allpaths = sorted(nodes, key=lambda p: (p.count('/'), p))
    # implicit parents allowed for tests
    paths = set(nodes)
    for path in list(paths):
        cur = path
        while cur != '/':
            cur = cur.rsplit('/', 1)[0] or '/'
            paths.add(cur)
    parents = {}
    for path in sorted(paths):
        if path != '/':
            parent = path.rsplit('/', 1)[0] or '/'
            parents.setdefault(parent, []).append(path)
    def emit(path):
        name = '' if path == '/' else path.rsplit('/', 1)[1]
        st.extend(cells(1))
        st.extend(name.encode() + b'\0')
        st.extend(b'\0' * ((-len(st)) % 4))
        for key, val in sorted(nodes.get(path, {}).items()):
            if key not in nameoffs:
                nameoffs[key] = len(strings)
                strings.extend(key.encode() + b'\0')
            st.extend(cells(3, len(val), nameoffs[key]))
            st.extend(val)
            st.extend(b'\0' * ((-len(st)) % 4))
        for child in sorted(parents.get(path, [])):
            emit(child)
        st.extend(cells(2))
    emit('/')
    st.extend(cells(9))
    reserve = b'\0' * 16
    st_off = 40 + len(reserve)
    strings_off = st_off + len(st)
    total = strings_off + len(strings)
    header = cells(0xd00dfeed, total, st_off, strings_off, 40, 17, 16, 0, len(strings), len(st))
    return header + reserve + st + strings


def mkdtbo(first, second):
    count, header_size, entry_size, page = 2, 32, 32, 2048
    off1 = page
    off2 = (off1 + len(first) + 3) & ~3
    total = off2 + len(second)
    data = bytearray(total)
    data[:32] = cells(0xd7b7ab1e, total, header_size, entry_size, count,
                      header_size, page, 0)
    data[32:64] = cells(len(first), off1, 0, 0, 0, 0, 0, 0)
    data[64:96] = cells(len(second), off2, 0, 26, 0, 0, 0, 0)
    data[off1:off1+len(first)] = first
    data[off2:off2+len(second)] = second
    return bytes(data)


def cpio():
    out = bytearray()
    def add(name, mode, content):
        field = [1, mode, 0, 0, 1, 0, len(content), 0, 0, 0, 0, len(name)+1, 0]
        out.extend(b'070701' + ''.join('%08X' % n for n in field).encode())
        out.extend(name.encode() + b'\0')
        out.extend(b'\0' * ((-len(out)) % 4))
        out.extend(content)
        out.extend(b'\0' * ((-len(out)) % 4))
    add('init', 0o100755, b'#!/bin/sh\nexec /bin/sh\n')
    add('bin/sh', 0o100755, b'\x7fELF' + b'\0'*252)
    add('dev/console', 0o020600, b'')
    add('TRAILER!!!', 0, b'')
    return bytes(out)


def mkboot(fdt):
    kernel = bytearray(65536)
    struct.pack_into('<QQQ', kernel, 8, 0x80000, 65536, 0)
    kernel[0x38:0x3c] = b'ARM\x64'
    ram = cpio()
    header = bytearray(2048)
    header[:8] = b'ANDROID!'
    for off, value in ((8,len(kernel)), (12,0x10008000), (16,len(ram)),
                       (20,0x11000000), (24,0), (28,0), (32,0x10000100),
                       (36,2048), (40,1), (44,0x18000171), (1632,0), (1644,1648)):
        struct.pack_into('<I', header, off, value)
    body = bytes(header) + bytes(kernel)
    body += ram + b'\0' * ((-len(ram)) % 2048)
    body += fdt
    return body


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OfflineGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='camera-offline-test-')
        cls.tmp = Path(cls.temp.name)
        cls.nodes = make_nodes()
        cls.good = mkfdt(cls.nodes)
        cls.fdt = cls.tmp / 'good.fdt'
        cls.fdt.write_bytes(cls.good)
        cls.boot = cls.tmp / 'synthetic-boot.img'
        cls.boot.write_bytes(mkboot(cls.good))
        o1 = mkfdt({'/': {'dtbo-hw_rev': cells(0), 'dtbo-hw_rev_end': cells(15)}})
        o2 = mkfdt({'/': {'dtbo-hw_rev': cells(16), 'dtbo-hw_rev_end': cells(255)}})
        cls.dtbo = cls.tmp / 'synthetic-dtbo.img'
        cls.dtbo.write_bytes(mkdtbo(o1, o2))
        cls.counter = 0
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def put(self, content, suffix='.fdt'):
        type(self).counter += 1
        path = self.tmp / ('negative-%02d' % self.counter + suffix)
        path.write_bytes(content)
        return path
    def runpy(self, script, *args):
        return subprocess.run([sys.executable, str(TOOL / script), *map(str, args)],
                              capture_output=True, text=True)
    def dt(self, nodes, *, merged=True, accepted=False):
        p = self.put(mkfdt(nodes))
        args = ['--merged'] if merged else []
        r = self.runpy('camera-dt-gate.py', *args, p)
        self.assertEqual(r.returncode == 0, accepted, r.stdout+r.stderr)
        return r
    def test_01_valid_synthetic_fdt(self):
        self.dt(self.nodes, accepted=True)
        t = dt_graph.parse_fdt(self.good)
        self.assertGreater(len(t.nodes), 8)
    def test_02_bad_fdt_magic(self):
        self.assertNotEqual(self.runpy('camera-dt-gate.py', self.put(b'NOPE'+self.good[4:])).returncode, 0)
    def test_03_truncated_fdt(self):
        self.assertNotEqual(self.runpy('camera-dt-gate.py', self.put(self.good[:250])).returncode, 0)
    def test_04_wrong_model(self):
        n=copy.deepcopy(self.nodes);n['/']['model']=string('Samsung BEYOND1LTE')
        self.dt(n)
    def test_05_missing_remote_endpoint(self):
        n=copy.deepcopy(self.nodes);del n['/mipi-csis@0/port/endpoint@0']['remote-endpoint']
        self.dt(n)
    def test_06_dangling_endpoint(self):
        n=copy.deepcopy(self.nodes);n['/mipi-csis@0/port/endpoint@0']['remote-endpoint']=cells(9999)
        self.dt(n)
    def test_07_lane_mismatch(self):
        n=copy.deepcopy(self.nodes);n['/mipi-csis@0/port/endpoint@0']['data-lanes']=cells(1,2,3,4)
        self.dt(n)
    def test_08_invalid_lane_map(self):
        n=copy.deepcopy(self.nodes);n['/mipi-csis@0/port/endpoint@0']['data-lanes']=cells(1,1)
        self.dt(n)
    def test_09_i2c_collision(self):
        n=copy.deepcopy(self.nodes)
        n['/i2c@0/camera-duplicate@30']={'compatible':string('samsung,s5k2l4'),'reg':cells(0x30)}
        self.dt(n)
    def test_10_wrong_clock(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['clocks']=cells(333,1)
        self.dt(n)
    def test_11_wrong_reset(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['resets']=cells(333,1)
        self.dt(n)
    def test_12_wrong_phy(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['phys']=cells(333,1)
        self.dt(n)
    def test_13_wrong_regulator(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['vdd-supply']=cells(333)
        self.dt(n)
    def test_14_wrong_pinctrl(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['pinctrl-0']=cells(333)
        self.dt(n)
    def test_15_gpio_ownership(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['reset-gpios']=cells(15,2,0)
        self.dt(n)
    def test_16_gpio_flags(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0/camera@30']['reset-gpios']=cells(15,9,9999)
        self.dt(n)
    def test_17_fimc_csis_conflict(self):
        n=copy.deepcopy(self.nodes)
        n['/fimc-is@0']={'compatible':string('samsung,fimc-is')}
        self.dt(n)
    def test_18_valid_dtbo_selected(self):
        r=self.runpy('camera-dt-gate.py','--board-rev','26','--dtbo-idx','1',self.dtbo)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_19_wrong_dtbo_selected(self):
        r=self.runpy('camera-dt-gate.py','--board-rev','26','--dtbo-idx','0',self.dtbo)
        self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
    def test_20_missing_dtbo_selection(self):
        self.assertNotEqual(self.runpy('camera-dt-gate.py',self.dtbo).returncode,0)
    def test_21_dtbo_header_bad(self):
        b=bytearray(self.dtbo.read_bytes());struct.pack_into('>I',b,16,99999)
        self.assertNotEqual(self.runpy('camera-dt-gate.py',self.put(b,'.img')).returncode,0)
    def test_22_dtbo_entry_bad_offset(self):
        b=bytearray(self.dtbo.read_bytes());struct.pack_into('>I',b,36,0xffffffff)
        self.assertNotEqual(self.runpy('camera-dt-gate.py',self.put(b,'.img')).returncode,0)
    def test_23_dtbo_truncated(self):
        self.assertNotEqual(self.runpy('camera-dt-gate.py',self.put(self.dtbo.read_bytes()[:-10],'.img')).returncode,0)
    def test_24_golden_semantic_noop(self):
        out=self.tmp/'noop.json'
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,'--candidate',self.fdt,'--json-out',out)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertTrue(json.loads(out.read_text())['semantic_equivalent'])
    def test_25_unrelated_nfc_dt_delta(self):
        n=copy.deepcopy(self.nodes);n['/nfc-status']['status']=string('disabled')
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,'--candidate',self.put(mkfdt(n)))
        self.assertNotEqual(r.returncode,0)
    def test_26_unrelated_ssp_dt_delta(self):
        n=copy.deepcopy(self.nodes);n['/ssp-status']['status']=string('disabled')
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,'--candidate',self.put(mkfdt(n)))
        self.assertNotEqual(r.returncode,0)
    def test_27_unrelated_display_dt_delta(self):
        n=copy.deepcopy(self.nodes);n['/display-status']['status']=string('disabled')
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,'--candidate',self.put(mkfdt(n)))
        self.assertNotEqual(r.returncode,0)
    def test_28_valid_synthetic_boot(self):
        r=self.runpy('verify-boot-image.py','--partition-bytes','1000000','--json',self.boot)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(json.loads(r.stdout)[0]['appended_dtb_count'],1)
    def test_29_bad_v1_header(self):
        b=bytearray(self.boot.read_bytes());struct.pack_into('<I',b,40,99999)
        self.assertNotEqual(self.runpy('verify-boot-image.py',self.put(b,'.img')).returncode,0)
    def test_30_wrong_page_size(self):
        b=bytearray(self.boot.read_bytes());struct.pack_into('<I',b,36,4096)
        self.assertNotEqual(self.runpy('verify-boot-image.py',self.put(b,'.img')).returncode,0)
    def test_31_gzip_kernel_payload(self):
        b=bytearray(self.boot.read_bytes());b[2048:2050]=b'\x1f\x8b'
        self.assertNotEqual(self.runpy('verify-boot-image.py',self.put(b,'.img')).returncode,0)
    def test_32_missing_appended_dtb(self):
        b=bytearray(self.boot.read_bytes()); b[-len(self.good):]=b'\0'*len(self.good)
        self.assertNotEqual(self.runpy('verify-boot-image.py',self.put(b,'.img')).returncode,0)
    def test_33_bad_appended_totalsize(self):
        b=bytearray(self.boot.read_bytes()); off=len(b)-len(self.good)
        struct.pack_into('>I',b,off+4,len(b)*8)
        self.assertNotEqual(self.runpy('verify-boot-image.py',self.put(b,'.img')).returncode,0)
    def test_34_partition_overflow(self):
        self.assertNotEqual(self.runpy('verify-boot-image.py','--partition-bytes','2048',self.boot).returncode,0)
    def test_35_boot_hash_mismatch(self):
        self.assertNotEqual(self.runpy('verify-boot-image.py','--expect-boot-sha256','0'*64,self.boot).returncode,0)
    def test_36_kernel_hash_mismatch(self):
        self.assertNotEqual(self.runpy('verify-boot-image.py','--expect-kernel-sha256','0'*64,self.boot).returncode,0)
    def test_37_ramdisk_hash_mismatch(self):
        self.assertNotEqual(self.runpy('verify-boot-image.py','--expect-ramdisk-sha256','0'*64,self.boot).returncode,0)
    def test_38_appended_dtb_hash_mismatch(self):
        self.assertNotEqual(self.runpy('verify-boot-image.py','--expect-dtb-sha256','0'*64,self.boot).returncode,0)
    def test_39_release_requires_manifest(self):
        self.assertNotEqual(self.runpy('camera-release-gate.py','--candidate-boot',self.boot).returncode,0)
    def test_40_release_rejects_unsigned_manifest(self):
        manifest=self.put(b'{}','.json')
        self.assertNotEqual(self.runpy('camera-release-gate.py','--manifest',manifest,
                           '--candidate-boot',self.boot).returncode,0)
    def test_41_bad_address_cells(self):
        n=copy.deepcopy(self.nodes);n['/i2c@0']['#address-cells']=cells(2)
        self.dt(n)
    def test_42_semantic_padding_equivalence(self):
        extra=self.put(self.good+b'\0'*16)
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,'--candidate',extra)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_43_unrelated_allowlist_cannot_bypass(self):
        n=copy.deepcopy(self.nodes);n['/nfc-status']['status']=string('disabled')
        target=self.put(mkfdt(n))
        al=self.tmp/'bad-allowlist.json'
        al.write_text(json.dumps({'schema':'nuxel.camera.dt-allowlist/v1',
          'changes':[{'path':'/nfc-status','property':'status','kind':'dependency',
                      'reason':'trying to bypass protected NFC owner'}]}))
        r=self.runpy('camera-dt-diff.py','--baseline',self.fdt,
                        '--candidate',target,'--allowlist',al)
        self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
    def test_44_valid_signed_synthetic_noop(self):
        if not shutil.which('openssl'):
            self.skipTest('openssl unavailable')
        base=self.tmp/'golden-synthetic-boot.img';base.write_bytes(self.boot.read_bytes())
        dtb=self.tmp/'golden-synthetic-dtb.fdt';dtb.write_bytes(self.good)
        dtbo=self.dtbo
        merged=self.fdt
        rec=self.tmp/'synthetic-recovery.bin';rec.write_bytes(b'SYNTHETIC - NOT A RECOVERY IMAGE')
        brd=self.tmp/'synthetic-board-evidence.txt';brd.write_text('SYNTHETIC ONLY')
        plan=self.tmp/'synthetic-rollback-plan.txt';plan.write_text('SYNTHETIC ONLY: NO RESTORE TEST')
        def desc(path):return {'path':str(path),'sha256':file_sha(path),'size_bytes':path.stat().st_size}
        artifacts={'boot':desc(base),'dtb':desc(dtb),'dtbo':desc(dtbo),
                   'merged_fdt':desc(merged),'recovery':desc(rec),
                   'selected_board_evidence':desc(brd),'rollback_plan':desc(plan)}
        manifest={'schema':'nuxel.camera.prompt00/v1',
            'capture_utc':datetime.now(timezone.utc).isoformat(),
            'device':{'model':'SM-G975F','codename':'beyond2lte',
                      'board_revision':26,'dtbo_index':1,'dt_layout':'boot-appended','appended_dtb_index':0,
                      'status':'NUXEL_HEALTHY'},'artifacts':artifacts,
            'partitions':{'boot_bytes':1000000,'dtb_bytes':1000000,'dtbo_bytes':1000000},
            'proof':{'off_device':True,'rollback_ready':True,'selected_overlay_verified':True,
                     'active_tree_matches_onflash':True,
                     'boot_readback_sha256':file_sha(base),
                     'dtb_readback_sha256':file_sha(dtb),
                     'dtbo_readback_sha256':file_sha(dtbo)}}
        m=self.tmp/'SYNTHETIC_DO_NOT_USE_manifest.json';m.write_text(json.dumps(manifest))
        priv=self.tmp/'SYNTHETIC_DO_NOT_USE_private.pem';pub=self.tmp/'SYNTHETIC_DO_NOT_USE_public.pem'
        sig=self.tmp/'synthetic.sig';receipts=self.tmp/'synthetic-receipts'
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048',
                        '-out',str(priv)],capture_output=True,check=True)
        subprocess.run(['openssl','pkey','-in',str(priv),'-pubout','-out',str(pub)],capture_output=True,check=True)
        subprocess.run(['openssl','dgst','-sha256','-sign',str(priv),'-out',str(sig),str(m)],capture_output=True,check=True)
        args=['--manifest',m,'--signature',sig,'--trusted-pubkey',pub,
              '--candidate-boot',base,'--candidate-dtb',dtb,'--candidate-dtbo',dtbo,
              '--candidate-merged',merged,'--receipt-dir',receipts,'--receipt-signing-key',priv]
        r=self.runpy('camera-release-gate.py',*args)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertEqual(json.loads(r.stdout)['result'],'PASS_OFFLINE_ONLY')
        self.assertTrue((receipts/'camera-release-receipt.json.sig').exists())
        # Missing rollback evidence is not accepted EVEN if a test signer
        # re-signs the manifest: check the actual validated fields/files.
        for label, change in [
          ('no-rollback', lambda x: x['artifacts'].pop('rollback_plan')),
          ('no-backup', lambda x: x['artifacts'].pop('boot')),
          ('no-recovery', lambda x: x['artifacts'].pop('recovery')),
          ('unhealthy', lambda x: x['device'].update(status='TWRP')),
          ('wrong-board', lambda x: x['device'].update(model='SM-G973F')),
          ('wrong-overlay', lambda x: x['device'].update(dtbo_index=0)),
          ('wrong-readback', lambda x: x['proof'].update(boot_readback_sha256='0'*64)),
          ('rollback-false', lambda x: x['proof'].update(rollback_ready=False)),
          ('no-trust', lambda x: x['proof'].update(active_tree_matches_onflash=False)),
        ]:
            modified=copy.deepcopy(manifest)
            change(modified)
            badfile=self.tmp/('signed-synthetic-'+label+'.json')
            badfile.write_text(json.dumps(modified))
            badsig=self.tmp/('signed-synthetic-'+label+'.sig')
            subprocess.run(['openssl','dgst','-sha256','-sign',str(priv),
                            '-out',str(badsig),str(badfile)],capture_output=True,check=True)
            badargs=list(args)
            badargs[badargs.index('--manifest')+1]=badfile
            badargs[badargs.index('--signature')+1]=badsig
            result=self.runpy('camera-release-gate.py',*badargs)
            self.assertNotEqual(result.returncode,0,label+': '+result.stdout+result.stderr)
        # Hash mismatch/absent rollback proof must fail even with the valid signature.
        br=copy.deepcopy(manifest);br['artifacts']['boot']['sha256']='0'*64
        altered=self.tmp/'tampered.json';altered.write_text(json.dumps(br))
        r=self.runpy('camera-release-gate.py',*(args[:args.index(m)]+[altered]+args[args.index(m)+1:]))
        self.assertNotEqual(r.returncode,0)
        r=self.runpy('camera-release-gate.py',*(args[:args.index('--candidate-dtb')]+[
            '--candidate-dtb',self.put(self.good+b'X')]+args[args.index('--candidate-dtbo'):]))
        self.assertNotEqual(r.returncode,0)

        # SYNTHETIC ONLY: exercise the combined known-good STOCK shared GPIO
        # and genuine separate-DTB/DTBO boot layout under signed evidence.
        stock = self.tmp / 'SYNTHETIC_stock-live.fdt'
        stock.write_bytes(mkfdt(self.stock_flash_nodes()))
        separate_boot = self.tmp / 'SYNTHETIC_separate-boot.img'
        separate_boot.write_bytes(mkboot(self.good)[:-len(self.good)])
        separate = copy.deepcopy(manifest)
        separate['device']['dt_layout'] = 'separate-dtb-dtbo'
        separate['device']['appended_dtb_index'] = None
        separate['proof']['bootloader_dt_source_verified'] = True
        for name, path in (('boot',separate_boot),('dtb',stock),('merged_fdt',stock)):
            separate['artifacts'][name] = desc(path)
        for name in ('boot', 'dtb'):
            separate['proof'][name + '_readback_sha256'] = separate['artifacts'][name]['sha256']
        separate_m = self.tmp / 'SYNTHETIC_signed-separate-manifest.json'
        separate_m.write_text(json.dumps(separate))
        separate_sig = self.tmp / 'SYNTHETIC_signed-separate-manifest.sig'
        subprocess.run(['openssl','dgst','-sha256','-sign',str(priv),
                        '-out',str(separate_sig),str(separate_m)],capture_output=True,check=True)
        separate_args = list(args)
        for flag, value in [('--manifest',separate_m),('--signature',separate_sig),
                            ('--candidate-boot',separate_boot),('--candidate-dtb',stock),
                            ('--candidate-merged',stock),
                            ('--receipt-dir',self.tmp / 'synthetic-separate-receipts')]:
            separate_args[separate_args.index(flag)+1] = value
        no = self.runpy('camera-release-gate.py',*separate_args)
        self.assertEqual(no.returncode,0,no.stdout+no.stderr)
        self.assertEqual(json.loads(no.stdout)['result'],'PASS_OFFLINE_ONLY')
        # Any signed assertion with the bootloader selection proof removed is
        # rejected even though all image bytes remain identical.
        unproven = copy.deepcopy(separate)
        unproven['proof']['bootloader_dt_source_verified'] = False
        unproven_m = self.tmp/'SYNTHETIC_unproven-separate.json'
        unproven_m.write_text(json.dumps(unproven))
        unproven_sig = self.tmp/'SYNTHETIC_unproven-separate.sig'
        subprocess.run(['openssl','dgst','-sha256','-sign',str(priv),
                        '-out',str(unproven_sig),str(unproven_m)],capture_output=True,check=True)
        bad_args = list(separate_args)
        bad_args[bad_args.index('--manifest')+1] = unproven_m
        bad_args[bad_args.index('--signature')+1] = unproven_sig
        no = self.runpy('camera-release-gate.py',*bad_args)
        self.assertNotEqual(no.returncode,0,no.stdout+no.stderr)

    def stock_flash_nodes(self):
        nodes = copy.deepcopy(self.nodes)
        nodes['/mipi-csis@0']['status'] = string('disabled')  # vendor baseline, native CSIS not active
        nodes['/gpio@1'] = {'phandle': cells(16), '#gpio-cells': cells(2)}
        nodes['/s2mpb02_pmic@59/torch'] = {
            'torch-gpios': cells(15, 4, 0, 16, 6, 0),
            'compatible': string('samsung,pmic-torch')}
        nodes['/fimc-is-flash-gpio@0'] = {
            'flash-gpios': cells(15, 4, 0, 16, 6, 0),
            'compatible': string('samsung,fimc-is-flash-gpio')}
        return nodes

    def test_45_preexisting_stock_flash_claim_requires_golden(self):
        nodes = self.stock_flash_nodes()
        fdt = self.put(mkfdt(nodes))
        # A naked duplicated GPIO is a hard failure (even if it *looks* stock).
        no = self.runpy('camera-dt-gate.py', '--merged', fdt)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)
        # Exact, hash-pinned live golden evidence permits a byte-identical overlap.
        yes = self.runpy('camera-dt-gate.py', '--merged',
                         '--golden-merged', fdt,
                         '--golden-merged-sha256', file_sha(fdt), fdt)
        self.assertEqual(yes.returncode, 0, yes.stdout+yes.stderr)

    def test_46_new_camera_owner_cannot_reuse_stock_flash_pin(self):
        baseline = self.put(mkfdt(self.stock_flash_nodes()))
        nodes = self.stock_flash_nodes()
        nodes['/i2c@0/camera@30']['torch-gpios'] = cells(15, 4, 0)
        candidate = self.put(mkfdt(nodes))
        no = self.runpy('camera-dt-gate.py', '--merged',
                        '--golden-merged', baseline,
                        '--golden-merged-sha256', file_sha(baseline), candidate)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)
        self.assertIn('NEW/ALTERED GPIO conflict', no.stdout)

    def test_47_mutated_stock_flash_flag_is_not_waived(self):
        baseline = self.put(mkfdt(self.stock_flash_nodes()))
        nodes = self.stock_flash_nodes()
        nodes['/fimc-is-flash-gpio@0']['flash-gpios'] = cells(15, 4, 0, 16, 6, 1)
        candidate = self.put(mkfdt(nodes))
        no = self.runpy('camera-dt-gate.py', '--merged',
                        '--golden-merged', baseline,
                        '--golden-merged-sha256', file_sha(baseline), candidate)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)

    def test_48_untrusted_or_mutated_golden_cannot_waive_conflict(self):
        fdt = self.put(mkfdt(self.stock_flash_nodes()))
        for args in [('--golden-merged', fdt),
                     ('--golden-merged-sha256', file_sha(fdt)),
                     ('--golden-merged', fdt, '--golden-merged-sha256', '0'*64)]:
            no = self.runpy('camera-dt-gate.py', '--merged', *args, fdt)
            self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)

    def separate_args(self, base, overlay, merged, idx=1, rev=26):
        return ['--separate-dtb-path', base, '--separate-dtb-sha256', file_sha(base),
                '--separate-dtbo-path', overlay, '--separate-dtbo-sha256', file_sha(overlay),
                '--separate-merged-path', merged, '--separate-merged-sha256', file_sha(merged),
                '--separate-dtbo-index', str(idx), '--separate-board-revision', str(rev)]

    def test_49_separate_dtb_with_complete_pinned_sources(self):
        noapp = self.put(mkboot(self.good)[:-len(self.good)], '.img')
        no = self.runpy('verify-boot-image.py', noapp)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)
        yes = self.runpy('verify-boot-image.py', '--json',
                         *self.separate_args(self.fdt, self.dtbo, self.fdt), noapp)
        self.assertEqual(yes.returncode, 0, yes.stdout+yes.stderr)
        self.assertEqual(json.loads(yes.stdout)[0]['appended_dtb_count'], 0)

    def test_50_separate_layout_mismatch_fails_closed(self):
        noapp = self.put(mkboot(self.good)[:-len(self.good)], '.img')
        cases = [self.separate_args(self.fdt, self.dtbo, self.fdt, idx=0),
                 self.separate_args(self.fdt, self.dtbo, self.fdt, rev=15),
                 self.separate_args(self.fdt, self.dtbo, self.fdt)[:-2]]
        for args in cases:
            no = self.runpy('verify-boot-image.py', *args, noapp)
            self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)
        invalid = self.separate_args(self.fdt, self.dtbo, self.fdt)
        invalid[3] = '0'*64
        no = self.runpy('verify-boot-image.py', *invalid, noapp)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)
        # Signed separate-DT claims cannot make a BOOT image with nonzero
        # trailing payload silently switch to another DT layout.
        mixed = self.put(mkboot(self.good), '.img')
        no = self.runpy('verify-boot-image.py',
                        *self.separate_args(self.fdt, self.dtbo, self.fdt), mixed)
        self.assertNotEqual(no.returncode, 0, no.stdout+no.stderr)

    def test_51_release_manifest_demands_explicit_dt_layout(self):
        # Untested assertions in JSON cannot replace owner-trusted evidence.
        import importlib.util
        spec = importlib.util.spec_from_file_location('camrelease', TOOL / 'camera-release-gate.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            module.check_manifest({'schema':'nuxel.camera.prompt00/v1',
                                   'capture_utc':datetime.now(timezone.utc).isoformat(),
                                   'device':{'model':'SM-G975F','codename':'beyond2lte',
                                             'status':'NUXEL_HEALTHY','board_revision':26,
                                             'dtbo_index':1,'appended_dtb_index':0},
                                   'proof':{}})
        except ValueError as exc:
            self.assertIn('explicit boot-appended vs separate-DT layout', str(exc))
        else:
            self.fail('manifest without DT layout was wrongly accepted')

if __name__ == '__main__':
    unittest.main(verbosity=2)
