# Nuxel keyboard — native virtual keyboard + physical keyboard (mission area 29)

Owner build group: **bg-06-core-phone-apps** (`briq-06d-settings-and-keyboard`).
Device: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64, kernel 4.14.253.
Rule this directory obeys: **do not invent a fake DOM-only keyboard** and **never
claim a keyboard works because a config file exists**.

## 1. What is actually installed (inspected, not assumed)

| Layer | What the repository/target really contains | Path of record |
| --- | --- | --- |
| OSK provider (phone rootfs) | `stevia-0.54.0-1.fc43.aarch64` + `stevia-phosh-osk-provider-0.54.0-1.fc43.noarch` — the phosh on-screen keyboard provider | `images/s10plus/packages-manifest.json` (group `session`) |
| OSK provider (UTM VM image) | the VM configuration script writes `~/.config/squeekboard/config.ini` with `layout=phone` | `artifacts/vm/nuxel-aarch64.utm/scripts/phosh-phone-resolution.sh` (`configure_squeekboard`) |
| Wayland compositor | `phoc` (wlroots-based), reached from the launcher host through the Wayland↔framebuffer bridge | `docs/architecture.md`, `tools/s10plus/a33/nuxel-wl-fb.c` |
| Text input protocol | `zwp_text_input_manager_v3` — the compositor raises/hides the OSK itself when a client focuses/clears a text field | `docs/architecture.md`, this directory |
| Launcher surface | Nuxel Home PWA in WebKitGTK; `window.NuxelHost` is the only IPC the pages get | `pwa/nuxel-home/js/host-bridge.js`, `tools/s10plus/a33/nuxel-pwa-host.c` |
| Settings document | `/etc/nuxel/keyboard/keyboard.json` (this directory) | `pwa/nuxel-apps/settings/settings-model.js` → `DOCS.keyboard` |
| Applier (the real consumer) | `tools/s10plus/a33/nuxel-keyboard-apply.sh` | same |
| Evidence probe | `keyboard-state` → `/run/nuxel-keyboard.state` | `tools/s10plus/a33/nuxel-pwa-host.c` (`CFG[]` status channels) |

`stevia` is the provider the **phone** ships; `squeekboard` is what the **VM** script
configures. The applier therefore probes for both, configures the one that is
present, and reports `NO_OSK_INSTALLED` when neither is — it never silently
succeeds.

### Why there is no "raise keyboard" IPC

WebKitGTK is a Wayland client: when a field is focused it issues
`zwp_text_input_v3.enable`, and `phoc` asks the registered OSK provider
(`stevia-phosh-osk-provider`) to show. That is the protocol path the mission asks
for ("use Wayland text-input protocols where supported"), it needs no privileged
helper in our pages, and it is why `nuxel-pwa-host` exposes **no** `osk-show`
verb: adding one would be a second, non-standard path that bypasses the
compositor's own arbitration of who owns the keyboard.

## 2. What each setting maps to

