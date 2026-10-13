# Nuxel UTM Deployment, Boot Verification & Phone Flash Preparation — Agent Prompt

> **Cycle reconciliation note (2026-08-19):** Section 21's deliverable has
> been authored and finalized in this cycle. The canonical
> `./nuxel-phone-flash-quickstart.md` (repo root) and its byte-identical copy
> at `finish/nuxel-phone-flash-quickstart.md` record the current flash-readiness
> status and the full 17-item procedure. Live outcome recorded there:
> **UTM VM validation succeeded; physical `mustang` flashing remains BLOCKED —
> zero hardware interaction in this task.** This prompt's procedural sections
> remain authoritative; the quickstart reflects the current repository reality
> and supersedes any stale readiness claims. Nothing in this prompt contradicts
> that status.

You are the execution agent for the Nuxel Linux phone OS project.

Your job is to take the current Nuxel repository on this MacBook and **actually verify and run Nuxel inside UTM**, not merely inspect scripts or tell me how it should work.

You have permission to control this MacBook directly, including UTM, Terminal, filesystem operations, SSH, and other tools required to perform the work.

The authoritative project context is the attached `nuxel-ultimate-build.md`. Read it carefully and use its terminology, paths, architecture, constraints, and especially **Part 12's mandatory create-before-start workflow**. Do not substitute a generic VM workflow for the Nuxel-specific one.

---

## 1. Primary objective

Determine whether Nuxel is already deployed in UTM on this Mac.

If an existing UTM VM contains a sufficiently current Nuxel installation:

1. Identify it.
2. Inspect its actual disk/configuration.
3. Boot it.
4. Verify that it is genuinely Nuxel and not merely a Fedora/Phosh development VM.
5. Repair/deploy/update it as necessary.
6. Test the complete Nuxel runtime.

If Nuxel is NOT actually deployed in a usable UTM VM:

1. Build/create a proper ARM64 Nuxel VM.
2. Register it with UTM.
3. Confirm UTM knows about it.
4. Only then start it.
5. Deploy the current Nuxel code into the guest.
6. Bootstrap/configure Nuxel.
7. Boot and test it.
8. Leave the VM in a usable state.

The end state must be an **actually booted, actually tested Nuxel environment**, or a precise evidence-backed failure report explaining exactly what prevented that.

Do not declare success because files/scripts exist.

---

# 2. Critical source-of-truth facts

The project audit says the architecture is approximately 26% complete overall and, critically, the build/test/integration portions are much less mature than the documentation. The project has real Python services, GTK4 code, PWAs, security configuration, VM scripts and UTM-related infrastructure, but much of it has historically been unbuilt or untested.

The audit reports five existing UTM VMs with Fedora ARM64 + Phosh, phone-shaped 720×1440 displays, GPU acceleration and persistent EFI variables, but explicitly says the important Nuxel runtime state was not confirmed.

Therefore:

**Do not assume a VM named `Nuxel`, `Nuxel-phase1`, `Nuxel-PWA`, etc. is actually running Nuxel. Inspect it.**

---

# 3. First inspect the Mac and UTM

Start by establishing the actual current state.

Check:

```bash
uname -m
sw_vers
ls -ld /Applications/UTM.app
/Applications/UTM.app/Contents/MacOS/utmctl list
```

Also inspect the UTM Documents directory:

```bash
ls -lah ~/Library/Containers/com.utmapp.UTM/Data/Documents/
```

Find all relevant `.utm` bundles.

Inspect candidate VM bundles rather than trusting their names.

For every candidate Nuxel VM, determine:

- VM name
- UUID
- current state
- disk image path
- disk image format
- disk size
- EFI variable file
- CPU architecture
- RAM
- display/GPU configuration
- network configuration
- whether the guest disk appears to contain Nuxel
- whether it is stale/experimental/current
- whether it is Fedora ARM64 + Phosh only or has the actual Nuxel stack

If a candidate VM can safely be inspected without booting, do that first.

