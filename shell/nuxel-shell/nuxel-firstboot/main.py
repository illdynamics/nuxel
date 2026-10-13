#!/usr/bin/env python3
"""
Nuxel First-Boot Setup Wizard for Google Pixel 10 Pro XL (mustang)

This script runs on the very first boot after flashing Nuxel to the device.
It presents a GTK-based wizard that:
  1. Welcomes the user to Nuxel
  2. Prompts for username and display name
  3. Configures WiFi networking
  4. Creates the nuxel user account
  5. Removes the /var/lib/nuxel/.firstboot-complete marker

Designed to run under Phosh/Wayland on mustang (3120x1440@120 display).
Supports both interactive (GUI) and non-interactive (CLI) modes.

Device: Google Pixel 10 Pro XL (mustang)
Serial: 58211FDCQ001LA
"""

import argparse
import fcntl
import getpass
import hashlib
import os
import pwd
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, GLib, Gdk, Gio, Pango
    HAS_GTK = True
except (ImportError, ValueError):
    HAS_GTK = False

# ── Constants ──────────────────────────────────────────────────────────────

FIRSTBOOT_MARKER = "/var/lib/nuxel/.firstboot-complete"
NUXEL_CONFIG_DIR = "/etc/nuxel"
NUXEL_DATA_DIR = "/var/lib/nuxel"
DEVICE_INFO_FILE = os.path.join(NUXEL_CONFIG_DIR, "device-info")
CONFD_FILE = "/etc/conf.d/nuxel-firstboot"
NUXEL_HOME = "/home/nuxel"
NUXEL_UID = 1000
NUXEL_GID = 1000

# ── System helpers ─────────────────────────────────────────────────────────

def log(msg):
    """Log to syslog-style output."""
    ts = time.strftime("%b %d %H:%M:%S")
    print(f"{ts} nuxel-firstboot: {msg}", flush=True)


# Single-source path config (briq-20): load /etc/nuxel/paths.conf, overridable
# via the NUXEL_PATHS_CONF environment variable. This re-reads and overrides
# the module-level path constants so every hardcoded /etc/nuxel and
# /var/lib/nuxel path in this file follows the shared configuration. The
# first-boot marker resolves to NUXEL_FIRSTBOOT_MARKER=/var/lib/nuxel/
# .firstboot-complete (briq-22).
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")


def load_paths_conf():
    """Read the single-source paths.conf and update the module path constants.

    The config file path itself can be overridden with the NUXEL_PATHS_CONF
    environment variable. Environment variables always win over both the file
    and the compiled-in defaults.
    """
    global FIRSTBOOT_MARKER, NUXEL_CONFIG_DIR, NUXEL_DATA_DIR, DEVICE_INFO_FILE
    mapping = {
        "NUXEL_CONFIG_DIR": NUXEL_CONFIG_DIR,
        "NUXEL_DATA_DIR": NUXEL_DATA_DIR,
        "NUXEL_FIRSTBOOT_MARKER": FIRSTBOOT_MARKER,
    }
    if os.path.exists(NUXEL_PATHS_CONF):
        try:
            with open(NUXEL_PATHS_CONF) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key in mapping:
                        mapping[key] = val
        except OSError as e:
            log(f"Warning: could not read {NUXEL_PATHS_CONF}: {e}")
    # Environment overrides take highest precedence.
    for key in list(mapping.keys()):
        env = os.environ.get(key)
        if env:
            mapping[key] = env
    FIRSTBOOT_MARKER = mapping["NUXEL_FIRSTBOOT_MARKER"]
    NUXEL_CONFIG_DIR = mapping["NUXEL_CONFIG_DIR"]
    NUXEL_DATA_DIR = mapping["NUXEL_DATA_DIR"]
    DEVICE_INFO_FILE = os.path.join(NUXEL_CONFIG_DIR, "device-info")
    return mapping


load_paths_conf()


