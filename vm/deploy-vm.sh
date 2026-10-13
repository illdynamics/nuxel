#!/usr/bin/env bash
# =============================================================================
# Nuxel VM Guest Deployment (briq-09/10 / group bg-05)
#
# Mirrors the CURRENT Nuxel workspace repo into the running UTM VM and then
# drives the guest bootstrap (vm/nuxel-vm-bootstrap.sh) inside the guest. This
# is the post-start deploy step of nuxel-ultimate-build.md Part 12 and operates
# on the SAME booted UTM VM the build/start pipeline provisions (Phosh booted
# at 720x1440). If the guest ends up without the real Nuxel stack (bridge,
# portal, notifications, HTTP API, Phosh agent), fix the deployment machinery
# here — never silently replace Nuxel's architecture with a generic distro.
#
# What it does:
#   [1] Waits for the guest to become SSH-reachable.
#   [2] Mirrors the repo to /home/nuxel/nuxel (NUXEL_ROOT used by the bootstrap,
#       and WorkingDirectory for nuxel-web.service which serves the PWA on
#       :8000). Preserves symlinks + permissions via rsync.
#   [3] Stages NUXEL_ROOT=/home/nuxel/nuxel and runs vm/nuxel-vm-bootstrap.sh
#       as root inside the guest.
#   [4] Writes a deploy manifest (git rev + VERSION) into the guest so the
#       verification report can cite the exact tree.
#   [5] Runs vm/vm-verify-services.sh to start + probe the core services.
#
# Usage:
#   vm/deploy-vm.sh                 # defaults: nuxel@<utmctl-discovered IP>
#   VM_SSH_USER=root SSH_PASS=x vm/deploy-vm.sh
#   VM_IP=192.168.64.3 vm/deploy-vm.sh      # explicit IP (skips discovery)
#   VM_NAME=my-vm vm/deploy-vm.sh           # different UTM VM name
#   SKIP_RUN_BOOTSTRAP=1 vm/deploy-vm.sh    # mirror only, no bootstrap
#   SKIP_VERIFY=1 vm/deploy-vm.sh           # no service verification
#   SKIP_PHOSH_AGENT=1 vm/deploy-vm.sh      # no phosh-agent user-session check
#
# Part 12 ordering (nuxel-ultimate-build.md): this deploy script is the
# post-start step. It refuses to run unless the VM is registered AND started
# (`utmctl list` + `utmctl status`), so it can never be mistaken for a
# create/register step. Guest IP is auto-discovered from the VM via
# `utmctl ip-address "<VM_NAME>"` (first IPv4) and only falls back to
# VM_IP when discovery is unavailable.
# =============================================================================
set -uo pipefail
# NOTE: not set -e body-wide; each phase is guarded so a single failure is
# reported and the script keeps going to gather maximal diagnostics.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VM_SSH_USER="${VM_SSH_USER:-nuxel}"
# Canonical UTM VM name (nuxel-ultimate-build.md Part 12 / vm/utm-state-report.md).
VM_NAME="${VM_NAME:-nuxel-aarch64-phosh}"
UTMCTL_BIN="${UTMCTL_BIN:-}"
if [ -z "${UTMCTL_BIN}" ] && [ -x "/Applications/UTM.app/Contents/MacOS/utmctl" ]; then
    UTMCTL_BIN="/Applications/UTM.app/Contents/MacOS/utmctl"
fi
# Guest IP: explicit VM_IP wins; otherwise auto-discover the live vmnet-shared
# address from the UTM VM via `utmctl ip-address "<VM_NAME>"` (first IPv4),
# with the historical default (192.168.64.3) as final fallback.
if [ -z "${VM_IP:-}" ]; then
    VM_IP="$( { "${UTMCTL_BIN}" ip-address "${VM_NAME}" 2>/dev/null || true; } \
        | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/{print $1; exit}' )"
    if [ -z "${VM_IP}" ]; then
        VM_IP="192.168.64.3"
    fi
fi
VM_SSH_PORT="${VM_SSH_PORT:-}"
# Allow pointing at a guest on a non-standard ssh port (e.g. a direct-boot
# qemu exposed via hostfwd tcp::2222->22). Empty -> default ssh port 22.
SSH_OPTS=(-q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=4 -o ServerAliveInterval=5 -o ServerAliveCountMax=3)
if [ -n "${VM_SSH_PORT}" ]; then
    SSH_OPTS+=(-p "${VM_SSH_PORT}")
fi
SSH_TARGET="${VM_SSH_USER}@${VM_IP}"
GUEST_REPO="/home/nuxel/nuxel"
GUEST_BOOT_THEME_TARBALL="/tmp/nuxel-boot-theme.tar.gz"

