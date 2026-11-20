## Exact failure branch still to pin down

The `-EIO` at `fimc_is_sec_run_fw_sel` is most plausibly caused simply by the missing `fimc_is_lib.bin` / `fimc_is_rta.bin` / `fimc_is_fw_mcu.bin` + setfiles in `/lib/firmware/`. But there is an unresolved ambiguity: the header defines `FIMC_IS_FW = "fimc_is_fw.bin"`, whereas the verified stock file is `fimc_is_fw_mcu.bin`. The authoritative loader request basename (`load_fw_name`) must be confirmed against the actual kernel source before deciding whether a second copy named `fimc_is_fw.bin` is needed. The prompt explicitly forbids blindly aliasing the two names. 

## Clear next step (safe, no flashing required)

1. **Deploy the 8 verified blobs** to the live device:
   `scp firmware/s10plus/blobs/device-vendor-firmware/{fimc_is_lib,fimc_is_rta,fimc_is_fw_mcu,setfile_2l4,setfile_3m3,setfile_3p9,setfile_3j1,setfile_4ha}.bin root@10.11.12.99:/usr/lib/firmware/`
   (this is userspace-only; no kernel/boot/partition writes, fully reversible).
2. **Confirm the exact `request_binary()` basename** first via `dmesg` (`path-linux load(...)`) or by opening a sensor video node with the existing `nuxel-fimc-capture` probe, to decide whether `fimc_is_fw.bin` vs `fimc_is_fw_mcu.bin` is requested — and only then determine if a named copy is justified.
3. Build the capture tool for aarch64 and run the bounded 2L4 first-frame trial on `/dev/video130` (capture MPLANE node) after owner approval.

The goal remains active (not complete). The camera is hardware-present and the firmware is ready to deploy; the core work is a single firmware push plus confirming the loader's exact requested filename, then running the existing `nuxel-fimc-capture` tool to get the first verified 2L4 frame. No TWRP flashing should be needed for this first step.

I have **not** called `update_goal` because the objective is genuinely not yet achieved — the next substantive action (deploy firmware + first-frame trial) is clearly specified above for continuation.

