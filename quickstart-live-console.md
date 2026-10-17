# Quickstart — connecting to the Nuxel S10+ Live Console

**What this is.** The shortest path from a host machine (Fedora laptop, or a Mac) onto a
**running** Nuxel S10+ — a USB **CDC-ACM serial gadget** that carries an **interactive root
shell** *and* a **live mirror of the target's `/dev/kmsg`** on one cable.

**Where this came from.** This document is built from **the terminal output in this tmux pane** —
pane `main:1.2` (`%6`) of session `main`, window `main:1`, on host `dextronux`, read back with
`tmux capture-pane -p -S -` on 2026-10-17 ≈01:40 CEST. The sessions visible in that scrollback are
`01a146f6` (the "can I connect to the live console?" answer), `01a1470e` and `01a14716`. Everything
quoted below appears in that scrollback; nothing is reconstructed from memory. Where the scrollback
itself quotes a repo file, the file is named inline.

**The short answer to "can I connect too?"** — **Yes, if the phone actually booted Nuxel.** It is
**not** a network service. There is no host, no port, no user, no password and no key: it is a
serial gadget, and the cable *is* the transport.

---

## 0. TL;DR

```sh
lsusb | grep 18d1                                            # is the gadget even there?
ls -la /dev/ttyACM0 /dev/serial/by-id/                       # node + stable by-id link
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'
```

If the third line prints a `===== … [rc=0 frame=… sha_ok=yes]` header and the command's output,
you are on the console. `/dev/ttyACM0` and `/dev/cu.usbmodem201` are **examples, not constants** —
the number changes across reboots and re-enumerations.

---

## 1. What it actually is

| Thing | Value |
|---|---|
| Gadget / product string | `Nuxel S10+ Live Console` (`Nuxel_Nuxel S10+_Live Console`) |
| USB IDs | `18d1:4ee7` (VID `0x18d1` Google, PID `0x4ee7`) |
| Serial | `NUXEL-S10PLUS-0001` |
| Linux host node | `/dev/ttyACM0` — `root:dialout`, mode `0660` |
| Linux stable alias | `/dev/serial/by-id/usb-Nuxel_Nuxel_S10+_Live_Console_NUXEL-S10PLUS-0001-if00` |
| macOS host node | `/dev/cu.usbmodem<N>` (the `N` changes — never hard-code it) |
| Line settings | `115200 8N1` |
| Target shell | `sh-5.3#`, `uid=0(root)` |
| Transport | framed, unique request id, target-side SHA-256 verified |
| Where it starts | `boot/initramfs/init.sh` runs `/opt/nuxel/nuxel-console` **before systemd exists** (marker `LIVE_CONSOLE_STARTED`) |

Two consequences follow from "before systemd exists", and both are visible in the scrollback:

* the console works even when userspace is broken — which is the whole point of it;
* it is a **gadget the phone has to create from userspace during a successful boot**, so
  "no `/dev/ttyACM*` at all" usually means the boot never got far enough (or the phone is in
  charger/LPM mode, not Nuxel).

> **Select the port by capability, never by name.** Every tool under `tools/beta/live/` matches on
> VID/PID + TTY base + serial + product string, for the same reason `/dev/input/eventN` must not be
> hard-coded for touch.

---

## 2. Confirm the gadget is there

```sh
# Linux
$ lsusb | grep 18d1
Bus 002 Device 015: ID 18d1:4ee7 Google Inc. Nexus/Pixel Device (charging + debug)

$ ls -la /dev/ttyACM0 /dev/serial/by-id/
crw-rw----. 1 root dialout 166, 0 Oct 16 19:30 /dev/ttyACM0
usb-Nuxel_Nuxel_S10+_Live_Console_NUXEL-S10PLUS-0001-if00 -> ../../ttyACM0
```

```sh
# macOS
$ ls -la /dev/cu.usb*
crw-rw-rw-  1 root  wheel  0x9000007 Oct 16 15:21 /dev/cu.usbmodem201
```

An empty `adb devices` is **normal and irrelevant**: `adb` is not the channel here — the serial
console is.

**Permission rule.** The node is `root:dialout 0660`. Be in `dialout`, or use `sudo`.
**Never `chmod` the device node.** (`sudo -n`, i.e. passwordless sudo, was verified on this host.)

---

## 3. Your first command

```sh
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'
```

Real captured output, exactly as it appears in this pane's scrollback:

```
# console /dev/ttyACM0
# shared lock /tmp/nuxel-live._dev_ttyACM0.lock is not usable by uid 0 ([Errno 13] Permission denied: '/tmp/nuxel-live._dev_ttyACM0.lock') — using private lock /tmp/nuxel-live._dev_ttyACM0.0.lock
===== uname -a   [rc=0 frame=d4796c3f sha_ok=yes]
    Linux fedora 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64 GNU/Linux
rc=0
```

How to read that, line by line:

1. `# console /dev/ttyACM0` — the node the tool actually opened. With no `--dev`, discovery found
   it by capability.
2. `# shared lock … using private lock …` — **informational, not an error.** Under `sudo`, Fedora's
   `fs.protected_regular=2` stops root `O_CREAT`-opening another user's file in the sticky `/tmp`,
   so the tool substitutes a private per-uid lock. The single-owner guarantee still holds. A
   *genuinely held* lock is reported as such and exits **3**.
3. `===== <command> [rc=0 frame=<id> sha_ok=yes]` — the frame header. `sha_ok=yes` means the host
   re-verified the target-side SHA-256 of the payload after base64-decoding, so a kernel-log line
   that shredded the stream can never masquerade as a successful result.
4. `rc=0` — the command's **real** exit status, returned from `@@NXR<id>:<rc>@@`.

If nothing is there at all, the tool fails closed with:

```
no CDC-ACM console node (/dev/cu.usbmodem* or /dev/ttyACM*) — is the phone running Nuxel?
```

---

## 4. Reachability preflight (run this first, every time)

```sh
python3 tools/beta/live/nuxel-live-reachability.py --json
```

It selects the port by capability, takes an exclusive lock, proves liveness **both** directions
(any bytes back, then one fully framed SHA-256-verified command) and writes a raw bundle plus a hash
manifest under `docs/beta-finalization/live/evidence/`.

| Exit | Meaning | What to do |
|---|---|---|
| `0` | console reachable | proceed |
| `3` | `BLOCKED_EXTERNAL_RESOURCE` — no gadget, byte-silent port, or **half-alive** console | fix the physical link / retry (see §7) |
| `4` | `BLOCKED_EXTERNAL_RESOURCE` — port already owned by another host tool | stop the other tool; do **not** defeat the lock |

Useful flags: `--dev` (explicit tty, skips capability selection), `--probe-seconds`, `--lock-wait`,
`--escalate` (alternate node → alternate baud → volume burst when the primary node is silent),
`--timeout`.

---

## 5. Recipes

All with `scripts/s10plus-debug-pack/nuxel-live.sh` (add `sudo -n` on Linux):

```sh
# one command
nuxel-live.sh --run 'systemctl status nuxel-ui --no-pager'

# a command that takes a while — always bound it
nuxel-live.sh --run 'sleep 30; echo hi' --timeout 45

# a batch file, one command per line (good for evidence runs)
nuxel-live.sh --batch docs/beta-finalization/preflight/live/batch-1-identity.txt

# just watch: interactive shell + the live kmsg mirror (Ctrl-C to stop)
nuxel-live.sh --watch

# pull a file off the phone
nuxel-live.sh --pull /var/lib/nuxel/ui.ppm --out /tmp/ui.ppm

# pin the node explicitly
nuxel-live.sh --dev /dev/cu.usbmodem201 --run 'id'

# offline self-test of the discovery path — opens NO port, touches no phone
nuxel-live.sh --dry-detect
# -> DISCOVERY-OK: 3/3 checks PASS (root=/dev, real node=/dev/ttyACM0)
```

macOS console helper — same channel, simpler surface:

```sh
nuxel-console-host.sh --list                  # enumerate /dev/cu.usbmodem*
nuxel-console-host.sh --watch                 # stream the console
nuxel-console-host.sh --run 'systemctl --failed'
nuxel-console-host.sh --accept                # the mission acceptance suite, with rc
nuxel-console-host.sh --say hello             # write one line to the target
```

Higher-level live tools on the same channel: `tools/beta/live/nuxel-live-baseline.py` (read-only
baseline), `nuxel-live-deploy.py --apply` (staged userspace deploy, per-file sha256 verify, atomic
install, smallest-service restart, auto-rollback), `nuxel-live-reboot-verify.py` (bounded reboot +
reconnect + verify).

---

## 6. Rules that are enforced, not suggested

1. **One owner per port.** The console mirrors `/dev/kmsg`, so two readers steal each other's bytes.
   The tool holds an exclusive `flock`; never open the port with `screen`/`minicom`/`cat` while a
   tool is running, and never run two live tools in parallel.
