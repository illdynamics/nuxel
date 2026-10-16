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

/* REVISION A31 (2026-10-16, beta finalizer) - three corrections:
 *   1. BOOT ANIMATION OWNERSHIP (mission 9).  On the S10+ the OS has already
 *      played the authoritative boot animation from the initramfs before this
 *      view exists, and the launcher's own <div id="boot-splash"> fullscreen
 *      <video> is therefore a SECOND, redundant animation that can flash over
 *      the launcher and intercept input.  This host now tells the launcher that
 *      the OS owns the animation (?boot=os); pwa/nuxel-home/js/app.js removes
 *      the splash element for that launch mode.  NUXEL_PWA_SPLASH=1 restores the
 *      PWA's own splash (the VM/desktop behaviour) - nothing global was deleted.
 *   2. PERMISSIONS (mission 16).  A29 granted EVERY permission request from ANY
 *      page.  A31 denies by default and grants only what this device and this
 *      trusted local origin actually have; every decision is logged.
 *   3. WEB PROCESS SUPERVISION (mission 15).  A dead WebKitWebProcess is now
 *      detected (web-process-terminated) and reloaded, bounded, instead of
 *      leaving a blank view forever.
 */
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
static int os_owns_boot_animation(void);

/* ============================================================================
 * TOUCH / INPUT DIAGNOSTIC INJECTION (A31, mission 11.5 + 12)
 *
 * The launcher source is NOT modified: this is a WebKit USER SCRIPT injected by
 * the host that reports, for one physical finger, exactly which browser events
 * the real Nuxel Home document received and which element they hit - and whether
 * the launcher's own app activation ran (`app:launch`, dispatched by
 * js/apps.js launchApp()).  Each report is forwarded to the native side through
 * a script-message handler and appended to /run/nuxel-home.state, so a single
 * physical tap can be correlated:
 *
 *   sec_ts IRQ  ->  /dev/input/event2 event  ->  nuxel-touch-arm TOUCH_POINT
 *     ->  libinput (shim log)  ->  phoc (owns event2)  ->  WebKit  ->  this log
 *
 * Disable with NUXEL_INPUT_DIAG=0.  It is a diagnostic, never a synthetic input
 * source: it only observes events that arrived from the real device.
 * ==========================================================================*/
static const char *DIAG_JS =
  "(function(){ try {"
  " if (window.__nuxelDiag) return; window.__nuxelDiag = 1;"
  " var post = function(kind, e) { try {"
  "   var t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0]) || null;"
  "   var x = (typeof e.clientX === 'number') ? e.clientX : (t ? t.clientX : -1);"
  "   var y = (typeof e.clientY === 'number') ? e.clientY : (t ? t.clientY : -1);"
  "   var el = e.target || {};"
  "   var id = el.id || '';"
  "   if (!id && el.closest) { var c = el.closest('[data-app-id],[data-app],.app-icon,.dock-item,.app-tile'); if (c) id = c.getAttribute('data-app-id') || c.getAttribute('data-app') || c.className; }"
  "   window.webkit.messageHandlers.nuxelDiag.postMessage("
  "     'EVT ' + kind + ' x=' + Math.round(x) + ' y=' + Math.round(y) +"
  "     ' tag=' + (el.tagName || '?') + ' id=' + id +"
  "     ' w=' + window.innerWidth + ' h=' + window.innerHeight +"
  "     ' dpr=' + (window.devicePixelRatio || 1) + ' splash=' + (document.getElementById('boot-splash') ? 'present' : 'absent'));"
  " } catch (err) {} };"
  " ['touchstart','touchmove','touchend','pointerdown','pointerup','click'].forEach(function(k){"
  "   document.addEventListener(k, function(e){ post(k, e); }, {passive:true, capture:true}); });"
  " document.addEventListener('app:launch', function(e){ try {"
  "   var a = (e.detail && e.detail.app) || {};"
  "   window.webkit.messageHandlers.nuxelDiag.postMessage('EVT app:launch id=' + (a.id || '?') + ' name=' + (a.name || '?'));"
  " } catch (err) {} }, true);"
  " post('diag-ready', {target:{tagName:'-'}, clientX:-1, clientY:-1});"
  " var probe = function(){ try {"
  "   var cs = getComputedStyle(document.body).backgroundImage || '';"
  "   var m = cs.match(/url\\(['\"]?([^'\")]+)['\"]?\\)/);"
  "   var url = m ? m[1] : '(none)';"
  "   if (url.charAt(0) === '/') url = location.origin + url;"
  "   var img = new Image();"
  "   img.onload = function(){ post('wallpaper url=' + url + ' decoded=1 natural=' + img.naturalWidth + 'x' + img.naturalHeight, {target:{tagName:'BODY'}, clientX:-1, clientY:-1}); };"
  "   img.onerror = function(){ post('wallpaper url=' + url + ' decoded=0', {target:{tagName:'BODY'}, clientX:-1, clientY:-1}); };"
  "   img.src = url;"
  " } catch (e) {} };"
  " if (document.readyState === 'complete') probe(); else window.addEventListener('load', probe);"
  " var splash = function(tag){ try {"
  "   var el = document.getElementById('boot-splash');"
  "   var pe = el ? getComputedStyle(el).pointerEvents : 'n/a';"
  "   var dz = el ? getComputedStyle(el).zIndex : 'n/a';"
  "   post('splash-' + tag + ' ' + (el ? 'present' : 'absent') + ' pointer-events=' + pe + ' z-index=' + dz,"
  "        {target:{tagName:'BODY'}, clientX:-1, clientY:-1});"
  " } catch (e) {} };"
  " setTimeout(function(){ splash('t1s'); }, 1000);"
  " setTimeout(function(){ splash('t4s'); }, 4000);"
  " setTimeout(function(){ splash('t9s'); }, 9000);"
  "} catch (e) {} })();";

