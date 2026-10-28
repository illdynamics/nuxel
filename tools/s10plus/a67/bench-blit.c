/* bench-blit — offline benchmark + pixel-exact verification for the A67
 * nuxel-wl-fb blit() rewrite.  No /dev/fb0, no Wayland, no handset required.
 *
 * It contains the SAME colour conversion and blit() bodies as nuxel-wl-fb.c,
 * kept in sync manually for the A67 change.  It:
 *   1. verifies the fast 2x path is pixel-identical to a naive reference blit;
 *   2. times the A34 (4x-convert) algorithm and the A67 (row-replicate + NEON)
 *      algorithm over many iterations and reports p50/p95/p99/mean/min/max.
 *
 * Compile for the handset (aarch64) and run there for real CPU timing, or on
 * any host for correctness only.
 */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#if defined(__aarch64__)
#include <arm_neon.h>
#endif

#define SRC_W 720
#define SRC_H 1520
#define DST_W 1440
#define DST_H 3040

/* ---- colour conversion, copied verbatim from nuxel-wl-fb.c ---- */
static uint32_t *cv_lo, *cv_hi;
static uint32_t src_fmt = 1; /* WL_SHM_FORMAT_XRGB8888 */
static unsigned hw_r_off = 0, hw_g_off = 8, hw_b_off = 16;

static void color_build(uint32_t format) {
  (void)format;
  cv_lo = malloc(sizeof(uint32_t) * 65536);
  cv_hi = malloc(sizeof(uint32_t) * 65536);
  if (!cv_lo || !cv_hi) { free(cv_lo); free(cv_hi); cv_lo = cv_hi = NULL; return; }
  for (uint32_t x = 0; x < 65536; x++) {
    cv_lo[x] = ((x & 0xffu) << 16) | (x & 0xff00u) | 0xff000000u;
    cv_hi[x] = (x & 0xffu);
  }
}

static inline uint32_t color_convert(uint32_t v) {
  if (cv_lo && cv_hi) return cv_lo[v & 0xffffu] | cv_hi[v >> 16];
  uint32_t r = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, b = v & 0xffu;
  return (r << hw_r_off) | (g << hw_g_off) | (b << hw_b_off) | 0xff000000u;
}

/* ---- fb-like destination ---- */
struct fbinfo {
  uint8_t *map;
  uint32_t w, h, bpp, line;
};
static struct fbinfo fb;

static uint16_t *xmap;
static int xmap_w, xmap_sx;
static uint32_t *rowbuf;
static size_t rowbuf_n;

/* ---- A67 fast blit (identical to nuxel-wl-fb.c) ---- */
static void row_expand2(const uint32_t *s, int sw, int convert) {
  uint32_t *o = rowbuf;
  int x = 0;
#if defined(__aarch64__)
  if (convert) {
    for (; x + 4 <= sw; x += 4) {
      uint32x4_t v = vld1q_u32(s + x);
      uint32x4_t b = vandq_u32(v, vdupq_n_u32(0x000000ffu));
      uint32x4_t g = vandq_u32(v, vdupq_n_u32(0x0000ff00u));
      uint32x4_t r = vandq_u32(v, vdupq_n_u32(0x00ff0000u));
      uint32x4_t c = vorrq_u32(vorrq_u32(vshlq_n_u32(b, 16), g), vshrq_n_u32(r, 16));
      c = vorrq_u32(c, vdupq_n_u32(0xff000000u));
      uint32x4x2_t ex = vzipq_u32(c, c);
      vst1q_u32(o + x * 2, ex.val[0]);
      vst1q_u32(o + x * 2 + 4, ex.val[1]);
    }
  } else {
    for (; x + 4 <= sw; x += 4) {
      uint32x4_t v = vld1q_u32(s + x);
      uint32x4_t c = vorrq_u32(v, vdupq_n_u32(0xff000000u));
      uint32x4x2_t ex = vzipq_u32(c, c);
      vst1q_u32(o + x * 2, ex.val[0]);
      vst1q_u32(o + x * 2 + 4, ex.val[1]);
    }
  }
#endif
  for (; x < sw; x++) {
    uint32_t c = convert ? color_convert(s[x]) : (s[x] | 0xff000000u);
    o[x * 2] = c;
    o[x * 2 + 1] = c;
  }
}

