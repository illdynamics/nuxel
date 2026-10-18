# Samsung S5000AP / Exynos 9820 Native Linux Modem Bring-up for Nuxel

## Executive finding

The central result is substantially better than the current Nuxel documentation suggests:

**Nuxel does not need a new kernel modem driver for the Galaxy S10+ SM-G975F. The exact Samsung downstream Linux 4.14.253 kernel already contains the native Exynos S5000AP modem-control, shared-memory transport, SIPC5 framing, mailbox signalling, boot/dump interface, packet-data path and network interfaces, and the attached Nuxel boot captures prove that this driver actually probes successfully on the target hardware.**

The kernel configuration path is explicit: `SEC_SIPC_MODEM_IF` enables Samsung's modem interface; `SEC_MODEM_S5000AP` selects `UMTS_MODEM_S5000AP`, `LINK_DEVICE_SHMEM`, secure CP boot, CP RAM logging, NAPI, zero-copy, GRO and Exynos9820-specific workarounds. citeturn29view0 The corresponding kernel Makefile compiles the generic `modem_v1` core, shared-memory/SBD implementation and `modem_ctrl_s5000ap.o`. citeturn29view1

The attached Nuxel evidence goes further than static source inspection. Its captured kernel configuration has, among others:

```text
CONFIG_SEC_SIPC_MODEM_IF=y
CONFIG_SEC_MODEM_S5000AP=y
CONFIG_LINK_DEVICE_NAPI=y
CONFIG_CP_ZEROCOPY=y
CONFIG_CP_DIT=y
CONFIG_CP_LINEAR_WA=y
CONFIG_CP_PKTPROC=y
CONFIG_LINK_DEVICE_SHMEM=y
CONFIG_UMTS_MODEM_S5000AP=y
CONFIG_CP_SECURE_BOOT=y
CONFIG_CP_RAM_LOGGING=y
CONFIG_MODEM_IF_NET_GRO=y
CONFIG_CP_ETDAC_OTP_WA=y
```

These are built-ins (`=y`), not absent modules. The same configuration occurs in multiple Nuxel debug captures from 15 October 2026, including:

```text
scripts/s10plus-debug-pack/captures/
  20261015T111341Z-full-collection-74105/kernel/recovery-config.gz
```

More importantly, the captured boot log contains the live probe sequence:

```text
mif: modem_probe: 10000.mif_pdata
mif: s5000ap_init_modemctl_device: +++
mif: s5000ap_init_modemctl_device: AP2CP_CFG:0x15020000
mif: create_modemctl_device: s5000ap is created!!!
mif: shmem_create_link_device: MODEM:s5000ap LINK:shmem
mif: shmem_create_link_device: shmem<->s5000ap: LINK_ATTR_SBD_IPC
mif: shmem_create_link_device: shmem<->s5000ap: LINK_ATTR_DPRAM_MAGIC
...
mif: create_io_device: rmnet0 created
...
mif: create_io_device: rmnet7 created
mif: create_io_device: BOOT device = umts_boot0
mif: create_io_device: umts_boot0 created
```

That evidence comes from the supplied repository, particularly:

```text
scripts/s10plus-debug-pack/captures/
  20261015T111341Z-full-collection-74105/
  recovery/current-recovery-dmesg.txt
```

Samsung's source independently agrees with what the capture shows. The S5000AP controller installs operations for CP power-on/off, shutdown, reset, boot-on, boot-off, boot-done, forced crash, dump and boot confirmation. citeturn29view5 The I/O layer explicitly manipulates SIPC5 link headers and hands IP packets to Linux network devices. citeturn29view4

So the blocker is **not**:

```text
Exynos 9820
    ↓
[MISSING Linux modem kernel driver]    ← no
    ↓
ModemManager
```

It is:

```text
Exynos 9820 / S5000AP CP
          │
          ▼
 Samsung downstream kernel                  PRESENT + PROBING
 ┌───────────────────────────────────────┐
 │ modem_v1                             │
 │ modem_ctrl_s5000ap                   │
 │ link_device_shmem + SBD/SIPC5        │
 │ Exynos mailbox                       │
 │ /dev/umts_boot0                      │
 │ /dev/umts_ipc0 / umts_ipc1           │
 │ /dev/umts_rfs0                       │
 │ rmnet0 ... rmnet7                    │
 └───────────────────────────────────────┘
          │
          ▼
 Native CP firmware bootstrap                MISSING
 (replacement for cbd)
          │
          ▼
 RFS/NV service + SIPC5 control stack        MISSING
          │
          ▼
 SIM / registration / SMS / PDP contexts    MISSING
          │
          ▼
 ModemManager/NetworkManager integration     LATER
```

**Accordingly, I would not write or replace `drivers/misc/modem_v1`.** The highest-value engineering work is a small native Linux replacement for the CP-boot portion of `cbd`, followed by an S5000AP-specific SIPC5/RFS userspace service. ModemManager comes after those layers.

