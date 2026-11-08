#!/usr/bin/env python3
"""Strict ARM64 Fedora S10+ userspace verifier; operates on staging OR ext4.

No mount, chroot, Docker, or libext2fs required in --ext4 mode. This verifies
package binary payloads and S10+ assets; it cannot verify hardware support.
"""
import argparse
import hashlib
import pathlib
import posixpath
import stat
import struct
import sys
from ext4lite import Ext4

BINARIES=(
    '/usr/bin/python3', '/usr/libexec/phosh', '/usr/bin/phoc',
    '/usr/lib/systemd/systemd', '/sbin/init',
    '/usr/bin/nuxel-fb-phone',
    # Current S10+ userspace (A34 TOUCHDOWN), compiled from repo sources by
    # images/s10plus/build-phone-rootfs-inside-fedora.sh in the arm64 container.
    '/usr/lib/nuxel/nuxel-wl-fb',
    '/usr/lib/nuxel/nuxel-pwa-host',
    '/usr/lib/nuxel/nuxel-button-manager',
    '/usr/lib/nuxel/libnuxel-libinput-path.so',
    '/usr/local/bin/nuxel-wl-snapshot',
    # A40/A44 socket-activated Home hardware monitor, built from repo source.
    '/usr/lib/nuxel/nuxel-metricsd',
    # PWNAGE-31000: the pre-lockscreen controller invokes this exact absolute
    # path (mpv 0.40 + FFmpeg-free chain).  A fresh image must contain it.
    '/usr/bin/mpv',
)
FILES=(
    '/etc/udev/rules.d/90-nuxel-beyond2lte.rules',
    '/etc/nuxel/nuxel-beyond2lte.conf',
    '/etc/nuxel/input/buttons.json',
    '/etc/nuxel/input/button-fsm.json',
    '/etc/nuxel/buttons/reboot-gate.json',
    '/usr/share/nuxel/nuxel-home/index.html',
    '/etc/nuxel/phone-runtime-status',
    '/etc/nuxel/keyboard/keyboard.json',
    '/usr/libexec/nuxel/nuxel-keyboard-apply',
    '/usr/lib/systemd/user/nuxel-keyboard-apply.service',
    '/usr/lib/systemd/user/nuxel-keyboard-apply.path',
    '/usr/libexec/nuxel/nuxel-sound-cue',
    '/etc/systemd/system/nuxel-boot-sound.service',
    '/usr/share/nuxel/assets/nuxel-boot-audio.mp3',
    '/usr/share/nuxel/assets/nuxel-pow.mp3',
    '/usr/share/nuxel/assets/button-left.png',
    '/usr/share/nuxel/assets/button-middle.png',
    '/usr/share/nuxel/assets/button-right.png',
    '/usr/share/nuxel/assets/nuxel-charging.png',
    '/usr/share/nuxel/assets/nuxel-connected-pc.png',
    '/usr/share/nuxel/assets/nuxel-live-console-active.png',
    '/usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png',
    '/usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png',
    '/etc/systemd/system/nuxel-metrics.service',
    # PWNAGE-58000 idle/wakeup contract: the one-shot tuning service, its
    # executable and the bounded journald drop-in must be in a fresh image.
    '/usr/lib/nuxel/nuxel-perf-tune.sh',
    '/etc/systemd/system/nuxel-perf-tune.service',
    '/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service',
    '/etc/systemd/journald.conf.d/50-nuxel-performance.conf',
    '/etc/systemd/system/nuxel-metrics.socket',
    '/etc/systemd/system/sockets.target.wants/nuxel-metrics.socket',
    # PWNAGE-31000 pre-lockscreen controller.  The supplied clip is installed
    # under /usr/share/nuxel/boot (not the static webroot) and its bytes are
    # checked against the checkout by SOURCE_PARITY below.
    '/usr/lib/nuxel/nuxel-preload-cinema',
    '/etc/nuxel/boot/preload-cinema.json',
    '/etc/systemd/system/nuxel-preload-cinema.service',
    '/usr/share/nuxel/doc/PWNAGE-31000.md',
    '/usr/share/nuxel/preload/nuxel-preloading-screen.mp4',
    # PWNAGE-46000 orientation owner: executable, importable package, policy,
    # schema, continuous unit and the exact console-indicator artwork.
    '/usr/libexec/nuxel/nuxel-orientationd',
    '/usr/local/bin/nuxel-rotation-notes',
    '/usr/bin/wlr-randr',
    '/usr/libexec/nuxel/nuxel_orientation/__init__.py',
    '/usr/libexec/nuxel/nuxel_orientation/policy.py',
    '/usr/libexec/nuxel/nuxel_orientation/sensors.py',
    '/usr/libexec/nuxel/nuxel_orientation/apply.py',
    '/etc/nuxel/orientation/orientation.json',
    '/etc/nuxel/orientation/orientation.schema.json',
    '/etc/systemd/system/nuxel-orientationd.service',
    '/usr/share/nuxel/assets/nuxel-console-serial.png',
    '/usr/share/nuxel/assets/nuxel-console-usb.png',
    '/usr/share/nuxel/assets/nuxel-console-wlan.png',
    '/usr/share/nuxel/preload/nuxel-preloading-screen.mp4.sha256',
    # Durable interface ON/OFF state + default-off Bluetooth bring-up.
    '/usr/lib/nuxel/nuxel-interface-state',
    '/usr/local/bin/nuxel-interface-state',
    '/usr/lib/nuxel/nuxel-bridge/interface_state.py',
    '/etc/systemd/system/nuxel-bluetooth.service',
    '/etc/systemd/system/nuxel-interface-state.service',
    '/etc/systemd/system/multi-user.target.wants/nuxel-interface-state.service',
    # PWNAGE-91000 firewall/permission surfaces: the bridge provider imports
    # this package from <bridge-dir>/../../nuxel-firewall, and the CLI/policy
    # are the recovery path the app and Settings call.
    '/usr/bin/nuxel-firewall',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/__init__.py',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/provider.py',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/policy.py',
    '/etc/nuxel/firewall/policy.json',
    '/etc/nuxel/firewall/policy.schema.json',
    '/usr/share/nuxel/pwa/nuxel-apps/firewall/index.html',
    '/usr/share/nuxel/pwa/nuxel-apps/firewall/manifest.json',
    '/usr/share/nuxel/pwa/nuxel-apps/permissions/index.html',
    '/usr/share/nuxel/pwa/nuxel-apps/permissions/manifest.json',
)

