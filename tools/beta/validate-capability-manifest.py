#!/usr/bin/env python3
"""validate-capability-manifest.py — schema + work-queue cross-check (briq-09c).

Two independent jobs, both fail-closed:

1. **Schema validation.** Validates `DEVICE-CAPABILITY-MANIFEST.json` against
   `DEVICE-CAPABILITY-MANIFEST.schema.json` with a small, explicit interpreter for
   the JSON-Schema subset the schema actually uses (`type`, `required`,
   `properties`, `additionalProperties`, `items`, `enum`, `pattern`, `minimum`,
   `minItems`, `minLength`, `$schema`-less local `$ref` is not used).  The subset
   is listed in the output so a reader knows exactly how much of the schema was
   enforced.

2. **Cross-check against the work queue.**  Every subsystem entry names a
   `briq-*` record.  The validator refuses to accept a claim that is stronger
   than its record, which is how this repository keeps the promise "no claim
   without a record":

   * the named record must exist on disk;
   * `record_state` must be one of the states that record has *ever* had (so a
     concurrent update by another build group cannot invalidate the manifest,
     while a state that was never recorded is rejected);
   * `record_verdict` must likewise be absent-or-historical;
   * the entry's `verdict` must be **no stronger** than the cap, where
     cap = min(strength(record's latest verdict), strength(record's declared
     offline ceiling)); a record with no verdict at all caps the entry at
     `NEEDS_OWNER_TEST`/`IMPLEMENTED_NOT_DEPLOYED` strength.  Ordering is in
     STRENGTH below.

Exit 0 = schema valid and every entry within its cap.  1 = violations.
2 = usage / unreadable input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

STRENGTH = {
    "NOT_SUPPORTED_ON_DEVICE": 0,
    "DEFERRED": 0,
    "FAILED": 0,
    "BLOCKED_KERNEL": 0,
    "BLOCKED_FIRMWARE": 0,
    "BLOCKED_HARDWARE": 0,
    "BLOCKED_EXTERNAL_RESOURCE": 0,
    "NEEDS_OWNER_TEST": 1,
    "IMPLEMENTED_NOT_DEPLOYED": 1,
    "OFFLINE_TESTED": 2,
    "DEPLOYED_UNVERIFIED": 3,
    "VERIFIED_IN_VM_ONLY": 4,
    "VERIFIED_ON_S10PLUS": 5,
}
NO_RECORD_VERDICT_CAP = 1        # a record with no verdict may not claim beyond this

VERDICT_VOCAB = [
    "VERIFIED_ON_S10PLUS", "VERIFIED_IN_VM_ONLY", "OFFLINE_TESTED", "DEPLOYED_UNVERIFIED",
    "IMPLEMENTED_NOT_DEPLOYED", "BLOCKED_KERNEL", "BLOCKED_FIRMWARE", "BLOCKED_HARDWARE",
    "BLOCKED_EXTERNAL_RESOURCE", "NEEDS_OWNER_TEST", "FAILED", "DEFERRED",
    "NOT_SUPPORTED_ON_DEVICE",
]

TYPES = {"object": dict, "array": list, "string": str, "integer": int,
         "number": (int, float), "boolean": bool, "null": type(None)}


# --------------------------------------------------------------------------- #
# minimal JSON-Schema (subset) interpreter
# --------------------------------------------------------------------------- #
def type_ok(value, want):
    wants = want if isinstance(want, list) else [want]
    for w in wants:
        py = TYPES.get(w)
        if py is None:
            continue
        if w == "integer" and isinstance(value, bool):
            continue
        if w in ("number", "integer") and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def validate(node, schema, path, errs, keywords):
    for kw in schema:
        keywords.add(kw)
    if "type" in schema and not type_ok(node, schema["type"]):
        errs.append("%s: expected type %s, got %s" % (path, schema["type"], type(node).__name__))
        return
    if "enum" in schema and node not in schema["enum"]:
        errs.append("%s: %r is not one of %s" % (path, node, schema["enum"]))
    if isinstance(node, str):
        if "minLength" in schema and len(node) < schema["minLength"]:
            errs.append("%s: shorter than minLength %d" % (path, schema["minLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], node):
            errs.append("%s: %r does not match %s" % (path, node, schema["pattern"]))
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errs.append("%s: %r below minimum %r" % (path, node, schema["minimum"]))
    if isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errs.append("%s: fewer than minItems %d" % (path, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(node):
                validate(item, schema["items"], "%s[%d]" % (path, i), errs, keywords)
    if isinstance(node, dict):
        for req in schema.get("required", []):
            if req not in node:
                errs.append("%s: missing required key %r" % (path, req))
        props = schema.get("properties", {})
        for key, val in node.items():
            if key in props:
                validate(val, props[key], "%s.%s" % (path, key), errs, keywords)
            elif schema.get("additionalProperties") is False:
                errs.append("%s: unexpected key %r" % (path, key))


# --------------------------------------------------------------------------- #
# work queue
# --------------------------------------------------------------------------- #
def load_records(wq_dir):
    recs = {}
    for name in sorted(os.listdir(wq_dir)):
        if not (name.startswith("briq-") and name.endswith(".json")):
            continue
        try:
            doc = json.load(open(os.path.join(wq_dir, name), encoding="utf-8"))
        except Exception as exc:                                  # pragma: no cover
            raise SystemExit("cannot read %s: %s" % (name, exc))
        recs[doc.get("id") or name[:-5]] = doc
    return recs


def record_summary(doc):
    revs = doc.get("revisions", [])
    states = [r.get("state") for r in revs if r.get("state")]
    verdicts = [r.get("verdict") for r in revs if r.get("verdict")]
    ceilings = [r.get("offline_ceiling") for r in revs if r.get("offline_ceiling")]
    latest = revs[-1] if revs else {}
    return {
        "states": states, "verdicts": verdicts, "ceilings": ceilings,
        "latest_state": latest.get("state"),
        "latest_verdict": latest.get("verdict"),
        "latest_ceiling": latest.get("offline_ceiling"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--workqueue", required=True)
    ap.add_argument("--json", help="write the report here too")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    for p in (a.manifest, a.schema):
        if not os.path.isfile(p):
            print("validate-capability-manifest: missing %s" % p, file=sys.stderr)
            return 2
    if not os.path.isdir(a.workqueue):
        print("validate-capability-manifest: missing work queue dir %s" % a.workqueue, file=sys.stderr)
        return 2

    manifest = json.load(open(a.manifest, encoding="utf-8"))
    schema = json.load(open(a.schema, encoding="utf-8"))
    records = load_records(a.workqueue)

    keywords = set()
    schema_errs = []
    validate(manifest, schema, "$", schema_errs, keywords)

    cross_errs, claims = [], []
    seen = set()
    for s in manifest.get("subsystems", []):
        sid = s.get("id")
        rec_id = s.get("record")
        v = s.get("verdict")
        if sid in seen:
            cross_errs.append("subsystem %r is declared twice" % sid)
        seen.add(sid)
        if v not in VERDICT_VOCAB:
            cross_errs.append("%s: verdict %r is outside the terminal vocabulary" % (sid, v))
            continue
        doc = records.get(rec_id)
        if doc is None:
            cross_errs.append("%s: names record %r, which does not exist in the work queue" % (sid, rec_id))
            continue
        r = record_summary(doc)
        st = s.get("record_state")
        if st and st not in r["states"]:
            cross_errs.append("%s: record_state %r was never recorded for %s (states: %s)"
                              % (sid, st, rec_id, r["states"]))
        rv = s.get("record_verdict")
        if rv and rv not in r["verdicts"]:
            cross_errs.append("%s: record_verdict %r was never recorded for %s (verdicts: %s)"
                              % (sid, rv, rec_id, r["verdicts"]))
        if r["latest_verdict"]:
            cap = STRENGTH.get(r["latest_verdict"], 0)
        else:
            cap = NO_RECORD_VERDICT_CAP
        if r["latest_ceiling"]:
            cap = min(cap, STRENGTH.get(r["latest_ceiling"], 0))
        strength = STRENGTH[v]
        claims.append({"id": sid, "verdict": v, "strength": strength, "cap": cap,
                       "record": rec_id, "record_latest_state": r["latest_state"],
                       "record_latest_verdict": r["latest_verdict"],
                       "record_ceiling": r["latest_ceiling"],
                       "within_cap": strength <= cap})
        if strength > cap:
            cross_errs.append(
                "%s: claims %s (strength %d) but its record %s caps it at strength %d "
                "(latest state %s, latest verdict %s, ceiling %s)"
                % (sid, v, strength, rec_id, cap, r["latest_state"], r["latest_verdict"],
                   r["latest_ceiling"]))

    ok = not schema_errs and not cross_errs
    report = {
        "tool": "tools/beta/validate-capability-manifest.py",
        "manifest": a.manifest,
        "schema": a.schema,
        "schema_keywords_enforced": sorted(keywords),
        "schema_errors": schema_errs,
        "cross_check_errors": cross_errs,
        "records_seen": len(records),
        "subsystems": len(manifest.get("subsystems", [])),
        "claims": claims,
        "verdict": "VALID" if ok else "INVALID",
        "cap_rule": ("verdict strength <= min(strength(record latest verdict), "
                     "strength(record latest offline ceiling)); a record with no verdict caps at "
                     "strength %d (NEEDS_OWNER_TEST / IMPLEMENTED_NOT_DEPLOYED)" % NO_RECORD_VERDICT_CAP),
        "strength_order": STRENGTH,
    }
    if not a.quiet:
        print("== capability manifest validation ==")
        print("manifest : %s" % a.manifest)
        print("schema   : %s" % a.schema)
        print("schema keywords enforced: %s" % ", ".join(sorted(keywords)))
        print("subsystems: %d   work-queue records read: %d"
              % (report["subsystems"], report["records_seen"]))
        print("-- schema errors --")
        print("  none" if not schema_errs else "\n".join("  " + e for e in schema_errs))
        print("-- work-queue cross-check (verdict vs record cap) --")
        for c in claims:
            mark = "ok  " if c["within_cap"] else "FAIL"
            print("  %s %-26s %-24s cap=%-2d  record=%-30s (%s)"
                  % (mark, c["id"], c["verdict"], c["cap"], c["record"],
                     c["record_latest_state"]))
        if cross_errs:
            print("-- cross-check errors --")
            for e in cross_errs:
                print("  " + e)
        print("verdict: %s (%d schema error(s), %d cross-check error(s))"
              % (report["verdict"], len(schema_errs), len(cross_errs)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        if not a.quiet:
            print("report: %s" % a.json)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
