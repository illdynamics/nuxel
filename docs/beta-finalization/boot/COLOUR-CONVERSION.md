# XRGB8888 → DECON ABGR8888 colour conversion — protected-asset re-verification (area 3, briq-02c)

Scope: Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Fedora 43 ARM64
userspace, Linux 4.14.253 (Samsung), DECON fbdev (`/dev/fb0`, `CONFIG_DRM` **not set**).

Access tier: **repository-only**. The conversion is a **protected A32 asset**
(`docs/beta-finalization/baseline-protection.json`, `INV-2-colour-conversion`); this
briq re-verifies it with a golden-bytes test and wires that test into the regression
gate, so any later change to `nuxel-wl-fb.c` that breaks it turns red.

**Terminal states for this area**

| Item | State |
|---|---|
| Conversion implemented + documented in the bridge | `OFFLINE_TESTED` |
| Golden-bytes test (source LUT + independent reference) | `OFFLINE_TESTED` |
| Golden bytes of the **compiled aarch64** bridge | `OFFLINE_TESTED` — the A32 binary's `--colour-selftest` runs on this host; the **A33** bridge was built as an aarch64 ELF by `build-a33-boot.sh` on the UTM Fedora 43 guest (sha256 `2d8718c4d92858bbae02b7e914f0172d295b1c12446eb861e91c355f2ac912fc`), where `--colour-selftest` passed and `--colour-dump` matched the golden bytes word for word. Not deployed |
| Red/blue order on the **glass** | previously observed on the handset in A20/A23 (photograph + driver proof); a fresh observation is `NEEDS_OWNER_TEST` |

No claim in this document is `VERIFIED_ON_S10PLUS`.

### Revision 3 (bg-02 verification pass) — re-verification, no semantic change

This is the *expected* outcome for a protected asset: the conversion was
**re-verified, not re-implemented**, and the primary evidence is that the files are
byte-identical to the revision-2 state and that the A32 hard pin still matches.

| Check | Command | Result |
|---|---|---|
| A32 conversion source is byte-pinned and unchanged | `bash tools/beta/regression-guard.sh` | `INV-2-colour-conversion` **MATCH**, `tools/s10plus/a32/nuxel-wl-fb.c` = `6501c6d5d74128f9004088663ca78e46356b7131756d325165822a76b56c51d7` (hard assertion) |
| The A33 bridge source under test | `sha256sum tools/s10plus/a33/nuxel-wl-fb.c` | `052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768` — **unchanged in this revision**: no conversion, alpha, LUT or format-detection line was edited |
| Golden bytes (source LUT evaluated as arithmetic + independent reference over 74 words) | `python3 tools/s10plus/a33/tests/test-colour-order.py` | **PASS, 42 checks / 0 failures** |
| Compiled aarch64 artefact word-for-word | `NUXEL_VM=… python3 tools/s10plus/a33/tests/test-colour-order.py` | **SKIPPED** — the UTM Fedora 43 guest was not reachable in this revision (`ssh … ConnectTimeout` timed out). A skip is recorded as a skip, never as a pass; the binary layer stays owned by `bg-11-vm-parity` / the next live deploy |
| Wallpaper asset unchanged (canonical + launcher copy, same bytes) | `sha256sum assets/nuxel-background.png pwa/nuxel-home/assets/nuxel-background.png` | both `6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29` (`INV-11` pin, hard) |
| Boot-animation asset unchanged | `sha256sum assets/nuxel-boot-animation.mp4 pwa/nuxel-home/assets/nuxel-boot-animation.mp4` | both `280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c` (`INV-11` pin, hard) |
| The owner-visible page still ships with the right swatches | the golden-bytes test's page layer | PASS (full-screen red default, `red | green | blue` thirds bar, self-contained) |

Raw vectors re-emitted by this run (identical to the table in §4, which is the
point):

