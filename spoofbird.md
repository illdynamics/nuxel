# Prompt: Fix PenguInterface (`org.nuxel.PenguInterface`) to Spoof Windows for Portal for Teams

> Feed this prompt to your agent (Codex / any capable coding agent). It describes the exact app, its bridge API, and what to change so **Portal for Teams** (flatpak `com.github.IsmaelMartinez.teams_for_linux`, v2.28.0) stops complaining that nuxel is a "Linux device" and instead sees us as a **Windows computer**.

---

## 1. Goal
Make **PenguInterface** (`org.nuxel.PenguInterface`) able to *spoof Windows* for the native/flatpak app launcher so **Portal for Teams** reports a **Windows** client (not Linux) during login / telemetry. The spoof must cover **more than just `/etc/os-release`**: it must also rewrite `uname`, the user-agent, and any other detection vectors that Portal for Teams (or its Electron runtime + flatpak portals) reads to decide "Linux vs Windows". Target end-state: *a Windows machine* as far as Portal for Teams can tell from inside its sandbox.

## 2. Environment / facts already gathered on `nuxel`
- Host: **Exe – "Mobile Linux for Control Freaks"**, a Linux-based mobile phone OS (phone-class SoC).
- Kernel: `Linux fedora 4.14.253-gf7194c1d15ed-dirty ... aarch64 GNU/Linux` → `uname -m = aarch64`, `uname -s = Linux`.
- `/etc/os-release` (`-> /usr/lib/os-release`) reports **Fedora Linux 43**, `ID=fedora`, `VERSION_ID=43`. Note: `/etc/os-release` is mode `0777` and symlinked, so it can be rewritten/overlaid.
- Flatpak apps installed system-wide via the nuxel flatpak repo, incl. **Portal for Teams** `com.github.IsmaelMartinez.teams_for_linux`. Other messengers present: ZapZap, Stremio, Vesktop, Ferdium, Signal Desktop, Telegram, Firefox, VLC, mpv, Text Editor, KDE/GNOME runtimes.
- Portal for Teams currently "whines" that nuxel is a Linux device → it reads OS identity from the runtime and/or flatpak portals and sees Linux.

## 3. Target app: `org.nuxel.PenguInterface` (a PWA-style native bridge app)
Location on device: `/usr/share/nuxel/pwa/nuxel-apps/penguinterface/`
Key files:
- `app.json` — manifest. `id: org.nuxel.PenguInterface`, `type: pwa`, capabilities `["system:inspect"]`, default_mode `read-only`. This is the app that owns the spoof bridge and the per-device profile.
- `profile.json` — **per-device compatibility profile** (schema `nuxel.device-profile/1`). Currently:
  - `"device": "Samsung Galaxy S10+ (SM-G975F)"`, `"codename": "beyond2lte"`, `"soc": "Exynos 9820"`, `"kernel": "4.14.253"`,
  - `"os": "Nuxel (Fedora 43 aarch64)"` → this is the human-readable OS line that currently says Linux/Fedora. **Update it to reflect Windows** where appropriate for spoofing.
- `js/spoof.js` — the **spoof panel logic**. It drives a global + per-app identity profile via:
  - `window.NuxelBridge.call('spoof', verb, params)` with verbs: `status`, `set`, `reset`, `apps`.
  - Config shape per profile: `{ enabled, scope ('global'|'app'), app_id?, ua (user-agent string), os_release (text of /etc/os-release), uname { sysname, nodename, release, version, machine } }`.
  - Scope = **global** (applies to all native app launches) or **per-app** (e.g. only `com.github.IsmaelMartinez.teams_for_linux`).
- `js/pengu.js` — renders the device-profile capabilities table from `profile.json` (validate + display).
- Native side: **`libnuxel-spoof.so`** injects the effective profile when a native app is launched; spoof status UI reports `"aarch64 libnuxel-spoof.so present"` vs `"not built/deployed"`. Confirm it exists and loads.

## 4. What to change (do all of these)
### 4.1 Add / default a **Windows** identity profile in `js/spoof.js`
- Extend the `DEFAULTS` object so the *default* spoofed `uname` looks like Windows, e.g.:
  - `sysname: 'windows_nt'`, `nodename: 'WIN-CLIENT'`, `release: '10.0'`, `version: '#1 SMP PREEMPT'`, `machine: 'amd64'`.
  - Add a **Windows user-agent** default (Chromium/Edge on Windows 10/11), e.g.:
    `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36`.
- Because Portal for Teams runs on **aarch64** here, keep a sensible machine value — you may set `machine: 'amd64'` to fully say "Windows x86_64", or add a toggle to choose `arm64` vs `amd64`. Recommend **fully Windows (`amd64`)** unless the app is picky about arch.
- Provide a ready-to-use named profile preset called **"Windows (Portal for Teams)"** that sets: uname→Windows, user-agent→Edge/Chrome-on-Windows, and an `/etc/os-release` text that reports `ID=windows` / `VERSION_ID=10` while staying internally consistent.

