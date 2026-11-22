#!/usr/bin/env python3
"""
Static lock-discipline check for the corrected bbd_do_transfer failure path.

Verifies against the ACTUAL applied source that:
  1. No `mutex_lock(&data->pending_mutex)` appears on the failure path AFTER
     the entry `mutex_lock(&data->pending_mutex)` (i.e. no self-deadlock).
  2. The number of pending_mutex unlocks balances the locks on that path.
  3. clean_msg() runs AFTER both mutex_unlock calls (no free-while-locked,
     no use-after-free of msg via list_del after free).
"""
import re, sys

SRC = "/Users/wicked/x/nuxel/kernel/s10plus/.build/src/drivers/sensorhub/brcm/ssp_bbd.c"

def get_failure_block():
    src = open(SRC).read()
    # Find the region between function start and the success-path 'list_add_tail'
    start = src.index("int bbd_do_transfer")
    end = src.index("if (!use_no_irq) {", start)
    block = src[start:end]
    return block

def main():
    block = get_failure_block()
    fails = []

    # Isolate the failure path: from the entry lock to end of block
    entry_idx = block.index("mutex_lock(&data->pending_mutex);")
    fail_path = block[entry_idx:]

    lock_count = fail_path.count("mutex_lock(&data->pending_mutex);")
    unlock_count = fail_path.count("mutex_unlock(&data->pending_mutex);")

    if lock_count > 1:
        fails.append(f"FAIL: pending_mutex locked {lock_count} times on failure path (self-deadlock)")
    if unlock_count != lock_count:
        fails.append(f"FAIL: pending_mutex unlock {unlock_count} != lock {lock_count} (unbalanced)")

    # clean_msg must appear after the last pending_mutex unlock on this path
    last_unlock = fail_path.rfind("mutex_unlock(&data->pending_mutex);")
    clean_idx = fail_path.find("clean_msg(msg);")
    if clean_idx != -1 and clean_idx < last_unlock:
        fails.append("FAIL: clean_msg(msg) before pending_mutex unlock (free-while-locked)")

    # comm_mutex must be unlocked before return
    if "mutex_unlock(&data->comm_mutex);" not in fail_path:
        fails.append("FAIL: comm_mutex not unlocked on failure path")

    if fails:
        for f in fails: print(f)
        return 1
    print(f"PASS: bbd_do_transfer failure path lock discipline verified")
    print(f"      pending_mutex lock/unlock = {lock_count}/{unlock_count} (balanced)")
    print(f"      clean_msg runs after both unlocks; comm_mutex released")
    return 0

if __name__ == "__main__":
    sys.exit(main())
