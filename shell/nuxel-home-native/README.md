# Nuxel Home Native

Native GTK4/libadwaita Home shell for Nuxel Phone OS.  
Replaces the PWA/Chromium-kiosk Home with a real Linux app running on Phosh/Wayland.

## Files

```
nuxel_home/
  main.py           — Adw.Application entry point, fullscreen window
  app_model.py      — App registry (5 PWA + 4 native-placeholder)
  app_launcher.py   — Launch PWAs via chromium --app=URL
  dbus_client.py    — D-Bus to org.nuxel.Bridge, Portal, Notifications
  system_status.py  — Real sysfs/D-Bus system status
  launcher_grid.py  — FlowBox with drag-reorder
  style.css         — GTK CSS for mobile look
```

## Usage

```bash
# Manual launch
python3 shell/nuxel-home-native/nuxel_home/main.py

# Or via launcher
/usr/local/bin/nuxel-home

# Systemd user service
systemctl --user start nuxel-home-native.service
```

## Dependencies

- python3-gobject, python3-dbus
- gtk4, libadwaita
- chromium (for PWA app windows)
