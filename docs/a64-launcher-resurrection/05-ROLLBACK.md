# 05 — Rollback

## Return launcher CSS to the pre-fix (broken) bytes
```sh
# from the live console
cp -a /var/tmp/nuxel-a64-prebackup-20261023T105215/nuxel-home-tree/css/launcher.css \
      /usr/share/nuxel/nuxel-home/css/launcher.css
sha256sum /usr/share/nuxel/nuxel-home/css/launcher.css   # e3b0c442… (0 bytes)
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```

## Restore the repaired launcher (back to fixed)
```sh
# repo bytes are already identical to the fixed on-device bytes
sha256sum /x/nuxel/pwa/nuxel-home/css/launcher.css       # 9d56a005…
# re-push via tools/beta/live/nuxel_live.py push_bytes, or:
cp /x/nuxel/pwa/nuxel-home/css/launcher.css \
   /usr/share/nuxel/nuxel-home/css/launcher.css
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd
```

## Display backlight recovery (if panel blanked)
```sh
echo 0 > /sys/class/backlight/panel/bl_power
echo 12800 > /sys/class/backlight/panel/brightness
printf 'screen-on\n' > /run/nuxel-wl-fb.cmd
```

The full pre-fix tree copy is preserved at
`/var/tmp/nuxel-a64-prebackup-20261023T105215/nuxel-home-tree/`.
