#!/usr/bin/env python3
"""Offline active-versus-candidate merged FDT proof (conservative).

IMPORTANT: This does NOT emulate Samsung's proprietary merge. It verifies the
board/selected overlay and requires a separately captured signed Prompt 00
baseline. Unlike the old implementation it never calls 'contained' a proof of
merged-tree equality while ignoring changed property values.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import dt_graph as dg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--merged', required=True, help='candidate merged FDT')
    ap.add_argument('--baseline-merged', required=True, help='exact active merged FDT captured under Prompt 00')
    ap.add_argument('--dtb', required=True)
    ap.add_argument('--dtbo', required=True)
    ap.add_argument('--board-rev', required=True, type=int)
    ap.add_argument('--dtbo-idx', required=True, type=int)
    ap.add_argument('--allowlist')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    try:
        raw = Path(a.dtbo).read_bytes()
        entries = dg.dtbo_entries(raw)
        if not (0 <= a.dtbo_idx < len(entries)):
            raise ValueError('missing/wrong selected DTBO entry')
        selected = dg.parse_fdt(dg.extract_fdts(raw)[a.dtbo_idx])
        root = selected.get('/')
        lo, hi = root.props.get('dtbo-hw_rev'), root.props.get('dtbo-hw_rev_end')
        if not lo or not hi or not lo.cells or not hi.cells or not (lo.cells[0] <= a.board_rev <= hi.cells[0]):
            raise ValueError('selected overlay does not support board revision')
        base = dg.parse_fdt(dg.extract_fdts(Path(a.dtb).read_bytes())[0])
        if not base.get('/'):
            raise ValueError('invalid base FDT')
        spec = importlib.util.spec_from_file_location('camera_dt_diff', ROOT/'camera-dt-diff.py')
        mod = importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        result = mod.diff(a.baseline_merged, a.merged, mod.load_allow(a.allowlist))
        if result['result'] != 'PASS':
            raise ValueError('%d unapproved semantic deltas' % len(result['unapproved']))
        result.update({'selected_overlay_entry':a.dtbo_idx, 'board_revision':a.board_rev,
                       'NOTE':'Offline comparison only, not proof of proprietary base/overlay merge',
                       'result':'PASS_OFFLINE_ONLY'})
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, IndexError, KeyError, TypeError) as e:
        print(json.dumps({'result':'FAIL','reason':str(e)}, indent=2))
        return 1

if __name__ == '__main__':
    sys.exit(main())
