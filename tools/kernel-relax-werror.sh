#!/usr/bin/env bash
# =============================================================================
# kernel-relax-werror.sh — neutralise a kernel tree's hard-coded -Werror.
#
# Usage: tools/kernel-relax-werror.sh <kernel-source-tree>
#
# Why this exists
# ---------------
# Nuxel cross-builds two downstream/vendor kernels with a modern GCC
# (aarch64-linux-gnu- GCC 13 on the CI runner) against source trees that
# predate it and hard-code `-Werror` in two places that a `KCFLAGS=...`
# relaxation CANNOT reach:
#
#   1. Per-category promotions in the top Makefile, e.g. the Exynos 9820
#      (S10+) tree at Makefile:935-947:
#          KBUILD_CFLAGS += $(call cc-option,-Werror=strict-prototypes)
#      GCC gives the *more specific* option priority over the generic
#      `-Wno-error`, independently of command-line order, so a trailing
#      `-Wno-error` (as passed via KCFLAGS) does NOT downgrade these.
#
#   2. Per-directory flags appended after KBUILD_CFLAGS on the cc command
#      line, e.g. the bcmdhd Wi-Fi driver (S10+):
#          DHDCFLAGS += -Wall -Werror -Wstrict-prototypes ...
#          EXTRA_CFLAGS += $(DHDCFLAGS)          # -> ccflags-y, appended last
#      Whatever is added there wins over anything KCFLAGS put into
#      KBUILD_CFLAGS, so the build dies on ordinary warnings
#      (`cc1: all warnings being treated as errors`).
#
# We therefore strip the `-Werror`/`-Werror=<diag>`/`-Werror-<diag>` tokens
# (and whole `$(call cc-option,-Werror=...)` expressions) from the tree's
# source Makefiles in place. The tree is always a throwaway clone under
# kernel/<dir>/.build/, so this is safe and regenerated on every build.
# `-Wno-error...` flags are left untouched, and the kbuild-internal
# `scripts/Makefile.*` / `scripts/Kconfig.include` helpers (which intentionally
# use `$(CC) -Werror ...` for feature probes) are deliberately NOT matched.
#
# Idempotent: re-running over an already-relaxed tree is a no-op.
# =============================================================================
set -euo pipefail

tree="${1:-}"
if [ -z "${tree}" ]; then
    echo "usage: $(basename "$0") <kernel-source-tree>" >&2
    exit 2
fi
if [ ! -d "${tree}" ]; then
    echo "error: no such kernel tree: ${tree}" >&2
    exit 2
fi

python3 - "${tree}" <<'PY'
import os
import re
import sys

root = sys.argv[1]

# A whole `$(call cc-option,-Werror=<diag>[,<fallback>])` expression.
ccall = re.compile(r'\$\(call\s+cc-?option,\s*-Werror[^)]*\)')
# A bare -Werror token, -Werror=<diag> or -Werror-<diag>.
# The lookbehind keeps us away from -Wno-error (no 'W' before 'error' there).
token = re.compile(r'(?<![\w-])-Werror(?:=[-\w]+|-[-\w]+)?')

# Only real source Makefiles — never the kbuild-internal scripts/Makefile.*
# helpers, whose `$(CC) -Werror ...` feature probes must keep working.
def is_makefile(name):
    return name in ('Makefile', 'Kbuild') or name.endswith('.mk')

changed = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d != '.git']
    for name in filenames:
        if not is_makefile(name):
            continue
        path = os.path.join(dirpath, name)
        try:
            with open(path, 'r', encoding='utf-8', errors='surrogateescape') as fh:
                src = fh.read()
        except OSError:
            continue
        new = ccall.sub('', src)
        new = token.sub('', new)
        if new != src:
            with open(path, 'w', encoding='utf-8', errors='surrogateescape') as fh:
                fh.write(new)
            changed.append(os.path.relpath(path, root))

print("[relax-werror] stripped hard-coded -Werror from %d Makefile(s)" % len(changed))
for rel in sorted(changed):
    print("               " + rel)
PY
