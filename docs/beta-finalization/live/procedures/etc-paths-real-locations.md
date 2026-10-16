# Procedure — where the staged `/etc/nuxel` documents are really read from

`configs/nuxel-remaining` installs every remaining `configs/nuxel/**` document and
unit file, using the path its **shipped consumer actually reads** rather than a
guess. Two classes of document need a second, documented step:

1. **Canonical paths outside the plan's userspace roots.** The plan's guard
   confines writes to a userspace whitelist (`/etc/nuxel`, `/etc/systemd`,
   `/etc/dbus-1/system.d`, `/usr/lib/nuxel`, `/usr/libexec/nuxel`, `/usr/bin`,
   `/usr/local`, `/usr/share/nuxel`, `/var/lib/nuxel`, `/home/nuxel/nuxel`, …).
   A document whose real consumer path is `/etc/NetworkManager/…`,
   `/etc/nftables/…`, `/etc/tor/…`, `/opt/nuxel/sandbox` or `/etc/udev/rules.d`
   is staged at the plan's path **and** copied here, hash-verified.
2. **Device-node / firmware-adjacent documents.** `configs/nuxel/modem/**` is
   deliberately not in the plan at all (see
   [modem-and-storage-mirror.md](modem-and-storage-mirror.md)).

| Repository source | Plan target (staged) | Canonical consumer path | Copy needed? |
|---|---|---|---|
| `configs/nuxel/paths.conf` | `/etc/nuxel/paths.conf` | same | no |
| `configs/nuxel/statusbar-safezones.json` | `/etc/nuxel/display/statusbar-safezones.json` | same (`nuxelctl ZONES_FILE`) | no |
| `configs/nuxel/buttons.json` | `/etc/nuxel/input/buttons.json` | same (`nuxelctl BUTTONS_FILE`, rootfs builder) | no |
| `configs/nuxel/input/button-fsm.json` | `/etc/nuxel/input/button-fsm.json` | same (`nuxelctl FSM_SPEC`) | no |
| `configs/nuxel/time/time.json`, `nuxel-chrony.conf` | `/etc/nuxel/time/…` | same (`nuxel-time.sh`) | no |
| `configs/nuxel/time/60-nuxel-timesyncd.conf` | `/etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf` | same | no |
| `configs/nuxel/keyboard/keyboard*.json`, `nuxel-keyboard-apply.{service,path}` | `/etc/nuxel/keyboard/…`, `/etc/systemd/system/…` | same (`nuxel-keyboard-apply.sh`) | no |
| `configs/nuxel/bootmode/bootmode-guard.json` | `/etc/nuxel/bootmode/bootmode-guard.json` | same (`nuxel-bootmode-guard.py` search order) | no |
| `configs/nuxel/{bluetooth,camera,gnss,haptics,leds,nfc,power,sensors,security,capabilities}/…` | `/etc/nuxel/<same subpath>` | same (the a33 diagnostics and the bridge read `/etc/nuxel/**`) | no |
| `configs/nuxel/haptics/nuxel-haptics-bridge.service`, `power/nuxel-power-mode.service`, `time/nuxel-rtc-check.{service,timer}`, `touch/nuxel-bootmode-reboot.service`, `keyboard/nuxel-keyboard-apply.{service,path}` | `/etc/systemd/system/…` | same | no |
| `configs/nuxel/security/tor/torrc` | `/etc/nuxel/security/tor/torrc` | **`/etc/tor/torrc`** | yes — step 1 below |
| `configs/nuxel/modem/microsd.json` | *not staged* (guard) | `/etc/nuxel/modem/microsd.json` | yes — see the modem procedure |
| `configs/nuxel/modem/90-nuxel-microsd.rules` | *not staged* (guard) | `/etc/udev/rules.d/90-nuxel-microsd.rules` | convention: udev rules are installed by the image builder, and the microSD automount window is a boot-order property; a live write would change device naming under a running udev |

## 1. The tor configuration (canonical `/etc/tor/torrc`)

```sh
# the plan staged it at /etc/nuxel/security/tor/torrc
sha256sum /etc/nuxel/security/tor/torrc
install -d /etc/tor
cp -a /etc/tor/torrc /etc/tor/torrc.nuxel-rollback 2>/dev/null || true
install -m 0644 /etc/nuxel/security/tor/torrc /etc/tor/torrc
sha256sum /etc/tor/torrc                 # must equal the staged hash
systemctl reload tor 2>/dev/null || systemctl restart tor 2>/dev/null || \
  echo "tor is not installed on this image - the copy is staged, the consumer is absent"
```

`tor` is **not** in the resolved package set, so on today's handset this step ends
with the consumer absent, and the Tor/VPN feature's verdict is
`BLOCKED_EXTERNAL_RESOURCE` (the package is the missing external resource) — not a
silent "configured".

## 2. NetworkManager, nftables and phoc documents

The NetworkManager/nftables/phoc documents that live **outside** `configs/nuxel/`
(`configs/networkmanager/**`, `configs/nftables/**`, `tools/s10plus/a29/phoc-phone.ini`)
belong to the connectivity and security groups' files; where this plan does stage a
document those groups' consumers read from `/etc/nuxel/**`, no copy is needed. If a
future revision moves one of them to `/etc/NetworkManager/conf.d/` or
`/etc/nftables/`, the rule is the same as §1: preserve, copy, verify, reload the
one affected unit, and record the previous hash in `DEPLOYMENTS.md`.

## 3. The sandbox profile tree

`shell/nuxel-shell/nuxel-sandbox/profiles/*.json` is staged to
`/etc/nuxel/sandbox/profiles/`. The sandbox runtime's canonical directory is
`NUXEL_SANDBOX_DIR` (`/opt/nuxel/sandbox`, resolved from `/etc/nuxel/paths.conf`),
which is outside the plan's userspace roots because that tree belongs to the image
staging step (`images/s10plus/build-phone-rootfs-inside-fedora.sh`). To make the
profiles effective:

```sh
install -d /opt/nuxel/sandbox/profiles
cp -a /opt/nuxel/sandbox/profiles /opt/nuxel/sandbox/profiles.nuxel-rollback 2>/dev/null || true
cp -a /etc/nuxel/sandbox/profiles/. /opt/nuxel/sandbox/profiles/
for f in /etc/nuxel/sandbox/profiles/*.json; do
  a=$(sha256sum "$f" | cut -d' ' -f1); b=$(sha256sum "/opt/nuxel/sandbox/profiles/${f##*/}" | cut -d' ' -f1)
  [ "$a" = "$b" ] || { echo "HASH_MISMATCH $f"; exit 1; }
done
```

There is no service to restart: `nuxel-sandbox` reads a profile when it starts an
application, so the next sandboxed launch consumes the new bytes. That is the
deliberate reload for these files, and it is stated here rather than implied.

## 4. Verdicts and limits

* Every copy in this procedure leaves the item at `DEPLOYED_UNVERIFIED` until the
  consumer is observed. A copied file is not a working configuration.
* Nothing here writes a device node, a partition, the BOOT container or the
  kernel; no `udev` rule is installed live.
* If a canonical path cannot be written (read-only mount, missing directory
  created by another package), say so and keep the document staged — never
  rewrite the plan's guard to reach it.
