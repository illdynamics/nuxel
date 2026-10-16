# Procedure — building and installing the native aarch64 binaries (no compiler on the handset required)

**Scope.** Every native userspace binary the built programme ships:

| Binary | Repository source | Built by | Installs to | Consumer |
|---|---|---|---|---|
| `nuxel-wl-fb` | `tools/s10plus/a33/nuxel-wl-fb.c` (+ `nuxel-handoff-logic.h`, `a29/wlr-screencopy-unstable-v1.xml`) | `tools/s10plus/a33/build-a33-boot.sh` → `build/out/s10plus/a33-boot/nuxel-wl-fb` | `/usr/lib/nuxel/nuxel-wl-fb` (image layout) or `/usr/local/bin/nuxel-wl-fb` (deploy mirror) | `nuxel-wl-fb.service` |
| `nuxel-button-manager` | `tools/s10plus/a33/nuxel-button-manager.c` (+ `nuxel-button-fsm.h`) | `tools/s10plus/a33/build-a33-buttons.sh` → `build/out/s10plus/a33/nuxel-button-manager` | `/usr/lib/nuxel/nuxel-button-manager` | `nuxel-button-manager.service` |
| `nuxel-pwa-host` | `tools/s10plus/a33/nuxel-pwa-host.c` (a32/a31 copies are the same lineage) | `tools/s10plus/a32/build-a32.sh` → `build/out/s10plus/a32/nuxel-pwa-host` | `/usr/lib/nuxel/nuxel-pwa-host` | `nuxel-pwa-host.service` / the launcher surface |
| `libnuxel-libinput-path.so` | `tools/s10plus/a33/nuxel-libinput-path.c` | `tools/s10plus/a33/build-libinput-shim.sh` → `build/out/s10plus/a33/libnuxel-libinput-path.so` | `/usr/lib/nuxel/libnuxel-libinput-path.so` | `LD_PRELOAD=` on `nuxel-wayland.service` |
| `nuxel-console` (rootfs copy) | `tools/s10plus/a33/nuxel-console.c` | `gcc -O2 -static` (below) | `/usr/bin/nuxel-console` | `nuxel-console.service`, **installed but deliberately NOT enabled** |
| native shell apps (`nuxel-contacts`, `nuxel-dialer`, `nuxel-messages`, `nuxel-settings`, `nuxel-permd`) | `shell/nuxel-shell/nuxel-*/` | `shell/nuxel-shell/meson.build` / `build-native-apps.sh` | `/usr/bin/` | `shell/config/*.desktop` (no consumer on the deployed launcher image) |

**The repository cannot stage these.** `build/` is gitignored, so a compiled
artefact is never a `source` in `tools/beta/live/deploy-manifest.json`: the group
`native-shell-sources` and `s10plus-a33-runtime` stage the **sources and the build
scripts**, and the binaries are produced here. Terminal state for a binary this
procedure has produced but not behaviourally observed: `DEPLOYED_UNVERIFIED`.
`INSTALL_PROCEDURE_REQUIRED` is the state until it has been produced at all.

## 1. Build channels (in order of preference)

1. **The aarch64 host/guest that matches the phone** (Fedora 43 aarch64; the UTM
   guest the A31/A32/A33 build scripts already use). Best fidelity: the ELF's
   dynamic dependencies are the phone's.
2. **A cross toolchain** on the Linux host: `CROSS_COMPILE=aarch64-linux-gnu-`.
   `build-libinput-shim.sh` and `build-a33-buttons.sh` accept it directly;
   `build-a33-boot.sh` uses it only if it can see the Wayland headers.

```sh
# 1. the framebuffer bridge (needs wayland-client headers)
bash tools/s10plus/a33/build-a33-boot.sh            # -> build/out/s10plus/a33-boot/nuxel-wl-fb
# 2. the hardware-button manager (needs alsa-lib headers)
bash tools/s10plus/a33/build-a33-buttons.sh         # -> build/out/s10plus/a33/nuxel-button-manager
# 3. the libinput path interposer (host selftest + aarch64 .so)
bash tools/s10plus/a33/build-libinput-shim.sh       # -> .../nuxel-libinput-path-selftest, .../libnuxel-libinput-path.so
# 4. the WebKitGTK launcher host (gtk3 + webkit2gtk4.1 headers)
bash tools/s10plus/a32/build-a32.sh                 # -> build/out/s10plus/a32/nuxel-pwa-host
# 5. the userspace live console (static, no dynamic deps at all)
aarch64-linux-gnu-gcc -O2 -static -o build/out/s10plus/a33/nuxel-console \
    tools/s10plus/a33/nuxel-console.c
```