```
src 0x00ff0000 -> bytes ff 00 00 ff  word 0xff0000ff   (red)
src 0x0000ff00 -> bytes 00 ff 00 ff  word 0xff00ff00   (green)
src 0x000000ff -> bytes 00 00 ff ff  word 0xffff0000   (blue)
src 0x00ffffff -> bytes ff ff ff ff  word 0xffffffff   (white)
src 0x00000000 -> bytes 00 00 00 ff  word 0xff000000   (black -> opaque)
src 0x00123456 -> bytes 12 34 56 ff  word 0xff563412
src 0x00fedcba -> bytes fe dc ba ff  word 0xffbadcfe
LUT == independent reference over 74 words (10 primaries + 64 LCG): PASS
```

**Changing the conversion semantics is forbidden** without a new work-queue revision
naming `briq-02c-fb-colour-conversion`. This revision names none, and the only edits
to the A33 bridge family in this pass are in `nuxel-anim-handoff.py` /
`nuxel-verbose-boot.py` (the recorded reason for a waived floor) — the `.c` file is
untouched.

---

## 1. Root cause (driver evidence, not assumption)

The DECON driver on this panel **contradicts itself**, and only one of the two
statements reaches the glass:

* `decon_check_var()` — what `FBIOGET_VSCREENINFO` reports to userspace — declares
  `red.offset=16, green.offset=8, blue.offset=0` (i.e. `0xAARRGGBB` = XRGB8888);
* `decon_pan_display()` — the **only** path that programs a DECON window for fbdev —
  programs `DECON_PIXEL_FORMAT_ABGR_8888`, whose memory order is
  `A[31:24] B[23:16] G[15:8] R[7:0]` (**R in the low byte**).

Source: `docs/s10plus-autonomous-boot-repair/NUXEL-COLOUR-ORDER.md` (quotes both
functions), corroborated by the A21 measurement in
`docs/s10plus-autonomous-boot-repair/COLOR-FORMAT-VERIFICATION.md` (live `NUXEL_FB_INFO`
dump from the handset: `red.off=0x10 green.off=0x8 blue.off=0x0`, plus a deterministic
colour round-trip), and by the boot-animation player, which logs its own override:
`NUXEL_ANIM_FB_RED_OFF=16` then `NUXEL_ANIM_HW_ORDER_NAME=abgr8888 R@0 G@8 B@16`.

Consequence: the Wayland compositor hands the bridge **XRGB8888** shm buffers
(memory bytes `B,G,R,X`). Copying those words into scanout unchanged swaps **red and
blue on the glass**. A29–A31 did exactly that; A32 fixed it and this document
re-verifies the fix.

## 2. The conversion contract

```
compositor word (XRGB8888, little-endian)   0x00RRGGBB   memory: B, G, R, X
DECON word      (ABGR_8888)                 0xAABBGGRR   memory: R, G, B, A
--------------------------------------------------------------
R = (src >> 16) & 0xff   ->  bits  0..7
G = (src >>  8) & 0xff   ->  bits  8..15   (unchanged in place)
B =  src        & 0xff   ->  bits 16..23
A = 0xff                 ->  bits 24..31   (forced opaque)
```

Alpha is **forced to 0xff** for every converted pixel: the DECON does not blend, so a
transparent shm pixel would otherwise expose the previous frame (a stale animation
frame or a previous window).

## 3. Implementation (`tools/s10plus/a33/nuxel-wl-fb.c`)

| Piece | Detail |
|---|---|
| Hardware order | `hw_r_off = 0, hw_g_off = 8, hw_b_off = 16`, `hw_order_override = 1` by default (the DECON order wins over `fb_var`'s declared order, exactly like the animation player's own override) |
| Fast path | two 64 KiB LUTs built once per source format — `cv_lo[x] = ((x & 0xff) << 16) \| (x & 0xff00) \| 0xff000000` and `cv_hi[x] = x & 0xff` — so the inner loop is `dst = cv_lo[src & 0xffff] \| cv_hi[src >> 16]` |
| Generic path (also used if the declared order is trusted) | `(r << hw_r_off) \| (g << hw_g_off) \| (b << hw_b_off) \| 0xff000000` |
| Pass-through formats | `XBGR8888` / `ABGR8888` are already `0xAABBGGRR`; they only get alpha forced opaque |
| Unknown format | logged once as `COLOR_UNKNOWN_SRC_FORMAT=0x… passthrough` — never silently mis-converted |
| Evidence | the applied order is logged on the state channel with the declared `fb_var` order: `… src_format=0x… colour=R@0,G@8,B@16_abgr8888_override=1` |
| Escape hatch | `--fbvar-order` restores the old "trust `fb_var`" path for A/B comparison; it is **not** the default |
| Offline entry points | `nuxel-wl-fb --colour-selftest` (primitives + alpha) and `nuxel-wl-fb --colour-dump` (machine-readable golden bytes for the primaries plus a 64-word LCG sequence) |

