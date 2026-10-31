# Diagnosing Issues — Quickstart: console, launcher reload, full reboot

**Verified live:** 2026-10-28 08:43Z / 09:43 CET
**Target:** Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820), Nuxel v0.7.4-beta
**Host:** Fedora 43 laptop, repository at `/x/nuxel`
**Phone state at verification:** USB serial `18d1:4ee7` on `/dev/ttyACM0`; WLAN
`10.20.30.16:22` reachable; `nuxel-wayland.service` and `sshd.service` active.

---

## 0. The quick answer

### Serial — full control, works now

```sh
cd /x/nuxel

# Launcher reload (non-disruptive)
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport serial --run \
  'printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd'

# Full reboot (normal kernel reboot, not a soft reboot)
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport serial --run \
  'systemctl reboot' --timeout 10
```

### WLAN SSH — inspection works now; privileged actions need root SSH

```sh
cd /x/nuxel

export PHONE_IP=10.20.30.16   # use the Target shown by the Wi-Fi SSH Console app

# Confirm the pinned host key and public-key auth
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --status

# Interactive shell as the unprivileged nuxel account
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --shell
```

**Important truth for this image:** WLAN SSH logs in as `nuxel` (uid 1000), not
root. `nuxel` cannot write `/run/nuxel-pwa-host.cmd`, and logind reports
`CanReboot = "challenge"` (interactive authentication required). Therefore the
two privileged actions below **cannot be issued over WLAN SSH as currently
provisioned**. Use serial for those, or do the optional one-time root-key
provisioning in §3.5.

> The reboot command is **`systemctl reboot`**. This is a normal full kernel
> reboot. Do **not** use `reboot -f`, `systemctl reboot --force`, or
> `systemctl soft-reboot` for this procedure. Those are not the supported
> normal reboot path.

---

## 1. What was actually verified on this laptop

The commands and output below are from the live phone, not reconstructed. The
launcher reload was actually executed during verification. **The phone was not
rebooted**; `systemctl reboot --dry-run` was used only to confirm the command
path on both transports.

### 1.1 Serial console identity

```console
$ sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport serial --run 'id; uname -a; systemctl is-active nuxel-wayland.service nuxel-pwa-host.service sshd.service'
# console /dev/ttyACM0
===== id; uname -a; systemctl is-active nuxel-wayland.service nuxel-pwa-host.service sshd.service 2>&1   [rc=0 frame=8cb4b53d sha_ok=yes]
    uid=0(root) gid=0(root) groups=0(root)
    Linux ... 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64 GNU/Linux
    active
    inactive
    active
```

`nuxel-pwa-host.service` is **inactive by design**: the host is launched under
`nuxel-wayland.service`. Do not restart `nuxel-pwa-host.service`; restart
`nuxel-wayland.service` only if the launcher host itself is wedged.

### 1.2 Launcher reload over serial

```console
$ sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport serial --run 'echo "BEFORE=$(date -u +%FT%TZ)"; tail -2 /run/nuxel-home.state 2>/dev/null; printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd; rc=$?; sleep 3; echo "fifo_rc=$rc"; echo "AFTER=$(date -u +%FT%TZ)"; grep -a "HOST_ACTION reload-launcher" /run/nuxel-home.state | tail -2; echo "BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)"; echo "UPTIME=$(cut -d" " -f1 /proc/uptime)s"'
# console /dev/ttyACM0
===== echo "BEFORE=$(date -u +%FT%TZ)"; tail -2 /run/nuxel-home.state 2>/dev/null; printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd; rc=$?; sleep 3; echo "fifo_rc=$rc"; echo "AFTER=$(date -u +%FT%TZ)"; grep -a "HOST_ACTION reload-launcher" /run/nuxel-home.state | tail -2; echo "BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)"; echo "UPTIME=$(cut -d" " -f1 /proc/uptime)s"   [rc=0 frame=6227b5ad sha_ok=yes]
    BEFORE=2026-10-28T08:43:37Z
    1793177014 HOST_CONFIG_GET name=wlfb-state bytes=94
    1793177016 HOST_CONFIG_GET name=wlfb-state bytes=94
    fifo_rc=0
    AFTER=2026-10-28T08:43:40Z
    1793177017 HOST_ACTION reload-launcher -> launcher page
    BOOT_ID=9cc0f1e0-8134-4f9f-8d17-f5935934d70a
    UPTIME=3194.29s
```