Every build script already refuses to report success for a non-aarch64 result
(`file … | grep -q 'ARM aarch64'`), and a build channel that cannot run is
reported as **skipped**, never as a pass.

## 2. Confirm the architecture before anything is copied

```sh
file build/out/s10plus/a33-boot/nuxel-wl-fb          # ELF 64-bit … ARM aarch64
for b in nuxel-wl-fb nuxel-pwa-host nuxel-button-manager libnuxel-libinput-path.so; do
  file "$b" | grep -q 'ARM aarch64' || { echo "NOT aarch64: $b"; exit 1; }
done
sha256sum build/out/s10plus/a33-boot/nuxel-wl-fb    # the staged hash, recorded in the deploy report
```

## 3. Install (hash-verified, previous file preserved)

Run over the live console as root, one host tool at a time:

```sh
T=/usr/lib/nuxel/nuxel-wl-fb
cp -a "$T" "$T.nuxel-rollback" 2>/dev/null || true          # preserve the previous binary
sha256sum "$T.nuxel-rollback" 2>/dev/null                   # the recorded previous hash
install -m 0755 /var/tmp/nuxel-wl-fb.staged "$T"            # atomic rename inside the target dir
sha256sum "$T"                                              # must equal the staged hash
systemctl restart nuxel-wl-fb.service                       # ONLY the smallest affected service
systemctl is-active nuxel-wl-fb.service
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb   # still exactly one /dev/fb0 writer
```

The same shape applies to each binary, with these service/target pairs:

| Target | Restart |
|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` | `nuxel-wl-fb.service` |
| `/usr/lib/nuxel/nuxel-button-manager` | `nuxel-button-manager.service` |
| `/usr/lib/nuxel/nuxel-pwa-host` | `nuxel-pwa-host.service` (or restart the launcher surface by hand) |
| `/usr/lib/nuxel/libnuxel-libinput-path.so` | `nuxel-wayland.service` (the preload target) |
| `/usr/bin/nuxel-console` | **none** — the console unit is installed but not enabled; the initramfs owner holds the port |

## 4. Behavioural check per binary (a hash match is not a working service)

* `nuxel-wl-fb` — `nuxel-wl-fb --colour-selftest` and `nuxel-wl-fb --handoff-selftest`
  print the conversion and handoff PASS lines; `/var/lib/nuxel/fb-owner` names
  `nuxel-wl-fb`; `/run/nuxel-fb-owner.lock` holds exactly one pid.
* `nuxel-button-manager` — `nuxelctl buttons fsm` reads the state machine and
  `nuxelctl buttons list` reads the current mapping; a real key press is
  `NEEDS_OWNER_TEST` (owner's hands, terminal until a human presses it).
* `nuxel-pwa-host` — the launcher answers: `curl -s -o /dev/null -w '%{http_code}'
  http://127.0.0.1:8000/pwa/nuxel-home/index.html` is `200` and the WebKit view
  renders (owner-visible; `NEEDS_OWNER_TEST` for the glass).
* `libnuxel-libinput-path.so` — the shim's own selftest binary plus
  `python3 tools/s10plus/a33/tests/test-libinput-shim-invocation.py` on the host;
  on the device, phoc's `/proc/<pid>/fd` shows the real input node.
* `nuxel-console` — **do not** start it while the initramfs console owns the port;
  `services/nuxel-console/test-console-ownership.py` is the assertion that the
  port stays single-owner. A second client is not a test, it is the defect.

## 5. Rollback

```sh
T=/usr/lib/nuxel/nuxel-wl-fb
cp -a "$T.nuxel-rollback" "$T" && sha256sum "$T" && systemctl restart nuxel-wl-fb.service
```

The rollback route is the same for every binary: the preserved
`<target>.nuxel-rollback` copy plus the restart of the single unit that loads it.
No partition, no BOOT container and no kernel are involved at any step — and this
procedure never installs a kernel.

## 6. Honest limits

* A binary built for a different glibc/WebKitGTK than the phone's will load and
  fail at runtime; the load error is the evidence, and the verdict stays
  `DEPLOYED_UNVERIFIED` (or `FAILED` after a rollback) until the consumer is seen
  working.
* `nuxel-console` built from `tools/s10plus/a33/nuxel-console.c` is the userspace
  copy; the artefact that actually owns `/dev/ttyACM0` on a normal boot comes from
  the BOOT container (`/opt/nuxel/nuxel-console`, static, a24 lineage) — replacing
  *that* is a BOOT update and is `BLOCKED_FIRMWARE`, see
  [boot-container-boundary.md](boot-container-boundary.md).