2. **Never open `/dev/fb0` from a host tool.** Closing a framebuffer fd runs `decon_release` and
   powers the AMOLED down; one `dd if=/dev/fb0` historically left 1279 pans failing. Screenshots go
   through the running UI's own command FIFO.
3. **No flashing, ever.** No BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/VBMETA/radio writes, no raw
   partition block devices, no repartitioning, no Heimdall/Odin/PIT, no Download Mode, no TWRP, no
   EFS/IMEI/calibration.
4. **No blind reboots.** Normal OS reboot only, only after the pre-reboot checklist, only once the
   console is confirmed answering. If the console is lost, stop rebooting and document.
5. **Bound everything.** `--timeout` on every long command; bounded reconnect, never "wait forever".

---

## 7. "What's the user, password, SSH key, host and port?"

This was the question that started this document, so it gets its own section.

**Serial console (the live console):** there is **no user, no password, no key, no host and no
port.** It hands you an **unauthenticated interactive root shell** — `nuxel-console.c` `chroot()`s
into the real Fedora root and `exec /bin/sh -i` (bash fallback). The security model is *physical USB
access + the single-owner flock*, nothing else. The repository states the residual risk openly:
*whoever controls this process controls a root shell on the phone.* "Host/port" for it is just the
cable: `/dev/ttyACM0`, `115200 8N1`.

**SSH:** **off by default, and there is no SSH key and no default password anywhere in the tree.**
From `configs/nuxel/security/remote-access.json`:

* `enabled: false` (the default); service `sshd-gadget.service` is installed but **not enabled**.
* When enabled it is **publickey only** — it explicitly refuses password, keyboard-interactive and
  root-login-with-password.
* It binds **only the USB gadget interface**: `usb0`, address `10.15.19.82`, port `22`. Binding
  `0.0.0.0`/`::` is a hard-refused state, and it is forbidden over cellular (`rmnet0`).
* `authorized_keys` lives at `/etc/nuxel/security/remote-access/authorized_keys` — **you generate
  the keys on the device**; nothing secret ships in the image.
* Enabling is refused unless the visible indicator `/run/nuxel/remote-access.state` can be rendered
  ("an invisible remote access path is not acceptable").

So: serial console → nothing to authenticate, root shell, cable only. SSH → create the keypair and
enable it yourself; no defaults exist.

---

## 8. What good — and bad — output looks like

A framed round trip, verbatim from `docs/beta-finalization/preflight/live/batch-1-identity.out` as
it appears in the scrollback:

```
# console /dev/ttyACM0
# shared lock /tmp/nuxel-live._dev_ttyACM0.lock is not usable by uid 0 ([Errno 13] Permission denied: '/tmp/nuxel-live._dev_ttyACM0.lock') — using private lock /tmp/nuxel-live._dev_ttyACM0.0.lock
===== uname -a; echo "rc=$?"; cat /etc/fedora-release; head -4 /etc/os-release   [rc=0 frame=cbc65ed0 sha_ok=yes]
    Linux fedora 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64 GNU/Linux
    rc=0
    Fedora release 43 (Forty Three)
    NAME="Fedora Linux"
    VERSION="43 (Forty Three)"
===== id; echo "HOME=$HOME"; echo "PATH=$PATH"   [rc=0 frame=254e5ed2 sha_ok=yes]
    uid=0(root) gid=0(root) groups=0(root)
    HOME=/root
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

Also visible in the same batch: `cat /proc/device-tree/model` →
`Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`, and `/proc/version` →
`Linux version 4.14.253 … #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026`.

A **healthy** post-reboot reconnect (from
`live/evidence/reboot-verify-20261017T004900+0200/reconnect-attempts.json`):

```json
"probe":  { "dev": "/dev/ttyACM0", "bytes_in": 54, "echo_ok": true, "reachable": true,
            "sample": "\nsh-5.3# \nsh-5.3# " },
"frame":  { "framed": true, "rc": 0, "sha_ok": true, "rid": "dd41a9f9", "elapsed_s": 0.834 },
"node":   { "callout": "/dev/ttyACM0", "match_stage": "explicit" }
```

A **half-alive** console looks like the below — bytes come back, but no verified frame — and it is a
**fail**, verdict `BLOCKED_EXTERNAL_RESOURCE`, exit `3`
(`live/evidence/reachability-20261016T212618+0200/reachability.json`):

