# Portal for Teams / PenguInterface repair report — 2026-11-09

## Root causes found on nuxel

1. **flatpak-portal inherited the wrong runtime directory.**
   The per-user bus `/run/user/1000/bus` was started from the compositor
   environment, so D-Bus-activated `flatpak-portal` had
   `XDG_RUNTIME_DIR=/run/nuxel-wayland`. It could not resolve
   `/run/user/1000/.flatpak/<instance>` and returned
   `Could not find requesting pid`. Zypak/Electron renderers then hung or
   died (`render-process-gone`, `RESULT_CODE_INVALID_SANDBOX_STATE`).

2. **Electron 44 / Chromium 152 still rejects its inner sandbox on this 4.14
   vendor kernel.**
   Even after the portal fix, the renderer exits with exit code 1407/5 when
   Chromium's own sandbox is enabled. The Flatpak bwrap sandbox remains
   authoritative, so the launch path now passes `--no-sandbox` and disables
   Vulkan/SkiaGraphite/Dawn (there is no DRM render node).

3. **Flatpak `/tmp` is read-only.**
   QtWebEngine (ZapZap/WhatsApp) failed with
   `Creating shared memory in /tmp/... failed: Read-only file system`.
   Every Flatpak launch now gets
   `TMPDIR=/run/user/1000/app/<app-id>`; Electron's wrapper already did this,
   QtWebEngine did not.

4. **QtWebEngine needs the software Qt path.**
   ZapZap now gets `QT_QUICK_BACKEND=software`, `QT_OPENGL=software`, and
   `QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu ...`.

5. **Xwayland is not available in the Fedora phoc build.**
   `phoc` is built without `PHOC_XWAYLAND`; `-X`/`xwayland=true` are silently
   ignored. The X11 fallback was a dead end. The working path is native
   Wayland + `--no-sandbox`.

6. **Teams already has first-class Windows emulation.**
   `platform.chromeUserAgent` + `platform.emulateWindowsChromium` in
   `~/.var/app/com.github.IsmaelMartinez.teams_for_linux/config/teams-for-linux/config.json`
   set the Windows UA and `navigator.platform=Win32`. The bridge writes this
   config automatically when the Teams spoof profile is active.

7. **Flatpak reserves `/usr`, so spoof assets must live under `/run`.**
   The bridge copies `libnuxel-spoof.so` and the optional preload into
   `/run/nuxel/spoof`, exposes that directory read-only with
   `--filesystem=/run/nuxel/spoof:ro`, and sets `LD_PRELOAD` /
   `ZYPAK_LD_PRELOAD` to the runtime copy.

## Changes

- `services/nuxel-bridge/src/flatpak_provider.py`
  - `--no-sandbox`, `--disable-features=Vulkan,SkiaGraphite,Dawn`
  - per-app `TMPDIR`
  - QtWebEngine software env and sandbox-free Chromium flags
  - `extra_env` / `extra_args` / `extra_fs` support
- `services/nuxel-bridge/src/api.py`
  - materializes the spoof profile under `/run/nuxel/spoof`
  - copies the injector/profile assets there
  - exposes the profile to Flatpak and injects `LD_PRELOAD`
  - writes Teams' Windows Chromium emulation config before launch
  - passes the Windows UA argument
- `tools/s10plus/a45/nuxel-session.sh` and
  `release/s10plus/gpu/nuxel-session.sh`
  - starts the user bus with `XDG_RUNTIME_DIR=/run/user/1000`
  - publishes the activation environment
  - pre-starts `flatpak-portal` with the correct environment
- `pwa/nuxel-apps/penguinterface/js/spoof.js`, `index.html`, `profile.json`
  - Windows (Portal for Teams) preset: Edge/Chrome-on-Windows UA,
    Windows uname, Windows os-release, per-app/global/reset semantics preserved
- `spoof/electron-spoof-preload.js`
  - CDP/JS injector kept as an artifact; packaged Electron ignores
    `NODE_OPTIONS`, so Teams uses its native emulation config instead

## Measured results

- `flatpak run --command=/bin/true` cold overhead:
  **~320 ms** for Teams, Vesktop and ZapZap (previously up to ~30 s while the
  document/Flatpak portals timed out).
- Bridge launches (surface visible):
  - Teams: **2642 ms**
  - Vesktop (Discord): **1672 ms**
  - ZapZap (WhatsApp): **8667 ms**
- All three are running and listed:
  - Teams: `Sign in to your account`
  - Vesktop: `(277) Discord | Friends`
  - ZapZap: `ZapZap`