---

# 4. Do NOT blindly start an existing VM

First determine whether it is genuinely useful.

The project audit explicitly warns that a stale/Phosh-only VM is not a valid Nuxel start.

A VM is not considered "Nuxel deployed" merely because:

- its name contains Nuxel;
- Fedora is installed;
- Phosh is installed;
- the screen has 720×1440 resolution;
- a Nuxel repository exists somewhere on the Mac;
- Nuxel scripts exist on the host.

The guest must actually contain and/or be configured to run the Nuxel services/application stack.

---

# 5. If a valid Nuxel VM already exists

Prefer repairing/reusing it over creating unnecessary duplicate VMs.

Boot it only after inspecting its state.

Then verify the guest from inside.

At minimum inspect:

```bash
uname -a
cat /etc/os-release
systemctl --failed
systemctl status nuxel-bridge nuxel-portal nuxel-notifications --no-pager
```

Check Nuxel paths:

```bash
find /etc/nuxel /var/lib/nuxel /usr/lib /usr/libexec \
  -maxdepth 3 -iname '*nuxel*' 2>/dev/null
```

Check running processes:

```bash
ps aux | grep -i nuxel
```

Check D-Bus:

```bash
busctl list | grep -i nuxel
```

Check API:

```bash
ss -ltnp | grep -E ':(8000|8080)'
curl -v 'http://127.0.0.1:8080/api/v1/ping?message=hello'
```

Use the actual API routes exposed by the current source if the endpoint differs.

---

# 6. If Nuxel is NOT actually deployed: create the VM properly

Follow **Part 12 exactly**.

The project specifically requires:

> Create the VM first → register it with UTM → confirm it exists → THEN start it.

Do not reverse this order.

The intended creation pipeline is:

```bash
VM_DISK_IMAGE=/path/to/Fedora-Cloud-Base-<ver>-aarch64.qcow2 \
  /bin/bash vm/build-vm-image.sh
```

Then:

```bash
/bin/bash vm/build-vm-image.sh --verify-only
```

Do not continue if verification fails.

The resulting VM bundle must contain the equivalent of:

```text
config.plist
Data.utm/Images/disk-0.qcow2
Data/efi_vars.fd
```

The source document explicitly requires a valid, non-empty qcow2 image and successful `--verify-only` before any start attempt.

---

# 7. Register the VM with UTM

The expected staging location is:

```text
~/Library/Containers/com.utmapp.UTM/Data/Documents/<name>.utm
```

Verify the actual bundle:

```bash
ls -lah \
  ~/Library/Containers/com.utmapp.UTM/Data/Documents/<name>.utm/
```

Verify:

```bash
ls -lh \
  ~/Library/Containers/com.utmapp.UTM/Data/Documents/<name>.utm/config.plist

ls -lh \
  ~/Library/Containers/com.utmapp.UTM/Data/Documents/<name>.utm/Data/efi_vars.fd
```

Then:

```bash
/Applications/UTM.app/Contents/MacOS/utmctl list
```

The new VM must appear.

**At this point it should still be stopped.**

That stopped state is a successful creation state, not a failure.

---

# 8. ONLY NOW start the VM

Once creation and registration are proven:

```bash
/Applications/UTM.app/Contents/MacOS/utmctl start "<VM name>"
```

Then:

```bash
/Applications/UTM.app/Contents/MacOS/utmctl status "<VM name>"
```

Require:

```text
started
```

Do not proceed if the VM does not actually start.

If start fails:

- stop;
- inspect creation/configuration;
- inspect UTM logs;
- verify disk;
- verify EFI vars;
- verify architecture;
- verify the UTM configuration;
- correct the creation problem;
- do NOT blindly rerun deployment against a broken VM.

The source explicitly says a failed start must be treated as a start failure rather than something to "power through."

---

# 9. Deploy the current Nuxel code into the guest

Once the VM is genuinely running:

Use the project's deployment machinery if present:

```bash
/Users/wicked/x/nuxel/vm/deploy-vm.sh
```

However, **do not assume the repository path is still `/Users/wicked/x/nuxel`**.

Determine the actual current repository path first.

If `deploy-vm.sh` has assumptions that are stale or broken, inspect it and fix/use the appropriate current mechanism.

Do not silently replace Nuxel's intended architecture with a generic distro installation.

---

# 10. Run the Nuxel VM bootstrap

The project specifically calls for actually running:

```text
vm/nuxel-vm-bootstrap.sh
```

inside a real ARM64 Fedora VM.

Run it where appropriate, inspect every failure, and fix deployment problems rather than merely reporting that the script exists.

The source identifies this as one of the immediate required actions.

---

# 11. Verify the Nuxel services

The minimum service set is:

- `nuxel-bridge`
- `nuxel-portal`
- `nuxel-notifications`
- Nuxel HTTP bridge/API
- Nuxel Phosh agent

Run:

```bash
systemctl status nuxel-bridge nuxel-portal nuxel-notifications --no-pager
```

Also:

```bash
systemctl --failed
```

and:

```bash
journalctl -u nuxel-bridge -u nuxel-portal -u nuxel-notifications \
  --no-pager -n 200
```

Verify D-Bus names:

```bash
busctl list | grep -E 'org\.nuxel|Nuxel'
```

The source describes the intended runtime integration as:

```text
PWA
 ↓ HTTP
API server
 ↓ Python
Bridge
 ↓ D-Bus
Portal
 ↓ D-Bus
PhoshAgent
 ↓
User consent
 ↓
ModemManager / NetworkManager / GeoClue
```

This chain is historically the single largest untested integration gap.

---

# 12. Verify the HTTP API

Check:

```bash
ss -ltnp | grep -E ':(8000|8080)'
```

Then test the API using the actual current endpoint.

The documented smoke test is:

```bash
curl 'http://127.0.0.1:8080/api/v1/ping?message=hello'
```

A successful HTTP response is required.

Do not accept a mock/fallback response as proof that the actual Nuxel bridge is working.

The audit specifically warns that the API has mock fallbacks which can hide a dead bridge.

Therefore verify that the bridge itself is alive before accepting API success.

---

# 13. Verify Phosh

Confirm the guest actually boots into the intended Phosh session.

Check:

```bash
echo "$XDG_SESSION_TYPE"
echo "$WAYLAND_DISPLAY"
ps aux | grep -i phosh
```

Use the project's existing verification helper if present:

```bash
vm/vm-verify-phosh-agent.sh
```

Also inspect the visual VM display yourself.

The requirement is not merely "Phosh process exists."

Verify that:

- graphical session appears;
- display is usable;
- Nuxel UI/home is reachable;
- Nuxel apps can be launched where currently implemented;
- permission UI can appear where supported.

---

# 14. Verify the Nuxel home/PWA path

The documented development path uses Chromium kiosk mode.

Where supported by the current VM:

```bash
chromium --kiosk \
  http://127.0.0.1:8000/pwa/nuxel-home/index.html
```

If the current repository exposes a different path/port, inspect the current scripts and use the real one.

Verify:

- Nuxel Home loads;
- JavaScript executes;
- service worker loads;
- bridge.js operates;
- API communication works;
- UI is not merely static HTML.

Remember that the current audit says the PWA runtime itself is not production-complete and that most PWAs historically run only as browser frontends. Do not claim production PWA isolation based solely on Chromium kiosk mode.

---

# 15. Verify D-Bus/portal/permission flow

Test the actual D-Bus chain.

At minimum inspect:

```bash
busctl tree org.nuxel.Bridge
busctl tree org.nuxel.Portal
busctl tree org.nuxel.Notifications
```

Use `dbus-send` or `busctl call` against safe read/test methods exposed by the current code.

Do not invent methods.

If a permission request can safely be triggered from an existing Nuxel test path, trigger it and verify:

```text
application
→ portal
→ PhoshAgent
→ visible consent dialog
→ response
→ result returned to caller
```

The audit specifically identifies portal timeout and PhoshAgent session integration as areas requiring real testing.

---

# 16. Verify security configuration — but distinguish "configured" from "enforced"

Check AppArmor:

```bash
aa-status
```

Check nftables:

```bash
nft list ruleset | head -100
```

Check whether the expected Nuxel profiles are actually loaded/enforced.

Do not report:

> "AppArmor works"

merely because profile files exist.

Likewise, do not report:

> "nftables sandbox works"

merely because the rules parse.

The audit explicitly says these components exist but have historically not been integration-tested.

---

# 17. Run the project's verification helpers

Find and use the current versions of:

```text
vm/vm-verify-services.sh
vm/vm-verify-phosh-agent.sh
vm/deploy-vm.sh
```

Run them where appropriate.

If they fail:

1. capture exact output;
2. determine root cause;
3. fix if reasonably possible;
4. rerun;
5. record final result.

---

# 18. Perform a real end-to-end smoke test

The minimum successful test should demonstrate:

```text
UTM
 ↓
ARM64 Fedora guest
 ↓
Phosh
 ↓
Nuxel services
 ↓
D-Bus
 ↓
HTTP API
 ↓
Nuxel Home/PWA
 ↓
bridge
```

At least one safe permission/portal path should be exercised if the current implementation supports it.

Do not claim the OS is "fully working" if only the graphical shell works.

Instead classify the result accurately, for example:

```text
BOOTABLE: YES
PHOSH: YES
Nuxel services: YES
HTTP API: YES
PWA Home: YES
D-Bus bridge: YES
Portal: YES
PhoshAgent: YES
AppArmor enforcement: NO/UNKNOWN
nftables enforcement: NO/UNKNOWN
Native GTK apps: PARTIAL
Production PWA runtime: NO
Physical Pixel support: NOT TESTED
```

---

# 19. Create/update a UTM state report

If the repository contains or expects:

```text
vm/utm-state-report.md
```

update it with the actual current state.

Include:

- date/time
- host Mac architecture
- UTM version if available
- VM name
- VM UUID
- disk path
- disk size
- CPU/RAM
- GPU mode
- network mode
- boot status
- guest distro
- Phosh status
- Nuxel services
- API status
- PWA status
- D-Bus status
- AppArmor status
- nftables status
- screenshots if the tooling allows
- failures encountered
- fixes applied

Do not preserve old claims if current testing contradicts them.

---

# 20. Phone flashing: DO NOT FLASH THE PHYSICAL PHONE DURING THIS TASK

This task is about getting Nuxel genuinely running in UTM and preparing the phone flashing instructions.

Do **not** flash the physical Pixel 10 Pro XL merely because the VM succeeds.

The source explicitly says the current build pipeline has historically produced zero-filled placeholder boot artifacts and that the flash script warns against using them on hardware. The project also states that there has been zero actual interaction with the target phone.

Therefore:

**No physical-phone flash unless the current repository contains independently verified real hardware images and the recovery path has been verified.**

---

# 21. Prepare the phone flashing quickstart

Create:

```text
./nuxel-phone-flash-quickstart.md
```

If the file already exists, update it rather than creating a contradictory second document.

The document must explain:

1. Current flash-readiness status.
2. Required prerequisites.
3. Android platform-tools.
4. Backup requirements.
5. Exact `mustang` target identification.
6. Factory-image acquisition.
7. SHA-256 verification.
8. Firmware extraction using the Nuxel firmware tooling.
9. Bootloader unlock requirements.
10. `fastboot` detection.
11. Test-boot strategy where supported.
12. Persistent flashing procedure using the repository's current `boot/flash.sh`.
13. AVB/A/B/dynamic partition considerations.
14. First boot validation.
15. Recovery to stock factory image.
16. What constitutes a safe/valid Nuxel hardware build.
17. Explicit warnings against flashing placeholder/stub images.

