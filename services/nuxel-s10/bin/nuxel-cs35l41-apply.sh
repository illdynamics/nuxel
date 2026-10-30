#!/bin/sh
# CS35L41 clock/boost/output patch (owner-confirmed speaker fix).
# Apply immediately before every PipeWire playback so a post-hw_free muted
# output stage can never leave the next volume preview or test silent.
set -u
CS35=${NUXEL_CS35_HELPER:-/usr/local/bin/nuxel-cs35.py}
[ -x "$CS35" ] || { echo "nuxel-cs35.py helper missing" >&2; exit 1; }
fail=0
for a in 0x40 0x41; do
  for spec in "0x4804 0x1b" "0x2c04 0x370" "0x6000 0x8000" "0x2024 0x0"; do
    set -- $spec
    reg=$1; val=$2
    if ! timeout -k 1 4 "$CS35" "$a" "$reg" "$val" >/dev/null 2>&1; then
      echo "CS35L41 patch write failed: $a $reg $val" >&2
      fail=1
    fi
  done
done
exit $fail
