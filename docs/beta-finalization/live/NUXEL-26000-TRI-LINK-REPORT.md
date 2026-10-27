# NUXEL-26000 — Tri-Link Console Revolution — final report

Date: 2026-10-27 (host Europe/Amsterdam)
Host: `dextronux` (Fedora 43 x86_64)
Target: Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820
Kernel: Samsung-derived Linux **4.14.253** (unchanged; **nothing flashed, rebuilt or repartitioned**)

## 0. Status matrix

| Link | Status | Evidence |
|---|---|---|
| Serial Live Console | **PASS (recovery preserved)** | framed root command before and after the work; `/dev/ttyACM0`; lock contention refused a second writer |
| WLAN SSH | **PASS (physical S10+ verified)** | pinned Ed25519 host key, public-key auth, interactive Bash, exit code 7 preserved, SHA-256-verified put/get, auth/host-key failures classified |
| USB-network SSH | **BLOCKED_KERNEL_PANIC (not claimed)** | real pstore `Panic#2 Part1`: `ncm_free_inst -> misc_deregister -> __list_del_entry_valid`; watchdog reboot; see §4 |
| Tri-Link manager | **PASS (physical host + phone, unit-tested failure paths)** | explicit `serial` / `wlan` / `usb` / `auto`; separate adapters; exit codes; transfer guard; serial flock |
| USB SSH with phone Wi-Fi disabled | **NOT RUN** | USB network link could not be established safely; no false claim |

The only complete links are **serial + WLAN SSH**. Tri-Link is therefore **not complete**; the third link is blocked by the live kernel/gadget stack.

## 1. Baseline and prior-state audit

- `git status` was dirty from earlier PWNAGE 25000 work. Those changes were preserved; this work did not reset or overwrite them.
- No `nuxel-live-deploy` process was active at start. The shared serial lock `/tmp/nuxel-live._dev_ttyACM0.lock` was **free**; `--lock-status` reported no recorded owner.
- The physical phone was reachable through `/dev/ttyACM0` at 115200 8N1. Baseline: Fedora 43, kernel `4.14.253`, boot ID `96f40ab6-e1ea-4952-af24-6f7efae499d2`.
- OpenSSH server `10.0p1-12.fc43` was already installed and `sshd.service` was active. The pre-existing A74 drop-in allowed **unrestricted `AllowUsers root`** (root key only, no password). That was tightened in this work; the existing root key was not changed.
- Wi-Fi: `wlan0` connected to `Nuxel Snoerbreuk`, `10.20.30.16/24`; host `wlp91s0` = `10.20.30.22/24`.
- USB gadget: `usb_gadget/nuxel` with only `acm.usb0`, bound to `10c00000.dwc3`.
- Kernel config: `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_DWC3=y`, `CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y`; **ECM and ECM_SUBSET are not set**; RNDIS compiled.
- `nft`, `iptables`, `ufw`, `firewall-cmd` are **absent** on the live image. SSH restriction is enforced by `sshd` `AllowUsers user@CIDR`, not by a local firewall binary.

## 2. Files changed

### New implementation

