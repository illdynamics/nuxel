/* nuxel-wayland-egl-probe — prove EGL/GLES on the live Wayland session.
 *
 * It intentionally does not infer success from an EGLDisplay: a PASS means a
 * wl_surface was created, a GLES2 context rendered, and eglSwapBuffers()
 * submitted at least one buffer to the compositor.  The test pattern has
 * distinct corner colours so a screenshot can prove presentation.
 *
 * Build (inside the aarch64 container or on the phone):
 *   cc -O2 -o nuxel-wayland-egl-probe nuxel-wayland-egl-probe.c \
 *      $(pkg-config --cflags --libs egl glesv2 wayland-client wayland-egl)
 */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <wayland-client.h>
#include <wayland-egl.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef EGL_PLATFORM_WAYLAND_KHR
#define EGL_PLATFORM_WAYLAND_KHR 0x31D8
#endif

struct ctx {
  struct wl_display *dpy;
  struct wl_registry *registry;
  struct wl_compositor *compositor;
  struct wl_surface *surface;
  struct wl_egl_window *window;
  EGLDisplay edpy;
  EGLConfig config;
  EGLContext context;
  EGLSurface esurface;
};

static void registry_global(void *data, struct wl_registry *r, uint32_t name,
                            const char *iface, uint32_t version) {
  struct ctx *c = data;
  if (strcmp(iface, "wl_compositor") == 0)
    c->compositor = wl_registry_bind(r, name, &wl_compositor_interface,
                                     version < 4 ? version : 4);
}
static void registry_global_remove(void *data, struct wl_registry *r,
                                   uint32_t name) {
  (void)data; (void)r; (void)name;
}
static const struct wl_registry_listener registry_listener = {
    registry_global, registry_global_remove};

static GLuint compile(GLenum type, const char *src) {
  GLuint s = glCreateShader(type);
  glShaderSource(s, 1, &src, NULL);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[1024] = {0};
    glGetShaderInfoLog(s, sizeof(log) - 1, NULL, log);
    fprintf(stderr, "shader error: %s\n", log);
  }
  return s;
}