## 4. The golden-bytes test (`tools/s10plus/a33/tests/test-colour-order.py`)

Three independent layers, so the test cannot pass by re-implementing the same bug:

1. **SOURCE** — the LUT lines are parsed out of `nuxel-wl-fb.c` and *evaluated as
   arithmetic*, i.e. the test executes the code's own expressions rather than a copy;
   it also asserts the structural facts (constants are the ABGR order, override on by
   default, LUT only built for the DECON order, alpha forced).
2. **REFERENCE** — an independent byte-level implementation derived from the driver
   documentation (`dst bytes = R, G, B, 0xFF`) must agree with layer 1 over the ten
   primaries **and** a 64-word LCG sequence (74 words total).
3. **BINARY** (when reachable) — `nuxel-wl-fb --colour-dump` is parsed and every word
   compared byte-for-byte with layers 1+2. This is the only layer that proves the
   **compiled artefact**; it runs against `build/out/s10plus/a32/nuxel-wl-fb` (the A32
   binary on this host) or against the aarch64 build via `NUXEL_VM=user@host`.

Golden bytes asserted (source → destination memory bytes `R,G,B,A`):

| Source (XRGB8888) | Meaning | Bytes | Word |
|---|---|---|---|
| `0x00ff0000` | red | `ff,00,00,ff` | `0xff0000ff` |
| `0x0000ff00` | green | `00,ff,00,ff` | `0xff00ff00` |
| `0x000000ff` | blue | `00,00,ff,ff` | `0xffff0000` |
| `0x00ffffff` | white | `ff,ff,ff,ff` | `0xffffffff` |
| `0x00000000` | black → **opaque** | `00,00,00,ff` | `0xff000000` |
| `0x00123456` | mixed | `12,34,56,ff` | `0xff563412` |
| `0x00fedcba` | mixed | `fe,dc,ba,ff` | `0xffbadcfe` |

Latest run: **42 checks, 0 failures** in the default (source + reference) mode, and
**48 checks, 0 failures** with the compiled-artefact layer enabled
(`NUXEL_VM=nuxel@192.168.64.3 python3 tools/s10plus/a33/tests/test-colour-order.py`) —
the A33 bridge was built on the UTM guest by `tools/s10plus/a33/build-a33-boot.sh`
(aarch64 ELF, sha256 `2d8718c4d92858bbae02b7e914f0172d295b1c12446eb861e91c355f2ac912fc`) and its
`--colour-dump` agrees word for word with the source-derived conversion. The layer is
skipped, with a printed note, when no aarch64 executable is reachable; the source and
reference layers always execute.

### The owner-visible layer: `pwa/nuxel-home/colour-test.html`

A conversion table cannot see the panel, so the briQ also ships the page the owner
actually looks at. It is served from the launcher's own docroot and therefore goes
through the real path under test (WebKitGTK → Phoc/Wayland → `nuxel-wl-fb` → `/dev/fb0`
→ DECON) — it writes no framebuffer memory itself:

```sh
# on the handset (owner, NEEDS_OWNER_TEST)
sudo systemctl set-environment NUXEL_HOME_URL=http://127.0.0.1:8000/pwa/nuxel-home/colour-test.html
sudo systemctl restart nuxel-pwa-host      # the launcher view now shows the colour test
#  -> the glass must be RED; tap to cycle RED/GREEN/BLUE/WHITE/BLACK/GREY/THIRDS
sudo systemctl unset-environment NUXEL_HOME_URL
sudo systemctl restart nuxel-pwa-host      # back to the normal launcher

# in the VM / any browser on the device
http://127.0.0.1:8000/pwa/nuxel-home/colour-test.html
```

