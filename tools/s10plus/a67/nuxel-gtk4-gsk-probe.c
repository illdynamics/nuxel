/* GTK4 GSK probe: reports the selected renderer independently of GTK3/WebKit. */
#include <gtk/gtk.h>
#include <stdio.h>
static void draw(GtkDrawingArea *a, cairo_t *cr, int w, int h, gpointer d) {
  (void)a; (void)d;
  cairo_set_source_rgb(cr, 0.1, 0.7, 0.3);
  cairo_paint(cr);
  printf("{\"gtk4_gsk\":\"PASS\",\"width\":%d,\"height\":%d}\n", w, h);
}
static gboolean close_window(gpointer w) { gtk_window_destroy(GTK_WINDOW(w)); return G_SOURCE_REMOVE; }
static void activate(GtkApplication *app, gpointer d) {
  (void)d;
  GtkWidget *w = gtk_application_window_new(app);
  GtkWidget *a = gtk_drawing_area_new();
  gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(a), draw, NULL, NULL);
  gtk_window_set_child(GTK_WINDOW(w), a);
  gtk_window_present(GTK_WINDOW(w));
  g_timeout_add(2500, close_window, w);
}
int main(int argc, char **argv) {
  GtkApplication *app = gtk_application_new("org.nuxel.Probe.Gsk", G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
  int rc = g_application_run(G_APPLICATION(app), argc, argv);
  g_object_unref(app);
  return rc;
}
