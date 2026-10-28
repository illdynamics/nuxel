# Nuxel Tri-Link Consoles — Quickstart

_Status as of 2026-10-28 · Nuxel v0.7.2-beta_

A step-by-step guide to the three Nuxel S10+ console entries:

| Phone app | Transport | What it is | Current state |
|---|---|---|---|
| **Serial Live Console** | USB CDC-ACM serial | Framed root recovery console over the USB cable | **READY** |
| **Wi-Fi SSH Console** | WLAN + SSH | Key-only OpenSSH shell over the phone's Wi-Fi address | **READY** when the app reports it |
| **USB SSH Console** | USB network + SSH | SSH over a USB NCM/RNDIS/ECM network gadget | **BLOCKED** on kernel 4.14.253 |

> **Read this first:** the three phone apps are **status panels**, not an
> in-phone terminal. They show the real phone-side endpoint, run read-only
> checks and print the exact host command. The interactive shell, file transfer
> and recovery commands run on the **development host**.

The verified host for this quickstart is Fedora 43. Commands are run from the
repository root:

```sh
cd /x/nuxel
```

---

## 0. One-minute path

```sh
# From the repository root.
# 1. See what is reachable right now.
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport auto --discover

# 2. Open Wi-Fi SSH (use the IP shown by the phone app; replace PHONE_IP).
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host PHONE_IP --shell

# 3. If SSH is unavailable, use the serial recovery console instead.
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'
```

Never use `--transport auto` as a silent fallback in the middle of a debugging
or deployment task. It reports what it discovered, selects one SSH transport,
and stops. Serial remains an explicit recovery choice.

---

## 1. What you need

- A **Nuxel S10+** that has booted past the lockscreen and is unlocked.
- The repository checked out on the host, with `python3` and the OpenSSH client.
- A USB **data** cable for serial recovery. A charge-only cable will not create
  a console device.
- For Wi-Fi SSH: the phone and host on the same local network, normally the
  `10.20.30.0/24` Nuxel network.
- For SSH: the host private key at
  `~/.ssh/nuxel-tri-link_ed25519` and the pinned host key in
  `configs/nuxel/security/ssh/known_hosts`.

On Linux, the serial node is normally `/dev/ttyACM0`, owned by
`root:dialout` with mode `0660`. Either join the `dialout` group or use
`sudo -n`. Do not `chmod` the device node.

---

## 2. Open a console from the phone

1. Unlock the phone. You should land on **Home**, not on a stale app or drawer.
2. Open the **Applications** drawer or app grid.
3. Tap the console you want:
   - **Serial Live Console**
   - **USB SSH Console**
   - **Wi-Fi SSH Console**
4. Read the **state**, **Target**, **Auth** and **Detail** fields.
5. Tap **Recheck** after changing Wi-Fi, reconnecting the cable or restarting
   SSH.
6. Tap **Copy host command** and run that exact command on the development
   host. The app does not store or use a private key on the phone.

### State meanings

| State shown by the app | Meaning |
|---|---|
| **READY** | The phone-side checks passed. The host still verifies the pinned host key and authenticates the key. |
| **CHECKING** | A read-only status refresh is in progress. |
| **SETUP REQUIRED** | The transport exists but is not fully provisioned or listening. |
| **UNAVAILABLE** | The transport cannot currently be used. Read the detail and checks. |
| **UNAVAILABLE · KERNEL BLOCKER** | The running kernel is known to be unsafe for this transport. Do not force it. |

A READY app is **not** proof that the host can connect. Confirm from the host
with `--status`, then open the shell.

---

## 3. Use the Serial Live Console

This is the recovery path. It works independently of Wi-Fi and SSH.

### 3.1 Connect the cable

1. Connect the phone to the host with a USB data cable.
2. On Linux, check for the Nuxel gadget:

   ```sh
   lsusb | grep 18d1
   ls -l /dev/serial/by-id/ 2>/dev/null | grep -i nuxel
   ```

   The USB IDs are `18d1:4ee7`. The node is usually `/dev/ttyACM0`, but the
   number can change after a reboot or re-enumeration.

3. Confirm the stable by-id link or let the launcher discover the port by
   capability:

   ```sh
   ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport auto --discover
   ```

### 3.2 Run a framed command

```sh
sudo -n ./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport serial --run 'id; uname -a'
```

Or use the existing serial launcher directly:

```sh
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --run 'uname -a'
```

A successful frame includes `rc=0 ... sha_ok=yes`; the command's real exit
status is returned at the end. For a long command, always bound it:

```sh
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh \
  --run 'sleep 30; echo done' --timeout 45
```

