# Nuxel S10+ Mobile Networking Pwnage Pack

Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820 / Shannon S5000AP, Nuxel Fedora ARM64, Samsung downstream Linux 4.14.253.

## What is in this pack

- `full-pwnage-mobile.md` — full autonomous engineering prompt for the agent.
- `pwnage-mobile.md` — compact kickoff prompt.
- `tools/s5000ap-status.c` + `tools/s5000ap_uapi.h` — a deliberately tiny read-only CP state probe. It opens `/dev/umts_boot0` read-only and issues only `MODEM_STATUS` (`_IO('o', 0x27)`). It does not power, reset, boot, download, dump, or update the modem.
- `tools/acquire-s10plus-modem-evidence.py` — read-only evidence collector over TWRP ADB or Nuxel SSH. It redacts long numeric identifiers and does not read protected partitions or SIM identities.
- `docs/ARCHITECTURE-AND-GAPS.md` — source review and the distinction between a kernel transport, CP boot, radio protocol, ModemManager integration, and actual service.
- `docs/PLUGIN-IMPLEMENTATION-CONTRACT.md` — implementation/acceptance contract for a real ModemManager plugin after the radio backend exists.
- `firmware/README.md` — firmware inventory and non-inclusion statement.

## Important: this is not a fake firmware/plugin drop

The supplied Nuxel archive contains no lawful, model-matched S5000AP modem firmware image, no validated G975F `cbd` replacement, no captured exact CP boot transaction, and no complete S10-specific SIPC/RFS protocol implementation. Those cannot be safely fabricated. The pack therefore does **not** contain a dummy `samsung-shannon.so`, a guessed modem image, or a speculative CP loader. The agent prompt requires it to build those layers from exact-device evidence and to keep ModemManager disabled for this modem until its backend is real.

The archived test fixtures include zero-byte files named `samsung-shannon.so`. Those are placeholders, not loadable ELF plugins. The agent is explicitly instructed to prevent these fixtures from passing as evidence of a real plugin.

## Host-side quick start

```sh
unzip Nuxel-Mobile-Networking-Pwnage-Pack.zip
cd Nuxel-Mobile-Networking-Pwnage-Pack

# Compile the read-only status probe (host compile only)
make -C tools
make -C tools test

# While the phone is in TWRP and connected by USB:
python3 tools/acquire-s10plus-modem-evidence.py --transport adb --profile twrp

# Once Nuxel is booted and Wi-Fi SSH is available:
python3 tools/acquire-s10plus-modem-evidence.py --transport ssh --profile nuxel \
  --target root@192.168.178.167 --key '~wicked/.ssh/wicked_wqn_id_rsa'
```

The SSH collector only executes read-only diagnostics. The key is used locally by `ssh`; it is never copied into the pack or printed.

## Boundaries

No modem partition write/flash, no EFS/EFSG/SEC_EFS/persist/NV/calibration access, no SIM identifier collection, no raw AT/APDU commands, no PIN/PUK logging, no emergency test calls, and no fabricated signal/registration/data state. Reflash only the kernel/system payloads proven necessary, using Nuxel's existing scripts and preserving rollback.
