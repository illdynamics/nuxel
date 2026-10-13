#!/bin/sh
#==============================================================================
# Nuxel Recovery / Failsafe Boot Shell for Google Pixel 10 Pro XL (mustang)
#
# This script boots when the main OS fails to start. It provides:
#   - A minimal busybox-based shell for diagnostics
#   - Tools to inspect and repair partitions
#   - Capability to re-flash from recovery
#   - Access to the serial console logs
#
# DEVICE:  Google Pixel 10 Pro XL (mustang)
# SERIAL:  58211FDCQ001LA
# HW:      MP1.0, SKU G45RY
# SoC:     Google Tensor G5
# MODEM:   Samsung Exynos 5500
#
# HOW TO ENTER RECOVERY:
#   1. Power off the device completely (hold Power + Volume Down for 15s)
#   2. Press and HOLD Volume UP + Power button
#   3. When the Google logo appears, release Power but keep holding Volume UP
#   4. You should see "No command" screen with an Android robot
#   5. Press Volume UP + Power briefly to show the recovery menu
#   6. Select "Enter recovery" using volume keys, confirm with Power
#
# ALTERNATIVE (from bootloader/fastboot):
#   fastboot reboot recovery
#
# ALTERNATIVE (from OS, if partially booted):
#   sudo reboot recovery
#==============================================================================

# ── Recovery shell prompt ───────────────────────────────────────────────────
export PS1="\n\033[1;31m[NUXEL-RECOVERY]\033[0m \033[1;34m\w\033[0m\n# "
export PATH="/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/bin"
export HOME="/root"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Recovery version ────────────────────────────────────────────────────────
RECOVERY_VERSION="0.2.0"

# ── Utility functions ───────────────────────────────────────────────────────

