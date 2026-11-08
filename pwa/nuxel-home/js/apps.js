// Nuxel Home - App Registry (A63 revision 5)
// Defines the default app list with metadata.
//
// SINGLE SOURCE OF TRUTH (briq-02d): the registry below is what both the handset
// and the UTM VM must serve.  The phone's copy had drifted (missing Terminal,
// stale status-bar/manifest), so this revision carries a machine-readable
// REGISTRY_VERSION that the launcher publishes on its evidence channel and that
// tools/s10plus/a33/tests/launcher-registry-test.js asserts ("org.nuxel.Terminal"
// and "nuxel-settings" present, every PWA served under /pwa/nuxel-apps/).
const NUXEL_REGISTRY_VERSION = 16;

const NUXEL_APPS = {
    // Native shell apps
    'nuxel-dialer': {
        id: 'nuxel-dialer',
        name: 'Phone',
        icon: '📞',
        color: '#4CAF50',
        category: 'communication',
        type: 'native',
        url: 'nuxel-dialer://',
        description: 'Make phone calls',
        capabilities: ['call:initiate', 'call:end', 'call:status', 'contacts:read'],
        docked: true,
    },
    'nuxel-messages': {
        id: 'nuxel-messages',
        name: 'Messages',
        icon: '💬',
        color: '#2196F3',
        category: 'communication',
        type: 'native',
        url: 'nuxel-messages://',
        description: 'Send and receive SMS',
        capabilities: ['sms:send', 'sms:receive', 'contacts:read'],
        docked: true,
    },
    'nuxel-contacts': {
        id: 'nuxel-contacts',
        name: 'Contacts',
        icon: '👤',
        color: '#9C27B0',
        category: 'communication',
        type: 'native',
        url: 'nuxel-contacts://',
        description: 'Manage your contacts',
        capabilities: ['contacts:read', 'contacts:write'],
        docked: false,
    },

    // PWA apps
    'org.nuxel.Clipper': {
        id: 'org.nuxel.Clipper',
        name: 'Clipper',
        icon: '📋',
        color: '#00BCD4',
        category: 'tools',
        type: 'pwa',
        url: '/pwa/nuxel-apps/clipper/index.html',
        description: 'Clipboard history and quick copy manager',
        capabilities: ['clipboard:read', 'clipboard:write'],
        docked: false,
    },
    'org.nuxel.Mail': {
        id: 'org.nuxel.Mail',
        name: 'Mail',
        icon: '✉️',
        color: '#FF9800',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/mail/index.html',
        description: 'Email client',
        capabilities: ['notifications:send', 'notifications:receive'],
        docked: false,
    },
    'org.nuxel.Calendar': {
        id: 'org.nuxel.Calendar',
        name: 'Calendar',
        icon: '📅',
        color: '#E91E63',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/calendar/index.html',
        description: 'Calendar and events',
        capabilities: ['notifications:send'],
        docked: false,
    },
    'org.nuxel.Browser': {
        id: 'org.nuxel.Browser', name: 'Browser', icon: '🌐', color: '#297ad7',
        category: 'tools', type: 'native',
        url: '/pwa/nuxel-apps/browser/index.html',
        nativeAppId: 'org.nuxel.BrowserNative',
        native_binary: '/usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py',
        description: 'Nuxel Browser — real top-level WebKitGTK browser (HTTPS)',
        capabilities: ['network:outbound', 'storage:persistent'], docked: false,
    },
    'org.nuxel.Notes': {
        id: 'org.nuxel.Notes',
        name: 'Notes',
        icon: '📝',
        color: '#607D8B',
        category: 'productivity',
        type: 'pwa',
        url: '/pwa/nuxel-apps/notes/index.html',
        description: 'Take notes',
        capabilities: [],
        docked: false,
    },
    'org.nuxel.Files': {
        id: 'org.nuxel.Files',
        name: 'Files',
        icon: '📁',
        color: '#3F51B5',
        category: 'tools',
        type: 'pwa',
        url: '/pwa/nuxel-apps/files/index.html',
        description: 'File browser',
        capabilities: [],
        docked: false,
    },
    'nuxel-camera': {
        id: 'nuxel-camera',
        name: 'Camera',
        icon: '📷',
        color: '#795548',
        category: 'media',
        type: 'native',
        url: 'nuxel-camera://',
        nativeAppId: 'org.nuxel.CameraNative',
        native_binary: '/usr/lib/nuxel/nuxel-camera-native/nuxel_camera_native.py',
        description: 'Nuxel Camera — honest hardware status + capture',
        capabilities: ['camera:capture', 'camera:preview'],
        docked: false,
    },

    // System apps
    'nuxel-settings': {
        id: 'nuxel-settings',
        name: 'Settings',
        icon: '⚙️',
        color: '#78909C',
        category: 'system',
        // A32: the native GTK4 placeholder (nuxel-settings://) has no implementation
        // on the handset OR in the VM, so the authoritative Settings surface is the
        // Nuxel Settings PWA under the same registry id: Display (status bar /
        // camera cutout safe zones, screen on/off), Sound (real ALSA volume),
        // Buttons & Gestures (Power/Bixby remapping) and Developer status.
        type: 'pwa',
        url: '/pwa/nuxel-apps/settings/index.html',
        description: 'System settings',
        capabilities: [],
        docked: true,
    },
    'org.nuxel.Firewall': {
        id: 'org.nuxel.Firewall',
        name: 'Firewall',
        icon: '🛡️',
        color: '#3ea6ff',
        category: 'security',
        type: 'pwa',
        url: '/pwa/nuxel-apps/firewall/index.html',
        description: 'Firewall control center',
        capabilities: ['system:inspect', 'network:manage'],
        docked: false,
    },
    'org.nuxel.Permissions': {
        id: 'org.nuxel.Permissions',
        name: 'Permissions',
        icon: '🔐',
        color: '#4caf50',
        category: 'security',
        type: 'pwa',
        url: '/pwa/nuxel-apps/permissions/index.html',
        description: 'Permission manager (same policy service as Settings)',
        capabilities: ['system:inspect'],
        docked: false,
    },
    'org.nuxel.Terminal': {
        id: 'org.nuxel.Terminal',
        name: 'Terminal',
        icon: '🖥️',
        color: '#263238',
        category: 'system',
        // A32: the Nuxel Terminal — a real PTY (/bin/sh through the launcher host),
        // one instance only.  The Bixby button opens this by default (mission 13).
        type: 'pwa',
        url: '/pwa/nuxel-apps/terminal/index.html',
        description: 'Nuxel shell console',
        capabilities: [],
        docked: true,
    },
    // NUXEL-28000 Tri-Link: three distinct Applications entries.  They stay
    // visible even when a transport is unavailable; the app itself reports the
    // truthful state.  Each entry has its own icon and its own handler page.
    'org.nuxel.LiveConsole': {
        id: 'org.nuxel.LiveConsole',
        name: 'Serial Live Console',
        icon: '📟',
        color: '#37474F',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/console/index.html',
        description: 'USB CDC-ACM recovery console (exclusive serial owner)',
        capabilities: [],
        docked: false,
        consoleTransport: 'serial',
    },
    'org.nuxel.USBSSHConsole': {
        id: 'org.nuxel.USBSSHConsole',
        name: 'USB SSH Console',
        icon: '🔌',
        color: '#6D4C41',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/console-usb/index.html',
        description: 'SSH over the USB network gadget (honest kernel blocker state)',
        capabilities: [],
        docked: false,
        consoleTransport: 'usb',
    },
    'org.nuxel.WiFiSSHConsole': {
        id: 'org.nuxel.WiFiSSHConsole',
        name: 'Wi-Fi SSH Console',
        icon: '📶',
        color: '#0288D1',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/console-wifi/index.html',
        description: 'Key-only SSH over the phone Wi-Fi address',
        capabilities: [],
        docked: false,
        consoleTransport: 'wifi',
    },
    // PWNAGE-47000 GUI Tri-Link: three graphical remote-access entries.  They
    // are separate from the serial/SSH console entries and never auto-start.
    'org.nuxel.RemoteDesktopXRDP': {
        id: 'org.nuxel.RemoteDesktopXRDP',
        name: 'XRDP Remote Desktop',
        icon: '🖥️',
        color: '#5db7ff',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/remote-xrdp/index.html',
        description: 'Separate authenticated RDP/TLS X11 session (Wi-Fi preferred)',
        capabilities: [], docked: false, remoteService: 'xrdp',
    },
    'org.nuxel.RemoteDesktopVNC': {
        id: 'org.nuxel.RemoteDesktopVNC',
        name: 'VNC Screen Sharing',
        icon: '🖵',
        color: '#48d597',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/remote-vnc/index.html',
        description: 'Share the actual Phoc/Wayland screen (Wi-Fi preferred)',
        capabilities: [], docked: false, remoteService: 'vnc',
    },
    'org.nuxel.ScrcpyMirror': {
        id: 'org.nuxel.ScrcpyMirror',
        name: 'scrcpy (Android)',
        icon: '📱',
        color: '#b68cff',
        category: 'system',
        type: 'pwa',
        url: '/pwa/nuxel-apps/remote-scrcpy/index.html',
        description: 'Official scrcpy for Android ADB targets only',
        capabilities: [], docked: false, remoteService: 'scrcpy',
    },

    // A59: user-facing apps authored in pwa/nuxel-apps but previously missing
    // from the launcher. Each resolves to a real index.html + manifest.json.
    'org.nuxel.Calculator': {
        id: 'org.nuxel.Calculator', name: 'Calculator', icon: '🧮', color: '#009688',
        category: 'tools', type: 'pwa',
        url: '/pwa/nuxel-apps/calculator/index.html',
        description: 'Calculator', capabilities: [], docked: false,
    },
    'org.nuxel.Clock': {
        id: 'org.nuxel.Clock', name: 'Clock', icon: '⏰', color: '#455A64',
        category: 'tools', type: 'pwa',
        url: '/pwa/nuxel-apps/clock/index.html',
        description: 'Clock, alarms and timers',
        capabilities: ['notifications:send', 'storage:persistent'], docked: false,
    },
    'org.nuxel.Photos': {
        id: 'org.nuxel.Photos', name: 'Gallery', icon: '🖼️', color: '#F06292',
        category: 'media', type: 'pwa',
        url: '/pwa/nuxel-apps/photos/index.html',
        description: 'Browse photos and videos', capabilities: ['storage:persistent'], docked: false,
    },
    'org.nuxel.Weather': {
        id: 'org.nuxel.Weather', name: 'Weather', icon: '⛅', color: '#29B6F6',
        category: 'tools', type: 'pwa',
        url: '/pwa/nuxel-apps/weather/index.html',
        description: 'Weather forecast',
        capabilities: ['storage:persistent', 'network:outbound'], docked: false,
    },
    'org.nuxel.Maps': {
        id: 'org.nuxel.Maps', name: 'Maps', icon: '🗺️', color: '#7CB342',
        category: 'tools', type: 'pwa',
        url: '/pwa/nuxel-apps/maps/index.html',
        description: 'Maps and navigation',
        capabilities: ['location:read', 'storage:persistent', 'network:outbound'], docked: false,
    },
    'org.nuxel.Nuxtore': {
        id: 'org.nuxel.Nuxtore', name: 'NuxTore', icon: '🛍️', color: '#FF7043',
        category: 'tools', type: 'pwa',
        url: '/pwa/nuxel-apps/nuxtore/index.html',
        description: 'Nuxel app catalog',
        capabilities: ['catalog:read', 'catalog:install', 'catalog:remove'], docked: false,
    },
    'org.nuxel.Recorder': {
        id: 'org.nuxel.Recorder', name: 'Recorder', icon: '🎙️', color: '#D32F2F',
        category: 'media', type: 'pwa',
        url: '/pwa/nuxel-apps/recorder/index.html',
        description: 'Voice recorder', capabilities: ['storage:persistent'], docked: false,
    },
    'org.nuxel.Doom': {
        id: 'org.nuxel.Doom', name: 'Nuxel Doom', icon: '🎮', color: '#ff7a2f',
        category: 'games', type: 'pwa',
        url: '/pwa/nuxel-apps/doom/index.html',
        description: 'Chocolate Doom WebAssembly — Freedoom and imported WADs',
        capabilities: [], docked: false,
    },
    'org.nuxel.SnekByte': {
        id: 'org.nuxel.SnekByte', name: 'SnekByte', icon: '🐍', color: '#66BB6A',
        category: 'games', type: 'pwa',
        url: '/pwa/nuxel-apps/snekbyte/index.html',
        description: 'SnekByte — Nuxel Arcade',
        capabilities: ['input:keyboard', 'input:touch'], docked: false,
    },

    // PWNAGE-43000: real Flatpak applications and lightweight native tools.
    // Each entry has a launchable executable plus its real desktop/icon source.
    'org.mozilla.firefox': {
        id: 'org.mozilla.firefox', name: 'Firefox', icon: '🦊', color: '#ff7139',
        category: 'tools', type: 'native',
        url: 'org.mozilla.firefox://',
        native_binary: '/usr/bin/firefox',
        description: 'Firefox (Flatpak aarch64; unprivileged Bubblewrap sandbox)',
        capabilities: ['network:outbound', 'storage:persistent'], docked: false,
    },
    'org.videolan.VLC': {
        id: 'org.videolan.VLC', name: 'VLC', icon: '🎬', color: '#ff8800',
        category: 'media', type: 'native',
        url: 'org.videolan.VLC://',
        native_binary: '/usr/lib/nuxel/nuxel-vlc-fallback',
        description: 'VLC (Flatpak aarch64; KDE runtime)',
        capabilities: ['storage:persistent', 'audio:output'], docked: false,
    },
    'org.signal.Signal': {
        id: 'org.signal.Signal', name: 'Signal', icon: '💬', color: '#3a76f0',
        category: 'communication', type: 'native',
        url: 'org.signal.Signal://',
        native_binary: '/usr/lib/nuxel/nuxel-flatpak-signal',
        description: 'Signal Desktop (Flatpak aarch64; unprivileged Bubblewrap sandbox)',
        capabilities: ['network:outbound', 'storage:persistent'], docked: false,
    },
    'com.stremio.Stremio': {
        id: 'com.stremio.Stremio', name: 'Stremio', icon: '🍿', color: '#7b5cff',
        category: 'media', type: 'native',
        url: 'com.stremio.Stremio://',
        native_binary: '/usr/lib/nuxel/nuxel-flatpak-stremio',
        description: 'Stremio (Flatpak aarch64; GNOME runtime)',
        capabilities: ['network:outbound', 'storage:persistent'], docked: false,
    },
    'org.gnome.FileRoller': {
        id: 'org.gnome.FileRoller', name: 'Archive Manager', icon: '🗜️', color: '#d6a45c',
        category: 'tools', type: 'native',
        url: 'org.gnome.FileRoller://',
        native_binary: '/usr/bin/file-roller',
        description: 'Archive manager (Fedora aarch64 RPM)',
        capabilities: ['storage:persistent'], docked: false,
    },
    'org.gnome.Loupe': {
        id: 'org.gnome.Loupe', name: 'Image Viewer', icon: '🖼️', color: '#4a90e2',
        category: 'media', type: 'native',
        url: 'org.gnome.Loupe://',
        native_binary: '/usr/bin/loupe',
        description: 'GNOME Loupe image viewer (Fedora aarch64 RPM)',
        capabilities: ['storage:persistent'], docked: false,
    },
    'org.gnome.Papers': {
        id: 'org.gnome.Papers', name: 'Document Viewer', icon: '📄', color: '#e05d5d',
        category: 'productivity', type: 'native',
        url: 'org.gnome.Papers://',
        native_binary: '/usr/bin/papers',
        description: 'GNOME Papers PDF/document viewer (Fedora aarch64 RPM)',
        capabilities: ['storage:persistent'], docked: false,
    },
    'org.gnome.SystemMonitor': {
        id: 'org.gnome.SystemMonitor', name: 'System Monitor', icon: '📈', color: '#4caf50',
        category: 'system', type: 'native',
        url: 'org.gnome.SystemMonitor://',
        native_binary: '/usr/bin/gnome-system-monitor',
        description: 'Live CPU/memory/process monitor (Fedora aarch64 RPM)',
        capabilities: [], docked: false,
    },
    // PWNAGE-45000: shipped local catalog apps and the native Software center.
    'org.nuxel.Media': {
        id: 'org.nuxel.Media', name: 'Media Player', icon: '🎬', color: '#e05d5d',
        category: 'media', type: 'pwa', url: '/pwa/nuxel-apps/media/index.html',
        description: 'Local audio/video playback through PipeWire/ALSA',
        capabilities: ['audio:playback', 'media:library'], docked: false,
    },
    'org.nuxel.Downloader': {
        id: 'org.nuxel.Downloader', name: 'Media Downloader', icon: '⬇️', color: '#4a90e2',
        category: 'media', type: 'pwa', url: '/pwa/nuxel-apps/downloader/index.html',
        description: 'Bounded download queue with checksums',
        capabilities: ['download:queue'], docked: false,
    },
    'org.nuxel.Authenticator': {
        id: 'org.nuxel.Authenticator', name: 'Authenticator', icon: '🔐', color: '#7e57c2',
        category: 'security', type: 'pwa', url: '/pwa/nuxel-apps/authenticator/index.html',
        description: 'Encrypted on-device TOTP authenticator',
        capabilities: ['storage:encrypted', 'secrets:authenticator-unlock'], docked: false,
    },
    'org.nuxel.Vault': {
        id: 'org.nuxel.Vault', name: 'Vault', icon: '🔑', color: '#0b3b46',
        category: 'security', type: 'pwa', url: '/pwa/nuxel-apps/vault/index.html',
        description: 'On-device keyring-backed password manager and secure notes',
        capabilities: ['secrets:manage'], docked: false,
    },
    'org.nuxel.Cleanup': {
        id: 'org.nuxel.Cleanup', name: 'Safe Cleanup', icon: '🧹', color: '#26a69a',
        category: 'tools', type: 'pwa', url: '/pwa/nuxel-apps/cleanup/index.html',
        description: 'Preview-then-delete allowlisted cache cleanup',
        capabilities: ['storage:cleanup'], docked: false,
    },
    'org.nuxel.DevMgmt': {
        id: 'org.nuxel.DevMgmt', name: 'DevMgmt', icon: '🛠️', color: '#00695c',
        category: 'tools', type: 'pwa', url: '/pwa/nuxel-apps/devmgmt/index.html',
        description: 'Read-only device and peripheral inspection',
        capabilities: ['system:inspect'], docked: false,
    },
    'org.nuxel.PenguInterface': {
        id: 'org.nuxel.PenguInterface', name: 'PenguInterface', icon: '🐧', color: '#3f51b5',
        category: 'system', type: 'pwa', url: '/pwa/nuxel-apps/penguinterface/index.html',
        description: 'Validated per-device compatibility profiles',
        capabilities: ['system:inspect'], docked: false,
    },
    'org.gnome.Software': {
        id: 'org.gnome.Software', name: 'Software', icon: '🛍️', color: '#2ec27e',
        category: 'system', type: 'native', url: 'org.gnome.Software://',
        native_binary: '/usr/lib/nuxel/nuxel-software',
        description: 'Fedora RPM and Flathub software center (PackageKit/DNF + Flatpak)',
        capabilities: [], docked: false,
    },
};