static void blit_a67(const uint8_t *src, int sw, int sh, int stride, int convert) {
  int sx = (int)fb.w / sw, sy = (int)fb.h / sh;
  if (sx < 1) sx = 1;
  if (sy < 1) sy = 1;
  if (sx == 2 && sy == 2 && (int)(fb.h % 2) == 0) {
    if (!rowbuf || rowbuf_n < (size_t)fb.w) {
      free(rowbuf);
      rowbuf = malloc(sizeof(uint32_t) * (fb.w ? fb.w : 1));
      rowbuf_n = fb.w;
      if (!rowbuf) return;
    }
    for (uint32_t ty = 0; ty < fb.h; ty += 2) {
      int srcrow = (int)(ty / 2u);
      if (srcrow >= sh) srcrow = sh - 1;
      const uint32_t *s = (const uint32_t *)(src + (size_t)srcrow * stride);
      row_expand2(s, sw, convert);
      uint32_t *d0 = (uint32_t *)(fb.map + (size_t)ty * fb.line);
      uint32_t *d1 = (uint32_t *)(fb.map + (size_t)(ty + 1u) * fb.line);
      memcpy(d0, rowbuf, (size_t)fb.w * sizeof(uint32_t));
      memcpy(d1, rowbuf, (size_t)fb.w * sizeof(uint32_t));
    }
    return;
  }
  /* generic */
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)(y / (uint32_t)sy); if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    for (uint32_t x = 0; x < fb.w; x++) {
      int tx = (int)(x / (uint32_t)sx); if (tx >= sw) tx = sw - 1;
      d[x] = convert ? color_convert(s[tx]) : (s[tx] | 0xff000000u);
    }
  }
}

/* ---- A34 original algorithm (4x redundant conversions) ---- */
static void blit_a34(const uint8_t *src, int sw, int sh, int stride, int convert) {
  int sx = (int)fb.w / sw, sy = (int)fb.h / sh;
  if (sx < 1) sx = 1;
  if (sy < 1) sy = 1;
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)(y / (uint32_t)sy); if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    if (convert) {
      for (uint32_t x = 0; x < fb.w; x++) {
        int tx = (int)(x / (uint32_t)sx); if (tx >= sw) tx = sw - 1;
        d[x] = color_convert(s[tx]);
      }
    } else {
      for (uint32_t x = 0; x < fb.w; x++) {
        int tx = (int)(x / (uint32_t)sx); if (tx >= sw) tx = sw - 1;
        d[x] = s[tx] | 0xff000000u;
      }
    }
  }
}

/* naive reference (per-pixel, no lookup table) for correctness */
static void blit_ref(const uint8_t *src, int sw, int sh, int stride, int convert) {
  int sx = (int)fb.w / sw, sy = (int)fb.h / sh;
  if (sx < 1) sx = 1;
  if (sy < 1) sy = 1;
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)(y / (uint32_t)sy); if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    for (uint32_t x = 0; x < fb.w; x++) {
      int tx = (int)(x / (uint32_t)sx); if (tx >= sw) tx = sw - 1;
      uint32_t v = s[tx];
      if (convert) {
        uint32_t r = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, b = v & 0xffu;
        d[x] = (r << hw_r_off) | (g << hw_g_off) | (b << hw_b_off) | 0xff000000u;
      } else {
        d[x] = v | 0xff000000u;
      }
    }
  }
}