### 3.3 Other serial actions

```sh
# Interactive shell + live kernel log mirror; Ctrl-C to stop.
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh --watch

# Pull a file from the phone.
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh \
  --pull /var/lib/nuxel/ui.ppm --out /tmp/ui.ppm

# Batch file, one command per line.
sudo -n bash scripts/s10plus-debug-pack/nuxel-live.sh \
  --batch path/to/commands.txt
```

### 3.4 Serial rules

- **One owner per serial port.** Do not run `screen`, `minicom`, `cat` or a
  second Nuxel tool against the same tty while one is running.
- If the tool says the lock is held, stop the other owner deliberately. Do not
  defeat or delete the lock.
- Serial is unauthenticated root access protected by physical USB access and the
  exclusive lock. Treat the cable as a root credential.
- If `/dev/ttyACM*` is absent, check the data cable, phone boot state and
  charger/LPM state before changing software.

---

## 4. Use the Wi-Fi SSH Console

The phone app discovers the current Wi-Fi IPv4 address and displays the exact
command. **Use the address shown by the app**; the recorded address
`10.20.30.16` is an example, not a permanent value.

### 4.1 Check reachability and the pinned host key

```sh
export PHONE_IP=10.20.30.16   # replace with the Target shown in the app

./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --status
```

Expected result:

```text
wlan   AVAILABLE   nuxel@...:22   account=nuxel   host key verified; ...
```

The host key must match the pinned Ed25519 key:

```text
SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs
```

### 4.2 Open an interactive shell

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --shell
```

The launcher reports the selected transport, account and remote shell, then
hands the terminal to Bash when Bash is available. Type `exit` to leave; the
shell's exit status is preserved.

### 4.3 Run a command and preserve its exit code

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --exec 'id; uname -a'
```

Test real status propagation:

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --exec 'exit 7'
echo "remote status: $?"   # must print 7
```

### 4.4 Transfer a file with SHA-256 verification

```sh
# Upload: local path first, remote path second.
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" \
  --put ./README.md /var/tmp/README.md

# Download: remote path first, local path second.
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" \
  --get /var/tmp/README.md /tmp/README.returned.md
```

Both directions stage to a temporary path, verify SHA-256, and only then move
the file into place. `--put` and `--get` take the cross-transport deployment
guard; a concurrent transfer or serial deployment is refused.

### 4.5 Let `auto` choose an available SSH transport

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport auto --discover
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport auto --shell
```

`auto` prints every discovery result and the selected transport before
connecting. If no SSH transport is available, it exits with status `3`; it does
not fall back to serial.

### 4.6 Remember the current target

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --remember
```

This writes the target to `~/.config/nuxel/live-ssh.json`. It does not store a
private key on the phone.

### 4.7 First-time key setup — only if authentication fails

If the app says **SETUP REQUIRED**, or the host gets authentication error
`5`, check the setup before changing anything:

```sh
# Create the host key only if it does not already exist.
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --init-key
```

If it creates a key, place the printed **public** key in
`configs/nuxel/security/ssh/authorized_keys.nuxel`, then deploy the SSH policy
over serial with the transactional manifest:

```sh
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/nuxel-ssh-provision-manifest.json \
  --name tri-link-ssh-apply --dev /dev/ttyACM0 --apply --timeout 30 \
  --lock-wait 30 --reconnect-timeout 180
