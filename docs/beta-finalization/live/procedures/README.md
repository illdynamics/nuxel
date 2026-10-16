# Live deploy procedures — the documented route for everything the plan cannot write itself

`tools/beta/live/deploy-manifest.json` deploys **userspace files** through one
discipline: record the previous hash → stage → verify the staged SHA-256 **on the
device** → atomic rename → restart **only** the smallest declared affected
service (or run the group's deliberate reload) → health check → automatic
rollback to the recorded baseline. Nothing else is written, ever: no partition,
no `.img`, no DTB/DTBO, no BOOT container, no kernel, no modem/EFS/PIT region.

Some artefacts cannot honestly be moved by that plan:

| Reason | Terminal state | Where it is handled |
|---|---|---|
| Needs a **compiler** (aarch64 ELF built from `.c`, the libinput shim `.so`, the native shell apps) | `INSTALL_PROCEDURE_REQUIRED` | [native-app-binaries.md](native-app-binaries.md) |
| Needs a **package transaction** (the Fedora 43 NEVRA set, flatpak) | `INSTALL_PROCEDURE_REQUIRED` / `BLOCKED_EXTERNAL_RESOURCE` | [packages-reconcile.md](packages-reconcile.md), [nuxtore-and-flatpak.md](nuxtore-and-flatpak.md) |
| Has a **canonical consumer path outside the plan's userspace roots** (`/etc/NetworkManager`, `/etc/nftables`, `/etc/tor`, `/opt/nuxel/sandbox`) | `INSTALL_PROCEDURE_REQUIRED` | [etc-paths-real-locations.md](etc-paths-real-locations.md) |
| Collides with the **flash-free guard's path-name family** (`modem`/`efs`/`pit`/…) | `INSTALL_PROCEDURE_REQUIRED` | [modem-and-storage-mirror.md](modem-and-storage-mirror.md) |
| Lives in the **BOOT container** (initramfs, kernel image, packed animation) | `BLOCKED_FIRMWARE` | [boot-container-boundary.md](boot-container-boundary.md) |

## The rules every procedure in this directory obeys

1. **Never flash.** No heimdall/Odin/wrapper, no Download Mode, no TWRP, no adb,
   no `dd` onto a block device, no repartition, no EFS/SEC_EFS/PIT/calibration
   write, no kernel install. A procedure that needs one of those does not belong
   here — it belongs in `BLOCKED_FIRMWARE` with the reason written down.
2. **Hash before and after.** Every copy is `sha256sum`-verified at the source,
   at the staged path and at the installed path; a mismatch stops the procedure
   and restores the preserved previous file (`<target>.nuxel-rollback`).
3. **Preserve the previous file.** `cp -a <target> <target>.nuxel-rollback`
   before the first write, so the rollback route is the same one the plan uses.
4. **Single console owner.** Anything run over the serial console goes through
   exactly one host tool at a time, via `sudo`, and never beside
   `screen`/`minicom`/`cat`. A procedure that needs the console releases it
   before the next tool starts.
5. **One writer of `/dev/fb0`.** A graphics procedure asserts, before and after,
   that exactly one process holds the framebuffer and that it is `nuxel-wl-fb`
   (`tools/beta/live/nuxel-fb-owner-assert.sh`). Starting a second client "to
   check" is the defect the assertion exists to catch.
6. **Verdict law.** A procedure copy that has not been behaviourally observed
   leaves the item at `DEPLOYED_UNVERIFIED`. `VERIFIED_ON_S10PLUS` requires a
   fresh device-produced artefact from the same session, committed under
   `docs/beta-finalization/live/evidence/<kind>-YYYYMMDDTHHMMSS+0200/` with a
   `SHA256SUMS`, a machine-readable JSON and the raw transcript. A passing unit
   test never yields `VERIFIED_ON_S10PLUS`; `NEEDS_OWNER_TEST` is terminal and is
   never promoted by inference.
7. **Nothing secret, nothing invented.** No key material is written by a
   procedure (keys are generated on the device by the owner), and no path,
   version or hash is quoted that the procedure does not actually compute.

## Related repository material

* `docs/beta-finalization/live/DEPLOYMENTS.md` — the per-deploy record (device,
  staged hash, installed hash, restart, health, rollback, evidence bundle).
* `docs/beta-finalization/live/BASELINE-CAPTURE.md` — what the live baseline is
  and which host/commands produced it.
* `docs/beta-finalization/boot/ANIMATION-HANDOFF.md` — the handoff contract and
  the single framebuffer owner.
* `docs/beta-finalization/system/SERVICE-GRAPH.md` — the units this plan installs.