The final stage-zero package produced and host-tested during this audit is here:

**[Download `nuxel-s5000ap-stage0.zip`](sandbox:/mnt/data/nuxel-s5000ap-stage0.zip)**

SHA-256:

```text
175ad7c695c47aad25deea47668e477c89f3053f26a98c2ed711a6b546a09e81
```

It contains a deliberately read-only modem status program, a comprehensive on-phone audit script, the minimal audited ABI header, build tests and a Nuxel documentation correction patch. The final version compiled under `-Wall -Wextra -Werror -Wformat=2 -Wshadow -Wconversion -Wstrict-prototypes`, passed its state-decoding tests and `bash -n`, and the Nuxel patch passed `patch --dry-run`. **It has not been executed on the physical SM-G975F from this environment**, so that distinction between host-tested and device-tested is important.

## Source and revision audit

The supplied Nuxel archive itself is identifiable:

```text
nuxel-main(3).zip
SHA-256:
17c15a013983c87febc488a7c6d0014d25e69cf4b9173d507fefb98a11378ffd

ZIP archive comment:
314b92af583f12e26aa3b045726129188fda44db
```

The ZIP contains no `.git` directory, so `314b92af...` is useful GitHub-archive provenance but cannot by itself provide local Git ancestry. The actual tree content should therefore be treated as the audited object, with that ZIP hash retained.

### Kernel provenance

Nuxel is unusually clear about the exact kernel it builds. Both:

```text
kernel/s10plus/defconfig
kernel/s10plus/build-kernel.sh
```

pin:

```text
Repository:
Linux4/android_kernel_samsung_exynos9820

Commit:
f7194c1d15eded1c2a1a4dc63825b26103435cc0

Defconfig:
arch/arm64/configs/exynos9820-beyond2lte_defconfig

Kernel:
Linux 4.14.253 downstream
```

That commit is still publicly addressable and GitHub identifies it as commit `f7194c1`. citeturn29view9 This is extremely important: all implementation work should be written against **that ABI**, not against a random contemporary Lineage branch and not against Exynos9825/Note10 code.

The requested LineageOS common and beyond2lte device repositories are also publicly available; the currently surfaced device trees are on the `lineage-23.2` generation. citeturn28view8turn28view9 They are valuable for identifying Samsung userspace, partition/vendor conventions and current Lineage compatibility choices, but they are **not** the source revision from which Nuxel's running kernel was built.

### Exact kernel driver composition

The exact pinned kernel's modem Kconfig gives the dependency tree directly:

```text
SEC_SIPC_MODEM_IF
└── SEC_MODEM_S5000AP
    ├── UMTS_MODEM_S5000AP
    ├── LINK_DEVICE_SHMEM
    ├── CP_SECURE_BOOT
    ├── CP_RAM_LOGGING
    ├── LINK_DEVICE_NAPI
    ├── CP_ZEROCOPY
    ├── MODEM_IF_NET_GRO
    ├── CP_LINEAR_WA
    └── CP_ETDAC_OTP_WA
```

This isn't inferred from another Exynos generation: the Kconfig actually describes `SEC_MODEM_S5000AP` as the Exynos ModAP S5xxxAP target and explicitly labels `CP_LINEAR_WA` as an Exynos9820 workaround. citeturn29view0

Its Makefile then produces:

```text
modem_main.o
modem_variation.o
modem_io_device.o
modem_utils.o
modem_dump.o

link_device_shmem.o
link_device_memory_snapshot.o
link_device_memory_flow_control.o
link_device_memory_debug.o
link_device_memory_sbd.o
modem_notifier.o

modem_ctrl_s5000ap.o
```

when the corresponding configuration symbols are enabled. citeturn29view1

That gives us the actual answer to the source-file portion of the requested audit:

| Function | Relevant kernel component |
|---|---|
| Core modem framework | `drivers/misc/modem_v1/modem_main.c`, `modem_prj.h` |
| I/O devices and character/network devices | `modem_io_device.c` |
| S5000AP CP control | `modem_ctrl_s5000ap.c` |
| Shared-memory link | `link_device_shmem.c` |
| SBD shared-memory rings | `link_device_memory_sbd.c` |
| Flow control | `link_device_memory_flow_control.c` |
| Memory snapshots/debug | `link_device_memory_snapshot.c`, `link_device_memory_debug.c` |
| SIPC5 framing | modem-v1 SIPC5 headers/helpers used by I/O/link code |
| CP dump | `modem_dump.c` and S5000AP dump operations |
| Notifications/state changes | `modem_notifier.c` plus modem-control state |
| Userspace ABI/ioctls | `modem_prj.h` and `modem_io_device.c` |

The public `modem_io_device.c` explicitly strips SIPC5 link headers before delivering raw traffic and handles IP packets as IPv4/IPv6 Linux network traffic. citeturn29view4 `struct io_device`/`struct link_device` also carries the SIPC version and SBD-link state. citeturn29view2turn29view3

