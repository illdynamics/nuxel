#!/usr/bin/env python3
"""Fail-closed startup check for the NFC per-app gate.

The daemon's hardened unit must be able to read the shared permD grant store;
otherwise every granted app is refused (measured on 2026-11-12 with
ProtectSystem=strict + a partial ReadWritePaths).  This preflight runs inside
the SAME sandbox as the daemon and refuses to start a controller that would
silently deny every app.

It never writes: it only lists the store and evaluates the policy module.
"""
import os
import sys

sys.path.insert(0, "/usr/lib/nuxel/nuxel-nfc")

STORE = os.environ.get("NUXEL_PERMISSIONS_DIR") or "/var/lib/nuxel/permissions"


def main() -> int:
    try:
        entries = os.listdir(STORE)
    except OSError as exc:
        print("nfcd-preflight: cannot read grant store %s: %s" % (STORE, exc),
              file=sys.stderr)
        return 1
    jsons = [n for n in entries if n.endswith(".json")]
    print("nfcd-preflight: store %s readable (%d record(s))" % (STORE, len(jsons)),
          file=sys.stderr)
    try:
        from nuxel_nfc import policy
    except Exception as exc:  # noqa: BLE001
        print("nfcd-preflight: policy module unavailable: %s" % exc, file=sys.stderr)
        return 1
    # An unidentifiable caller must always be refused; this also proves the
    # module loaded with the expected verbs instead of a stale copy.
    verdict = policy.authorize(None, "scan")
    if verdict.get("allowed"):
        print("nfcd-preflight: policy accepted an unidentified caller",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
