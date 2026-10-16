#!/usr/bin/env bash
# push-file.sh — push one file to the running Nuxel phone over the USB live
# console using only nuxel-live.sh --run (the verified transport) plus shell
# builtins on the target.
#
# MEASURED CONSTRAINT (A29): this link has no flow control and silently drops
# command lines longer than ~512 characters (256/512 land exactly; 768/1024/1536/
# 2048 arrive empty).  So the payload travels as 380-character base64 chunks and
# EVERY chunk is acknowledged by reading the cumulative file size back from the
# target - the command echo is never used as proof.
#
#   push-file.sh <local> <remote-path> [--mode 755] [--chunk 380]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE="$HERE/../../../scripts/s10plus-debug-pack/nuxel-live.sh"
LOCAL="$1"; REMOTE="$2"; shift 2
MODE=644; CHUNK=380; DEV=""; RETRIES=4
while [ $# -gt 0 ]; do
  case "$1" in --mode) MODE="$2"; shift 2 ;; --chunk) CHUNK="$2"; shift 2 ;;
    --dev) DEV="$2"; shift 2 ;; *) echo "unknown $1" >&2; exit 2 ;; esac
done
[ -f "$LOCAL" ] || { echo "missing $LOCAL" >&2; exit 3; }
DEVARG=""; [ -n "$DEV" ] && DEVARG="--dev $DEV"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
gzip -9 -c "$LOCAL" > "$TMP/gz"
LOCAL_SHA=$(sha256sum "$LOCAL" | cut -d' ' -f1)
base64 < "$TMP/gz" | tr -d '\n' > "$TMP/b64"; printf '\n' >> "$TMP/b64"
B64BYTES=$(wc -c < "$TMP/b64" | tr -d ' ')
fold -w "$CHUNK" "$TMP/b64" > "$TMP/chunks"
TOTAL=$(wc -l < "$TMP/chunks" | tr -d ' ')
F=/tmp/nx.b64
echo "# push $LOCAL -> $REMOTE raw=$(wc -c < "$LOCAL" | tr -d ' ') gzip=$(wc -c < "$TMP/gz" | tr -d ' ') b64=$B64BYTES chunks=$TOTAL mode=$MODE"
run() { "$LIVE" $DEVARG --timeout 25 --run "$1" 2>&1; }

# truncate-and-restart helper on the target
run ": > $F" >/dev/null
expect=0; i=0
while IFS= read -r chunk || [ -n "$chunk" ]; do
  i=$((i + 1)); want=$((expect + ${#chunk}))
  ok=0
  for try in 1 2 3; do
    out=$(run "printf '%s' '$chunk' >> $F; wc -c < $F")
    got=$(printf '%s\n' "$out" | grep -oE '^ *[0-9]+ *$' | tail -1 | tr -d ' ')
    if [ -n "$got" ] && [ "$got" = "$want" ]; then ok=1; break; fi
    # repair: cut the partial chunk back to the last known-good length, retry
    run "head -c $expect $F > $F.t 2>/dev/null || : > $F.t; mv $F.t $F" >/dev/null
    echo "#   chunk $i retry $try (want=$want got=${got:-none})" >&2
  done
  [ "$ok" = 1 ] || { echo "# chunk $i FAILED after retries — aborting" >&2; exit 4; }
  expect=$want
  [ $((i % 10)) = 0 ] && printf '\r# %d/%d chunks' "$i" "$TOTAL" >&2
done < "$TMP/chunks"
printf '\r# %d/%d chunks\n' "$TOTAL" "$TOTAL" >&2
RES=$(run "set -e; base64 -d < $F | gunzip > $F.new; T=\$(sha256sum $F.new | cut -d' ' -f1); echo WANT=$LOCAL_SHA; echo GOT=\$T; install -m $MODE $F.new '$REMOTE'; V=\$(sha256sum '$REMOTE' | cut -d' ' -f1); echo INST=\$V; rm -f $F $F.new")
echo "$RES" | grep -E "WANT=|GOT=|INST=" | tail -3
if echo "$RES" | grep -q "GOT=$LOCAL_SHA" && echo "$RES" | grep -q "INST=$LOCAL_SHA"; then
  echo "# OK $REMOTE sha256=$LOCAL_SHA"; exit 0
fi
echo "# FAIL expected sha256=$LOCAL_SHA" >&2; exit 5