- `tools/beta/live/nuxel_tri_link.py` — transport model, pinned-host-key SSH adapter, SSH failure classifier, verified put/get, serial delegation, USB capability audit, reconnect classifier, discovery and `auto` selection, cross-transport deployment guard.
- `tools/beta/live/nuxel-live-ssh.py` — CLI for explicit `--transport serial|wlan|usb|auto`, `--exec`, `--shell`, `--put`, `--get`, `--diagnose`, `--discover`, `--init-key`, `--trust-host-key`, `--deploy-manifest`.
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` — thin launcher (same directory/naming as the existing `nuxel-live.sh`).
- `tools/beta/live/nuxel-usb-net.py` — opt-in USB NCM helper; refuses the known-bad 4.14.253 kernel by default; rollback/confirm/status; do **not** run `--apply` on this kernel.
- `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh` — Fedora host-side USB link address helper; refuses when no 18d1:4ee7 net interface exists; macOS is explicitly not guessed.
- `tools/beta/live/nuxel-ssh-provision-manifest.json` — transactional SSH policy deployment (3 files, one `sshd` restart).
- `configs/nuxel/security/ssh/50-nuxel-a74-recovery.conf` — preserves the root key, removes unrestricted `AllowUsers root`.
- `configs/nuxel/security/ssh/60-nuxel-tri-link.conf` — key-only auth, CIDR-restricted users, no forwarding/tunnels, bounded auth timeouts.
- `configs/nuxel/security/ssh/authorized_keys.nuxel` — public key for `nuxel` (private key stays at `~/.ssh/nuxel-tri-link_ed25519`).
- `configs/nuxel/security/ssh/known_hosts` — pinned Ed25519 key under alias `nuxel-s10plus`.
- `configs/nuxel/security/ssh/known_hosts.fingerprint` — `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`.
- `configs/nuxel/security/ssh/README.md` — key/pin/deploy/rollback instructions.
- `configs/nuxel/live-ssh.json` — recorded (not guessed) WLAN/USB/serial targets and USB blocker.
- `tools/beta/live/tests/test_tri_link.py` — 51 offline tests (below).
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/` — full physical USB panic evidence.
- `docs/beta-finalization/live/evidence/tri-link-ssh-{plan,plan2,apply-n26000,apply2-n26000,noop-n26000}/` — deploy plans, journals, evidence and SHA-256 manifests.

### Modified

- `tools/beta/live/nuxel_live.py` — added `/etc/ssh/sshd_config.d` and `/home/nuxel/.ssh` to `ALLOWED_TARGET_ROOTS` (the flash-adjacent guards are unchanged). The large diff also contains the pre-existing PWNAGE 25000 working-tree changes, which were preserved.
- `tools/beta/live/deploy-manifest.json` — two `non_deployable` entries: the SSH policy source (deployed by its own manifest) and the host-side `live-ssh.json`.
- `configs/nuxel/security/remote-access.json` — records the actual Tri-Link state and the USB blocker.
- `configs/nuxel/security/README.md` — points at the new Tri-Link state.

## 3. WLAN SSH — implementation and physical acceptance

### Security model

- Public key only. `PasswordAuthentication no`, `PermitEmptyPasswords no`, `KbdInteractiveAuthentication no`, `AuthenticationMethods publickey`.
- Root password login is not enabled. The existing root **key** remains, but the previous unrestricted `AllowUsers root` was removed; root is now limited to the local WLAN/USB CIDRs and loopback.
- Host key is pinned. Ordinary connections use `StrictHostKeyChecking=yes`, `UserKnownHostsFile=configs/nuxel/security/ssh/known_hosts`, `GlobalKnownHostsFile=/dev/null`, `HostKeyAlias=nuxel-s10plus`, `CheckHostIP=no`.
- No agent/X11/TCP forwarding or tunnels.
- The live image has no nft/iptables binary. The effective restriction is `sshd` `AllowUsers user@CIDR` plus no port-forward/NAT rule. The listener is `0.0.0.0:22`/`[::]:22`; **this is a disclosed limitation**, not a claim of a firewall. Port 22 is not forwarded by this repository or host configuration; no external reachability was tested from the Internet.

### Physical commands and results (actual S10+)

```text
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --host 10.20.30.16 --status
# wlan AVAILABLE ... host key verified; public-key auth ok
# remote-shell OK /usr/bin/bash

... --exec 'printf "hello from %s\n" "$(hostname)"; exit 7'
# rc=7 (remote status preserved; hostname(1) is absent on the phone and the shell
# reported that in-band, which is not a transport failure)

printf 'echo INTERACTIVE_OK; echo SHELL=$0; exit 3\n' | ... --shell
# INTERACTIVE_OK
# SHELL=/bin/bash
# rc=3

... --put /tmp/nuxel-tri-link-src.txt /var/tmp/nuxel-tri-link-src.txt
# 55 bytes, sha256 6392c0db672f0ad5c6bc891324b37830b58334103a300b54511d6b7e7203533d verified
... --get /var/tmp/nuxel-tri-link-src.txt /tmp/nuxel-tri-link-roundtrip.txt
# 55 bytes, same SHA-256, cmp: ROUNDTRIP_BYTES_IDENTICAL

# wrong pinned key
... --known-hosts /tmp/nuxel-wrong-known-hosts --status
# HOSTKEY_MISMATCH, rc=4

# unauthorized key
... --key /tmp/unauthorized/id_ed25519 --status
# AUTHENTICATION, rc=5
```

