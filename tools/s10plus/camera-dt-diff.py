#!/usr/bin/env python3
"""Fail-closed, semantic binary-FDT delta checker for camera release candidates.

Properties are compared by decoded *bytes*, not DTS formatting or ordering;
node and property order, padding, and header serialization do not matter.
Phandle renumbering remains a hard change (conservative and intentionally so).
A proposed dependency change requires an explicitly named exact-property
allowlist item with rationale; no wildcard paths or prefix exceptions.
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import dt_graph


def sha(b):
    return hashlib.sha256(b).hexdigest()


def tree(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if not dt_graph.is_fdt(raw):
        raise ValueError('%s must be a bare, merged FDT' % path)
    return dt_graph.parse_fdt(dt_graph.extract_fdts(raw)[0])


def props(t):
    return {(path, name): prop.data for path, node in t.nodes.items()
            for name, prop in node.props.items()}


def camera_node(t, path):
    node = t.get(path)
    if not node:
        return False
    p = node.props.get('compatible')
    return bool(re.search(r'fimc|csis|camera|s5k|2l4|3j1|3m3|3p9|4ha|sensor-module',
                          path, re.I) or (p and any(re.search(
                          r'fimc|csis|camera|s5k|2l4|3j1|3m3|3p9|4ha', c, re.I)
                          for c in p.strings)))


def load_allow(path):
    if not path:
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get('schema') != 'nuxel.camera.dt-allowlist/v1':
        raise ValueError('invalid allowlist schema')
    allowed = {}
    for item in data.get('changes', []):
        if not isinstance(item, dict):
            raise ValueError('invalid allowlist entry')
        p, n, kind, reason = (item.get(k) for k in ('path', 'property', 'kind', 'reason'))
        if not isinstance(p, str) or not p.startswith('/') or p.endswith('/*') or \
                not isinstance(n, str) or '*' in n or not n or \
                kind not in ('camera', 'dependency') or \
                not isinstance(reason, str) or len(reason.strip()) < 15:
            raise ValueError('allowlist needs exact node/property, kind and substantive reason')
        key = (p, n)
        if key in allowed:
            raise ValueError('duplicate allowlist item %r' % (key,))
        allowed[key] = item
    return allowed


def approved_dependency(path):
    """Shared-resource-only allowlist; never allow NFC/SSP/display deltas."""
    if re.search(r'nfc|ssp|sensorhub|display|dpu|touch|fingerprint|wifi|wlan|bluetooth|'
                 r'usb|gpu|charging|charger|battery|modem|audio|mic|speaker|storage|ufs',
                 path, re.I):
        return False
    return bool(re.search(r'regulator|clock|clk|pinctrl|gpio|reset|phy|power-domain', path, re.I))


def diff(baseline, candidate, allow=None):
    allow = allow or {}
    tb, tc = tree(baseline), tree(candidate)
    x, y = props(tb), props(tc)
    path_delta = sorted(set(tb.nodes) ^ set(tc.nodes))
    changes, rejected = [], []
    for path in path_delta:
        # Every node addition/deletion needs explicit @node permission.
        item = allow.get((path, '@node'))
        cam = camera_node(tb, path) or camera_node(tc, path)
        reason = 'node added/removed'
        ok = item is not None and (
            (item['kind'] == 'camera' and cam) or
            (item['kind'] == 'dependency' and approved_dependency(path)))
        change = {'path': path, 'property': '@node', 'baseline': path in tb.nodes,
                  'candidate': path in tc.nodes, 'allowlisted': ok, 'reason': reason}
        changes.append(change)
        if not ok:
            rejected.append(change)
    for key in sorted(set(x) | set(y)):
        if x.get(key) == y.get(key) and (key in x) == (key in y):
            continue
        path, name = key
        item = allow.get(key)
        cam = camera_node(tb, path) or camera_node(tc, path)
        ok = item is not None and (
            (item['kind'] == 'camera' and cam) or
            (item['kind'] == 'dependency' and approved_dependency(path)))
        change = {'path': path, 'property': name,
                  'baseline_sha256': sha(x[key]) if key in x else None,
                  'candidate_sha256': sha(y[key]) if key in y else None,
                  'allowlisted': ok}
        changes.append(change)
        if not ok:
            rejected.append(change)
    return {'baseline': {'path': baseline, 'nodes': len(tb.nodes)},
            'candidate': {'path': candidate, 'nodes': len(tc.nodes)},
            'semantic_equivalent': not changes, 'changes': changes,
            'unapproved': rejected, 'result': 'PASS' if not rejected else 'FAIL'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--allowlist')
    ap.add_argument('--json-out')
    args = ap.parse_args()
    try:
        report = diff(args.baseline, args.candidate, load_allow(args.allowlist))
        if args.json_out:
            with open(args.json_out, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, sort_keys=True)
                f.write('\n')
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report['result'] == 'PASS' else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'result': 'FAIL', 'error': str(exc)}))
        return 1

if __name__ == '__main__':
    sys.exit(main())