// Launcher artwork is intentionally separate from the canonical app registry:
// native consumers still receive their stable textual icon field while Home
// renders the supplied PNG pack everywhere an app is shown.
const NUXEL_APP_ICON_ASSETS = {
    'nuxel-dialer': '/assets/nuxel-applications-icon-pack/01-08_phone.png?v=a37',
    'nuxel-messages': '/assets/nuxel-applications-icon-pack/02-01_messages.png?v=a37',
    'nuxel-contacts': '/assets/nuxel-applications-icon-pack/02-02_contacts.png?v=a37',
    'nuxel-settings': '/assets/nuxel-applications-icon-pack/01-11_settings.png?v=a37',
    'org.nuxel.Terminal': '/assets/nuxel-applications-icon-pack/01-01_terminal.png?v=a37',
    'org.nuxel.LiveConsole': '/assets/nuxel-applications-icon-pack/05-05_live-console.png?v=a80',
    'org.nuxel.USBSSHConsole': '/assets/nuxel-applications-icon-pack/06-05_usb-connection.png?v=a80',
    'org.nuxel.WiFiSSHConsole': '/assets/nuxel-quicksettings-icon-pack/01-wifi.png?v=a80',
    'org.nuxel.RemoteDesktopXRDP': '/assets/nuxel-applications-icon-pack/05-07_web-window.png?v=p47000',
    'org.nuxel.RemoteDesktopVNC': '/assets/nuxel-applications-icon-pack/06-04_casting-screen.png?v=p47000',
    'org.nuxel.ScrcpyMirror': '/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png?v=p47000',
    'org.nuxel.SnekByte': '/assets/nuxel-applications-icon-pack/01-02_snekbyte.png?v=a63',
    'org.nuxel.Doom': '/pwa/nuxel-apps/doom/icons/icon-192.png?v=p77000',
    'org.nuxel.Calculator': '/assets/nuxel-applications-icon-pack/06-02_calculator.png?v=p33000',
    'org.nuxel.Clock': '/assets/nuxel-applications-icon-pack/06-03_clock.png?v=p33000',
    'org.nuxel.Photos': '/assets/nuxel-applications-icon-pack/03-02_gallery.png?v=p33000',
    'org.nuxel.Nuxtore': '/assets/nuxel-applications-icon-pack/02-07_nuxtore.png?v=p33000',
    'org.nuxel.Recorder': '/assets/nuxel-applications-icon-pack/06-01_recorder.png?v=p33000',
    'org.nuxel.Maps': '/assets/nuxel-applications-icon-pack/03-05_maps.png?v=p33000',
    'org.nuxel.Calendar': '/assets/nuxel-applications-icon-pack/02-03_day-calendar.png?v=p33000',
    'org.nuxel.Mail': '/assets/nuxel-applications-icon-pack/01-06_pixel-envelope.png?v=p33000',
    'org.nuxel.Files': '/assets/nuxel-applications-icon-pack/02-06_file-explorer.png?v=p33000',
    'org.nuxel.Notes': '/assets/nuxel-applications-icon-pack/02-09_notes.png?v=p33000',
    'nuxel-camera': '/assets/nuxel-applications-icon-pack/03-01_camera.png?v=p33000',
    'org.nuxel.Browser': '/assets/nuxel-applications-icon-pack/01-09_browser-swirl.png?v=p33000',
    'org.mozilla.firefox': '/assets/native-app-icons/firefox.png?v=p50000',
    'org.videolan.VLC': '/assets/native-app-icons/vlc.png?v=p50000',
    'org.signal.Signal': '/assets/nuxel-applications-icon-pack/01-06_pixel-envelope.png',
    'com.stremio.Stremio': '/assets/native-app-icons/stremio.svg?v=p50000',
    'org.gnome.FileRoller': '/assets/native-app-icons/org.gnome.FileRoller.svg?v=p50000',
    'org.gnome.Loupe': '/assets/native-app-icons/org.gnome.Loupe.svg?v=p50000',
    'org.gnome.Papers': '/assets/native-app-icons/org.gnome.Papers.svg?v=p50000',
    'org.gnome.SystemMonitor': '/assets/native-app-icons/org.gnome.SystemMonitor.svg?v=p50000',
    'org.nuxel.Media': '/assets/nuxel-applications-icon-pack/03-04_video-player.png',
    'org.nuxel.Downloader': '/assets/nuxel-applications-icon-pack/06-04_casting-screen.png',
    'org.nuxel.Authenticator': '/assets/nuxel-applications-icon-pack/01-06_pixel-envelope.png',
    'org.nuxel.Cleanup': '/assets/nuxel-applications-icon-pack/02-05_folders.png',
    'org.nuxel.DevMgmt': '/assets/nuxel-applications-icon-pack/05-02_system-monitor.png',
    'org.nuxel.PenguInterface': '/assets/nuxel-app-penguinterface.png?v=p54000',
    'org.nuxel.Clipper': '/assets/nuxel-applications-icon-pack/05-09_clipboard.png?v=p54000',
    'org.gnome.Software': '/assets/native-app-icons/org.gnome.Software.svg?v=p50000',
};

