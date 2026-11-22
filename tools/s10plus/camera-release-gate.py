#!/usr/bin/env python3
"""Offline-only evidence-backed camera release gate. Never flashes or touches hardware.

This is a gate, NOT independent attestation of physical device health: the owner
must first verify Prompt 00 capture provenance and trusted signing key out of
band. An unsigned or absent live baseline always means FAIL/NO-FLASH.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import dt_graph
from importlib.machinery import SourceFileLoader


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def verify_sig(path, signature, public_key):
    result = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', public_key,
                             '-signature', signature, path], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('signed manifest verification FAILED: %s' % result.stderr.strip())


def checked(path, expect, label, private=False):
    p = Path(path).resolve(strict=True)
    if not p.is_file() or p.stat().st_size < 1:
        raise ValueError('%s missing/empty' % label)
    if private and (p == ROOT or ROOT in p.parents):
        raise ValueError('%s is inside checkout; private backups must remain OFF repository' % label)
    if not isinstance(expect, dict) or not expect.get('sha256') or not expect.get('size_bytes'):
        raise ValueError('%s lacks SHA256 and size attestation' % label)
    if p.stat().st_size != expect['size_bytes'] or sha_file(p) != expect['sha256']:
        raise ValueError('%s SHA256/size mismatch' % label)
    return str(p)


def check_manifest(m):
    if m.get('schema') != 'nuxel.camera.prompt00/v1':
        raise ValueError('wrong Prompt 00 manifest schema')
    try:
        when = datetime.fromisoformat(m['capture_utc'].replace('Z', '+00:00'))
        if when.tzinfo is None:
            raise ValueError('capture_utc must have timezone')
        age = (datetime.now(timezone.utc) - when).total_seconds()
        if age < -300 or age > 72 * 3600:
            raise ValueError('Prompt 00 snapshot missing freshness (<72h)')
        dev = m['device']
        if dev['model'] != 'SM-G975F' or dev['codename'] != 'beyond2lte' or \
                dev['status'] != 'NUXEL_HEALTHY' or not isinstance(dev['board_revision'], int) or \
                not isinstance(dev['dtbo_index'], int):
            raise ValueError('active board/kernel/overlay identity not proven')
        layout = dev.get('dt_layout')
        if layout not in ('boot-appended', 'separate-dtb-dtbo'):
            raise ValueError('explicit boot-appended vs separate-DT layout required')
        if layout == 'boot-appended':
            if not isinstance(dev.get('appended_dtb_index'), int) or dev['appended_dtb_index'] < 0:
                raise ValueError('appended DT selection not independently proven')
        elif ('appended_dtb_index' in dev and dev['appended_dtb_index'] is not None) or \
                m['proof'].get('bootloader_dt_source_verified') is not True:
            raise ValueError('separate-DT layout needs no appended selection AND verified bootloader source proof')
        proof = m['proof']
        if proof.get('off_device') is not True or proof.get('rollback_ready') is not True or \
                proof.get('selected_overlay_verified') is not True or \
                proof.get('active_tree_matches_onflash') is not True:
            raise ValueError('Prompt 00 physical verification/rollback not PASS')
        arts = m['artifacts']
        out = {}
        for key in ('boot', 'dtb', 'dtbo', 'merged_fdt', 'recovery',
                    'selected_board_evidence', 'rollback_plan'):
            a = arts[key]
            out[key] = checked(a['path'], a, key, private=(key in ('boot', 'dtb', 'dtbo', 'recovery')))
        for key in ('boot', 'dtb', 'dtbo'):
            if proof.get(key + '_readback_sha256') != arts[key]['sha256']:
                raise ValueError('readback hash mismatch for %s' % key)
        limits = m['partitions']
        for key in ('boot', 'dtb', 'dtbo'):
            cap = limits[key + '_bytes']
            if not isinstance(cap, int) or cap <= 0 or arts[key]['size_bytes'] > cap:
                raise ValueError('unverified %s partition size/overflow' % key)
        if m['device']['board_revision'] < 0 or m['device']['board_revision'] > 255:
            raise ValueError('board revision outside supported range')
        return out
    except (KeyError, TypeError, AttributeError, OSError) as e:
        raise ValueError('incomplete Prompt 00 manifest: %s' % e)


def call_tool(tool, args):
    cmd = [sys.executable, str(ROOT / 'tools/s10plus' / tool), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise ValueError('%s failed (exit %s): %s %s' %
                         (tool, result.returncode, result.stdout[-1800:], result.stderr[-1000:]))
    return result.stdout


def audit(a):
    rep = {'gate': 'nuxel-camera-release-gate/v1', 'result': 'FAIL',
           'not_a_physical_boot_test': True, 'steps': {}, 'artifacts': {}}
    def passed(key, note):
        rep['steps'][key] = 'PASS'
        rep['artifacts'][key] = note
    try:
        if not all([a.manifest, a.signature, a.trusted_pubkey, a.candidate_boot,
                    a.candidate_dtb, a.candidate_dtbo, a.candidate_merged, a.receipt_dir,
                    a.receipt_signing_key]):
            raise ValueError('all signed manifest, boot, dtb/dtbo, candidate merged and receipt options mandatory')
        verify_sig(a.manifest, a.signature, a.trusted_pubkey)
        with open(a.manifest, encoding='utf-8') as f:
            m = json.load(f)
        paths = check_manifest(m)
        approval = None
        if a.candidate_approval or a.candidate_approval_signature:
            if not a.candidate_approval or not a.candidate_approval_signature:
                raise ValueError('both signed candidate approval files mandatory')
            verify_sig(a.candidate_approval, a.candidate_approval_signature, a.trusted_pubkey)
            with open(a.candidate_approval) as f:
                approval = json.load(f)
            if approval.get('schema') != 'nuxel.camera.candidate-approval/v1' or \
                    approval.get('golden_manifest_sha256') != rep.get('manifest_sha256', sha_file(a.manifest)):
                raise ValueError('candidate approval not tied to golden capture')
        passed('ROLLBACK_READY', 'Prompt 00 signed manifest + off-device backup hashes checked')
        rep['manifest_sha256'] = sha_file(a.manifest)
        dev = m['device']
        # Board identity must bind both signed manifest and decoded active FDT.
        active = dt_graph.parse_fdt(dt_graph.extract_fdts(open(paths['merged_fdt'], 'rb').read())[0])
        comp = active.get('/').props.get('compatible')
        models = active.get('/').props.get('model')
        if not comp or not any('exynos9820' in c.lower() for c in comp.strings) or \
                (models and models.strings and not any('beyond2lte' in x.lower() for x in models.strings)):
            raise ValueError('active merged FDT does not prove beyond2lte exynos9820 model')
        passed('ACTIVE_BOARD_MATCH', {'model': dev['model'], 'rev': dev['board_revision'],
                                     'overlay_entry': dev['dtbo_index']})
        # Offline no-change must bind all input member SHA256s. Changed BOOT
        # requires separately signed, exact member approval.
        bootargs = [a.candidate_boot, '--json', '--partition-bytes', str(m['partitions']['boot_bytes'])]
        separate = None
        if dev['dt_layout'] == 'boot-appended':
            bootargs += ['--selected-appended-dtb-index', str(dev['appended_dtb_index'])]
        else:
            # Source of these hashes is the owner-signed private Prompt00 manifest.
            # The verifier independently verifies all three source files and their
            # layout. Never accept an unsupported --no-dtb / absent-DT switch.
            separate = {
                'dtb_path': paths['dtb'], 'dtb_sha256': m['artifacts']['dtb']['sha256'],
                'dtbo_path': paths['dtbo'], 'dtbo_sha256': m['artifacts']['dtbo']['sha256'],
                'merged_path': paths['merged_fdt'], 'merged_sha256': m['artifacts']['merged_fdt']['sha256'],
                'dtbo_index': dev['dtbo_index'], 'board_revision': dev['board_revision'],
            }
            for key, value in separate.items():
                bootargs += ['--separate-' + key.replace('_', '-'), str(value)]
        if sha_file(a.candidate_boot) == m['artifacts']['boot']['sha256']:
            bootargs += ['--expect-boot-sha256', m['artifacts']['boot']['sha256']]
        else:
            if not all([a.candidate_approval, a.candidate_approval_signature]):
                raise ValueError('modified BOOT needs independently signed candidate/member approval')
            for key, flag in (('boot', '--expect-boot-sha256'), ('kernel', '--expect-kernel-sha256'),
                              ('ramdisk', '--expect-ramdisk-sha256'), ('dtb', '--expect-dtb-sha256')):
                v = approval.get(key + '_sha256')
                if not isinstance(v, str) or len(v) != 64:
                    raise ValueError('candidate source member hash missing: ' + key)
                bootargs += [flag, v]
        result = json.loads(call_tool('verify-boot-image.py', bootargs))
        if any(item.get('result') != 'PASS' for item in result):
            raise ValueError('BOOT container gate returned failure')
        # BOOT-only release may change the kernel, but Prompt01 does not have
        # a reproducible Samsung base/overlay merge implementation. Until a
        # separately audited merge proof exists, the selected appended DTB
        # must remain byte-identical to the current known-good BOOT member.
        from importlib import util
        v_spec = util.spec_from_file_location('boot_verify', ROOT / 'tools/s10plus/verify-boot-image.py')
        # Import runs no write actions; inspect returns the selected FDT hash.
        v_mod = util.module_from_spec(v_spec)
        v_spec.loader.exec_module(v_mod)
        g = v_mod.Gate()
        original = v_mod.inspect(paths['boot'], m['partitions']['boot_bytes'], g,
                   selected_appended_idx=dev.get('appended_dtb_index'),
                   separate_dt_evidence=separate)
        if g.failures or not original.get('dtb_sha256'):
            raise ValueError('golden BOOT DT source is malformed: ' + '; '.join(g.failures))
        if result[0].get('dtb_sha256') != original['dtb_sha256']:
            raise ValueError('candidate BOOT changes trusted DTB source: NO-FLASH')
        passed('BOOT_CONTAINER_PASS', result[0]['sha256'])
        # Candidate table must have *exact* partition size and independently
        # explicit entry selection. Never default to revision 26/index 9.
        for name in ('dtb', 'dtbo'):
            candidate = getattr(a, 'candidate_' + name)
            cap = m['partitions'][name + '_bytes']
            if os.path.getsize(candidate) > cap:
                raise ValueError('%s candidate partition overflow' % name)
        dtargs = ['--json', '--board-rev', str(dev['board_revision']), '--dtbo-idx', '0', a.candidate_dtb]
        result = json.loads(call_tool('camera-dt-gate.py', dtargs))
        result += json.loads(call_tool('camera-dt-gate.py',
                 ['--json', '--merged', '--golden-merged', paths['merged_fdt'],
                  '--golden-merged-sha256', m['artifacts']['merged_fdt']['sha256'],
                  a.candidate_merged]))
        if any(item.get('result') != 'PASS' for item in result):
            raise ValueError('camera graph gate failed')
        dtresult = json.loads(call_tool('camera-dt-gate.py',
                             ['--json', '--board-rev', str(dev['board_revision']),
                              '--dtbo-idx', str(dev['dtbo_index']), a.candidate_dtbo]))
        if any(item.get('result') != 'PASS' for item in dtresult):
            raise ValueError('selected overlay failed camera graph gate')
        passed('CAMERA_DT_GRAPH_PASS', 'parsed candidate DTB + selected DTBO entry + candidate merged tree')
        # Separate DTB/DTBO writes are explicitly forbidden at this Prompt01
        # stage. No "signed approval" can substitute for owner go-ahead plus
        # independent reconstruction of the active Samsung overlay merge.
        if sha_file(a.candidate_dtb) != m['artifacts']['dtb']['sha256'] or \
                sha_file(a.candidate_dtbo) != m['artifacts']['dtbo']['sha256']:
            raise ValueError('candidate modifies separate DTB/DTBO partitions; BLOCK until explicitly authorized future stage')
        # Candidate merged graph must be available offline. Missing merge is NOT
        # recoverable by optimistic containment assumptions.
        import importlib.util
        spec = importlib.util.spec_from_file_location('camera_dt_diff', ROOT / 'tools/s10plus/camera-dt-diff.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        allow = mod.load_allow(a.allowlist)
        if allow and (not approval or approval.get('allowlist_sha256') != sha_file(a.allowlist)):
            raise ValueError('camera/dependency allowlist requires hash-bound signed approval')
        if approval and approval.get('candidate_merged_sha256') and \
                approval['candidate_merged_sha256'] != sha_file(a.candidate_merged):
            raise ValueError('candidate merged FDT differs from approved member')
        d = mod.diff(paths['merged_fdt'], a.candidate_merged, allow)
        rep['dt_semantic_diff'] = d
        if d['result'] != 'PASS':
            raise ValueError('%d unapproved merged-FDT property changes' % len(d['unapproved']))
        passed('NO_UNRELATED_DT_DELTA', {'changes': len(d['changes']),
                                          'unapproved': len(d['unapproved'])})
        # source proof only: this does not verify Samsung proprietary merge
        # correctness. The Prompt00 active-onflash evidence is indispensable.
        passed('MERGED_FDT_PROOF', 'candidate merged semantic diff checked against signed active FDT')
        rep['result'] = 'PASS_OFFLINE_ONLY'
    except (ValueError, OSError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as e:
        rep['failures'] = [str(e)]
    return rep


def main():
    ap = argparse.ArgumentParser()
    for key in ('manifest', 'signature', 'trusted-pubkey', 'candidate-boot',
                'candidate-dtb', 'candidate-dtbo', 'candidate-merged', 'allowlist',
                'candidate-approval', 'candidate-approval-signature', 'receipt-dir',
                'receipt-signing-key'):
        ap.add_argument('--' + key)
    a = ap.parse_args()
    rep = audit(a)
    print(json.dumps(rep, indent=2, sort_keys=True))
    # Always produce hashed audit when a receipt folder is supplied. A PASS
    # needs a signed receipt; signing failure converts it to hard FAIL.
    if a.receipt_dir:
        os.makedirs(a.receipt_dir, exist_ok=True)
        target = Path(a.receipt_dir) / 'camera-release-receipt.json'
        target.write_text(json.dumps(rep, indent=2, sort_keys=True) + '\n')
        digest = sha_file(target)
        (target.parent / 'camera-release-receipt.sha256').write_text(digest + '  ' + target.name + '\n')
        if rep['result'] == 'PASS_OFFLINE_ONLY':
            r = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', a.receipt_signing_key,
                                '-out', str(target) + '.sig', str(target)], capture_output=True)
            if r.returncode:
                print('FAIL: signing receipt failed: %s' % r.stderr.decode(errors='replace'))
                return 1
    return 0 if rep['result'] == 'PASS_OFFLINE_ONLY' else 1

if __name__ == '__main__':
    sys.exit(main())