That line is the proof: the native host accepted the action and dispatched it to
the launcher page. The page performs `window.location.reload()`; the PWA host
and compositor stay running.

### 1.3 WLAN SSH identity and limitation

```console
$ ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan --host 10.20.30.16 --status
# wlan   AVAILABLE nuxel@10.20.30.16:22 account=nuxel host key verified; public-key auth ok
#   tool:ssh     OK
#   tool:scp     OK
#   private-key  OK           /home/wicked/.ssh/nuxel-tri-link_ed25519
#   host-key     OK           pinned key matches the phone
#   tcp          OK           tcp connect ok
#   auth         OK           publickey accepted
#   remote-shell OK           /usr/bin/bash
```

```console
$ ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan --host 10.20.30.16 --exec 'id; ls -l /run/nuxel-pwa-host.cmd; busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanReboot' --allow-busy-deploy
uid=1000(nuxel) gid=1000(nuxel) groups=1000(nuxel)
prw------- 1 root root 0 Oct 28 08:52 /run/nuxel-pwa-host.cmd
s "challenge"
```

A `challenge` result means polkit wants interactive authentication. There is no
`sudo` on the phone and no password/keyboard-interactive SSH, so a non-root SSH
session cannot satisfy it.

---

## 2. Serial path — step by step (recommended for these actions)

### 2.1 Connect the laptop

1. Connect the phone to the laptop with a **USB data** cable (not charge-only).
2. Confirm the Nuxel gadget enumerated:

   ```sh
   lsusb | grep 18d1
   ```

   Expected: a line containing `18d1:4ee7`.

3. Confirm the stable console link:

   ```sh
   ls -l /dev/serial/by-id/ | grep -i nuxel
   ```

   Expected symlink:

   ```text
   usb-Nuxel_Nuxel_S10+_Live_Console_NUXEL-S10PLUS-0001-if00 -> ../../ttyACM0
   ```

   `/dev/ttyACM0` is usual, but the number can change after a reboot. Prefer the
   `by-id` link or let the tool discover by capability.

4. If the serial node is `root:dialout 0660`, either join `dialout` or use
   `sudo -n`. Do **not** `chmod` the device node.

### 2.2 Prove the console answers

```sh
cd /x/nuxel

sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run 'id; uname -a'
```

Expected: `uid=0(root)`, the S10+ kernel line, and a frame ending in
`sha_ok=yes`. If you see `===== ... [rc=0 ... sha_ok=yes]`, the framed console
is working.

### 2.3 Reload the launcher

This is the quick, non-disruptive reload:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run \
  'printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd; sleep 3; grep -a "HOST_ACTION reload-launcher" /run/nuxel-home.state | tail -1'
```

Expected result:

```text
HOST_ACTION reload-launcher -> launcher page
```

If you only want to fire the action and not verify it:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run \
  'printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd'
```

Do **not** replace this with `systemctl restart nuxel-wayland.service` unless the
launcher is actually wedged. That restarts the compositor/UI stack and is much
heavier than a launcher page reload.

### 2.4 Full reboot

First record the current boot identity:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run \
  'echo BOOT_ID=$(cat /proc/sys/kernel/random/boot_id); echo UPTIME=$(cut -d" " -f1 /proc/uptime)s'
```

Then issue the full reboot:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run 'systemctl reboot' --timeout 10
```

The USB console **will disappear**. A timeout, `ConsoleLost`, or non-zero exit
from the host tool is expected because the phone is rebooting. Do not retry the
reboot just because the command lost its transport.

### 2.5 Verify the phone returned

Wait for the gadget to re-enumerate, then reconnect. The node may change from
`ttyACM0` to another number, so use the `by-id` link or let the tool discover it.

```sh
sleep 45
ls -l /dev/serial/by-id/ | grep -i nuxel

sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run \
  'echo BOOT_ID=$(cat /proc/sys/kernel/random/boot_id); echo UPTIME=$(cut -d" " -f1 /proc/uptime)s; systemctl is-active nuxel-wayland.service sshd.service'
```

