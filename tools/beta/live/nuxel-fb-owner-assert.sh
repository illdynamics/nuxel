#!/bin/sh
# nuxel-fb-owner-assert.sh — assert EXACTLY ONE writer of the framebuffer, and
# that the writer is the component that is allowed to own it.
#
# WHY THIS EXISTS (briq-01-deploy-manifest-extension, mission rule [FRAMEBUFFER])
#   The S10+ panel is a DECON framebuffer with no DRM.  A31/A32 measured that a
#   second opener of /dev/fb0 runs decon_release and disables the panel
#   regulator, so a deploy that touches the graphics path must prove, BEFORE and
#   AFTER, that there is exactly one holder of the node and that it is the
#   expected one (nuxel-wl-fb on the shipping image).  It is also the correct
#   answer to give when somebody wants to "just check" the panel with a second
#   client: that check is itself the defect.
#
# WHAT IT READS (read-only; no device is opened, no daemon is signalled)
#   $PROC/<pid>/fd/*  symlinks resolving to the framebuffer device
#   $PROC/<pid>/comm  the process name, identity-verified like the bridge does
#
# USAGE
#   nuxel-fb-owner-assert.sh [--proc-root DIR] [--fb /dev/fb0] [--expect NAME]
#                            [--allow-zero] [--quiet]
#
#   --proc-root DIR  read DIR instead of /proc (offline tests: a fixture tree)
#   --fb PATH        the framebuffer node to look for (default /dev/fb0)
#   --expect NAME    the ONLY acceptable writer name (default nuxel-wl-fb);
#                    pass "" to skip the name check
#   --allow-zero     accept "no writer" (used while the compositor is down on
#                    purpose); the default treats it as a failure
#
# OUTPUT (one machine-readable line, always)
#   FB_OWNER_ASSERT=PASS owner=<name> pid=<pid> count=1 fb=/dev/fb0
#   FB_OWNER_ASSERT=FAIL reason=<zero|multiple|wrong-owner> count=<n> owners=<list>
#
# EXIT CODES
#   0 exactly one writer and it is the expected one
#   1 no writer (and --allow-zero was not given)
#   2 more than one writer  (the failure this exists to catch)
#   3 exactly one writer, but it is the wrong component
#   4 usage / unreadable proc tree
#
# This script never writes to a device, never flashes anything, never opens
# /dev/fb0 and never touches a partition.
set -u

PROC="/proc"
FB="/dev/fb0"
EXPECT="nuxel-wl-fb"
ALLOW_ZERO=0
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --proc-root) PROC="${2:-}"; shift 2 ;;
    --fb)        FB="${2:-}";   shift 2 ;;
    --expect)    EXPECT="${2:-}"; shift 2 ;;
    --allow-zero) ALLOW_ZERO=1; shift ;;
    --quiet)     QUIET=1; shift ;;
    -h|--help)   sed -n '1,40p' "$0"; exit 0 ;;
    *) echo "nuxel-fb-owner-assert: unknown argument: $1" >&2; exit 4 ;;
  esac
done

[ -d "$PROC" ] || { echo "nuxel-fb-owner-assert: no proc tree at $PROC" >&2; exit 4; }

count=0
owner_pid=""
owner_name=""
owners=""
for d in "$PROC"/[0-9]*; do
  [ -d "$d" ] || continue
  pid="${d##*/}"
  hit=0
  for fd in "$d"/fd/*; do
    [ -L "$fd" ] || continue
    target="$(readlink "$fd" 2>/dev/null || true)"
    case "$target" in
      "$FB") hit=1 ;;
    esac
  done
  [ "$hit" = 1 ] || continue
  name="$(cat "$d/comm" 2>/dev/null | tr -d '\n' || true)"
  [ -n "$name" ] || name="?"
  count=$((count + 1))
  owners="$owners$name($pid) "
  if [ -z "$owner_name" ]; then owner_name="$name"; owner_pid="$pid"; fi
done

if [ "$count" -eq 0 ]; then
  if [ "$ALLOW_ZERO" = 1 ]; then
    echo "FB_OWNER_ASSERT=PASS owner=none count=0 fb=$FB allow_zero=1"
    exit 0
  fi
  echo "FB_OWNER_ASSERT=FAIL reason=zero count=0 fb=$FB"
  exit 1
fi
if [ "$count" -gt 1 ]; then
  echo "FB_OWNER_ASSERT=FAIL reason=multiple count=$count owners=$owners"
  exit 2
fi
if [ -n "$EXPECT" ] && [ "$owner_name" != "$EXPECT" ]; then
  echo "FB_OWNER_ASSERT=FAIL reason=wrong-owner count=1 owners=$owners expect=$EXPECT"
  exit 3
fi
echo "FB_OWNER_ASSERT=PASS owner=$owner_name pid=$owner_pid count=1 fb=$FB"
exit 0