| Setting (Settings → Input) | Real component it drives | Applied through | If the mechanism is absent |
| --- | --- | --- | --- |
| `keyboard.enabled` | the OSK provider's enable switch | `gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled <bool>` (the key phosh's OSK manager watches) + squeekboard `config.ini` | recorded as `not_applied:no-mechanism`, never shown as "on" |
| `keyboard.auto_show` | OSK auto-raise on focus | same key pair (`screen-keyboard-enabled` false ⇒ manual-only) | same |
| `keyboard.layout` | compositor input source + OSK layout | `gsettings set org.gnome.desktop.input-sources sources "[('xkb','<layout>')]"`; squeekboard `config.ini` `layout=` | `not_applied:provider-managed` if the provider has no layout knob |
| `keyboard.numeric_layout` | numeric key view for number fields | OSK provider layout selection (`stevia` ships a numeric view; squeekboard picks it from the field's `inputmode`) | `not_applied:provider-managed` |
| `keyboard.height_dp` | OSK height | squeekboard `config.ini` / layout key sizing; `stevia` 0.54 sizes from its own theme | recorded, reported `not_applied:provider-managed` — a value the stack cannot honour is reported, not faked |
| `keyboard.key_repeat` (+ delay/interval) | GTK/WebKitGTK key repeat, including OSK backspace repeat | `org.gnome.desktop.peripherals.keyboard repeat`, `repeat-interval`, `delay` | `not_applied:no-mechanism` |
| `keyboard.haptics` | per-key haptic feedback | delegated to the haptics component (`configs/nuxel/haptics/haptics.json`, owner bg-08); the applier only records the delegation | reported as `delegated` |
| `keyboard.clipboard` | OSK clipboard bar / GTK clipboard | squeekboard `config.ini` `show-clipboard-button`; GTK clipboard otherwise | `not_applied:provider-managed` |
| `keyboard.hardware_passthrough` | physical USB/Bluetooth keyboard | presence is **probed** (`/sys/class/input`, `/dev/input/by-path/*kbd*`, `libinput list-devices`); the OSK never grabs the device, so passthrough needs no grant | reported `hardware_keyboard=present|absent` |

Everything above is written by the **same applier** whether the change comes from
the Settings UI (`NuxelHost.configSet`) or from `nuxelctl` — one settings system,
not a UI path plus a console path.

## 3. Evidence — how you know it is not cosmetic

1. `nuxel-keyboard-apply.sh apply` writes `/run/nuxel-keyboard.state`: one
   `key=value` line per setting with `applied` / `not_applied:<reason>` /
   `delegated` / `provider-managed`, plus the probed stack
   (`osk=stevia|squeekboard|none`, `compositor=`, `text_input=`, `hardware_keyboard=`).
2. The Settings app reads that file through the launcher host status channel
   `keyboard-state`, so the UI shows the *application verdict*, not the wish.
3. `tools/s10plus/a33/keyboard-probe.html` is the last hop: it logs real
   `keydown`/`beforeinput`/`input` events with `isTrusted`, and it labels any
   script-synthesised delivery `[synthetic]` so a test harness can never be
   mistaken for a human pressing keys on an OSK. Open it in the VM/phone
   WebKitGTK surface, focus the text field, press keys **on the on-screen
   keyboard** and read the evidence line.
4. `tools/s10plus/a33/tests/test-virtual-keyboard.py` runs the offline half:
   schema ↔ Settings model ↔ shipped document consistency, the applier's
   `selftest` (including every degradation path against a fake root), the host
   status channel, and a jsdom execution of the probe page that asserts a
   synthetic delivery is labelled synthetic.

Verdict ladder for this feature: **OFFLINE_TESTED** (offline tests green) →
**VERIFIED_IN_VM_ONLY** (probe page run in the UTM VM with a real OSK) →
**VERIFIED_ON_S10PLUS** (owner proof, area 29 of
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`). No offline test can
promote this to `VERIFIED_ON_S10PLUS`.

## 4. Install (on the target, by the deployment path — never from this repo directly)

```sh
install -Dm644 configs/nuxel/keyboard/keyboard.json        /etc/nuxel/keyboard/keyboard.json
install -Dm644 configs/nuxel/keyboard/keyboard.schema.json /usr/share/nuxel/schemas/keyboard.schema.json
install -Dm755 tools/s10plus/a33/nuxel-keyboard-apply.sh   /usr/libexec/nuxel/nuxel-keyboard-apply
install -Dm644 configs/nuxel/keyboard/nuxel-keyboard-apply.service /usr/lib/systemd/user/nuxel-keyboard-apply.service
install -Dm644 configs/nuxel/keyboard/nuxel-keyboard-apply.path    /usr/lib/systemd/user/nuxel-keyboard-apply.path
systemctl --user enable --now nuxel-keyboard-apply.path
```

`nuxel-keyboard-apply.sh --selftest` and `--dry-run` are safe to run on the
device and on a workstation: they touch only a temporary fake root. The applier
never writes a block device, never touches a partition, never enters Recovery or
Download Mode — see the NO-FLASHING invariant in
`docs/beta-finalization/BASELINE-PROTECTION.md`.

## 5. Manual proof (owner, area 29)

`docs/beta-finalization/manual-proof/20-applications.md` §"Virtual keyboard" and
§"Settings → Input" carry the exact steps, expected result, failure symptoms and
diagnostic commands. In short: open Settings → Input, tap the probe page link or
type in Files' search box, confirm the keyboard rises on focus and hides on
blur, then press keys **with a finger** and confirm the characters appear.