A real reboot is proven by a **changed `BOOT_ID`** and a small `UPTIME`.
`systemctl is-active` should return `active` for `nuxel-wayland.service` and
`sshd.service`.

### 2.6 Optional: guarded reboot with pre/post checks

The repository also ships a guarded reboot verifier. This is slower, but it
performs the pre-reboot checklist, uses the reboot policy, waits for the console
to return, and captures post-reboot evidence:

```sh
sudo -n python3 tools/beta/live/nuxel-live-reboot-verify.py \
  --dev /dev/ttyACM0 \
  --reboot \
  --reason 'operator requested full reboot' \
  --diagnostic 'post-reboot boot_id, uptime and session-unit check' \
  --reboot-cmd 'systemctl reboot' \
  --reconnect-timeout 240
```

Use `--reboot-cmd 'systemctl reboot'` explicitly. The tool's default contains
`--force`; the normal Nuxel reboot path is the non-forced command above.

---

## 3. WLAN SSH path — step by step

### 3.1 Connect the laptop and phone to the same LAN

The current Nuxel WLAN is normally `10.20.30.0/24`. The phone address is
**dynamic**; read it from the phone's **Wi-Fi SSH Console** app (the `Target`
field) or ask over serial:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run 'ip -4 -o addr show wlan0'
```

Do not guess or hard-code the address.

Required host material:

- private key: `~/.ssh/nuxel-tri-link_ed25519` (mode `0600`)
- pinned host key: `configs/nuxel/security/ssh/known_hosts`
- expected fingerprint: `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`

### 3.2 Check reachability and host-key trust

```sh
cd /x/nuxel
export PHONE_IP=10.20.30.16   # replace with the app's Target

./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --status
```

Expected:

```text
wlan   AVAILABLE   nuxel@...:22   account=nuxel   host key verified; public-key auth ok
```

Do **not** run this with `sudo`. Under `sudo`, the wrapper looks for the private
key under `/root/.ssh/` and reports WLAN unavailable. Run it as your normal
laptop user.

### 3.3 Open a shell or run an inspection command

Interactive:

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --shell
```

One-shot:

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --exec \
  'id; echo BOOT_ID=$(cat /proc/sys/kernel/random/boot_id); systemctl is-active nuxel-wayland.service sshd.service'
```

This is the useful WLAN SSH role on the current image: inspection, logs, files,
and read-only diagnosis.

### 3.4 Current limitation: privileged actions over WLAN SSH

The WLAN account is `nuxel`, and it is not root:

```console
$ ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan --host "$PHONE_IP" --exec 'id; nuxelctl action reload-launcher'
uid=1000(nuxel) gid=1000(nuxel) groups=1000(nuxel)
Traceback (most recent call last):
  ...
PermissionError: [Errno 13] Permission denied: '/run/nuxel-buttons.cmd'
```

Likewise:

```console
$ ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
    --transport wlan --host "$PHONE_IP" --exec \
    'busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanReboot'
s "challenge"
```

So on this image:

- WLAN SSH **can** connect, inspect, read logs, copy files, and run diagnostics.
- WLAN SSH **cannot** write the root-owned launcher FIFO.
- WLAN SSH **cannot** issue a reboot without an interactive polkit credential.

**Use the serial path in §2 for launcher reload and full reboot.** This is the
fastest working route today.

### 3.5 Optional: one-time root SSH provisioning (only if you need WLAN-only admin)

This is a deliberate privilege change: it lets a root-authorized key log in over
the local WLAN. The phone's `sshd` policy already permits `root` from
`10.20.30.0/24` with `PermitRootLogin prohibit-password`, but a root key must be
installed first. Do this only on a trusted LAN.

Recommended: generate a **separate** root key on the laptop.

```sh
ssh-keygen -t ed25519 -f ~/.ssh/nuxel-root_ed25519 -N ''
PUBKEY="$(cat ~/.ssh/nuxel-root_ed25519.pub)"
```

Install it over the serial console (one time):

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run \
  "install -d -m 700 /root/.ssh; grep -qxF '$PUBKEY' /root/.ssh/authorized_keys 2>/dev/null || printf '%s\n' '$PUBKEY' >> /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys"
```

