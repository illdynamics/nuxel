Complete!
[nuxel] systemd pin OK: systemd-258.11-1.fc43.aarch64
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:8:35: warning: '/*' within comment [-Wcomment]
    8 |  * pwa/nuxel-home (index.html, css/*, js/apps.js registry, js/launcher.js,
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:2493:69: warning: '/*' within comment [-Wcomment]
 2493 |  * Measured this cycle on the handset: after replacing index.html/js/*.js the
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:2496:47: warning: '/*' within comment [-Wcomment]
 2496 |  * launcher's service worker kept serving ./js/*.js from its cache namespace, and
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c: In function 'action_perform':
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:1509:36: warning: '%03ld' directive output may be truncated writing between 3 and 14 bytes into a region of size between 1 and 32 [-Wformat-truncation=]
 1509 |   snprintf(stamp, sizeof stamp, "%s%03ldZ", base, now.tv_nsec / 1000000L);
      |                                    ^~~~~
In function 'nuxel_capture_screenshot',
    inlined from 'action_perform' at /nuxel/tools/s10plus/a45/nuxel-pwa-host.c:1778:9:
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:1509:33: note: directive argument in the range [-9223372036854, 9223372036854]
 1509 |   snprintf(stamp, sizeof stamp, "%s%03ldZ", base, now.tv_nsec / 1000000L);
      |                                 ^~~~~~~~~~
/nuxel/tools/s10plus/a45/nuxel-pwa-host.c:1509:3: note: 'snprintf' output between 5 and 47 bytes into a destination of size 32
 1509 |   snprintf(stamp, sizeof stamp, "%s%03ldZ", base, now.tv_nsec / 1000000L);
      |   ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/nuxel/shell/nuxel-shell/nuxel-messages/main.c:328:1: warning: 'on_conversation_activated' defined but not used [-Wunused-function]
  328 | on_conversation_activated(GtkWidget *list, gpointer user_data)
      | ^~~~~~~~~~~~~~~~~~~~~~~~~
wrote /tmp/nuxel-current-userspace/a45/navdock-art.h (78940 bytes)
/nuxel/tools/s10plus/a45/nuxel-statusbar.c:598:13: warning: 'bar_reveal' defined but not used [-Wunused-function]
  598 | static void bar_reveal(void) { bar_show(); }
      |             ^~~~~~~~~~
/nuxel/tools/s10plus/a59/nuxel-foreign-toplevel.c:96:28: warning: 'wl_display_interface' defined but not used [-Wunused-variable]
   96 | static struct wl_interface wl_display_interface = {
      |                            ^~~~~~~~~~~~~~~~~~~~
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c:916:14: warning: 'tracked_get' defined but not used [-Wunused-function]
  916 | static void *tracked_get(const char *key) {
      |              ^~~~~~~~~~~
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c: In function 'scan_nodes.constprop':
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c:611:38: warning: '%s' directive output may be truncated writing up to 255 bytes into a region of size 64 [-Wformat-truncation=]
  611 |     snprintf(entries[n], NAME_MAX_, "%s", de->d_name);
      |                                      ^~
In function 'list_event_entries',
    inlined from 'scan_nodes.constprop' at /nuxel/tools/s10plus/a33/nuxel-libinput-path.c:657:9:
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c:611:5: note: 'snprintf' output between 1 and 256 bytes into a destination of size 64
  611 |     snprintf(entries[n], NAME_MAX_, "%s", de->d_name);
      |     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c: In function 'retry_tick':
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c:1060:36: warning: '%s' directive output may be truncated writing up to 1407 bytes into a region of size 64 [-Wformat-truncation=]
 1060 |       snprintf(due[n], NAME_MAX_, "%s", g_retry[i].name);
      |                                    ^~
/nuxel/tools/s10plus/a33/nuxel-libinput-path.c:1060:7: note: 'snprintf' output between 1 and 1408 bytes into a destination of size 64
 1060 |       snprintf(due[n], NAME_MAX_, "%s", g_retry[i].name);
      |       ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
dba4367f0a4a3101fbc53f496fea35f3dd8c23ff26c5cc6c3d1fde174d0ef6c5  /tmp/nuxel-current-userspace/nuxel-wl-fb
937d78e0d4f7e145dc2baf7b7eb9524d495beb36ceb7ed18d6e8490a37c54058  /tmp/nuxel-current-userspace/nuxel-wl-snapshot
d308b72f821b0660670b04d4f98838991720d2e76e9da9fe161be2f80da69155  /tmp/nuxel-current-userspace/nuxel-screenshot
803006f9a89cf757b113232bf6942aa9338062a5297b5e0f72598b1374b7b581  /tmp/nuxel-current-userspace/nuxel-pwa-host
226766bbe1b6896867f5501c260227e0aa3b693da8eda3f0125c0b660406f0b9  /tmp/nuxel-current-userspace/nuxel-button-manager
06bfc7ee3518a0b83be45b351729156af9a470a1ddf9141337634521e6fa3814  /tmp/nuxel-current-userspace/nuxel-soundctl
220e9d5f77aaa59e3925a0851c162df90bc5d2039eaf70186abe07a957623189  /tmp/nuxel-current-userspace/libnuxel-libinput-path.so
6732ba3a0d2b02865fb5cf751c67325e2cafee2c3b56005214cb5ed0272d2fea  /tmp/nuxel-current-userspace/nuxel-metricsd
83469b2e5aacd29c9a506e92c18dc4cd873770b3fc405adc9a1d675c395f8e58  /tmp/nuxel-current-userspace/nuxel-navdock
f0471e225c611d95bbd3c9f635ef5cc4555258633d568bd3928208ec9ddaeee8  /tmp/nuxel-current-userspace/nuxel-statusbar
67bfb2d077c9037c3eb816740bc099e5c0a63c3d80ef9127fc9d2f0882c607bd  /tmp/nuxel-current-userspace/nuxel-osd
f251dca48a7dabb7fba1c9565315ee3780aaa7d33523dc8a6feda4ad4ea1e85a  /tmp/nuxel-current-userspace/nuxel-foreign-toplevel
[nuxel] preload cinema asset sha256 OK: b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1
nuxel-wayland-gpu-wrapper.sh: FAILED
nuxel-session.sh: FAILED
sha256sum: WARNING: 2 computed checksums did NOT match
ERROR: release GPU assets failed SHA-256 verification in /nuxel/release/s10plus/gpu
Error: Process completed with exit code 1.