/* The launcher's own js/app.js removes #boot-splash for ?boot=os, but only after
 * an `await` in its async init - measured live: at the document's `load` event the
 * element was STILL present (diag report `splash=present`).  Until it is gone it is
 * an opaque, z-index:99999, pointer-events:auto layer over the app grid, i.e. it
 * can both hide the launcher and swallow the first touches.  The host therefore
 * enforces the ownership policy itself, two ways, only in phone launch mode:
 *   * a user STYLE SHEET - declarative, applied before first paint, so the overlay
 *     is never visible and never hit-testable;
 *   * a user SCRIPT at document start with a MutationObserver that removes the
 *     element the moment it is parsed.
 * Both are no-ops for any other launch mode (the UTM/desktop behaviour is intact). */
static const char *POLICY_CSS =
  "#boot-splash{display:none !important;visibility:hidden !important;"
  "pointer-events:none !important}";

static const char *POLICY_JS =
  "(function(){ try {"
  " if (window.__nuxelBootOwner) return;"
  " if (new URLSearchParams(window.location.search).get('boot') !== 'os') return;"
  " window.__nuxelBootOwner = 1;"
  " var kill = function(){ try { var el = document.getElementById('boot-splash');"
  "   if (el) { if (el.parentNode) el.parentNode.removeChild(el); else el.style.display='none'; } } catch(e){} };"
  " kill();"
  " var mo = new MutationObserver(function(){ kill(); });"
  " try { mo.observe(document.documentElement, {childList:true, subtree:true}); } catch(e){}"
  " window.addEventListener('DOMContentLoaded', function(){ kill(); setTimeout(kill, 250); }, {once:true});"
  " setTimeout(function(){ kill(); try { mo.disconnect(); } catch(e){} }, 15000);"
  "} catch (e) {} })();";

static void on_diag_message(WebKitUserContentManager *m, WebKitJavascriptResult *r, gpointer d) {
  (void)m; (void)d;
  JSCValue *v = webkit_javascript_result_get_js_value(r);
  char *s = v ? jsc_value_to_string(v) : NULL;
  if (s) { st("NUXEL_INPUT %s", s); g_free(s); }
}

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

/* Web-process supervision (A31, mission 15): WebKit can lose its renderer for
 * reasons outside this view's control (the A29b media-sink crash was one).  A
 * view that is never reloaded stays blank forever - this reloads it, bounded, and
 * records the exact reason code from WebKit instead of guessing. */