The bottom bar is literally **red | green | blue** left to right: if the left third
looks blue, the R/B swap is back. `test-colour-order.py` asserts that the page ships,
that its swatches are exactly these golden colours, that the thirds bar is in R,G,B
order, and that it is self-contained (no external script or asset fetch). The page
reports each mode to the host diagnostic channel (`COLOURTEST mode=…`) so a
console-side log line exists next to the photo.

## 5. Regression-gate wiring

* `tools/s10plus/a32/tests/run-tests.sh` — the full offline suite the regression guard
  executes (register invariant `INV-9-a32-suite`) — now carries the A33 legs:
  the colour-order golden bytes, the handoff decision table, the verbose-boot
  durability harness, the settings store, the launcher registry and the boot-surface
  contract check. Verified: `bash tools/s10plus/a32/tests/run-tests.sh` → `== 0 failing suite(s) ==`.
* `tools/s10plus/a33/tests/run-boot-tests.sh` — the same bg-02 legs as one command, with
  the optional aarch64 build of the A33 bridge (`build-a33-boot.sh`) when a Linux
  toolchain or the UTM guest is reachable. A build that cannot run is reported as
  skipped/blocked, never as a pass.
* The A32 binary leg (`build/out/s10plus/a32/nuxel-wl-fb --colour-selftest`) remains
  the hard `program` assertion in `INV-2-colour-conversion`, and it passes here
  (`red src=0x00ff0000 got=0xff0000ff want=0xff0000ff`, …).
* The A33 source test is bound to the **A33** bridge (`nuxel-wl-fb.c` in
  `tools/s10plus/a33/`), so a future edit to either bridge file is covered.

## 6. How to re-verify (offline, or on the glass by the owner)

```sh
python3 tools/s10plus/a33/tests/test-colour-order.py            # golden bytes (42 checks)
NUXEL_VM=nuxel@192.168.64.3 python3 tools/s10plus/a33/tests/test-colour-order.py
                                                                # + the compiled artefact (48 checks)
bash    tools/s10plus/a33/tests/run-boot-tests.sh               # every bg-02 leg, one command
bash    tools/s10plus/a33/build-a33-boot.sh                     # build + self-test the aarch64 bridge
bash    tools/s10plus/a32/tests/run-tests.sh                    # the whole offline suite
build/out/s10plus/a32/nuxel-wl-fb --colour-dump | head          # compiled A32 artefact
build/out/s10plus/a32/nuxel-wl-fb --fbvar-order --colour-selftest   # the BUG, for contrast
```

On the handset (owner/live, `NEEDS_OWNER_TEST`): display the shipped colour page
(`pwa/nuxel-home/colour-test.html`, procedure in §4) so the panel must be **red**, not
blue — the page fills the screen with the named colour and its bottom bar is literally
red | green | blue left to right. A photo of the panel is the evidence; `dmesg | grep -i
colour` / the bridge state line (`colour=R@0,G@8,B@16_abgr8888_override=1`) confirms
which path ran, and the page reports `COLOURTEST mode=…` on the host diagnostic channel.
Failure symptom: red and blue exchanged everywhere (launcher icons, wallpaper, green
Wi-Fi tick) — that is the A29–A31 defect, i.e. the conversion was bypassed.

`build/out/s10plus/a32/nuxel-wl-fb --colour-dump` output used as the golden source of
truth is reproducible byte for byte; there is no time- or hardware-dependent input in
the conversion (a pure word → word map), which is why the golden test is valid offline.

## 7. Rollback

Repository-only. `git revert` the commit(s) touching
`tools/s10plus/a33/nuxel-wl-fb.c` (and, if the whole colour revision is being undone,
`tools/s10plus/a32/nuxel-wl-fb.c`). On the device the A32 bridge binary
(`/usr/lib/nuxel/nuxel-wl-fb`, sha256
`e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e`) is the known-good
colour implementation — rolling back to it restores the ABGR conversion. No
boot/USERDATA/DTB write is involved — **no flashing of any kind**.
