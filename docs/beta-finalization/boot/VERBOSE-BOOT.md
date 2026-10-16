# Verbose boot: a durable Settings option, its boot-time consumer, and the honest
# Bixby-hold override (area 3 – display/boot, briq-02b)

Scope: Samsung Galaxy S10+ **SM-G975F / beyond2lte**, Fedora 43 ARM64 userspace,
Linux 4.14.253, systemd PID 1.

Access tier: **repository-only implementation** with a persisted setting and a
boot-time consumer, plus a **one-time Bixby hold override** that the installed
early boot stage cannot support today.

**Terminal states for this area**

| Item | State |
|---|---|
| Durable setting document + migration + upgrade-safety | `OFFLINE_TESTED` |
| Settings UI path (Quick Settings tile + Settings app) | `OFFLINE_TESTED` |
| Console path (`nuxelctl verbose-boot status\|on\|off`) | `OFFLINE_TESTED` |
| Boot-time consumer (early userspace stage, systemd unit) | `OFFLINE_TESTED` |
| An actual verbose boot seen on the glass | `NEEDS_OWNER_TEST` |
| One-time **Bixby hold** override | `BLOCKED_KERNEL` / **`BOOT_UPDATE_REQUIRED`** (see §5) |

No claim in this document is `VERIFIED_ON_S10PLUS`.

---

## 1. What "verbose boot" means here

There are two different things a user could call "verbose boot", and only one of
them is reachable without flashing:

1. **Kernel command line** (`nuxel.verbose_boot=1`, `console=ttyGS0`, loglevel).
   This lives in the **BOOT partition**. Changing it needs a boot-image write,
   which this mission forbids. It is therefore **not** implemented and the tooling
   says so (see §5).
2. **Nuxel's own boot surface** — the thing the user actually sees: a boot log on
   the panel + a shortened boot animation so the log is visible as early as
   possible, instead of a full 8 s animation. **This is what the setting
   controls**, and it is entirely userspace: no BOOT/USERDATA/DTB write.

The setting is deliberately honest about that boundary: enabling it never claims
to have changed the kernel command line.

## 2. Storage contract: durable, migratable, never clobbered

| Item | Value |
|---|---|
| Durable document | `/etc/nuxel/boot/verbose-boot.json` (shipped default: `configs/nuxel/boot/verbose-boot.json`) |
| Schema | `schema_version: 1`, `verbose_boot: bool`, `set_by`, `updated_at`, `migrated_from` |
| Written by | Nuxel Settings / Quick Settings (via `NuxelHost.configSet('verbose-boot')`) and `nuxelctl verbose-boot on\|off` — **the same file, atomically** (same-directory `rename`) |
| Legacy locations migrated once | `/etc/nuxel/verbose-boot`, `/var/lib/nuxel/verbose-boot.legacy`, `/var/lib/nuxel/verbose-boot`; plus the old launcher localStorage flags `nuxel.verboseBoot`, `nuxel.verbose_boot`, `nuxel.settings.verboseBoot` |
| Upgrade rule | the image installs the shipped default with the **`keep`** rule (existing file wins), and every write **merges** into the loaded document, so keys a newer/older revision does not know about are preserved. An unreadable document is reported and **never overwritten** |
| Runtime state it publishes | `/run/nuxel/verbose-boot` (K=V), `/run/nuxel/anim-skip.request`, `/var/lib/nuxel/verbose-boot` (durable record), `/var/log/nuxel/boot-stage.log`, kernel marker `NUXEL_VERBOSE_BOOT=…` |

## 3. Boot-time consumer

`nuxel-verbose-boot.service` (installed from
`tools/s10plus/a33/nuxel-verbose-boot.service`) runs
`/usr/libexec/nuxel/nuxel-verbose-boot`
(`tools/s10plus/a33/nuxel-verbose-boot.py`) in the **early userspace** stage:

* `DefaultDependencies=no`, `After=local-fs.target systemd-journald.socket`,
  `Before=nuxel-wl-fb.service nuxel-pwa-host.service nuxel-wayland.service`,
  `WantedBy=sysinit.target`;
* `SuccessExitStatus=0 1` — a failure here must never stop a boot;
* it touches **no framebuffer memory**: it decides, records and publishes, which
  keeps the single-owner rule from `ANIMATION-HANDOFF.md` intact. The display
  bridge and the launcher read the state it publishes.

Read by:

| Consumer | Uses |
|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` (bridge) | `/run/nuxel/verbose-boot`, `/run/nuxel/anim-skip.request` before the handoff ⇒ **deliberately waives the minimum-cycle floor** so the boot log is on the glass as early as possible. The verdict comes from decision 5 of the shared handoff table; the bridge emits `ANIM_MIN_CYCLE_SKIPPED`, writes `ANIM_MIN_CYCLE_SKIPPED` to `/var/lib/nuxel/anim-min-cycle.completed`, and the receipt records `reason=verbose_boot_requested` with **`terminal=0`** — a user choice is never reported as a completed animation cycle |
| `nuxel-pwa-host` + `pwa/nuxel-home/js/bootlog.js` | the boot-log overlay in the launcher (same boot) |
| `nuxelctl verbose-boot status` | printed effective state, source and override capability |

Effective-state resolution order (first match wins, and the source is recorded):
`bixby_hold_once` → `cmdline` → `config` → `default`.

## 4. The UI and console paths cannot diverge

| Surface | File | Notes |
|---|---|---|
| Quick Settings tile | `pwa/nuxel-home/js/qs.js` | "Verbose boot" tile, created dynamically, synced from the store; toggling writes the same document |
| Settings app | `pwa/nuxel-apps/settings/` (Developer → **Boot** card) | A real toggle (`#verbose-boot-toggle`) that writes the same document through the host (`configSet('verbose-boot')`), **merges** into the loaded JSON (so unknown keys survive), sets `set_by=user`/`updated_at`, shows the durable state + `this boot:` line from `/run/nuxel/verbose-boot`, and states the override capability verbatim. If the write fails the switch flips back — the UI never claims a setting it did not store |
| Settings store | `pwa/nuxel-home/js/settings-store.js` | DOM-free, unit-tested store: one document per setting name, merge-on-write, migration, host→localStorage degradation |
| Console | `tools/s10plus/a33/nuxelctl` | `verbose-boot status`, `on`, `off`, `override` |
| Offline gate | `tools/s10plus/a33/tests/run-boot-tests.sh` | runs this harness (plus the handoff, colour, launcher and safe-zone legs) as one command, headless and rootless |
| Owner procedure | `docs/beta-finalization/manual-proof/03-display-boot.md` | area 3 step 5: enable it, reboot once, watch the boot log appear, disable it again |
| Launcher manifest | `pwa/nuxel-home/manifest.json` | `nuxel.settings_documents` lists `/etc/nuxel/boot/verbose-boot.json` |

## 5. The one-time Bixby-hold override — implemented, NOT deployed

Requirement: holding **Bixby during the early boot stage** turns verbose boot on
for **that boot only** (a recovery aid).

* The early boot stage half is written (`tools/s10plus/a33/nuxel-boot-stage-verbose.sh`):
  it discovers the `gpio_keys` input node **by name** (never a hard-coded
  `eventN`, the same rule the touch pipeline uses), checks that the Bixby key
  (keycode 703) is held for `NUXEL_BIXBY_HOLD_MS` (default 1200 ms), then drops
  `/run/nuxel/boot-verbose-once` and publishes
  `bixby-hold-override=1` in `/run/nuxel/boot-stage-capabilities`.
* **It is not installed.** That fragment belongs in the initramfs inside the
  **BOOT partition** (insertion point documented: `boot/initramfs/init.sh`, just
  before the `nuxel_start_animation` call). Installing it requires a BOOT
  partition write, which this mission forbids.
* The userspace consumer therefore honours the override **only** when the stage
  proves it can produce it (`bixby-hold-override=1` present). On the installed
  A23 initramfs it reports:

```
OVERRIDE_CAPABILITY=BOOT_UPDATE_REQUIRED
OVERRIDE_REASON=the installed early boot stage does not publish bixby-hold-override=1
                (it cannot read the Bixby key state); enabling the one-time override
                requires a BOOT partition update, which this mission forbids (no flashing)
NUXEL_VERBOSE_BOOT_OVERRIDE_REFUSED reason=BOOT_UPDATE_REQUIRED
```

There is **no cosmetic switch** for this: a request that cannot be honoured is
refused with a kernel marker, and the shipped config records the status as
`BOOT_UPDATE_REQUIRED` in `bixby_hold_override.status`. When a future BOOT update
installs the fragment, the same code path starts honouring it with no change.