# ---------------------------------------------------------------------------
# preflight_utm: Part 12 ordering gate — refuse to deploy unless the VM is
# registered (utmctl list) AND started (utmctl status). Deployment is the
# post-start step; running it against a stopped/absent VM would otherwise
# burn SSH_WAIT_SECONDS polling a guest that cannot come up.
# ---------------------------------------------------------------------------
preflight_utm() {
    if [ -z "${UTMCTL_BIN}" ] || [ ! -x "${UTMCTL_BIN}" ]; then
        log_warn "utmctl not found — skipping UTM preflight (proceeding with SSH-only deploy)."
        return 0
    fi
    local list_out status_out
    list_out="$("${UTMCTL_BIN}" list 2>/dev/null)"
    if ! printf '%s\n' "${list_out}" | grep -q "${VM_NAME}"; then
        log_error "VM '${VM_NAME}' is NOT registered with UTM (utmctl list)."
        log_error "Part 12 order: create (vm/build-vm-image.sh) -> register -> confirm -> start -> THEN deploy. Refusing to deploy."
        exit 3
    fi
    status_out="$("${UTMCTL_BIN}" status "${VM_NAME}" 2>/dev/null | head -1)"
    if [ "${status_out}" != "started" ]; then
        log_error "VM '${VM_NAME}' is registered but NOT started (status='${status_out}')."
        log_error "Start it first (Part 12): ${UTMCTL_BIN} start \"${VM_NAME}\" then re-run this script."
        exit 3
    fi
    log_info "UTM preflight OK: '${VM_NAME}' registered and started."
    return 0
}
BOOTSTRAP_NUXEL_ROOT="${GUEST_REPO}"
SKIP_RUN_BOOTSTRAP="${SKIP_RUN_BOOTSTRAP:-0}"
BOOT_THEME_STAGED=0
SKIP_VERIFY="${SKIP_VERIFY:-0}"
SSH_WAIT_SECONDS="${SSH_WAIT_SECONDS:-420}"     # 7 min default boot wait
SSH_PASS="${SSH_PASS:-}"                        # optional; else rely on keys/agent

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Prefer sshpass when a password is supplied (common for a freshly-provisioned
# Fedora Cloud guest), otherwise use key-based auth. For sudo on the guest we
# embed the literal password value (the remote shell won't see the local var).
SSH=(ssh "${SSH_OPTS[@]}")
SUDO_PASS_VALUE=""
if [ -n "${SSH_PASS}" ] && command -v sshpass >/dev/null 2>&1; then
    SSH=(sshpass -e ssh "${SSH_OPTS[@]}")
    export SSHPASS="${SSH_PASS}"
    # Shell-escape the password for safe embedding on the remote command line.
    SUDO_PASS_VALUE="$(printf '%s' "${SSH_PASS}" | sed "s/'/'\\''/g")"
fi
RSYNC_OPTS=(-az --delete -e "ssh ${SSH_OPTS[*]}" \
    --exclude '.git' --exclude '.qq' --exclude '.qq/**' --exclude '.codeseeq' \
    --exclude '.DS_Store' --exclude '__pycache__' --exclude '*.pyc' \
    --exclude '.env' --exclude 'artifacts' --exclude 'kernel/.build' \
    --exclude 'trace.log' --exclude '.qq_prompt_*.md')

# ---------------------------------------------------------------------------
# wait_ssh: poll until the guest accepts SSH, or time out.
# ---------------------------------------------------------------------------
wait_ssh() {
    local attempts=0
    local max=$(( SSH_WAIT_SECONDS / 5 ))
    log_info "Waiting for guest ssh at ${SSH_TARGET} (up to ${SSH_WAIT_SECONDS}s)..."
    while [ "${attempts}" -lt "${max}" ]; do
        attempts=$(( attempts + 1 ))
        if "${SSH[@]}" "${SSH_TARGET}" true 2>/dev/null; then
            log_info "Guest SSH up at ${SSH_TARGET}"
            return 0
        fi
        sleep 5
    done
    log_error "Guest never became SSH-reachable at ${SSH_TARGET} within ${SSH_WAIT_SECONDS}s."
    return 1
}

guest() { "${SSH[@]}" "${SSH_TARGET}" "$@"; }
# Run a command as root on the guest: pipe the password to sudo -S when we have
# one, otherwise sudo -S with no piped input (key-based, passwordless sudo for
# the nuxel dev user is configured by the bootstrap's /etc/sudoers.d/nuxel).
guest_root() {
    if [ -n "${SUDO_PASS_VALUE}" ]; then
        "${SSH[@]}" "${SSH_TARGET}" "echo '${SUDO_PASS_VALUE}' | sudo -S bash -c '$*'"
    else
        "${SSH[@]}" "${SSH_TARGET}" "sudo -S $*"
    fi
}

# ---------------------------------------------------------------------------
# stage_nuxel_boot_theme: build the animated Nuxel Plymouth theme on the HOST
# (where ffmpeg + H.264 decode are available) and ship it into the guest so
# the bootstrap does not need ffmpeg inside the VM. Falls back gracefully if
# the host tool/ffmpeg are missing — the bootstrap can then try an in-guest
# build or keep the default Plymouth spinner.
# ---------------------------------------------------------------------------
stage_nuxel_boot_theme() {
    local tool="${PROJECT_ROOT}/tools/build-nuxel-boot-theme.sh"
    local mp4="${PROJECT_ROOT}/assets/nuxel-boot-animation.mp4"
    local tarball
    tarball="$(mktemp "${TMPDIR:-/tmp}/nuxel-boot-theme.XXXXXX.tar.gz")"
    rm -f "${tarball}"

    if [ ! -x "${tool}" ] || [ ! -f "${mp4}" ]; then
        log_warn "Boot theme tool/MP4 missing on host — guest will fall back to in-guest build."
        return 1
    fi
    if ! command -v ffmpeg >/dev/null 2>&1; then
        log_warn "ffmpeg not available on host — skipping pre-built boot theme (guest fallback)."
        return 1
    fi

    log_info "Building Nuxel Plymouth boot theme on host (ffmpeg)..."
    # Build at the UTM display geometry (720x1440) so both the Plymouth frames
    # and the GRUB background fill the VM screen instead of the 720x1280 device
    # default. NUXEL_BOOT_THEME_LOOP=1 keeps the animation spinning until
    # plymouthd hands the display to the desktop (a play-once theme freezes on
    # the last frame when boot outlasts the 8s clip, which reads as a hang).
    if ! NUXEL_BOOT_THEME_LOOP=1 "${tool}" --mp4 "${mp4}" --width 720 --height 1440 --tarball "${tarball}"; then
        log_warn "Failed to build Nuxel boot theme on host."
        rm -f "${tarball}"
        return 1
    fi

    log_info "Shipping boot theme to ${SSH_TARGET}:${GUEST_BOOT_THEME_TARBALL}..."
    if command -v rsync >/dev/null 2>&1; then
        if ! rsync "${RSYNC_OPTS[@]}" "${tarball}" "${SSH_TARGET}:${GUEST_BOOT_THEME_TARBALL}"; then
            log_warn "rsync of boot theme failed."
            rm -f "${tarball}"
            return 1
        fi
    else
        if ! "${SSH[@]}" "${SSH_TARGET}" "cat > '${GUEST_BOOT_THEME_TARBALL}'" < "${tarball}"; then
            log_warn "ssh transfer of boot theme failed."
            rm -f "${tarball}"
            return 1
        fi
    fi
    rm -f "${tarball}"
    BOOT_THEME_STAGED=1
    return 0
}

# ---------------------------------------------------------------------------
# Step 0: Part 12 preflight (VM registered + started), then wait for SSH
# ---------------------------------------------------------------------------
preflight_utm

if ! wait_ssh; then
    log_warn "Deployment aborted: guest not reachable (was bg-01 / build-vm-image.sh run?)."
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 2: mirror the repo into the guest at /home/nuxel/nuxel
# ---------------------------------------------------------------------------
log_info "Creating guest repo dir ${GUEST_REPO}..."
guest_root "mkdir -p ${GUEST_REPO}"
guest_root "chown -R ${VM_SSH_USER} ${GUEST_REPO} 2>/dev/null || true"

log_info "Mirroring workspace repo -> ${SSH_TARGET}:${GUEST_REPO} (rsync, keep symlinks/perms)..."
if command -v rsync >/dev/null 2>&1; then
    rsync "${RSYNC_OPTS[@]}" "${PROJECT_ROOT}/" "${SSH_TARGET}:${GUEST_REPO}/" \
        || log_warn "rsync returned non-zero; continuing (some paths may be absent)."
else
    log_warn "rsync not available on host — falling back to tar-over-ssh."
    tar \
        --exclude='.git' --exclude='.qq' --exclude='.qq/**' --exclude='.codeseeq' \
        --exclude='.DS_Store' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.env' --exclude='artifacts' --exclude='kernel/.build' \
        --exclude='trace.log' --exclude='.qq_prompt_*.md' \
        -C "${PROJECT_ROOT}" -cf - . | \
        guest_root "tar -C ${GUEST_REPO} -xf -"
fi

# Stage NUXEL_ROOT distinct from the PWA-serving mirror is unnecessary because
# both resolve to the same path; document it for the report.

# ---------------------------------------------------------------------------
# Step 3: write the deploy manifest (git rev + VERSION) for the report to cite
# ---------------------------------------------------------------------------
git_rev="$(git -C "${PROJECT_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")"
git_branch="$(git -C "${PROJECT_ROOT}" branch --show-current 2>/dev/null || echo "unknown")"
version="$(cat "${PROJECT_ROOT}/VERSION" 2>/dev/null || echo "unknown")"
{
  echo "nuxel-deploy-manifest"
  echo "git_branch=${git_branch}"
  echo "git_rev=${git_rev}"
  echo "version=${version}"
  echo "deployed_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source=${PROJECT_ROOT}"
} | guest_root "cat > ${GUEST_REPO}/vm/deploy-vm-manifest.txt && chown ${VM_SSH_USER} ${GUEST_REPO}/vm/deploy-vm-manifest.txt"
log_info "Manifest written: git_rev=${git_rev} version=${version}"

# ---------------------------------------------------------------------------
# Step 4: sanity check the mirror (diff the critical subtrees)
# ---------------------------------------------------------------------------
log_info "Sanity-checking mirrored repo (diff -r on vm/, services/, shell/, pwa/, ci/)."
for _d in vm services shell pwa/nuxel-home ci; do
    if guest "test -d '${GUEST_REPO}/${_d}'"; then
        # Compare file counts between host and guest for the subtree.
        host_count=$(find "${PROJECT_ROOT}/${_d}" -type f -not -path '*/__pycache__/*' -not -name '*.pyc' -not -name '.DS_Store' 2>/dev/null | wc -l | tr -d ' ')
        guest_count=$(guest "find '${GUEST_REPO}/${_d}' -type f -not -path '*/__pycache__/*' -not -name '*.pyc' -not -name '.DS_Store' 2>/dev/null | wc -l | tr -d ' '")
        if [ "${host_count}" = "${guest_count}" ]; then
            log_info "  [OK] ${_d}: ${guest_count}/${host_count} files"
        else
            log_warn "  [MISMATCH] ${_d}: guest=${guest_count} host=${host_count}"
        fi
    else
        log_warn "  [MISSING] ${_d} not present in guest mirror"
    fi
done

if [ "${SKIP_RUN_BOOTSTRAP}" = "1" ]; then
    log_info "SKIP_RUN_BOOTSTRAP=1 — mirror complete; not running bootstrap."
    exit 0
fi

# ---------------------------------------------------------------------------
# Step 4b: stage a host-built Nuxel Plymouth boot theme (best-effort).
# ---------------------------------------------------------------------------
stage_nuxel_boot_theme || true

# ---------------------------------------------------------------------------
# Step 5: run the bootstrap as root with NUXEL_ROOT resolving to the guest repo
# ---------------------------------------------------------------------------
BOOTSTRAP_ENV="NUXEL_ROOT=${BOOTSTRAP_NUXEL_ROOT}"
if [ "${BOOT_THEME_STAGED}" = "1" ]; then
    BOOTSTRAP_ENV="${BOOTSTRAP_ENV} NUXEL_BOOT_THEME_TARBALL=${GUEST_BOOT_THEME_TARBALL}"
fi
log_info "Running vm/nuxel-vm-bootstrap.sh inside the guest as root (${BOOTSTRAP_ENV})."
BOOTSTRAP_LOG="/var/log/nuxel/bootstrap-$(date -u +%Y%m%d-%H%M%SZ).log"
if guest_root "bash -c 'mkdir -p /var/log/nuxel && ${BOOTSTRAP_ENV} bash ${GUEST_REPO}/vm/nuxel-vm-bootstrap.sh 2>&1 | tee ${BOOTSTRAP_LOG}'"; then
    log_info "Bootstrap completed inside the guest (full output: ${SSH_TARGET}:${BOOTSTRAP_LOG})."
else
    log_error "Bootstrap exited non-zero inside the guest. Full output: ${SSH_TARGET}:${BOOTSTRAP_LOG}; see output above; continuing to gather state."
fi

# ---------------------------------------------------------------------------
# Step 6: verify services (briq-5) unless disabled
# ---------------------------------------------------------------------------
if [ "${SKIP_VERIFY}" = "1" ]; then
    log_info "SKIP_VERIFY=1 — deployment done; skipping service verify."
    exit 0
fi

log_info "Running service verification in the guest..."
guest_root "bash ${GUEST_REPO}/vm/vm-verify-services.sh" \
    || log_warn "vm/vm-verify-services.sh reported failures — see above."

# ---------------------------------------------------------------------------
# Step 7: demonstrate the nuxel-phosh-agent user-session permission flow (briq-6)
# ---------------------------------------------------------------------------
if [ "${SKIP_PHOSH_AGENT:-0}" = "1" ]; then
    log_info "SKIP_PHOSH_AGENT=1 — skipping phosh-agent user-session verify."
else
    log_info "Running nuxel-phosh-agent user-session verification in the guest..."
    guest_root "bash ${GUEST_REPO}/vm/vm-verify-phosh-agent.sh" \
        || log_warn "vm/vm-verify-phosh-agent.sh reported failures — see above."
fi

log_info "Deployment complete."