static int webproc_reloads;
static gboolean on_web_process_terminated(WebKitWebView *v, WebKitWebProcessTerminationReason reason, gpointer d) {
  (void)d;
  st("NUXEL_HOME_WEBPROC_TERMINATED reason=%d reload=%d", (int)reason, webproc_reloads);
  if (webproc_reloads < 5) { webproc_reloads++; webkit_web_view_reload(v); }
  else st("NUXEL_HOME_WEBPROC_GIVEUP reloads=%d", webproc_reloads);
  return FALSE;
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

/* A31 permission policy: deny by default, allow only from the trusted local
   origin, and only the capability the launcher legitimately uses (notifications -
 * js/app.js requests notifications:receive).  Camera/microphone are denied
 * because there is no working media path on this kernel, so the launcher reports
 * them truthfully as unavailable rather than holding a permission it cannot use.
 * Every request and decision is written to the state file. */
static void on_permission(WebKitWebView *v, WebKitPermissionRequest *r, gpointer d) {
  (void)d;
  const char *trusted = getenv("NUXEL_TRUSTED_ORIGIN");
  if (!trusted || !*trusted) trusted = "http://127.0.0.1:8000";
  const gchar *uri = webkit_web_view_get_uri(v);
  gboolean from_trusted = uri && g_str_has_prefix(uri, trusted);
  gboolean allow = FALSE;
  const char *reason = "denied-default";
  if (!from_trusted) {
    reason = "denied-untrusted-origin";
  } else if (WEBKIT_IS_NOTIFICATION_PERMISSION_REQUEST(r)) {
    allow = TRUE; reason = "allowed-notifications";
  } else if (WEBKIT_IS_USER_MEDIA_PERMISSION_REQUEST(r)) {
    reason = "denied-no-camera-or-microphone";
  } else {
    reason = "denied-not-required-by-launcher";
  }
  if (allow) webkit_permission_request_allow(r); else webkit_permission_request_deny(r);
  st("NUXEL_PERMISSION type=%s uri=%s trusted=%d allow=%d reason=%s",
     G_OBJECT_TYPE_NAME(r), uri ? uri : "?", from_trusted ? 1 : 0, allow ? 1 : 0, reason);
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
  const char *diag_env = getenv("NUXEL_INPUT_DIAG");
  gboolean diag = !(diag_env && diag_env[0] == '0');
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
  WebKitUserContentManager *ucm = webkit_user_content_manager_new();
  if (os_owns_boot_animation()) {   /* forward decl used here; defined below main's help */
    WebKitUserStyleSheet *ss = webkit_user_style_sheet_new(POLICY_CSS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME, WEBKIT_USER_STYLE_LEVEL_USER, NULL, NULL);
    webkit_user_content_manager_add_style_sheet(ucm, ss);
    webkit_user_style_sheet_unref(ss);
    WebKitUserScript *ps = webkit_user_script_new(POLICY_JS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, ps);
    webkit_user_script_unref(ps);
    st("NUXEL_BOOT_POLICY host-enforced=1 css=1 dom_removal=1 (phone launch mode)");
  }
  if (diag) {
    webkit_user_content_manager_register_script_message_handler(ucm, "nuxelDiag");
    g_signal_connect(ucm, "script-message-received::nuxelDiag", G_CALLBACK(on_diag_message), NULL);
    WebKitUserScript *us = webkit_user_script_new(DIAG_JS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, us);
    webkit_user_script_unref(us);
    st("NUXEL_INPUT_DIAG enabled=1 (user-script observer; launcher source unmodified)");
  }
  WebKitWebView *v = WEBKIT_WEB_VIEW(
      webkit_web_view_new_with_user_content_manager(ucm));
  webkit_web_view_set_settings(v, s);
  g_object_unref(ucm);
  g_object_unref(s);
  g_signal_connect(v, "load-changed", G_CALLBACK(on_load_changed), NULL);
  g_signal_connect(v, "load-failed", G_CALLBACK(on_load_failed), NULL);
  g_signal_connect(v, "create", G_CALLBACK(on_create), NULL);
  g_signal_connect(v, "permission-request", G_CALLBACK(on_permission), NULL);
  g_signal_connect(v, "web-process-terminated", G_CALLBACK(on_web_process_terminated), NULL);
  g_signal_connect(v, "notify::uri", G_CALLBACK(on_notify_uri), NULL);
  return v;
}

/* Is the OS the boot-animation owner for this launch?  On the phone: yes (the
 * initramfs player already ran).  NUXEL_PWA_SPLASH=1 opts back into the PWA's
 * own splash, which is what the UTM/desktop path wants. */
static int os_owns_boot_animation(void) {
  const char *e = getenv("NUXEL_PWA_SPLASH");
  return !(e && e[0] == '1');
}

int main(int argc, char **argv) {
  gtk_init(&argc, &argv);
  const char *url = getenv("NUXEL_HOME_URL");
  if (!url || !*url) url = DEFAULT_URL;
  char urlbuf[768];
  if (os_owns_boot_animation()) {
    snprintf(urlbuf, sizeof urlbuf, "%s%sboot=os", url, strchr(url, '?') ? "&" : "?");
    url = urlbuf;
  }

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

  st("NUXEL_HOME_BOOT_OWNER os_animation=%d splash_removed_by_launcher=%d",
     os_owns_boot_animation(), os_owns_boot_animation());
  st("NUXEL_HOME_OPEN url=%s engine=WebKitGTK/%d.%d", url,
     webkit_get_major_version(), webkit_get_minor_version());
  webkit_web_view_load_uri(WEBKIT_WEB_VIEW(v), url);
  gtk_main();
  st("NUXEL_HOME_EXIT");
  return 0;
}
