# PWNAGE-54000 — safe Wi-Fi SSH deployment

Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora ARM64 userspace.
No kernel, firmware, bootloader, recovery or partition write is performed.

## Preconditions

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167 \
  'uname -m; test -e /dev/fb0; systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-orientationd'
```

Expected: `aarch64`, `/dev/fb0` exists, all three services active.

## Deploy

```sh
tools/s10plus/a67/deploy-pwnage54000.sh root@192.168.178.167
```

The script:

1. backs up every file it replaces under `/var/backups/nuxel/p54000-<UTC>`;
2. rebuilds `nuxel-navdock`, `nuxel-foreign-toplevel`, `nuxel-wl-fb`,
   `nuxel-pwa-host` and `libnuxel-libinput-path.so` on the target;
3. installs the orientation daemon/package/config, remote-sync consumer, PWA
   assets, portal fix, media host fix and input shim;
4. repairs `/var/lib/nuxel` traverse access for the portal without widening the
   permissions directory;
5. restarts only the changed userspace services and the Wayland session.

## Verify

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167 '
  /usr/libexec/nuxel/nuxel-orientationd status --json
  cat /run/nuxel-orientation/input.json
  cat /run/nuxel-touch-calibration.state
  cat /run/nuxel-wl-fb.orientation
  systemctl is-active nuxel-portal nuxel-orientationd nuxel-wayland nuxel-wl-fb'
```

Expected fixed-mode evidence for `Locked (LS)`:

```text
mode=landscape effective=90 transform=270 logical=1520x720 display_verified=true
input transform=270 matrix=[0,1,0,-1,0,1] applied=true
touch calibration applied=1 transform=270
framebuffer presenter_rotation=0 double_rotation=0
```

Recorder/microphone:

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167 \
  "curl -sS -H 'Content-Type: application/json' \
     -H 'X-Nuxel-App-Id: org.nuxel.Recorder' \
     -d '{\"namespace\":\"audio\",\"verb\":\"capture-route\",\"params\":{}}' \
     http://127.0.0.1:8080/api/v1/rpc"
```

Expected: `available=true`, source `S10+ microphone (WDMA1, 48 kHz)`.

## Rollback

Every deploy prints the backup path. To roll back:

```sh
tools/s10plus/a67/rollback-pwnage54000.sh root@192.168.178.167 \
  /var/backups/nuxel/p54000-<timestamp>
```

The rollback restores the orientation package/config, PWA tree, navdock,
foreign-toplevel, media host, input shim, portal and service unit, then restarts
the orientation daemon, portal and Wayland session. It does not touch BOOT,
firmware or any partition.

If SSH is unavailable and the display is unusable, the local rollback path is
the orientation daemon's last-good restoration and the retained
`.p54000-prev` binaries. The USB/serial console remains the recovery transport.
