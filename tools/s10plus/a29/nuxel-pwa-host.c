/* nuxel-pwa-host — the display host for the EXISTING Nuxel launcher.
 *
 * This is NOT a launcher.  It renders the launcher that already exists and
 * already runs in the UTM VM - /usr/share/nuxel/nuxel-home, served on
 * 127.0.0.1:8000 by the same static server the VM uses (services/nuxel-web
 * .service) - in the same engine family the VM renders it with (WebKitGTK).
 * All UI, styling, icons, ordering and app-launching behaviour stay in
 * pwa/nuxel-home (index.html, css/*, js/apps.js registry, js/launcher.js,
 * js/app.js).  js/app.js itself opens a tapped application as a fullscreen
 * iframe of that registry entry, so one view is enough and the app registry is
 * never duplicated here.
 *
 * Differences from the VM, and nothing else:
 *   * Wayland-only: the view is a Wayland client of the stock phoc compositor
 *     running with the headless backend (no /dev/dri on this handset); the
 *     composited frames reach the AMOLED through nuxel-wl-fb.
 *   * Software rendering: WEBKIT_DISABLE_COMPOSITING_MODE=1 is exported by the
 *     session wrapper because there is no EGL/GBM device on this kernel.
 *   * The URL is read from the environment so the same binary can host any
 *     registry entry (NUXEL_HOME_URL).
 *
 * Evidence: NUXEL_HOME_READY / NUXEL_HOME_LOAD_FAIL and the iframe/app
 * navigations are written to /run/nuxel-home.state, and the readiness file
 * /run/nuxel-launcher-ready is what the fallback unit waits for.
 */
#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define STATE  "/run/nuxel-home.state"
#define READY  "/run/nuxel-launcher-ready"
#define DEFAULT_URL "http://127.0.0.1:8000/pwa/nuxel-home/index.html"

static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  FILE *f = fopen(STATE, "a");
  if (!f) return;
  fprintf(f, "%ld ", (long)time(NULL));
  va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
  fputc('\n', f); fclose(f);
}

static WebKitWebView *view_new(void);

static gboolean on_load_failed(WebKitWebView *v, WebKitLoadEvent ev, gchar *uri, GError *err, gpointer d) {
  (void)v; (void)ev; (void)d;
  st("NUXEL_HOME_LOAD_FAIL uri=%s err=%s", uri, err && err->message ? err->message : "?");
  return FALSE;
}

static void on_load_changed(WebKitWebView *v, WebKitLoadEvent ev, gpointer d) {
  (void)d;
  if (ev == WEBKIT_LOAD_FINISHED) {
    const gchar *uri = webkit_web_view_get_uri(v);
    st("NUXEL_HOME_READY uri=%s", uri ? uri : "?");
    FILE *f = fopen(READY, "w");
    if (f) { fprintf(f, "%s\n", uri ? uri : ""); fclose(f); }
  } else if (ev == WEBKIT_LOAD_COMMITTED) {
    st("NUXEL_HOME_COMMITTED uri=%s", webkit_web_view_get_uri(v) ?: "?");
  }
}

static void on_notify_uri(WebKitWebView *v, GParamSpec *p, gpointer d) {
  (void)p; (void)d;
  st("NUXEL_HOME_NAV uri=%s", webkit_web_view_get_uri(v) ?: "?");
}

/* A registry entry that opens a popup gets a real top-level Wayland window (the
 * compositor maps it fullscreen, exactly like any other client). */
static WebKitWebView *on_create(WebKitWebView *v, WebKitNavigationAction *a, gpointer d) {
  (void)v; (void)d;
  WebKitURIRequest *req = webkit_navigation_action_get_request(a);
  const gchar *uri = req ? webkit_uri_request_get_uri(req) : "?";
  st("NUXEL_APP_WINDOW uri=%s", uri ?: "?");
  return view_new();
}

static void on_permission(WebKitWebView *v, WebKitPermissionRequest *r, gpointer d) {
  (void)v; (void)d;
  st("NUXEL_PERMISSION %s", G_OBJECT_TYPE_NAME(r));
  webkit_permission_request_allow(r);
}