### Userspace source audit

`LineageOS/android_external_libsamsung-ipc` remains available, but it is an old Replicant-derived Samsung IPC implementation: GitHub describes it simply as “replicant's samsung modem IPC implementation”, with the surfaced branch still `cm-14.1`. citeturn29view8

That makes it useful for:

* understanding Samsung IPC command families and naming;
* studying request/response semantics;
* reusing protocol concepts where packet formats match.

It does **not** establish that its device backends, boot procedure or command tables can be dropped unchanged onto beyond2lte/S5000AP. In fact, ShannonBaseband's Samsung-RIL reverse-engineering issue specifically calls out RIL message tracing, understanding RFS and further exploration of SIPC encoding as unfinished work, while linking directly to a Galaxy S10-family `SM-G973F` kernel's `modem_v1/include/sipc5.h`. citeturn28view11

That is strong evidence for treating old `libsamsung-ipc` as a protocol reference rather than assuming binary compatibility with the S10 generation.

The same ShannonBaseband issue received an October 2026 reference to `tinycbd`, but that report concerns Pixel/oriole work, not beyond2lte/S5000AP. citeturn28view11 It may contain useful design ideas, but transferring offsets, secure-boot conventions or firmware sections from that target would violate the target-specific constraint of this project.

Current Lineage's Exynos9820 common proprietary manifest also confirms that the radio userspace remains a significant layer above the kernel: it lists `cass`, RIL init files, `rild`, Samsung SLSI radio manifests and Samsung radio libraries. citeturn29view7 That reinforces the conclusion that having `rmnet0` or `/dev/umts_ipc0` does not by itself mean Linux has a functional telephony stack.

The `ianmacd/d2s` S5000AP DTS is therefore useful only as **architectural corroboration**. It must not be a source of physical addresses or ring layout for this project. The attached Nuxel DTB already gives us the exact beyond2lte values, so there is no reason to import d2s board constants.

## Exact Nuxel hardware and kernel architecture

The attached repository contains enough captured data to reconstruct the AP↔CP interface with unusually high confidence.

### Device-tree memory map

I audited the captured DTB:

```text
scripts/s10plus-debug-pack/captures/
  20261015T064803Z-boot-image-7315/
  boot-image/fdt-00-at-22056960.dtb
```

rather than transferring addresses from d2s or another Exynos model.

For the exact Nuxel/beyond2lte image, the important nodes are:

```text
/shmem
/mailbox_cp
/mif_pdata
/reserved-memory/modem_if
/reserved-memory/modem_spare
/reserved-memory/cp_ram_logging
```

The captured layout is:

| Region / property | Exact captured value |
|---|---:|
| Main modem shared-memory base | `0xF0000000` |
| Main modem shared-memory size | `0x0B900000` |
| CP area size | `0x07800000` |
| VSS offset | `0x07800000` |
| VSS size | `0x00800000` |
| L2B offset | `0x08000000` |
| L2B size | `0x03200000` |
| IPC offset | `0x0B200000` |
| IPC size | `0x00500000` |
| VSS/PARAM offset | `0x0B700000` |
| VSS/PARAM size | `0x00200000` |
| CP RAM logging base | `0xFB900000` |
| CP RAM logging size | `0x02000000` |
| Modem spare base | `0xD0000000` |
| Modem spare size | `0x01600000` |
| AP→CP configuration register | `0x15020000` |
| CP mailbox MMIO | `0x15920000` |
| Mailbox span | `0x180` |
| Captured CP watchdog IRQ | `270` |

The live kernel log independently prints much of the same layout and reports its memory-map verification as successful. That agreement between DTB and boot-time driver output is far stronger evidence than an address copied from a related Samsung board.

The logical topology is therefore:

```text
                    Exynos 9820 AP
                         │
          ┌──────────────┴──────────────┐
          │                             │
     mailbox_cp                     AP2CP_CFG
   0x15920000                       0x15020000
          │                             │
          └──────────────┬──────────────┘
                         │
                  modem_ctrl_s5000ap
                         │
                         ▼
                link_device_shmem
                         │
      ┌──────────────────┴──────────────────┐
      │         shared 0xF0000000           │
      │                                      │
      │ CP executable / boot areas           │
      │ VSS                                  │
      │ L2B                                  │
      │ IPC/SBD rings  @ +0x0B200000         │
      │ parameter area                       │
      └──────────────────┬───────────────────┘
                         │
                         ▼
                     S5000AP CP
```

This also explains why describing the hardware merely as an “integrated modem” is insufficient for Linux bring-up. The AP and CP are separate execution domains communicating through reserved DRAM and mailbox interrupts, with Linux owning the AP side.

### Device enumeration

The exact target DT and captured boot log define considerably more than a single modem character device.

The observed I/O-device set is:

