import { startRemoteApp } from '/pwa/nuxel-common/remote-desktop.js?v=p47000';
startRemoteApp({
  appId: "org.nuxel.RemoteDesktopVNC",
  service: "vnc",
  title: "VNC Screen Sharing",
  subtitle: "Real Phoc/Wayland screen sharing · Wi-Fi preferred",
  sessionLabel: "CURRENT WAYLAND SESSION",
  icon: "/assets/nuxel-applications-icon-pack/06-04_casting-screen.png",
  glyph: "VNC",
  defaultTransport: "wlan",
  transports: [
    { id: "wlan", label: "Wi-Fi", detail: "Owner LAN / ZeroTier · direct" },
    { id: "usb", label: "USB network", detail: "BLOCKED_KERNEL_PANIC on 4.14.253" }
  ],
  confirmText: "This lets an authenticated VNC client view and control the actual Nuxel Phoc screen while it is running. The listener is direct on the owner LAN / ZeroTier and has no VNC password. Keep it off untrusted networks. Start it?",
  note: "wayvnc attaches to the active Phoc session using wlr-screencopy and virtual pointer/keyboard. It never opens /dev/fb0, never starts a second compositor, and the normal Nuxel lock policy still applies."
});
