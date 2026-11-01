import { startRemoteApp } from '/pwa/nuxel-common/remote-desktop.js?v=p47000';
startRemoteApp({
  appId: "org.nuxel.RemoteDesktopXRDP",
  service: "xrdp",
  title: "XRDP Remote Desktop",
  subtitle: "Separate authenticated X11 session · RDP/TLS · Wi-Fi preferred",
  sessionLabel: "SEPARATE X11 SESSION",
  icon: "/assets/nuxel-applications-icon-pack/05-07_web-window.png",
  glyph: "RDP",
  defaultTransport: "wlan",
  transports: [
    { id: "wlan", label: "Wi-Fi", detail: "Owner LAN / ZeroTier · direct" },
    { id: "usb", label: "USB network", detail: "BLOCKED_KERNEL_PANIC on 4.14.253" }
  ],
  confirmText: "This starts a separate X11 remote login on this phone over RDP/TLS, served directly on the owner LAN / ZeroTier with TLS + PAM as nuxel. It does not mirror the physical Phoc screen. Start it?",
  note: "This is a separate remote X11 session. It does not mirror the physical Phoc/Wayland screen, never owns /dev/fb0, and uses a local nuxel account with TLS + PAM."
});