Do not invent image filenames, partition names, Google download URLs, or commands that the repository/current device documentation does not establish.

If exact details need current external verification, clearly mark them as requiring verification rather than fabricating them.

---

# 22. Important hardware reality

The project documentation identifies the Pixel 10 Pro XL / `mustang` as a difficult target.

It reports mainline support historically at approximately UART/initramfs level, with display/touch/modem/GPU/audio support still major risks.

The current architecture recommendation is a vendor-kernel bootstrap using the Google `android-gs-mustang-6.12` path, with migration toward mainline later.

Do not silently change the project's architecture.

If the VM succeeds but the phone is not currently flashable, report:

> "VM validation succeeded; physical mustang flashing remains blocked."

That is a valid and useful result.

---

# 23. Terminal quickstart required at the end

When finished, print a concise **copy/paste quickstart** in the terminal/output for me.

It must answer:

### Start Nuxel

Exactly how I start the verified UTM Nuxel VM.

For example, if the final VM name is actually `Nuxel`:

```bash
/Applications/UTM.app/Contents/MacOS/utmctl start "Nuxel"
```

But use the actual final VM name.

### Check status

```bash
/Applications/UTM.app/Contents/MacOS/utmctl status "<actual VM name>"
```

### Stop Nuxel

```bash
/Applications/UTM.app/Contents/MacOS/utmctl stop "<actual VM name>"
```

### Verify Nuxel

Give me the shortest useful guest-side verification commands.

### Test Home/PWA

Give me the exact current working command.

Do not output hypothetical commands.

---

# 24. Final report format

At the very end, give me a brutally honest summary:

```text
Nuxel UTM RESULT
================

Existing Nuxel VM found: YES/NO
Existing VM reused: YES/NO
New VM created: YES/NO
UTM registration: PASS/FAIL
VM boot: PASS/FAIL
ARM64 guest: PASS/FAIL
Fedora/Distro: ...
Phosh: PASS/FAIL
Nuxel bridge: PASS/FAIL
Nuxel portal: PASS/FAIL
Nuxel notifications: PASS/FAIL
PhoshAgent: PASS/FAIL
HTTP API: PASS/FAIL
Nuxel Home/PWA: PASS/FAIL
D-Bus integration: PASS/FAIL
AppArmor enforcement: PASS/FAIL/UNKNOWN
nftables enforcement: PASS/FAIL/UNKNOWN
Native GTK apps: PASS/PARTIAL/FAIL
End-to-end smoke test: PASS/FAIL

Physical Pixel flash readiness:
READY / NOT READY / BLOCKED

Reason:
...

Recovery path:
READY / NOT READY / UNKNOWN

Quickstart:
...

Phone quickstart:
./nuxel-phone-flash-quickstart.md
```

Do not use "PASS" where the evidence only shows that a file exists.

---

# 25. Definition of DONE

You are not finished merely because the VM was created.

The task is complete only when:

1. A complete UTM bundle exists.
2. It contains a real bootable disk.
3. UTM has registered it.
4. `utmctl list` shows it.
5. It was started only after creation/registration succeeded.
6. The guest actually boots.
7. Nuxel is actually deployed inside the guest.
8. Phosh actually runs.
9. Bridge/portal/notifications actually run.
10. The HTTP API actually responds.
11. The Nuxel Home/PWA path actually works.
12. The relevant D-Bus integration has been exercised.
13. Verification scripts have been run.
14. Failures are fixed or explicitly documented.
15. The VM is left in a state I can start again myself.
16. The terminal contains a concise start/test/stop quickstart.
17. `./nuxel-phone-flash-quickstart.md` exists and accurately describes the current physical-phone flashing readiness and future procedure.
18. You explicitly distinguish **VM success** from **physical Pixel success**.

The project's own Part 12 acceptance criteria require a complete UTM bundle, UTM registration, a successful start, and verification of Phosh + bridge + portal + notifications + HTTP API.

**Do the work. Do not merely tell me how to do it.**