```

Replace the host user/group in `-u wicked -g dialout` if your workstation uses
different names. Never copy the private key to the phone, enable password
authentication, or use a wildcard `AllowUsers` entry.

For a replacement phone or a deliberately changed host key, pin it explicitly
after confirming the fingerprint out-of-band:

```sh
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_IP" --trust-host-key
```

Do this only after verifying the new fingerprint. A normal connection must
never bypass host-key checking.

---

## 5. Use the USB SSH Console

The USB SSH app is present, but the transport is **not usable on the current
kernel**.

- The live kernel is Samsung-derived **4.14.253**.
- `CONFIG_USB_F_NCM` and `CONFIG_USB_CONFIGFS_NCM` are compiled in, but NCM
  teardown previously panicked the phone in `ncm_free_inst`, and the watchdog
  rebooted it.
- The app therefore reports **UNAVAILABLE · KERNEL BLOCKER** with evidence at
  `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`.
- There is no `usb0`/`ncm0`/`rndis0` transport to connect to.

### What to do now

1. Open **USB SSH Console** and confirm that it does not claim READY.
2. Use **Wi-Fi SSH Console** for network shell access.
3. Use **Serial Live Console** for recovery.
4. Do **not** run `tools/beta/live/nuxel-usb-net.py --apply` on kernel
   4.14.253, and do not bypass the helper with `--allow-unsafe-kernel`.
5. Do not retry NCM teardown to “see if it works”. The failure caused a real
   kernel panic and reboot.

USB SSH can be reconsidered only after a fixed kernel/gadget stack is available
and the capability audit and physical acceptance tests are repeated.

---

## 6. Exit codes and troubleshooting

Local Tri-Link failures use these exit codes. A successfully connected remote
command returns **its own** status, such as `7`, unchanged.

| Code | Meaning | First action |
|---|---|---|
| `0` | Success or transport available | Continue |
| `2` | Usage or validation error | Fix the command/arguments |
| `3` | Transport unavailable | Check cable, Wi-Fi, phone app state and `--discover` |
| `4` | Host-key mismatch | **Stop.** Compare the fingerprint over serial; do not bypass |
| `5` | Authentication failure | Check the private key path and `authorized_keys` |
| `6` | Network, route, timeout or refusal | Check IP, same LAN, route and `sshd` state |
| `7` | Transfer or checksum failure | Re-run; inspect staging and free space |
| `8` | Transfer/deployment lock conflict | Wait for or deliberately stop the other owner |
| `130` | Cancelled with Ctrl-C | Remote work may still be finishing |

### Common problems

**No serial node / no `/dev/ttyACM*`**
: Try a known data cable, confirm the phone actually booted Nuxel, and check
  `lsusb | grep 18d1`. An empty `adb devices` is irrelevant; this is not ADB.

**Serial port busy**
: Another host tool owns the single-owner lock. Find and stop that owner; do not
  delete the lock or open the tty with another terminal.

**Wi-Fi app says READY, host says connection refused**
: `sshd` is not listening. Use serial recovery to inspect `systemctl status
  sshd --no-pager`; restart it deliberately if appropriate.

**Wi-Fi app says READY, host times out**
: The phone may have changed address, left the network, or the host route/VPN is
  wrong. Re-read the app's Target and re-run `--status`.

**Host-key mismatch**
: The phone's host key changed, or you are connecting to another device. Do not
  disable `StrictHostKeyChecking`. Investigate over serial before using
  `--trust-host-key`.

**A freshly changed Wi-Fi subnet is refused**
: `sshd` allows only the configured CIDRs. Update
  `configs/nuxel/security/ssh/60-nuxel-tri-link.conf` and redeploy through the
  serial transaction; do not add a wildcard.

**USB SSH says blocked**
: Expected on kernel 4.14.253. Continue with Wi-Fi SSH or serial. Do not retry
  NCM.

---

## 7. Safe operating rules

1. **One serial writer, always.** The serial stream mirrors `/dev/kmsg`; two
   readers corrupt the evidence.
2. **No silent fallback.** Use `--transport auto --discover` to inspect, then
   choose explicitly. Do not let a deployment report success on the wrong link.
3. **No simultaneous mutating transfers.** `--put`, `--get` and deployments take
   the cross-transport guard. Refuse, do not race.
4. **No password SSH.** Public-key authentication only. Keep the private key on
   the host and the host key pinned.
5. **No Internet exposure.** Do not forward port 22. Access is intended for the
   local Nuxel WLAN; the current image restricts access with `sshd`
   `AllowUsers user@CIDR`, not a firewall binary.
6. **No USB NCM experiment on 4.14.253.** It has already caused a kernel panic
   and watchdog reboot.
7. **Firmware stays untouched.** These consoles do not flash, repartition,
   wipe, or modify the kernel.

---

## 8. Useful files

| File | Purpose |
|---|---|
| `scripts/s10plus-debug-pack/nuxel-live.sh` | Proven serial recovery launcher |
| `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` | Tri-Link launcher: serial / WLAN / USB / auto |
| `tools/beta/live/nuxel-live-ssh.py` | Transport CLI implementation |
| `tools/beta/live/nuxel_tri_link.py` | Transport adapters, discovery, guards and transfers |
| `services/nuxel-bridge/src/tri_link_status.py` | Read-only phone-side status source |
| `pwa/nuxel-apps/console/` | Shared console status UI |
| `pwa/nuxel-apps/console-wifi/` | Wi-Fi SSH app entry |
| `pwa/nuxel-apps/console-usb/` | USB SSH app entry |
| `configs/nuxel/security/ssh/` | Pinned host key, key-only SSH policy and public key |
| `docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md` | Physical test evidence and limitations |
| `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/` | USB NCM panic evidence |

---

**Serial for survival. USB for speed. WLAN for freedom. Three links, one Nuxel.**