| Device | DT channel ID | Type / likely role |
|---|---:|---|
| `umts_cass` | `0x23` | Samsung CASS userspace channel |
| `umts_ipc0` | `0xeb` | principal formatted IPC/control |
| `umts_ipc1` | `0xec` | secondary formatted IPC/control |
| `umts_rfs0` | `0xf5` | RFS/NV filesystem service |
| `umts_csd` | `0x01` | circuit-switched/data service |
| `umts_router` | `0x19` | Samsung vendor service |
| `umts_dm0` | `0x1c` | diagnostic/DM channel |
| `ipc_loopback0` | `0xf4` | IPC loopback/testing |
| `rmnet0` | `0x0a` | packet-data endpoint |
| `rmnet1` | `0x0b` | packet-data endpoint |
| `rmnet2` | `0x0c` | packet-data endpoint |
| `rmnet3` | `0x0d` | packet-data endpoint |
| `rmnet4` | `0x0e` | packet-data endpoint |
| `rmnet5` | `0x0f` | packet-data endpoint |
| `rmnet6` | `0x10` | packet-data endpoint |
| `rmnet7` | `0x11` | packet-data endpoint |
| `multipdp_hiprio` | `0x00` | multiplexed/high-priority data |
| `multipdp` | `0x00` | multiplexed packet data |
| `umts_boot0` | `0xd7` | CP boot/control interface |
| `umts_ramdump0` | `0xe1` | CP dump interface |
| `smd4` | `0x21` | auxiliary vendor channel |
| `umts_ciq0` | `0x1a` | auxiliary/diagnostic channel |

The kernel source confirms the distinction between formatted IPC, raw IPC and network delivery: its I/O layer handles SIPC5 link framing and feeds raw IPv4/IPv6 packets to Linux netdevices. citeturn29view4

This changes the interpretation of the Nuxel state dramatically:

> Seeing `rmnet0` through `rmnet7` is **not** evidence that cellular data is already usable; it means the AP-side packet transport has been instantiated.

A PDP context still has to be requested through Samsung's control protocol; registration, SIM state, APN/context setup and resulting address/DNS/route information must be handled by userspace before an `rmnetN` becomes an actual bearer.

Likewise, the presence of `umts_ipc0` does not mean a RIL daemon is running. It means the Linux endpoint through which such a service can speak to the CP exists.

### Driver state machine and ABI

Samsung's S5000AP driver wires the modem control object to:

```text
modem_on
modem_off
modem_shutdown
modem_reset
modem_boot_on
modem_boot_off
modem_boot_done
modem_force_crash_exit
modem_dump_start
modem_boot_confirm
```

in the exact pinned source. citeturn29view5

The public `modem_prj.h`/I/O implementation exposes a userspace control ABI including, among others:

```text
IOCTL_MODEM_ON
IOCTL_MODEM_OFF
IOCTL_MODEM_RESET
IOCTL_MODEM_BOOT_ON
IOCTL_MODEM_BOOT_OFF
IOCTL_MODEM_BOOT_DONE
IOCTL_MODEM_STATUS

IOCTL_MODEM_DL_START
IOCTL_MODEM_FW_UPDATE
IOCTL_MODEM_DUMP_START
IOCTL_MODEM_DUMP_UPDATE
IOCTL_MODEM_FORCE_CRASH_EXIT

IOCTL_MODEM_XMIT_BOOT
IOCTL_MODEM_GET_SHMEM_INFO
```

and the I/O-device ioctl dispatcher connects those requests to the modem-controller and link-device operations. citeturn18view0turn18view1

The modem state enumeration includes:

```text
OFFLINE
CRASH_RESET
CRASH_EXIT
BOOTING
ONLINE
NV_REBUILDING
LOADER_DONE
SIM_ATTACH
SIM_DETACH
CRASH_WATCHDOG
```

and the boot-transfer ABI includes a userspace firmware descriptor carrying a binary pointer, image size, modem/binary offsets, mode and transfer length. citeturn16view7

This is the ABI that a native replacement for Samsung `cbd` must target.

### The Calliope trap

One important Nuxel source-audit correction is necessary.

`firmware/s10plus/manifest.yml` currently contains:

```text
calliope2.dt
calliope_dram.bin
calliope_dram_2.bin
calliope_sram.bin
calliope_sram_2.bin
```

near modem-related material. **Those files must not be treated as proof that Nuxel has extracted the cellular CP firmware.**

The Nuxel dmesg tells us exactly who requests at least the SRAM images:

```text
samsung-abox 18c50000.abox:
    Direct firmware load for calliope_sram.bin ...

samsung-abox 18c50000.abox:
    Direct firmware load for calliope_sram_2.bin ...
```

They belong to Samsung's ABOX/audio subsystem in these captures.

So:

```text
calliope_sram.bin
        ≠
SM-G975F cellular modem firmware image
```

for purposes of this project.

The cellular CP image should instead be analysed from the phone's existing stock modem/RADIO partition, read-only. Do **not** substitute the ABOX Calliope images and do **not** invent a `/lib/firmware/modem.bin` mechanism based on Nuxel's unrelated Exynos5500 code.

