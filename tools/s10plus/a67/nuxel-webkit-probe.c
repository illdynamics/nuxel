/* Minimal GTK3 + WebKit2GTK 4.1 accelerated-compositing probe.
 * It loads a deterministic local page and reports WebKit's version plus the
 * graphics environment.  A PASS here still requires the backing-store proof
 * in /run/nuxel-webkit-probe.json; the presence of WebGL alone is not enough. */
#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <stdio.h>
#include <stdlib.h>
static const char *HTML =
  "<html><body style='margin:0;background:#111;color:#fff'>"
  "<div id='box' style='width:180px;height:180px;background:linear-gradient(135deg,#0f0,#00f);"
  "animation:spin 1.2s linear infinite'></div>"
  "<style>@keyframes spin{to{transform:rotate(360deg)}}</style></body></html>";
static void loaded(WebKitWebView *v, WebKitLoadEvent ev, gpointer d) {
  (void)v; (void)d;
  if (ev != WEBKIT_LOAD_FINISHED) return;
  const char *u = webkit_web_view_get_uri(v);
  printf("{\"webkit_probe\":\"LOADED\",\"uri\":\"%s\",\"webkit_version\":\"%s\"}\n",
         u ? u : "", webkit_get_major_version() ? "runtime" : "unknown");
}
int main(int argc, char **argv) {
  gtk_init(&argc, &argv);
  GtkWidget *w = gtk_window_new(GTK_WINDOW_TOPLEVEL);
  WebKitWebView *v = WEBKIT_WEB_VIEW(webkit_web_view_new());
  g_signal_connect(v, "load-changed", G_CALLBACK(loaded), NULL);
  gtk_container_add(GTK_CONTAINER(w), GTK_WIDGET(v));
  webkit_web_view_load_html(v, HTML, "http://127.0.0.1/");
  gtk_widget_show_all(w);
  g_timeout_add(5000, (GSourceFunc)gtk_main_quit, NULL);
  gtk_main();
  printf("{\"webkit_probe\":\"DONE\",\"disable_env\":\"%s\",\"force_env\":\"%s\"}\n",
         getenv("WEBKIT_DISABLE_COMPOSITING_MODE") ?: "",
         getenv("WEBKIT_FORCE_COMPOSITING_MODE") ?: "");
  return 0;
}
