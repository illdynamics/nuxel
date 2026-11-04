/* Nuxel GLES2 offscreen benchmark (PWNAGE-60000 completion evidence).
 *
 * Renders a full-screen quad with a bounded fragment-shader loop into a
 * surfaceless EGL FBO and reports frames/second after glFinish().  It is a
 * workload/back-end discriminator, not a game benchmark.
 *
 * Usage: nuxel-gles-bench [--seconds N] [--size N] [--label TEXT]
 * Note: run with the kbase EGL environment for Mali, and with
 * LIBGL_ALWAYS_SOFTWARE=1 + the stock Mesa vendor JSON for llvmpipe.
 */
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

static const char *VS =
    "attribute vec2 p; varying vec2 uv;"
    "void main(){ uv=p*0.5+0.5; gl_Position=vec4(p,0.0,1.0); }";

/* 128 dependent-ish iterations: enough ALU work per fragment to be measurable
 * on both Mali and llvmpipe without relying on texture bandwidth. */
static const char *FS =
    "precision highp float; varying vec2 uv;"
    "void main(){ float a=uv.x, b=uv.y, s=0.0;"
    "  for (int i=0;i<128;i++){ float f=float(i);"
    "    a=fract(a+b*0.001+f*0.0001); b=fract(b+a*0.001+f*0.0001);"
    "    s+=a*b; }"
    "  gl_FragColor=vec4(fract(s), fract(s*1.7), fract(s*2.3), 1.0); }";

static GLuint mk(GLenum t, const char *src) {
  GLuint s = glCreateShader(t);
  glShaderSource(s, 1, &src, NULL);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[1024] = {0};
    glGetShaderInfoLog(s, sizeof(log) - 1, NULL, log);
    fprintf(stderr, "shader: %s\n", log);
    exit(4);
  }
  return s;
}

static double now(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
  int secs = 5, size = 512;
  const char *label = "unlabelled";
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--seconds") && i + 1 < argc) secs = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--size") && i + 1 < argc) size = atoi(argv[++i]);
    else if (!strcmp(argv[i], "--label") && i + 1 < argc) label = argv[++i];
  }
  if (secs < 1 || secs > 120 || size < 64 || size > 2048) {
    fprintf(stderr, "usage: %s [--seconds 1..120] [--size 64..2048] [--label T]\n", argv[0]);
    return 2;
  }

  PFNEGLGETPLATFORMDISPLAYEXTPROC get_dpy =
      (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
  if (!get_dpy) { fprintf(stderr, "no eglGetPlatformDisplayEXT\n"); return 2; }
  EGLDisplay dpy = get_dpy(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
  EGLint major = 0, minor = 0;
  if (dpy == EGL_NO_DISPLAY || !eglInitialize(dpy, &major, &minor)) {
    fprintf(stderr, "eglInitialize failed 0x%x\n", eglGetError());
    return 2;
  }
  if (!eglBindAPI(EGL_OPENGL_ES_API)) { fprintf(stderr, "eglBindAPI failed\n"); return 2; }
  static const EGLint cfg_attribs[] = {
      EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE,
      EGL_OPENGL_ES2_BIT, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8,
      EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE};
  EGLConfig cfg = NULL;
  EGLint ncfg = 0;
  if (!eglChooseConfig(dpy, cfg_attribs, &cfg, 1, &ncfg) || ncfg < 1)
    cfg = EGL_NO_CONFIG_KHR;
  static const EGLint ctx_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
  EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attribs);
  if (ctx == EGL_NO_CONTEXT ||
      !eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx)) {
    fprintf(stderr, "context/makecurrent failed 0x%x\n", eglGetError());
    return 2;
  }

  const char *ren = (const char *)glGetString(GL_RENDERER);
  const char *ver = (const char *)glGetString(GL_VERSION);
  GLuint tex = 0, fb = 0;
  glGenTextures(1, &tex);
  glBindTexture(GL_TEXTURE_2D, tex);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size, size, 0, GL_RGBA,
               GL_UNSIGNED_BYTE, NULL);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  glGenFramebuffers(1, &fb);
  glBindFramebuffer(GL_FRAMEBUFFER, fb);
  glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                         GL_TEXTURE_2D, tex, 0);
  if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
    fprintf(stderr, "FBO incomplete\n");
    return 3;
  }
  GLuint vs = mk(GL_VERTEX_SHADER, VS), fs = mk(GL_FRAGMENT_SHADER, FS);
  GLuint prog = glCreateProgram();
  glAttachShader(prog, vs); glAttachShader(prog, fs);
  glBindAttribLocation(prog, 0, "p");
  glLinkProgram(prog);
  GLint linked = 0;
  glGetProgramiv(prog, GL_LINK_STATUS, &linked);
  if (!linked) { fprintf(stderr, "program link failed\n"); return 4; }
  glUseProgram(prog);
  static const GLfloat quad[] = {-1,-1, 1,-1, -1,1, 1,1};
  glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, quad);
  glEnableVertexAttribArray(0);
  glViewport(0, 0, size, size);
  glClearColor(0.0f, 0.0f, 0.0f, 1.0f);

  for (int i = 0; i < 8; i++) { glClear(GL_COLOR_BUFFER_BIT); glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); }
  glFinish();

  unsigned frames = 0;
  double t0 = now(), t1 = t0;
  do {
    glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glFinish();
    frames++;
    t1 = now();
  } while (t1 - t0 < (double)secs);
  GLenum err = glGetError();
  unsigned char px[4] = {0};
  glReadPixels(size / 2, size / 2, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
  double elapsed = t1 - t0;
  printf("BENCH label=%s renderer=\"%s\" version=\"%s\" size=%d frames=%u "
         "seconds=%.3f fps=%.1f pixel=%02x%02x%02x%02x gl_error=0x%x\n",
         label, ren ? ren : "(null)", ver ? ver : "(null)", size, frames,
         elapsed, (double)frames / elapsed, px[0], px[1], px[2], px[3], err);
  return (err == GL_NO_ERROR && px[0] + px[1] + px[2] > 0) ? 0 : 5;
}
