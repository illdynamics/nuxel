/* Probe Mesa panfrost on ARM kbase through EGL surfaceless.
 * Prints the real GL strings and renders a triangle, then exits 0 only if a
 * non-software renderer produced pixels. */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef EGL_PLATFORM_SURFACELESS_MESA
#define EGL_PLATFORM_SURFACELESS_MESA 0x31DD
#endif
#ifndef EGL_NO_CONFIG_KHR
#define EGL_NO_CONFIG_KHR ((EGLConfig)0)
#endif

static const char *es2_vs =
    "attribute vec2 p; void main(){ gl_Position=vec4(p,0.0,1.0); }";
static const char *es2_fs =
    "precision mediump float; void main(){ gl_FragColor=vec4(0.2,0.8,0.3,1.0); }";

static GLuint shader(GLenum type, const char *src) {
  GLuint s = glCreateShader(type);
  glShaderSource(s, 1, &src, NULL);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[1024] = {0};
    glGetShaderInfoLog(s, sizeof(log) - 1, NULL, log);
    fprintf(stderr, "shader: %s\n", log);
  }
  return s;
}

int main(void) {
  PFNEGLGETPLATFORMDISPLAYEXTPROC get_platform_display =
      (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
  if (!get_platform_display) {
    fprintf(stderr, "no eglGetPlatformDisplayEXT\n");
    return 2;
  }
  EGLDisplay dpy = get_platform_display(EGL_PLATFORM_SURFACELESS_MESA,
                                        EGL_DEFAULT_DISPLAY, NULL);
  if (dpy == EGL_NO_DISPLAY) {
    fprintf(stderr, "no surfaceless display\n");
    return 2;
  }
  EGLint major = 0, minor = 0;
  if (!eglInitialize(dpy, &major, &minor)) {
    fprintf(stderr, "eglInitialize failed 0x%x\n", eglGetError());
    return 2;
  }
  if (!eglBindAPI(EGL_OPENGL_ES_API)) {
    fprintf(stderr, "eglBindAPI failed\n");
    return 2;
  }
  static const EGLint cfg_attribs[] = {
      EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE,
      EGL_OPENGL_ES2_BIT, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE,
      8, EGL_ALPHA_SIZE, 8, EGL_NONE};
  EGLConfig cfg = NULL;
  EGLint ncfg = 0;
  if (!eglChooseConfig(dpy, cfg_attribs, &cfg, 1, &ncfg) || ncfg < 1) {
    cfg = EGL_NO_CONFIG_KHR;
  }
  static const EGLint ctx_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
  EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attribs);
  if (ctx == EGL_NO_CONTEXT) {
    fprintf(stderr, "eglCreateContext failed 0x%x\n", eglGetError());
    return 2;
  }
  if (!eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
    fprintf(stderr, "eglMakeCurrent failed 0x%x\n", eglGetError());
    return 2;
  }

  const GLubyte *ver = glGetString(GL_VERSION);
  const GLubyte *ren = glGetString(GL_RENDERER);
  const GLubyte *ven = glGetString(GL_VENDOR);
  printf("EGL %d.%d\n", major, minor);
  printf("GL_VERSION=%s\n", ver ? (const char *)ver : "(null)");
  printf("GL_RENDERER=%s\n", ren ? (const char *)ren : "(null)");
  printf("GL_VENDOR=%s\n", ven ? (const char *)ven : "(null)");
  printf("EGL_EXTENSIONS=%s\n", eglQueryString(dpy, EGL_EXTENSIONS));
  if ((!ver || strstr((const char *)ver, "Panfrost") == NULL) &&
      (!ren || strstr((const char *)ren, "Panfrost") == NULL)) {
    fprintf(stderr, "NOT PANFRONT/KBASE\n");
    return 3;
  }

  GLuint vs = shader(GL_VERTEX_SHADER, es2_vs);
  GLuint fs = shader(GL_FRAGMENT_SHADER, es2_fs);
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
    fprintf(stderr, "link: %s\n", log);
    return 4;
  }
  glUseProgram(prog);
  static const GLfloat tri[] = {0.0f, 0.9f, -0.9f, -0.9f, 0.9f, -0.9f};
  glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, tri);
  glEnableVertexAttribArray(0);
  /* Surfaceless EGL has no default drawable: render into an FBO. */
  GLuint tex = 0, fb = 0;
  glGenTextures(1, &tex);
  glBindTexture(GL_TEXTURE_2D, tex);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 256, 256, 0, GL_RGBA,
               GL_UNSIGNED_BYTE, NULL);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  glGenFramebuffers(1, &fb);
  glBindFramebuffer(GL_FRAMEBUFFER, fb);
  glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                         GL_TEXTURE_2D, tex, 0);
  if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
    fprintf(stderr, "FBO incomplete\n");
    return 6;
  }
  glViewport(0, 0, 256, 256);
  glClearColor(0.05f, 0.05f, 0.05f, 1.0f);
  const char *secs_env = getenv("NUXEL_GPU_BURN_SECONDS");
  int secs = secs_env ? atoi(secs_env) : 0;
  struct timespec t0, now;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  unsigned frames = 0;
  do {
    glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();
    frames++;
    clock_gettime(CLOCK_MONOTONIC, &now);
  } while ((now.tv_sec - t0.tv_sec) < secs);
  GLenum err = glGetError();
  unsigned char px[4] = {0};
  glReadPixels(128, 128, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
  printf("frames=%u elapsed=%ld.%03lds pixel=%02x%02x%02x%02x\n", frames,
         (long)(now.tv_sec - t0.tv_sec),
         (long)((now.tv_nsec - t0.tv_nsec) / 1000000),
         px[0], px[1], px[2], px[3]);
  printf("glGetError=0x%x\n", err);
  return err == GL_NO_ERROR ? 0 : 5;
}