int main(int argc, char **argv) {
  int frames = argc > 1 ? atoi(argv[1]) : 3;
  struct ctx c = {0};
  int rc = 1;
  if (frames < 1) frames = 1;

  const char *wl = getenv("WAYLAND_DISPLAY");
  const char *rt = getenv("XDG_RUNTIME_DIR");
  printf("{\"probe\":\"wayland-egl\",\"wayland_display\":\"%s\","
         "\"xdg_runtime_dir\":\"%s\",\"frames_requested\":%d}\n",
         wl ? wl : "", rt ? rt : "", frames);

  c.dpy = wl_display_connect(NULL);
  if (!c.dpy) {
    fprintf(stderr, "wl_display_connect failed: %s\n", strerror(errno));
    return 2;
  }
  c.registry = wl_display_get_registry(c.dpy);
  wl_registry_add_listener(c.registry, &registry_listener, &c);
  wl_display_roundtrip(c.dpy);
  if (!c.compositor) {
    fprintf(stderr, "no wl_compositor global\n");
    rc = 3;
    goto out;
  }

  PFNEGLGETPLATFORMDISPLAYEXTPROC get_platform_display =
      (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress(
          "eglGetPlatformDisplayEXT");
  PFNEGLGETPLATFORMDISPLAYPROC get_platform_display2 =
      (PFNEGLGETPLATFORMDISPLAYPROC)eglGetProcAddress("eglGetPlatformDisplay");
  if (get_platform_display)
    c.edpy = get_platform_display(EGL_PLATFORM_WAYLAND_KHR, c.dpy, NULL);
  else if (get_platform_display2)
    c.edpy = get_platform_display2(EGL_PLATFORM_WAYLAND_KHR, c.dpy, NULL);
  else
    c.edpy = eglGetDisplay((EGLNativeDisplayType)c.dpy);
  if (c.edpy == EGL_NO_DISPLAY) {
    fprintf(stderr, "eglGetPlatformDisplay(WAYLAND) failed 0x%x\n",
            eglGetError());
    rc = 4;
    goto out;
  }
  EGLint major = 0, minor = 0;
  if (!eglInitialize(c.edpy, &major, &minor)) {
    fprintf(stderr, "eglInitialize failed 0x%x\n", eglGetError());
    rc = 5;
    goto out;
  }
  printf("{\"egl_vendor\":\"%s\",\"egl_version\":\"%s\","
         "\"egl_client_extensions\":\"%s\"}\n",
         eglQueryString(c.edpy, EGL_VENDOR),
         eglQueryString(c.edpy, EGL_VERSION),
         eglQueryString(EGL_NO_DISPLAY, EGL_EXTENSIONS));
  if (!eglBindAPI(EGL_OPENGL_ES_API)) {
    fprintf(stderr, "eglBindAPI failed 0x%x\n", eglGetError());
    rc = 6;
    goto out;
  }
  static const EGLint cfg_attribs[] = {
      EGL_SURFACE_TYPE, EGL_WINDOW_BIT, EGL_RENDERABLE_TYPE,
      EGL_OPENGL_ES2_BIT, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8,
      EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE};
  EGLint ncfg = 0;
  if (!eglChooseConfig(c.edpy, cfg_attribs, &c.config, 1, &ncfg) || ncfg < 1) {
    fprintf(stderr, "eglChooseConfig failed 0x%x ncfg=%d\n", eglGetError(),
            ncfg);
    rc = 7;
    goto out;
  }
  c.surface = wl_compositor_create_surface(c.compositor);
  c.window = wl_egl_window_create(c.surface, 720, 1520);
  if (!c.window) {
    fprintf(stderr, "wl_egl_window_create failed\n");
    rc = 8;
    goto out;
  }
  static const EGLint ctx_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
  c.context = eglCreateContext(c.edpy, c.config, EGL_NO_CONTEXT, ctx_attribs);
  if (c.context == EGL_NO_CONTEXT) {
    fprintf(stderr, "eglCreateContext failed 0x%x\n", eglGetError());
    rc = 9;
    goto out;
  }
  c.esurface = eglCreateWindowSurface(c.edpy, c.config,
                                      (EGLNativeWindowType)c.window, NULL);
  if (c.esurface == EGL_NO_SURFACE) {
    fprintf(stderr, "eglCreateWindowSurface failed 0x%x\n", eglGetError());
    rc = 10;
    goto out;
  }
  if (!eglMakeCurrent(c.edpy, c.esurface, c.esurface, c.context)) {
    fprintf(stderr, "eglMakeCurrent failed 0x%x\n", eglGetError());
    rc = 11;
    goto out;
  }
  printf("{\"gl_version\":\"%s\",\"gl_renderer\":\"%s\","
         "\"gl_vendor\":\"%s\",\"egl_extensions\":\"%s\"}\n",
         glGetString(GL_VERSION), glGetString(GL_RENDERER),
         glGetString(GL_VENDOR), eglQueryString(c.edpy, EGL_EXTENSIONS));

  const char *vs_src =
      "attribute vec2 p; varying vec2 uv;"
      "void main(){uv=p*0.5+0.5;gl_Position=vec4(p,0.0,1.0);}";
  const char *fs_src =
      "precision mediump float; varying vec2 uv;"
      "void main(){gl_FragColor=vec4(uv.x, uv.y, 0.25+0.5*uv.x*uv.y, 1.0);}";
  GLuint vs = compile(GL_VERTEX_SHADER, vs_src);
  GLuint fs = compile(GL_FRAGMENT_SHADER, fs_src);
  GLuint prog = glCreateProgram();
  glAttachShader(prog, vs);
  glAttachShader(prog, fs);
  glBindAttribLocation(prog, 0, "p");
  glLinkProgram(prog);
  GLint linked = 0;
  glGetProgramiv(prog, GL_LINK_STATUS, &linked);
  if (!linked) {
    char log[1024] = {0};
    glGetProgramInfoLog(prog, sizeof(log) - 1, NULL, log);
    fprintf(stderr, "link failed: %s\n", log);
    rc = 12;
    goto out;
  }
  glUseProgram(prog);
  static const GLfloat tri[] = {-1, -1, 3, -1, -1, 3};
  glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, tri);
  glEnableVertexAttribArray(0);
  glViewport(0, 0, 720, 1520);
  for (int i = 0; i < frames; i++) {
    glClearColor(0.02f, 0.02f, 0.06f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();
    if (!eglSwapBuffers(c.edpy, c.esurface)) {
      fprintf(stderr, "eglSwapBuffers failed on frame %d: 0x%x\n", i,
              eglGetError());
      rc = 13;
      goto out;
    }
    wl_display_roundtrip(c.dpy);
  }
  printf("{\"swapbuffers\":%d,\"result\":\"PASS\"}\n", frames);
  rc = 0;
out:
  if (c.esurface != EGL_NO_SURFACE) eglDestroySurface(c.edpy, c.esurface);
  if (c.context != EGL_NO_CONTEXT) eglDestroyContext(c.edpy, c.context);
  if (c.window) wl_egl_window_destroy(c.window);
  if (c.surface) wl_surface_destroy(c.surface);
  if (c.edpy != EGL_NO_DISPLAY) eglTerminate(c.edpy);
  if (c.registry) wl_registry_destroy(c.registry);
  if (c.dpy) wl_display_disconnect(c.dpy);
  return rc;
}