Verify root SSH before relying on it:

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" \
  --user root --key ~/.ssh/nuxel-root_ed25519 \
  --exec 'id; echo root-ssh-ok'
```

Expected: `uid=0(root)` and `root-ssh-ok`.

Then the WLAN equivalents are:

```sh
# Launcher reload over WLAN SSH as root
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" \
  --user root --key ~/.ssh/nuxel-root_ed25519 \
  --exec 'printf "action reload-launcher\n" > /run/nuxel-pwa-host.cmd; sleep 3; grep -a "HOST_ACTION reload-launcher" /run/nuxel-home.state | tail -1'

# Full reboot over WLAN SSH as root
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" \
  --user root --key ~/.ssh/nuxel-root_ed25519 \
  --exec 'systemctl reboot' --timeout 10
```

Again, the SSH connection will drop during the reboot. Reconnect with
`--status` and compare `BOOT_ID`/`UPTIME` as in §2.5.

If you do not want to add a root key, stop at §3.3 and use serial for the two
privileged actions. That is the safer default.

---

## 4. Which path should I use?

| Need | Use |
|---|---|
| Quickest launcher reload | Serial — §2.3 |
| Quickest full reboot | Serial — §2.4 |
| Diagnose from another room / no USB cable | WLAN SSH — §3.3, then serial for privileged actions |
| WLAN-only reload/reboot | Optional root SSH provisioning — §3.5 |
| Guarded reboot with evidence | `nuxel-live-reboot-verify.py` — §2.6 |

---

## 5. Troubleshooting

### `no CDC-ACM console node`

- Use a USB **data** cable.
- Confirm `lsusb | grep 18d1` shows `18d1:4ee7`.
- Confirm `ls -l /dev/serial/by-id/ | grep -i nuxel`.
- Wake/unlock the phone; a charger-only or LPM boot may not create the gadget.
- After a reboot the node may change from `ttyACM0` to another number. Use the
  `by-id` link or let the tool discover by capability.

### `serial port busy` or `lock ... owned by another host tool`

Another host tool owns the single-owner serial console. Wait for it to finish,
then retry. Do not delete the lock and do not run `screen`, `minicom`, `cat`,
and a Nuxel tool against the same port at the same time.

### WLAN SSH says `private key not found` under `sudo`

Run the WLAN commands as your normal laptop user, not with `sudo`. The key is at
`~/.ssh/nuxel-tri-link_ed25519`, not `/root/.ssh/`.

### WLAN SSH says `authentication failed` as `root`

Root key login is not provisioned for this laptop. Either use serial, your
existing root-authorized key, or the optional provisioning in §3.5. The current
root `authorized_keys` entry is `wicked@infranux`; it is not present on this
laptop.

### WLAN SSH mutation is refused because a serial session owns the phone

The wrapper serialises serial deploy/console sessions. Wait for the serial
command to finish and retry. `--allow-busy-deploy` should only be used when you
are certain no serial deployment is active; it is not a general-purpose bypass.

### Launcher reload returns `HOST_ACTION_REFUSED reload-launcher`

That is a stale/old host binary or a mismatched host image. Check the live host
path and version; do not loop the command. On a current image the accepted line
is exactly `HOST_ACTION reload-launcher -> launcher page`.

### Launcher reload works but the UI still looks stale

The reload is a page reload, not a cache purge. If assets are stale, restart the
heavier UI stack from serial:

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run 'systemctl restart nuxel-wayland.service'
```

Then wait for the launcher to come back. This is an escalation, not the normal
reload.

---

## 6. Safety rules

- **One owner per serial port.** The console mirrors `/dev/kmsg`; concurrent
  readers steal bytes. The tool holds an exclusive lock.
- **No force reboot.** Use `systemctl reboot`; never `reboot -f` or
  `systemctl reboot --force`.
- **No flashing or partition writes.** These console procedures are userspace
  only.
- **Do not reboot blind.** Record `boot_id` and uptime before, and confirm a
  changed `boot_id` and returning services after. The repository policy refuses
  repeated identical reboot attempts.
- **Treat the USB cable and the SSH private key as root credentials.**
- **Do not add a root WLAN key casually.** §3.5 is optional and persistent;
  prefer serial for privileged actions unless WLAN-only admin is required.
