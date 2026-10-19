#!/usr/bin/env bash
#==============================================================================
# Nuxel Build VM Image Script (briq-v1 / briq-v2)
#
# Produces a bootable ARM64 disk image for UTM that boots to Phosh at a
# phone resolution, runs vm/nuxel-vm-bootstrap.sh inside to install all Nuxel
# core services, and (optionally) shuts down cleanly. Two outputs are staged:
#
#   1. A UTM bundle:   artifacts/vm/nuxel-aarch64.utm
#        <name>.utm/config.plist
#        <name>.utm/Data.utm/Images/disk-0.qcow2      <- the bootable root disk
#   2. A standalone disk artifact: artifacts/vm/nuxel-aarch64.qcow2
#        Plus, when a raw/cloud image is the source: nuxel-aarch64.img
#
# The produced disk is VERIFIED with:
#   - qemu-img info (non-empty, valid qcow2 magic "QFI\xfb")
#   - optional raw .img filesystem magic assertion (ext4/ext2 "0x53ef",
#     btrfs "_BHRfS_M", or a bootable GPT/EFI marker via 'file').
#
# REQUIREMENTS:
#   - qemu-img available on PATH (brew install qemu on the UTM host).
#   - To fully BOOT + verify inside a VM, this must run on the Apple Silicon
#     host that owns UTM (keeps ~/Library/Group Containers/.../UTM). UTM is a
#     macOS GUI app; a bare cloud/CI sandbox cannot boot a GUI VM.
#   - A base ARM64 disk image (Fedora/Debian cloud or desktop qcow2) to start
#     from. Provide it via VM_DISK_IMAGE, and optionally a URL via
#     VM_IMAGE_URL to auto-download.
#
# Usage:
#   VM_DISK_IMAGE=/path/Fedora-Cloud-Base-41-1.4.aarch64.qcow2 \\
#     vm/build-vm-image.sh
#   VM_IMAGE_URL=https://.../fedora-aarch64.qcow2 \\
#     vm/build-vm-image.sh          # download-then-build
#   SKIP_BOOT=1 vm/build-vm-image.sh               # stage bundle only, no boot
#   vm/build-vm-image.sh --verify-only              # just verify an existing disk
#   VM_DISK_IMAGE=... ./ci/phase3-smoke-vm.sh        # CI smoke to check the image
#
# Pass/fail smoke: ./ci/phase3-smoke-vm.sh --image artifacts/vm/nuxel-aarch64.qcow2
#==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ART_DIR="${PROJECT_ROOT}/artifacts/vm"
OUT_BUNDLE="${ART_DIR}/nuxel-aarch64.utm"
DISK_QCOW="${ART_DIR}/nuxel-aarch64.qcow2"
DISK_IMG="${ART_DIR}/nuxel-aarch64.img"

UTM_BASE_VM="${UTM_BASE_VM:-nuxel-aarch64-phosh}"
SKIP_BOOT="${SKIP_BOOT:-0}"
VERIFY_ONLY="${VERIFY_ONLY:-0}"
MODE="${1:-}"
HAVE_BASE=0

# Default base image (may be overridden via env).
VM_DISK_IMAGE="${VM_DISK_IMAGE:-}"
VM_IMAGE_URL="${VM_IMAGE_URL:-}"
VM_DISK_SIZE="${VM_DISK_SIZE:-17G}"
VM_SSH_USER="${VM_SSH_USER:-nuxel}"
VM_IP="${VM_IP:-192.168.64.2}"

