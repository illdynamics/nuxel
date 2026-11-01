/*
 * nuxel-kbase-egl — LD_PRELOAD shim: let wlroots/phoc use the Mali-G76
 * through Mesa panfrost on the proprietary Samsung kbase driver.
 *
 * The stock wlroots 0.19 renderer_autocreate() insists on a DRM render node
 * before it will construct a GLES2 renderer.  This S10+ vendor kernel has no
 * DRM device at all (only /dev/mali0 via ARM kbase), so wlroots falls back to
 * pixman.  Mesa's panfrost gallium driver can drive kbase directly when EGL
 * is brought up on the surfaceless platform with MESA_KBASE_NODE=/dev/mali0.
 *
 * This shim replaces only wlr_renderer_autocreate().  When NUXEL_KBASE_EGL=1
 * is present it creates that EGL display + ES2 context, hands them to the
 * still-exported wlr_egl_create_with_context()/wlr_gles2_renderer_create(),
 * and otherwise falls back to the unmodified wlroots allocator.  A failure
 * here can only cost performance: the original pixman path is always tried
 * before returning NULL.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef EGL_PLATFORM_SURFACELESS_MESA
#define EGL_PLATFORM_SURFACELESS_MESA 0x31DD
#endif
#ifndef EGL_NO_CONFIG_KHR
#define EGL_NO_CONFIG_KHR ((EGLConfig)0)
#endif

struct wlr_egl;
struct wlr_renderer;

typedef void *(*autocreate_fn)(void *);
typedef struct wlr_egl *(*egl_create_ctx_fn)(EGLDisplay, EGLContext);
typedef struct wlr_renderer *(*gles2_create_fn)(struct wlr_egl *);
typedef struct wlr_renderer *(*pixman_create_fn)(void);

static void *wlroots_handle(void) {
  static void *h;
  if (h)
    return h;
  /* The caller already has libwlroots loaded; prefer that exact object. */
  h = dlopen("/usr/lib64/libwlroots-0.19.so", RTLD_NOW | RTLD_NOLOAD);
  if (!h)
    h = dlopen("libwlroots-0.19.so", RTLD_NOW);
  return h;
}

static int kbase_enabled(void) {
  const char *v = getenv("NUXEL_KBASE_EGL");
  return v && (strcmp(v, "1") == 0 || strcmp(v, "yes") == 0 ||
               strcmp(v, "true") == 0);
}

static EGLDisplay surfaceless_display(void) {
  PFNEGLGETPLATFORMDISPLAYEXTPROC get_platform_display =
      (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
  if (!get_platform_display)
    get_platform_display =
        (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplay");
  if (!get_platform_display) {
    fprintf(stderr, "nuxel-kbase-egl: no eglGetPlatformDisplay\n");
    return EGL_NO_DISPLAY;
  }
  return get_platform_display(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
}

static EGLContext make_es2_context(EGLDisplay dpy) {
  EGLint major = 0, minor = 0;
  if (!eglInitialize(dpy, &major, &minor)) {
    fprintf(stderr, "nuxel-kbase-egl: eglInitialize failed 0x%x\n", eglGetError());
    return EGL_NO_CONTEXT;
  }
  if (!eglBindAPI(EGL_OPENGL_ES_API)) {
    fprintf(stderr, "nuxel-kbase-egl: eglBindAPI(ES) failed\n");
    return EGL_NO_CONTEXT;
  }

  static const EGLint cfg_attribs[] = {
      EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
      EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
      EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
      EGL_NONE};
  EGLConfig cfg = NULL;
  EGLint ncfg = 0;
  if (!eglChooseConfig(dpy, cfg_attribs, &cfg, 1, &ncfg) || ncfg < 1) {
    fprintf(stderr, "nuxel-kbase-egl: no pbuffer ES2 config (0x%x); "
                    "trying configless\n", eglGetError());
    cfg = EGL_NO_CONFIG_KHR;
  }

  static const EGLint ctx_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
  EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attribs);
  if (ctx == EGL_NO_CONTEXT) {
    fprintf(stderr, "nuxel-kbase-egl: eglCreateContext failed 0x%x\n",
            eglGetError());
    return EGL_NO_CONTEXT;
  }
  return ctx;
}

static struct wlr_renderer *try_kbase(void) {
  void *h = wlroots_handle();
  if (!h) {
    fprintf(stderr, "nuxel-kbase-egl: cannot resolve libwlroots\n");
    return NULL;
  }
  egl_create_ctx_fn create_egl =
      (egl_create_ctx_fn)dlsym(h, "wlr_egl_create_with_context");
  gles2_create_fn create_gles2 =
      (gles2_create_fn)dlsym(h, "wlr_gles2_renderer_create");
  if (!create_egl || !create_gles2) {
    fprintf(stderr, "nuxel-kbase-egl: wlroots lacks EGL/GLES2 entry points\n");
    return NULL;
  }

  EGLDisplay dpy = surfaceless_display();
  if (dpy == EGL_NO_DISPLAY)
    return NULL;
  EGLContext ctx = make_es2_context(dpy);
  if (ctx == EGL_NO_CONTEXT) {
    eglTerminate(dpy);
    return NULL;
  }

  struct wlr_egl *egl = create_egl(dpy, ctx);
  if (!egl) {
    fprintf(stderr, "nuxel-kbase-egl: wlr_egl_create_with_context failed\n");
    eglDestroyContext(dpy, ctx);
    eglTerminate(dpy);
    return NULL;
  }
  struct wlr_renderer *renderer = create_gles2(egl);
  if (!renderer) {
    fprintf(stderr, "nuxel-kbase-egl: wlr_gles2_renderer_create failed; "
                    "falling back\n");
    /* wlr_egl_destroy is not exported in all builds; leak the tiny wrapper
       rather than risk tearing down a display we no longer own. */
    return NULL;
  }
  fprintf(stderr, "nuxel-kbase-egl: Mali kbase GLES2 renderer active\n");
  return renderer;
}

__attribute__((visibility("default")))
struct wlr_renderer *wlr_renderer_autocreate(void *backend) {
  if (kbase_enabled()) {
    struct wlr_renderer *r = try_kbase();
    if (r)
      return r;
    fprintf(stderr, "nuxel-kbase-egl: GPU path unavailable; using wlroots "
                    "default renderer selection\n");
  }

  void *h = wlroots_handle();
  autocreate_fn real = h ? (autocreate_fn)dlsym(h, "wlr_renderer_autocreate") : NULL;
  if (real) {
    /* The shim symbol is what the caller resolved; dlsym on the library handle
       returns the library's own definition, not this interposer. */
    return real(backend);
  }
  fprintf(stderr, "nuxel-kbase-egl: no wlroots renderer_autocreate\n");
  return NULL;
}
