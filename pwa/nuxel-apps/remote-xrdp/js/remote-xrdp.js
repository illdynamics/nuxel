import { startRemoteApp } from '/pwa/nuxel-common/remote-desktop.js?v=p47000';
startRemoteApp({
  appId: "org.nuxel.RemoteDesktopXRDP",
  service: "xrdp",
  title: "XRDP Remote Desktop",
  subtitle: "RDP/TLS mirror of this phone's live screen · Wi-Fi",
  sessionLabel: "LIVE PHOC SCREEN",
  icon: "/assets/nuxel-applications-icon-pack/05-07_web-window.png",
  glyph: "RDP",
  defaultTransport: "wlan",
  transports: [
    { id: "wlan", label: "Wi-Fi", detail: "Owner LAN / ZeroTier · direct" },
    { id: "usb", label: "USB network", detail: "BLOCKED_KERNEL_PANIC on 4.14.253" }
  ],
  confirmText: "This starts an RDP/TLS server on this phone that mirrors the live screen, served directly on the owner LAN with TLS + PAM as nuxel. Start it?",
  note: "This mirrors the live Phoc/Wayland screen, never owns /dev/fb0, and uses a local nuxel account with TLS + PAM."
});