static int64_t now_ns(void) {
  struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static int cmp64(const void *a, const void *b) {
  int64_t x = *(const int64_t *)a, y = *(const int64_t *)b;
  return (x > y) - (x < y);
}

static void report(const char *name, int64_t *samples, int n) {
  qsort(samples, (size_t)n, sizeof(int64_t), cmp64);
  int64_t sum = 0;
  for (int i = 0; i < n; i++) sum += samples[i];
  double mean = (double)sum / n;
  printf("%-10s n=%d mean_ms=%.3f p50_ms=%.3f p95_ms=%.3f p99_ms=%.3f min_ms=%.3f max_ms=%.3f\n",
         name, n, mean/1e6, samples[n/2]/1e6, samples[n*95/100]/1e6,
         samples[n*99/100]/1e6, samples[0]/1e6, samples[n-1]/1e6);
}

int main(void) {
  color_build(src_fmt);
  if (!cv_lo || !cv_hi) { fprintf(stderr, "LUT alloc failed\n"); return 1; }

  fb.w = DST_W; fb.h = DST_H; fb.bpp = 32; fb.line = DST_W * 4;
  fb.map = malloc((size_t)fb.line * fb.h);
  if (!fb.map) { fprintf(stderr, "fb alloc failed\n"); return 1; }

  size_t src_len = (size_t)SRC_W * 4 * SRC_H;
  uint32_t *src = malloc(src_len);
  uint8_t *srcb = (uint8_t *)src;
  if (!src) { fprintf(stderr, "src alloc failed\n"); return 1; }

  /* deterministic pseudo-random source (LCG), fixed seed */
  uint32_t x = 0x12345678u;
  for (size_t i = 0; i < src_len / 4; i++) { x = x * 1103515245u + 12345u; src[i] = x & 0x00ffffffu; }

  /* --- correctness: A67 fast path == naive reference --- */
  uint8_t *gold = malloc((size_t)fb.line * fb.h);
  uint8_t *got  = malloc((size_t)fb.line * fb.h);
  if (!gold || !got) { fprintf(stderr, "cmp alloc failed\n"); return 1; }
  blit_ref(srcb, SRC_W, SRC_H, SRC_W*4, 1);
  memcpy(gold, fb.map, (size_t)fb.line * fb.h);
  memset(fb.map, 0, (size_t)fb.line * fb.h);
  blit_a67(srcb, SRC_W, SRC_H, SRC_W*4, 1);
  memcpy(got, fb.map, (size_t)fb.line * fb.h);
  int mismatch = memcmp(gold, got, (size_t)fb.line * fb.h) != 0;
  printf("CORRECTNESS a67_2x_vs_reference=%s bytes=%zu\n",
         mismatch ? "MISMATCH" : "PIXEL_IDENTICAL", (size_t)fb.line * fb.h);
  if (mismatch) {
    for (size_t i = 0; i < (size_t)fb.line * fb.h / 4; i++) {
      if (((uint32_t*)gold)[i] != ((uint32_t*)got)[i]) {
        printf("  first mismatch word=%zu gold=0x%08x got=0x%08x\n", i,
               ((uint32_t*)gold)[i], ((uint32_t*)got)[i]);
        break;
      }
    }
  }

  /* --- timing --- */
  int N = 40;
  int64_t *t_a34 = malloc(sizeof(int64_t) * (size_t)N);
  int64_t *t_a67 = malloc(sizeof(int64_t) * (size_t)N);
  if (!t_a34 || !t_a67) { fprintf(stderr, "timing alloc failed\n"); return 1; }

  /* warm-up both paths once */
  blit_a34(srcb, SRC_W, SRC_H, SRC_W*4, 1);
  blit_a67(srcb, SRC_W, SRC_H, SRC_W*4, 1);

  for (int i = 0; i < N; i++) {
    int64_t t0 = now_ns();
    blit_a34(srcb, SRC_W, SRC_H, SRC_W*4, 1);
    t_a34[i] = now_ns() - t0;
  }
  for (int i = 0; i < N; i++) {
    int64_t t0 = now_ns();
    blit_a67(srcb, SRC_W, SRC_H, SRC_W*4, 1);
    t_a67[i] = now_ns() - t0;
  }

  report("a34_old", t_a34, N);
  report("a67_new", t_a67, N);

  /* effective FPS ceiling estimate for a fully-changing 720x1520->1440x3040 frame */
  double mean_a34 = 0, mean_a67 = 0;
  for (int i = 0; i < N; i++) { mean_a34 += (double)t_a34[i]; mean_a67 += (double)t_a67[i]; }
  mean_a34 /= N; mean_a67 /= N;
  printf("EFFECTIVE_CEILING_FPS old=%.2f new=%.2f (blit-only, no screencopy/hash/pan)\n",
         1e9/mean_a34, 1e9/mean_a67);

  free(gold); free(got); free(t_a34); free(t_a67); free(src); free(fb.map);
  return mismatch ? 2 : 0;
}