Starting from the repository:
`bash tools/s10plus/a33/nuxel-boot-stage-verbose.sh` is the fragment; a future
BOOT update must add `nuxel-key-hold` (a small helper that returns 0 when the key
is held for the requested duration) to the initramfs.

## 6. Tests (offline)

```sh
python3 tools/s10plus/a33/nuxel-verbose-boot.py --selftest   # the acceptance harness
python3 tools/s10plus/a33/nuxel-verbose-boot.py --status
node      tools/s10plus/a33/tests/settings-store-test.js     # the store contract
NUXEL_ROOT=/tmp/fake nuxelctl verbose-boot on|off|status     # the console path
```

### 6.1 The acceptance harness: does the setting survive an upgrade?

`nuxel-verbose-boot.py --selftest` runs the **real** consumer and the **real**
decision code against fake roots (`/etc`, `/run`, `/var`, `/proc` under a tmpdir) —
no phone, no systemd, no `/etc` write on this host:

| Scenario | Assertion | Result |
|---|---|---|
| shipped default | `verbose_boot=false`; override recorded as `BOOT_UPDATE_REQUIRED` (not faked) | PASS |
| fresh install | `EFFECTIVE=0`, no `anim-skip.request`, durable record written, capability reported | PASS |
| user turns it ON | `EFFECTIVE=1 SOURCE=config`, `ANIM_HANDOFF=skip-animation`, boot log seeded | PASS |
| **rootfs/package upgrade** | the installer's **`keep`** rule leaves the user's `verbose_boot=true` (and `set_by=user`) intact; the next boot is still verbose | PASS |
| negative control | a *plain overwrite* of the shipped default **would** lose the setting (proves the test is load-bearing) | PASS |
| legacy location | one migration into the durable document, value preserved, `migrated_from` recorded | PASS |
| unreadable document | boot still succeeds (exit 0), file left byte-identical, reported `CONFIG_SOURCE=unreadable` | PASS |
| Bixby hold, stage cannot | `ONCE_REQUESTED=1`, `ONCE=0`, boot stays non-verbose (refused, not faked) | PASS |
| Bixby hold, stage can | `EFFECTIVE=1 SOURCE=bixby_hold_once`, **nothing persisted**, request consumed so a second start in the same boot is normal again | PASS |

Result: **`verbose-boot offline harness passed (upgrade-safe, offline)`** — 29 checks, 0 failures.

### 6.2 The store contract (`settings-store-test.js`)

31 checks, 0 failures: default OFF, one host name (`verbose-boot`), persistence and
round-trip, merge-on-write preserving an unknown key, legacy-flag migration marked
`set_by=migrated` and **not** overriding a user decision, host transport
(`configGet`/`configSet('verbose-boot')`), and cross-checks that the boot consumer,
the launcher manifest, the Quick Settings tile **and the Settings app's Boot card**
all use the same document (including that the app merges rather than replaces, and
reverts its switch when a write fails).

## 7. Owner test (deferred; recorded in the manual proof checklist, area 3)

```sh
nuxelctl verbose-boot on ; cat /etc/nuxel/boot/verbose-boot.json
# reboot normally (the phone must return to Nuxel), then:
cat /run/nuxel/verbose-boot
dmesg | grep NUXEL_VERBOSE_BOOT
```
Expected: next boot shows Nuxel's boot log early and a shortened animation; the
document still says `"verbose_boot": true` after the reboot. Then
`nuxelctl verbose-boot off` and reboot again: the full animation returns.

Failure symptoms: the document reverts to `false` after a reboot/upgrade (the
`keep` rule or a merge was broken); `/run/nuxel/verbose-boot` absent (the unit did
not run — `systemctl status nuxel-verbose-boot`).

## 8. Rollback

Repository-only. `git revert` the commit(s) touching
`tools/s10plus/a33/nuxel-verbose-boot.py`,
`tools/s10plus/a33/nuxel-verbose-boot.service`,
`tools/s10plus/a33/nuxel-boot-stage-verbose.sh`,
`configs/nuxel/boot/verbose-boot.json`, `pwa/nuxel-home/js/qs.js`,
`pwa/nuxel-home/js/settings-store.js`. On the device: `systemctl disable
nuxel-verbose-boot.service` restores the previous behaviour immediately (the
setting document is inert without its consumer), and the `/etc/nuxel/boot/`
document may be left in place — nothing else reads it. No boot/USERDATA/DTB write
is involved at any point — **no flashing of any kind**.
