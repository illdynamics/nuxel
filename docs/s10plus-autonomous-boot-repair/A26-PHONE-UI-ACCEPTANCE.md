# A26 — PHONE UI ACCEPTANCE (live, on the glass-owning process)

The interface was exercised **only through the running application's own command
FIFO**, `/run/nuxel-ui.cmd`. No second framebuffer client was ever started: A24
measured that a second client's exit runs `fb_release` → `disable regulator(1:vdd2)`
→ dark panel.

## 1. The UI now starts by itself

No workaround was used. `nuxel-ui.service` is an ordinary unit in
`multi-user.target.wants`; once `multi-user.target` became active
(`A26-SYSTEMD-BOOT-GRAPH-FIX.md`) it started on its own:

```
systemctl is-active nuxel-ui.service   -> active
ps -o pid,stat,etime,comm -p $(cat /var/lib/nuxel/ui.pid)
   PID STAT     ELAPSED COMMAND
  6421 R<s        02:21 nuxel-ui
cat /var/lib/nuxel/animation            -> ANIM_STAGE=ANIMATION_STOPPED
cat /var/lib/nuxel/ui-fb-ready          -> PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888
ls -l /run/nuxel-ui.cmd                 -> prw-r--r-- root root /run/nuxel-ui.cmd
```

## 2. Status / navigation / screenshots (FIFO commands)

`status` writes `PAGE=… COMMITS=… PAN_RC=…` to `/var/lib/nuxel/ui-status.txt`.

```
echo status > /run/nuxel-ui.cmd   ->  PAGE=home COMMITS=179 PAN_RC=0
echo page=settings > …            ->  PAGE=settings COMMITS=224 PAN_RC=0
echo page=system   > …            ->  PAGE=system   COMMITS=230 PAN_RC=0
echo page=logs     > …            ->  PAGE=logs     COMMITS=236 PAN_RC=0
echo page=home     > …            ->  PAGE=home     COMMITS=242 PAN_RC=0
```

`COMMITS` advances on every redraw and `PAN_RC=0` reports `fbio_pan_display`
succeeding — i.e. frames are really being pushed to the DECON, not merely drawn
into memory. The process stayed alive throughout.

## 3. Screenshot capture through the UI itself

```
echo "screenshot /var/lib/nuxel/ui-small.ppm" > /run/nuxel-ui.cmd
-> -rw-r--r-- 3283216 bytes   (P6 720x1520, half-scale)
echo "screenshot /var/lib/nuxel/ui-$p.ppm" > /run/nuxel-ui.cmd   (per page)
-> ui-home.ppm ui-settings.ppm ui-system.ppm ui-logs.ppm
   each 13,132,817 bytes = P6 1440x3040x3 + 17-byte header
```

Pulled to the Mac with SHA-256 verified on both sides
(`nuxel-live.sh --pull`); remote and local hashes agreed exactly.

### What the home page contains (structural analysis of the real capture)

Colour histogram of `ui-small.ppm`: dominant `rgb(18,41,82)` panel background,
`rgb(9,21,39)` darker chrome, white `rgb(255,255,255)` text, and a
`rgb(59,130,246)` accent — a dark-blue Nuxel theme. A downsampled luminance
render shows, top to bottom: a status bar; a centred wordmark; a row of four
bordered tiles; a large rounded content panel with several rows of text; a
bottom navigation bar. This matches the intended home layout.

### `screenshot small` argument-handling bug (source-level, found this cycle)

`cmd_handle()` does `const char *v = str_after(a,' '); path = (v==a) ? DEFAULT : v;`
and then `half = str_find(a,"small")`. So bare `screenshot` uses the default
path, but `screenshot small` treats the *word* `small` as the **path** and writes
a file called `small` in the CWD (observed: `/small` existed and was removed).
The correct incantation today is to put `small` inside the path, e.g.
`screenshot /var/lib/nuxel/ui-small.ppm`. Fix queued in `nuxel-ui.c`:
parse `small` as a modifier only when a path token was actually supplied.

## 4. Honest limits

* A framebuffer-memory capture is **not** proof the glass shows it. `PAN_RC=0`
  plus `decon-0 UNBLANK` is strong evidence the frames are being committed, but
  the human-visible check is separate and is recorded in
  `A26-TOUCHSCREEN-ACCEPTANCE.md`.
* The running binary reports `ui-build=A23-fbdev-phone-ui-1`. The A25 initramfs
  ships `opt/nuxel/nuxel-ui.rev = A25-fbdev-phone-ui-1`, so either the installed
  binary predates the A25 revision or the install step did not refresh
  `/var/lib/nuxel/ui-build`. **Not investigated this cycle** — recorded as an
  open item, because "which build is on the glass" matters.
* Stop/restart behaviour and clean shutdown were not exercised (deliberately: a
  stop would drop the panel owner and needs the recovery plan in place first).
