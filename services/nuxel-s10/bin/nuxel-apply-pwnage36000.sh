#!/bin/sh
# Nuxel S10+ PWN36000 staged apply.
#
#   --files-only   install files, keys, udev cleanup and preload ownership
#                  (called synchronously from nuxel-device-permissions.service,
#                  which is ordered Before=nuxel-wayland.service)
#   --services     package install + service enable/restart/verification
#                  (called from a transient unit after the early phase)
#   --all          both (manual/recovery use)
#
# Fail-open: every step logs and continues.  This script never touches the boot
# partition, the kernel, /dev/fb0, or the SSH daemon configuration.
set -u
umask 022
STAGE=${NUXEL_STAGE:-/usr/lib/nuxel/stage36000}
MODE=${1:---all}
LOG=${NUXEL_APPLY_LOG:-/var/lib/nuxel/apply-pwnage36000.log}
BACKUP=${NUXEL_ROLLBACK_DIR:-/var/lib/nuxel/rollback-pwnage36000-$(date +%Y%m%dT%H%M%S)}

mkdir -p /var/lib/nuxel 2>/dev/null || true
say() { printf '%s %s\n' "$(date -u +%FT%TZ 2>/dev/null || date)" "$*" >>"$LOG" 2>/dev/null || true; }
backup() {
    [ -e "$1" ] || return 0
    rel=${1#/}
    mkdir -p "$BACKUP/$(dirname "$rel")" 2>/dev/null || true
    cp -a "$1" "$BACKUP/$rel" 2>/dev/null || true
}
inst() {
    src=$1 dst=$2 mode=${3:-0644}
    if [ ! -f "$src" ]; then say "missing-stage $src"; return 1; fi
    [ -e "$dst" ] && backup "$dst"
    mkdir -p "$(dirname "$dst")" 2>/dev/null || true
    # Atomic replace: do not truncate a script that may be executing (e.g.
    # nuxel-wifi-up.sh during the early boot window).
    tmp="${dst}.nuxel-new.$$"
    cp -f "$src" "$tmp" 2>/dev/null || { say "copy-failed $src -> $dst"; rm -f "$tmp" 2>/dev/null || true; return 1; }
    chmod "$mode" "$tmp" 2>/dev/null || true
    mv -f "$tmp" "$dst" 2>/dev/null || { cp -f "$tmp" "$dst" 2>/dev/null; rm -f "$tmp" 2>/dev/null || true; }
    say "installed $dst"
    return 0
}
remove_file() {
    [ -e "$1" ] || return 0
    backup "$1"
    rm -f "$1" 2>/dev/null || true
    say "removed $1"
}
run() {
    desc=$1; shift
    if command -v timeout >/dev/null 2>&1; then
        timeout 45 "$@" >>"$LOG" 2>&1
    else
        "$@" >>"$LOG" 2>&1
    fi
    rc=$?
    say "$desc rc=$rc"
    return $rc
}

install_ssh_keys() {
    keyfile=$STAGE/ssh/wicked_wqn_id_rsa.pub
    [ -f "$keyfile" ] || { say "ssh-key: staged key missing"; return 0; }
    key=$(tr -d '\r\n' <"$keyfile" 2>/dev/null)
    [ -n "$key" ] || return 0
    for home in /home/nuxel /root; do
        [ -d "$home" ] || continue
        mkdir -p "$home/.ssh" 2>/dev/null || true
        chmod 700 "$home/.ssh" 2>/dev/null || true
        touch "$home/.ssh/authorized_keys" 2>/dev/null || true
        if ! grep -Fq "$key" "$home/.ssh/authorized_keys" 2>/dev/null; then
            printf '%s\n' "$key" >>"$home/.ssh/authorized_keys" 2>/dev/null || true
            say "ssh-key: appended to $home/.ssh/authorized_keys"
        else
            say "ssh-key: already present in $home/.ssh/authorized_keys"
        fi
        chmod 600 "$home/.ssh/authorized_keys" 2>/dev/null || true
        if [ "$home" = /home/nuxel ]; then
            chown -R nuxel:nuxel "$home/.ssh" 2>/dev/null || true
        fi
    done
}

install_zsh_files() {
    z=$STAGE/nuxel-zsh
    [ -d "$z" ] || { say "zsh: stage missing"; return 0; }
    mkdir -p /usr/lib/nuxel/zsh /etc/nuxel /usr/local/bin /etc/profile.d 2>/dev/null || true
    inst "$z/nuxel.zsh" /usr/lib/nuxel/zsh/nuxel.zsh 0644 || true
    inst "$z/nuxel-theme" /usr/lib/nuxel/zsh/nuxel-theme 0755 || true
    inst "$z/nuxel-theme" /usr/local/bin/nuxel-theme 0755 || true
    inst "$z/nuxel-banner" /usr/lib/nuxel/zsh/nuxel-banner 0644 || true
    inst "$z/nuxel-banner.sh" /etc/profile.d/nuxel-banner.sh 0755 || true
    if [ ! -e /etc/nuxel/zsh.conf ]; then
        inst "$z/nuxel-zsh.conf" /etc/nuxel/zsh.conf 0644 || true
    fi
    if [ ! -e /etc/nuxel/banner ]; then
        inst "$z/nuxel-banner" /etc/nuxel/banner 0644 || true
    fi
    if [ -f /etc/zshrc ] && grep -Fq '# >>> nuxel-zsh >>>' /etc/zshrc 2>/dev/null; then
        say "zsh: /etc/zshrc already sources nuxel.zsh"
    else
        [ -f /etc/zshrc ] && backup /etc/zshrc
        {
            printf '\n# >>> nuxel-zsh >>>\n'
            printf '[ -r /usr/lib/nuxel/zsh/nuxel.zsh ] && source /usr/lib/nuxel/zsh/nuxel.zsh\n'
            printf '# <<< nuxel-zsh <<<\n'
        } >>/etc/zshrc 2>/dev/null || true
        say "zsh: appended source block to /etc/zshrc"
    fi
}

install_preload() {
    # Session/controller live in /usr/lib/nuxel; the PWA files are root-owned.
    [ -f "$STAGE/session/nuxel-session.sh" ] && inst "$STAGE/session/nuxel-session.sh" /usr/lib/nuxel/nuxel-session.sh 0755 || true
    [ -f "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema" ] && inst "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema" /usr/lib/nuxel/nuxel-preload-cinema 0755 || true
    [ -f "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema.service" ] && inst "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema.service" /etc/systemd/system/nuxel-preload-cinema.service 0644 || true
    # Launcher assets are installed ONLY when the staged copy is newer than the
    # deployed file.  This bootstrap runs --files-only on every boot; an
    # unconditional install silently reverted live PWNAGE fixes (measured
    # 2026-10-29: the fixed app.js/style.css/index.html were overwritten by this
    # stage's older copies).  `-nt` keeps a same-run deploy intact and still lets
    # a genuinely updated stage roll forward.
    for f in index.html css/style.css js/app.js sw.js; do
        src="$STAGE/pwa/$f"; dst="/usr/share/nuxel/pwa/nuxel-home/$f"
        if [ -f "$src" ]; then
            if [ ! -f "$dst" ] || [ "$src" -nt "$dst" ]; then
                inst "$src" "$dst" 0644 || true
            else
                say "kept newer deployed $dst (stage copy is older)"
            fi
        fi
    done
    # The early session controller owns the one-shot video.  The systemd unit
    # raced it and could write the .done marker before the launcher existed.
    remove_file /etc/systemd/system/multi-user.target.wants/nuxel-preload-cinema.service
    remove_file /etc/systemd/system/sockets.target.wants/nuxel-preload-cinema.service
    remove_file /usr/share/nuxel/pwa/nuxel-home/preload-status.json
    remove_file /usr/share/nuxel/nuxel-home/preload-status.json
    say "preload: session owns the boot overlay; systemd unit disabled"
}

files_only() {
    say "== files-only begin (stage=$STAGE) =="
    install_ssh_keys
    install_zsh_files
    install_preload

    # nuxel-s10 binaries.  The real permissions script is installed under a
    # distinct name because the live path is the early wrapper.
    #
    # PWN-40000: this bootstrap runs --files-only on EVERY boot.  The first
    # revision unconditionally installed its staged nuxel-audio-route.sh and
    # silently reverted the verified RDMA1 route (and the staged unit file) at
    # 2026-10-30T09:19Z.  Keep a newer deployed route script, and never replace
    # a script that contains the proven ABOX RDMA1_EN gate with an older staged
    # copy that lacks it.  The same content guard applies to the route units.
    for f in nuxel-audio-route.sh nuxel-wifi-up.sh nuxel-charger-mode-recovery.sh; do
        src="$STAGE/nuxel-s10/bin/$f"; dst="/usr/lib/nuxel/$f"
        [ -f "$src" ] || continue
        if [ "$f" = nuxel-audio-route.sh ] && [ -f "$dst" ] && \
           grep -q "ABOX RDMA1_EN" "$dst" && ! grep -q "ABOX RDMA1_EN" "$src"; then
            say "kept proven deployed $dst (staged copy lacks ABOX RDMA1_EN)"
            continue
        fi
        if [ -f "$dst" ] && [ "$dst" -nt "$src" ]; then
            say "kept newer deployed $dst (stage copy is older)"
            continue
        fi
        inst "$src" "$dst" 0755 || true
    done
    [ -f "$STAGE/nuxel-s10/bin/nuxel-device-permissions.sh" ] && \
        inst "$STAGE/nuxel-s10/bin/nuxel-device-permissions.sh" /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 0755 || true
    # Do not overwrite the wrapper while it is executing this script.  It is
    # installed once during deployment; the staged copy is kept for rollback.
    if ! grep -q "Early boot wrapper" /usr/lib/nuxel/nuxel-device-permissions.sh 2>/dev/null; then
        [ -f "$STAGE/nuxel-s10/bin/nuxel-device-permissions-early-wrapper.sh" ] && \
            inst "$STAGE/nuxel-s10/bin/nuxel-device-permissions-early-wrapper.sh" /usr/lib/nuxel/nuxel-device-permissions.sh 0755 || true
    fi
    [ -f "$STAGE/nuxel-s10/bin/nuxel-audio-status" ] && inst "$STAGE/nuxel-s10/bin/nuxel-audio-status" /usr/local/bin/nuxel-audio-status 0755 || true
    [ -f "$STAGE/nuxel-s10/bin/nuxel-gps-status" ] && inst "$STAGE/nuxel-s10/bin/nuxel-gps-status" /usr/local/bin/nuxel-gps-status 0755 || true
    [ -f "$STAGE/nuxel-s10/bin/nuxel-verify-pwnage36000.sh" ] && \
        inst "$STAGE/nuxel-s10/bin/nuxel-verify-pwnage36000.sh" /usr/local/bin/nuxel-verify-pwnage36000 0755 || true
    for f in "$STAGE"/nuxel-s10/systemd/*.service; do
        [ -f "$f" ] || continue
        dst="/etc/systemd/system/$(basename "$f")"
        # Never let the boot bootstrap replace a newer live unit (measured
        # 2026-10-30: it reverted the route unit's 45 s bound and ordering
        # comments).  Also refuse an empty staged unit: one zero-byte copy
        # silently masked nuxel-audio-route-retry.service on 2026-10-30.
        [ -s "$f" ] || { say "skipped empty staged unit $f"; continue; }
        if [ -f "$dst" ] && [ "$dst" -nt "$f" ]; then
            say "kept newer deployed $dst (stage copy is older)"
            continue
        fi
        inst "$f" "$dst" 0644 || true
    done
    # SSH allowlist for the owner's current LAN.  Installed as a drop-in so the
    # 26000 Tri-Link policy keeps its public-key-only rules.
    [ -f "$STAGE/nuxel-s10/ssh/61-nuxel-lan38.conf" ] &&         inst "$STAGE/nuxel-s10/ssh/61-nuxel-lan38.conf" /etc/ssh/sshd_config.d/61-nuxel-lan38.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/wireplumber/99-nuxel-s10.conf" ] && \
        inst "$STAGE/nuxel-s10/wireplumber/99-nuxel-s10.conf" /etc/wireplumber/wireplumber.conf.d/99-nuxel-s10.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/pipewire/99-nuxel-s10.conf" ] && \
        inst "$STAGE/nuxel-s10/pipewire/99-nuxel-s10.conf" /etc/pipewire/pipewire.conf.d/99-nuxel-s10.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/alsa/99-nuxel-s10-default.conf" ] && \
        inst "$STAGE/nuxel-s10/alsa/99-nuxel-s10-default.conf" /etc/alsa/conf.d/99-nuxel-s10-default.conf 0644 || true
    # The old workaround pointed at RDMA0, which never advances.  Remove it.
    remove_file /etc/alsa/conf.d/99-nuxel-s10-workaround.conf
    [ -f "$STAGE/nuxel-s10/geoclue/geoclue.conf" ] && \
        inst "$STAGE/nuxel-s10/geoclue/geoclue.conf" /etc/geoclue/geoclue.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/dbus/99-geoclue-nuxel.conf" ] && \
        inst "$STAGE/nuxel-s10/dbus/99-geoclue-nuxel.conf" /etc/dbus-1/system.d/99-geoclue-nuxel.conf 0644 || true

    # udevd is masked on this kernel.  Remove the rules that never ran.
    for r in 90-nuxel-s10.rules 90-nuxel-audio.rules 90-nuxel-bluetooth.rules 99-bluetooth.rules; do
        remove_file "/etc/udev/rules.d/$r"
    done
    # Apply the new permission policy immediately on the first boot too.
    [ -x /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 ] && \
        /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 >>"$LOG" 2>&1 || true
    say "== files-only done (rollback=$BACKUP) =="
    printf '{"ok":true,"mode":"files-only","rollback":"%s","finished_at":"%s"}\n' \
        "$BACKUP" "$(date -u +%FT%TZ 2>/dev/null || date)" > /var/lib/nuxel/pwnage36000-files.json 2>/dev/null || true
}

services() {
    say "== services begin =="
    if ! command -v zsh >/dev/null 2>&1; then
        say "zsh: installing package"
        if command -v dnf >/dev/null 2>&1; then
            timeout 240 dnf install -y zsh >>"$LOG" 2>&1; say "dnf install zsh rc=$?"
        elif command -v apt-get >/dev/null 2>&1; then
            timeout 240 apt-get install -y zsh >>"$LOG" 2>&1; say "apt-get install zsh rc=$?"
        fi
    fi
    if [ -x "$STAGE/nuxel-zsh/install-nuxel-zsh.sh" ] && command -v zsh >/dev/null 2>&1; then
        run "nuxel-zsh installer" sh "$STAGE/nuxel-zsh/install-nuxel-zsh.sh" --root / --no-package || true
    fi

    run "daemon-reload" systemctl daemon-reload
    run "disable preload unit" systemctl disable nuxel-preload-cinema.service
    # Bootcap is a 24 s diagnostic capture.  It must not hold multi-user.target
    # or compete with the display bridge on a normal boot.
    run "disable bootcap unit" systemctl disable nuxel-bootcap.service
    run "enable services" systemctl enable bluetooth.service nuxel-bluetooth.service geoclue.service \
        nuxel-wifi.service nuxel-device-permissions.service nuxel-audio-route.service \
        nuxel-charger-mode-recovery.service
    run "rfkill bluetooth" rfkill unblock bluetooth
    # nuxel-bluetooth.service is ordered Before=bluetooth.service and is still
    # running its one-time patchram download when this transient unit executes.
    # Restarting it here made systemd stop the active service, wait the 30 s
    # SIGTERM timeout, abort, and re-run the whole bring-up.  That put the
    # patchram download behind multi-user.target (measured 2026-10-29: 51 s
    # userspace).  Leave the bring-up alone once it is active; only start it
    # when the unit is genuinely not running.
    if ! systemctl is-active --quiet nuxel-bluetooth.service; then
        run "start bluetooth bring-up" systemctl start nuxel-bluetooth.service
    else
        say "bluetooth bring-up already active; not restarting"
    fi
    if ! systemctl is-active --quiet bluetooth.service; then
        run "start bluetooth" systemctl start bluetooth.service
    fi
    run "restart geoclue" systemctl restart geoclue.service
    run "restart wifi" systemctl restart nuxel-wifi.service
    run "start audio route" systemctl start nuxel-audio-route.service
    # PWNAGE-41000: Wi-Fi is ON by default after every normal boot.
    # nuxel-wifi.service enables NetworkManager's Wi-Fi radio and verifies the
    # readback; it does not select profiles, rewrite autoconnect flags, touch
    # passwords, or start a second supplicant.  A manual OFF is respected until
    # the next normal boot.  This installer therefore leaves the boot policy to
    # the unit and never rewrites saved profiles.
    say "bluetooth: $(hciconfig 2>&1 | head -2 | tr '\n' ' ')"
    say "wifi: $(ip -4 -brief addr show wlan0 2>/dev/null | awk '{print $3}')"
    say "audio: $(nuxel-audio-status 2>&1 | tr '\n' ' ')"
    say "gps: $(nuxel-gps-status 2>&1 | tr '\n' ' ')"
    say "== services done =="
    printf '{"ok":true,"mode":"services","finished_at":"%s"}\n' \
        "$(date -u +%FT%TZ 2>/dev/null || date)" > /var/lib/nuxel/pwnage36000-services.json 2>/dev/null || true
}

case $MODE in
    --files-only) files_only ;;
    --services) services ;;
    --all) files_only; services ;;
    *) echo "usage: $0 [--files-only|--services|--all]" >&2; exit 2 ;;
esac
exit 0
