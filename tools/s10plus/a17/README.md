# A17 build + helper sources (cycle 7, 2026-10-15)

Everything needed to reproduce candidate A17 from scratch. Kept here (not in
`.scratch/`, which is gitignored) so the patch set survives context resets.

## The systemd source edits (the decisive fix)

| File | Purpose |
|---|---|
| `nuxel-systemd-edit.py` | The two anchored edits applied inside `rpmbuild %prep`: `process-util.c::posix_spawn_wrapper()` (posix_spawn fallback, A13) and `pidref.c::pidref_set_pid()` (degrade to a PID-only PidRef when `pidfd_open()` is unsupported — **new in A17**). Fails loudly if an anchor is missing or non-unique. |
| `build-systemd4.sh` | Container driver: `podman exec sd258 sh build-systemd4.sh`. Prints `BOTH EDITS VERIFIED PRESENT:` before the build and extracts `libsystemd-shared-258.11-1.fc43.so` from the `systemd-shared` RPM afterwards. |

```
podman cp nuxel-systemd-edit.py sd258:/b/
podman cp build-systemd4.sh     sd258:/b/nx17/
podman exec sd258 sh /b/nx17/build-systemd4.sh         # ~8 min, log: /b/nx17/build4.log
podman cp sd258:/b/nx17/out4/shared/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so .
# expect sha256 848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981
```

## Offline spawn-path validation (run before every flash)

`stub4k.c` emulates a pidfd-less 4.14 kernel on the modern host kernel;
`psw_test.c` calls the **real** `posix_spawn_wrapper()` out of the library under
test; `fix_pidref.c` is the fix as a preloadable object used to prove the
diagnosis independently of a rebuild.

```sh
gcc -O1 -shared -fPIC -o libstub4k.so   stub4k.c
gcc -O1 -o psw_test psw_test.c -L. -l:libsystemd-shared-258.11-1.fc43.so -Wl,-rpath,$PWD
LD_PRELOAD=./libstub4k.so ./psw_test -
```

Expected: A13/A16 library → `rc=-38 ENOSYS` **with the child still running**;
A17 library → `rc=0`.

## The initramfs edits

| File | Purpose |
|---|---|
| `edit-init-a17.py` | Six anchored edits to `boot/initramfs/init.sh` (A17-INIT-1..5). `INIT_SH=<path> NUXEL_SD_SHA256=… NUXEL_SD_BYTES=… python3 edit-init-a17.py` |
| `build-a17-initramfs.sh` | Builds `A17/initramfs.cpio` from A16's archive + the A17 `/init`, library and helpers. |

## The two new helpers

| File | Purpose |
|---|---|
| `nuxel-verify.c` | Self-contained SHA-256 + ELF verifier so `/init` can prove a deployment without coreutils. `sha256 <file> [hex]`, `elf <file> <machine>`, `present <file> <bytes>`. |
| `nuxel-console.c` | CDC-ACM USB gadget + live kernel-log pump + interactive root shell inside the Fedora root (chroot through a dirfd so `switch_root` is unaffected). No rootfs modification. |

Built static: `gcc -Os -static -ffunction-sections -fdata-sections -Wl,--gc-sections -o <out> <src>.c && strip --strip-all <out>`

## Host-side monitoring

`nuxel-usb-monitor.py <outdir> <seconds> [cmds…]` waits for `/dev/{cu,tty}.usbmodem*`,
configures it 115200 8N1 and logs everything the phone emits.
`usb-watch.sh <outdir> <seconds>` logs any change in the Mac's USB inventory.
