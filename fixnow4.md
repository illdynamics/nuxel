connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99

make sure when we have USB Tethering turned on it is actually sharing the itnernet connection we have over WiFi shared over the USB, as my macbook still has no internet with wifi turned off. DO NOT turn my macbook wifi off to test, just make sure you can ping and resolve hosts on the right network interface on my mac and name the service on my mac NuxNet as well. also it is STILL shopwing the old IP-address 10.15.19.1 on the settings of USB networking. fix it properly.

then please fix the VNC and XRDP I can connect to both, only the screens on my macbook for both do not update.
I can successfully clikc and drag and see it happen on my phone only the screens on ther macbook stay the same, sometimes after a while it updates once and then stays on that again, but when moving the mouse I see the mouse on the phone moving lol.

also make sure when we leave the VNC and RDP sessions the pointer is hidden. we should never have a mouse pointer on the screen when not busy with a mouse either locally or remotely.

and I still do not see smaller circles on the pattern lock, still full finger size. make the circles around the lockheads all 9 of them smaller please, and also make the distance between all dots/lockheads +15% more ass well just to be sure.
also use same pattern when setting up pattern lock.

also make sure that microphone quick settings works properly as microphone already works, but it says mic unavailable or is greyed out, make sure it it turned on as we can successfully use the mic, and when we turn it off the microphone is unable to be used by any app until we turn it on again. turn it on by default.

make sure when we drag down top bar once, we get all the quick settings toggle buttons like now, and all notifications as well, change the "More Connection Status" button to "Show More" and when we drag down second time it should NOT expand just yet, ONLY when we actually press the button. so when we drag down twice we will have the quick settings and notifications full over the screen but this extra part is still collapsed. when we actually press "Show More" only THEN you show that External Power, USB data link to host and console transports, live consoles and file transfer status, and add XRDP and VNC statuses and any other missing important info we have to know. also add our IP-addresses of Wifi, USB net, BT status and other cool statuses.

make sure the top bar and quick settings work fast, I notice it is somtimes a bit slow and sluggish or when we disconnect or connect a USB it takes more then 10 seconds to detect the change in the icons and top bar/quick settings/statuses.

make sure all changes are deployed to the live phone, and please version-bump the whole repossitory to v0.8.7-beta, git add commit push everything to a feature branch please and then merge it to main via a PR, then create the tag v0.8.7-beta and make sure the github workflow is building the release that is the most recent/latest version as well that is currently live on the phone.

fix the github workflow error we have now:

Run case "s10plus" in
[nuxel] Device key:       s10plus
[nuxel] Device directory: s10plus
[nuxel-s10plus-kernel] MAKE: gmake
[nuxel-s10plus-kernel] HOSTCFLAGS: -I/home/runner/work/nuxel/nuxel/kernel/host-tools/include
[nuxel-s10plus-kernel] note: dropping flag unsupported by aarch64-linux-gnu-gcc: -Wno-error=return-mismatch
[nuxel-s10plus-kernel] Device: s10plus (beyond2lte, Exynos 9820)
[nuxel-s10plus-kernel] Kernel: android_kernel_samsung_exynos9820@f7194c1d15ed (Linux 4.14.253 downstream)
[nuxel-s10plus-kernel] Cross:   aarch64-linux-gnu-
[nuxel-s10plus-kernel] Defconfig: exynos9820-beyond2lte_defconfig
[nuxel-s10plus-kernel] KCFLAGS: -fcommon -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=implicit-int -Wno-error=strict-prototypes -Wno-error=date-time -Wno-error=designated-init -Wno-error=discarded-qualifiers -Wno-error=pointer-sign -Wno-error
[nuxel-s10plus-kernel] Output:  /home/runner/work/nuxel/nuxel/kernel/s10plus/.build/out
[kernel] Cloning https://github.com/Linux4/android_kernel_samsung_exynos9820 (commit f7194c1d15ed)...
Cloning into '/home/runner/work/nuxel/nuxel/kernel/s10plus/.build/src'...
Note: switching to 'f7194c1d15eded1c2a1a4dc63825b26103435cc0'.

You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by switching back to a branch.

If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -c with the switch command. Example:

  git switch -c <new-branch-name>

Or undo this operation with:

  git switch -

Turn off this advice by setting config variable advice.detachedHead to false

