import { startRemoteApp } from '/pwa/nuxel-common/remote-desktop.js?v=p47000';
startRemoteApp({
  appId: "org.nuxel.ScrcpyMirror",
  service: "scrcpy",
  title: "scrcpy (Android)",
  subtitle: "Official Android ADB target mirroring · USB ADB preferred",
  sessionLabel: "ANDROID ADB ONLY",
  icon: "/assets/nuxel-applications-icon-pack/01-12_phone-alternative.png",
  glyph: "ADB",
  defaultTransport: "android-adb-usb",
  transports: [
    { id: "android-adb-usb", label: "USB ADB", detail: "Android USB debugging · preferred" },
    { id: "android-adb-tcpip", label: "Wi-Fi / TCP-IP", detail: "Android wireless debugging · optional" }
  ],
  note: "scrcpy is an Android screen-mirroring system. Native Nuxel is Fedora/Linux, not Android, and is not an ADB target. Use VNC Screen Sharing for native Nuxel."
});