Service restart versus reboot was tested by stopping `sshd` over serial:

```text
stop sshd  -> WLAN status UNREACHABLE (tcp connection refused), rc=6
start sshd -> WLAN status AVAILABLE, rc=0
boot ID unchanged at that point (service restart, not reboot)
```

The pstore reboot later changed the boot ID; see §4.  After that reboot the same
checks were repeated: auto discovery reported WLAN `AVAILABLE`, USB
`UNAVAILABLE` (no gadget net interface) and serial `AVAILABLE`, selected WLAN,
and a 47-byte post-reboot put/get round trip returned the same SHA-256
(`7c3494739dd5e82655a5f6fa5a5f38bf973648667a5e76b851876b9566dae526`).

`sshd -T` is root-only on this image, so the non-root diagnostic probe reports
empty output; the effective key-only/CIDR policy was verified as root over the
serial console (`allowusers nuxel@… / root@… / …`, no unrestricted
`allowusers root`).

## 4. USB-network SSH — physical audit and hard blocker

Kernel capability is present (NCM compiled), but the live gadget stack is **not safe**:

1. Read-only audit: only `acm.usb0` in `usb_gadget/nuxel`, UDC `10c00000.dwc3`, SuperSpeed; `CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y`; ECM not compiled.
2. An opt-in NCM helper was transferred over WLAN SSH and run. It created `functions/ncm.usb0`, then failed on the read-only `ifname` attribute. Its failure path rebound the UDC.
3. The host then logged `usb 2-3: can't set config #1, error -71`; `/dev/ttyACM0` disappeared. A host `USBDEVFS_RESET` plus `bConfigurationValue=1` restored it.
4. The leftover NCM function was removed with `rmdir`. **The phone panicked** and the watchdog rebooted it. pstore begins `Panic#2 Part1` and the trace contains:

```text
__list_del_entry_valid
misc_deregister
ncm_free_inst
usb_put_function_instance
ncm_attr_release
```

- boot ID before: `96f40ab6-e1ea-4952-af24-6f7efae499d2`
- boot ID after: `a269e14b-2ccd-4f0a-bbeb-088e84daa5a3`
- reset reason: `4`; previous-boot journal ends with `watchdog0: watchdog did not stop!` at 15:25:32.
- After reboot: kernel `4.14.253`, serial PASS, WLAN SSH PASS, gadget clean (`acm.usb0` only), `/var/lib/nuxel/usb-net` and `/var/tmp/nuxel-usb` removed.

**This reboot was an unplanned consequence of the NCM teardown, not a requested reboot.** The phone returned without a manual power cycle. `tools/beta/live/nuxel-usb-net.py --apply` now refuses 4.14.253 with `BLOCKED_KERNEL_PANIC` unless the explicit `--allow-unsafe-kernel` experiment flag is passed. Do not retry NCM on this kernel.

USB SSH with phone Wi-Fi disabled was **NOT RUN** because no USB network interface could be established. No USB transport is claimed.

Host compatibility actually tested: **Fedora 43 x86_64** (host `dextronux`;
`cdc_ncm`, `cdc_ether` and `rndis_host` modules present, no gadget net
interface). **macOS was not tested**; the host helper refuses to guess with
`networksetup`/`ifconfig` and prints a manual-step message on Darwin. The
kernel's ECM and ECM_SUBSET options are not compiled, so CDC-ECM was never a
candidate; NCM is compiled but its teardown is the blocker above.

After the reboot the updated helper was copied over WLAN SSH and run read-only:
it reported `kernel_release: 4.14.253`, `known_bad_kernel: true`,
`status: BLOCKED_KERNEL_PANIC`; `--apply` then refused with exit 2 and the
message above, without creating an NCM function.  The temporary host-side copy
was removed.

Full evidence and SHA-256 sums: `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`
(including `guard-refusal.txt`).

