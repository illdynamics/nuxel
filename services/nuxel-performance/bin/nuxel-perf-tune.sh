#!/bin/sh
# Nuxel idle/performance tuning (userspace only).
#
# Reversible boot-time knobs chosen for the S10+ UFS/flash storage.  This never
# touches cpufreq governors, thermal protection, kernel watchdogs, SELinux, the
# display pipeline or any partition/block-device contents.
set -u
say() { printf 'nuxel-perf-tune: %s\n' "$*"; }

# 1. CFQ is CPU-heavy on flash; use the kernel's no-op scheduler for
#    non-rotational devices.  The set of devices is discovered, never assumed.
for q in /sys/block/*/queue/scheduler; do
    [ -w "$q" ] || continue
    dev=${q%/queue/scheduler}; dev=${dev##*/}
    [ -r "/sys/block/$dev/queue/rotational" ] || continue
    [ "$(cat "/sys/block/$dev/queue/rotational" 2>/dev/null)" = "0" ] || continue
    case " $(cat "$q" 2>/dev/null) " in
        *" [noop] "*) : ;;
        *" noop "*) echo noop > "$q" 2>/dev/null && say "scheduler[$dev]=noop" ;;
    esac
done

# 2. Batch dirty writeback: with 7 GiB RAM and flash storage, waking the
#    flusher every 5 s is unnecessary.  15 s keeps latency bounded while
#    cutting periodic writeback wakeups by 3x.
sysctl -q -w vm.dirty_writeback_centisecs=1500 2>/dev/null \
    && say "vm.dirty_writeback_centisecs=1500"
sysctl -q -w vm.dirty_expire_centisecs=4500 2>/dev/null \
    && say "vm.dirty_expire_centisecs=4500"
# No swap is configured; a low swappiness is still correct if zram is added.
sysctl -q -w vm.swappiness=10 2>/dev/null && say "vm.swappiness=10"

# 3. The kernel softdog/audit paths are deliberately NOT touched here.
exit 0
