/* GTK3 GDK/GL probe: separate from GTK4 GSK and from WebKitGTK. */
#include <gtk/gtk.h>
#include <epoxy/gl.h>
#include <stdio.h>
static gboolean draw(GtkGLArea *a, GdkGLContext *c, gpointer d) {
  (void)a; (void)d;
  glClearColor(0.1f, 0.7f, 0.3f, 1.0f);
  glClear(GL_COLOR_BUFFER_BIT);
  printf("{\"gtk3_gl\":\"PASS\",\"gl_version\":\"%s\",\"gl_renderer\":\"%s\",\"gl_vendor\":\"%s\"}\n",
         glGetString(GL_VERSION), glGetString(GL_RENDERER), glGetString(GL_VENDOR));
  return TRUE;
}
int main(int argc, char **argv) {
  gtk_init(&argc, &argv);
  GtkWidget *w = gtk_window_new(GTK_WINDOW_TOPLEVEL);
  GtkWidget *a = gtk_gl_area_new();
  g_signal_connect(a, "render", G_CALLBACK(draw), NULL);
  gtk_container_add(GTK_CONTAINER(w), a);
  gtk_widget_show_all(w);
  g_timeout_add(2500, (GSourceFunc)gtk_main_quit, NULL);
  gtk_main();
  return 0;
}
