# Procedure — the modem / microSD documents the plan deliberately refuses

## Why these files are not in the deploy plan

`tools/beta/live/deploy-manifest.json` refuses any target whose path segments
match the flash-adjacent family

```
modem | radio | efs | sec_efs | persist | calibration | imei | pit | param | nvdata
```

(see `FORBIDDEN_PATH_PATTERNS` in `tools/beta/live/nuxel_live.py`). The pattern is
deliberately **over-broad**: it cannot tell a modem NV item from a JSON document
whose directory happens to be called `modem`, and the mission's hard rule is that
no path in that family may ever be written by this tooling. Loosening the guard to
let `/etc/nuxel/modem/*.json` through would also let a mistake through, so the
guard stays as it is and these userspace documents are installed by hand, with the
same hash discipline.

Affected repository files (`configs/nuxel/modem/`):

| File | Canonical consumer path | Consumer |
|---|---|---|
| `modem.json` | `/etc/nuxel/modem/modem.json` | `tools/s10plus/a33/nuxel-modem-diag.sh`, the Settings "About phone" surface |
| `microsd.json` | `/etc/nuxel/modem/microsd.json` | `tools/s10plus/a33/nuxel-microsd-diag.sh` |
| `90-nuxel-microsd.rules` | `/etc/udev/rules.d/90-nuxel-microsd.rules` | `udev` (device naming / automount window) |
| `README.md` | `/etc/nuxel/modem/README.md` | documentation |
| `nuxel-microsd-automount.service` | `/etc/systemd/system/nuxel-microsd-automount.service` | **this one IS in the plan** (its target path contains no forbidden segment) |
| `tools/s10plus/a33/nuxel-modem-diag.sh` | `/usr/local/bin/nuxel-modem-diag.sh` | `nuxelctl` sibling lookup — refused for the same reason |

## The install (read-only source, hash-verified, no device node written)

```sh
# 1. verify the source bytes in the repository first (this is the artefact identity)
sha256sum configs/nuxel/modem/modem.json configs/nuxel/modem/microsd.json

# 2. stage and install, preserving whatever is there today
install -d /etc/nuxel/modem
for f in modem.json microsd.json; do
  t=/etc/nuxel/modem/$f
  [ -e "$t" ] && cp -a "$t" "$t.nuxel-rollback"
  install -m 0644 "var/tmp/nuxel-stage/configs/nuxel/modem/$f" "$t.new"   # pushed by the console tool
  mv -f "$t.new" "$t"                                                     # atomic rename
  sha256sum "$t"
done

# 3. the diagnostic tool, next to nuxelctl so its sibling lookup finds it
install -m 0755 /var/tmp/nuxel-stage/tools/s10plus/a33/nuxel-modem-diag.sh \
    /usr/local/bin/nuxel-modem-diag.sh
sha256sum /usr/local/bin/nuxel-modem-diag.sh

# 4. behaviour: the shipped tool must now find its document and answer honestly
/usr/local/bin/nuxel-modem-diag.sh status           # capability report, or a named absence
```

Rollback is the same route the plan uses:

```sh
for f in modem.json microsd.json; do
  t=/etc/nuxel/modem/$f; [ -e "$t.nuxel-rollback" ] && cp -a "$t.nuxel-rollback" "$t"
done
```

## udev rules — staged, not live-installed

`90-nuxel-microsd.rules` is **not** copied onto a running system by this
procedure. Renaming device nodes under a live `udev` on a phone whose console is
the only way back in is a self-inflicted outage, and the microSD automount window
is a boot-order property of the image (`images/s10plus/build-phone-rootfs-*`).
If the owner wants the rule active, the place for it is the image build, and the
change is then covered by a BOOT/rootfs update — i.e. outside this mission's
userspace plan. Terminal state: `IMPLEMENTED_NOT_DEPLOYED` for the rule, with this
paragraph as the reason.

## Hardware honesty

Nothing in this procedure proves the modem, the SIM slot or the microSD reader
works. A registered kernel driver is not proof that the hardware works, and a
staged JSON document is not proof that anything reads it. The on-device verdicts
for the modem (+SIM), the microSD slot and the storage stack belong to the live
hardware-subsystem captures; the tools that produce them are
`nuxel-modem-diag.sh`, `nuxel-microsd-diag.sh` and `nuxelctl`, and their output is
the evidence — not this file. Never write to `EFS`, `SEC_EFS`, the calibration
area, the IMEI, the PIT or any partition, and never flash a modem image.