## What is actually missing

The existing `configs/s10plus/modem/README.md` frames the problem mainly as “there is no ModemManager plugin”. That is one layer too high.

It should be divided into four separate problems.

### CP firmware bootstrap

Something must perform the userspace side of Samsung's boot protocol over `/dev/umts_boot0`.

The kernel already knows how to:

```text
power/reset S5000AP
configure AP↔CP state
receive mailbox interrupts
provide CP shared memory
accept boot transfers
perform secure-boot-related control
transition through modem states
```

but it does not mean a normal Linux `request_firmware()` call will magically bootstrap the CP.

The appropriate native component is something like:

```text
/usr/libexec/nuxel-cpboot
```

or:

```text
nuxel-cpbootd.service
```

whose job is deliberately narrow:

```text
discover exact stock modem partition
        ↓
read/validate Samsung modem image
        ↓
open /dev/umts_boot0
        ↓
execute exact S5000AP cbd boot ioctl sequence
        ↓
transfer the correct image sections
        ↓
complete secure CP boot
        ↓
wait for STATE_ONLINE / defined failure state
```

**The exact ioctl ordering and modem-container section mapping should not be guessed.** That is the most important unresolved boot detail.

The next reverse-engineering action is therefore to capture the exact stock `cbd` interaction with `/dev/umts_boot0`: ioctl numbers/order, `modem_firmware` fields, image offsets and lengths, state transitions and any secure-boot preparation. The downstream driver tells us what operations exist; only the matching stock userspace or a proven equivalent tells us how Samsung intended this exact image to exercise them.

This is precisely where target mixing is dangerous. A Pixel Exynos modem loader or an S5000AP implementation from another board may teach the control flow, but it cannot establish the G975F image offsets or board-specific boot parameters.

### RFS and persistent modem state

`/dev/umts_rfs0` is not ornamental.

ShannonBaseband's own RIL reverse-engineering task specifically identifies “Understand how RFS is implemented” separately from SIPC-message decoding. citeturn28view11 The exact Nuxel DT also creates `umts_rfs0`.

This means the native design should reserve a separate component:

```text
nuxel-rfsd
```

for whatever Samsung RFS operations the S5000AP expects.

The critical safety rule is that an RFS implementation must not translate “modem needs NV data” into arbitrary writes against EFS. First capture and decode the stock operation set. Then implement only the required file semantics with strict pathname validation and backups.

Your existing Nuxel warning about `efs`/`efsg` is correct and should stay:

**never initialise, format, erase, restore from another device, or flash those partitions.**

IMEI/NV/calibration preservation is more important than getting one experimental modem boot.

### SIPC radio control

After CP boot, a native radio daemon must speak S5000AP's actual SIPC5 command set through the formatted IPC endpoint.

The kernel already proves this is a SIPC5 transport: the exact I/O source identifies and removes SIPC5 link headers, and the S10-family Shannon reverse-engineering work points directly to the corresponding `sipc5.h`. citeturn29view4turn28view11

A sensible userspace split is:

```text
libsipc5-s5000
    framing
    request/sequence tracking
    endian-safe encode/decode
    command/group definitions
    unsolicited indications
    timeouts/reconnect

nuxel-radiod
    SIM/PIN state
    modem identity
    network registration
    signal information
    operator selection
    SMS
    packet contexts/APNs
    radio power
```

Do not initially bake this into ModemManager itself. A standalone daemon makes protocol capture, fuzz-hardening and restart behaviour much easier to debug.

Old `libsamsung-ipc` can provide terminology and command-family clues, but its old `cm-14.1` lineage and older device support make S5000AP packet validation mandatory. citeturn29view8

The current Lineage tree's use of Samsung `rild`, Samsung SLSI radio manifests/libraries and `cass` likewise shows how much device-specific userspace still exists above the kernel. citeturn29view7 Those binaries are useful as an **oracle for tracing behaviour**, not as the architecture of an independent Fedora implementation.

### Linux cellular integration

Only after the previous layers work should ModemManager become the focus.

The target milestone before writing a serious MM plugin is:

```text
CP boots repeatably
STATE_ONLINE is reached
        +
SIM status can be queried
        +
PLMN registration works
        +
an APN can create a PDP context
        +
raw IP works over one rmnet interface
        +
SMS send/receive works
```

Then an S5000AP ModemManager backend can map those operations onto the normal Linux cellular model:

```text
SIPC SIM        → MM SIM
SIPC registration → 3GPP registration
SIPC signal     → MM signal properties
SIPC PDP        → Bearer connect/disconnect
rmnetN          → data port
SIPC SMS        → Messaging interface
```

This ordering avoids trying to debug three undocumented layers simultaneously.

`device/s10plus/deviceinfo` therefore also deserves correction. Its current:

```text
deviceinfo_modem_driver="UNKNOWN_NOT_MM_READY"
```

is misleading.

A more accurate description is:

```text
sec_sipc_modem_if / modem_v1
S5000AP SHMEM transport present;
CP userspace boot + radio service pending
```

The documentation correction is included in the downloadable patch.

## Implementation plan

The most efficient implementation sequence is not “write modem driver → write MM plugin”. It is a staged proof of each AP↔CP boundary.

### Establish an immutable baseline

On the currently booting Nuxel system, first run only read-only diagnostics.

From the supplied package:

```bash
unzip nuxel-s5000ap-stage0.zip
cd nuxel-s5000ap-stage0

make

sudo ./nuxel-s5000ap-audit.sh | tee /tmp/s5000ap-audit.txt
sudo ./s5000ap-status --json
```

The status tool opens:

```text
/dev/umts_boot0
```

read-only and issues only:

```c
IOCTL_MODEM_STATUS
```

It deliberately contains **none** of the power, reset, firmware-download or crash ioctls.

Typical interpretation:

```text
0 OFFLINE
```

means the kernel modem controller exists but the CP has not been brought online.

```text
3 BOOTING
```

means something has started the kernel CP boot state machine.

```text
4 ONLINE
```

means the kernel reached its online state.

The status ioctl/state machinery comes directly from the Samsung modem-v1 ABI rather than an AT-command assumption. citeturn18view1turn16view7

The audit script checks:

```text
/proc/config.gz
/dev/umts_*
/dev/ipc_loopback0
rmnet0...rmnet7
multipdp*
live device-tree nodes
reserved-memory modem regions
S5000AP dmesg
modem/RADIO/EFS partition labels
```

without writing any of them.

A very useful first live-console result would be:

```text
/dev/umts_boot0 exists
/dev/umts_ipc0 exists
/dev/umts_rfs0 exists
rmnet0..7 exist
IOCTL_MODEM_STATUS => OFFLINE
```

That would reproduce under Fedora what the attached recovery logs already prove during boot.

### Capture the stock CP image without modifying it

Resolve the actual live block-device name first:

```bash
ls -l /dev/disk/by-partlabel
ls -l /dev/block/by-name 2>/dev/null
```

Do not assume whether Linux exposes Samsung's PIT entry as `RADIO`, `modem` or something else.

Once positively identified, make a **read-only copy** to ordinary filesystem storage:

```bash
sudo dd if=/dev/<confirmed-modem-partition> \
    of=/var/lib/nuxel/modem-stock.img \
    bs=4M status=progress

sha256sum /var/lib/nuxel/modem-stock.img
sudo blockdev --getsize64 /dev/<confirmed-modem-partition>
```

Then all reverse engineering is done against:

```text
/var/lib/nuxel/modem-stock.img
```

—not against the block device.

Keep:

```text
whole-image SHA-256
partition byte size
first/last sectors
PIT metadata
phone firmware/baseband version
```

with every trace. Section offsets are meaningless without tying them to a specific modem image revision.

### Reconstruct `cbd` exactly

This is the decisive reverse-engineering stage.

Build a trace table of every `/dev/umts_boot0` interaction on stock Samsung/Lineage:

| Order | Operation | Input | Return | CP state |
|---|---|---|---|---|
| A | open | flags | fd | OFFLINE |
| B | ioctl | command + argument | ret | … |
| C | boot image transfer | section/offset/length | ret | … |
| D | ioctl | command | ret | BOOTING |
| E | mailbox event | — | — | LOADER_DONE |
| F | ioctl | boot confirmation | ret | ONLINE |

The exact names already exposed by the kernel tell you what to watch for:

```text
MODEM_ON
MODEM_BOOT_ON
MODEM_XMIT_BOOT
MODEM_DL_START
MODEM_BOOT_OFF
MODEM_BOOT_DONE
MODEM_STATUS
```

but **do not hard-code that textual order merely because it looks plausible**. Capture Samsung's real sequence first. The kernel has several distinct boot and boot-confirm operations, which is precisely why guessing is unnecessary and risky. The S5000AP driver exposes those operations explicitly. citeturn29view5

For every `XMIT_BOOT`, capture the userspace descriptor and correlate:

```text
binary address
size
m_offset
b_offset
mode
len
```

against the immutable modem image.

That gives the specification for `nuxel-cpboot`.

### Implement the smallest possible native loader

The first `nuxel-cpboot` should have almost no policy.

Conceptually:

```c
open_boot_device();
verify_target_is_beyond2lte();
verify_expected_modem_image_hash_or_header();

state = modem_status();
require(state == OFFLINE || known_recoverable_state);

execute_verified_boot_sequence();

while (...) {
        state = modem_status();

        if (state == ONLINE)
                success();

        if (state == CRASH_RESET ||
            state == CRASH_EXIT ||
            state == CRASH_WATCHDOG)
                collect_diagnostics_and_fail();
}
```

Features to include from day one:

```text
--dry-run
--image PATH
--boot-device PATH
--verbose
--trace
--timeout
--no-retry
```

