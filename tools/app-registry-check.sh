#!/usr/bin/env bash
# Nuxel App Registry — validation & single-source enforcement (briq-se1)
#
# Verifies configs/nuxel/app-registry/app_registry.json:
#   1. is well-formed JSON and validates against the accompanying JSON Schema
#   2. app_id values are unique
#   3. every entry's cgroup_name equals the deterministic mapping of app_id
#      (lowercase, [a-z0-9-] else '-', collapsed, trimmed, prefixed 'app-'),
#      so it matches the nftables "socket cgroupv2 level 2 'app-*'" rule
#   4. (when present) the per-app sandbox profiles in nuxel-sandbox/profiles/
#      agree with the registry on cgroup_name + network_class (single source)
#
# Exit code 0 = all checks pass. Non-zero = a repair is required.
# The qontroller / CI may run this after every construqtor cycle.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REG="${1:-${NUXEL_APP_REGISTRY:-$ROOT/configs/nuxel/app-registry/app_registry.json}}"
SCHEMA="${2:-$ROOT/configs/nuxel/app-registry/app-registry.schema.json}"
PROFILES_DIR="${NUXEL_PROFILES_DIR:-$ROOT/shell/nuxel-shell/nuxel-sandbox/profiles}"

if ! command -v python3 >/dev/null 2>&1; then
    cat >&2 <<EOM
FATAL: python3 is required to run this check.
EOM
    exit 2
fi

ok()   { echo "ok:   $*"; }
fail() { echo "FAIL: $*" >&2; FAILED=1; }
FAILED=0

# ---- 1. JSON parse + schema validation ----
if [ ! -f "$REG" ]; then
    echo "FAIL: registry not found: $REG" >&2
    exit 1
fi
if [ ! -f "$SCHEMA" ]; then
    echo "FAIL: schema not found: $SCHEMA" >&2
    exit 1
fi

if python3 -c "import jsonschema" 2>/dev/null; then
    if ! python3 - "$REG" "$SCHEMA" <<'PY'
import json, sys
import jsonschema
reg = json.load(open(sys.argv[1]))
sch = json.load(open(sys.argv[2]))
jsonschema.validate(reg, sch)
print("ok:   registry validates against schema")
PY
    then
        fail "registry fails JSON Schema validation: see message above"
    fi
else
    if ! python3 -c "import json,sys; reg=json.load(open(sys.argv[1])); json.load(open(sys.argv[2])); assert reg.get('schema_version',0)==1" "$REG" "$SCHEMA"; then
        fail "registry or schema is not valid JSON / wrong schema_version"
    else
        ok "jsonschema module not present; basic JSON parse + schema_version checked"
    fi
fi

# ---- 2. unique app_id + 3. deterministic cgroup mapping ----
if ! python3 - "$REG" <<'PY'
import json, re, sys
reg = json.load(open(sys.argv[1]))
ids = [a["app_id"] for a in reg["apps"]]
if len(ids) != len(set(ids)):
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    raise SystemExit(f"duplicate app_id values: {dupes}")
def to_cgroup(aid):
    o = re.sub(r'-+', '-', re.sub(r'[^a-z0-9-]', '-', aid.lower())).strip('-')
    return 'app-' + o
bad = [ (a["app_id"], a["cgroup_name"], to_cgroup(a["app_id"]))
        for a in reg["apps"]
        if a.get("cgroup_name") != to_cgroup(a["app_id"]) ]
if bad:
    for bid, have, want in bad:
        print(f"FAIL: {bid}: cgroup_name '{have}' != deterministic '{want}'", file=sys.stderr)
    raise SystemExit(1)
print(f"ok:   {len(ids)} apps, unique app_id, deterministic cgroup_name verified")
PY
then
    FAILED=1
fi

# ---- 4. profile agreement (single source) ----
if [ -d "$PROFILES_DIR" ]; then
    if ! python3 - "$REG" "$PROFILES_DIR" <<'PY'
import json, os, sys
reg = json.load(open(sys.argv[1]))
pf = sys.argv[2]
mapping = {a["app_id"]: a for a in reg["apps"]}
issues = []
for fn in sorted(os.listdir(pf)):
    if not fn.endswith(".json"):
        continue
    try:
        prof = json.load(open(os.path.join(pf, fn)))
    except Exception as e:
        issues.append(f"{fn}: unparseable profile ({e})")
        continue
    aid = prof.get("app_id")
    if aid is None:
        issues.append(f"{fn}: profile has no app_id")
        continue
    # Reusable templates carry APP_ID placeholders and are not individually
    # registered / launched; skip them (detected by the placeholder marker).
    if "APP_ID" in str(prof.get("cgroup_name", "")):
        continue
    entry = mapping.get(aid)
    if entry is None:
        if str(prof.get("app_id", "")).upper().endswith("TEMPLATE"):
            continue  # reusable templates need not be individually registered
        issues.append(f"{fn}: app_id '{aid}' not in registry — add it to app_registry.json")
        continue
    if "cgroup_name" in prof and prof["cgroup_name"] != entry["cgroup_name"]:
        issues.append(f"{fn}: cgroup_name '{prof['cgroup_name']}' != registry '{entry['cgroup_name']}'")
    if "network_class" in prof and prof["network_class"] != entry["network_class"]:
        issues.append(f"{fn}: network_class '{prof['network_class']}' != registry '{entry['network_class']}'")
if issues:
    for i in issues:
        print("FAIL:", i, file=sys.stderr)
    raise SystemExit(1)
print(f"ok:   profiles in {pf} agree with registry (single source)")
PY
    then
        FAILED=1
    fi
else
    ok "no profiles dir to cross-check ($PROFILES_DIR)"
fi

echo ""
if [ "$FAILED" = "1" ]; then
    echo "app-registry-check: FAILED — see errors above." >&2
    exit 1
fi
echo "app-registry-check: all checks passed."
exit 0