function nuxelAppIcon(app) {
    const src = (app && (app.iconAsset || NUXEL_APP_ICON_ASSETS[app.id])) || '';
    if (!src) return '<span>' + ((app && app.icon) || '📱') + '</span>';
    const name = String((app && app.name) || 'App').replace(/[&<>'"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[c]));
    return '<img src="' + src + '" alt="' + name + '" width="48" height="48" loading="lazy" fetchpriority="low" draggable="false" decoding="async" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span class="nuxel-icon-fallback" hidden>' + ((app && app.icon) || '📱') + '</span>';
}
try { window.NuxelAppIcon = nuxelAppIcon; } catch (e) { /* non-DOM registry test */ }

// App state management
class AppRegistry {
    constructor() {
        this.apps = new Map(Object.entries(NUXEL_APPS));
        this.userApps = new Map();
        this.recentApps = [];
        this.maxRecentApps = 10;
        // Apps that exist only because NuxTore registered them.  They must be
        // able to disappear again when the user presses Remove; static built-in
        // apps are never removed by a registry refresh.
        this.canonicalDynamicIds = new Set();
        this.lastRegistryDelta = { added: 0, removed: 0 };
        this._loadState();
    }

    /* PWNAGE-45000: merge the canonical Bridge/registry file into Home.
       Static entries remain the offline baseline; the registry is authoritative
       for status/paths and adds local catalog apps NuxTore has registered.
       Case-only aliases are collapsed onto one canonical id. */
    applyCanonicalRegistry(doc) {
        const aliases = { 'org.nuxel.NuxTore': 'org.nuxel.Nuxtore',
                          'org.nuxel.Snekbyte': 'org.nuxel.SnekByte' };
        const canonical = (id) => aliases[id] || id;
        const incoming = Array.isArray(doc && doc.apps) ? doc.apps : [];
        let changed = false;
        let added = 0, removed = 0;
        const incomingIds = new Set();
        for (const raw of incoming) {
            if (!raw || !raw.id) continue;
            const id = canonical(raw.id);
            incomingIds.add(id);
            if (id !== raw.id) changed = true;
            const known = this.apps.has(id);
            if (!known) { added++; changed = true; }
            const prev = this.apps.get(id) || {};
            const merged = Object.assign({}, prev, raw, { id });
            if (!merged.name) merged.name = id;
            if (!merged.type) merged.type = 'pwa';
            if (!merged.url && merged.native_binary) merged.url = id + '://';
            this.apps.set(id, merged);
        }
        // NuxTore removal unregisters the app in the canonical registry.  Drop
        // catalogue-installed entries that are no longer present, while never
        // touching the offline static baseline.
        for (const id of Array.from(this.canonicalDynamicIds)) {
            if (!incomingIds.has(id) && !Object.prototype.hasOwnProperty.call(NUXEL_APPS, id)) {
                if (this.apps.delete(id)) { changed = true; removed++; }
            }
        }
        this.canonicalDynamicIds = new Set(Array.from(incomingIds)
            .filter(id => !Object.prototype.hasOwnProperty.call(NUXEL_APPS, id)));
        this.lastRegistryDelta = { added, removed };
        // Drop legacy case variants if both somehow exist.
        for (const legacy of Object.keys(aliases)) {
            if (legacy !== aliases[legacy] && this.apps.has(legacy)) {
                this.apps.delete(legacy); changed = true;
            }
        }
        if (changed || incoming.length) {
            try { document.dispatchEvent(new CustomEvent('nuxel:app-registry-changed', { detail: { count: incoming.length } })); } catch (e) {}
        }
        return incoming.length;
    }

    async refreshFromBridge() {
        // The launcher is served from :8000 while the bridge API is :8080.
        // Use the shared authenticated client when the module has loaded, then
        // fall back to the loopback API (dev mode allows loopback without a
        // token).  The old relative fetch returned 404 on the handset because
        // nuxel-web does not proxy /api/v1.
        let doc = null;
        try {
            if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
                doc = await window.NuxelBridge.call('apps', 'registry', {});
            }
        } catch (e) { doc = null; }
        if (!doc || !Array.isArray(doc.apps)) {
            try {
                const res = await fetch('http://127.0.0.1:8080/api/v1/apps/registry', { cache: 'no-store' });
                if (!res.ok) return 0;
                doc = await res.json();
            } catch (e) { return 0; }
        }
        const n = this.applyCanonicalRegistry(doc);
        const delta = this.lastRegistryDelta || { added: 0, removed: 0 };
        if (delta.added || delta.removed) {
            try {
                if (window.launcher) {
                    if (window.launcher._renderDrawerApps) window.launcher._renderDrawerApps(true);
                    if (window.launcher._renderAppGrid) window.launcher._renderAppGrid();
                }
            } catch (e) {}
        }
        try { document.dispatchEvent(new CustomEvent('nuxel:app-registry-changed', { detail: { count: n, added: delta.added, removed: delta.removed, source: 'flatpak+registry' } })); } catch (e) {}
        return n;
    }

    /* Software installs happen in a separate foreground app.  Poll while Home
       is alive and refresh immediately whenever Home becomes visible again, so
       a newly installed Flatpak reaches the drawer (and Home when unlocked)
       without a reboot. */
    startBridgeWatch(intervalMs) {
        if (this._bridgeWatchTimer) return;
        const interval = Math.max(10000, Number(intervalMs) || 30000);
        this._bridgeWatchTimer = setInterval(() => {
            if (typeof document !== 'undefined' && document.hidden) return;
            this.refreshFromBridge();
        }, interval);
        if (typeof document !== 'undefined' && document.addEventListener) {
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) this.refreshFromBridge();
            });
            document.addEventListener('app:lifecycle', (ev) => {
                if (ev && ev.detail && ev.detail.state === 'CLOSED') this.refreshFromBridge();
            });
        }
        if (typeof window !== 'undefined' && window.addEventListener) {
            window.addEventListener('focus', () => this.refreshFromBridge());
            window.addEventListener('nuxel:app-closed', () => this.refreshFromBridge());
        }
    }

    getAllApps() {
        const apps = [...this.apps.values()];
        // Merge user-installed apps
        for (const app of this.userApps.values()) {
            apps.push(app);
        }
        return apps.sort((a, b) => a.name.localeCompare(b.name));
    }

    getDockedApps() {
        return this.getAllApps().filter(app => app.docked);
    }

    getAppsByCategory(category) {
        return this.getAllApps().filter(app => app.category === category);
    }

    getApp(id) {
        return this.apps.get(id) || this.userApps.get(id);
    }

    addRecentApp(appId) {
        // Remove if already present
        this.recentApps = this.recentApps.filter(id => id !== appId);
        // Add to front
        this.recentApps.unshift(appId);
        // Limit size
        if (this.recentApps.length > this.maxRecentApps) {
            this.recentApps = this.recentApps.slice(0, this.maxRecentApps);
        }
        this._saveState();
    }

    getRecentApps() {
        return this.recentApps
            .map(id => this.getApp(id))
            .filter(app => app !== undefined);
    }

    searchApps(query) {
        const q = query.toLowerCase().trim();
        if (!q) return [];

        const results = [];
        for (const app of this.getAllApps()) {
            if (app.name.toLowerCase().includes(q) ||
                app.description.toLowerCase().includes(q) ||
                app.category.toLowerCase().includes(q)) {
                results.push({
                    ...app,
                    matchType: app.name.toLowerCase().includes(q) ? 'name' : 'description',
                });
            }
        }

        // Sort by relevance
        results.sort((a, b) => {
            const aScore = a.matchType === 'name' ? 0 : 1;
            const bScore = b.matchType === 'name' ? 0 : 1;
            if (aScore !== bScore) return aScore - bScore;
            return a.name.localeCompare(b.name);
        });

        return results;
    }

    launchApp(appId) {
        const app = this.getApp(appId);
        if (!app) {
            console.error(`App not found: ${appId}`);
            return;
        }

        this.addRecentApp(appId);

        // Dispatch launch event
        const event = new CustomEvent('app:launch', {
            detail: { app },
            bubbles: true,
        });
        document.dispatchEvent(event);

        // Handle based on type
        if (app.type === 'pwa') {
            // Open PWA via iframe or navigation
            this._launchPwa(app);
        } else if (app.type === 'native') {
            // Launch native app via custom protocol or xdg-open
            this._launchNative(app);
        }
    }

    _launchPwa(app) {
        console.log(`Launching PWA: ${app.name} (${app.url})`);
        // In a real implementation, this would:
        // 1. Check if PWA is already open (via service worker)
        // 2. Focus existing window or open new one
        // 3. Request capabilities from nuxel-bridge
        
        // Open in fullscreen iframe or new window
        const event = new CustomEvent('pwa:open', {
            detail: {
                app: app,
                url: app.url,
            },
            bubbles: true,
        });
        document.dispatchEvent(event);
    }

    _launchNative(app) {
        console.log(`Launching native app: ${app.name} (${app.url})`);
        
        // Try xdg-open for custom protocol URLs
        try {
            // Use nuxel-bridge to request launch
            const event = new CustomEvent('native:launch', {
                detail: {
                    app: app,
                    url: app.url,
                },
                bubbles: true,
            });
            document.dispatchEvent(event);
        } catch (e) {
            console.error(`Failed to launch native app: ${e}`);
        }
    }

    installApp(manifest) {
        const app = {
            id: manifest.id || `user-${Date.now()}`,
            name: manifest.name || 'Unknown App',
            icon: manifest.icon || '📱',
            color: manifest.color || '#555',
            category: manifest.category || 'tools',
            type: 'pwa',
            url: manifest.start_url || '/',
            description: manifest.description || '',
            capabilities: manifest.capabilities || [],
            docked: false,
            userInstalled: true,
        };

        this.userApps.set(app.id, app);
        this._saveState();

        const event = new CustomEvent('app:installed', {
            detail: { app },
            bubbles: true,
        });
        document.dispatchEvent(event);

        return app;
    }

    uninstallApp(appId) {
        if (this.userApps.has(appId)) {
            this.userApps.delete(appId);
            this._saveState();

            const event = new CustomEvent('app:uninstalled', {
                detail: { appId },
                bubbles: true,
            });
            document.dispatchEvent(event);
            return true;
        }
        return false;
    }

    _saveState() {
        try {
            const state = {
                recentApps: this.recentApps,
                userApps: [...this.userApps.entries()],
            };
            localStorage.setItem('nuxel-app-registry', JSON.stringify(state));
        } catch (e) {
            console.warn('Failed to save app state:', e);
        }
    }

    _loadState() {
        try {
            const raw = localStorage.getItem('nuxel-app-registry');
            if (raw) {
                const state = JSON.parse(raw);
                // A59 shipped a case-skewed id. Preserve the owner's recents
                // while migrating to the canonical app/manifest id.
                this.recentApps = (state.recentApps || [])
                    .map(id => id === 'org.nuxel.Snekbyte' ? 'org.nuxel.SnekByte' : id)
                    .filter((id, index, ids) => ids.indexOf(id) === index);
                if (state.userApps) {
                    this.userApps = new Map(state.userApps);
                    if (this.userApps.has('org.nuxel.Snekbyte')) {
                        this.userApps.delete('org.nuxel.Snekbyte');
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to load app state:', e);
        }
    }
}

// Create global instance
const appRegistry = new AppRegistry();
// A33: registry revision + launcher deeplinks.  manifest.json's shortcuts
// (Terminal / Settings / Live Console) resolve to ./index.html#app=<id>, so the
// launcher has to honour that hash - otherwise the shortcuts would be a manifest
// promise the OS never keeps.
try { window.NUXEL_REGISTRY_VERSION = NUXEL_REGISTRY_VERSION; } catch (e) { /* ignore */ }

function nuxelLaunchFromHash(hash) {
    const m = /(?:^#|&)app=([^&]+)/.exec(hash || '');
    if (!m) return false;
    const id = decodeURIComponent(m[1]);
    if (!appRegistry.getApp(id)) {
        console.warn('[registry] deeplink unknown app: ' + id);
        return false;
    }
    // Wait for the launcher to be wired (app.js publishes window.nuxel on
    // DOMContentLoaded) before dispatching the launch event.
    const go = () => appRegistry.launchApp(id);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(go, 0));
    else setTimeout(go, 0);
    return true;
}
try {
    window.addEventListener('hashchange', () => nuxelLaunchFromHash(window.location.hash));
    if (window.location.hash) nuxelLaunchFromHash(window.location.hash);
} catch (e) { /* no DOM (offline registry test) */ }
// A32: expose the registry to the launcher host (hardware-button remapping needs
// the authoritative app list) and to same-origin PWA iframes (Settings).
try { window.appRegistry = appRegistry; } catch (e) { /* ignore */ }