and structured logs containing every state change and boot-section hash.

Features **not** to include initially:

```text
modem partition writes
EFS repair
automatic NV reset
firmware update ioctl
automatic crash/reboot loops
RAM dump upload
“try another board's offsets”
```

A failed boot must leave evidence, not mutate the phone trying to recover itself.

### Bring up RFS and IPC independently

After repeatable CP boot, open only `umts_ipc0` and `umts_rfs0` with trace logging and determine what arrives unsolicited.

A useful architecture is:

```text
                    nuxel-cpbootd
                          │
                          │ ONLINE
                          ▼
                ┌───────────────────┐
                │ nuxel-radiod      │
                │                   │
umts_ipc0 ◄────►│ libsipc5-s5000    │
umts_ipc1 ◄────►│                   │
                └────────┬──────────┘
                         │
                         │ controlled RFS requests
                         ▼
                    nuxel-rfsd
                         │
                    /dev/umts_rfs0
```

The first command objectives should be modest:

```text
get CP identity/version
read SIM-present/PIN state
read IMSI/ICCID where protocol permits
radio-power query
registration query
operator query
signal-strength query
```

Only after these work should you send state-changing registration or PDP commands.

For parser security, treat CP packets as untrusted input. Validate:

```text
minimum/maximum SIPC frame length
header length
channel ID
command group
command ID
sequence IDs
nested payload lengths
string termination/encoding
fragment counts
integer overflow
```

before decoding any payload. A baseband is a second computer feeding binary data into a privileged userspace process; its parser should be written accordingly.

### Packet data milestone

The clean first networking milestone is not LTE speed testing. It is:

```text
SIM detected
        ↓
registered on network
        ↓
request one PDP context for known APN
        ↓
CP reports context active
        ↓
associate context with rmnetN
        ↓
configure returned address/prefix
        ↓
install route
        ↓
configure returned DNS
        ↓
ping by IP
        ↓
DNS lookup
        ↓
disconnect PDP cleanly
```

The kernel's network path is already there: Samsung's source removes SIPC5 framing, recognises IPv4 versus IPv6 and passes the packet into the Linux networking stack. citeturn29view4

That means a successful first bearer does **not** require replacing the network driver. The missing knowledge is which SIPC control exchanges create the PDP context and which control response supplies the IP configuration.

### SMS, calls and IMS should follow separately

SMS is principally a SIPC-control problem and is a reasonable milestone after registration.

Voice is not a single problem.

There are at least:

```text
call-control signalling
        +
CP/audio path setup
        +
Samsung ABOX/audio routing
        +
possibly IMS/VoLTE signalling
```

The presence of `umts_csd` should not be interpreted as proof that voice will immediately work after radio registration.

IMS/VoLTE in particular should be treated as a later project rather than allowed to block SIM, SMS and LTE packet-data bring-up.

## Tested code and concrete Nuxel changes

The downloadable package contains:

```text
nuxel-s5000ap-stage0/
├── Makefile
├── README.md
├── nuxel_s5000ap_uapi.h
├── s5000ap-status.c
├── nuxel-s5000ap-audit.sh
├── nuxel-modem-status-doc.patch
└── SHA256SUMS.json
```

**[Download the package](sandbox:/mnt/data/nuxel-s5000ap-stage0.zip)**

### Minimal safe modem-status program

The key safety decision in this code is that the public header contains only:

```c
#define IOCTL_MODEM_STATUS _IO('o', 0x27)
```

not the power/reset/download ioctls.

Its relevant logic is effectively:

```c
int fd = open("/dev/umts_boot0", O_RDONLY | O_CLOEXEC);
if (fd < 0)
        /* fail */;

int state = ioctl(fd, IOCTL_MODEM_STATUS);
```

with the audited state decoder:

```c
enum phone_state {
        STATE_OFFLINE = 0,
        STATE_CRASH_RESET,
        STATE_CRASH_EXIT,
        STATE_BOOTING,
        STATE_ONLINE,
        STATE_NV_REBUILDING,
        STATE_LOADER_DONE,
        STATE_SIM_ATTACH,
        STATE_SIM_DETACH,
        STATE_CRASH_WATCHDOG,
};
```

The state model comes from the exact Samsung modem-v1 ABI. citeturn16view7

The resulting tool can therefore answer the first crucial question from the live Nuxel console without taking control of the CP:

```bash
sudo ./s5000ap-status
```

or:

```bash
sudo ./s5000ap-status --json
```

### Host test result

The corrected final source passed:

```text
cc -O2 -g \
   -Wall -Wextra -Werror \
   -Wformat=2 -Wshadow -Wconversion -Wstrict-prototypes \
   -std=c11 \
   -o s5000ap-status s5000ap-status.c
```

and:

```text
./s5000ap-status --decode 0
→ 0 OFFLINE

./s5000ap-status --decode 4
→ 4 ONLINE

./s5000ap-status --decode 9 --json
→ CRASH_WATCHDOG

unknown state:
→ deliberately returns exit status 2

bash -n nuxel-s5000ap-audit.sh
→ pass

all host tests passed
```