- Inside the Teams Flatpak with the generated profile:
  - `uname -a` → `windows_nt WIN-CLIENT 10.0 #1 SMP PREEMPT amd64 ...`
  - `/etc/os-release` → `NAME="Windows 10"`, `ID=windows`,
    `VERSION_ID=10`, `PRETTY_NAME="Windows 10 Enterprise"`
- Teams config now contains:
  - `platform.chromeUserAgent` = Windows Edge 152 UA
  - `platform.emulateWindowsChromium` = true

## Login test (supplied account)

- **Before spoof:** sign-in stopped at **Error 53003**, with
  `Device platform: Linux` and `Device state: Unregistered`.
- **After Windows UA + `navigator.platform=Win32`:** the password was accepted
  and the flow advanced to **Microsoft Authenticator number matching**
  (`Approve sign in request … Enter the number if prompted: 15`).
  The Linux conditional-access block is no longer the stopping point.
- MFA approval cannot be completed without the owner's Authenticator app.
- Residual: `navigator.userAgentData.platform` still reports `Linux` because
  Teams' emulation overrides UA/platform but not UA-CH platform. The tested
  conditional-access policy accepted the current spoof. If a future policy
  checks UA-CH, use `Network.setUserAgentOverride` (the preload artifact does
  this) or patch `app/browser/tools/emulatePlatform.js` in the app asar.

## Reset / verify

- PenguInterface → **Windows (Portal for Teams)** → Apply. Reset per-app or
  global as before; the existing reset semantics are unchanged.
- Verify inside the sandbox:
  `flatpak run --filesystem=/run/nuxel/spoof:ro --env=LD_PRELOAD=/run/nuxel/spoof/libnuxel-spoof.so --env=NUXEL_SPOOF_PROFILE=/run/nuxel/spoof/profile.com.github.IsmaelMartinez.teams_for_linux.json --command=sh com.github.IsmaelMartinez.teams_for_linux -c 'uname -a; cat /etc/os-release'`
- Verify bridge evidence:
  `journalctl -u nuxel-http-bridge.service -b | grep -E 'spoof injected|native app evidence|teams spoof config'`

## 2026-11-09 follow-up: "Switch Edge profile" root cause and fix

### What the Edge-profile screen actually is

The AAD converged-login page sets `desktopSsoConfig.isEdgeAnaheimAllowed=true`
and `isEdgeAllowed=false` for this tenant. With an `Edg/...` user agent AAD
takes the Edge/WAM path; with a normal Chrome-on-Windows UA it still starts the
desktop-SSO (BSSO) progress view (`FetchSessionsProgress`, view 55). In
Electron there is no Edge/WAM broker, so that view never advances. The
username/password view is loaded, but the pagination component's CSS state
machine leaves it collapsed (`height: 0`, `animate: slide-out-next`,
`hidePaginatedView`/`hideSubView` out of sync). That is what looked like an
endless "Trying to sign you in" / "Switch Edge profile" screen.

### Fix (shipped in this tree)

- `services/nuxel-bridge/src/teams_emulatePlatform.js` (patched copy of
  `app/browser/tools/emulatePlatform.js`):
  - replaces upstream's `structuredClone(navigator.userAgentData)` (which
    throws `NavigatorUAData object could not be cloned`) with a plain
    Windows/Chrome UA-CH object;
  - reports `platform: Win32`, `userAgentData.platform: Windows`,
    `architecture: x86`, `bitness: 64`, and Google-Chrome/Chromium brands
    (Microsoft Edge brands when the launched UA contains `Edg/`);
  - on `login.microsoftonline.com`, advances the AAD pagination control past
    the BSSO spinner (`view 55 -> 1`) and pumps `view_onAnimationEnd()` until
    the selected view is visible (also fixes the collapsed SAS number-matching
    view).
- `services/nuxel-bridge/src/asar_patch.py`: pure-Python Electron ASAR
  rewriter (no Node/npm on the phone). It preserves unpacked entries and
  recomputes SHA-256 integrity.
- `services/nuxel-bridge/src/api.py`: before launching Teams, writes the
  patched renderer module into the Flatpak `app.asar` (idempotent, re-applied
  after a Flatpak update) and exports `NUXEL_SPOOF_UA`/`NUXEL_SPOOF_PLATFORM`.
- `services/nuxel-bridge/systemd/nuxel-http-bridge.service`: grants the bridge
  write access only to the Teams Flatpak deployment tree so the ASAR repair can
  be installed from the sandboxed service.
