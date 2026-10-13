# bg-02 — VM Start Evidence (briq-02)

> Build group: **Start the VM** (roadmap Part 12 step 4).
> Run: QonQrete `20260814-020321-a929fbc1`, cycle 001, construqtor (bg-02).
> Executed: **2026-08-14 04:06–04:07 CEST**. Handoff target: bg-03 (Guest SSH wait + mirror + bootstrap).

## Precondition (briq-01) — confirmed all-green before start

Creation state re-verified immediately prior to starting (no `utmctl start` was
attempted before every check below passed):

- `qemu-img info artifacts/vm/nuxel-aarch64.qcow2`
  - `file format: qcow2`
  - `virtual size: 17 GiB (18253611008 bytes)` (non-zero)
  - `disk size: 520 MiB` / file length `544997648 bytes` (non-zero, real backing)
- QFI magic confirmed on all three disk copies via `od -c` (output `Q F I`):
  - `artifacts/vm/nuxel-aarch64.qcow2`
  - `.../nuxel-aarch64-phosh.utm/Data/disk-0.qcow2`
  - `.../nuxel-aarch64-phosh.utm/Data.utm/Images/disk-0.qcow2`
- `vm/build-vm-image.sh --verify-only` → **exit 0**, outputs `[PASS]` lines:
  - `[PASS] qcow2 magic detected (QFI)`
  - `[PASS] qemu-img confirms qcow2 format`
  - `[PASS] disk image verification complete: artifacts/vm/nuxel-aarch64.qcow2`
- Registered bundle layout complete (all present, 544997648 bytes / 329216 bytes, mtime 2026-08-14 02:33):
  - `config.plist`
  - `Data/efi_vars.fd`, `Data/disk-0.qcow2`
  - `Data.utm/efi_vars.fd`, `Data.utm/Images/disk-0.qcow2`
- `utmctl list` pre-start: UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Status **stopped** (expected pre-start state).

## (1) utmctl start — SEPARATE action

```
$ /Applications/UTM.app/Contents/MacOS/utmctl start "nuxel-aarch64-phosh"
exit_code=0
```

Exit code **0** (success). No error output.

## (2) utmctl status

```
=== utmctl status (t=0) ===
started
exit=0
```

Validated again after the boot-wait period: status remained `started`.

## (3) utmctl list — row assert

```
$ /Applications/UTM.app/Contents/MacOS/utmctl list
UUID                                 Status   Name
711988C4-B34A-4A0F-BA86-B2C4A182E4BE started  nuxel-aarch64-phosh
```

Row shows UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Status **started**, Name `nuxel-aarch64-phosh`. ✅

## (4) Live qemu process assertion

UTM on macOS launches the VM through its own QEMU helper (the binary is
`qemu-aarch64-softmmu` under `QEMULauncher`), NOT the homebrew `qemu-system-aarch64`.
The live UTM VM process is:

```
$ ps aux | grep 'Documents/nuxel-aarch64-phosh.utm' | grep -v grep
PID 5119  /Applications/UTM.app/Contents/XPCServices/QEMUHelper.xpc/.../QEMULauncher
  .../qemu-aarch64-softmmu ... -netdev vmnet-shared,id=net0 -accel hvf
  -drive if=pflash,unit=1,file.filename=.../Documents/nuxel-aarch64-phosh.utm/Data/efi_vars.fd
  -drive ...file.filename=.../Documents/nuxel-aarch64-phosh.utm/Data/disk-0.qcow2,discard=unmap,detect-zeroes=unmap
  -name nuxelaarch64phosh -uuid 711988C4-B34A-4A0F-BA86-B2C4A182E4BE
```

The command line references **all three** required elements:
- `nuxel-aarch64-phosh` → `.../nuxel-aarch64-phosh.utm/...` + `-name nuxelaarch64phosh`
- `disk-0.qcow2` → `.../Data/disk-0.qcow2`
- `vmnet-shared` → `-netdev vmnet-shared,id=net0`

