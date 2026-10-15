# A26 — P1: LIVE CONSOLE AND DEPLOYMENT VALIDATED

Everything here was used for real during this cycle; nothing is aspirational.

## 1. What was actually wrong with the old console path

* `nuxel-live.sh` (v1) framed a command with `@@B@@` … `@@rc=$?@@` and a fixed
  `sleep 3`. During a burst of kernel log (`sec_ts`, `[SSP]`, `wl_cfg80211`,
  watchdog) the command's output could be **eaten**, and a long-running command
  wedged the single shared shell for minutes — every later command queued silently
  behind it. Measured: after `systemctl restart systemd-udevd`, a plain
  `echo ALIVE; uptime` returned **no output at all**, several commands in a row.
* `nuxel-live-deploy.sh` verified a SHA-256 of the *staged* file, which is good,
  but had no host-side serialisation, no cancellation and no pull direction.

## 2. New host tool: `scripts/s10plus-debug-pack/nuxel-live.sh`

The old file is kept as `nuxel-live.v1.sh`.

| Requirement | How it is met |
|---|---|
| one writer per port | `flock` on `/tmp/nuxel-live.<dev>.lock`; a second tool refuses with exit 3 |
| unique per-command id | `<4 hex random><4 hex time>` in every marker |
| unambiguous framing | target writes output to `/var/tmp/nx-<id>.out`, then emits `@@NXB<id>@@`, `@@NXR<id>:<rc>@@`, `@@NXH<id>:<sha256>@@`, the base64 body, `@@NXE<id>@@` |
| real exit status | `@@NXR<id>:<rc>@@` comes from the shell, not from a guess |
| stdout and stderr | both captured (`>file 2>&1`) — **merged by design**, documented |
| bounded execution | `--timeout` (default 20 s) |
| cancellation | on timeout the host writes Ctrl-C into the port and drains, so the shared shell is *never* left wedged |
| partial-response detection | no `@@NXE@@` ⇒ `FRAMED-ERROR` + exit 1, never a silent success |
| corruption detection | the target's SHA-256 of the payload is recomputed after base64 decode; mismatch ⇒ automatic retry (3 attempts), then `UNVERIFIED` |
| kmsg interference | lines matching the kernel-log shape are filtered out; base64 lines are required to match a strict charset, so telemetry cannot be mistaken for data |
| no false success | `rc` absent ⇒ explicit failure; hash mismatch ⇒ failure |
| no cross-talk | markers carry the request id, so one command's output cannot be consumed as another's |

Live evidence it works:

```
===== echo HELLO_FRAME; id; uname -r; printf "stderr-line\n" >&2; false   [rc=1 frame=c3b6414d sha_ok=yes]
    HELLO_FRAME
    uid=0(root) gid=0(root) groups=0(root)
    4.14.253
    stderr-line
```
```
(frame 65ff42b8 integrity mismatch on attempt 1 — re-requesting)
===== … [rc=0 frame=827342cf sha_ok=yes]
```
```
===== … [FRAMED-ERROR: no end marker within 90s — command cancelled]
     ! ^C   ← the shell survived and answered the next command
```

Runtime dropped from ~6 s per command (v1) to ~1.9 s (v2) at equal or better
reliability.

## 3. Safe binary transfer (both directions)

**Push** (`nuxel-live-deploy.sh`, unchanged contract): gzip+base64, bounded by an
exact byte count (`head -c <len>`), target-side `sha256sum` compared to the local
hash, previous file kept as `*.prev`, only then installed.

**Pull** (new): `nuxel-live.sh --pull <remote> [--out <local>]`

```
$ nuxel-live.sh --timeout 240 --pull /var/lib/nuxel/ui-small.ppm --out /tmp/ui-small.ppm
# remote /var/lib/nuxel/ui-small.ppm sha256 7a83b03c4d34546572ca3c690f3ce2acee2a898a6dc41e1c5c1756ff0fc19eed
# wrote /tmp/ui-small.ppm (3283216 bytes) sha256 7a83b03c…9eed VERIFIED
```

It fetches the remote SHA-256 first, transfers `gzip -9 | base64`, decompresses,
and refuses to write unless the bytes match the remote hash. This is how the UI
screenshots were retrieved for review.

## 4. Reconnection: measured, twice

* The Mac closed the port and reopened it repeatedly; the shell came back every
  time on the same `/dev/cu.usbmodem201` (the A24 `trap '' HUP` + respawn
  supervisor holds).
* **Full USB loss was also exercised by accident.** While the udev storm was
  melting the board, the gadget vanished completely
  (`ls /dev/cu.usbmodem*` → no match; the device was absent from
  `system_profiler SPUSBDataType` for ~30 s) and then **re-enumerated by itself**
  as `/dev/cu.usbmodem201` with the same serial `NUXEL-S10PLUS-0001`. No reboot of
  the Mac, no `kextload`, no replug. The console came straight back.
* One real bug found by that event: the host tool raised
  `OSError: [Errno 6] Device not configured` instead of reporting a clean
  disconnect. **Open item** — `nuxel-live.sh` should trap `OSError` on the serial
  fd and retry/report `console lost`, not traceback.

## 5. Durable developer workflow (all executed this cycle)

| Task | Command |
|---|---|
| execute a command | `nuxel-live.sh --run '<cmd>'` |
| bounded / cancellable | `nuxel-live.sh --run '<cmd>' --timeout 90` |
| batch | `nuxel-live.sh --batch file.txt` |
| stream journal | `nuxel-live.sh --run 'journalctl -b -u X --no-pager -n 40'` |
| query services | `systemctl is-active/is-system-running` via `--run` |
| transfer a file (down) | `nuxel-live.sh --pull <remote> --out <local>` |
| deploy a binary (up) | `nuxel-live-deploy.sh <binary> --to <path> [--restart <unit>]` |
| restart a service | `nuxel-live.sh --run 'systemctl restart <unit>'` |
| inspect UI state | `--run 'echo status > /run/nuxel-ui.cmd; sleep 1; cat /var/lib/nuxel/ui-status.txt'` |
| screenshot via the UI | `--run 'echo "screenshot /var/lib/nuxel/ui-small.ppm" > /run/nuxel-ui.cmd'` then `--pull` |
| watch | `nuxel-live.sh --watch` |

The console never opens `/dev/fb0` — that rule is why the UI is driven through
its own FIFO.

## 6. Follow-ups not done

1. `OSError` handling on cable pull (above).
2. A second, bulk channel: the mission suggests USB networking with authenticated
   SSH. The gadget is CDC-ACM only and the UDC can carry one bound gadget, so
   adding a network function means re-configuring (or replacing) the gadget in the
   initramfs — a BOOT change, deliberately **not** attempted while the console is
   the only lifeline. Recommend an ECM/RNDIS function added alongside ACM in the
   next initramfs, then SSH/scp for bulk work, with ACM kept as the fallback.
3. `nuxel-live-deploy.sh` should adopt the v2 framing/verification helpers.