# Runtime-critical files copied verbatim by the rootfs builder.  Comparing the
# packaged bytes with the checkout makes "latest source" an enforceable image
# property instead of an assumption based on a successful copy command.
SOURCE_PARITY = {
    '/usr/share/nuxel/pwa/nuxel-home/js/app.js': 'pwa/nuxel-home/js/app.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js': 'pwa/nuxel-home/js/touch-keyboard.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/status-bar.js': 'pwa/nuxel-home/js/status-bar.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/qs.js': 'pwa/nuxel-home/js/qs.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js': 'pwa/nuxel-home/js/host-bridge.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/apps.js': 'pwa/nuxel-home/js/apps.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/launcher.js': 'pwa/nuxel-home/js/launcher.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/immersive.js': 'pwa/nuxel-home/js/immersive.js',
    '/usr/share/nuxel/pwa/nuxel-home/css/launcher.css': 'pwa/nuxel-home/css/launcher.css',
    '/usr/share/nuxel/pwa/nuxel-common/back.js': 'pwa/nuxel-common/back.js',
    '/usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js': 'pwa/nuxel-apps/settings/power-menu.js',
    '/usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css': 'pwa/nuxel-apps/settings/power-menu.css',
    '/usr/share/nuxel/pwa/nuxel-home/sw.js': 'pwa/nuxel-home/sw.js',
    '/usr/share/nuxel/pwa/nuxel-home/manifest.json': 'pwa/nuxel-home/manifest.json',
    '/usr/share/nuxel/pwa/nuxel-apps/terminal/index.html': 'pwa/nuxel-apps/terminal/index.html',
    '/usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js': 'pwa/nuxel-apps/terminal/terminal.js',
    '/usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.css': 'pwa/nuxel-apps/terminal/terminal.css',
    '/etc/nuxel/app-registry/app_registry.json': 'pwa/nuxel-common/app-registry.json',
    '/etc/nuxel/bridge-version.json': 'pwa/nuxel-common/bridge-version.json',
    '/etc/nuxel/keyboard/keyboard.json': 'configs/nuxel/keyboard/keyboard.json',
    '/usr/share/nuxel/assets/nuxel-boot-audio.mp3': 'assets/nuxel-boot-audio.mp3',
    '/usr/share/nuxel/assets/nuxel-pow.mp3': 'assets/nuxel-pow.mp3',
    '/usr/share/nuxel/assets/button-left.png': 'assets/button-left.png',
    '/usr/share/nuxel/assets/button-middle.png': 'assets/button-middle.png',
    '/usr/share/nuxel/assets/button-right.png': 'assets/button-right.png',
    '/usr/share/nuxel/assets/nuxel-charging.png': 'assets/nuxel-charging.png',
    '/usr/share/nuxel/assets/nuxel-connected-pc.png': 'assets/nuxel-connected-pc.png',
    '/usr/share/nuxel/assets/nuxel-live-console-active.png': 'assets/nuxel-live-console-active.png',
    '/usr/share/nuxel/assets/nuxel-console-serial.png': 'assets/nuxel-console-serial.png',
    '/usr/share/nuxel/assets/nuxel-console-usb.png': 'assets/nuxel-console-usb.png',
    '/usr/share/nuxel/assets/nuxel-console-wlan.png': 'assets/nuxel-console-wlan.png',
    '/usr/libexec/nuxel/nuxel-orientationd': 'services/nuxel-orientation/nuxel-orientationd',
    '/usr/libexec/nuxel/nuxel_orientation/policy.py': 'services/nuxel-orientation/nuxel_orientation/policy.py',
    '/usr/libexec/nuxel/nuxel_orientation/sensors.py': 'services/nuxel-orientation/nuxel_orientation/sensors.py',
    '/usr/libexec/nuxel/nuxel_orientation/apply.py': 'services/nuxel-orientation/nuxel_orientation/apply.py',
    '/etc/nuxel/orientation/orientation.json': 'configs/nuxel/orientation/orientation.json',
    '/etc/nuxel/orientation/orientation.schema.json': 'configs/nuxel/orientation/orientation.schema.json',
    '/etc/systemd/system/nuxel-orientationd.service': 'services/nuxel-orientation/systemd/nuxel-orientationd.service',
    '/usr/share/nuxel/assets/nuxel-applications-icon-pack/01-01_terminal.png': 'assets/nuxel-applications-icon-pack/01-01_terminal.png',
    '/usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/01-wifi.png': 'assets/nuxel-quicksettings-icon-pack/01-wifi.png',
    '/usr/libexec/nuxel/nuxel-sound-cue': 'tools/s10plus/a33/nuxel-sound-cue.py',
    '/etc/systemd/system/nuxel-boot-sound.service': 'services/nuxel-session/systemd/nuxel-boot-sound.service',
    '/usr/libexec/nuxel/nuxel-keyboard-apply': 'tools/s10plus/a33/nuxel-keyboard-apply.sh',
    # A44 launcher/navigation/metrics bytes that were live-deployed on the
    # handset. A fresh image must carry exactly these checkout versions.
    '/usr/share/nuxel/pwa/nuxel-home/index.html': 'pwa/nuxel-home/index.html',
    '/usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css': 'pwa/nuxel-home/css/lockscreen.css',
    '/usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js': 'pwa/nuxel-home/js/lockscreen.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js': 'pwa/nuxel-home/js/lockscreen-indicators.js',
    '/usr/lib/nuxel/nuxel-bridge/system_indicators.py': 'services/nuxel-bridge/src/system_indicators.py',
    '/usr/share/nuxel/pwa/nuxel-home/css/launcher.css': 'pwa/nuxel-home/css/launcher.css',
    '/usr/share/nuxel/pwa/nuxel-home/css/style.css': 'pwa/nuxel-home/css/style.css',
    '/usr/share/nuxel/pwa/nuxel-home/js/launcher.js': 'pwa/nuxel-home/js/launcher.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/home-settings.js': 'pwa/nuxel-home/js/home-settings.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/navigation.js': 'pwa/nuxel-home/js/navigation.js',
    '/usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js': 'pwa/nuxel-home/js/system-monitor.js',
    '/usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js': 'pwa/nuxel-apps/settings/wifi-settings.js',
    '/usr/lib/nuxel/nuxel-bridge/bridge.py': 'services/nuxel-bridge/src/bridge.py',
    '/usr/lib/nuxel/nuxel-bridge/api.py': 'services/nuxel-bridge/src/api.py',
    '/usr/lib/nuxel/nuxel-bridge/interface_state.py': 'services/nuxel-bridge/src/interface_state.py',
    '/usr/lib/nuxel/nuxel-interface-state': 'services/nuxel-s10/bin/nuxel-interface-state',
    '/etc/systemd/system/nuxel-bluetooth.service': 'services/nuxel-s10/systemd/nuxel-bluetooth.service',
    '/etc/systemd/system/nuxel-interface-state.service': 'services/nuxel-s10/systemd/nuxel-interface-state.service',
    '/usr/share/nuxel/pwa/nuxel-home/js/desktop-layout.js': 'pwa/nuxel-home/js/desktop-layout.js',
    # PWNAGE-91000 firewall/permissions bytes must match the checkout exactly.
    '/usr/bin/nuxel-firewall': 'services/nuxel-firewall/bin/nuxel-firewall',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/__init__.py': 'services/nuxel-firewall/nuxel_firewall/__init__.py',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/provider.py': 'services/nuxel-firewall/nuxel_firewall/provider.py',
    '/usr/lib/nuxel/nuxel-firewall/nuxel_firewall/policy.py': 'services/nuxel-firewall/nuxel_firewall/policy.py',
    '/etc/nuxel/firewall/policy.json': 'configs/nuxel/firewall/policy.json',
    '/etc/nuxel/firewall/policy.schema.json': 'configs/nuxel/firewall/policy.schema.json',
    '/usr/share/nuxel/pwa/nuxel-apps/firewall/index.html': 'pwa/nuxel-apps/firewall/index.html',
    '/usr/share/nuxel/pwa/nuxel-apps/firewall/manifest.json': 'pwa/nuxel-apps/firewall/manifest.json',
    '/usr/share/nuxel/pwa/nuxel-apps/permissions/index.html': 'pwa/nuxel-apps/permissions/index.html',
    '/usr/share/nuxel/pwa/nuxel-apps/permissions/manifest.json': 'pwa/nuxel-apps/permissions/manifest.json',
    '/usr/share/nuxel/pwa/nuxel-home/js/qs-firewall.js': 'pwa/nuxel-home/js/qs-firewall.js',
    '/usr/share/nuxel/pwa/nuxel-apps/settings/firewall-settings.js': 'pwa/nuxel-apps/settings/firewall-settings.js',
    '/usr/share/nuxel/pwa/nuxel-apps/settings/keyboard-settings.js': 'pwa/nuxel-apps/settings/keyboard-settings.js',
    '/etc/systemd/system/nuxel-metrics.service': 'services/nuxel-metrics/nuxel-metrics.service',
    '/usr/lib/nuxel/nuxel-perf-tune.sh': 'services/nuxel-performance/bin/nuxel-perf-tune.sh',
    '/etc/systemd/system/nuxel-perf-tune.service': 'services/nuxel-performance/systemd/nuxel-perf-tune.service',
    '/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service': 'services/nuxel-performance/systemd/nuxel-perf-tune.service',
    '/etc/systemd/journald.conf.d/50-nuxel-performance.conf': 'configs/nuxel/performance/journald.conf',
    '/etc/systemd/system/nuxel-metrics.socket': 'services/nuxel-metrics/nuxel-metrics.socket',
    '/etc/systemd/system/sockets.target.wants/nuxel-metrics.socket': 'services/nuxel-metrics/nuxel-metrics.socket',
    '/usr/lib/nuxel/nuxel-preload-cinema': 'services/nuxel-preload-cinema/nuxel-preload-cinema',
    '/etc/nuxel/boot/preload-cinema.json': 'configs/nuxel/boot/preload-cinema.json',
    '/etc/systemd/system/nuxel-preload-cinema.service': 'services/nuxel-preload-cinema/nuxel-preload-cinema.service',
    '/usr/share/nuxel/doc/PWNAGE-31000.md': 'docs/pwnage-31000/IMPLEMENTATION.md',
    '/usr/share/nuxel/preload/nuxel-preloading-screen.mp4': 'assets/nuxel-preloading-screen.mp4',
}


