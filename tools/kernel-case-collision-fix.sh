#!/usr/bin/env bash
# =============================================================================
# kernel-case-collision-fix.sh — build on a case-insensitive filesystem
#
# Usage: tools/kernel-case-collision-fix.sh <kernel-source-tree>
#
# The pinned exynos9820 tree ships file pairs that differ only in case, e.g.
#
#   net/netfilter/xt_MARK.c            net/netfilter/xt_mark.c
#   include/uapi/linux/netfilter/xt_MARK.h   .../xt_mark.h
#
# macOS (APFS/HFS+ default) and most container bind mounts from it cannot hold
# both names, so one file silently wins and sources that include the other
# one compile against the wrong header ("invalid use of undefined type
# 'struct xt_mark_tginfo2'").  The pinned source is Linux-only ASCII; on such a
# host the colliding include is rewritten to the explicit `uapi/` path, which
# names exactly one file.  Linux hosts (case-sensitive) are left untouched.
# =============================================================================
set -euo pipefail
SRC="${1:?usage: kernel-case-collision-fix.sh <kernel-source-tree>}"
[ -d "$SRC" ] || { echo "no source tree: $SRC" >&2; exit 1; }

fixed=0
for pair in \
    "net/netfilter/xt_mark.c:linux/netfilter/xt_mark.h:uapi/linux/netfilter/xt_mark.h" \
    "net/netfilter/xt_mark.c:linux/netfilter/xt_MARK.h:uapi/linux/netfilter/xt_mark.h" \
    "net/netfilter/xt_MARK.c:linux/netfilter/xt_MARK.h:uapi/linux/netfilter/xt_MARK.h"
do
    f="${pair%%:*}"; rest="${pair#*:}"; from="${rest%%:*}"; to="${rest#*:}"
    [ -f "$SRC/$f" ] || continue
    if grep -q "#include <$from>" "$SRC/$f"; then
        sed -i.bak "s|#include <$from>|#include <$to>|" "$SRC/$f"
        rm -f "$SRC/$f.bak"
        echo "[case-collision] $f: include <$to>"
        fixed=$((fixed + 1))
    fi
done
# The xt_TCPMSS target (xt_TCPMSS.c) and the xt_tcpmss matcher (xt_tcpmss.c)
# are a case-only pair as well.  This config enables the target and disables
# the matcher (CONFIG_NETFILTER_XT_MATCH_TCPMSS is not set), so the correct
# source for the enabled symbol must be materialised.  Restore it from git.
if [ -n "${NUXEL_CASE_TCPMSS:-1}" ] && [ -d "$SRC/.git" ]; then
    if [ ! -f "$SRC/net/netfilter/xt_TCPMSS.c" ] && \
       [ "$(git -C "$SRC" ls-files net/netfilter/xt_TCPMSS.c)" != "" ]; then
        # the on-disk colliding file is the matcher; move it aside and restore
        # the target source the config actually enables.
        [ -f "$SRC/net/netfilter/xt_tcpmss.c" ] && mv "$SRC/net/netfilter/xt_tcpmss.c" "/tmp/xt_tcpmss.c.$$.bak"
        git -C "$SRC" checkout -- net/netfilter/xt_TCPMSS.c
        echo "[case-collision] restored target net/netfilter/xt_TCPMSS.c"
        fixed=$((fixed + 1))
    fi
fi

echo "[case-collision] fixed=${fixed}"