/* MEASURED (A29b, handset, 2026-09-15T00:07:45Z): webkit2gtk4.1-2.52.5 builds a
 * GStreamer playbin for the launcher's <video id="boot-splash-video"> splash.
 * The handset image carries gstreamer1 + gstreamer1-plugins-base but NOT
 * gstreamer1-plugins-good, so `autoaudiosink` (libgstautodetect.so) is missing.
 * The handset log then reads:
 *     phoc: GStreamer element autoaudiosink not found. Please install it
 *     WebKitWebProcess: invalid (NULL) pointer instance
 *     WebKitWebProcess: g_signal_connect_data: assertion 'G_TYPE_CHECK_INSTANCE (instance)' failed
 *     systemd-coredump: Process 6550 (WebKitWebProces) terminated abnormally
 * and the *web process* is gone: the view stays blank and is never reloaded.
 * The UTM VM renders the same page because its image has 239 gst plugins
 * (libgstautodetect.so present) - this is a host-image gap, not a launcher defect.
 *
 * So media is enabled only where the audio sink really exists, and the decision is
 * written to the state file instead of being claimed.  The launcher degrades by
 * design when media is unavailable: js/app.js hides #boot-splash on the video
 * element's 'error' event and after a 12 s safety timeout, and the phone has
 * already played the original boot animation from the initramfs before this view
 * exists (index.html + js/app.js are not modified by this port).
 */
static gboolean audio_sink_available(void) {
  static const char *p[] = {
      "/usr/lib64/gstreamer-1.0/libgstautodetect.so",
      "/usr/lib/gstreamer-1.0/libgstautodetect.so", NULL};
  for (int i = 0; p[i]; i++)
    if (g_file_test(p[i], G_FILE_TEST_EXISTS)) return TRUE;
  return FALSE;
}

static WebKitWebView *view_new(void) {
  gboolean media = audio_sink_available();
  st("NUXEL_HOME_MEDIA enable_media=%d audio_sink=%d", media ? 1 : 0, media ? 1 : 0);
  WebKitSettings *s = webkit_settings_new_with_settings(
      "enable-javascript", TRUE,
      "enable-dns-prefetching", FALSE,
      "enable-developer-extras", FALSE,
      "javascript-can-open-windows-automatically", TRUE,
      "enable-media", media,
      "enable-mediasource", media,
      "user-agent", "Mozilla/5.0 (Linux; aarch64) Nuxel/1.0 (S10+, like Gecko) WebKitGTK",
      NULL);
  WebKitWebView *v = WEBKIT_WEB_VIEW(webkit_web_view_new_with_settings(s));
  g_object_unref(s);
  g_signal_connect(v, "load-changed", G_CALLBACK(on_load_changed), NULL);
  g_signal_connect(v, "load-failed", G_CALLBACK(on_load_failed), NULL);
  g_signal_connect(v, "create", G_CALLBACK(on_create), NULL);
  g_signal_connect(v, "permission-request", G_CALLBACK(on_permission), NULL);
  g_signal_connect(v, "notify::uri", G_CALLBACK(on_notify_uri), NULL);
  return v;
}

int main(int argc, char **argv) {
  gtk_init(&argc, &argv);
  const char *url = getenv("NUXEL_HOME_URL");
  if (!url || !*url) url = DEFAULT_URL;

  GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
  gtk_window_set_title(GTK_WINDOW(win), "Nuxel");
  gtk_window_set_decorated(GTK_WINDOW(win), FALSE);
  gtk_window_set_resizable(GTK_WINDOW(win), TRUE);
  gtk_widget_set_size_request(win, 360, 760);
  GtkWidget *v = GTK_WIDGET(view_new());
  gtk_container_add(GTK_CONTAINER(win), v);
  g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), NULL);
  gtk_widget_show_all(win);
  gtk_window_fullscreen(GTK_WINDOW(win));

  st("NUXEL_HOME_OPEN url=%s engine=WebKitGTK/%d.%d", url,
     webkit_get_major_version(), webkit_get_minor_version());
  webkit_web_view_load_uri(WEBKIT_WEB_VIEW(v), url);
  gtk_main();
  st("NUXEL_HOME_EXIT");
  return 0;
}