HEAD is now at f7194c1d15ed FROMLIST: ANDROID: binder: Add BINDER_GET_NODE_INFO_FOR_REF ioctl.
[kernel-patches] SKIP documentation stub: 0001-nuxel-phone-features.patch
[kernel-patches] APPLY: 0003-nuxel-initramfs-delivery-diagnostics.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0003-nuxel-initramfs-delivery-diagnostics.patch
[kernel-patches] APPLY: 0004-nuxel-abox-boot-done-and-bt-hciuart.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0004-nuxel-abox-boot-done-and-bt-hciuart.patch
[kernel-patches] APPLY: 0005-nuxel-udmabuf-kbase-buffers.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0005-nuxel-udmabuf-kbase-buffers.patch
[kernel-patches] APPLY: 0006-sec-ts-lpm-bind.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0006-sec-ts-lpm-bind.patch
[kernel-patches] APPLY: 0007-nuxel-sec-nfc-nci-transport.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0007-nuxel-sec-nfc-nci-transport.patch
[kernel-patches] ALREADY_APPLIED: 0007-sec-nfc-class-name.patch
[kernel-patches] APPLY: 0008-mfc-firmware-fail-closed.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0008-mfc-firmware-fail-closed.patch
[kernel-patches] APPLY: 0008-nuxel-userns-flatpak.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0008-nuxel-userns-flatpak.patch
[kernel-patches] APPLY: 0009-nuxel-statx-mnt-id.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0009-nuxel-statx-mnt-id.patch
[kernel-patches] APPLY: 0010-nuxel-dp-shadow-timeout-recovery.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0010-nuxel-dp-shadow-timeout-recovery.patch
[kernel-patches] APPLY: 0011-nuxel-usb-ncm-lifecycle.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0011-nuxel-usb-ncm-lifecycle.patch
[kernel-patches] APPLY: 0014-nuxel-ucount-inc-user-namespaces-fix.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0014-nuxel-ucount-inc-user-namespaces-fix.patch
[kernel-patches] APPLY: 0016-nuxel-chroot-false-positive-userns.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0016-nuxel-chroot-false-positive-userns.patch
[kernel-patches] ALREADY_APPLIED: 0017-nuxel-sec-nfc-ese-gate.patch
[kernel-patches] ALREADY_APPLIED: 0018-nuxel-sec-nfc-force-clk.patch
[kernel-patches] ALREADY_APPLIED: 0019-nuxel-sec-nfc-clk-hold-session.patch
[kernel-patches] APPLY: 0020-nuxel-ssp-hub-power-and-pm.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0020-nuxel-ssp-hub-power-and-pm.patch
[kernel-patches] APPLY: 0021-nuxel-s3nrn82-nci-read-and-strap.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0021-nuxel-s3nrn82-nci-read-and-strap.patch
[kernel-patches] APPLY: 0022-nuxel-fimc-is-linux-firmware-paths.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0022-nuxel-fimc-is-linux-firmware-paths.patch
[kernel-patches] APPLY: 0023-nuxel-nfc-fw-sha1-stack-safe.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0023-nuxel-nfc-fw-sha1-stack-safe.patch
[kernel-patches] APPLY: 0024-nuxel-userns-clone-sysctl-register.patch
[kernel-patches] APPLIED_AND_VERIFIED: 0024-nuxel-userns-clone-sysctl-register.patch
[kernel-patches] summary: /home/runner/work/nuxel/nuxel/kernel/s10plus/.build/out/patch-application.log
[relax-werror] stripped hard-coded -Werror from 41 Makefile(s)
               Makefile
               arch/alpha/lib/Makefile
               arch/alpha/mm/Makefile
               arch/alpha/oprofile/Makefile
               arch/metag/oprofile/Makefile
               arch/mips/Kbuild
               arch/powerpc/kernel/Makefile
               arch/powerpc/kernel/trace/Makefile
               arch/powerpc/kvm/Makefile
               arch/powerpc/lib/Makefile
               arch/powerpc/mm/Makefile
               arch/powerpc/oprofile/Makefile
               arch/powerpc/perf/Makefile
               arch/powerpc/platforms/Makefile
               arch/powerpc/sysdev/Makefile
               arch/powerpc/sysdev/xics/Makefile
               arch/powerpc/sysdev/xive/Makefile
               arch/powerpc/xmon/Makefile
               arch/sh/cchips/hd6446x/Makefile
               arch/sh/kernel/Makefile
               arch/sh/lib/Makefile
               arch/sh/mm/Makefile
               arch/sparc/kernel/Makefile
               arch/sparc/lib/Makefile
               arch/sparc/mm/Makefile
               arch/sparc/prom/Makefile
               drivers/gpu/drm/i915/Makefile
               drivers/gpu/drm/tilcdc/Makefile
               drivers/misc/cxl/Makefile
               drivers/net/wireless/broadcom/bcmdhd_101_16/Makefile
               drivers/scsi/aic7xxx/Makefile
               drivers/scsi/lpfc/Makefile
               drivers/staging/fsl-mc/bus/dpio/Makefile
               tools/build/feature/Makefile
               tools/lib/api/Makefile
               tools/lib/bpf/Makefile
               tools/lib/subcmd/Makefile
               tools/objtool/Makefile
               tools/testing/selftests/nsfs/Makefile
               tools/testing/selftests/powerpc/Makefile
               tools/virtio/Makefile
[nuxel-s10plus-kernel] WARN: EMBED_FW_DIR /home/runner/work/nuxel/nuxel/build/out/s10plus/pwnage38000/firmware does not exist; not embedding core Calliope blobs
gmake[1]: Entering directory '/home/runner/work/nuxel/nuxel/kernel/s10plus/.build/out'
  HOSTCC  scripts/basic/fixdep
In file included from /usr/include/x86_64-linux-gnu/sys/types.h:176,
                 from /home/runner/work/nuxel/nuxel/kernel/s10plus/.build/src/scripts/basic/fixdep.c:105:
/home/runner/work/nuxel/nuxel/kernel/host-tools/include/endian.h:51:6: error: #error "endian.h shim: host __BYTE_ORDER__/endianness must be defined"
   51 | #    error "endian.h shim: host __BYTE_ORDER__/endianness must be defined"
      |      ^~~~~
gmake[2]: *** [scripts/Makefile.host:102: scripts/basic/fixdep] Error 1
gmake[1]: *** [/home/runner/work/nuxel/nuxel/kernel/s10plus/.build/src/Makefile:472: scripts_basic] Error 2
gmake: *** [Makefile:146: sub-make] Error 2
gmake[1]: Leaving directory '/home/runner/work/nuxel/nuxel/kernel/s10plus/.build/out'
Error: Process completed with exit code 2.

then when github workflow is triggered let it do its thing, do not keep monitoring, and reboot the phone when finished.
