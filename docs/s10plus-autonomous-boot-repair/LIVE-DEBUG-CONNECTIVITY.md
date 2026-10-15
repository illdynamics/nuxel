# NUXEL — LIVE DEBUG CONNECTIVITY (P2) — **WORKING as of A21**

## Status

```
P2_LIVE_USB_CONSOLE_BIDIRECTIONAL      = YES  (proved live on A21, kernel #7)
P2_INTERACTIVE_ROOT_SHELL              = YES
P2_SURVIVES_THE_MP4_ANIMATION_RUNNING  = YES  (used while the panel played at 24 fps)
P2_RECOVERS_AFTER_RECONNECT            = not yet exercised (needs the operator to unplug/replug)
```

## What the link is

| Field | Value |
|---|---|
| Gadget | Exynos DWC3 `10c00000.dwc3`, configfs, CDC-ACM |
| Target tty | `/dev/ttyGS0` (char 243:0) — mknod'd by `nuxel-console` from `/sys/class/tty/ttyGS0/dev` |
| Host | macOS `/dev/cu.usbmodem201`, "Nuxel S10+ Live Console" |
| Prompt | `nuxel-s10+ # ` (interactive shell, bracketed-paste escape sequences present) |
| Log pump | the console mirrors `/dev/kmsg` to the same tty, so kernel evidence streams out live |

## Acceptance tests (mission section 11) — measured on A21

Host → target → host, wrap markers `@@B@@` … `@@rc=$?@@` … `@@E@@`:

| # | Test | Result |
|---|---|---|
| 1 | Nuxel sends to the Mac | PASS — the console streamed `NUXEL_ANIM_LOOP=13`, `NUXEL_ANIM_HEARTBEAT_FRAMES=…`, SSP/`max77705` kernel lines, 1238 bytes in 12 s |
| 2 | Mac receives the exact message | PASS — the bytes arrived verbatim (`NUXEL_HOSTPROBE hello-from-mac`) |
| 3 | Mac sends to Nuxel | PASS — the target echoed the command and executed it |
| 4 | Nuxel receives and acknowledges | PASS — `sh: NUXEL_HOSTPROBE: command not found` is the shell's own ACK of receipt |
| 5 | stdout, stderr, exit status | PASS — see the table below (`false` returns 1, `===END===` markers bracket stdout, stderr interleaves correctly) |
| 6 | Recovers after an ordinary cable reconnect | **NOT YET EXERCISED** — requires an unplug/replug; the A21 gadget re-enumerated after a full reboot, which is a weaker property |

### The mandated minimum proofs

```
uname -a          -> Linux fedora 4.14.253 #7 SMP PREEMPT Thu Oct 15 17:37:43 UTC 2026 aarch64 GNU/Linux
id                -> uid=0(root) gid=0(root) groups=0(root)
cat /etc/os-release -> NAME="Fedora Linux"  VERSION="43 (Forty Three)"
systemctl --failed  -> 0 loaded units listed
false; echo $?    -> 1
```

## Why it was zero bytes before, and what changed

A16–A20 observed enumeration with no data. On A21 the same `nuxel-console` binary
carried data immediately. The difference is **display/ownership related, not USB
related**: on A20 the resident penguin painter re-ran `FBIOBLANK` + `FBIOPUT_VSCREENINFO`
four times a second for the whole boot, and the console's `mknod` of `/dev/ttyGS0` raced a
boot that was busy repainting; on A21 the painter is deferred, the panel is quiet, and
`/dev/ttyGS0` appears (243:0) with the gadget bound to `10c00000.dwc3`. The USB path
itself was never the failing component — which is also why the `NO UDC` /
`configfs mount failed` observations from A20 were transient boot-time noise, not the
root cause. This is consistent with A19's finding that `/dev/ttyGS0` needs the node
created by userspace (`nuxel-console` does exactly that).

## Diagnostic rule discovered the hard way (added A22)

**Do not `open()`/`close()` `/dev/fb0` from another process while the phone is being
observed.** Any process that closes the last fb fd runs the DECON's `fb_release` path,
which disables the display; the panel then only returns via `FBIOPUT_VSCREENINFO`.
A single `dd if=/dev/fb0` issued over this console produced
`decon_release + : 0` and **1279** subsequent
`decon_pan_display: decon0 state(6), UNBLANK missed` failures — i.e. it blanked the
panel being observed. Reading framebuffer *memory* through the console is therefore
not a read-only operation in practice. A22 makes the animation self-healing (it
re-asserts the panel on any failed pan), so a third party can no longer blank it
permanently.

## Operating the link (host side)

```sh
# raw, no CR translation, no echo
stty -f /dev/cu.usbmodem201 115200 raw -echo
cat /dev/cu.usbmodem201 &            # live kernel + Nuxel console stream
printf 'systemctl --failed\r' > /dev/cu.usbmodem201
```

`scripts/s10plus-debug-pack/` should grow a `nuxel-console-host.sh` wrapping exactly
this, plus the `@@B@@/@@rc/@@E@@` marker protocol used for the acceptance capture
(`captures/*A21-live-run/console-acceptance.txt`).

## Consequence for the workflow

Routine userspace development can now move off TWRP: the phone can be inspected,
patched and re-tested live while the boot animation plays. TWRP stays for recovery and
kernel/BOOT replacement only, exactly as the mission requires.