Full verbatim command line (PID 5119, `qemu-aarch64-softmmu`):

```
/Applications/UTM.app/Contents/XPCServices/QEMUHelper.xpc/Contents/MacOS/QEMULauncher.app/Contents/MacOS/QEMULauncher /Applications/UTM.app/Contents/Frameworks/qemu-aarch64-softmmu.framework/Versions/A/qemu-aarch64-softmmu -L /Users/wicked/Library/Containers/com.utmapp.UTM/Data/Library/Caches/qemu -S -spice unix=on,addr=711988C4-B34A-4A0F-BA86-B2C4A182E4BE.spice,disable-ticketing=on,image-compression=off,playback-compression=off,streaming-video=off,gl=on -chardev spiceport,name=org.qemu.monitor.qmp.0,id=org.qemu.monitor.qmp -mon chardev=org.qemu.monitor.qmp,mode=control -nodefaults -vga none -device virtio-net-pci,mac=52:54:00:A1:6A:6B,netdev=net0 -netdev vmnet-shared,id=net0 -device virtio-gpu-gl-pci -chardev spiceport,id=term0,name=com.utmapp.terminal.0 -serial chardev:term0 -cpu max -smp cpus=4,sockets=1,cores=4,threads=1 -machine virt -accel hvf -drive if=pflash,format=raw,unit=0,file.filename=/Users/wicked/Library/Containers/com.utmapp.UTM/Data/Library/Caches/qemu/edk2-aarch64-code.fd,file.locking=off,readonly=on -drive if=pflash,unit=1,file.filename=/Users/wicked/Library/Containers/com.utmapp.UTM/Data/Documents/nuxel-aarch64-phosh.utm/Data/efi_vars.fd -m 8192 -audio none -audiodev spice,id=audio0 -device virtio-blk-pci,drive=drive711988c4-b34a-4a0f-ba86-b2c4a182e4be,serial=711988c4b34a4a0fba86,bootindex=0 -drive if=none,media=disk,id=drive711988c4-b34a-4a0f-ba86-b2c4a182e4be,file.filename=/Users/wicked/Library/Containers/com.utmapp.UTM/Data/Documents/nuxel-aarch64-phosh.utm/Data/disk-0.qcow2,discard=unmap,detect-zeroes=unmap -device virtio-serial -device virtserialport,chardev=org.qemu.guest_agent,name=org.qemu.guest_agent.0 -chardev spiceport,name=org.qemu.guest_agent.0,id=org.qemu.guest_agent -name nuxelaarch64phosh -uuid 711988C4-B34A-4A0F-BA86-B2C4A182E4BE -device virtio-rng-pci
```

> **Note for bg-03 (SSH-wait):** a separate, unrelated long-running dev QEMU exists
> on this host (`/opt/homebrew/bin/qemu-system-aarch64 -name nuxel-directboot`,
> drives `artifacts/vm/work-phosh.qcow2`, `hostfwd=tcp::2222-:22`, `-netdev user`;
> PID 75861, started 02:01, ~7 min CPU). That is **NOT** the UTM VM. The UTM VM uses
> `vmnet-shared` (PID 5119) and is reachable on the vmnet-shared subnet — **not** on
> localhost:2222. Do not confuse the two; the UTM guest SSH target is the
> vmnet-shared IP (bg-03 step 6).

## POST-START boot-wait

Gave the VM ~25s to begin booting (status re-checked and still `started`) before
handing off to the SSH-wait step. Recommended: continue polling `utmctl status`
and probe the vmnet-shared guest until SSH is reachable.

## RESULT

`utmctl start` succeeded (exit 0); status = `started`; `utmctl list` row =
`711988C4-B34A-4A0F-BA86-B2C4A182E4BE started nuxel-aarch64-phosh`; live UTM qemu
process (PID 5119) references nuxel-aarch64-phosh / disk-0.qcow2 / vmnet-shared.
briq-02 PASS. Handing off to bg-03 (Guest SSH wait + mirror + bootstrap).