### 4.2 `/etc/os-release` spoofing (beyond the first line)
- The panel already accepts free-form `os_release` text via field `spoof-os-release`. Add a **Windows preset** for it, e.g.:
  ```
  NAME="Windows 10"
  ID=windows
  VERSION_ID=10
  PRETTY_NAME="Windows 10 Enterprise"
  ANSI_COLOR="0;34"
  CPE_NAME="cpe:/o:microsoft:windows:10"
  DEFAULT_HOSTNAME="WIN-CLIENT"
  ```
- Ensure the spoof writes/overlays `/etc/os-release` (it is `0777`, symlink `/etc/os-release -> ../usr/lib/os-release`) **and** the real backing file `/usr/lib/os-release`, so both the host and the flatpak runtime see Windows.

### 4.3 `uname` spoofing (the 5 fields)
- Wire the existing `uname { sysname, nodename, release, version, machine }` fields to the Windows defaults above. Make sure the native launcher (`libnuxel-spoof.so`) uses these when Portal for Teams calls `uname()` / reads `/proc/sys/kernel/` style info inside its sandbox.

### 4.4 User-agent spoofing
- Set a **Windows UA** string (field `ua`). This is often what Electron-based apps read first, so make it the primary signal and keep it consistent with uname/os-release.

### 4.5 Other detection vectors "any other means necessary"
Cover at least these additional sources so Portal for Teams cannot fall back to Linux:
- **DMI / hardware ID**: if available, spoof `sysfs`/`dmidecode` fields (`product_name`, `system-product-name`) and any Windows-y board product id the runtime checks.
- **flatpak portal telemetry** (org.freedesktop.PortalBackendFactory / xdg-desktop-portal): ensure the spoofed identity is exposed through portals, not just raw `/etc/os-release`. If a portal exposes `os-release`/`uname`, route it through the same profile.
- **hostname**: set to a Windows-style name (`WIN-CLIENT`) via `nodename` / `/etc/hostname` so `gethostname()` also reads Windows-y.
- **arch consistency**: reconcile `uname -m` (aarch64) with a Windows claim — pick amd64 for a clean "Windows PC" report, or document the tradeoff in the UI if the app validates arch against hardware.
- Keep spoofing **scoped and resettable** (existing global / per-app / reset-all semantics already exist in `spoof.js`); preserve them so the owner can target just Portal for Teams or apply globally.

### 4.6 Device profile (`profile.json`)
- Update `"os": "Nuxel (Fedora 43 aarch64)"` → e.g. `"Windows 10 (Portal for Teams spoof)"` and, where it makes sense, add a capability note like `"os_spoof": {"state": "enabled", "evidence": "PenguInterface global/portal profile"}` so the UI shows Windows is being reported.

## 5. Concrete steps to implement
1. Open `/usr/share/nuxel/pwa/nuxel-apps/penguinterface/js/spoof.js`.
2. Extend `DEFAULTS` with the **Windows** uname fields + a Windows user-agent; add a named preset `"windows-portal"`.
3. Add a helper to load/apply the Windows `/etc/os-release` text (field `spoof-os-release`) and write it to both `/etc/os-release` and `/usr/lib/os-release`.
4. Ensure `call('set', ...)` persists `ua`, `os_release`, and `uname` for **global** scope AND for app id `com.github.IsmaelMartinez.teams_for_linux` (per-app override) so Portal for Teams always gets Windows even if global is off.
5. Verify `libnuxel-spoof.so` is present (`aarch64`) and that the launcher injects the profile at native launch; if it needs a rebuild to pick up new fields, note that in the UI (it already reports "present"/"not built").
6. In `profile.json`, set `"os"` to reflect Windows for the spoofed view (keep real data recoverable).
7. Rebuild/redeploy PenguInterface so the flatpak/PWA bundle reflects changes (`org.nuxel.PenguInterface` lives under `/var/lib/nuxel/live-deploy/rollback-*/usr/share/nuxel/pwa/nuxel-apps/`).

## 6. Verification (run on nuxel, as root)
```bash
# 1. Confirm PenguInterface + Portal for Teams present
flatpak list | grep -iE 'Pengu|teams'

# 2. Apply Windows spoof globally (or per app com.github.IsmaelMartinez.teams_for_linux) via the bridge:
#    window.NuxelBridge.call('set', { scope:'global', enabled:true, ua:'<Windows UA>', os_release:'<Windows os-release text>', uname:{sysname:'windows_nt',nodename:'WIN-CLIENT',release:'10.0',version:'#1 SMP PREEMPT',machine:'amd64'} })

# 3. Check effective identity
cat /etc/os-release; echo '---'; cat /usr/lib/os-release

# 4. Inside Portal for Teams' flatpak runtime, check uname/os-release as it sees them:
flatpak run --command=uname com.github.IsmaelMartinez.teams_for_linux -a
flatpak run --command=sh  com.github.IsmaelMartinez.teams_for_linux -c 'cat /etc/os-release; echo ---; uname -m'

# 5. Reopen Portal for Teams and confirm the "Linux device" warning is gone / it reports Windows.
```

## 7. Acceptance criteria
- Portal for Teams reads **Windows** from `/etc/os-release`, `uname`, user-agent, (and DMI/portal where applicable) — not Linux.
- Spoof is applied via PenguInterface's existing bridge (`spoof` verb), scoped global or per-app, and resettable.
- No leftover fallback to Fedora/Linux in the vectors above; arch reported consistently with a Windows claim.