```json
"blocked_reason": "port answered bytes but no verified command frame (half-alive console)",
"capability": { "vid": "0x18d1", "pid": "0x4ee7", "serial": "NUXEL-S10PLUS-0001" },
"exit_code": 3,
"probe": { "bytes_in": 91, "echo_ok": true, "reachable": true,
           "sample": "\n\u001b[?2004lsh: :s^[[?2004: substitution failed\nsh-5.3# " },
"steps": [ { "step": "select-by-capability", "ok": true },
           { "step": "framed-command", "ok": false,
             "detail": { "framed": false, "sha_ok": false, "rc": null } } ]
```

**Bytes in ≠ a working console.** Do not treat the second as a pass.

An equally common non-error: a console with the `sh-5.3#` prompt and a lone failed substitution line
(`sh: :s: substitution failed`) is normal — that is the mirror stream, not your command failing.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `no CDC-ACM console node … is the phone running Nuxel?` (exit 1) | phone not in Nuxel, cable/port dead, wrong USB role | boot the phone normally into Nuxel; reseat the cable; re-check §2 |
| `… exists but is not readable by <you>` … `Never chmod the node.` | node is `root:dialout 0660` | re-run with `sudo`, or `usermod -aG dialout <you>` + fresh login |
| exit `3`, byte-silent port | gadget enumerated but the console is silent | `--escalate`; verify the handset is running Nuxel, not charger/LPM mode |
| exit `3`, `half-alive console` | bytes but no verified frame | retry; if it persists, the userspace console owner is not running on the target |
| exit `4` | another host tool owns the port | stop it — single-owner rule; never defeat the lock |
| `!! console lost (…)` (exit 4) | USB disconnect / gadget re-enumeration mid-command | `--wait-reconnect <secs>` for the same command once; the gadget re-enumerates by itself |
| `PermissionError`/traceback on the lock | pre-A33 tool under `sudo` on Fedora | update the tool; modern versions substitute a private lock and say so |
| `ioreg unavailable: [Errno 2] …` | macOS-only probe run on Linux | expected; Linux capability enumeration uses `/sys/class/tty/*/device/../idVendor` |
| Output interleaved with `[SSP]`, battery, wlan lines | that is the `/dev/kmsg` mirror doing its job | normal — the framing keeps your command's output separable |

---

## 10. Where the evidence lives

| Path | What |
|---|---|
| `docs/beta-finalization/preflight/live/batch-*.out` / `.txt` | raw live console batches (identity, graphics/input, audio/radio/power, packages/services/receipts) |
| `docs/beta-finalization/preflight/live/no-dev-discovery-run.out` | the glob-safe discovery fix, verified |
| `docs/beta-finalization/live/evidence/reachability-*` | reachability bundles (`reachability.json`, raw probes) |
| `docs/beta-finalization/live/evidence/baseline-*` | read-only baselines (41/41 verified frames) |
| `docs/beta-finalization/live/evidence/deploy-*` | deployment plans and applies |
| `docs/beta-finalization/live/evidence/reboot-verify-*` | reboot + reconnect + verify bundles |
| `docs/beta-finalization/live/BASELINE-CAPTURE.md`, `DEPLOYMENTS.md` | narrative summaries |
| `docs/beta-finalization/preflight/ENVIRONMENT.md` §5, §6, §13 | console reachability measurements and the three host-tool defects that were fixed |

**Provenance.** Terminal scrollback of pane `main:1.2` (`%6`), session `main`, window `main:1`, on
`dextronux` (Linux 6.17.1-300.fc43.x86_64), captured 2026-10-17 ≈01:40 CEST. The sessions visible in
that scrollback are `01a146f6` (the console answer), `01a1470e` and `01a14716`. Console output quoted
inside that scrollback traces to `preflight/live/batch-1-identity.out`,
`preflight/live/no-dev-discovery-run.out`, `live/evidence/reachability-20261016T212618+0200/`,
`live/evidence/reboot-verify-20261017T004900+0200/`, and the headers of
`scripts/s10plus-debug-pack/nuxel-live.sh`, `nuxel-console-host.sh`, `tools/beta/live/nuxel_live.py`
and `tools/beta/live/nuxel-live-reachability.py`.

> **Deliberate omission.** The device's own `androidboot.serialno` / `ap_serial` values are visible in
> the raw `/proc/cmdline` console capture in this scrollback but are **not** reproduced here. Identity
> is established by model, board, SoC and bootloader string.
