# FULL-PWNAGE-104400 — TEE / TrustZone worker stall and runaway load average

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104400.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Eliminate the permanent TEE worker stall that pins the load average at ~13 on an
8-core phone. Restore a responsive system without weakening secure-world isolation and
without breaking anything that legitimately uses TEE (keymaster, keyring, DRM,
Samsung SSP/RPMB).

---

## 1. Current observed state (2026-11-14 16:01 CET)

```
$ uptime
 16:01:41 up  1:15,  load average: 13.02, 13.03, 12.91     # 8 CPUs

$ vmstat 1
 r  b  ...  us sy id wa
 0  0  ...  8  5 88  0     # almost no runnable work, no iowait
```

Blocked (`D`) kernel threads, all present since boot (uptime 1:15):

```
[tEE] tz_worker_threa   × 8   (PIDs 12,18,25,32,39,46,53,60, PPID 2)
[scsi_srpmb_work]             (PID 1037, PPID 2)
[ree_time]                    (PID 1817, PPID 2)
[tz_iwsock]                   (PID 1823, PPID 2)
```

Because `ps`/`vmstat` show ~88 % idle but the load average is ~13, the load is
**uninterruptible-sleep accounting**: the TEE worker kthreads never finish their
first work item. With 8 workers stuck, every subsequent TEE request is likely queued
behind them.

Kernel: `4.14.253-gf7194c1d15ed-dirty #3 SMP PREEMPT Sat Nov 14 09:51:04 CET 2026`
(rebuilt this morning — treat as a prime suspect, exactly as in PWNAGE-104000).

---

## 2. Why this matters

- TEE backs keymaster/keystore, keyring unlock, DRM (Widevine/PlayReady), and some
  Samsung sensor-hub / RPMB paths. A wedged TEE worker can make those hang.
- `scsi_srpmb_work` stuck suggests the RPMB secure-storage path is also blocked.
- `ree_time` / `tz_iwsock` are TEE time/socket workers; `tz_iwsock` blocked can
  wedge any TEE client that waits on the secure socket.
- A load of 13 hides real regressions (e.g. GPS, camera, NFC slow paths) and makes
  monitoring useless.

---

## 3. Non-negotiable rules

1. Do not disable TEE/TrustZone, `CONFIG_TEE`, `optee`, or secure monitor calls to
   "make load go away". Isolation is a security boundary.
2. Do not kill kernel threads; they are not killable and that would be a hack.
3. No flashing without explicit approval. Kernel/config changes need a manifest and
   a get-out-of-jail plan.
4. Every test bounded with a timeout; never wedge the phone in a state that needs a
   battery pull without telling the operator first.
5. Preserve a way to restore the previous kernel/boot image.

---

## 4. Work order

### Step 1 — Characterise the stall

- `cat /proc/<pid>/stack` for each stuck PID (12,18,25,32,39,46,53,60,1037,1817,1823)
  and record the blocking symbols.
- `cat /proc/<pid>/wchan`, `/proc/<pid>/status` (State: D).
- Collect `dmesg | grep -iE 'tee|tz|trustzone|secure|rpmb|optee|smon|mcd'`.
- Determine whether the kernel was built with the TEE driver as before
  (`/proc/config.gz`, `zcat /proc/config.gz | grep -iE 'TEE|OPTEE|TRUSTZONE'`), and
  diff against the last known-good boot image config.
- Check whether a TEE client is waiting: `ls -l /dev/tee*`, `tee-supplicant`, and any
  userspace clients (keyring, keymaster, DRM).

### Step 2 — Identify the change

- Compare with the boot image / kernel from before the 2026-11-14 09:51 rebuild
  (`/root/boot-*.img` snapshots exist; diff config, DTB, and TEE driver sources).
- Check `git log` for `kernel/`, `tee/`, `drivers/tee`, DT changes around that date.
- The previous kernel may not have started `tz_worker_threa` fans-out the same way.

### Step 3 — Fix

Choose the smallest correct fix and justify it:

- Correct a TEE worker/queue initialisation regression in the kernel driver.
- Correct a DT/secure-monitor handshake (e.g. missing `qcom,scm`-style node, wrong
  mailbox/IRQ) that leaves workers waiting forever.
- Restore the previously working TEE driver/config if the rebuild changed it.

If the only practical fix is a boot-image revert, produce the manifest and **stop for
operator approval**.

### Step 4 — Verify

1. After reboot, `ps -eo stat | grep -c '^D'` must be 0 (or explain any remaining
   legitimate blocking).
2. Load average returns to a sane idle value (< nproc).
3. `grep -iE 'tee|tz|rpmb' dmesg` clean.
4. TEE clients work: keyring unlock, any keystore test, DRM playback smoke test.
5. GPS/camera/NFC do not regress (run the GNSS service and confirm no new hang).
6. Survives a second reboot.

---

## 5. Report contract (`REPORT-PWNAGE-104400.md`)

Stack traces, config/DT diffs, the precise regression, the fix, reboot evidence,
load-average before/after, TEE client smoke tests, and rollback. End with
`FULLY_DONE` / `PARTIAL` / `BLOCKED`.