def read_staging(root, path):
    name=path
    for _ in range(25):
        p=root/name.lstrip('/')
        parts=pathlib.PurePosixPath(name).parts
        prefix=[]
        changed=False
        for j, part in enumerate(parts):
            if part=='/':continue
            prefix.append(part)
            cand=root.joinpath(*prefix)
            if cand.is_symlink():
                target=cand.readlink().as_posix()
                prior='/'+'/'.join(prefix[:-1])
                replacement=target if target.startswith('/') else posixpath.join(prior,target)
                rem=[v for v in parts[j+1:] if v!='/']
                name=posixpath.normpath(posixpath.join(replacement,*rem))
                changed=True
                break
        if not changed:
            if not p.is_file(): raise ValueError('not a file: '+path)
            return p.read_bytes()
    raise ValueError('excessive symlink depth: '+path)


def read_ext4(fs, path):
    name=path
    for _ in range(25):
        if not name.startswith('/'): raise ValueError('not absolute: '+name)
        parts=[p for p in name.strip('/').split('/') if p]
        parent=2
        changed=False
        for j,part in enumerate(parts):
            ino=fs.children(parent)[part][0]
            inode,_=fs.inode(ino)
            mode=fs.u16(inode,0)
            if stat.S_ISLNK(mode):
                link=fs.get(ino).decode('utf-8')
                prev='/'+'/'.join(parts[:j])
                replacement=link if link.startswith('/') else posixpath.join(prev,link)
                name=posixpath.normpath(posixpath.join(replacement,*parts[j+1:]))
                changed=True
                break
            parent=ino
        if not changed:
            inode,_=fs.inode(parent)
            if not stat.S_ISREG(fs.u16(inode,0)):raise ValueError('not a regular file: '+path)
            return fs.get(parent)
    raise ValueError('excessive symlink depth: '+path)