## 5. Tri-Link manager

- Separate adapters: `SerialAdapter` delegates to the existing `nuxel-live.sh`; `SshAdapter` handles WLAN/USB SSH. The serial protocol is not duplicated.
- `--transport auto` performs explicit discovery and prints every result before selecting. It chooses only an `AVAILABLE` SSH transport, never falls back after selection, and reports serial separately as the explicit recovery route. Serial-only actions (`--run`, `--pull`, `--batch`, `--deploy-manifest`) require `--transport serial`; `auto` refuses them instead of silently switching.
- `--transport serial --run/--pull/--batch` delegates to the proven serial launcher; `--deploy-manifest` runs `nuxel-live-deploy.py` under the cross-transport guard.
- `--exec` returns the remote command's status verbatim (tested with 7 and 3). Local failures use:
  - 2 usage/validation
  - 3 transport unavailable
  - 4 host-key mismatch
  - 5 authentication failure
  - 6 network/route/refusal/timeout
  - 7 transfer/checksum failure
  - 8 transfer/deployment lock conflict
  - 130 cancellation
- `--put`/`--get` stage to a temporary remote/local path, verify SHA-256, install atomically, and clean up on failure.
- The cross-transport `DeploymentGuard` excludes a second SSH transfer/deployment. A serial deployment lock is also checked before SSH mutation; ordinary `--exec` is not put behind the exclusive transfer guard.
- Reconnect classification distinguishes `phone_reboot` (boot ID changed), `sshd_restart` (sshd ActiveEnterTimestamp changed) and `transport_loss` (same boot, same sshd).

Physical lock evidence:

```text
# two serial writers
first:  sleep 3; echo FIRST_DONE -> rc=0
second: echo SECOND_SHOULD_FAIL -> rc=3, "owned by another host tool"
# Tri-Link guard held by a deployment
--put ... -> rc=8, "another Tri-Link transfer/deploy owns ..."; file did not arrive
```

## 6. Tests — exact commands and results

### Offline/unit + fake-console integration (no physical phone)

```text
python3 -m pytest tools/beta/live/tests/test_tri_link.py -q
51 passed in 12.33s

python3 -m pytest tools/beta/live/tests/test_live_lib.py \
                 tools/beta/live/tests/test_live_reload_and_transport.py -q
79 passed in 94.10s
```

The 51 tests cover: auth failure, host-key mismatch, missing SSH tools, network refused/timeout/route/DNS/reset, missing USB capability, kernel config parsing, `auto` selection/no fallback, serial delegation, serial busy state, transfer success/corruption/cleanup, exit codes, Ctrl-C -> 130, guard contention, deployment conflict, explicit serial-only actions, reconnect classification, USB early-failure no-rebind, known-bad-kernel refusal, and a real fake-console deploy rollback (exit 5, previous file restored).

Static checks:

```text
python3 -m py_compile tools/beta/live/nuxel_live.py \
  tools/beta/live/nuxel_tri_link.py tools/beta/live/nuxel-live-ssh.py \
  tools/beta/live/nuxel-usb-net.py
# ALL_COMPILE_OK
bash -n scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
        scripts/s10plus-debug-pack/nuxel-usb-net-host.sh
# SHELL_SYNTAX_OK
git diff --check
# clean
```

### Full live-tool suite (pre-existing failures disclosed)

```text
python3 -m pytest tools/beta/live/tests -q
176 passed, 9 failed in 465.08s
```

(The full-suite run collected 49 of the final 51 Tri-Link tests; the focused
suite after the last two CLI cancellation/exit-code tests is the 51-pass run
above.)

The 9 failures are pre-existing and in files this work did not modify:
- 4 coverage assertions in `test_live_deploy_plan.py` (uncovered `configs/nuxel/orientation/*`, `pwa/nuxel-apps/settings/wifi-settings.js`, `pwa/nuxel-apps/snekbyte/js/snek-controls.js`, and several `services/**`/A33 files present in the working tree but not in that manifest). After restoring the manifest formatting, the only remaining `configs/nuxel` miss is the pre-existing `orientation/` set; the new Tri-Link files are named `non_deployable`.
- 5 in `test_live_reboot_verify.py`: the top-level `verdict` is `null` for a deferred reboot (the tool puts `DEFERRED` under `reboot.verdict`), the IRQ-zero rule returns `DEPLOYED_UNVERIFIED` instead of `BLOCKED_HARDWARE`, and three end-to-end cases inherit those two behaviors. `git status` shows those files unmodified by this work.

