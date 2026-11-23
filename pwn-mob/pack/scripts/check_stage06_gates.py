#!/usr/bin/env python3
"""Conservative offline Stage 06 gate checker. Does not infer evidence from logs.

An operator/agent must manually mark a gate passed AND supply evidence path.
This tool never modifies the JSON or device and never declares Stage 06 passed
without all explicit receipts. Exits 0 only if every gate is present.
"""
import argparse
import json
from pathlib import Path


def check(path: Path):
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('schema_version') != 1 or not isinstance(doc.get('gates'), list):
        raise ValueError('bad gate schema')
    gates = doc['gates']
    ids = [g.get('id') for g in gates]
    if len(gates) != 10 or len(set(ids)) != 10:
        raise ValueError('expected exactly 10 unique stage-06 gates')
    pending = []
    for g in gates:
        if g.get('passed') is not True or not isinstance(g.get('evidence'), str) or not g['evidence'].strip():
            pending.append(g.get('name', 'unknown gate'))
    return len(gates), pending


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('json_file', type=Path)
    a = p.parse_args()
    total, pending = check(a.json_file)
    print(f'Stage 06 evidence gates: {total - len(pending)}/{total} explicitly marked with receipts')
    if pending:
        print('NOT COMPLETE — pending:')
        for g in pending:
            print(f' - {g}')
        raise SystemExit(2)
    print('All gates are ASSERTED with evidence paths; human review of receipts remains required.')


if __name__ == '__main__':
    main()