def validate(read):
    for p in BINARIES:
        b=read(p)
        if len(b)<64 or b[:4]!=b'\x7fELF' or b[4]!=2 or b[5]!=1 or struct.unpack_from('<H',b,18)[0]!=183:
            raise ValueError('expected actual aarch64 ELF, not a source/shim: '+p)
        print('PASS ELF aarch64:',p,len(b),'bytes')
    for p in FILES:
        b=read(p)
        if not b:raise ValueError('empty file '+p)
        print('PASS asset:',p,len(b),'bytes')
    repo = pathlib.Path(__file__).resolve().parents[2]
    for image_path, source_path in SOURCE_PARITY.items():
        packaged = read(image_path)
        source = (repo/source_path).read_bytes()
        if packaged != source:
            raise ValueError('source/image drift: %s != %s (%s != %s)' % (
                image_path, source_path, hashlib.sha256(packaged).hexdigest(),
                hashlib.sha256(source).hexdigest()))
        print('PASS exact source parity:', source_path, '->', image_path)
    status=read('/etc/nuxel/phone-runtime-status')
    for token in (b'BASE_OS=fedora-43-aarch64',b'INIT_SYSTEM=systemd',b'HARDWARE_BOOT_VERIFIED=false',b'DISPLAY_DRIVER_VERIFIED=false'):
        if token not in status:raise ValueError('incorrect runtime status '+repr(token))
    print('PASS: Fedora RPM installed ARM64 phone binaries, systemd, Nuxel S10+ overlays')
    print('NOT VERIFIED: kernel, GPU/DRM, DTBO/hw-revision, touch or actual phone boot')


def main():
    a=argparse.ArgumentParser()
    g=a.add_mutually_exclusive_group(required=True)
    g.add_argument('--staging',type=pathlib.Path)
    g.add_argument('--ext4',type=pathlib.Path)
    args=a.parse_args()
    try:
        if args.staging:
            root=args.staging
            if (root/'etc/nuxel/device/g7power').exists():raise ValueError('G7Power overlay found')
            validate(lambda p:read_staging(root,p))
        else:
            fs=Ext4(str(args.ext4))
            try:fs.resolve('/etc/nuxel/device/g7power')
            except KeyError:pass
            else:raise ValueError('G7Power overlay found')
            validate(lambda p:read_ext4(fs,p))
    except (ValueError,KeyError,AssertionError,IndexError,FileNotFoundError) as e:
        print('FAIL: FEDORA PHONE RUNTIME NOT COMPLETE: '+str(e),file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