def load_confd():
    """Parse /etc/conf.d/nuxel-firstboot and return values dict."""
    cfg = {
        "default_user": "nuxel",
        "default_shell": "/bin/bash",
        "skip_wifi": False,
        "skip_user": False,
        "locale": "en_US.UTF-8",
        "timezone": "UTC",
        "keyboard_layout": "us",
        "keyboard_variant": "",
        "display_manager": "phosh",
        "auto_reboot": True,
    }
    if not os.path.exists(CONFD_FILE):
        return cfg
    try:
        with open(CONFD_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip().lower().replace("nuxel_", "", 1)
                val = val.strip().strip('"').strip("'")
                bool_keys = {"skip_wifi", "skip_user", "auto_reboot"}
                if key in bool_keys:
                    cfg[key] = val.lower() in ("yes", "true", "1")
                elif key in cfg:
                    cfg[key] = val
    except (OSError, IOError) as e:
        log(f"Warning: could not read {CONFD_FILE}: {e}")
    return cfg


def is_first_boot():
    """Check if the first-boot marker exists."""
    return os.path.exists(FIRSTBOOT_MARKER)


def ensure_state_dir():
    """Ensure the per-boot state directory (/var/lib/nuxel) exists.

    The first-boot marker (/var/lib/nuxel/.firstboot-complete) lives inside
    this directory, so it must be created before the marker can be written or
    removed. (briq-22)
    """
    try:
        os.makedirs(NUXEL_DATA_DIR, exist_ok=True)
    except OSError as e:
        log(f"Warning: could not create {NUXEL_DATA_DIR}: {e}")


def remove_firstboot_marker():
    """Remove the first-boot marker to prevent re-running."""
    ensure_state_dir()
    try:
        os.remove(FIRSTBOOT_MARKER)
        log("First-boot marker removed")
        return True
    except OSError as e:
        log(f"Error removing first-boot marker: {e}")
        return False


def disable_self():
    """Disable the first-boot service from running again."""
    subprocess.run(
        ["rc-update", "del", "nuxel-firstboot", "default"],
        capture_output=True, timeout=10
    )
    log("nuxel-firstboot service disabled")


def get_network_interfaces():
    """Get list of Wi-Fi network interfaces."""
    ifaces = []
    try:
        result = subprocess.run(
            ["iw", "dev"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                iface = line.split()[-1]
                ifaces.append(iface)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ifaces


def scan_wifi(iface="wlan0"):
    """Scan for available Wi-Fi networks on the given interface."""
    networks = []
    try:
        result = subprocess.run(
            ["iw", iface, "scan"],
            capture_output=True, text=True, timeout=15
        )
        current = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("BSS "):
                if current.get("ssid"):
                    networks.append(current)
                current = {"bssid": line.split()[1].strip("()")}
            elif line.startswith("SSID:"):
                current["ssid"] = line.split(":", 1)[1].strip()
            elif line.startswith("freq:"):
                current["freq"] = line.split()[-1]
            elif line.startswith("signal:"):
                try:
                    current["signal"] = float(line.split()[1])
                except (ValueError, IndexError):
                    current["signal"] = -100
            elif "WPA" in line or "RSN" in line:
                current.setdefault("security", []).append(
                    "WPA3" if "SAE" in line else "WPA2"
                )
        if current.get("ssid"):
            networks.append(current)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    # Deduplicate by SSID, keep strongest signal
    seen = {}
    for net in networks:
        ssid = net.get("ssid", "")
        if not ssid:
            continue
        if ssid not in seen or net.get("signal", -100) > seen[ssid].get("signal", -100):
            seen[ssid] = net
    result = sorted(seen.values(), key=lambda x: x.get("signal", -100), reverse=True)
    return result


def connect_wifi(ssid, password, iface="wlan0"):
    """Connect to a Wi-Fi network using wpa_supplicant and dhcpcd."""
    wpa_conf = f"""
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
    priority=10
}}
"""
    try:
        # Write temporary wpa_supplicant config
        tmp_conf = f"/tmp/nuxel-wpa-{iface}.conf"
        with open(tmp_conf, "w") as f:
            f.write('ctrl_interface=/var/run/wpa_supplicant\n')
            f.write('update_config=1\n')
            f.write(wpa_conf)

        # Kill any existing wpa_supplicant on this interface
        subprocess.run(
            ["pkill", "-f", f"wpa_supplicant.*{iface}"],
            capture_output=True, timeout=5
        )

        # Start wpa_supplicant
        subprocess.run(
            ["wpa_supplicant", "-B", "-i", iface, "-c", tmp_conf],
            capture_output=True, timeout=10
        )

        # Get IP via dhcpcd
        subprocess.run(
            ["dhcpcd", "-q", iface],
            capture_output=True, timeout=30
        )

        # Verify connectivity
        time.sleep(2)
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "5", "8.8.8.8"],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"Timeout connecting to WiFi {ssid}")
        return False
    except OSError as e:
        log(f"Error connecting to WiFi: {e}")
        return False


def create_user(username, display_name, shell="/bin/bash"):
    """Create the nuxel user account with the given username and display name."""
    try:
        # Check if user already exists
        try:
            pwd.getpwnam(username)
            log(f"User {username} already exists")
            return True
        except KeyError:
            pass

        # Create user group
        subprocess.run(
            ["groupadd", "--force", "--gid", str(NUXEL_GID), "nuxel"],
            capture_output=True, check=True
        )

        # Create the user
        subprocess.run(
            [
                "useradd",
                "--create-home",
                "--home-dir", f"/home/{username}",
                "--uid", str(NUXEL_UID),
                "--gid", str(NUXEL_GID),
                "--groups", "wheel,audio,video,input,netdev,dbus,nfc,nuxel",
                "--shell", shell,
                "--comment", display_name,
                "--password", "",
                username
            ],
            capture_output=True, check=True
        )

        # Set up user directories
        user_home = f"/home/{username}"
        for d in ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"]:
            os.makedirs(os.path.join(user_home, d), exist_ok=True)

        # Copy default configs
        skel_files = ["/etc/skel/.bashrc", "/etc/skel/.profile"]
        for src in skel_files:
            if os.path.exists(src):
                shutil.copy2(src, user_home)

        # Set ownership
        subprocess.run(
            ["chown", "-R", f"{NUXEL_UID}:{NUXEL_GID}", user_home],
            capture_output=True, check=True
        )

        # Set password to empty (user can change later via passwd)
        subprocess.run(
            ["passwd", "-d", username],
            capture_output=True, check=True
        )

        # Add user to sudo/wheel with no-password for first session
        sudoers_line = f"{username} ALL=(ALL) NOPASSWD: ALL"
        subprocess.run(
            ["sh", "-c", f"echo '{sudoers_line}' > /etc/sudoers.d/{username}"],
            capture_output=True, check=True
        )
        subprocess.run(
            ["chmod", "0440", f"/etc/sudoers.d/{username}"],
            capture_output=True, check=True
        )

        # Create XDG user directories
        try:
            subprocess.run(
                ["runuser", "-u", username, "xdg-user-dirs-update"],
                capture_output=True, timeout=15
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        log(f"User {username} created with display name '{display_name}'")
        return True

    except subprocess.CalledProcessError as e:
        log(f"Error creating user: {e}")
        log(f"  stdout: {e.stdout.decode() if e.stdout else ''}")
        log(f"  stderr: {e.stderr.decode() if e.stderr else ''}")
        return False
    except OSError as e:
        log(f"OS error creating user: {e}")
        return False


def set_locale(locale="en_US.UTF-8"):
    """Configure system locale."""
    try:
        with open("/etc/locale.conf", "w") as f:
            f.write(f"LANG={locale}\n")
            f.write(f"LC_ALL={locale}\n")
        log(f"Locale set to {locale}")
    except OSError as e:
        log(f"Error setting locale: {e}")


def set_timezone(tz="UTC"):
    """Set system timezone."""
    tz_file = f"/usr/share/zoneinfo/{tz}"
    if os.path.exists(tz_file):
        try:
            if os.path.islink("/etc/localtime"):
                os.remove("/etc/localtime")
            os.symlink(tz_file, "/etc/localtime")
            with open("/etc/timezone", "w") as f:
                f.write(f"{tz}\n")
            log(f"Timezone set to {tz}")
        except OSError as e:
            log(f"Error setting timezone: {e}")


def set_keyboard(layout="us", variant=""):
    """Configure keyboard layout."""
    try:
        variant_str = f'  variant "{variant}"' if variant else ""
        with open("/etc/vconsole.conf", "w") as f:
            f.write(f'KEYMAP="{layout}"\n')
            f.write(f'{variant_str}\n')
        log(f"Keyboard layout set to {layout}")
    except OSError as e:
        log(f"Error setting keyboard: {e}")


def reboot_device():
    """Reboot the device after setup."""
    log("Rebooting device...")
    subprocess.run(["reboot"], timeout=30)


def validate_username(name):
    """Validate a Linux username."""
    if not name:
        return "Username cannot be empty"
    if len(name) < 2:
        return "Username must be at least 2 characters"
    if len(name) > 31:
        return "Username must be 31 characters or less"
    if not re.match(r"^[a-z_][a-z0-9_-]*$", name):
        return "Username must start with a letter, contain only lowercase letters, digits, hyphens, underscores"
    try:
        pwd.getpwnam(name)
        return f"User '{name}' already exists"
    except KeyError:
        pass
    return ""


def validate_display_name(name):
    """Validate a display name."""
    if not name:
        return "Display name cannot be empty"
    if len(name) > 255:
        return "Display name too long"
    return ""


# ── GTK UI ─────────────────────────────────────────────────────────────────

class FirstBootWizard:
    """GTK4/Adwaita-based first-boot setup wizard."""

    def __init__(self, config):
        self.config = config
        self.username = ""
        self.display_name = ""
        self.wifi_ssid = ""
        self.wifi_password = ""
        self.wifi_iface = ""
        self.networks = []
        self.wizard_complete = False

        self.app = Adw.Application.new(
            "org.nuxel.FirstBoot",
            Gio.ApplicationFlags.FLAGS_NONE
        )
        self.app.connect("activate", self.on_activate)

    def on_activate(self, app):
        """Build and show the main window."""
        win = Adw.Window.new(app)
        win.set_title("Nuxel Setup")
        win.set_default_size(600, 700)
        win.set_resizable(False)
        win.set_modal(True)

        # Apply dark theme for phone use
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        # Full-screen on mustang display
        win.fullscreen()

        # Build the UI
        self.build_ui(win)
        win.present()

    def build_ui(self, win):
        """Build wizard pages using AdwCarousel or stacked pages."""
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(300)

        # Page 1: Welcome
        page_welcome = self.build_welcome_page()
        self.stack.add_titled(page_welcome, "welcome", "Welcome")

        # Page 2: User setup
        page_user = self.build_user_page()
        self.stack.add_titled(page_user, "user", "User")

        # Page 3: WiFi
        page_wifi = self.build_wifi_page()
        self.stack.add_titled(page_wifi, "wifi", "WiFi")

        # Page 4: Summary
        page_summary = self.build_summary_page()
        self.stack.add_titled(page_summary, "summary", "Summary")

        # Page 5: Setup progress
        page_progress = self.build_progress_page()
        self.stack.add_titled(page_progress, "progress", "Progress")

        self.stack.set_visible_child_name("welcome")
        win.set_child(self.stack)

    def build_welcome_page(self):
        """Build the welcome/intro page."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(80)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        # Logo / icon
        icon = Gtk.Image.new_from_icon_name("phone-os-symbolic")
        icon.set_pixel_size(96)
        icon.set_opacity(0.8)
        box.append(icon)

        # Title
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Welcome to Nuxel</span>")
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        # Subtitle
        subtitle = Gtk.Label()
        subtitle.set_markup(
            "Your new phone OS for the <b>Google Pixel 10 Pro XL</b>"
        )
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_opacity(0.7)
        box.append(subtitle)

        # Description
        desc = Gtk.Label(
            label="Let's get your phone set up. This one-time setup will create your user account "
                  "and connect you to Wi-Fi. It should only take a minute."
        )
        desc.set_wrap(True)
        desc.set_max_width_chars(50)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_halign(Gtk.Align.CENTER)
        desc.set_opacity(0.6)
        box.append(desc)

        # Device info
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_halign(Gtk.Align.CENTER)
        info_box.set_margin_top(16)

        badge = Adw.Badge.new()
        badge.set_text("mustang")
        info_box.append(badge)

        badge2 = Adw.Badge.new()
        badge2.set_text("Tensor G5")
        info_box.append(badge2)

        badge3 = Adw.Badge.new()
        badge3.set_text("Linux 6.12")
        info_box.append(badge3)

        box.append(info_box)

        # Start button
        btn = Gtk.Button(label="Get Started")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_size_request(280, 48)
        btn.set_margin_top(24)
        btn.connect("clicked", lambda _: self.go_to_page("user"))
        box.append(btn)

        frame = Gtk.Frame()
        frame.set_child(box)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        return box

    def build_user_page(self):
        """Build the user creation page."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(60)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)

        # Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Create Your Account</span>")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        subtitle = Gtk.Label(
            label="This will be your main user account for the phone."
        )
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_opacity(0.7)
        box.append(subtitle)

        box.append(Gtk.Separator())

        # Username field
        username_label = Gtk.Label(label="Username")
        username_label.set_halign(Gtk.Align.START)
        username_label.set_margin_top(8)
        box.append(username_label)

        self.username_entry = Adw.EntryRow()
        self.username_entry.set_placeholder_text("e.g. alice")
        self.username_entry.set_text(self.config.get("default_user", "nuxel"))
        self.username_entry.connect("changed", self.on_username_changed)
        box.append(self.username_entry)

        self.username_error = Gtk.Label()
        self.username_error.set_halign(Gtk.Align.START)
        self.username_error.add_css_class("error")
        self.username_error.set_opacity(0.8)
        self.username_error.set_visible(False)
        box.append(self.username_error)

        # Display name field
        display_label = Gtk.Label(label="Display Name")
        display_label.set_halign(Gtk.Align.START)
        display_label.set_margin_top(12)
        box.append(display_label)

        self.display_entry = Adw.EntryRow()
        self.display_entry.set_placeholder_text("e.g. Alice")
        self.display_entry.set_text("Nuxel User")
        self.display_entry.connect("changed", self.on_display_changed)
        box.append(self.display_entry)

        self.display_error = Gtk.Label()
        self.display_error.set_halign(Gtk.Align.START)
        self.display_error.add_css_class("error")
        self.display_error.set_opacity(0.8)
        self.display_error.set_visible(False)
        box.append(self.display_error)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        # Navigation buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label="Back")
        back_btn.connect("clicked", lambda _: self.go_to_page("welcome"))
        button_box.append(back_btn)

        next_btn = Gtk.Button(label="Next")
        next_btn.add_css_class("suggested-action")
        next_btn.connect("clicked", lambda _: self.on_user_next())
        next_btn.set_sensitive(False)
        self.user_next_btn = next_btn
        button_box.append(next_btn)

        box.append(button_box)

        return box

    def on_username_changed(self, entry):
        """Validate username as user types."""
        name = entry.get_text().strip()
        error = validate_username(name)
        if error and name:
            self.username_error.set_text(error)
            self.username_error.set_visible(True)
            self.user_next_btn.set_sensitive(False)
        else:
            self.username_error.set_visible(False)
            self.check_user_form_valid()

    def on_display_changed(self, entry):
        """Validate display name as user types."""
        name = entry.get_text().strip()
        error = validate_display_name(name)
        if error and name:
            self.display_error.set_text(error)
            self.display_error.set_visible(True)
            self.user_next_btn.set_sensitive(False)
        else:
            self.display_error.set_visible(False)
            self.check_user_form_valid()

    def check_user_form_valid(self):
        """Enable next button if form is valid."""
        uname = self.username_entry.get_text().strip()
        dname = self.display_entry.get_text().strip()
        valid = (
            len(uname) >= 2 and not validate_username(uname)
            and len(dname) >= 1 and not validate_display_name(dname)
        )
        self.user_next_btn.set_sensitive(valid)

    def on_user_next(self):
        """Save user info and go to WiFi page."""
        self.username = self.username_entry.get_text().strip()
        self.display_name = self.display_entry.get_text().strip()
        self.go_to_page("wifi")

    def build_wifi_page(self):
        """Build the WiFi selection page."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(60)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Connect to Wi-Fi</span>")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        subtitle = Gtk.Label(
            label="Select your Wi-Fi network to connect to the internet."
        )
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_opacity(0.7)
        box.append(subtitle)

        box.append(Gtk.Separator())

        # Scan button
        scan_btn = Gtk.Button(label="Scan for Networks")
        scan_btn.add_css_class("pill")
        scan_btn.connect("clicked", lambda _: self.scan_networks())
        self.scan_btn = scan_btn
        box.append(scan_btn)

        # Network list (placeholder - populated by scan)
        self.network_list = Gtk.ListBox()
        self.network_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.network_list.connect("row-selected", self.on_network_selected)
        self.network_list.set_visible(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.set_child(self.network_list)
        box.append(scroll)

        self.scanning_label = Gtk.Label(label="")
        self.scanning_label.set_halign(Gtk.Align.CENTER)
        self.scanning_label.set_opacity(0.6)
        box.append(self.scanning_label)

        # Password field (shown when network selected)
        self.password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.password_box.set_visible(False)

        pw_label = Gtk.Label(label="Wi-Fi Password")
        pw_label.set_halign(Gtk.Align.START)
        self.password_box.append(pw_label)

        self.password_entry = Adw.EntryRow()
        self.password_entry.set_placeholder_text("Enter password")
        self.password_entry.set_visibility(False)
        self.password_entry.connect("activate", lambda _: self.on_wifi_connect())
        self.password_box.append(self.password_entry)

        box.append(self.password_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        # Skip button
        skip_btn = Gtk.Button(label="Skip Wi-Fi Setup")
        skip_btn.set_opacity(0.5)
        skip_btn.connect("clicked", lambda _: self.on_wifi_skip())
        box.append(skip_btn)

        # Navigation
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label="Back")
        back_btn.connect("clicked", lambda _: self.go_to_page("user"))
        button_box.append(back_btn)

        connect_btn = Gtk.Button(label="Connect")
        connect_btn.add_css_class("suggested-action")
        connect_btn.set_sensitive(False)
        connect_btn.connect("clicked", lambda _: self.on_wifi_connect())
        self.connect_btn = connect_btn
        button_box.append(connect_btn)

        box.append(button_box)

        return box

    def scan_networks(self):
        """Scan for Wi-Fi networks and populate the list."""
        self.scanning_label.set_text("Scanning...")
        self.scan_btn.set_sensitive(False)
        self.network_list.remove_all()
        self.network_list.set_visible(False)

        ifaces = get_network_interfaces()
        if not ifaces:
            self.scanning_label.set_text(
                "No Wi-Fi interface found. You can skip this step."
            )
            self.scan_btn.set_sensitive(True)
            return

        self.wifi_iface = ifaces[0]
        self.networks = scan_wifi(self.wifi_iface)

        if not self.networks:
            self.scanning_label.set_text("No networks found. Try again or skip.")
            self.scan_btn.set_sensitive(True)
            return

        self.scanning_label.set_text(
            f"Found {len(self.networks)} networks on {self.wifi_iface}"
        )
        self.network_list.set_visible(True)

        for net in self.networks:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)

            # Signal indicator
            signal = net.get("signal", -100)
            if signal > -50:
                sig_icon = "network-wireless-signal-excellent-symbolic"
            elif signal > -65:
                sig_icon = "network-wireless-signal-good-symbolic"
            elif signal > -75:
                sig_icon = "network-wireless-signal-ok-symbolic"
            else:
                sig_icon = "network-wireless-signal-weak-symbolic"
            icon = Gtk.Image.new_from_icon_name(sig_icon)
            icon.set_pixel_size(24)
            hbox.append(icon)

            # SSID
            ssid_label = Gtk.Label(label=net.get("ssid", "Hidden Network"))
            ssid_label.set_halign(Gtk.Align.START)
            ssid_label.set_hexpand(True)
            hbox.append(ssid_label)

            # Security badge
            sec = net.get("security", [])
            if sec:
                badge = Adw.Badge.new()
                badge.set_text("WPA3" if "WPA3" in sec else "WPA2")
                hbox.append(badge)

            row.set_child(hbox)
            self.network_list.append(row)

        self.scan_btn.set_sensitive(True)

    def on_network_selected(self, listbox, row):
        """Handle network selection from the list."""
        if row is None:
            return
        idx = row.get_index()
        if idx < len(self.networks):
            self.wifi_ssid = self.networks[idx].get("ssid", "")
            sec = self.networks[idx].get("security", [])
            needs_pw = bool(sec) or True  # Most home networks need a password
            self.password_box.set_visible(needs_pw)
            self.connect_btn.set_sensitive(True)
            if needs_pw:
                self.password_entry.grab_focus()
            else:
                self.on_wifi_connect()

    def on_wifi_connect(self):
        """Proceed to connect to selected WiFi."""
        self.wifi_password = self.password_entry.get_text().strip()
        name = self.username or self.config.get("default_user", "nuxel")
        dname = self.display_name or "Nuxel User"

        log(f"WiFi: connecting to {self.wifi_ssid}")
        log(f"User: {name} / {dname}")

        self.go_to_page("progress")

    def on_wifi_skip(self):
        """Skip WiFi setup."""
        self.wifi_ssid = ""
        self.wifi_password = ""
        name = self.username or self.config.get("default_user", "nuxel")
        dname = self.display_name or "Nuxel User"

        log("WiFi setup skipped")
        log(f"User: {name} / {dname}")

        self.go_to_page("progress")

    def build_summary_page(self):
        """Build the summary page showing what will be configured."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(60)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Ready to Go</span>")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        subtitle = Gtk.Label(
            label="Review your choices before we begin setup."
        )
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_opacity(0.7)
        box.append(subtitle)

        box.append(Gtk.Separator())

        # Summary items
        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        summary_box.set_margin_top(12)

        items = [
            ("person", f"Username: {self.username}"),
            ("avatar-default", f"Display Name: {self.display_name}"),
        ]

        if self.wifi_ssid:
            items.append(
                ("network-wireless", f"Wi-Fi: {self.wifi_ssid}")
            )
        else:
            items.append(
                ("network-wireless", "Wi-Fi: Skipped (connect later)")
            )

        items.append(("phone-os", "Device: Pixel 10 Pro XL (mustang)"))

        for icon_name, text in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(20)
            row.append(icon)
            label = Gtk.Label(label=text)
            label.set_halign(Gtk.Align.START)
            row.append(label)
            summary_box.append(row)

        box.append(summary_box)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)

        back_btn = Gtk.Button(label="Back")
        back_btn.connect("clicked", lambda _: self.go_to_page("wifi"))
        button_box.append(back_btn)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", lambda _: self.go_to_page("progress"))
        button_box.append(apply_btn)

        box.append(button_box)

        return box

    def build_progress_page(self):
        """Build the progress/status page showing setup steps."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_margin_top(60)
        box.set_margin_bottom(40)
        box.set_margin_start(40)
        box.set_margin_end(40)

        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Setting Up Your Phone</span>")
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(12)
        box.append(title)

        # Spinner
        spinner = Gtk.Spinner()
        spinner.set_size_request(48, 48)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.start()
        box.append(spinner)

        # Progress list
        self.progress_list = Gtk.ListBox()
        self.progress_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.progress_list.set_sensitive(False)

        self.steps = [
            ("Creating user account...", "pending"),
            ("Setting up home directories...", "pending"),
            ("Configuring system locale...", "pending"),
            ("Setting up Wi-Fi...", "pending"),
            ("Finalizing setup...", "pending"),
        ]
        self.step_labels = []

        for step_text, _ in self.steps:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)

            icon = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic")
            icon.set_pixel_size(16)
            icon.set_opacity(0.5)
            hbox.append(icon)

            lbl = Gtk.Label(label=step_text)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_opacity(0.5)
            hbox.append(lbl)

            row.set_child(hbox)
            self.progress_list.append(row)
            self.step_labels.append((hbox, icon, lbl))

        box.append(self.progress_list)

        # Status label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.CENTER)
        self.status_label.set_opacity(0.6)
        box.append(self.status_label)

        return box

    def go_to_page(self, page_name):
        """Transition to the given page."""
        self.stack.set_visible_child_name(page_name)
        if page_name == "progress":
            self.run_setup()

    def mark_step(self, index, status):
        """Mark a step as running, done, or failed."""
        if index >= len(self.step_labels):
            return
        hbox, icon, lbl = self.step_labels[index]
        if status == "running":
            icon.set_from_icon_name("media-playback-start-symbolic")
            icon.set_opacity(1.0)
            lbl.set_opacity(1.0)
        elif status == "done":
            icon.set_from_icon_name("emblem-ok-symbolic")
            icon.set_opacity(1.0)
            lbl.set_opacity(0.8)
        elif status == "failed":
            icon.set_from_icon_name("dialog-warning-symbolic")
            icon.set_opacity(1.0)

    def run_setup(self):
        """Execute the setup steps in sequence with UI updates."""
        def do_setup():
            success = True

            # Step 0: Create user
            GLib.idle_add(lambda: self.mark_step(0, "running"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Creating user account...")
            )
            time.sleep(0.5)

            user_ok = create_user(self.username, self.display_name)
            if user_ok:
                GLib.idle_add(lambda: self.mark_step(0, "done"))
            else:
                GLib.idle_add(lambda: self.mark_step(0, "failed"))
                success = False

            # Step 1: Home directories
            GLib.idle_add(lambda: self.mark_step(1, "running"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Setting up home directories...")
            )
            time.sleep(0.3)

            home = f"/home/{self.username}"
            GLib.idle_add(lambda: self.mark_step(1, "done"))

            # Step 2: Locale and timezone
            GLib.idle_add(lambda: self.mark_step(2, "running"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Configuring system...")
            )
            time.sleep(0.3)

            set_locale(self.config.get("locale", "en_US.UTF-8"))
            set_timezone(self.config.get("timezone", "UTC"))
            set_keyboard(
                self.config.get("keyboard_layout", "us"),
                self.config.get("keyboard_variant", "")
            )
            GLib.idle_add(lambda: self.mark_step(2, "done"))

            # Step 3: WiFi
            GLib.idle_add(lambda: self.mark_step(3, "running"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Connecting to Wi-Fi...")
            )

            if self.wifi_ssid and self.wifi_password:
                wifi_ok = connect_wifi(
                    self.wifi_ssid, self.wifi_password, self.wifi_iface
                )
                if wifi_ok:
                    GLib.idle_add(lambda: self.mark_step(3, "done"))
                else:
                    GLib.idle_add(lambda: self.mark_step(3, "failed"))
                    GLib.idle_add(
                        lambda: self.status_label.set_text(
                            "Wi-Fi connection failed. Connect later in Settings."
                        )
                    )
            else:
                GLib.idle_add(lambda: self.mark_step(3, "done"))
                GLib.idle_add(
                    lambda: self.status_label.set_text(
                        "Wi-Fi setup skipped."
                    )
                )
            time.sleep(0.5)

            # Step 4: Finalize
            GLib.idle_add(lambda: self.mark_step(4, "running"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Finalizing setup...")
            )
            time.sleep(0.5)

            remove_firstboot_marker()
            disable_self()

            GLib.idle_add(lambda: self.mark_step(4, "done"))
            GLib.idle_add(
                lambda: self.status_label.set_text("Setup complete! Rebooting...")
            )
            time.sleep(2)

            # Reboot
            if self.config.get("auto_reboot", True):
                GLib.idle_add(reboot_device)
            else:
                GLib.idle_add(
                    lambda: self.status_label.set_text(
                        "Setup complete! Please reboot manually."
                    )
                )

            return False

        import threading
        t = threading.Thread(target=do_setup, daemon=True)
        t.start()

    def run(self):
        """Run the GTK application."""
        self.app.run(sys.argv)


# ── CLI mode (no GTK) ──────────────────────────────────────────────────────

def cli_mode(config):
    """Run setup in non-interactive CLI mode."""
    if not is_first_boot():
        log("No first-boot marker found. Nothing to do.")
        return 0

    log("Running first-boot setup in CLI mode")

    username = config.get("default_user", "nuxel")
    display_name = "Nuxel User"

    print("\n==============================================")
    print("  Nuxel First-Boot Setup (CLI)")
    print("  Google Pixel 10 Pro XL (mustang)")
    print("==============================================\n")

    # User input
    try:
        inp = input(f"Username [{username}]: ").strip()
        if inp:
            username = inp
        inp = input(f"Display Name [{display_name}]: ").strip()
        if inp:
            display_name = inp
    except (EOFError, KeyboardInterrupt):
        print()

    # Validate
    err = validate_username(username)
    if err:
        log(f"Invalid username: {err}")
        print(f"Error: {err}")
        return 1

    err = validate_display_name(display_name)
    if err:
        log(f"Invalid display name: {err}")
        print(f"Error: {err}")
        return 1

    print(f"\nCreating user: {username} ({display_name})")

    # Create user
    if not create_user(username, display_name):
        log("Failed to create user")
        return 1

    # Locale
    set_locale(config.get("locale", "en_US.UTF-8"))
    set_timezone(config.get("timezone", "UTC"))
    set_keyboard(
        config.get("keyboard_layout", "us"),
        config.get("keyboard_variant", "")
    )
    log("System configured")

    # WiFi
    if not config.get("skip_wifi", False):
        try:
            inp = input("Connect to Wi-Fi? [Y/n]: ").strip().lower()
            if inp not in ("n", "no"):
                ifaces = get_network_interfaces()
                if ifaces:
                    print(f"Wi-Fi interfaces: {', '.join(ifaces)}")
                    iface = ifaces[0]
                    networks = scan_wifi(iface)
                    if networks:
                        print("\nAvailable networks:")
                        for i, net in enumerate(networks[:20]):
                            sig = net.get("signal", -100)
                            bars = "▂▄▆█" if sig > -50 else "▂▄▆" if sig > -65 else "▂▄" if sig > -75 else "▂"
                            sec = ",".join(net.get("security", ["open"]))
                            print(f"  {i+1:>2}. {bars} {net.get('ssid', 'Hidden'):30s} [{sec}]")

                        try:
                            choice = input("\nSelect network number (or 0 to skip): ").strip()
                            if choice.isdigit():
                                idx = int(choice) - 1
                                if 0 <= idx < len(networks):
                                    ssid = networks[idx].get("ssid", "")
                                    password = getpass.getpass(f"Password for {ssid}: ")
                                    if connect_wifi(ssid, password, iface):
                                        print(f"Connected to {ssid}")
                                    else:
                                        print("Connection failed (can retry later)")
                        except (EOFError, KeyboardInterrupt):
                            print()
        except (EOFError, KeyboardInterrupt):
            print()

    # Finalize
    remove_firstboot_marker()
    disable_self()

    print("\nSetup complete!")
    return 0


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Nuxel First-Boot Setup Wizard"
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="Run in CLI mode (no GTK required)"
    )
    parser.add_argument(
        "--username", type=str,
        help="Username to create (CLI mode)"
    )
    parser.add_argument(
        "--display-name", type=str,
        help="Display name for the user (CLI mode)"
    )
    parser.add_argument(
        "--skip-wifi", action="store_true",
        help="Skip Wi-Fi setup (CLI mode)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Run even if first-boot marker is missing"
    )
    args = parser.parse_args()

    # Ensure the state directory exists so the first-boot marker and any
    # per-boot state can be created/removed (briq-22).
    ensure_state_dir()

    # Check if we should run
    if not is_first_boot() and not args.force:
        log("First-boot marker not found. Skipping setup.")
        return 0

    config = load_confd()

    # Override config from CLI args
    if args.skip_wifi:
        config["skip_wifi"] = True

    # Determine mode
    use_cli = args.cli or not HAS_GTK

    if use_cli:
        return cli_mode(config)
    else:
        wizard = FirstBootWizard(config)
        wizard.run()
        return 0


if __name__ == "__main__":
    sys.exit(main())