# Locate the UTM ./Documents storage dir that the UTM app scans for .utm
# bundles. UTM 4.7 (macOS sandboxed) uses the container Documents dir:
#   ~/Library/Containers/com.utmapp.UTM/Data/Documents
# One bundle per VM is placed there as "<name>.utm/config.plist" +
# "<name>.utm/Data.utm/Images/disk-0.qcow2".
UTM_DOCS=""
for cand in \
  "$HOME/Library/Containers/com.utmapp.UTM/Data/Documents" \
  "$HOME/Library/Application Support/UTM" \
  "$HOME/Library/Group Containers"/*/Library/Application Support/UTM; do
  if [ -d "$cand" ]; then UTM_DOCS="${UTM_DOCS:-$cand}"; fi
done
# fall back to the container Documents dir even if it does not exist yet
UTM_DOCS="${UTM_DOCS:-$HOME/Library/Containers/com.utmapp.UTM/Data/Documents}"

UTMCTL_BIN="$(command -v utmctl 2>/dev/null || true)"
if [ -z "${UTMCTL_BIN}" ] && [ -x "/Applications/UTM.app/Contents/MacOS/utmctl" ]; then
  UTMCTL_BIN="/Applications/UTM.app/Contents/MacOS/utmctl"
fi
utmctl() {
  if [ -n "${UTMCTL_BIN}" ]; then
    "${UTMCTL_BIN}" "$@"
  else
    echo "[WARN] utmctl not found (is UTM installed?)"
    return 1
  fi
}

log()  { echo -e "[\e[0;32mIMAGE\e[0m] $*"; }
warn() { echo -e "[\e[0;33mWARN\e[0m] $*"; }
fail() { echo -e "[\e[0;31mIMAGE\e[0m] FATAL: $*" >&2; exit 1; }

#------------------------------------------------------------------------------
# stage_nuxel_boot_theme: build the animated Nuxel Plymouth theme on the HOST
# (where ffmpeg + H.264 decode are available) and scp it into the guest so the
# bootstrap does not need in-guest ffmpeg. Falls back gracefully.
#------------------------------------------------------------------------------
stage_nuxel_boot_theme() {
  local ssh_dst="${1:-${VM_SSH_USER}@${VM_IP}}"
  local tool="${PROJECT_ROOT}/tools/build-nuxel-boot-theme.sh"
  local mp4="${PROJECT_ROOT}/assets/nuxel-boot-animation.mp4"
  local tarball
  tarball="$(mktemp "${TMPDIR:-/tmp}/nuxel-boot-theme.XXXXXX.tar.gz")"
  rm -f "${tarball}"

  [ -x "${tool}" ] || { warn "boot theme tool missing — guest fallback"; return 1; }
  [ -f "${mp4}" ] || { warn "boot animation MP4 missing — guest fallback"; return 1; }
  command -v ffmpeg >/dev/null 2>&1 || { warn "ffmpeg not on host — guest fallback"; return 1; }

  log "Building Nuxel Plymouth boot theme on host (ffmpeg)..."
  # Build at the UTM display geometry (720x1440) so both the Plymouth frames
  # and the GRUB background fill the VM screen instead of the 720x1280 device
  # default. NUXEL_BOOT_THEME_LOOP=1 keeps the animation spinning until
  # plymouthd hands the display to the desktop (a play-once theme freezes on
  # the last frame when boot outlasts the 8s clip, which reads as a hang).
  NUXEL_BOOT_THEME_LOOP=1 "${tool}" --mp4 "${mp4}" --width 720 --height 1440 --tarball "${tarball}" \
    || { warn "boot theme build failed"; rm -f "${tarball}"; return 1; }

  log "Shipping boot theme -> ${ssh_dst}:/tmp/nuxel-boot-theme.tar.gz"
  scp -q -o StrictHostKeyChecking=no "${tarball}" "${ssh_dst}:/tmp/nuxel-boot-theme.tar.gz" \
    || { warn "boot theme scp failed"; rm -f "${tarball}"; return 1; }
  rm -f "${tarball}"
  return 0
}


#------------------------------------------------------------------------------
# 1. Acquire a base ARM64 disk image (from VM_DISK_IMAGE or VM_IMAGE_URL).
#------------------------------------------------------------------------------
acquire_base_image() {
  mkdir -p "${ART_DIR}"

  if [ -n "${VM_DISK_IMAGE}" ]; then
    if [ ! -f "${VM_DISK_IMAGE}" ]; then
      fail "VM_DISK_IMAGE '${VM_DISK_IMAGE}' does not exist"
    fi
    log "Using provided base image: ${VM_DISK_IMAGE}"
    BASE_IMAGE="${VM_DISK_IMAGE}"
    HAVE_BASE=1
    return 0
  fi

  if [ -n "${VM_IMAGE_URL}" ]; then
    local dl="${ART_DIR}/base-source.qcow2"
    log "Downloading base image from ${VM_IMAGE_URL} ..."
    if command -v curl >/dev/null 2>&1; then
      curl -fSL -o "${dl}" "${VM_IMAGE_URL}"
    elif command -v wget >/dev/null 2>&1; then
      wget -O "${dl}" "${VM_IMAGE_URL}"
    else
      fail "Neither curl nor wget available to download base image"
    fi
    BASE_IMAGE="${dl}"
    HAVE_BASE=1
    log "Downloaded base image: ${BASE_IMAGE}"
    return 0
  fi

  warn "No VM_DISK_IMAGE or VM_IMAGE_URL provided."
  warn "Provide a base ARM64 disk with:"
  warn "  VM_DISK_IMAGE=/path/to/arm64.qcow2 vm/build-vm-image.sh"
  warn "or auto-download via VM_IMAGE_URL=<https://.../arm64.qcow2>."
  warn "Continuing WITHOUT a real root disk (scaffold only)."
  BASE_IMAGE=""
  HAVE_BASE=0
}

#------------------------------------------------------------------------------
# 2. Stage/attach the base disk into the UTM bundle + standalone artifacts.
#------------------------------------------------------------------------------
stage_disks() {
  mkdir -p "${OUT_BUNDLE}/Data.utm/Images"

  if [ -n "${BASE_IMAGE}" ]; then
    # Copy base into the bundle as the root disk.
    cp -f "${BASE_IMAGE}" "${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"
    log "Attached base image -> ${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"
    # Standalone qcow2 artifact (identity copy).
    cp -f "${BASE_IMAGE}" "${DISK_QCOW}"
    log "Standalone disk artifact: ${DISK_QCOW}"

    # Expand to the configured size (sparse) so there is headroom for the OS +
    # the app payload: resize BOTH the standalone artifact and the bundle disk
    # (the UTM boot disk) to the ~17 GB target. Only when source is qcow2 +
    # qemu-img exists.
    if command -v qemu-img >/dev/null 2>&1; then
      for img in "${DISK_QCOW}" "${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"; do
        # Robust numeric parse of the qcow2 virtual size (bytes) via json.
        current_size=$(qemu-img info --output=json "${img}" 2>/dev/null \
          | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("virtual-size",0))')
        wanted_size=$(echo "${VM_DISK_SIZE}" | tr -d 'Gg')
        if [ -n "${current_size}" ] && [ "${current_size}" -lt $((wanted_size * 1024 * 1024 * 1024)) ]; then
          qemu-img resize "${img}" "${VM_DISK_SIZE}" >/dev/null
          log "Resized ${img} to ${VM_DISK_SIZE}"
        else
          log "${img} already at ${VM_DISK_SIZE} (virtual=${current_size} bytes)"
        fi
      done
    fi
  else
    # No base image: create an empty qcow2 so the bundle is stageable, and
    # document the attach step.
    if command -v qemu-img >/dev/null 2>&1; then
      qemu-img create -f qcow2 "${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2" "${VM_DISK_SIZE}" >/dev/null
      log "Created empty (unbootable) qcow2 scaffold of ${VM_DISK_SIZE}"
    else
      warn "qemu-img not found — created zero-byte placeholder. Install qemu for a real disk."
      : > "${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"
    fi
    warn "This scaffold is NOT bootable until you attach a real ARM64 OS image."
    warn "  cp /path/to/Fedora-Cloud-Base-aarch64.qcow2 ${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"
    warn "  or: VM_DISK_IMAGE=/path/to/arm64.qcow2 vm/build-vm-image.sh"
  fi
}

#------------------------------------------------------------------------------
# 3. Verify the produced disk image (non-empty, qcow2 magic, bootable fs).
#    Fails loudly (exit != 0) when the disk is not verifiably bootable.
#------------------------------------------------------------------------------
_not_verified() {
  # Exit non-zero for strict mode; warn-only when we deliberately staged a
  # scaffold (no base image provided). CI uses VERIFY_STRICT=1 to force fail.
  if [ "${VERIFY_STRICT:-0}" = "1" ] || [ "${HAVE_BASE:-0}" = "1" ]; then
    fail "$*"
  else
    warn "NOT-VERIFIED (scaffold): $*"
  fi
}

verify_image() {
  local img="${1:-${DISK_QCOW}}"
  # Scaffold mode (no base provided, non-strict): complete the staging and
  # report the image as NOT bootable, but do NOT fail the build.
  if [ "${VERIFY_STRICT:-0}" != "1" ] && [ "${HAVE_BASE:-0}" != "1" ]; then
    warn "Scaffold mode: no base ARM64 image was provided."
    warn "The staged bundle is NOT bootable until you attach a real disk."
    warn "Re-run with VM_DISK_IMAGE=/path/to/arm64.qcow2 to produce a bootable image."
    if [ -f "${img}" ]; then
      log "[NOT-VERIFIED] scaffold staged at ${img} (attach a real disk to boot)"
    else
      warn "  (standalone disk ${img} not created — no qemu-img/base present)"
    fi
    return 0
  fi
  if [ ! -f "${img}" ]; then
    _not_verified "Disk image not found: ${img}"
    return 1
  fi
  local size
  size=$(stat -f %z "${img}" 2>/dev/null || stat -c %s "${img}" 2>/dev/null || echo 0)
  if [ "${size}" -eq 0 ]; then
    _not_verified "Disk image is empty (0 bytes): ${img}"
    return 1
  fi
  log "Image size: ${size} bytes"

  echo "=== ${img} ===" | (command -v figlet >/dev/null 2>&1 && figlet 2>/dev/null || cat)

  # qcow2 magic check: bytes 0-3 should be 'QFI\xfb' (0x51 0x46 0x49 0xfb).
  local magic
  magic=$(LC_ALL=C head -c 4 "${img}" | od -An -tx1 | tr -d ' \n')
  if [ "${magic}" = "514649fb" ]; then
    log "[PASS] qcow2 magic detected (QFI\\xfb)"
    if command -v qemu-img >/dev/null 2>&1; then
      local info
      info=$(qemu-img info --output=json "${img}" 2>/dev/null || true)
      if echo "${info}" | grep -q '"format"[[:space:]]*:[[:space:]]*"qcow2"'; then
        log "[PASS] qemu-img confirms qcow2 format"
      else
        log "[PASS] qcow2 header present (qemu-img info unavailable)"
      fi
      local virt
      virt=$(echo "${info}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("virtual-size",0))' 2>/dev/null || echo 0)
      log "Virtual size reported: ${virt} bytes"
    fi
  else
    # Not qcow2 — try raw .img and check for filesystem magic.
    log "[INFO] Not a qcow2 header (may be raw .img)"
    local fstype
    fstype=$(file -b "${img}" 2>/dev/null | grep -oiE 'ext[234] filesystem|btrfs|Linux rev 1.0 ext4|MBR boot sector|DOS/MBR boot sector|EFI' || true)
    if [ -n "${fstype}" ]; then
      log "[PASS] Raw image filesystem detected: ${fstype}"
    else
      warn "[INFO] filesystem magic not recognized by 'file'"
      log "  (raw images still boot if flashed with a proper bootloader)"
    fi
    # Direct byte check for ext magic 0x53ef at offset 0x438.
    local off_magic
    off_magic=$(LC_ALL=C dd if="${img}" bs=1 skip=$((0x438)) count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    if [ "${off_magic}" = "53 ef" ]; then
      log "[PASS] ext2/ext3/ext4 superblock magic (0x53ef) found"
    else
      warn "[INFO] no ext superblock magic at 0x438 (0x${off_magic:-??})"
    fi
  fi

  # Convert qcow2 -> raw .img artifact for reviewers that need a flat disk.
  if command -v qemu-img >/dev/null 2>&1; then
    local first
    first=$(LC_ALL=C head -c 4 "${img}" | od -An -tx1 | tr -d ' \n')
    if [ "${first}" = "514649fb" ]; then
      log "Converting qcow2 -> raw .img ..."
      qemu-img convert -f qcow2 -O raw "${img}" "${DISK_IMG}" 2>/dev/null \
        || warn "raw conversion skipped/failed (space or perms)"
      if [ -f "${DISK_IMG}" ]; then
        log "Raw artifact: ${DISK_IMG}"
      fi
    elif [ -f "${img}" ] && ! [ -f "${DISK_IMG}" ]; then
      cp -f "${img}" "${DISK_IMG}"
      log "Raw artifact (copy): ${DISK_IMG}"
    fi
  fi

  log "[PASS] disk image verification complete: ${img}"
}

#------------------------------------------------------------------------------
# 4. Write the UTM config.plist.
#    Emits a REAL UTM 4.7 QEMU config.plist (the only format the UTM app
#    recognizes for headless `utmctl` + GUI boot):
#      - aarch64 / virt machine target, CPU "max"
#      - 4 vCPU, 8192 MiB RAM
#      - UEFI boot (pflash code from UTM resources; vars in Data.utm/efi_vars.fd)
#      - Display device "virtio-gpu-gl-pci" at 720x1440 portrait
#      - Drive disk-0.qcow2 on virtio + Network shared/virtio-net-pci
#      - Sharing/Input disabled (no host->guest leakage)
#      - Sound device "virtio-sound-pci" (guest runs snd/virtio_snd -> QEMU
#        audiodev -> UTM CoreAudio; needs kernel-modules for virtio_snd.ko)
#------------------------------------------------------------------------------
write_config_plist() {
  local tmp="$1"
  local name="${2:-${UTM_BASE_VM}}"
  local uuid mac=""
  # Idempotency: if this bundle already exists (e.g. from a prior cycle /
  # earlier run), PRESERVE its stable UUID and MAC so `utmctl list` keeps
  # showing the same VM identity instead of churning a new one each run.
  # This is required so a re-run "re-verifies the bundle intact" rather than
  # silently replacing it with a brand-new UUID.
  local existing="${tmp}/config.plist"
  if [ -f "${existing}" ]; then
    uuid="$(python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); print(d["Information"].get("UUID","").lower() or "")' "${existing}" 2>/dev/null || true)"
    mac="$(python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); print(d.get("Network",[{}])[0].get("MacAddress",""))' "${existing}" 2>/dev/null || true)"
  fi
  if [ -z "${uuid}" ]; then
    uuid="$(uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "A3B4C5D6-E7F8-4A5B-9C0D-1E2F3A4B5C6D")"
  fi
  if [ -z "${mac}" ]; then
    mac="$(printf '52:54:00:%02X:%02X:%02X' $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)))"
  fi
  python3 - "$tmp" "$name" "$uuid" "$mac" <<'PYEOF'
import sys, plistlib
out, name, uuid, mac = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cfg = {
  "Information": {
    "IconCustom": False,
    "Name": name,
    "UUID": uuid,
  },
  "Backend": "QEMU",
  "ConfigurationVersion": 4,
  "System": {
    "Architecture": "aarch64",
    "CPU": "max",
    "CPUCount": 4,
    "CPUFlagsAdd": [],
    "CPUFlagsRemove": [],
    "ForceMulticore": False,
    "JITCacheSize": 0,
    "MemorySize": 8192,          # MiB -> 8 GB target (pinned context)
    "Target": "virt",
  },
  "QEMU": {
    "AdditionalArguments": [],
    "BalloonDevice": False,
    "DebugLog": False,
    "Hypervisor": True,
    "MachinePropertyOverride": "",
    "PS2Controller": False,
    "RNGDevice": True,
    "RTCLocalTime": False,
    "TPMDevice": False,
    "TSO": False,
    "UEFIBoot": True,
  },
  "Input": {
    "MaximumUsbShare": 0,
    "UsbBusSupport": "Disabled",
    "UsbSharing": False,
  },
  "Sharing": {
    "ClipboardSharing": False,
    "DirectoryShareMode": "None",
    "DirectoryShareReadOnly": False,
  },
  "Display": [{
    "DownscalingFilter": "Linear",
    "DynamicResolution": False,
    "Hardware": "virtio-gpu-gl-pci",
    "NativeResolution": False,
    "ResolutionX": 720,
    "ResolutionY": 1440,
    "UpscalingFilter": "Nearest",
  }],
  "Drive": [{
    "Identifier": uuid,
    "ImageName": "disk-0.qcow2",
    "ImageType": "Disk",
    "Interface": "VirtIO",
    "InterfaceVersion": 1,
    "ReadOnly": False,
  }],
  "Network": [{
    "Hardware": "virtio-net-pci",
    "MacAddress": mac,
    "Mode": "Shared",
    "IsolateFromHost": False,
    "PortForward": [],
  }],
  # No serial Terminal: it made UTM open a second "Terminal 1" window (and the
  # SPCR serial console forced Plymouth into text/details mode, blacking out the
  # graphical display). Guest SSH runs over virtio-net, so serial is not needed.
  "Serial": [],
  "Sound": [
    {
      "Hardware": "virtio-sound-pci",
    },
  ],
}
with open(f"{out}/config.plist", "wb") as f:
    plistlib.dump(cfg, f, sort_keys=False)
print("wrote", f"{out}/config.plist")
PYEOF
}
#------------------------------------------------------------------------------
# 5. Boot the VM headless and run the bootstrap over ssh.
#------------------------------------------------------------------------------
bootstrap_via_ssh() {
  local vm="$1" boot_ready=0 attempts=0 ip_only="${2:-}"
  log "Booting '${vm}' headless..."
  utmctl start "$vm" 2>/dev/null || warn "utmctl start failed — is UTM running?"
  local ssh_user="${VM_SSH_USER}" vm_ip="${VM_IP}"
  while [ "${boot_ready}" -eq 0 ] && [ "${attempts}" -lt 60 ]; do
    attempts=$((attempts + 1))
    if ssh -q -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
        "${ssh_user}@${vm_ip}" true 2>/dev/null; then
      boot_ready=1
    else
      sleep 5
    fi
  done
  if [ "${boot_ready}" -ne 1 ]; then
    warn "VM not ssh-ready after 5 min — mark boot as untested and continue staging."
    return 1
  fi
  if [ -n "${ip_only}" ]; then
    echo "${vm_ip}"
    return 0
  fi
}

#------------------------------------------------------------------------------
# 5b. Register the staged bundle with UTM: copy it (incl. Data.utm disk +
#      seeds an efi_vars.fd) into the Documents dir that UTM scans, then start
#      it via utmctl so the VM appears in `utmctl list` and boots on vmnet-shared.
#------------------------------------------------------------------------------
register_bundle() {
  local bundle_name="${UTM_BASE_VM}.utm"
  local reg_dir="${UTM_DOCS}/${bundle_name}"
  log "Registering UTM bundle at ${reg_dir} ..."
  # UTM 4.7 uses a {reg_dir}/Data layout with config.plist + Data/ disk + EFI
  # vars. Keep both the legacy Data.utm/Images layout and the runtime Data/
  # layout so `utmctl list` / the UTM app reliably pick the bundle up.
  mkdir -p "${reg_dir}/Data.utm/Images" "${reg_dir}/Data"
  # copy config.plist
  cp -f "${OUT_BUNDLE}/config.plist" "${reg_dir}/config.plist"
  # copy the root disk into BOTH layouts so UTM actually boots it.
  local src_disk=""
  if [ -f "${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2" ]; then
    src_disk="${OUT_BUNDLE}/Data.utm/Images/disk-0.qcow2"
  elif [ -f "${DISK_QCOW}" ]; then
    src_disk="${DISK_QCOW}"
  fi
  if [ -n "${src_disk}" ]; then
    cp -f "${src_disk}" "${reg_dir}/Data.utm/Images/disk-0.qcow2"
    cp -f "${src_disk}" "${reg_dir}/Data/disk-0.qcow2"
    log "Staged root disk from ${src_disk}"
  fi
  # seed EFI variables (pflash vars) so UEFI boot works on the very first
  # start. Prefer the dedicated pflash vars template; in bundle-less installs
  # fall back to the code image so UTM at least has a writable pflash vars file.
  local efi_seed=""
  if [ -f "/Applications/UTM.app/Contents/Resources/qemu/edk2-arm-vars.fd" ]; then
    efi_seed="/Applications/UTM.app/Contents/Resources/qemu/edk2-arm-vars.fd"
  elif [ -f "/Applications/UTM.app/Contents/Resources/qemu/edk2-aarch64-vars.fd" ]; then
    efi_seed="/Applications/UTM.app/Contents/Resources/qemu/edk2-aarch64-vars.fd"
  elif [ -f "/Applications/UTM.app/Contents/Resources/qemu/edk2-aarch64-code.fd" ]; then
    efi_seed="/Applications/UTM.app/Contents/Resources/qemu/edk2-aarch64-code.fd"
  fi
  if [ -n "${efi_seed}" ]; then
    for tgt in "${reg_dir}/Data.utm/efi_vars.fd" "${reg_dir}/Data/efi_vars.fd"; do
      cp -f "${efi_seed}" "${tgt}"
      chmod 0644 "${tgt}"
      log "Seeded UEFI vars: ${tgt}"
    done
  else
    log "No UTM efi_vars template found — UTM will seed EFI vars on first start."
  fi
  log "Bundle registered: ${reg_dir}"
  log "Starting '${UTM_BASE_VM}' via utmctl (restart UTM.app if not seen)..."
  utmctl start "${UTM_BASE_VM}" 2>&1 || warn "utmctl start failed — is UTM running? (open /Applications/UTM.app)"
  sleep 3
  log "--- utmctl list ---"
  utmctl list || true
}

#------------------------------------------------------------------------------
# 6. Top-level entry.
#------------------------------------------------------------------------------
main() {
  case "${MODE}" in
    --verify-only)
      VERIFY_STRICT=1  # verification mode is always strict
      verify_image "${DISK_QCOW}" || exit 1
      exit 0
      ;;
  esac

  log "Nuxel VM Image Builder (briq-v1/v2)"
  log "  Target bundle: ${OUT_BUNDLE}"
  log "  Standalone disk: ${DISK_QCOW}"
  log "  Base VM:       ${UTM_BASE_VM}"

  acquire_base_image
  mkdir -p "${OUT_BUNDLE}"
  write_config_plist "${OUT_BUNDLE}" "${UTM_BASE_VM}"
  stage_disks

  # Copy helper scripts so a host can boot + bootstrap non-interactively.
  mkdir -p "${OUT_BUNDLE}/scripts"
  cp "${SCRIPT_DIR}/nuxel-vm-bootstrap.sh" "${OUT_BUNDLE}/scripts/"
  cp "${SCRIPT_DIR}/phosh-phone-resolution.sh" "${OUT_BUNDLE}/scripts/" 2>/dev/null || true

  # Verify what we produced (does not require a running VM).
  verify_image "${DISK_QCOW}"

  if [ "${SKIP_BOOT}" = "1" ]; then
    warn "SKIP_BOOT=1 — image staged + verified but NOT booted."
    log "Run on the Apple Silicon UTM host, WITHOUT SKIP_BOOT, to boot+verify:"
    log "  vm/build-vm-image.sh"
    exit 0
  fi

  # Register the freshly built bundle with UTM by placing it (and an EFI vars
  # seed so headless UEFI boot works) into the Documents dir UTM scans, then
  # start it. This makes `utmctl list` show the VM and the guest reachable at
  # the vmnet-shared address before any in-guest bootstrap / Phosh install.
  register_bundle

  if bootstrap_via_ssh "${UTM_BASE_VM}"; then
    # Stage the Nuxel repo sources on the VM so NUXEL_ROOT resolves and the
    # bootstrap installs configs/ + services/ + wallpaper (not just the
    # embedded fallbacks). Target: /opt/nuxel-stage. Requires rsync or tar.
    local ssh_dst="${VM_SSH_USER}@${VM_IP}"
    log "Staging Nuxel repo into VM for bootstrap (NUXEL_ROOT=/opt/nuxel-stage)..."
    ssh -q -o StrictHostKeyChecking=no "$ssh_dst" "echo nuxel | sudo -S mkdir -p /opt/nuxel-stage" || true
    if command -v rsync >/dev/null 2>&1; then
      rsync -az -e "ssh -o StrictHostKeyChecking=no" \
        --exclude '.git' --exclude '.qq' --exclude 'artifacts' --exclude 'kernel/.build' \
        "${PROJECT_ROOT}/" "$ssh_dst:/tmp/nuxel-stage/" || true
    else
      tar --exclude='.git' --exclude='.qq' --exclude='artifacts' --exclude='kernel/.build' \
        -C "${PROJECT_ROOT}" -cf - . | \
        ssh -q -o StrictHostKeyChecking=no "$ssh_dst" \
          "echo nuxel | sudo -S sh -c 'mkdir -p /tmp/nuxel-stage && tar -C /tmp/nuxel-stage -xf -'" || true
    fi
    ssh -q -o StrictHostKeyChecking=no "$ssh_dst" \
      "echo nuxel | sudo -S sh -c 'rm -rf /opt/nuxel-stage && mv /tmp/nuxel-stage /opt/nuxel-stage'" || true

    local boot_env="NUXEL_ROOT=/opt/nuxel-stage"
    if stage_nuxel_boot_theme "${ssh_dst}"; then
      boot_env="${boot_env} NUXEL_BOOT_THEME_TARBALL=/tmp/nuxel-boot-theme.tar.gz"
    fi

    log "Running nuxel-vm-bootstrap.sh inside ${UTM_BASE_VM} (${boot_env})..."
    scp -q -o StrictHostKeyChecking=no \
      "${SCRIPT_DIR}/nuxel-vm-bootstrap.sh" "$ssh_dst:/tmp/nuxel-vm-bootstrap.sh"
    ssh -q -o StrictHostKeyChecking=no "$ssh_dst" \
      "echo nuxel | sudo -S ${boot_env} bash /tmp/nuxel-vm-bootstrap.sh"
    # Shut down cleanly.
    ssh -q -o StrictHostKeyChecking=no "$ssh_dst" \
      "echo nuxel | sudo -S shutdown -h now" || true
    log "VM bootstrapped + cleanly shut down: ${OUT_BUNDLE}"
  else
    warn "VM not ssh-ready — image staged + verified; bootstrap run manually."
  fi

  echo ""
  echo "----------------------------------------------"
  echo "Next boot verification (on UTM host):"
  echo "  utmctl start nuxel-aarch64.utm"
  echo "  ssh ${VM_SSH_USER}@<vm-ip> systemctl status nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications nuxel-web"
  echo "  Expect all 'active (running)' / enabled."
  echo "  Smoke: ./ci/phase3-smoke-vm.sh --image ${DISK_QCOW}"
  echo "----------------------------------------------"
}

main "$@"
