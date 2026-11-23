#!/usr/bin/env python3
"""Read-only Stage-04 kernel-tree lineage / unrelated-edit guard.

Never cleans, resets, checks out, rewrites, or deletes source files. In a
fresh source tree, run before patching. In an already patched tree, pass
--allow-patch-touched to permit modifications exactly limited to repository
patch target paths. This does NOT prove content equals the patch series:
independent patch applicability and build checks are mandatory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PINNED = 'f7194c1d15eded1c2a1a4dc63825b26103435cc0'


def git(src: Path, *args: str) -> str:
    p = subprocess.run(['git', '-C', str(src), *args],
                       capture_output=True, text=True, check=False)
    if p.returncode:
        raise ValueError('git ' + ' '.join(args) + ': ' + p.stderr.strip())
    return p.stdout


def patch_targets(patches: Path) -> set[str]:
    paths = set()
    for patch in patches.glob('*.patch'):
        # The paths are repo-relative git-diff paths. Retired patches are not
        # included. Include all active patches, not only SSP.
        for line in patch.read_text(errors='replace').splitlines():
            if line.startswith('diff --git a/') and ' b/' in line:
                paths.add(line.split(' b/', 1)[1])
    return paths


def inspect(src: Path, patches: Path, pinned: str, allow_patch_touched: bool) -> dict:
    require = lambda ok, msg: None if ok else (_ for _ in ()).throw(ValueError(msg))
    require((src / '.git').exists(), 'kernel git checkout missing (not included in source ZIP)')
    head = git(src, 'rev-parse', 'HEAD').strip()
    paths = patch_targets(patches)
    # Git machine output: --name-only -z avoids spaces, rename notation and
    # porcelain index ambiguity. Tracked changes are counted relative to HEAD.
    changed = {x for x in git(src, 'diff', '--name-only', 'HEAD', '--').splitlines() if x}
    staged = {x for x in git(src, 'diff', '--cached', '--name-only', '--').splitlines() if x}
    changed |= staged
    # Untracked files are also contamination, except generated files ignored
    # by Git. A clean build uses O= output outside this kernel source tree.
    unknown = {x for x in git(src, 'ls-files', '--others', '--exclude-standard').splitlines() if x}
    unexpected = sorted((changed - paths) if allow_patch_touched else changed)
    status = 'PASS' if head == pinned and not unexpected and not unknown else 'FAIL'
    return {'schema': 'ssp-kernel-source-audit-v1', 'status': status,
            'pinned_expected': pinned, 'actual_head': head,
            'source': str(src), 'allow_patch_touched': allow_patch_touched,
            'tracked_modified_count': len(changed),
            'untracked_files': sorted(unknown),
            'unexpected_modified_files': unexpected,
            'patch_target_count': len(paths),
            'warning': 'A PASS does not prove any patch applied or that a kernel builds'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--patch-dir', type=Path, required=True)
    p.add_argument('--expected-commit', default=PINNED)
    p.add_argument('--allow-patch-touched', action='store_true')
    p.add_argument('--json-out', type=Path)
    a=p.parse_args(argv)
    try:
        d=inspect(a.source, a.patch_dir, a.expected_commit, a.allow_patch_touched)
    except (ValueError, OSError) as exc:
        d={'schema':'ssp-kernel-source-audit-v1', 'status':'FAIL', 'error':str(exc)}
    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps(d, indent=2, sort_keys=True)+'\n')
    print(json.dumps(d, indent=2, sort_keys=True))
    return 0 if d['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