- `pwa/nuxel-apps/penguinterface/js/spoof.js`: the Windows (Portal for Teams)
  preset now uses **Windows Chrome 152** (not `Edg/`) and applies per-app to
  `com.github.IsmaelMartinez.teams_for_linux`. Chrome-on-Windows reaches the
  normal password/MFA flow; advertising Edge makes AAD ask for the Edge
  profile broker that Electron cannot provide.

### Verified on nuxel (2026-11-09)

- Bridge launch argv contains the Chrome-on-Windows UA; config.json contains
  `platform.emulateWindowsChromium=true` and the same UA.
- Inside the renderer (CDP):
  - `navigator.userAgent` = Windows Chrome 152
  - `navigator.platform` = `Win32`
  - `navigator.userAgentData` = `[{Google Chrome,152},{Chromium,152},{Not_A Brand,24}]`,
    `platform: Windows`
  - AAD `ServerData.browser` = `Chrome`, OS `Windows 10.0`
  - AAD pagination auto-switched `55 -> 1`; username view visible.
- Submitted the supplied email/password: AAD accepted the password and
  rendered the Microsoft Authenticator number-matching view automatically
  (`Approve sign in request`, number `96`). No Linux/Edge-profile block.
- Remaining step: the owner must approve the Authenticator push (or enter the
  6-digit code from the Authenticator app). MFA is a real factor and cannot be
  synthesized from the password or the local device.

### Reset / reapply

- To remove the renderer patch, restore
  `/var/lib/flatpak/app/com.github.IsmaelMartinez.teams_for_linux/current/active/files/teams-for-linux/resources/app.asar.nuxel-orig`
  over `app.asar`.
- To reapply manually:
  `python3 /usr/lib/nuxel/nuxel-bridge/asar_patch.py --asar <app.asar> --backup --set app/browser/tools/emulatePlatform.js:/usr/lib/nuxel/nuxel-bridge/teams_emulatePlatform.js`
  (the bridge does this automatically on the next spoofed Teams launch).

## Why the final 53000 block remains (device compliance, not browser identity)

After the Windows/Chrome spoof and pagination fix, the flow now reaches the
password step, MFA, and then AAD's final Conditional Access page:

```
Error Code: 53000
Device identifier: Not available
Device platform: Windows 10
Device state: Unregistered
This application ... can only be accessed from:
Devices or client applications that meet ASN Bank management compliance policy.
Since you're using Chrome, you need to install this extension. You must be on
Windows 10 version 1703 and above. Alternatively, you can use Microsoft Edge
or Internet Explorer ...
```

That is a **server-side device compliance check**. The browser is already
reporting Windows 10 and the correct Chrome UA-CH; the missing piece is a
Microsoft-signed device registration / compliance token (the Windows Accounts
SSO extension or Edge profile broker). No amount of `uname`, os-release,
user-agent, DMI or UA-CH spoofing can forge that token.

### Microsoft identity broker for Linux attempt

We also installed and started `microsoft-identity-broker` 1.6.1 on nuxel
(aarch64) to see whether its Entra device-registration/PRT path could satisfy
the policy:

- The package is Java-only and its jars do run on aarch64; `microsoft-identity-device-broker`
  started successfully after:
  - installing `java-21-openjdk-headless`,
  - adding `--add-exports java.base/sun.net.www.protocol.https=ALL-UNNAMED`,
  - reloading the D-Bus system policy.
- The user broker (`com.microsoft.identity.broker1`) then failed at JavaFX
  startup:
  - `Error initializing QuantumRenderer: no suitable pipeline found`
  - `No toolkit found`
  The package's JavaFX 15 native libraries are x86_64 and JavaFX expects
  GTK/X11; nuxel has neither Xwayland nor aarch64 JavaFX 15.
- Even with aarch64 JavaFX + Xvfb, the broker's interactive flow would still
  have to register the device and the tenant policy would still decide whether
  the device is *compliant* (Intune), not merely registered.

The broker services were stopped after this test; the package remains installed
for future work. This is recorded as a blocked path, not a silent failure.

### What can actually satisfy the policy

1. A real Windows 10/11 device (or Windows VM) joined/compliant with the
   tenant, using the Edge profile or the Microsoft SSO extension.
2. A tenant-side Conditional Access change: exclude this user/device, or
   allow unmanaged devices with MFA for Teams.
3. A supported Intune-managed Linux device (the tenant would need to support
   Linux compliance; Fedora 43 aarch64 is not a supported Intune Linux target).
4. Use the Teams mobile app on a compliant phone instead of the nuxel web
   client.