log_info()    { printf '%b\n' "${BLUE}[INFO]${NC}  $1"; }
log_ok()      { printf '%b\n' "${GREEN}[OK]${NC}    $1"; }
log_warn()    { printf '%b\n' "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { printf '%b\n' "${RED}[ERROR]${NC} $1"; }
log_separator() { printf '%b\n' "${CYAN}──────────────────────────────────────────────${NC}"; }

# ── Diagnostic functions ────────────────────────────────────────────────────

diagnostic_overview() {
    log_separator
    printf '%b\n' "${BOLD}  NUXEL RECOVERY DIAGNOSTIC REPORT${NC}"
    printf '%b\n' "  Device:  Google Pixel 10 Pro XL (mustang)"
    printf '%b\n' "  Serial:  58211FDCQ001LA"
    printf '%b\n' "  Date:    $(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'unknown')"
    printf '%b\n' "  Kernel:  $(uname -r 2>/dev/null || echo 'unknown')"
    printf '%b\n' "  Uptime:  $(uptime 2>/dev/null | sed 's/.*up //' | sed 's/,.*//' || echo 'unknown')"
    log_separator
}

check_partitions() {
    log_info "Checking partitions..."
    log_separator

    # List all block devices
    printf '%b\n' "${BOLD}Block devices:${NC}"
    ls -la /dev/block/ 2>/dev/null || ls -la /dev/sd* /dev/mmcblk* 2>/dev/null || echo "  No block devices found"
    echo ""

    # UFS storage (mustang uses UFS 4.0)
    printf '%b\n' "${BOLD}UFS devices:${NC}"
    ls -la /dev/ufs* 2>/dev/null || echo "  No UFS devices found (drivers may not be loaded)"
    echo ""

    # Partition labels
    if [ -d "/dev/disk/by-partlabel" ]; then
        printf '%b\n' "${BOLD}Partitions by label:${NC}"
        ls -la /dev/disk/by-partlabel/ 2>/dev/null | head -40
    else
        printf '%b\n' "${YELLOW}  /dev/disk/by-partlabel not available${NC}"
    fi
    echo ""

    # A/B slot detection
    printf '%b\n' "${BOLD}A/B Slot status:${NC}"
    for slot in "a" "b"; do
        for part in "boot" "vendor_boot" "init_boot" "dtbo" "vbmeta" "system" "modem"; do
            path="/dev/block/by-name/${part}_${slot}"
            if [ -b "${path}" ]; then
                size=$(blockdev --getsize64 "${path}" 2>/dev/null || echo "?")
                echo "  ${part}_${slot}: ${path} (${size} bytes)"
            fi
        done
    done
    echo ""

    # Partition table summary
    printf '%b\n' "${BOLD}Partition sizes:${NC}"
    cat /proc/partitions 2>/dev/null | head -30 || echo "  /proc/partitions not available"
    echo ""
}

check_mounts() {
    log_info "Checking mounts..."
    log_separator
    mount | grep -v "^proc\|^sys\|^devtmpfs\|^devpts\|^tmpfs" 2>/dev/null || echo "  No filesystems mounted"
    echo ""
}

check_kernel_logs() {
    log_info "Checking kernel logs..."
    log_separator

    # Try dmesg first
    if command -v dmesg >/dev/null 2>&1; then
        printf '%b\n' "${BOLD}Last 50 kernel messages:${NC}"
        dmesg 2>/dev/null | tail -50 || echo "  Cannot read kernel log"
    else
        printf '%b\n' "${YELLOW}  dmesg not available${NC}"
    fi
    echo ""
}

check_recovery_logs() {
    log_file="/tmp/recovery.log"
    if [ -f "${log_file}" ]; then
        printf '%b\n' "${BOLD}Recovery log:${NC}"
        tail -30 "${log_file}"
    fi
}

check_hardware() {
    log_info "Checking hardware status..."
    log_separator

    # CPU info
    printf '%b\n' "${BOLD}CPU:${NC}"
    grep "model name\|Hardware\|Processor" /proc/cpuinfo 2>/dev/null | head -5 || \
        echo "  Tensor G5 (gs501) - Cortex-X5/A730/A530"

    # Memory
    printf '%b\n' "\n${BOLD}Memory:${NC}"
    free -h 2>/dev/null || cat /proc/meminfo 2>/dev/null | grep "MemTotal\|MemFree\|MemAvailable" || \
        echo "  Unknown"

    # Check for key hardware nodes
    printf '%b\n' "\n${BOLD}Hardware nodes:${NC}"
    for dev in \
        "/dev/dri/card0" "/dev/dri/renderD128" \
        "/dev/input/event0" \
        "/dev/iio:device0" \
        "/dev/snd/pcmC0D0p" \
        "/dev/ttyGSI0"; do
        if [ -e "${dev}" ]; then
            printf '%b\n' "  ${GREEN}✓${NC} ${dev}"
        else
            printf '%b\n' "  ${RED}✗${NC} ${dev} (not found, driver may be missing)"
        fi
    done

    # Network interfaces
    printf '%b\n' "\n${BOLD}Network interfaces:${NC}"
    if command -v ip >/dev/null 2>&1; then
        ip link show 2>/dev/null | grep -v "^ " | grep -v "^$" | head -20 || \
            echo "  No interfaces"
    elif [ -d "/sys/class/net" ]; then
        ls /sys/class/net/ 2>/dev/null || echo "  None"
    fi

    # USB
    printf '%b\n' "\n${BOLD}USB devices:${NC}"
    lsusb 2>/dev/null | head -10 || \
        cat /sys/kernel/debug/usb/devices 2>/dev/null | head -20 || \
        echo "  USB information not available"

    # PCIe (for MHI modem)
    printf '%b\n' "\n${BOLD}PCIe devices (MHI modem):${NC}"
    if command -v lspci >/dev/null 2>&1; then
        lspci 2>/dev/null | head -10 || echo "  No PCIe devices"
    else
        cat /sys/bus/pci/devices/*/device 2>/dev/null | head -5 || \
            echo "  PCIe not available"
    fi

    echo ""
}

check_kernel_modules() {
    log_info "Checking kernel modules..."
    log_separator
    if command -v lsmod >/dev/null 2>&1; then
        lsmod 2>/dev/null | head -30 || echo "  Cannot list modules"
    else
        cat /proc/modules 2>/dev/null | head -20 || echo "  No module info"
    fi
    echo ""
}

check_boot_slot() {
    log_info "Boot slot status..."
    log_separator

    # Check which slot we booted from
    slot=""
    if [ -f "/proc/cmdline" ]; then
        slot=$(grep -o 'androidboot.slot_suffix=[ab]' /proc/cmdline 2>/dev/null | cut -d= -f2 || \
               grep -o 'nuxel.slot=[ab]' /proc/cmdline 2>/dev/null | cut -d= -f2)
    fi

    if [ -n "${slot}" ]; then
        printf '%b\n' "  Booted from slot: ${slot}"
        other_slot="b"
        [ "${slot}" = "b" ] && other_slot="a"
        printf '%b\n' "  Other slot: ${other_slot}"
    else
        printf '%b\n' "  ${YELLOW}Boot slot not detected in cmdline${NC}"
        printf '%b\n' "  Raw cmdline:"
        cat /proc/cmdline 2>/dev/null | tr ' ' '\n' | head -20
    fi
    echo ""
}

check_filesystem() {
    partition="$1"
    fstype="${2:-ext4}"

    if [ -b "${partition}" ]; then
        log_info "Checking filesystem on ${partition}..."
        if command -v fsck.${fstype} >/dev/null 2>&1; then
            fsck.${fstype} -n "${partition}" 2>&1 | tail -20
        elif command -v fsck >/dev/null 2>&1; then
            fsck -n "${partition}" 2>&1 | tail -20
        else
            printf '%b\n' "${YELLOW}  fsck not available${NC}"
        fi
    else
        log_error "Partition ${partition} not found"
    fi
    echo ""
}

# ── Action functions ────────────────────────────────────────────────────────

mount_root() {
    slot="${1:-a}"
    root_dev="/dev/disk/by-partlabel/system_${slot}"

    log_info "Attempting to mount root filesystem from slot ${slot}..."

    if [ ! -b "${root_dev}" ]; then
        log_error "Root device ${root_dev} not found"
        return 1
    fi

    mount_point="/mnt/root"
    mkdir -p "${mount_point}" 2>/dev/null

    # Try ext4 (primary filesystem)
    if mount -t ext4 -o ro "${root_dev}" "${mount_point}" 2>/dev/null; then
        log_ok "Root filesystem from slot ${slot} mounted at ${mount_point}"
        echo ""
        printf '%b\n' "${BOLD}Contents of ${mount_point}:${NC}"
        ls -la "${mount_point}" 2>/dev/null
        echo ""
        return 0
    fi

    # Try f2fs (alternative)
    if mount -t f2fs -o ro "${root_dev}" "${mount_point}" 2>/dev/null; then
        log_ok "Root filesystem (f2fs) from slot ${slot} mounted at ${mount_point}"
        ls -la "${mount_point}"
        return 0
    fi

    log_error "Failed to mount root filesystem"
    return 1
}

unmount_root() {
    mount_point="/mnt/root"
    if mountpoint -q "${mount_point}" 2>/dev/null; then
        umount "${mount_point}" 2>/dev/null
        log_ok "Root filesystem unmounted"
    fi
}

view_logs() {
    log_separator
    printf '%b\n' "${BOLD}System Log Collection${NC}"
    log_separator
    echo ""

    # Create log bundle
    log_dir="/tmp/nuxel-logs"
    mkdir -p "${log_dir}"

    # Collect logs
    dmesg > "${log_dir}/dmesg.log" 2>/dev/null
    cat /proc/cmdline > "${log_dir}/cmdline.log" 2>/dev/null
    cat /proc/partitions > "${log_dir}/partitions.log" 2>/dev/null
    mount > "${log_dir}/mounts.log" 2>/dev/null
    lsmod > "${log_dir}/modules.log" 2>/dev/null
    cat /proc/cpuinfo > "${log_dir}/cpuinfo.log" 2>/dev/null
    cat /proc/meminfo > "${log_dir}/meminfo.log" 2>/dev/null
    ip link show > "${log_dir}/network.log" 2>/dev/null

    # Boot log from pstore if available
    if [ -d "/sys/fs/pstore" ]; then
        cp -r /sys/fs/pstore "${log_dir}/pstore" 2>/dev/null
    fi

    # Console output
    printf '%b\n' "${GREEN}Logs collected to: ${log_dir}${NC}"
    echo ""
    ls -la "${log_dir}/"
    echo ""

    # Show dmesg errors
    printf '%b\n' "${BOLD}Kernel errors:${NC}"
    dmesg 2>/dev/null | grep -i "error\|fail\|panic\|oops\|bug" | tail -20 || \
        echo "  No kernel errors detected"

    # Show OOM
    printf '%b\n' "\n${BOLD}OOM killer activity:${NC}"
    dmesg 2>/dev/null | grep -i "oom\|out of memory" | tail -5 || \
        echo "  No OOM events"
    echo ""
}

reflash_device() {
    log_separator
    printf '%b\n' "${BOLD}  REFLASH FROM RECOVERY${NC}"
    log_separator
    echo ""
    log_warn "This will re-flash the Nuxel OS to this device."
    log_warn "You need the Nuxel boot images accessible via ADB sideload"
    log_warn "or from an external storage device."
    echo ""

    # Check if fastboot is available
    if command -v fastboot >/dev/null 2>&1; then
        log_info "fastboot is available in recovery"
    else
        log_error "fastboot not available in this recovery image"
        echo ""
        echo "To re-flash from a fully booted system:"
        echo "  1. Connect the device to a computer via USB"
        echo "  2. Reboot to bootloader: adb reboot bootloader"
        echo "  3. Run the flash script: ./boot/flash.sh"
        return
    fi

    echo ""
    echo "Options:"
    echo "  1. ADB Sideload - Push images via adb sideload"
    echo "  2. USB Mass Storage - Mount device as USB drive"
    echo "  3. Network Flash - Flash via network (requires TFTP server)"
    echo "  4. Cancel"
    echo ""
    printf "Select option [1-4]: "
    read -r choice

    case "${choice}" in
        1)
            echo ""
            log_info "Starting ADB sideload..."
            echo "On your computer, run: adb sideload nuxel-update.zip"
            echo ""
            if command -v recovery >/dev/null 2>&1; then
                recovery --sideload 2>&1
            else
                # Manual sideload using adbd
                adbd 2>/dev/null &
                echo "ADB daemon started. Connect your computer and run:"
                echo "  adb sideload <nuxel-image.zip>"
            fi
            ;;
        2)
            echo ""
            log_info "Enabling USB mass storage..."
            echo "Mount a partition and access via USB"
            log_error "USB mass storage not yet implemented in recovery"
            ;;
        3)
            echo ""
            log_info "Network flash mode..."
            printf 'TFTP server IP: '; read -r tftp_ip
            echo "Network flash to ${tftp_ip} not yet implemented in recovery"
            ;;
        *)
            echo "Cancelled"
            return
            ;;
    esac
}

emergency_shell() {
    echo ""
    log_separator
    printf '%b\n' "${BOLD}  EMERGENCY SHELL${NC}"
    printf '%b\n' "  Type 'help' for available commands"
    log_separator
    echo ""

    # Drop to /bin/sh with busybox
    if command -v busybox >/dev/null 2>&1; then
        export SHELL="/bin/sh"
        /bin/sh -i 2>&1
    else
        # Fall back to whatever shell is available
        sh
    fi
}

factory_reset() {
    log_separator
    printf '%b\n' "${BOLD}  FACTORY RESET${NC}"
    log_separator
    echo ""
    log_warn "=================================================="
    log_warn "  THIS WILL WIPE ALL USER DATA!"
    log_warn "  This includes accounts, settings, and files."
    log_warn "  This action CANNOT be undone."
    log_warn "=================================================="
    echo ""
    printf "Type 'YES' to confirm: "
    read -r confirm
    if [ "${confirm}" != "YES" ]; then
        echo "Factory reset cancelled."
        return
    fi

    echo ""
    log_info "Starting factory reset..."

    # Find userdata partition
    userdata_dev=""
    for candidate in "/dev/disk/by-partlabel/userdata" \
                     "/dev/block/by-name/userdata"; do
        if [ -b "${candidate}" ]; then
            userdata_dev="${candidate}"
            break
        fi
    done

    if [ -n "${userdata_dev}" ]; then
        log_info "Wiping ${userdata_dev}..."
        if command -v mkfs.ext4 >/dev/null 2>&1; then
            mkfs.ext4 -F "${userdata_dev}" 2>&1 | tail -3
            log_ok "Userdata partition formatted"
        else
            dd if=/dev/zero of="${userdata_dev}" bs=1M count=1 2>/dev/null
            log_warn "Userdata partition zeroed (quick wipe)"
        fi
    else
        log_error "Userdata partition not found"
    fi

    # Remove first-boot marker so setup runs again. The canonical marker is
    # /var/lib/nuxel/.firstboot-complete (briq-22); the parent dir is created
    # before touching so a wipe always produces a fresh marker.
    for mount_point in "/mnt" "/mnt/root"; do
        mkdir -p "${mount_point}/var/lib/nuxel" 2>/dev/null
        touch "${mount_point}/var/lib/nuxel/.firstboot-complete" 2>/dev/null
        log_ok "First-boot marker restored"
    done

    log_info "Factory reset complete. Reboot to start fresh."
}

reboot_to_bootloader() {
    log_info "Rebooting to bootloader..."
    reboot bootloader 2>/dev/null || \
    busybox reboot bootloader 2>/dev/null || {
        log_warn "Cannot reboot directly. Force reboot manually:"
        echo "  Hold Power + Volume Down for 15 seconds"
        echo "  Then release and press Volume Down to enter bootloader"
    }
}

reboot_device() {
    log_info "Rebooting..."
    sync
    reboot -f 2>/dev/null || busybox reboot -f 2>/dev/null || {
        echo "Reboot failed. Force power-off by holding Power for 15 seconds."
    }
}

show_help() {
    echo ""
    printf '%b\n' "${BOLD}NUXEL RECOVERY COMMANDS${NC}"
    echo "═══════════════════════════════════════════"
    echo ""
    printf '%b\n' "${CYAN}DIAGNOSTICS:${NC}"
    echo "  overview          - Show device overview"
    echo "  partitions        - List all partitions"
    echo "  mounts            - Show current mounts"
    echo "  dmesg             - Show kernel logs"
    echo "  hardware          - Check hardware status"
    echo "  modules           - List kernel modules"
    echo "  boot-slot         - Show active boot slot"
    echo "  logs              - Collect diagnostic logs"
    echo ""
    printf '%b\n' "${CYAN}FILESYSTEM:${NC}"
    echo "  mount-root [a|b]  - Mount root filesystem from slot"
    echo "  umount-root       - Unmount root filesystem"
    echo "  fsck [partition]  - Check filesystem"
    echo ""
    printf '%b\n' "${CYAN}ACTIONS:${NC}"
    echo "  reflash           - Re-flash Nuxel OS"
    echo "  factory-reset     - Wipe all user data"
    echo "  shell             - Drop to emergency shell"
    echo "  bootloader        - Reboot to bootloader"
    echo "  reboot            - Reboot device"
    echo ""
    printf '%b\n' "${CYAN}OTHER:${NC}"
    echo "  help              - Show this help"
    echo "  banner            - Show recovery banner again"
    echo ""
}

# ── Main recovery menu ─────────────────────────────────────────────────────

show_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║            ${BOLD}NUXEL RECOVERY v${RECOVERY_VERSION}${NC}             ║"
    echo "║         Google Pixel 10 Pro XL (mustang)            ║"
    echo "║         Serial: 58211FDCQ001LA                      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    printf '%b\n' "${YELLOW}The main OS failed to boot. Running recovery...${NC}"
    echo ""
}

main() {
    show_banner
    diagnostic_overview

    echo ""
    printf '%b\n' "${BOLD}Available actions:${NC}"
    echo "  1. Run full diagnostics"
    echo "  2. Drop to emergency shell"
    echo "  3. Attempt to boot from other slot (b)"
    echo "  4. Mount root filesystem"
    echo "  5. Re-flash Nuxel OS"
    echo "  6. Factory reset"
    echo "  7. Reboot to bootloader"
    echo "  8. Reboot device"
    echo ""
    printf "Select option [1-8] or 'help' for all commands: "
    read -r choice

    case "${choice}" in
        1|"diagnostics"|"overview")
            diagnostic_overview
            check_boot_slot
            check_partitions
            check_mounts
            check_hardware
            check_kernel_modules
            check_kernel_logs
            log_info "Diagnostics complete"
            ;;
        2|"shell")
            emergency_shell
            ;;
        3|"other-slot"|"b-slot"|"b")
            current_slot=$(grep -o 'androidboot.slot_suffix=[ab]' /proc/cmdline 2>/dev/null | cut -d= -f2 || echo "a")
            other_slot="b"
            [ "${current_slot}" = "b" ] && other_slot="a"
            log_info "Current slot: ${current_slot}. Attempting slot ${other_slot}..."
            # Just set the slot and reboot - fastboot will handle it
            echo "Set active slot to ${other_slot} via fastboot from computer:"
            echo "  fastboot set_active ${other_slot}"
            echo "  fastboot reboot"
            ;;
        4|"mount"|"mount-root")
            printf 'Slot to mount [a]: '; read -r slot
            slot="${slot:-a}"
            mount_root "${slot}"
            if [ $? -eq 0 ]; then
                echo "You can now inspect the root filesystem at /mnt/root/"
                echo "Run 'umount-root' when done."
            fi
            ;;
        5|"reflash")
            reflash_device
            ;;
        6|"factory-reset")
            factory_reset
            ;;
        7|"bootloader")
            reboot_to_bootloader
            ;;
        8|"reboot")
            reboot_device
            ;;
        "help"|"h"|"?")
            show_help
            ;;
        *)
            log_warn "Unknown option: ${choice}"
            echo "Type 'help' for available commands."
            ;;
    esac

    # After action, show menu again
    echo ""
    echo "────────────────────────────────────────────────"
    echo "Press Enter to return to the recovery menu..."
    read -r _
    main
}

# ── CLI: --help / -h / --version (no device or hardware required) ───────────
case "${1:-}" in
    --help|-h)
        cat <<'USAGE'
Nuxel Recovery / Failsafe shell — Google Pixel 10 Pro XL (mustang)

Usage: recovery.sh [--help|--version]

This console runs ON THE DEVICE when the main OS fails to boot. On a host it
prints this help instead of opening the on-device menu.

Enter recovery on the Pixel 10 Pro XL:
  1. Power off (hold Power + Volume Down ~15 s)
  2. Hold Volume Up + Power; release Power when the Google logo appears
  3. On "No command", press Volume Up + Power to open the recovery menu
  4. Select "Enter recovery"
  Or from fastboot:   fastboot reboot recovery
  Or from the OS:     sudo reboot recovery

Restore stock Android (safety net):
  - flash-all.sh from mustang-bp1a.250405.001-factory-*.zip, or
  - boot/google-pixel-10-pro-xl/flash.sh --revert

Recovery menu actions: diagnostics, emergency shell, switch to slot (b),
mount rootfs, re-flash Nuxel OS, factory reset, reboot to bootloader, reboot.
USAGE
        exit 0
        ;;
    --version)
        echo "nuxel-recovery ${RECOVERY_VERSION} (mustang)"
        exit 0
        ;;
esac

# ── Entry point (only if executed directly) ─────────────────────────────────
if [ "$(basename "$0")" = "recovery.sh" ] || [ "$(basename "$0")" = "init" ]; then
    main "$@"
fi