They were not deleted, skipped or weakened.

## 7. Physical-device evidence (separate from unit tests)

Actually performed on the S10+:

- WLAN SSH host-key verification, public-key auth and Bash shell: PASS.
- Remote exit codes 7 and 3 preserved: PASS.
- 55-byte put/get round trip with identical SHA-256: PASS.
- Wrong pinned key -> exit 4: PASS.
- Unauthorized key -> exit 5: PASS.
- Stop/start `sshd` detected as refused then available, boot ID unchanged at that point: PASS.
- Serial recovery before and after the work: PASS (root framed command, kernel `4.14.253`).
- Serial lock contention: second writer refused with exit 3: PASS.
- Cross-transport deployment guard: transfer refused with exit 8 and no remote file: PASS.
- Idempotent SSH policy deploy: 0 changed files, 0 restarts, 1 health check, `no_op: true`: PASS.
- USB NCM: **BLOCKED**; kernel panic and watchdog reboot; no USB SSH claimed.

## 8. Security implications and limitations

- SSH port 22 listens on all interfaces because the image has no nft/iptables. Authentication is restricted by `sshd` `AllowUsers user@CIDR`; only public keys work. If the phone joins a network whose subnet overlaps the allowed CIDRs, a host there can attempt key auth but still needs an authorized key. Port 22 is not port-forwarded by this repository/host; external Internet reachability was not tested.
- The existing root key remains authorized. Root password login is disabled; root key login is now CIDR-restricted.
- The host key is pinned to `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`. A changed key is a hard failure (exit 4), never silently accepted.
- A Wi-Fi subnet change requires updating the `AllowUsers` CIDR in `60-nuxel-tri-link.conf` and redeploying; otherwise WLAN SSH will refuse the new address.
- USB NCM is not merely untested: its teardown panicked this kernel. A future kernel/gadget fix is required before USB network can be reconsidered.

## 9. Rollback instructions

Serial recovery is independent and was verified after the changes.

Inspect the transaction before restoring:

```bash
python3 tools/beta/live/nuxel-live-deploy.py --transaction-status \
  docs/beta-finalization/live/evidence/tri-link-ssh-apply2-n26000
```

Restore the SSH policy (run over serial as root, with the console lock free):

```bash
for t in \
  /etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf \
  /etc/ssh/sshd_config.d/60-nuxel-tri-link.conf \
  /home/nuxel/.ssh/authorized_keys; do
  b="$t.nuxel-rollback"
  if [ -e "$b" ]; then cp -a "$b" "$t"; else rm -f "$t"; fi
done
sshd -t && systemctl restart sshd.service
```

This restores the pre-NUXEL-26000 A74 file (which contained unrestricted
`AllowUsers root`), removes the Tri-Link drop-in and removes the new `nuxel`
authorized key. The root key and the serial console are untouched. The exact
per-transaction copies are also recorded as
`<target>.nuxel-rollback.pre-<operation-id>` in the evidence directory.

To roll back only the new `nuxel` key while keeping the hardened policy:

```bash
rm -f /home/nuxel/.ssh/authorized_keys
```

Do **not** run `nuxel-usb-net.py --apply` on 4.14.253. The NCM function is
already gone after the reboot; no USB state remains.

## 10. Remaining work

1. A kernel/gadget fix for `ncm_free_inst`/`misc_deregister` (or a different
   supported gadget mode) is required before USB-network SSH can be attempted
   again. Do not flash or rebuild as part of NUXEL-26000.
2. If a firewall binary is later installed, bind/restrict SSH at the packet
   layer rather than relying only on `sshd` CIDRs.
3. If the WLAN subnet changes, update the CIDR and redeploy.
4. Physical USB SSH with Wi-Fi disabled remains **NOT RUN** by definition.