The patch against the supplied Nuxel tree also passed a dry run:

```text
checking file device/s10plus/deviceinfo
checking file configs/s10plus/modem/README.md
```

with exit status `0`.

Again, this is **compile/static/host-tested code, not physical-device-tested code**. The first live run should remain the read-only audit/status phase.

### Proposed source correction

The package's patch updates the stale Nuxel claim that the modem driver is unknown. The essential correction is:

```diff
-deviceinfo_modem_driver="UNKNOWN_NOT_MM_READY"
+deviceinfo_modem_driver="sec_sipc_modem_if/modem_v1 (S5000AP SHMEM; userspace CP boot + radio service pending)"
```

and rewrites the modem README's architecture from:

```text
no ModemManager plugin
→ cellular unavailable
```

to the technically correct:

```text
kernel S5000AP transport exists and probes
        ↓
CP userspace loader missing
        ↓
RFS/SIPC radio service missing
        ↓
ModemManager integration later
```

That distinction matters because otherwise future engineering work is likely to waste time creating another AP-side modem transport when Samsung's complete target-specific one is already running.

## Open questions, risks and final engineering verdict

Several details remain intentionally unresolved because the evidence collected does not justify guessing them.

**The exact G975F `cbd` boot transaction is the primary unknown.** The kernel ABI exposes the mechanisms, but this audit did not establish the exact sequence of `MODEM_ON`/boot/download/confirmation calls or the exact mapping between the SM-G975F modem image's sections and `struct modem_firmware` offsets. That should be obtained from a trace of the matching Samsung userspace, not transplanted from Pixel, Exynos9825 or another S5000-class phone.

**The exact RFS protocol is the second major unknown.** `/dev/umts_rfs0` is unquestionably instantiated on the target, and external Shannon research independently identifies RFS as a distinct reverse-engineering requirement. citeturn28view11 What file namespace and NV transactions the G975F CP actually expects still needs to be captured.

**The exact S10-generation SIPC command dictionary remains to be validated.** `libsamsung-ipc` is real and valuable, but the available Lineage fork is an old Replicant-derived implementation on `cm-14.1`, not proof of an S5000AP backend. citeturn29view8 Every command used for SIM, registration, SMS and PDP should therefore be compared to actual S10 RIL traffic before transmission.

**Current Lineage proprietary userspace should not be mistaken for the desired native solution.** It still carries `cass`, Samsung RIL configuration, `rild` and Samsung radio libraries. citeturn29view7 Those components can be powerful reverse-engineering oracles, but a Fedora-native Nuxel design should replace their required functionality incrementally.

**The Nuxel Calliope firmware entries are an unrelated audio finding, not the cellular image.** The supplied dmesg attributes the `calliope_sram*.bin` requests to `samsung-abox`; using those blobs as the S5000AP image would send the project in the wrong direction.

**No board addresses should be imported from d2s.** The exact beyond2lte DTB and boot logs already expose the G975F mapping, including `AP2CP_CFG=0x15020000`, mailbox MMIO at `0x15920000`, and the full `0xF0000000` shared-memory layout. The exact-device data should win whenever a related Samsung source differs.

The resulting engineering verdict is therefore:

> **The Galaxy S10+ SM-G975F Nuxel modem effort should be reclassified from “native Linux kernel modem driver implementation” to “native userspace S5000AP CP bootstrap + RFS + SIPC5 radio-service implementation”.**

The AP-side Linux kernel portion is not merely present in source; according to the supplied 15 October 2026 captures it has already successfully executed on the phone, mapped the exact Exynos9820 CP memory, initialised its mailbox/watchdog controls, created the S5000AP shared-memory/SBD link, instantiated the SIPC/RFS/boot devices and registered `rmnet0` through `rmnet7`. Samsung's pinned source confirms that these are the intended S5000AP driver mechanisms. citeturn29view0turn29view1turn29view4turn29view5

That removes one of the hardest unknowns from the project.

The shortest credible route to the first native cellular data session is now:

```text
READ-ONLY live audit
        ↓
prove /dev/umts_boot0 + OFFLINE state
        ↓
immutable extraction/hash of exact stock modem image
        ↓
trace exact G975F cbd boot protocol
        ↓
nuxel-cpboot reaches STATE_ONLINE
        ↓
capture / implement minimal RFS
        ↓
decode SIPC5 identity + SIM + registration
        ↓
activate one PDP context
        ↓
route raw IP over existing rmnetN
        ↓
SMS
        ↓
ModemManager backend
        ↓
voice / audio / IMS as separate later work
```

That path preserves the device's original modem/EFS material, uses the exact kernel and exact beyond2lte hardware description already proven by Nuxel, and avoids the two most dangerous mistakes for this platform: **rewriting a kernel driver that already works, and copying CP boot constants from a different Exynos phone.**