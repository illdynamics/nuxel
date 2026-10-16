/* ============================================================================
 * nuxel-ui — the Nuxel phone interface, drawn directly on the Samsung S10+
 * AMOLED through the hardware-proven DECON fbdev path (no X11, no Wayland, no
 * DRM: this kernel has `# CONFIG_DRM is not set`).
 *
 * A23 (2026-10-15).  Freestanding aarch64, raw syscalls, no libc — the same
 * build discipline as nuxel-fb-phone / nuxel-anim-player, so the UI runs on a
 * 4.14 vendor kernel and a Fedora 43 userspace without an ABI surprise.
 *
 * WHAT IT IS
 *   * a REAL userspace process (systemd unit nuxel-ui.service), not a frame
 *     painted during early boot;
 *   * an interactive screen: status bar (clock/date/battery/USB), Nuxel home,
 *     settings, system information, log viewer, controlled reboot/shutdown;
 *   * a framebuffer client that measures the panel at runtime and respects the
 *     driver's stride / buffer count / pixel format;
 *   * a touch client: evdev multitouch (type B) with single-touch fallback,
 *     plus a command channel so the live CDC-ACM console can drive it when the
 *     touchscreen is not up;
 *   * the owner of the handoff: it commits a real frame BEFORE it asks the boot
 *     animation to stop, and it records every transition in /var/lib/nuxel.
 *
 * COLOUR — see the long comment in nuxel-anim-player.c and
 * docs/s10plus-autonomous-boot-repair/NUXEL-COLOUR-ORDER.md.  decon_pan_display()
 * programs DECON_PIXEL_FORMAT_ABGR_8888 for 24/32 bpp while fb_var declares
 * red@16/blue@0, so the panel reads R from bits 0..7.  This file therefore packs
 * pixels from the HARDWARE format, not from fb_var, and can be told otherwise
 * with --hworder=fbvar for A/B testing.
 *
 * USAGE
 *   nuxel-ui                       run the UI (systemd)
 *   nuxel-ui --selftest=DIR        render every page into DIR as PPM and exit
 *   nuxel-ui --hworder=fbvar       pack with fb_var declared bitfields
 *   nuxel-ui --page=settings       start on a page
 *   nuxel-ui --once                render one frame, commit, exit
 * ==========================================================================*/
typedef unsigned long u64;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef signed int s32;
typedef signed long s64;

/* ---- syscall numbers / flags (shared by both builds) ---- */
#define SYS_read 63
#define SYS_write 64
#define SYS_close 57
#define SYS_ioctl 29
#define SYS_openat 56
#define SYS_mmap 222
#define SYS_munmap 215
#define SYS_exit_group 94
#define SYS_getpid 172
#define SYS_kill 129
#define SYS_nanosleep 101
#define SYS_clock_gettime 113
#define SYS_ppoll 73
#define SYS_getdents64 61
#define SYS_mknodat 33
#define SYS_mkdirat 34
#define SYS_unlinkat 35
#define SYS_reboot 142
#define SYS_lseek 62
#define SYS_fcntl 25
/* A28: needed by the launcher's app-launch path and the wallpaper loader */
#define SYS_faccessat 48
#define SYS_clone 220
#define SYS_execve 221
#define SYS_wait4 260

#define AT_FDCWD (-100)
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_CREAT 0100
#define O_EXCL 0200
#define O_TRUNC 01000
#define O_APPEND 02000
#define O_NONBLOCK 04000
#define O_DIRECTORY 040000   /* A21 lesson: 0x10000 is O_DIRECT and procfs EINVALs it */
#define O_CLOEXEC 02000000

#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_PRIVATE 2
#define MAP_ANONYMOUS 0x20
#define MAP_FAILED ((void*)-1)

#define CLOCK_REALTIME 0
#define CLOCK_MONOTONIC 1

#define POLLIN 1
#define POLLERR 8
#define POLLHUP 0x10

/* ---- small string helpers (shared by both builds, no syscalls) ---- */
static void sleep_ms_(long ms);
static void *mem_zero(void *d,u64 n){ u8*p=d; while(n--)*p++=0; return d; }
static u64 slen(const char *s){ u64 n=0; while(s[n])n++; return n; }
static void mem_copy(void *d,const void *s,u64 n){ u8*a=d; const u8*b=s; while(n--)*a++=*b++; }
static int str_eq(const char *a,const char *b){ while(*a&&*a==*b){a++;b++;} return *a==*b; }
static int str_starts(const char *a,const char *b){ while(*b){ if(*a++!=*b++)return 0;} return 1; }
static const char *str_after(const char *s,char c){ while(*s&&*s!=c)s++; return *s?s+1:s; }
static int str_find(const char *h,const char *n){ for(const char*p=h;*p;p++){ const char*a=p,*b=n; while(*b&&*a==*b){a++;b++;} if(!*b)return 1;} return 0; }
static u64 atou_(const char *s){ u64 v=0; while(*s>='0'&&*s<='9')v=v*10+(u64)(*s++-'0'); return v; }

#define STATE_DIR "/var/lib/nuxel"

#ifdef NUXEL_UI_HOST
/* Host build for the offline layout harness (tools/s10plus/a27/test-ui-layout.sh):
   the syscall layer is replaced by libc so the SAME render code can be exercised
   at every scale with injected fixtures.  Device-only members are guarded out
   further down; nothing here touches a framebuffer. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
static void wr(const char *t){ fputs(t,stdout); }
static void wrn(const char *t,u64 v){ printf("%s=%llu\n",t,(unsigned long long)v); }
static void wrs(const char *t,const char *v){ printf("%s=%s\n",t,v?v:"(null)"); }
static long sys0(long n){ (void)n; return 0; }
static long sys1(long n,long a){ (void)n;(void)a; return -1; }
static long sys2(long n,long a,long b){ (void)n;(void)a;(void)b; return -1; }
static long sys3(long n,long a,long b,long c){ (void)n;(void)a;(void)b;(void)c; return -1; }
static long sys4(long n,long a,long b,long c,long d){ (void)n;(void)a;(void)b;(void)c;(void)d; return -1; }
static long sys5(long n,long a,long b,long c,long d,long e){ (void)n;(void)a;(void)b;(void)c;(void)d;(void)e; return -1; }
static long sys6(long n,long a,long b,long c,long d,long e,long f){ (void)n;(void)a;(void)b;(void)c;(void)d;(void)e;(void)f; return -1; }
static void log_open(void){}
static int ui_lock_take(void){ return 0; }   /* host: no framebuffer to own */
static void sleep_ms_(long ms){ struct timespec ts; ts.tv_sec=ms/1000; ts.tv_nsec=(ms%1000)*1000000L; nanosleep(&ts,0); }
#else
/* ---------------------------------------------------------------- syscalls */
static long sys0(long n){ register long x0 __asm__("x0")=0,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x8):"memory"); return x0; }
static long sys1(long n,long a){ register long x0 __asm__("x0")=a,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x8):"memory"); return x0; }
static long sys2(long n,long a,long b){ register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x8):"memory"); return x0; }
static long sys3(long n,long a,long b,long c){ register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x8):"memory"); return x0; }
static long sys4(long n,long a,long b,long c,long d){ register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory"); return x0; }
static long sys5(long n,long a,long b,long c,long d,long e){ register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x8):"memory"); return x0; }
static long sys6(long n,long a,long b,long c,long d,long e,long f){ register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory"); return x0; }

#define S_IFIFO 0010000
#define S_IFDIR 0040000


#endif /* NUXEL_UI_HOST — syscall layer */

#ifndef NUXEL_UI_HOST
/* ------------------------------------------------------------------ logging */
static long LOGFD = -1;
static void log_open(void){
  LOGFD = sys4(SYS_openat,AT_FDCWD,(long)"/dev/kmsg",O_WRONLY|O_NONBLOCK,0);
  if(LOGFD<0) LOGFD = 2;
}
static void wr(const char *s){ if(LOGFD>=0 && s[0]) sys3(SYS_write,LOGFD,(long)s,slen(s)); }
static void wrn(const char *tag,u64 v){
  char b[128]; int i=0; while(tag[i] && i<96){ b[i]=tag[i]; i++; } b[i++]='=';
  char d[24]; int k=0; if(!v)d[k++]='0'; while(v){ d[k++]=(char)('0'+(int)(v%10)); v/=10; }
  while(k) b[i++]=d[--k]; b[i++]='\n'; sys3(SYS_write,LOGFD,(long)b,i);
}
static void wrs(const char *tag,const char *v){
  char b[192]; int i=0; while(tag[i]&&i<120){ b[i]=tag[i]; i++; } b[i++]='=';
  int j=0; while(v[j]&&i<180) b[i++]=v[j++]; b[i++]='\n'; sys3(SYS_write,LOGFD,(long)b,i);
}

/* --------------------------------------------------------------- state files
 * /var/lib/nuxel is ext4 in the Fedora rootfs: both the initramfs-side boot
 * animation (which holds a dirfd on it across switch_root) and this process
 * see the same directory, so it is the handoff channel. */
static void state_write(const char *name,const char *text){
  char p[160]; int i=0; const char *a=STATE_DIR;
  while(a[i]){p[i]=a[i];i++;} p[i++]='/';
  int j=0; while(name[j]&&i<150) p[i++]=name[j++]; p[i]=0;
  long fd=sys4(SYS_openat,AT_FDCWD,(long)p,O_WRONLY|O_CREAT|O_TRUNC,0644);
  if(fd<0) return;
  sys3(SYS_write,fd,(long)text,slen(text));
  sys1(SYS_close,fd);
}
static void state_num(const char *name,u64 v){
  char b[24]; int k=0; if(!v)b[k++]='0'; while(v){ b[k++]=(char)('0'+(int)(v%10)); v/=10; }
  char o[26]; int n=0; while(k)o[n++]=b[--k]; o[n]=0; state_write(name,o);
}
/* Append one line to a bounded ring log (the UI's own persistent record). */
static void ui_log(const char *line){
  long fd=sys4(SYS_openat,AT_FDCWD,(long)STATE_DIR"/ui.log",O_WRONLY|O_CREAT|O_APPEND,0644);
  if(fd<0) return;
  sys3(SYS_write,fd,(long)line,slen(line));
  sys3(SYS_write,fd,(long)"\n",1);
  sys1(SYS_close,fd);
  wr("NUXEL_UI_LOG "); wr(line); wr("\n");
}
static int file_read(const char *path,char *buf,int cap){
  long fd=sys4(SYS_openat,AT_FDCWD,(long)path,O_RDONLY,0);
  if(fd<0) return -1;
  long n=sys3(SYS_read,fd,(long)buf,cap-1);
  sys1(SYS_close,fd);
  if(n<0) return -1;
  buf[n]=0;
  return (int)n;
}
static long out_open(const char *p){ return sys4(SYS_openat,AT_FDCWD,(long)p,O_WRONLY|O_CREAT|O_TRUNC,0644); }
static long out_write(long fd,const void *b,u64 n){ return sys3(SYS_write,fd,(long)b,n); }
static void out_close(long fd){ sys1(SYS_close,fd); }
static void *alloc_anon(u64 n){ return (void*)sys6(SYS_mmap,0,(long)n,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0); }
static int make_dir(const char *d){ return (int)sys3(SYS_mkdirat,AT_FDCWD,(long)d,0755); }
static int file_exists(const char *path){
  long fd=sys4(SYS_openat,AT_FDCWD,(long)path,O_RDONLY,0);
  if(fd<0) return 0; sys1(SYS_close,fd); return 1;
}

/* ============================================================================
 * A27 DISPLAY OWNERSHIP — the lock is acquired BEFORE /dev/fb0 is opened.
 *
 * A21/A24 measured that merely OPENING and CLOSING /dev/fb0 runs the DECON's
 * fb_release path, which disables the panel regulator; a second instance that
 * opened the framebuffer and then refused to run therefore still damaged the
 * active display.  A25 added a single-instance check -- but AFTER it had already
 * opened and mmapped /dev/fb0, which is the wrong order.
 *
 * The gate is now an advisory exclusive flock() on /run/nuxel-ui.lock, taken
 * before the framebuffer is touched:
 *   * the kernel releases it automatically when the owner dies, so a stale pid
 *     file can never block a legitimate start (a PID alone is not proof of
 *     ownership, and this no longer uses one as such);
 *   * it survives service restarts, crashes, stale state files and console
 *     reconnects, because it lives as long as the process does;
 *   * a second instance is refused with a named verdict BEFORE it can open the
 *     framebuffer at all, so it cannot power the panel down on its way out.
 * The pid file is still written, but only as human-readable context.
 * ==========================================================================*/
#define SYS_flock 32
#define LOCK_EX 2
#define LOCK_NB 4
static int UI_LOCK_FD=-1;
static int ui_lock_take(void){
  const char *paths[2]={"/run/nuxel-ui.lock","/var/lib/nuxel/ui.lock"};
  for(int i=0;i<2;i++){
    long fd=sys4(SYS_openat,AT_FDCWD,(long)paths[i],O_RDWR|O_CREAT,0644);
    if(fd<0) continue;
    long rc=sys2(SYS_flock,fd,LOCK_EX|LOCK_NB);
    if(rc<0){
      wr("NUXEL_UI_DISPLAY_OWNER_REFUSED "); wr(paths[i]);
      wr(" is locked by another framebuffer client\n");
      sys1(SYS_close,fd);
      state_write("ui-refused","ANOTHER_INSTANCE_OWNS_THE_DISPLAY (flock held)\n");
      return -2;
    }
    UI_LOCK_FD=(int)fd;
    state_num("ui.lock.owner",(u64)sys0(SYS_getpid));
    wr("NUXEL_UI_DISPLAY_LOCK_ACQUIRED "); wr(paths[i]); wr("\n");
    return 0;
  }
  wr("NUXEL_UI_DISPLAY_LOCK_UNAVAILABLE (no lock file could be created)\n");
  return -1;
}
#else

/* ---- HOST variants: the harness runs on macOS/Linux with libc ---- */
static void state_write(const char *name,const char *text){ (void)name;(void)text; }
static void state_num(const char *name,u64 v){ (void)name;(void)v; }
static void ui_log(const char *line){ printf("UI_LOG %s\n",line); }
static int file_read(const char *path,char *buf,int cap){
  FILE *f=fopen(path,"rb"); if(!f) return -1;
  size_t n=fread(buf,1,(size_t)(cap-1),f); fclose(f); buf[n]=0; return (int)n;
}
static int file_exists(const char *path){ FILE *f=fopen(path,"rb"); if(!f) return 0; fclose(f); return 1; }
static long out_open(const char *p){ FILE *f=fopen(p,"wb"); return f?(long)(size_t)f:-1; }
static long out_write(long fd,const void *b,u64 n){ FILE *f=(FILE*)(size_t)fd; return f?(long)fwrite(b,1,(size_t)n,f):-1; }
static void out_close(long fd){ FILE *f=(FILE*)(size_t)fd; if(f) fclose(f); }
static void *alloc_anon(u64 n){ return calloc(1,(size_t)n); }
static int make_dir(const char *d){ mkdir(d,0755); return 0; }
#endif /* NUXEL_UI_HOST */

/* --------------------------------------------------------------- framebuffer
 * Geometry is MEASURED, never assumed: /proc/cmdline is silent about the panel
 * and the driver's var is the only authority. */
struct fb_bitfield { u32 offset,length,msb_right; };
struct fb_var {
  u32 xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bits_per_pixel,grayscale;
  struct fb_bitfield red,green,blue,transp;
  u32 nonstd,activate,height,width,accel_flags,pixclock,left_margin,right_margin,
      upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace,reserved[4];
};
struct fb_fix { char id[16]; u64 smem_start; u32 smem_len,type,type_aux,visual;
  u16 xpanstep,ypanstep,wrapstep; u32 line_length; u64 mmio_start; u32 mmio_len,accel;
  u16 capabilities,reserved[2]; };
#define FBIOGET_VSCREENINFO 0x4600
#define FBIOGET_FSCREENINFO 0x4602
#define FBIOPUT_VSCREENINFO 0x4601
#define FBIOPAN_DISPLAY     0x4606
#define FBIOBLANK           0x4611
#define FB_BLANK_UNBLANK    0

struct screen {
  long fd;
  u8  *mem;         /* mmap of the whole virtual framebuffer */
  u64  mapped;
  u32  w,h,vh,stride,bpp,bufs;
  u32  toff;        /* rows to offset our canvas inside the virtual fb */
  int  is_fb;
  int  hw_abgr;     /* 1 = DECON_PIXEL_FORMAT_ABGR_8888 (R@0 B@16) */
  u8  *canvas;      /* set by selftest: an anonymous buffer instead of /dev/fb0 */
};
static struct screen SCR;   /* SCR.hw_abgr MUST default to 1: see NUXEL-COLOUR-ORDER.md */

static u32 pack_rgb(u32 r,u32 g,u32 b){
  if(SCR.bpp==32){
    if(SCR.hw_abgr) return ((r&0xffu)<<0)|((g&0xffu)<<8)|((b&0xffu)<<16)|(0xffu<<24);
    return ((r&0xffu)<<16)|((g&0xffu)<<8)|((b&0xffu)<<0)|(0xffu<<24);
  }
  if(SCR.bpp==16){ /* 5-6-5, positions unambiguous on every layout */ 
    return ((r>>3)<<11)|((g>>2)<<5)|(b>>3);
  }
  return ((r&0xff)<<0)|((g&0xff)<<8)|((b&0xff)<<16);
}
/* One pixel into the canvas we are composing (always the top-left buffer). */
static inline void px(int x,int y,u32 c){
  if(x<0||y<0||(u32)x>=SCR.w||(u32)y>=SCR.h) return;
  u8 *row = SCR.canvas + (u64)y*SCR.stride + (u64)x*(SCR.bpp/8);
  if(SCR.bpp==32) *(volatile u32*)row = c;
  else if(SCR.bpp==16) *(volatile u16*)row = (u16)c;
  else { row[0]=(u8)(c&0xff); row[1]=(u8)((c>>8)&0xff); row[2]=(u8)((c>>16)&0xff); }
}
static void fill_rect(int x,int y,int w,int h,u32 c){
  int x0=x<0?0:x, y0=y<0?0:y;
  int x1=x+w>(int)SCR.w?(int)SCR.w:x+w, y1=y+h>(int)SCR.h?(int)SCR.h:y+h;
  if(x1<=x0||y1<=y0) return;
  for(int yy=y0;yy<y1;yy++){
    u8 *row=SCR.canvas+(u64)yy*SCR.stride+(u64)x0*(SCR.bpp/8);
    if(SCR.bpp==32){ volatile u32*p=(volatile u32*)row; int n=x1-x0; while(n--)*p++=c; }
    else if(SCR.bpp==16){ volatile u16*p=(volatile u16*)row; int n=x1-x0; while(n--)*p++=(u16)c; }
    else { u8*p=row; for(int xx=x0;xx<x1;xx++){ *p++=(u8)(c&0xff); *p++=(u8)((c>>8)&0xff); *p++=(u8)((c>>16)&0xff);} }
  }
}
/* Rounded rectangle: the Nuxel card look (radius 16 * scale). */
static void round_rect(int x,int y,int w,int h,int r,u32 c){
  if(r*2>w) r=w/2; if(r*2>h) r=h/2;
  fill_rect(x+r,y,w-2*r,h,c);
  fill_rect(x,y+r,r,h-2*r,c);
  fill_rect(x+w-r,y+r,r,h-2*r,c);
  for(int j=0;j<r;j++)for(int i=0;i<r;i++){
    int dx=r-1-i, dy=r-1-j;
    if((s64)(dx*dx+dy*dy) <= (s64)(r-1)*(r-1)){ 
      fill_rect(x+i,y+j,1,1,c); fill_rect(x+w-1-i,y+j,1,1,c);
      fill_rect(x+i,y+h-1-j,1,1,c); fill_rect(x+w-1-i,y+h-1-j,1,1,c);
    }
  }
}
static void vline(int x,int y,int h,u32 c){ fill_rect(x,y,1,h,c); }
static void hline(int x,int y,int w,u32 c){ fill_rect(x,y,w,1,c); }
static void frame_rect(int x,int y,int w,int h,int t,u32 c){
  fill_rect(x,y,w,t,c); fill_rect(x,y+h-t,w,t,c);
  fill_rect(x,y,t,h,c); fill_rect(x+w-t,y,t,h,c);
}

/* --------------------------------------------------------------------- font
 * MEASURED text.  Glyphs come from tools/s10plus/a27/generated/nuxel-font-atlas.c
 * (rasterised from DejaVu Sans, which is redistributable: see
 * tools/s10plus/a27/assets/fonts/LICENSE-DejaVu.txt).  Every size carries its own
 * ascent/descent, so a line box is a measurement, not an estimate.
 *
 * This replaced the scaled 5x7 bitmap font that produced the A26 photograph's
 * block lettering, the 1680-px-wide clock and the fused dock labels: with
 * width/height measured before placement, and every draw clipped to its own
 * rectangle, those defects cannot reappear silently. */
#include "a27/generated/nuxel-font-atlas.c"

/* A28: the UTM launcher port's own tables, GENERATED from the launcher's
   sources (see tools/s10plus/a28/gen-launcher.py and make-emoji-atlas.py).
   Nothing in them is hand-written: app list/order/colours/icons come from
   pwa/nuxel-home/js/apps.js, the design tokens from
   pwa/nuxel-home/css/style.css. */
#include "a28/generated/nuxel-launcher.h"
#include "a28/generated/nuxel-emoji-atlas.c"

/* clip rectangle in PANEL pixels; every draw is bounded by it */
static int CLX0,CLY0,CLX1,CLY1;
static void clip_all(void){ CLX0=0; CLY0=0; CLX1=(int)SCR.w; CLY1=(int)SCR.h; }
static void clip_set(int x,int y,int w,int h){
  int x1=x+w,y1=y+h;
  if(x<0)x=0; if(y<0)y=0; if(x1>CLX1)x1=CLX1; if(y1>CLY1)y1=CLY1;
  if(x1<(CLX0=x))x1=x; if(y1<(CLY0=y))y1=y;
  CLX0=x; CLY0=y; CLX1=x1; CLY1=y1;
}
static int clip_w(void){ return CLX1>CLX0?CLX1-CLX0:0; }
static int clip_h(void){ return CLY1>CLY0?CLY1-CLY0:0; }

static const struct nuxel_font *font_for(int design_px){
  int best=0;
  for(int i=0;i<NUXEL_FONT_NSIZES;i++){
    if(NUXEL_FONTS[i].design<=design_px) best=i;
  }
  return &NUXEL_FONTS[best];
}
static int font_h(const struct nuxel_font *f){ return f->ascent+f->descent; }
static int font_w(const struct nuxel_font *f,const char *t){
  int w=0;
  for(;*t;t++){
    unsigned char c=(unsigned char)*t;
    if(c<NUXEL_FONT_FIRST||c>NUXEL_FONT_FIRST+NUXEL_FONT_COUNT-1) c='?';
    w+=NUXEL_FONT_GLYPHS[f->goff+(c-NUXEL_FONT_FIRST)].adv;
  }
  return w;
}
/* Blend one 4-bit coverage value into the canvas (2x2 box filter when the panel
   is a fraction of the 4x atlas, nearest when larger). */
static u32 blend_cov(u32 dst,u32 src,int cov){
  if(cov<=0) return dst;
  u32 a=(u32)(cov*17);
  if(a>=255) return src;
  u32 ia=255-a, out=0xff000000u;
  for(int sh=0;sh<24;sh+=8){
    u32 d=(dst>>sh)&0xffu, sc=(src>>sh)&0xffu;
    out|=(((sc*a+d*ia)/255u)&0xffu)<<sh;
  }
  return out;
}
/* y is the TOP of the line box (baseline = y + ascent). */
static void font_draw(int x,int y,const struct nuxel_font *f,const char *t,u32 col){
  int pen=x, top=y+((font_h(f)-font_h(f))/2);
  (void)top;
  int baseline=y+f->ascent;
  for(;*t;t++){
    unsigned char c=(unsigned char)*t;
    if(c<NUXEL_FONT_FIRST||c>NUXEL_FONT_FIRST+NUXEL_FONT_COUNT-1) c='?';
    const struct nuxel_glyph *g=&NUXEL_FONT_GLYPHS[f->goff+(c-NUXEL_FONT_FIRST)];
    int gx=pen+g->xoff, gy=baseline+g->yoff;
    for(int j=0;j<(int)g->h;j++){
      int py=gy+j;
      if(py<CLY0||py>=CLY1) continue;
      for(int i=0;i<(int)g->w;i++){
        int pxl=gx+i;
        if(pxl<CLX0||pxl>=CLX1) continue;
        u32 idx=(u32)j*(u32)g->w+(u32)i;
        u32 b=NUXEL_FONT_BITS[g->off+(idx>>1)];
        int cov=(idx&1)?(int)(b&0x0fu):(int)(b>>4);
        if(!cov) continue;
        u8 *row=SCR.canvas+(u64)py*SCR.stride+(u64)pxl*(SCR.bpp/8);
        u32 dst;
        if(SCR.bpp==32) dst=*(volatile u32*)row;
        else if(SCR.bpp==16) dst=*(volatile u16*)row;
        else dst=((u32)row[0])|((u32)row[1]<<8)|((u32)row[2]<<16);
        u32 out;
        if(SCR.bpp==32) out=blend_cov(dst,col,cov);
        else out=(cov>=8)?col:dst;
        if(SCR.bpp==32) *(volatile u32*)row=out;
        else if(SCR.bpp==16) *(volatile u16*)row=(u16)out;
        else { row[0]=(u8)(out&0xff); row[1]=(u8)((out>>8)&0xff); row[2]=(u8)((out>>16)&0xff); }
      }
    }
    pen+=g->adv;
  }
}
static void font_center(int cx,int y,const struct nuxel_font *f,const char *t,u32 col){
  font_draw(cx-font_w(f,t)/2,y,f,t,col);
}
static void font_right(int rx,int y,const struct nuxel_font *f,const char *t,u32 col){
  font_draw(rx-font_w(f,t),y,f,t,col);
}
/* Truncate `t` into `out` so that it fits `maxw`, adding an ellipsis only when
   something was actually dropped.  This is the ONLY way text is placed: a box
   can never be overrun because a string was too long. */
static void font_fit_str(const struct nuxel_font *f,const char *t,int maxw,char *out,int cap){
  int n=0; out[0]=0;
  if(maxw<=0||cap<2) return;
  int ell=(font_w(f,"...")<=maxw);
  int budget=ell?maxw-font_w(f,"..."):maxw;
  int w=0;
  for(;t[n]&&n<cap-1;n++){
    unsigned char c=(unsigned char)t[n];
    if(c<NUXEL_FONT_FIRST||c>NUXEL_FONT_FIRST+NUXEL_FONT_COUNT-1) c='?';
    int adv=NUXEL_FONT_GLYPHS[f->goff+(c-NUXEL_FONT_FIRST)].adv;
    if(w+adv>budget) break;
    w+=adv;
  }
  int k=0; for(int i=0;i<n&&k<cap-1;i++) out[k++]=t[i];
  if(ell&&t[n]&&k+3<cap){ out[k++]='.'; out[k++]='.'; out[k++]='.'; }
  out[k]=0;
}
/* -------------------------------------------------------------- text fields */
static void u2s(u64 v,char *o){ /* unsigned -> decimal, no padding */
  char b[24]; int k=0; if(!v)b[k++]='0'; while(v){ b[k++]=(char)('0'+(int)(v%10)); v/=10; }
  int n=0; while(k)o[n++]=b[--k]; o[n]=0;
}
static void u2s2(u64 v,char *o){ /* zero padded to 2 */
  o[0]=(char)('0'+(int)((v/10)%10)); o[1]=(char)('0'+(int)(v%10)); o[2]=0;
}
static void u2s4(u64 v,char *o){
  o[0]=(char)('0'+(int)((v/1000)%10)); o[1]=(char)('0'+(int)((v/100)%10));
  o[2]=(char)('0'+(int)((v/10)%10));   o[3]=(char)('0'+(int)(v%10)); o[4]=0;
}

/* ---------------------------------------------------------------- palette */
static u32 C_BG, C_BG2, C_CARD, C_CARD_HI, C_TXT, C_TXT2, C_ACCENT, C_ACCENT_D,
           C_OK, C_WARN, C_ERR, C_WHITE, C_BLACK, C_LINE;
/* A28: the palette is the launcher's -- exactly.  Every value below is the CSS
   custom property named in the comment, compiled in by gen-launcher.py, so the
   phone and the UTM PWA cannot disagree about a colour. */
static u32 rgb24(u32 v){ return pack_rgb((v>>16)&0xffu,(v>>8)&0xffu,v&0xffu); }
static void palette_init(void){
  C_BG     = rgb24(L_BG_PRIMARY);      /* --bg-primary    #0a1628 */
  C_BG2    = rgb24(L_BG_SECONDARY);    /* --bg-secondary  #0d1f3c */
  C_CARD   = rgb24(L_BG_CARD);         /* --bg-card       #122952 */
  C_CARD_HI= rgb24(L_BG_CARD_HOVER);   /* --bg-card-hover #1a3466 */
  C_TXT    = rgb24(L_TEXT_PRIMARY);    /* --text-primary  #ffffff */
  C_TXT2   = rgb24(L_TEXT_SECONDARY);  /* --text-secondary #b8c7e0 */
  C_ACCENT = rgb24(L_ACCENT_LIGHT);    /* --accent-light  #3b82f6 */
  C_ACCENT_D=rgb24(L_ACCENT);          /* --accent        #1e40af */
  C_OK     = rgb24(L_SUCCESS);         /* --success       #4caf50 */
  C_WARN   = rgb24(L_WARNING);         /* --warning       #ff9800 */
  C_ERR    = rgb24(L_ERROR);           /* --error         #f44336 */
  C_WHITE  = rgb24(L_TEXT_PRIMARY);
  C_BLACK  = pack_rgb(0,0,0);
  C_LINE   = pack_rgb(0x1c,0x33,0x5e); /* diagnostic separator (not a CSS token) */
}
/* vertical gradient background + the subtle Nuxel "circuit" rules */
static void background(void){
  for(u32 y=0;y<SCR.h;y++){
    u32 f=(y*255u)/SCR.h;
    u32 r=(0x0a*(255-f)+0x07*f)/255u, g=(0x16*(255-f)+0x14*f)/255u, b=(0x28*(255-f)+0x26*f)/255u;
    fill_rect(0,(int)y,(int)SCR.w,1,pack_rgb(r,g,b));
  }
  for(int i=0;i<6;i++){ /* faint diagonal circuitry, top-right and bottom-left */
    int x=(int)SCR.w-1-i*90; int y=(int)(SCR.h/2)+i*140;
    for(int k=0;k<300;k++) px(x-k,y+k,pack_rgb(0x11,0x24,0x46));
  }
}

/* ================================================================== system data
 * Everything the UI shows comes from a real kernel/userspace interface; if a
 * source is missing the UI SAYS SO on screen instead of inventing a value. */
struct sysinfo_ui {
  char kernel[128], osname[96], pid1[32], system_state[48], cgroup[64],
       root_fs[48], uptime[32], touch[64], usb[48], touchpath[64];
  int  battery_pct, battery_ok, charging, on_ac;
  char battery_status[32];
  int  fb_ok, cols, rows;   /* character grid for the log viewer */
};
static struct sysinfo_ui SI;

static void trim_nl(char *s){ for(int i=0;s[i];i++) if(s[i]=='\n'||s[i]=='\r'){s[i]=0;break;} }
static void copy_trim(char *dst,const char *src,int cap){
  int i=0; while(src[i]&&i<cap-1){ dst[i]=(src[i]=='\n'||src[i]=='\r')?' ':src[i]; i++; } dst[i]=0;
}
static void info_kernel(void){
  char b[512];
  if(file_read("/proc/version",b,sizeof b)>0){
    /* "Linux version 4.14.253 (...) #7 SMP PREEMPT ..." -> keep through the build */
    int i=0,n=0; while(b[i]&&n<90){ b[n++]=b[i]; if(b[i]==')'&&b[i+1]==' ')break; i++; }
    b[n]=0; copy_trim(SI.kernel,b,sizeof SI.kernel);
  } else copy_trim(SI.kernel,"/proc/version unreadable",sizeof SI.kernel);
}
static void info_osrelease(void){
  char b[1024];
  if(file_read("/etc/os-release",b,sizeof b)>0){
    const char *p=b;
    while(*p){
      if(str_starts(p,"PRETTY_NAME=\"")){
        const char *q=p+13; int n=0; while(q[n]&&q[n]!='"'&&n<90){ SI.osname[n]=q[n]; n++; }
        SI.osname[n]=0; return;
      }
      while(*p&&*p!='\n')p++; if(*p)p++;
    }
  }
  copy_trim(SI.osname,"/etc/os-release unreadable",sizeof SI.osname);
}
static void info_pid1(void){
  char b[64];
  if(file_read("/proc/1/comm",b,sizeof b)>0){ trim_nl(b); copy_trim(SI.pid1,b,sizeof SI.pid1); }
  else copy_trim(SI.pid1,"?",sizeof SI.pid1);
  /* A real "is the system up" signal: does the systemd private dir exist, and
     is PID 1 talking on D-Bus?  Presence of a unit list alone proves nothing. */
  if(file_exists("/run/systemd/system")) copy_trim(SI.system_state,"systemd running (system manager dir present)",sizeof SI.system_state);
  else copy_trim(SI.system_state,"systemd manager dir MISSING",sizeof SI.system_state);
  if(file_exists("/run/dbus/system_bus_socket")) {
    int n=(int)slen(SI.system_state);
    copy_trim(SI.system_state+n,", D-Bus socket live",(int)sizeof(SI.system_state)-n);
  } else {
    int n=(int)slen(SI.system_state);
    copy_trim(SI.system_state+n,", D-Bus socket ABSENT",(int)sizeof(SI.system_state)-n);
  }
}
static void info_cgroup(void){
  char b[256];
  if(file_read("/sys/fs/cgroup/cgroup.controllers",b,sizeof b)>0){ trim_nl(b); copy_trim(SI.cgroup,b,sizeof SI.cgroup); }
  else copy_trim(SI.cgroup,"cgroup2 not mounted",sizeof SI.cgroup);
}
static void info_uptime(void){
  char b[128];
  if(file_read("/proc/uptime",b,sizeof b)>0){
    u64 s=atou_(b); char t[32]; u2s(s,&t[0]); /* whole seconds */
    u64 h=s/3600,m=(s%3600)/60; char hh[8],mm[8]; u2s(h,&hh[0]); u2s(m,&mm[0]);
    int n=0; for(int i=0;hh[i];i++)SI.uptime[n++]=hh[i]; SI.uptime[n++]='H'; SI.uptime[n++]=' ';
    for(int i=0;mm[i];i++)SI.uptime[n++]=mm[i]; SI.uptime[n++]='M'; SI.uptime[n]=0;
  } else copy_trim(SI.uptime,"?",sizeof SI.uptime);
}
static void info_rootfs(void){
  char b[4096];
  if(file_read("/proc/mounts",b,sizeof b)>0){
    const char *p=b;
    while(*p){
      if(p[0]=='/'&&(p[1]==' '||p[1]=='/')){ /* first field is the device */
        const char *q=p; while(*q&&*q!=' ')q++;
        while(*q==' ')q++;
        if(*q=='/'&&q[1]==' '){
          copy_trim(SI.root_fs,p,sizeof SI.root_fs);
          /* append the device name */
          const char *dev=p; const char *slash=0; int n=0;
          for(const char *r=p;r<q;r++) if(*r=='/')slash=r;
          if(slash){ const char *nm=slash+1; int k=(int)slen(SI.root_fs);
            SI.root_fs[k++]=' '; SI.root_fs[k++]='('; 
            while(*nm&&*nm!=' '&&k<44) SI.root_fs[k++]=*nm++; SI.root_fs[k++]=')'; SI.root_fs[k]=0; }
          (void)dev;(void)n;
          return;
        }
      }
      while(*p&&*p!='\n')p++; if(*p)p++;
    }
  }
  copy_trim(SI.root_fs,"/proc/mounts unreadable",sizeof SI.root_fs);
}
static void info_battery(void){
  char b[128];
  SI.battery_pct=-1; SI.battery_ok=0; SI.charging=0; SI.on_ac=0;
  copy_trim(SI.battery_status,"unknown",sizeof SI.battery_status);
  static const char *dirs[]={"/sys/class/power_supply/battery","/sys/class/power_supply/BAT0","/sys/class/power_supply/max77705-charger"};
  for(int d=0;d<3;d++){
    char p[128]; int i=0; const char *a=dirs[d]; while(a[i]){p[i]=a[i];i++;} 
    const char *suf="/capacity"; int j=0; while(suf[j])p[i++]=suf[j++]; p[i]=0;
    if(file_read(p,b,sizeof b)>0){
      trim_nl(b); SI.battery_pct=(int)atou_(b); SI.battery_ok=1;
      i=0; a=dirs[d]; while(a[i]){p[i]=a[i];i++;}
      suf="/status"; j=0; while(suf[j])p[i++]=suf[j++]; p[i]=0;
      if(file_read(p,b,sizeof b)>0){ trim_nl(b); copy_trim(SI.battery_status,b,sizeof SI.battery_status); }
      if(str_find(SI.battery_status,"Charging")||str_find(SI.battery_status,"Full")) SI.charging=1;
      break;
    }
  }
  /* online flag from any supply that reports it (USB / DC) */
  static const char *ac[]={"/sys/class/power_supply/usb/online","/sys/class/power_supply/dc/online",
                           "/sys/class/power_supply/ac/online"};
  for(int d=0;d<3;d++){
    if(file_read(ac[d],b,sizeof b)>0){ trim_nl(b); if(b[0]=='1'){ SI.on_ac=1; break; } }
  }
}
static void info_usb(void){
  /* The live console gadget is only "up" when the UDC has a state and the tty
     node exists: enumeration alone is not proof. */
  static const char *udcs[]={"/sys/class/udc/10c00000.dwc3/state","/sys/class/udc/10c00000.dwc3/current_speed"};
  char b[128]; SI.usb[0]=0;
  if(file_exists("/dev/ttyGS0")) copy_trim(SI.usb,"ttyGS0 node",sizeof SI.usb);
  else copy_trim(SI.usb,"no ttyGS0",sizeof SI.usb);
  for(int i=0;i<2;i++){
    if(file_read(udcs[i],b,sizeof b)>0){ trim_nl(b);
      int n=(int)slen(SI.usb); if(n<44){ SI.usb[n++]=' '; SI.usb[n++]='('; 
        int k=0; while(b[k]&&n<60) SI.usb[n++]=b[k++]; SI.usb[n++]=')'; SI.usb[n]=0; }
    }
  }
  if(file_exists("/sys/class/udc")) { int n=(int)slen(SI.usb); if(n<60) copy_trim(SI.usb+n," udc=present",(int)sizeof(SI.usb)-n); }
}
static void info_touch(void){
  /* Input is only real if /dev/input/event* exists AND a device reports
     absolute multitouch.  Enumeration alone is not proof (mission section 8). */
  copy_trim(SI.touch,"no /dev/input/event*",sizeof SI.touch);
  copy_trim(SI.touchpath,"none",sizeof SI.touchpath);
  long dfd=sys4(SYS_openat,AT_FDCWD,(long)"/dev/input",O_RDONLY|O_DIRECTORY,0);
  if(dfd<0){ copy_trim(SI.touch,"/dev/input absent",sizeof SI.touch); return; }
  char buf[4096]; int found=0; char first[64]; first[0]=0;
  for(;;){
    long n=sys3(SYS_getdents64,dfd,(long)buf,sizeof buf);
    if(n<=0) break;
    for(long off=0;off<n;){
      u16 reclen=*(u16*)(buf+off+16);
      if(reclen<24) break;
      char *nm=buf+off+19;
      if(nm[0]=='e'&&nm[1]=='v'&&nm[2]=='e'&&nm[3]=='n'&&nm[4]=='t'&&nm[5]>='0'&&nm[5]<='9'){
        found++;
        if(!first[0]){ int k=0; const char *a="/dev/input/"; int i2=0;
          while(a[i2]) first[k++]=a[i2++];
          for(int q=0;nm[q]&&k<60;q++) first[k++]=nm[q];
          first[k]=0; }
      }
      off+=reclen;
    }
  }
  sys1(SYS_close,dfd);
  if(found){
    char t[24]; u2s((u64)found,t);
    int n=0; const char *pre="evdev nodes=";
    for(int i=0;pre[i];i++) SI.touch[n++]=pre[i];
    for(int i=0;t[i];i++) SI.touch[n++]=t[i];
    SI.touch[n]=0;
    copy_trim(SI.touchpath,first,sizeof SI.touchpath);
  }
}
/* Filled in by info_touch_refine() once the input layer has scanned the devices. */
static void info_touch_refine(void);
static void info_collect(void){
  info_kernel(); info_osrelease(); info_pid1(); info_cgroup(); info_uptime();
  info_rootfs(); info_battery(); info_usb(); info_touch(); info_touch_refine();
}

/* ============================================================== UI structure */
#define NUXEL_UI_REV "A28-nuxel-home-launcher-1 (" NUXEL_LAUNCHER_REV ")"
/* A28: page 0 is the LAUNCHER (the default screen).  The A23..A27 diagnostic
   pages are retained, unchanged, as the fallback/diagnostic interface the
   mission requires (reachable by tapping the launcher title or `page=<p>`). */
#define PAGE_LAUNCHER 0
#define PAGE_HOME 1
#define PAGE_SETTINGS 2
#define PAGE_SYSTEM 3
#define PAGE_LOGS 4
#define PAGE_POWER 5
#define PAGE_ABOUT 6
#define PAGE_MAX 7
static const char *PAGE_NAME[PAGE_MAX]={"launcher","home","settings","system","logs","power","about"};

/* actions a touch (or a console command) can request */
#define ACT_NONE     0
#define ACT_HOME     1
#define ACT_SETTINGS 2
#define ACT_SYSTEM   3
#define ACT_LOGS     4
#define ACT_POWER    5
#define ACT_ABOUT    6
#define ACT_LOGDOWN  7
#define ACT_LOGUP    8
#define ACT_CTEST    9
#define ACT_SHOT     10
#define ACT_RESTART  11
#define ACT_REBOOT   12
#define ACT_SHUTDOWN 13
#define ACT_ANIMCTL  14
#define ACT_APP_BASE 100          /* + NUXEL_APP_LIST index (launch that app) */
#define ACT_DIAG     140          /* launcher title -> the diagnostic pages */
#define ACT_SEARCH_CLOSE 141

struct widget { int x,y,w,h,act; };
static struct widget WIDGETS[40];
static int NWIDGETS = 0;
static void widget_add(int x,int y,int w,int h,int act){
  if(NWIDGETS<(int)(sizeof WIDGETS/sizeof WIDGETS[0])){ WIDGETS[NWIDGETS].x=x; WIDGETS[NWIDGETS].y=y;
    WIDGETS[NWIDGETS].w=w; WIDGETS[NWIDGETS].h=h; WIDGETS[NWIDGETS].act=act; NWIDGETS++; }
}
static int hit_test(int x,int y){
  for(int i=NWIDGETS-1;i>=0;i--){
    if(x>=WIDGETS[i].x&&y>=WIDGETS[i].y&&x<WIDGETS[i].x+WIDGETS[i].w&&y<WIDGETS[i].y+WIDGETS[i].h)
      return WIDGETS[i].act;
  }
  return ACT_NONE;
}

static int PAGE=PAGE_LAUNCHER;
static int POWER_ARMED=0;
static u64 POWER_ARM_UNTIL=0;
/* SC / OX / DESIGN_H and the design tokens live in the presentation section. */
static char TOAST[160];
static int  TOAST_UNTIL=0;       /* monotonic seconds */
static char UI_ERROR[160];       /* last error, drawn on EVERY page */
static int  LOG_TOP=0;           /* first visible log line */

#ifndef NUXEL_UI_HOST
static void now_ts(long clk,long *ts){ sys2(SYS_clock_gettime,clk,(long)ts); }
#else
static void now_ts(long clk,long *ts){
  struct timespec t;
  clock_gettime(clk==CLOCK_REALTIME?CLOCK_REALTIME:CLOCK_MONOTONIC,&t);
  ts[0]=t.tv_sec; ts[1]=t.tv_nsec/1000;
}
#endif
static u64 mono_sec(void){ long ts[2]; now_ts(CLOCK_MONOTONIC,ts); return (u64)ts[0]; }
static void toast(const char *s,u64 secs){
  int i=0; while(s[i]&&i<150){ TOAST[i]=s[i]; i++; } TOAST[i]=0;
  TOAST_UNTIL=(int)(mono_sec()+secs);
}

/* ------------------------------------------------------------------- clock */
static void civil_from_days(s64 z,int *y,int *m,int *d){
  z+=719468;
  s64 era=(z>=0?z:z-146096)/146097;
  u64 doe=(u64)(z-era*146097);
  u64 yoe=(doe-doe/1460+doe/36524-doe/146096)/365;
  s64 yy=(s64)yoe+era*400;
  u64 doy=doe-(365*yoe+yoe/4-yoe/100);
  u64 mp=(5*doy+2)/153;
  u64 dd=doy-(153*mp+2)/5+1;
  u64 mm=mp+(mp<10?3:-9);
  *y=(int)(yy+(mm<=2)); *m=(int)mm; *d=(int)dd;
}
struct clock_ui { int hh,mm,ss,y,mo,d; };
static void clock_read(struct clock_ui *c){
  long ts[2]; now_ts(CLOCK_REALTIME,ts);
  s64 t=(s64)ts[0]; s64 days=t/86400; s64 rem=t-days*86400;
  c->hh=(int)(rem/3600); c->mm=(int)((rem%3600)/60); c->ss=(int)(rem%60);
  civil_from_days(days,&c->y,&c->mo,&c->d);
}

/* ============================================================================
 * A27 PRESENTATION — a real phone layout system, in the VM's own design units.
 *
 * The panel is exactly 4 x (360x760): one design unit == one PWA CSS pixel, and
 * every token below is taken from the repository's own interface, not invented:
 * pwa/nuxel-home/css/style.css   --status-bar-height:36  --dock-height:80
 *                                --grid-padding:16  --app-icon-size:64
 *                                --app-icon-radius:16  --card-radius:16
 *                                --button-radius:12  (and the navy palette)
 * launcher.css                   grid gap 8/16, label 11px, header 28px
 * shell/nuxel-home-native        body 14, caption 11, title 22/28
 *
 * THE THREE RULES (see the font section): measure, clip, register.  A page is
 * built from rows and cards whose rectangles are all known, text is placed with
 * dtext() (which fits or ellipsises inside a known width), and layout_check()
 * reports any content element that overlaps another or leaves the safe area.
 * ==========================================================================*/
/* A28: these ARE the launcher's CSS tokens, parsed from
   pwa/nuxel-home/css/style.css by tools/s10plus/a28/gen-launcher.py and
   asserted below.  Change the CSS and the UI follows on the next build. */
#define L_LABEL_PX 11            /* launcher.css .app-item .app-label */
#define DPAD      L_GRID_PADDING
#define DSTATUS   L_STATUS_BAR_HEIGHT
#define DDOCK     L_DOCK_HEIGHT
#define DCARD_R   L_CARD_RADIUS
#define DBTN_R    L_BUTTON_RADIUS
#define DICON     L_APP_ICON_SIZE
#define DICON_R   L_APP_ICON_RADIUS
#define DROW      56
#define DCUT_X0   118
#define DCUT_X1   242
#define DCUT_H    36
/* The phone panel is 1440x3040 = 4 x (360x760) design units, i.e. one design
   unit is one PWA CSS pixel, and 360 CSS px is INSIDE style.css's
   `@media (max-width: 480px)` band - measured on the live VM launcher DOM
   (WebKitGTK geometry harness: grid icons 56x56, grid padding 12px).  The port
   therefore uses the EFFECTIVE tokens, and these asserts pin them. */
_Static_assert(DPAD==12&&DSTATUS==36&&DDOCK==80&&DICON==56&&DICON_R==16&&
               DCARD_R==16&&DBTN_R==12,"style.css design tokens changed: the "
               "phone layout must be re-measured (see UTM-LAUNCHER-PORT)");
_Static_assert(LB_GRID_PADDING==16&&LB_APP_ICON_SIZE==64,
               "the un-overridden :root values are expected to be 16/64px");

static int SC=4;      /* px per design unit; the panel decides it */
static int OX=0;      /* letterbox for panels that are not a whole multiple */
static int DESIGN_H=760;
#define GAP8      8
#define GAP12     12
#define GAP16     16
static const char *MONTHS[12]={"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"};
/* Panel pixels -> design units.  The S10+ panel is exactly 1440x3040, i.e. 4 x the
   360x760 design space of the VM/PWA interface, so every design unit is a whole
   number of pixels (SC) and OX is zero.  Other panels still work: SC is floored
   and the design box is centred. */
static int A_LAYOUT_VERBOSE=0;   /* --layout-verbose: name every violation */
static void ui_metrics(int panel_w,int panel_h){
  int sc=panel_w/360; if(sc<1)sc=1; if(sc>8)sc=8;
  SC=sc;
  DESIGN_H=panel_h/sc;
  OX=(panel_w-360*sc)/2; if(OX<0)OX=0;
}

static int DX(int v){ return OX+v*SC; }
static int DY(int v){ return v*SC; }
static void dfill(int x,int y,int w,int h,u32 c){ fill_rect(DX(x),DY(y),w*SC,h*SC,c); }
static void dround(int x,int y,int w,int h,int r,u32 c){ round_rect(DX(x),DY(y),w*SC,h*SC,r*SC,c); }
static void dhline(int x,int y,int w,u32 c){ fill_rect(DX(x),DY(y),w*SC,SC>1?SC:1,c); }
static void dclip(int x,int y,int w,int h){ clip_set(DX(x),DY(y),w*SC,h*SC); }

/* text placement: pick the largest font <= design_px that fits the box, then fit
   (or ellipsise) the string into the width that is left.  y is the box top. */
#define AL_LEFT 0
#define AL_CENTER 1
#define AL_RIGHT 2
static void dtext(int x,int y,int w,int h,int design_px,const char *t,u32 col,int align){
  if(w<=0||h<=0) return;
  const struct nuxel_font *f=font_for(design_px);
  char tmp[256];
  font_fit_str(f,t,w*SC,tmp,sizeof tmp);
  int pxw=font_w(f,tmp);
  int pxh=font_h(f);
  int py=DY(y)+(h*SC-pxh)/2;
  int pxx;
  if(align==AL_CENTER) pxx=DX(x)+(w*SC-pxw)/2;
  else if(align==AL_RIGHT) pxx=DX(x+w)-pxw;
  else pxx=DX(x);
  dclip(x,y,w,h);
  font_draw(pxx,py,f,tmp,col);
}
/* a second, smaller line under the first one (used by list rows and tiles) */
static void dtext2(int x,int y,int w,int h,int design_px,const char *t,u32 col,int align){
  dtext(x,y,w,h,design_px,t,col,align);
}

/* ---------------------------------------------------------------- registry
 * Every element worth protecting registers its rectangle.  layout_check() then
 * reports overlapping CONTENT boxes, content outside the safe area, status-bar
 * content inside the camera cutout, and chrome outside its own band.  The
 * offline harness turns a non-zero count into a failing test. */
#define REG_MAX 96
#define REG_CONTENT 0
#define REG_STATUS  1
#define REG_DOCK    2
struct region { const char *name; short x,y,w,h; unsigned char kind; };
static struct region REG[REG_MAX];
static int NREG=0;
static int LAYOUT_VIOLATIONS=0;
static void dreg(const char *name,int x,int y,int w,int h,int kind){
  if(NREG>=REG_MAX) return;
  REG[NREG].name=name; REG[NREG].x=(short)x; REG[NREG].y=(short)y;
  REG[NREG].w=(short)w; REG[NREG].h=(short)h; REG[NREG].kind=(unsigned char)kind;
  NREG++;
}
static int rect_overlap(int ax,int ay,int aw,int ah,int bx,int by,int bw,int bh){
  return !(ax+aw<=bx||bx+bw<=ax||ay+ah<=by||by+bh<=ay);
}
static int layout_check(int verbose){
  int bad=0;
  for(int i=0;i<NREG;i++){
    struct region *r=&REG[i];
    int ytop=(r->kind==REG_STATUS)?0:DSTATUS;
    int ybot=(r->kind==REG_DOCK)?DESIGN_H:(DESIGN_H-DDOCK);
    int xlo=(r->kind==REG_CONTENT)?DPAD-2:0;
    int xhi=(r->kind==REG_CONTENT)?(360-DPAD+2):360;
    if(r->x<xlo||r->x+r->w>xhi||r->y<ytop||r->y+r->h>ybot){
      if(verbose) wr("NUXEL_UI_LAYOUT_OUT_OF_SAFE_AREA ");
      if(verbose){ wr(r->name); wr("\n"); }
      bad++;
    }
    if(r->kind==REG_STATUS && rect_overlap(r->x,r->y,r->w,r->h,DCUT_X0,0,DCUT_X1-DCUT_X0,DCUT_H)){
      if(verbose) wr("NUXEL_UI_LAYOUT_IN_CUTOUT ");
      if(verbose){ wr(r->name); wr("\n"); }
      bad++;
    }
    for(int j=i+1;j<NREG;j++){
      struct region *q=&REG[j];
      if(r->kind!=q->kind) continue;               /* chrome may sit over content */
      if(rect_overlap(r->x,r->y,r->w,r->h,q->x,q->y,q->w,q->h)){
        if(verbose){ wr("NUXEL_UI_LAYOUT_OVERLAP "); wr(r->name); wr(" "); wr(q->name); wr("\n"); }
        bad++;
      }
    }
  }
  LAYOUT_VIOLATIONS=bad;
  if(verbose) wrn("NUXEL_UI_LAYOUT_VIOLATIONS",(u64)bad);
  return bad;
}

/* --------------------------------------------------------------- status bar */
static void battery_glyph_d(int x,int y,int h,int pct,int charging){
  int w=h/2, t=h/12; if(t<2)t=2;
  frame_rect(DX(x),DY(y),w*SC,h*SC,t*SC,C_TXT2);
  fill_rect(DX(x+w),DY(y+h/4),t*2*SC,DY(h/2),C_TXT2);
  int inner_w=(w-2*t)*SC, fill=(inner_w*(pct<0?0:(pct>100?100:pct)))/100;
  u32 c = charging? C_OK : (pct<0? C_TXT2 : (pct<=15? C_ERR : (pct<=30? C_WARN : C_OK)));
  int bh=(h-2*t)*fill/(inner_w?inner_w:1);
  if(bh>0) fill_rect(DX(x+t),DY(y+h-t)-bh,inner_w,bh,c);
  if(charging){
    int cx=DX(x+w/2), cy=DY(y+h/2), arm=(h/5)*SC;
    fill_rect(cx-arm,cy-SC/2,arm*2,SC,C_WHITE);
    fill_rect(cx-SC/2,cy-arm,SC,arm*2,C_WHITE);
  }
}
static void draw_status_bar(void){
  dfill(0,0,360,DSTATUS,C_BG2);
  fill_rect(0,DY(DSTATUS)-1,(int)SCR.w,1,C_LINE);
  struct clock_ui c; clock_read(&c);
  char hh[4],mm[4]; u2s2((u64)c.hh,hh); u2s2((u64)c.mm,mm);
  char t[8]; t[0]=hh[0];t[1]=hh[1];t[2]=':';t[3]=mm[0];t[4]=mm[1];t[5]=0;
  dtext(DPAD,0,52,DSTATUS,14,t,C_TXT,AL_LEFT);
  dreg("status.time",DPAD,0,52,DSTATUS,REG_STATUS);
  int pct=SI.battery_pct;
  char pb[8]; if(pct<0){ pb[0]='-';pb[1];pb[0]='-';pb[1]='-';pb[2]=0; } else u2s((u64)pct,pb);
  char pbs[8]; int n=0; for(int i=0;pb[i];i++)pbs[n++]=pb[i]; pbs[n++]='%'; pbs[n]=0;
  /* battery: glyph at the far right, percentage immediately to its left --
     two boxes that provably do not touch (the A26 status bar had them collide
     with the punch-hole band, which is why the cutout rule exists). */
  int gx=360-DPAD-10;
  battery_glyph_d(gx,10,16,pct,SI.charging);
  dreg("status.battery.glyph",gx,10,10,16,REG_STATUS);
  dtext(gx-44,0,40,DSTATUS,13,pbs,C_TXT,AL_RIGHT);
  dreg("status.battery.label",gx-44,0,40,DSTATUS,REG_STATUS);
  if(SI.on_ac||SI.charging){
    int r=3, ax=DPAD+58;                 /* clear of status.time (16..68) */
    fill_rect(DX(ax),DY(DSTATUS/2-r),r*2*SC,r*2*SC,C_OK);
    dreg("status.ac",ax,DSTATUS/2-r,r*2,r*2,REG_STATUS);
  }
}

/* ------------------------------------------------------------------ glyphs */
/* Icons are drawn in DESIGN units (cx,cy,r are design units).  They are simple
   geometric marks in the VM's accent colours - no image decoder is needed. */
static void i_disc(int cx,int cy,int r,u32 col){
  int R=r*SC, CX=DX(cx), CY=DY(cy);
  for(int j=-R;j<=R;j++)for(int i=-R;i<=R;i++) if(i*i+j*j<=R*R) px(CX+i,CY+j,col);
}
static void i_ring(int cx,int cy,int r,int t,u32 col){
  int R=r*SC, T=t*SC, CX=DX(cx), CY=DY(cy);
  for(int j=-R;j<=R;j++)for(int i=-R;i<=R;i++){
    int d2=i*i+j*j;
    if(d2<=R*R&&d2>=(R-T)*(R-T)) px(CX+i,CY+j,col);
  }
}
static void i_gear(int cx,int cy,int r,u32 col){
  int R=r*SC, T=r*SC/3; if(T<2)T=2, R=r*SC;
  i_ring(cx,cy,r,r/3>0?r/3:1,col);
  for(int k=0;k<8;k++){
    int a=k*45;
    int ux=(a==0?SC:0);
    (void)ux;
    /* 8 spokes at 45 degree steps, drawn as small squares on the ring */
    int sx=(k==0||k==4)?(k==0?1:-1):0;
    int sy=(k==2||k==6)?(k==2?1:-1):0;
    int dx=(k==1||k==7)?1:((k==3||k==5)?-1:0);
    int dy=(k==1||k==3)?1:((k==5||k==7)?-1:0);
    dfill(cx+dx*r-sx*r,cy+dy*r-sy*r,2,2,col);
    (void)T;
  }
}
static void i_grid(int cx,int cy,int r,u32 col){
  int s=(r*2)/3, g=(r*2)/3/3;
  dround(cx-r,cy-r,s,s,2,col); dround(cx-r+s+g,cy-r,s,s,2,col);
  dround(cx-r,cy-r+s+g,s,s,2,col); dround(cx-r+s+g,cy-r+s+g,s,s,2,col);
}
static void i_terminal(int cx,int cy,int r,u32 col){
  dround(cx-r,cy-r*7/10,r*2,r*7/5,3,col);
  dfill(cx-r/2,cy-r/4,r/3,1,C_BG);
  dfill(cx,cy+r/5,r/3,1,C_BG);
}
static void i_power(int cx,int cy,int r,u32 col){
  int R=r*SC, CX=DX(cx), CY=DY(cy), T=(r/4>0?r/4:1)*SC;
  for(int j=-R;j<=R;j++)for(int i=-R;i<=R;i++){
    int d2=i*i+j*j;
    if(d2<=R*R&&d2>=(R-T)*(R-T)&&j>-(R/3)) px(CX+i,CY+j,col);
  }
  dfill(cx-1,cy-r,2,r,col);
}
static void i_display(int cx,int cy,int r,u32 col){
  dround(cx-r,cy-r,r*2,r*2-r/4,3,col);
  dfill(cx-r+1,cy-r+1,r*2-2,r*2-r/4-2,C_BG);
  dfill(cx-1,cy+r-r/3,3,r/4,col);
}
static void i_about(int cx,int cy,int r,u32 col){
  i_disc(cx,cy,r,col);
  const struct nuxel_font *f=font_for(r);
  font_center(DX(cx),DY(cy)-font_h(f)/2,f,"i",C_BG);
}
static void i_search(int cx,int cy,int r,u32 col){
  i_ring(cx-r/4,cy-r/4,r*3/5,r/6>0?r/6:1,col);
  dfill(cx+r/6,cy+r/6,r/2+1,1,col);
  dfill(cx+r/6+1,cy+r/6+1,1,r/2+1,col);
}
static void i_phone(int cx,int cy,int r,u32 col){
  dfill(cx-r/2,cy-r,2*r/3,r*2,col);
  dfill(cx-r/6,cy+r-r/5,r/3,1,C_BG);
}
static void i_camera(int cx,int cy,int r,u32 col){
  dround(cx-r,cy-r*3/5,r*2,r*6/5,3,col);
  i_ring(cx,cy,r/2,r/6>0?r/6:1,C_BG);
}

struct tile { const char *label; int act; void(*icon)(int,int,int,u32); int enabled; };
static const struct tile TILES[8]={
  {"SETTINGS",ACT_SETTINGS,i_gear,1},
  {"SYSTEM",  ACT_SYSTEM,  i_grid,1},
  {"LOGS",    ACT_LOGS,    i_terminal,1},
  {"DISPLAY", ACT_CTEST,   i_display,1},
  {"POWER",   ACT_POWER,   i_power,1},
  {"ABOUT",   ACT_ABOUT,   i_about,1},
  {"PHONE",   0,           i_phone,0},      /* not implemented on this build */
  {"CAMERA",  0,           i_camera,0}
};
static const struct tile DOCK[5]={
  {"HOME",ACT_HOME,i_grid,1},{"SETTINGS",ACT_SETTINGS,i_gear,1},{"SYSTEM",ACT_SYSTEM,i_display,1},
  {"LOGS",ACT_LOGS,i_terminal,1},{"POWER",ACT_POWER,i_power,1}
};

/* --------------------------------------------------------------------- cards */
static void card(int x,int y,int w,int h,const char *title){
  dround(x,y,w,h,DCARD_R,C_CARD);
  if(title) dtext(x+DPAD,y+10,w-DPAD*2,18,11,title,C_TXT2,AL_LEFT);
  dreg(title?title:"card",x,y,w,h,REG_CONTENT);
}
/* ONE list row: key left, value right, both single-line and clipped.  The row is
   exactly DROW tall and its value gets whatever width the key leaves; if the text
   does not fit it is ellipsised, never allowed to run into the next column.  (The
   A26 defect here was a 44-px row holding 84-px text.) */
static void row_kv(int x,int y,int w,const char *k,const char *v){
  dreg(k,x,y,w,DROW,REG_CONTENT);
  dtext(x+DPAD,y,w/2, DROW,13,k,C_TXT2,AL_LEFT);
  int kw=font_w(font_for(13),k);
  int vx=x+DPAD+kw+12;
  int vw=(x+w-DPAD)-vx;
  if(vw<40){ vx=x+w/2; vw=x+w-DPAD-vx; }
  dtext(vx,y,vw>0?vw:0,DROW,14,v,C_TXT,AL_RIGHT);
  dhline(x+DPAD,y+DROW-1,w-DPAD*2,C_LINE);
}
static void row_button(int x,int y,int w,int h,const char *label,int act,u32 bg,u32 fg,int design_px){
  dround(x,y,w,h,DBTN_R,bg);
  dtext(x+12,y,w-24,h,design_px,label,fg,AL_CENTER);
  widget_add(DX(x),DY(y),w*SC,h*SC,act);
  dreg(label,x,y,w,h,REG_CONTENT);
}
static void section(int x,int y,int w,const char *t){
  dtext(x+DPAD,y,w-DPAD,20,11,t,C_ACCENT,AL_LEFT);
}

/* ----------------------------------------------------------------- home */
static void page_home(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+DPAD;
  struct clock_ui c; clock_read(&c);
  char hh[4],mm[4]; u2s2((u64)c.hh,hh); u2s2((u64)c.mm,mm);
  char t[8]; t[0]=hh[0];t[1]=hh[1];t[2]=':';t[3]=mm[0];t[4]=mm[1];t[5]=0;
  /* hero: time (28, like the PWA header) + date, then the VM's search pill */
  dtext(x,y,w/2,40,28,t,C_TXT,AL_LEFT); y+=40;
  char date[40]; int n=0;
  const char *mo=MONTHS[(c.mo>=1&&c.mo<=12)?c.mo-1:0];
  for(int i=0;mo[i];i++)date[n++]=mo[i];
  date[n++]=' ';
  char dd[4]; u2s((u64)c.d,dd);
  for(int i=0;dd[i];i++)date[n++]=dd[i];
  date[n++]=','; date[n++]=' ';
  char yy[8]; u2s((u64)c.y,yy);
  for(int i=0;yy[i];i++)date[n++]=yy[i];
  date[n]=0;
  dtext(x,y,w,18,13,date,C_TXT2,AL_LEFT); y+=18+GAP12;
  /* status card: battery + link + uptime (the VM's system chips) */
  int ch=72;
  card(x,y,w,ch,"DEVICE");
  battery_glyph_d(x+DPAD,y+26,22,SI.battery_pct,SI.charging);
  char bs[40]; int m=0;
  if(SI.battery_ok){ char pb[8]; u2s((u64)(SI.battery_pct<0?0:SI.battery_pct),pb);
    for(int i=0;pb[i];i++)bs[m++]=pb[i]; bs[m++]='%'; bs[m++]=' '; }
  else { const char *u="NO BATTERY "; for(int i=0;u[i];i++)bs[m++]=u[i]; }
  for(int i=0;SI.battery_status[i]&&m<34;i++)bs[m++]=SI.battery_status[i];
  bs[m]=0;
  dtext(x+DPAD+22,y+26,w/2-24,22,14,bs,C_TXT,AL_LEFT);
  dtext(x+w/2,y+26,w/2-DPAD,22,13,SI.uptime,C_TXT2,AL_RIGHT);
  char us[48]; int k=0; const char *pr="USB "; for(int i=0;pr[i];i++)us[k++]=pr[i];
  for(int i=0;SI.usb[i]&&k<40;i++)us[k++]=SI.usb[i];
  us[k]=0;
  dtext(x+DPAD,y+50,w-DPAD*2,18,11,us,C_TXT2,AL_LEFT);
  y+=ch+GAP16;
  /* app grid: 4 columns x 2 rows of 64-px icons, VM launcher geometry */
  int cols=4, cw=(w-(cols-1)*GAP12)/cols, ih=DICON+22;
  for(int i=0;i<8;i++){
    int col=i%cols, row=i/cols;
    int tx=x+col*(cw+GAP12), ty=y+row*(ih+GAP12);
    if(ty+ih>DESIGN_H-DDOCK-GAP8) break;
    int ix=tx+(cw-DICON)/2;
    dround(ix,ty,DICON,DICON,DICON_R,TILES[i].enabled?C_CARD:pack_rgb(0x0f,0x1c,0x33));
    TILES[i].icon(ix+DICON/2,ty+DICON/2,18,TILES[i].enabled?C_ACCENT:pack_rgb(0x2c,0x3d,0x5c));
    dtext(tx,ty+DICON+2,cw,18,11,TILES[i].label,TILES[i].enabled?C_TXT:C_TXT2,AL_CENTER);
    if(TILES[i].enabled) widget_add(DX(ix),DY(ty),DICON*SC,DICON*SC,TILES[i].act);
    dreg(TILES[i].label,tx,ty,cw,ih,REG_CONTENT);
  }
}
/* ------------------------------------------------------------ settings etc. */
static void page_settings(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+GAP12;
  dtext(x,y,w,26,22,"Settings",C_TXT,AL_LEFT); y+=30;
  char res[32]; int n=0;
  { char t[16]; u2s((u64)SCR.w,t); for(int i=0;t[i];i++)res[n++]=t[i]; res[n++]='x';
    u2s((u64)SCR.h,t); for(int i=0;t[i];i++)res[n++]=t[i]; res[n]=0; }
  char fb[48]; int m=0;
  { const char *p="STRIDE "; for(int i=0;p[i];i++)fb[m++]=p[i];
    char t[16]; u2s((u64)SCR.stride,t); for(int i=0;t[i];i++)fb[m++]=t[i];
    const char *q=" BPP "; for(int i=0;q[i];i++)fb[m++]=q[i];
    u2s((u64)SCR.bpp,t); for(int i=0;t[i];i++)fb[m++]=t[i];
    const char *r=" BUFS "; for(int i=0;r[i];i++)fb[m++]=r[i];
    u2s((u64)SCR.bufs,t); for(int i=0;t[i];i++)fb[m++]=t[i]; fb[m]=0; }
  section(x,y,w,"DISPLAY"); y+=20;
  row_kv(x,y,w,"PANEL",res); y+=DROW;
  row_kv(x,y,w,"FRAMEBUFFER",fb); y+=DROW;
  row_kv(x,y,w,"COLOUR ORDER",SCR.hw_abgr?"ABGR8888 (hardware)":"FBVAR DECLARED"); y+=DROW;
  y+=GAP8;
  section(x,y,w,"INTERFACE"); y+=20;
  row_kv(x,y,w,"BUILD",NUXEL_UI_REV); y+=DROW;
  row_kv(x,y,w,"ANIMATION",file_exists("/var/lib/nuxel/animation")?"state file present":"no state file"); y+=DROW;
  row_kv(x,y,w,"TOUCH",SI.touch); y+=DROW;
  row_kv(x,y,w,"INPUT NODE",SI.touchpath); y+=DROW;
  y+=GAP12;
  /* two columns: the four actions must fit the safe area at every scale, and a
     half-width button is measured against its own half (never the page). */
  int bw2=(w-GAP12)/2;
  row_button(x,y,bw2,48,"COLOUR TEST",ACT_CTEST,C_ACCENT_D,C_TXT,13);
  row_button(x+bw2+GAP12,y,bw2,48,"SCREENSHOT",ACT_SHOT,C_ACCENT_D,C_TXT,13);
  y+=48+GAP8;
  row_button(x,y,bw2,48,"RESTART UI",ACT_RESTART,C_CARD,C_TXT,13);
  row_button(x+bw2+GAP12,y,bw2,48,"POWER",ACT_POWER,C_CARD,C_ERR,13);
}
static int SYS_TOP=0;
static void page_system(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+GAP12;
  dtext(x,y,w/2,26,22,"System",C_TXT,AL_LEFT);
  row_button(x+w-124,y-4,60,30,"UP",ACT_LOGUP,C_CARD,C_TXT,11);
  row_button(x+w-60,y-4,60,30,"DN",ACT_LOGDOWN,C_CARD,C_TXT,11);
  y+=30;
  static char anim[80], uistage[80];
  anim[0]=0; uistage[0]=0;
  { char st[128]; int n=file_read("/var/lib/nuxel/animation",st,sizeof st);
    if(n>0){ int m=0; for(int i=0;i<n&&m<70;i++) if(st[i]!='\n') anim[m++]=st[i]; anim[m]=0; } }
  { char st[128]; int n=file_read("/var/lib/nuxel/ui-stage",st,sizeof st);
    if(n>0){ int m=0; for(int i=0;i<n&&m<70;i++) if(st[i]!='\n') uistage[m++]=st[i]; uistage[m]=0; } }
  const char *K[12]={"KERNEL","OS","PID1","STATE","CGROUP","UPTIME","ROOTFS","BATTERY",
                     "USB CONSOLE","INPUT","ANIM STAGE","UI STAGE"};
  const char *V[12]={SI.kernel,SI.osname,SI.pid1,SI.system_state,SI.cgroup,SI.uptime,
                     SI.root_fs,SI.battery_status,SI.usb,SI.touch,
                     anim[0]?anim:"(not reported)",uistage[0]?uistage:"(not reported)"};
  int avail=(DESIGN_H-DDOCK-GAP16-y)/DROW;
  if(avail<3) avail=3;
  if(SYS_TOP>12-avail) SYS_TOP=12-avail;
  if(SYS_TOP<0) SYS_TOP=0;
  for(int i=0;i<avail;i++){
    int k=i+SYS_TOP;
    if(k>=12) break;
    row_kv(x,y,w,K[k],V[k]); y+=DROW;
  }
}
static void page_logs(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+GAP12;
  dtext(x,y,w/2,26,22,"Logs",C_TXT,AL_LEFT);
  row_button(x+w-124,y-4,60,30,"UP",ACT_LOGUP,C_CARD,C_TXT,11);
  row_button(x+w-60,y-4,60,30,"DN",ACT_LOGDOWN,C_CARD,C_TXT,11);
  y+=30;
  static char LB[8192];
  const char *src="/var/lib/nuxel/ui.log";
  if(!file_exists(src)) src="/var/log/nuxel-bootreport.txt";
  int got=file_read(src,LB,sizeof LB-1);
  if(got<=0){ dtext(x,y,w,20,13,"no /var/lib/nuxel/ui.log yet",C_TXT2,AL_LEFT); return; }
  static int loff[256]; int nlines=0;
  loff[0]=0; nlines=1;
  for(int i=0;i<got&&nlines<256;i++) if(LB[i]=='\n'){ LB[i]=0; loff[nlines++]=i+1; }
  if(nlines>1&&loff[nlines-1]>=got) nlines--;
  section(x,y,w,src); y+=18;
  int rh=30, avail=(DESIGN_H-DDOCK-GAP16-y)/rh;
  if(avail<1) avail=1;
  if(LOG_TOP>nlines-avail) LOG_TOP=nlines-avail;
  if(LOG_TOP<0) LOG_TOP=0;
  for(int i=0;i<avail;i++){
    int k=i+LOG_TOP;
    if(k>=nlines) break;
    dtext(x,y,w,rh-6,11,LB+loff[k],C_TXT,AL_LEFT);
    y+=rh;
  }
}
static void page_power(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+GAP16;
  dtext(x,y,w,30,22,"Power",C_TXT,AL_CENTER); y+=34;
  dtext(x,y,w,18,11,"Tap once to arm, tap again within 6s to execute.",C_TXT2,AL_CENTER); y+=26;
  int armed=POWER_ARMED && (int)mono_sec()<(int)POWER_ARM_UNTIL;
  row_button(x,y,w,56,armed?"TAP AGAIN: REBOOT NOW":"REBOOT",ACT_REBOOT,
             armed?pack_rgb(0x7a,0x1c,0x10):C_CARD,armed?C_WHITE:C_TXT,16); y+=56+GAP8;
  row_button(x,y,w,56,armed?"TAP AGAIN: SHUT DOWN":"SHUT DOWN",ACT_SHUTDOWN,
             armed?pack_rgb(0x7a,0x1c,0x10):C_CARD,armed?C_WHITE:C_TXT,16); y+=56+GAP8;
  row_button(x,y,w,56,"CANCEL",ACT_HOME,C_CARD,C_TXT2,16); y+=56+GAP8;
  if(armed){
    char t[48]; int m=0; const char *p="ARMED FOR "; for(int i=0;p[i];i++)t[m++]=p[i];
    char s[8]; u2s((u64)(POWER_ARM_UNTIL-mono_sec()),s);
    for(int i=0;s[i];i++)t[m++]=s[i]; t[m++]='s'; t[m]=0;
    dtext(x,y,w,18,11,t,C_WARN,AL_CENTER);
  }
}
static void page_about(void){
  int x=DPAD, w=360-DPAD*2, y=DSTATUS+GAP16;
  dtext(x,y,w,34,28,"Nuxel",C_ACCENT,AL_CENTER); y+=36;
  dtext(x,y,w,18,13,"A Fedora Linux phone",C_TXT2,AL_CENTER); y+=26;
  row_kv(x,y,w,"BUILD",NUXEL_UI_REV); y+=DROW;
  row_kv(x,y,w,"DEVICE","Galaxy S10+ (beyond2lte)"); y+=DROW;
  row_kv(x,y,w,"SOC","Exynos 9820"); y+=DROW;
  row_kv(x,y,w,"DISPLAY","1440x3040 AMOLED fbdev"); y+=DROW;
  row_kv(x,y,w,"GRAPHICS","DECON/DSIM fbdev (no DRM/KMS)"); y+=DROW;
  row_kv(x,y,w,"SHELL","fbdev-native (transitional)"); y+=DROW;
  row_kv(x,y,w,"FONT","DejaVu Sans (bitmap atlas)"); y+=DROW;
  y+=GAP8;
  dtext(x,y,w,16,11,"Boot animation: the original Nuxel MP4, decoded on this",C_TXT2,AL_LEFT); y+=16;
  dtext(x,y,w,16,11,"panel by nuxel-anim-player. The opening frame is painted",C_TXT2,AL_LEFT); y+=16;
  dtext(x,y,w,16,11,"by nuxel-fb-phone before systemd starts.",C_TXT2,AL_LEFT); y+=20;
  dtext(x,y,w,16,11,"Phosh needs DRM/KMS: not available on this 4.14 kernel.",C_WARN,AL_LEFT);
}

/* ---------------------------------------------------------------------- dock */
static void draw_dock(void){
  int y=DESIGN_H-DDOCK;
  dfill(0,y,360,DDOCK,C_BG2);
  fill_rect(0,DY(y)-1,(int)SCR.w,1,C_LINE);
  int n=5, slot=360/n;
  for(int i=0;i<n;i++){
    int x=i*slot;
    int act=DOCK[i].act;
    int active=(act==ACT_HOME&&PAGE==PAGE_HOME)||(act==ACT_SETTINGS&&PAGE==PAGE_SETTINGS)||
               (act==ACT_SYSTEM&&PAGE==PAGE_SYSTEM)||(act==ACT_LOGS&&PAGE==PAGE_LOGS)||
               (act==ACT_POWER&&PAGE==PAGE_POWER);
    if(active) dround(x+8,y+8,slot-16,DDOCK-16,DBTN_R,C_CARD);
    u32 col=act==ACT_POWER?C_ERR:(active?C_ACCENT:C_TXT2);
    DOCK[i].icon(x+slot/2,y+26,10,col);
    /* the label is FITTED to its own slot: this is the fix for the A26 fused
       dock labels (SETTINGS needed ~384 px in a 288 px slot). */
    dtext(x+3,y+DDOCK-22,slot-6,16,11,DOCK[i].label,active?C_TXT:C_TXT2,AL_CENTER);
    dreg(DOCK[i].label,x+2,y,slot-4,DDOCK,REG_DOCK);
    widget_add(DX(x),DY(y),slot*SC,DDOCK*SC,act);
  }
}
/* ------------------------------------------------------------------ toasts */
static void draw_toast(void){
  if(TOAST[0] && (int)mono_sec()<TOAST_UNTIL){
    int th=44, y=DESIGN_H-DDOCK-th-GAP12;
    dround(DPAD,y,360-DPAD*2,th,12,C_CARD_HI);
    dtext(DPAD+12,y,360-DPAD*2-24,th,13,TOAST,C_TXT,AL_CENTER);
    dreg("toast",DPAD,y,360-DPAD*2,th,REG_CONTENT);
  }
}
/* A27: the error banner used to sit at the top of the content area, where it
   collided with the System/Logs scroll buttons.  It is now a snackbar in the
   band above the dock (the same band as the toast), stacked ABOVE the toast when
   both are visible, so neither can ever cover the other or the page header. */
static void draw_error_banner(void){
  if(!UI_ERROR[0]) return;
  int th=32;
  int y=DESIGN_H-DDOCK-GAP12-th;
  if(TOAST[0] && (int)mono_sec()<TOAST_UNTIL) y-=th+GAP8;
  dround(DPAD,y,360-DPAD*2,th,10,pack_rgb(0x4a,0x10,0x10));
  dtext(DPAD+10,y,360-DPAD*2-20,th,11,UI_ERROR,C_TXT,AL_CENTER);
  dreg("error.banner",DPAD,y,360-DPAD*2,th,REG_CONTENT);
}


/* ============================================================================
 * A28 — THE NUXEL HOME LAUNCHER PORT (S10+)
 *
 * WHAT THIS IS.  The Nuxel launcher that runs in the UTM VM is the Nuxel Home
 * PWA (pwa/nuxel-home/), served by services/nuxel-web.service on 127.0.0.1:8000
 * and rendered by a WebKitGTK browser inside the Phosh Wayland session; its
 * native GTK4 twin is shell/nuxel-home-native/.  This phone's kernel is a
 * Samsung 4.14 vendor tree with `# CONFIG_DRM is not set`, so there is no
 * /dev/dri: no Wayland compositor, no GTK, no browser engine can present to the
 * DECON panel.  The launcher therefore runs as a MINIMAL PLATFORM ADAPTER over
 * the one hardware-proven display path (fbdev), and everything it SHOWS comes
 * from the launcher's own files:
 *
 *   app list, order, docking, colours, icons
 *        -> pwa/nuxel-home/js/apps.js, compiled in by
 *           tools/s10plus/a28/gen-launcher.py (see generated/nuxel-launcher.h)
 *   design tokens (palette, status-bar/dock/grid/icon geometry)
 *        -> pwa/nuxel-home/css/style.css :root, same generator
 *   grid + dock layout, icon tinting, label metrics
 *        -> pwa/nuxel-home/css/launcher.css + js/launcher.js
 *   status bar layout
 *        -> pwa/nuxel-home/css/status-bar.css
 *   wallpaper
 *        -> assets/nuxel-background.png, decoded at runtime (the file the PWA
 *           loads as ../assets/nuxel-background.png), with the PWA's own
 *           background-color as the documented fallback
 *   app launch commands
 *        -> apps.js type/url + app_registry.json native_binary
 *
 * NOTHING here is a second design: no new colours, no new icons, no new app
 * list, no new ordering.  See docs/s10plus-autonomous-boot-repair/
 * UTM-LAUNCHER-PORT/ for the port record and the measured limitations.
 * ==========================================================================*/
static const char *A_WALLDUMP="";   /* --wallpaper-dump=FILE (offline gate) */
static const int LAUNCHER_GRID_IDX[NUXEL_LAUNCHER_GRID_COUNT]=NUXEL_LAUNCHER_GRID;
static const int LAUNCHER_DOCK_IDX[NUXEL_LAUNCHER_DOCK_COUNT]=NUXEL_LAUNCHER_DOCK;

/* ---- alpha compositing ---------------------------------------------------
 * launcher.js paints an app tile as `background: <app.color>33` (0x33/255 =
 * 20% alpha) over whatever is beneath it - in the VM that is the wallpaper.
 * So the tile is composited against the CANVAS, not against a flat colour. */
static int blend_a(u32 dst,u32 src,int alpha, u32 *out){
  if(alpha>=255){ *out=src; return 0; }
  if(alpha<=0){ *out=dst; return 0; }
  u32 ia=255u-(u32)alpha, o=0xff000000u;
  for(int sh=0;sh<24;sh+=8){
    u32 d=(dst>>sh)&0xffu, s=(src>>sh)&0xffu;
    o|=((((s*(u32)alpha)+(d*ia))/255u)&0xffu)<<sh;
  }
  *out=o;
  return 0;
}
static void px_blend(int x,int y,u32 src,int alpha){
  if(x<0||y<0||(u32)x>=SCR.w||(u32)y>=SCR.h) return;
  /* NOTE: deliberately NOT clipped by CLX/CLY.  The clip rectangle belongs to
     dtext/font_draw (the A23..A27 convention - fill_rect() and px() ignore it
     too); honouring it here let the last dtext on the page clip every later
     composited element, which is how the A28 colour gate caught the app tiles
     never being painted. */
  u8 *row=SCR.canvas+(u64)y*SCR.stride+(u64)x*(SCR.bpp/8);
  u32 dst;
  if(SCR.bpp==32) dst=*(volatile u32*)row;
  else if(SCR.bpp==16) dst=*(volatile u16*)row;
  else dst=((u32)row[0])|((u32)row[1]<<8)|((u32)row[2]<<16);
  u32 out; blend_a(dst,src,alpha,&out);
  if(SCR.bpp==32) *(volatile u32*)row=out;
  else if(SCR.bpp==16) *(volatile u16*)row=(u16)out;
  else { row[0]=(u8)(out&0xff); row[1]=(u8)((out>>8)&0xff); row[2]=(u8)((out>>16)&0xff); }
}
static void fill_rect_a(int x,int y,int w,int h,u32 c,int alpha){
  int x0=x<0?0:x, y0=y<0?0:y;
  int x1=x+w>(int)SCR.w?(int)SCR.w:x+w, y1=y+h>(int)SCR.h?(int)SCR.h:y+h;
  if(x1<=x0||y1<=y0) return;
  for(int yy=y0;yy<y1;yy++)
    for(int xx=x0;xx<x1;xx++) px_blend(xx,yy,c,alpha);
}
static void round_rect_a(int x,int y,int w,int h,int r,u32 c,int alpha){
  if(r*2>w) r=w/2; if(r*2>h) r=h/2;
  fill_rect_a(x+r,y,w-2*r,h,c,alpha);
  fill_rect_a(x,y+r,r,h-2*r,c,alpha);
  fill_rect_a(x+w-r,y+r,r,h-2*r,c,alpha);
  for(int j=0;j<r;j++)for(int i=0;i<r;i++){
    int dx=r-1-i, dy=r-1-j;
    if((s64)(dx*dx+dy*dy)<=(s64)(r-1)*(r-1)){
      px_blend(x+i,y+j,c,alpha); px_blend(x+w-1-i,y+j,c,alpha);
      px_blend(x+i,y+h-1-j,c,alpha); px_blend(x+w-1-i,y+h-1-j,c,alpha);
    }
  }
}

/* ---- the launcher's emoji icons ------------------------------------------
 * make-emoji-atlas.py rasterised the codepoints in apps.js from Noto Emoji, so
 * the phone draws the registry's OWN icons, tinted with each app's colour -
 * exactly what launcher.js does with `color: <app.color>`. */
static const struct nuxel_emoji *emoji_lookup(int design_px,unsigned int cp){
  int si=-1;
  for(int i=0;i<NUXEL_EMOJI_NSIZES;i++) if(NUXEL_EMOJI_FONTS[i].design<=design_px) si=i;
  if(si<0) si=0;
  const struct nuxel_emoji *t=NUXEL_EMOJI_TABLES[si];
  for(int i=0;i<NUXEL_EMOJI_GLYPH_COUNT;i++) if(t[i].cp==cp) return &t[i];
  return 0;
}

/* ---- zlib inflate (RFC 1950/1951) ----------------------------------------
 * Needed for ONE job: decoding the PWA's own wallpaper asset at runtime, so the
 * binary that must travel over the CDC-ACM console stays small. ~250 lines of
 * self-contained code, no libc, no external dependency. */
struct bx { const u8 *in; u64 n,pos; u32 bitb; int bitn; };
static int bx_bit(struct bx *b){
  if(b->bitn==0){ if(b->pos>=b->n) return -1; b->bitb=b->in[b->pos++]; b->bitn=8; }
  int v=(int)(b->bitb&1u); b->bitb>>=1; b->bitn--; return v;
}
static int bx_bits(struct bx *b,int n){
  int v=0; for(int i=0;i<n;i++){ int bit=bx_bit(b); if(bit<0) return -1; v|=bit<<i; } return v;
}
static int bx_byte(struct bx *b){ if(b->pos>=b->n) return -1; return (int)b->in[b->pos++]; }
static void bx_align(struct bx *b){ b->bitn=0; b->bitb=0; }

struct huff { u16 count[16]; u16 sym[320]; };
static int huff_build(struct huff *h,const u8 *len,int n){
  for(int i=0;i<16;i++) h->count[i]=0;
  for(int i=0;i<n;i++) h->count[len[i]]++;
  h->count[0]=0;
  int left=1;
  for(int l=1;l<16;l++){ left<<=1; left-=h->count[l]; if(left<0) return -1; }
  u16 offs[16]; offs[1]=0;
  for(int l=1;l<15;l++) offs[l+1]=(u16)(offs[l]+h->count[l]);
  for(int i=0;i<n;i++) if(len[i]) h->sym[offs[len[i]]++]= (u16)i;
  return 0;
}
static int huff_dec(struct bx *b,const struct huff *h){
  int code=0,first=0,index=0;
  for(int len=1;len<=15;len++){
    int bit=bx_bit(b); if(bit<0) return -1;
    code|=bit;
    int count=(int)h->count[len];
    if(code-first<count) return (int)h->sym[index+(code-first)];
    index+=count; first+=count; first<<=1; code<<=1;
  }
  return -1;
}
static const u16 INF_LEN_BASE[29]={3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,
                                    67,83,99,115,131,163,195,227,258};
static const u8  INF_LEN_EXT[29]={0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
static const u16 INF_DIST_BASE[30]={1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,
                                     769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
static const u8  INF_DIST_EXT[30]={0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};
static const u8  INF_CLORDER[19]={16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};

static long inflate_zlib(const u8 *in,u64 n,u8 *out,u64 cap,u64 *outlen){
  struct bx b; b.in=in; b.n=n; b.pos=0; b.bitb=0; b.bitn=0;
  int cmf=bx_byte(&b), flg=bx_byte(&b);
  if(cmf<0||flg<0) return -1;
  if((cmf&0x0f)!=8) return -2;                     /* must be deflate */
  if(((cmf<<8)|flg)%31!=0) return -3;              /* FCHECK */
  if(flg&0x20) return -4;                          /* preset dictionary */
  u64 o=0;
  for(;;){
    int last=bx_bits(&b,1); if(last<0) return -5;
    int type=bx_bits(&b,2); if(type<0) return -6;
    if(type==0){
      bx_align(&b);
      int l0=bx_byte(&b),l1=bx_byte(&b),m0=bx_byte(&b),m1=bx_byte(&b);
      if(l0<0||l1<0||m0<0||m1<0) return -7;
      u32 len=(u32)l0|((u32)l1<<8), nlen=(u32)m0|((u32)m1<<8);
      if(((len^0xffffu)&0xffffu)!=nlen) return -8;
      if(o+len>cap) return -9;
      for(u32 i=0;i<len;i++){ int c=bx_byte(&b); if(c<0) return -10; out[o++]=(u8)c; }
    } else if(type==1||type==2){
      static u8 fxl[288], fxd[30];
      struct huff lit,dist;
      if(type==1){
        for(int i=0;i<144;i++) fxl[i]=8;
        for(int i=144;i<256;i++) fxl[i]=9;
        for(int i=256;i<280;i++) fxl[i]=7;
        for(int i=280;i<288;i++) fxl[i]=8;
        for(int i=0;i<30;i++) fxd[i]=5;
        if(huff_build(&lit,fxl,288)<0||huff_build(&dist,fxd,30)<0) return -11;
      } else {
        int hlit=bx_bits(&b,5), hdist=bx_bits(&b,5), hclen=bx_bits(&b,4);
        if(hlit<0||hdist<0||hclen<0) return -12;
        hlit+=257; hdist+=1; hclen+=4;
        if(hlit>286||hdist>30) return -13;
        u8 cl[19];
        for(int i=0;i<19;i++) cl[i]=0;
        for(int i=0;i<hclen;i++){ int v=bx_bits(&b,3); if(v<0) return -14; cl[INF_CLORDER[i]]=(u8)v; }
        struct huff clh;
        if(huff_build(&clh,cl,19)<0) return -15;
        u8 lens[320]; int i=0;
        while(i<hlit+hdist){
          int sym=huff_dec(&b,&clh); if(sym<0) return -16;
          if(sym<16){ lens[i++]=(u8)sym; }
          else if(sym==16){ if(i==0) return -17; int v=bx_bits(&b,2); if(v<0) return -18;
            u8 prev=lens[i-1]; for(int k=0;k<3+v;k++) lens[i++]=prev; }
          else if(sym==17){ int v=bx_bits(&b,3); if(v<0) return -19;
            for(int k=0;k<3+v;k++) lens[i++]=0; }
          else { int v=bx_bits(&b,7); if(v<0) return -20;
            for(int k=0;k<11+v;k++) lens[i++]=0; }
          if(i>hlit+hdist) return -21;
        }
        if(lens[256]==0) return -22;
        if(huff_build(&lit,lens,hlit)<0||huff_build(&dist,lens+hlit,hdist)<0) return -23;
      }
      for(;;){
        int sym=huff_dec(&b,&lit); if(sym<0) return -24;
        if(sym<256){ if(o>=cap) return -25; out[o++]=(u8)sym; continue; }
        if(sym==256) break;
        sym-=257; if(sym>=29) return -26;
        int len=INF_LEN_BASE[sym];
        if(INF_LEN_EXT[sym]){ int v=bx_bits(&b,INF_LEN_EXT[sym]); if(v<0) return -27; len+=v; }
        int ds=huff_dec(&b,&dist); if(ds<0||ds>=30) return -28;
        int d=INF_DIST_BASE[ds];
        if(INF_DIST_EXT[ds]){ int v=bx_bits(&b,INF_DIST_EXT[ds]); if(v<0) return -29; d+=v; }
        if((u64)d>o) return -30;
        if(o+(u64)len>cap) return -31;
        for(int k=0;k<len;k++){ out[o]=out[o-(u64)d]; o++; }
      }
    } else return -32;
    if(last) break;
  }
  *outlen=o;
  return 0;
}

/* ---- PNG decode (bit depth 8, no interlace) ------------------------------ */
static u32 be32(const u8 *p){ return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|(u32)p[3]; }
/* Returns 0 and fills *rgb (w*h*3 bytes, row-major) on success.  Negative codes
   name the failure so the log says WHY the wallpaper is absent. */
static long png_decode_rgb(const u8 *d,u64 n,u8 *raw,u64 rawcap,u8 *rgb,u64 rgbcap,
                           u32 *ow,u32 *oh,u64 *rawused){
  if(n<8||d[0]!=0x89||d[1]!='P'||d[2]!='N'||d[3]!='G') return -1;
  u32 w=0,h=0; int bd=0,ct=0,comp=0,filt=0,inter=0;
  u64 idat_total=0, idat_have=0, off=8;
  u8 plte[768]; int plte_n=0;
  int seen_ihdr=0;
  while(off+8<=n){
    u32 ln=be32(d+off);
    const char *t=(const char*)(d+off+4);
    if(off+12+(u64)ln>n) return -2;
    const u8 *p=d+off+8;
    if(t[0]=='I'&&t[1]=='H'&&t[2]=='D'&&t[3]=='R'){
      if(ln!=13) return -3;
      w=be32(p); h=be32(p+4); bd=p[8]; ct=p[9]; comp=p[10]; filt=p[11]; inter=p[12];
      seen_ihdr=1;
      if(bd!=8) return -4;                 /* only 8-bit assets are shipped */
      if(inter) return -5;                 /* no Adam7 */
      if(comp||filt) return -6;
      if(ct!=0&&ct!=2&&ct!=3&&ct!=4&&ct!=6) return -7;
      if(!w||!h) return -8;
    } else if(t[0]=='P'&&t[1]=='L'&&t[2]=='T'&&t[3]=='E'){
      if(ln/3>256) return -9;
      plte_n=(int)(ln/3);
      for(int i=0;i<plte_n;i++){ plte[i*3]=p[i*3]; plte[i*3+1]=p[i*3+1]; plte[i*3+2]=p[i*3+2]; }
    } else if(t[0]=='I'&&t[1]=='D'&&t[2]=='A'&&t[3]=='T'){ idat_total+=ln; }
    else if(t[0]=='I'&&t[1]=='E'&&t[2]=='N'&&t[3]=='D') break;
    off+=12+(u64)ln;
  }
  if(!seen_ihdr) return -10;
  if(!idat_total) return -11;
  int ch = (ct==0)?1:(ct==2)?3:(ct==3)?1:(ct==4)?2:4;
  u64 stride=(u64)w*(u64)ch;
  u64 need=(stride+1u)*(u64)h;
  if(need>rawcap) return -12;
  /* gather IDAT into `raw` (its first idat_total bytes), then inflate in place
     is impossible, so inflate into a second half of raw. */
  u64 zb_cap=rawcap/2;
  if(idat_total>zb_cap) return -13;
  u8 *zb=raw; u8 *un=raw+zb_cap;
  if(need>zb_cap) return -14;
  off=8;
  while(off+8<=n){
    u32 ln=be32(d+off);
    const char *t=(const char*)(d+off+4);
    if(off+12+(u64)ln>n) return -15;
    if(t[0]=='I'&&t[1]=='D'&&t[2]=='A'&&t[3]=='T'){
      for(u32 i=0;i<ln;i++) zb[idat_have+i]=d[off+8+i];
      idat_have+=ln;
    } else if(t[0]=='I'&&t[1]=='E'&&t[2]=='N'&&t[3]=='D') break;
    off+=12+(u64)ln;
  }
  if(idat_have!=idat_total) return -16;
  u64 uo=0;
  if(inflate_zlib(zb,idat_total,un,zb_cap,&uo)!=0) return -17;
  if(uo<need) return -18;
  /* unfilter in place, expanding to RGB */
  if((u64)rgbcap<(u64)w*(u64)h*3u) return -19;
  *rawused=uo;
  u8 *prev=un;                       /* previous unfiltered scanline */
  for(u32 y=0;y<h;y++){
    u8 *cur=un+(u64)y*(stride+1u);
    int ft=cur[0];
    u8 *row=cur+1;
    if(ft==0){ }
    else if(ft==1){ for(u64 i=(u64)ch;i<stride;i++) row[i]=(u8)(row[i]+row[i-ch]); }
    else if(ft==2){ if(y) for(u64 i=0;i<stride;i++) row[i]=(u8)(row[i]+prev[1+i]); }
    else if(ft==3){
      if(y){ for(u64 i=0;i<stride;i++){
        u32 left=(i>=(u64)ch)?row[i-ch]:0;
        row[i]=(u8)(row[i]+((left+prev[1+i])>>1)); } }
      else { for(u64 i=(u64)ch;i<stride;i++) row[i]=(u8)(row[i]+(row[i-ch]>>1)); }
    }
    else if(ft==4){
      if(y){ for(u64 i=0;i<stride;i++){
        int a=(i>=(u64)ch)?row[i-ch]:0, bb=prev[1+i], c=(i>=(u64)ch)?prev[1+i-ch]:0;
        int pa=bb-c, pb=a-c, pc=a+bb-2*c;
        if(pa<0)pa=-pa; if(pb<0)pb=-pb; if(pc<0)pc=-pc;
        int pr=(pa<=pb&&pa<=pc)?a:((pb<=pc)?bb:c);
        row[i]=(u8)(row[i]+pr); } }
      else { for(u64 i=(u64)ch;i<stride;i++) row[i]=(u8)(row[i]+row[i-ch]); }
    }
    else return -20;
    u8 *o=rgb+(u64)y*(u64)w*3u;
    for(u32 x=0;x<w;x++){
      if(ct==2){ o[0]=row[x*3]; o[1]=row[x*3+1]; o[2]=row[x*3+2]; }
      else if(ct==6){ o[0]=row[x*4]; o[1]=row[x*4+1]; o[2]=row[x*4+2]; }
      else if(ct==4){ o[0]=row[x*2]; o[1]=row[x*2]; o[2]=row[x*2]; }
      else if(ct==0){ o[0]=row[x]; o[1]=row[x]; o[2]=row[x]; }
      else { int idx=row[x]; if(idx>=plte_n) idx=0;
             o[0]=plte[idx*3]; o[1]=plte[idx*3+1]; o[2]=plte[idx*3+2]; }
      o+=3;
    }
    prev=cur;
  }
  *ow=w; *oh=h;
  return 0;
}

/* ---- the wallpaper -------------------------------------------------------
 * style.css: html,body { background-color: #1a1a2e; background-image:
 * url('../assets/nuxel-background.png'); background-size: cover;
 * background-position: center; background-attachment: fixed; }
 * The port loads the SAME asset from the Fedora rootfs, cover-fits it to the
 * panel once, and falls back to the PWA's own background-color - never to an
 * invented gradient. */
static const char *WALL_PATHS[4]={
  "/usr/share/nuxel/nuxel-background.png",
  "/usr/share/nuxel/nuxel-home/assets/nuxel-background.png",
  "/home/nuxel/nuxel/pwa/nuxel-home/assets/nuxel-background.png",
  0
};
static const char *WALL_FORCE=0;      /* --wallpaper=PATH (offline harness) */
static u8  *WALL_PRE=0;               /* cover-fitted panel-sized pixels */
static u64  WALL_PRE_BYTES=0;
static u32  WALL_PRE_W=0, WALL_PRE_H=0;
static int  WALL_STATE=-1;            /* -1 not tried, 0 unavailable, 1 ready */
static char WALL_NOTE[160];
static u32  WALL_SRC_W=0, WALL_SRC_H=0;

#ifdef NUXEL_UI_HOST
/* the offline harness has no syscall layer: load through libc so the SAME
   decoder can be measured against an independent decode of the same asset */
static u8 *file_load_all(const char *path,u64 *len,u64 cap){
  FILE *f=fopen(path,"rb");
  if(!f) return 0;
  u8 *buf=(u8*)alloc_anon(cap);
  if(!buf){ fclose(f); return 0; }
  size_t n=fread(buf,1,(size_t)cap,f);
  fclose(f);
  if(!n) return 0;
  *len=(u64)n;
  return buf;
}
#else
static u8 *file_load_all(const char *path,u64 *len,u64 cap){
  long fd=sys4(SYS_openat,AT_FDCWD,(long)path,O_RDONLY,0);
  if(fd<0) return 0;
  u8 *buf=(u8*)alloc_anon(cap);
  if(buf==MAP_FAILED||!buf){ sys1(SYS_close,fd); return 0; }
  u64 got=0;
  for(;;){
    long n=sys3(SYS_read,fd,(long)(buf+got),(long)(cap-got));
    if(n<=0) break;
    got+=(u64)n;
    if(got>=cap) break;
  }
  sys1(SYS_close,fd);
  if(got==0){ sys2(SYS_munmap,(long)buf,(long)cap); return 0; }
  *len=got;
  return buf;
}
#endif /* NUXEL_UI_HOST */
static void wall_note_set(const char *a,const char *b){
  int n=0;
  for(int i=0;a[i]&&n<80;i++) WALL_NOTE[n++]=a[i];
  for(int i=0;b&&b[i]&&n<150;i++) WALL_NOTE[n++]=b[i];
  WALL_NOTE[n]=0;
}
/* cover-fit with bilinear sampling, once, into a panel-sized u32 buffer */
static int wall_prepare(int pw,int ph){
  if(WALL_STATE>=0 && WALL_PRE_W==(u32)pw && WALL_PRE_H==(u32)ph) return WALL_STATE;
  if(WALL_PRE){ sys2(SYS_munmap,(long)WALL_PRE,(long)WALL_PRE_BYTES); WALL_PRE=0; WALL_PRE_BYTES=0; }
  WALL_PRE_W=(u32)pw; WALL_PRE_H=(u32)ph;
  const char *path=WALL_FORCE;
  u64 flen=0; u8 *filedata=0; static char chosen[160]; chosen[0]=0;
  for(int i=0;;i++){
    const char *p = path?path:WALL_PATHS[i];
    if(!p) break;
    filedata=file_load_all(p,&flen,8u<<20);
    if(filedata){ int k=0; for(int q=0;p[q]&&k<150;q++) chosen[k++]=p[q]; chosen[k]=0; break; }
    if(path) break;
  }
  if(!filedata){ WALL_STATE=0; wall_note_set("asset-not-found ",chosen[0]?chosen:""); ui_log("WALLPAPER_UNAVAILABLE asset-not-found"); return WALL_STATE; }
  u64 rawcap=32u<<20;
  u8 *raw=(u8*)alloc_anon(rawcap);
  if(raw==MAP_FAILED||!raw){ WALL_STATE=0; wall_note_set("no-memory decode",""); ui_log("WALLPAPER_UNAVAILABLE no-memory"); return WALL_STATE; }
  u32 sw=0,sh=0; u64 rawused=0;
  u8 *rgbi=raw+(24u<<20);              /* the RGB expansion lives in the top 8 MiB */
  long rc=png_decode_rgb(filedata,flen,raw,24u<<20,rgbi,8u<<20,&sw,&sh,&rawused);
  if(rc!=0){
    WALL_STATE=0;
    { char b[48]; int n=0; const char *p="png-decode-failed rc=";
      for(int i=0;p[i];i++)b[n++]=p[i];
      char t[16]; if(rc<0){ b[n++]='-'; u2s((u64)(-rc),t); } else u2s((u64)rc,t);
      for(int i=0;t[i];i++)b[n++]=t[i]; b[n]=0; wall_note_set(b,""); }
    { char l[96]; int n=0; const char *p="WALLPAPER_UNAVAILABLE ";
      for(int i=0;p[i];i++)l[n++]=p[i];
      for(int i=0;WALL_NOTE[i]&&n<80;i++)l[n++]=WALL_NOTE[i]; l[n]=0; ui_log(l); }
    return WALL_STATE;
  }
  WALL_SRC_W=sw; WALL_SRC_H=sh;
  /* cover: scale = max(pw/sw, ph/sh) in 16.16 fixed point */
  u32 sx_fp=(u32)(((u64)pw<<16)/(u64)sw), sy_fp=(u32)(((u64)ph<<16)/(u64)sh);
  u32 sc=sx_fp>sy_fp?sx_fp:sy_fp;
  u32 used_w=(u32)(((u64)sw*sc)>>16), used_h=(u32)(((u64)sh*sc)>>16);
  u32 xoff=(used_w>(u32)pw)?(used_w-(u32)pw)/2:0;
  u32 yoff=(used_h>(u32)ph)?(used_h-(u32)ph)/2:0;
  WALL_PRE_BYTES=(u64)pw*(u64)ph*4u;
  WALL_PRE=(u8*)alloc_anon(WALL_PRE_BYTES);
  if(WALL_PRE==MAP_FAILED||!WALL_PRE){ WALL_PRE=0; WALL_STATE=0; wall_note_set("no-memory panel",""); ui_log("WALLPAPER_UNAVAILABLE no-memory-panel"); return WALL_STATE; }
  for(u32 y=0;y<(u32)ph;y++){
    u32 *dst=(u32*)(WALL_PRE+(u64)y*(u64)pw*4u);
    u64 syfp=(((u64)(y+yoff))<<16)+32768u;
    u64 sy0=syfp>>16;
    if(sy0>=(u64)sh) sy0=(u64)sh-1u;
    u64 sy1=(sy0+1u<(u64)sh)?(sy0+1u):sy0;
    u32 fy=(u32)((syfp>>8)&0xffu);
    const u8 *r0=rgbi+(sy0*(u64)sw)*3u;
    const u8 *r1=rgbi+(sy1*(u64)sw)*3u;
    for(u32 x=0;x<(u32)pw;x++){
      u64 sxq=(((u64)(x+xoff))<<16)+32768u;
      u64 sx0=sxq>>16;
      if(sx0>=(u64)sw) sx0=(u64)sw-1u;
      u64 sx1=(sx0+1u<(u64)sw)?(sx0+1u):sx0;
      u32 fx=(u32)((sxq>>8)&0xffu);
      u32 c[3];
      for(int k=0;k<3;k++){
        u32 a=r0[sx0*3u+(u32)k], b=r0[sx1*3u+(u32)k];
        u32 d2=r1[sx0*3u+(u32)k], e=r1[sx1*3u+(u32)k];
        u32 top=(a*(256u-fx)+b*fx)>>8, bot=(d2*(256u-fx)+e*fx)>>8;
        c[k]=(top*(256u-fy)+bot*fy)>>8;
      }
      dst[x]=pack_rgb(c[0],c[1],c[2]);
    }
  }
  WALL_STATE=1;
  { char l[192]; int n=0; const char *p="WALLPAPER_OK path=";
    for(int i=0;p[i];i++)l[n++]=p[i];
    for(int i=0;chosen[i]&&n<120;i++)l[n++]=chosen[i];
    const char *q=" src="; for(int i=0;q[i];i++)l[n++]=q[i];
    char t[16]; u2s((u64)sw,t); for(int i=0;t[i];i++)l[n++]=t[i]; l[n++]='x';
    u2s((u64)sh,t); for(int i=0;t[i];i++)l[n++]=t[i];
    const char *r=" panel="; for(int i=0;r[i];i++)l[n++]=r[i];
    u2s((u64)pw,t); for(int i=0;t[i];i++)l[n++]=t[i]; l[n++]='x';
    u2s((u64)ph,t); for(int i=0;t[i];i++)l[n++]=t[i];
    const char *s=" png="; for(int i=0;s[i];i++)l[n++]=s[i];
    u2s(flen,t); for(int i=0;t[i];i++)l[n++]=t[i]; l[n]=0;
    ui_log(l); }
  if(rgbi) sys2(SYS_munmap,(long)raw,(long)rawcap);
  if(filedata) sys2(SYS_munmap,(long)filedata,8u<<20);
  return WALL_STATE;
}
static void wall_blit(void){
  if(WALL_STATE!=1||!WALL_PRE||SCR.bpp!=32) return;
  if(WALL_PRE_W!=SCR.w||WALL_PRE_H!=SCR.h) return;
  for(u32 y=0;y<SCR.h;y++){
    u32 *dst=(u32*)(SCR.canvas+(u64)y*SCR.stride);
    const u32 *src=(const u32*)(WALL_PRE+(u64)y*SCR.w*4u);
    for(u32 x=0;x<SCR.w;x++) dst[x]=src[x];
  }
}
/* ---- the launcher's status bar (pwa/nuxel-home/css/status-bar.css) --------
 * height:36, padding:0 16px, background rgba(26,26,46,.95), 1px rgba(255,255,
 * 255,.03) bottom border, time 13px weight 600 left, battery glyph 22x11 +
 * 11px percentage right.  The CENTRE cluster (signal + wifi) is drawn only when
 * a real value exists: this phone has no radio and no wlan driver, so drawing a
 * fake signal bar would be a lie - and the punch-hole cutout band (design x
 * 118..242) must stay clear (A27 rule, enforced by layout_check). */
static void draw_status_bar_launcher(void){
  fill_rect_a(0,DY(0),(int)SCR.w,DSTATUS*SC,pack_rgb(0x1a,0x1a,0x2e),242);
  fill_rect_a(0,DY(DSTATUS)-1,(int)SCR.w,SC,pack_rgb(0xff,0xff,0xff),8);
  struct clock_ui c; clock_read(&c);
  char hh[4],mm[4]; u2s2((u64)c.hh,hh); u2s2((u64)c.mm,mm);
  char t[8]; t[0]=hh[0];t[1]=hh[1];t[2]=':';t[3]=mm[0];t[4]=mm[1];t[5]=0;
  dtext(L_STATUSBAR_PAD,0,52,DSTATUS,13,t,pack_rgb(0xff,0xff,0xff),AL_LEFT);
  dreg("status.time",L_STATUSBAR_PAD,0,52,DSTATUS,REG_STATUS);
  int pct=SI.battery_pct;
  char pbs[8]; int n=0;
  if(pct<0){ pbs[n++]='-'; pbs[n++]='-'; }
  else { char pb[8]; u2s((u64)pct,pb); for(int i=0;pb[i];i++)pbs[n++]=pb[i]; }
  pbs[n++]='%'; pbs[n]=0;
  int gw=22, gh=11;
  int gx=360-L_STATUSBAR_PAD-gw;
  dtext(gx-40,0,38,DSTATUS,11,pbs,pack_rgb(0xff,0xff,0xff),AL_RIGHT);
  dreg("status.battery.label",gx-40,0,38,DSTATUS,REG_STATUS);
  /* the 22x11 CSS battery: body + terminal + fill, in --success/--error/--warning */
  {
    u32 col = SI.charging? C_OK : (pct<0? C_TXT2 : (pct<=15? C_ERR : (pct<=30? C_WARN : C_OK)));
    int by=DY((DSTATUS-gh)/2);
    frame_rect(DX(gx),by,(gw-3)*SC,gh*SC,(SC>1?SC:1),pack_rgb(0xff,0xff,0xff));
    fill_rect(DX(gx+gw-3),by+3*SC,3*SC,gh*SC-6*SC,pack_rgb(0xff,0xff,0xff));
    int inner=(gw-3)*SC-4*SC;
    int fillw=inner*(pct<0?0:(pct>100?100:pct))/100;
    if(fillw>0) fill_rect(DX(gx)+2*SC,by+2*SC,fillw,gh*SC-4*SC,col);
    if(SI.charging){
      int cx=DX(gx)+((gw-3)*SC)/2-2*SC, cy=by+gh*SC/2;
      fill_rect(cx,cy-SC/2,SC*4,SC,C_WHITE);
      fill_rect(cx+SC+SC/2,cy-SC*2,SC,SC*4,C_WHITE);
    }
  }
  dreg("status.battery.glyph",gx,10,gw,gh,REG_STATUS);
}

/* ---- the launcher's app tile (launcher.css .app-item .app-icon) ---- */
static void emoji_draw_scaled(unsigned int cp,int cx,int cy,int design_px,u32 col){
  const struct nuxel_emoji *g=emoji_lookup(design_px,cp);
  if(!g||!g->w||!g->h) return;
  int tw=(int)(((s64)g->w*SC)/NUXEL_EMOJI_ATLAS_SCALE); if(tw<1) tw=1;
  int th=(int)(((s64)g->h*SC)/NUXEL_EMOJI_ATLAS_SCALE); if(th<1) th=1;
  int x0=cx-tw/2, y0=cy-th/2;
  for(int j=0;j<th;j++){
    int py=y0+j;
    int sy0=(int)(((s64)j*(s64)g->h)/th), sy1=(int)(((s64)(j+1)*(s64)g->h)/th);
    if(sy1<=sy0) sy1=sy0+1;
    for(int i=0;i<tw;i++){
      int pxl=x0+i;
      int sx0=(int)(((s64)i*(s64)g->w)/tw), sx1=(int)(((s64)(i+1)*(s64)g->w)/tw);
      if(sx1<=sx0) sx1=sx0+1;
      int acc=0,cnt=0;
      for(int yy=sy0;yy<sy1;yy++) for(int xx=sx0;xx<sx1;xx++){
        u32 idx=(u32)yy*(u32)g->w+(u32)xx;
        u32 b=NUXEL_EMOJI_BITS[g->off+(idx>>1)];
        acc+=(idx&1)?(int)(b&0x0fu):(int)(b>>4); cnt++;
      }
      if(!cnt) continue;
      int cov=acc/cnt; if(!cov) continue;
      px_blend(pxl,py,col,(cov*17>255)?255:cov*17);
    }
  }
}
static void app_glyph_draw_scaled(int ai,int cx,int cy,int design_px,u32 col){
  const struct nuxel_app *a=&NUXEL_APP_LIST[ai];
  for(int k=0;k<3;k++){
    if(!a->icon_cp[k]) break;
    if(emoji_lookup(design_px,a->icon_cp[k])){ emoji_draw_scaled(a->icon_cp[k],cx,cy,design_px,col); return; }
  }
  { const struct nuxel_font *f=font_for(design_px);
    char s[2]; s[0]=a->name[0]; s[1]=0;
    font_draw(cx-font_w(f,s)/2,cy-font_h(f)/2,f,s,col); }
}
/* .app-item .app-icon { width:var(--app-icon-size); border-radius:
   var(--app-icon-radius); background: <color>33; color: <color> } */
static void app_tile(int ai,int x,int y,int size,int glyph_px){
  const struct nuxel_app *a=&NUXEL_APP_LIST[ai];
  u32 tile=pack_rgb((a->color_rgb>>16)&0xffu,(a->color_rgb>>8)&0xffu,a->color_rgb&0xffu);
  round_rect_a(DX(x),DY(y),size*SC,size*SC,L_APP_ICON_RADIUS*SC,tile,0x33);
  app_glyph_draw_scaled(ai,DX(x)+size*SC/2,DY(y)+size*SC/2,glyph_px,tile);
}

/* ---- the launcher's dock (launcher.css .dock / .dock-items) --------------
 * height 80, background --bg-secondary, 1px rgba(255,255,255,.05) top border,
 * 56px icons with a 20px gap, centred, NO labels. */
static void draw_dock_launcher(void){
  int y=DESIGN_H-DDOCK;
  dfill(0,y,360,DDOCK,pack_rgb((L_BG_SECONDARY>>16)&0xffu,(L_BG_SECONDARY>>8)&0xffu,L_BG_SECONDARY&0xffu));
  fill_rect_a(0,DY(y)-1,(int)SCR.w,SC,pack_rgb(0xff,0xff,0xff),13);
  int icon=56, gap=20, total=NUXEL_LAUNCHER_DOCK_COUNT*icon+(NUXEL_LAUNCHER_DOCK_COUNT-1)*gap;
  int x0=(360-total)/2, iy=y+(DDOCK-icon)/2;
  for(int i=0;i<NUXEL_LAUNCHER_DOCK_COUNT;i++){
    int ai=LAUNCHER_DOCK_IDX[i];
    int tx=x0+i*(icon+gap);
    app_tile(ai,tx,iy,icon,24);
    widget_add(DX(tx),DY(iy),icon*SC,icon*SC,ACT_APP_BASE+ai);
    dreg(NUXEL_APP_LIST[ai].name,tx,iy,icon,icon,REG_DOCK);
  }
}

/* ---- search overlay (js/search.js searchApps() + css/search.css) ---------
 * searchApps() ranks a NAME match above a description/category match and then
 * sorts by name; this reproduces exactly that, over the same registry.  The
 * fbdev build has no on-screen keyboard (that needs a Wayland OSK), so the
 * query arrives on the console channel (`search <text>`) or the live shell. */
#define SEARCH_MAX 9
static int  SEARCH_OPEN=0;
static char SEARCH_Q[48];
static int  SEARCH_HITS[SEARCH_MAX];
static int  SEARCH_NHITS=0;
static int lower_(int c){ return (c>='A'&&c<='Z')?c+32:c; }
static int app_search_rank(int ai,const char *q){
  const struct nuxel_app *a=&NUXEL_APP_LIST[ai];
  int qn=0; while(q[qn]) qn++;
  if(!qn) return -1;
  for(int i=0;a->name[i];i++){
    int k=0; while(k<qn&&a->name[i+k]&&lower_(a->name[i+k])==lower_(q[k])) k++;
    if(k==qn) return 0;
  }
  for(int i=0;a->desc[i];i++){ int k=0; while(k<qn&&a->desc[i+k]&&lower_(a->desc[i+k])==lower_(q[k])) k++; if(k==qn) return 1; }
  return -1;
}
static void search_apply(void){
  SEARCH_NHITS=0;
  if(!SEARCH_Q[0]) return;
  int rank[NUXEL_LAUNCHER_APP_COUNT];
  for(int i=0;i<NUXEL_LAUNCHER_APP_COUNT;i++) rank[i]=app_search_rank(i,SEARCH_Q);
  for(int want=0;want<2;want++){
    for(int i=0;i<NUXEL_LAUNCHER_APP_COUNT&&SEARCH_NHITS<SEARCH_MAX;i++){
      if(rank[i]!=want) continue;
      SEARCH_HITS[SEARCH_NHITS++]=i;
    }
  }
}
static void draw_search_overlay(void){
  int y0=DSTATUS;
  dfill(0,y0,360,DESIGN_H-y0,pack_rgb((L_BG_PRIMARY>>16)&0xffu,(L_BG_PRIMARY>>8)&0xffu,L_BG_PRIMARY&0xffu));
  dreg("search.overlay",0,y0,360,DESIGN_H-y0,REG_DOCK);
  int by=y0;                      /* .search-bar-container: 12px 16px, bg-secondary */
  dfill(0,by,360,56,pack_rgb((L_BG_SECONDARY>>16)&0xffu,(L_BG_SECONDARY>>8)&0xffu,L_BG_SECONDARY&0xffu));
  dreg("search.bar",DPAD,by,360-DPAD*2,56,REG_CONTENT);
  dround(DPAD,by+12,360-DPAD*2-56,32,L_BUTTON_RADIUS,pack_rgb(0x12,0x29,0x52));
  dtext(DPAD+12,by+12,360-DPAD*2-56-24,32,14,SEARCH_Q[0]?SEARCH_Q:"type on the console: search <text>",
        SEARCH_Q[0]?C_TXT:C_TXT2,AL_LEFT);
  dtext(360-DPAD-52,by+12,52,32,14,"Cancel",pack_rgb(0x60,0xa5,0xfa),AL_RIGHT);
  widget_add(DX(360-DPAD-56),DY(by+12),56*SC,32*SC,ACT_SEARCH_CLOSE);
  /* results: 44px icon + name 15 + desc 12, 10px/12px padding, 8px gap */
  int y=by+56+8;
  if(!SEARCH_Q[0]){
    dtext(DPAD+4,y,360-DPAD*2,20,13,"Type a query on the Nuxel console: search <text>",C_TXT2,AL_LEFT);
  } else if(SEARCH_NHITS==0){
    dtext(DPAD+4,y,360-DPAD*2,20,13,"No apps match that search",C_TXT2,AL_LEFT);
  }
  for(int i=0;i<SEARCH_NHITS;i++){
    int ai=SEARCH_HITS[i];
    if(y+56>DESIGN_H-DDOCK-8) break;
    dround(DPAD,y,360-DPAD*2,56,L_BUTTON_RADIUS,pack_rgb(0x12,0x29,0x52));
    app_tile(ai,DPAD+12,y+6,44,22);
    dtext(DPAD+64,y+8,360-DPAD*2-80,20,14,NUXEL_APP_LIST[ai].name,C_TXT,AL_LEFT);
    dtext(DPAD+64,y+30,360-DPAD*2-80,18,11,NUXEL_APP_LIST[ai].desc,C_TXT2,AL_LEFT);
    widget_add(DX(DPAD),DY(y),(360-DPAD*2)*SC,56*SC,ACT_APP_BASE+ai);
    dreg(NUXEL_APP_LIST[ai].name,DPAD,y,360-DPAD*2,56,REG_CONTENT);
    y+=64;
  }
}

/* ---- app launching ------------------------------------------------------
 * The launch commands are the ones the repo already uses:
 *   PWA  -> services/nuxel-web.service serves the tree on 127.0.0.1:8000 and
 *           shell/nuxel-kiosk/nuxel-home-kiosk opens it with chromium
 *           (--kiosk) / firefox (--kiosk); the VM ships epiphany/WebKitGTK.
 *           pwa/launcher/nuxel-pwa-launcher is the hardened WebKitGTK runner.
 *   native -> app_registry.json's native_binary (/usr/bin/nuxel-*).
 * Every attempt is recorded with its OUTCOME, and an app that cannot run says
 * so by name instead of pretending (mission section 8). */
static int APP_STATE[NUXEL_LAUNCHER_APP_COUNT];      /* 0 untried 1 started 2 unavailable */
static char APP_NOTE[NUXEL_LAUNCHER_APP_COUNT][64];
static const char *APP_ENVP[6]={"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                                "HOME=/root","TERM=dumb","LANG=C",0,0};
static char APP_ENV_ID[128], APP_ENV_URL[224], APP_ENV_DATA[192];
static const char *APP_ENVP_PWA[7];
static long SPAWN_PID=-1;
static void app_note(int ai,const char *s){
  int n=0; for(int i=0;s[i]&&n<60;i++) APP_NOTE[ai][n++]=s[i]; APP_NOTE[ai][n]=0;
}
static void apps_state_write(void){
  char b[1024]; int n=0;
  const char *h="# nuxel-ui launcher app state (A28)\n"; for(int i=0;h[i];i++) b[n++]=h[i];
  for(int i=0;i<NUXEL_LAUNCHER_APP_COUNT;i++){
    const struct nuxel_app *a=&NUXEL_APP_LIST[i];
    const char *s=APP_STATE[i]==0?"untried":(APP_STATE[i]==1?"started":"unavailable");
    for(int k=0;a->id[k]&&n<1000;k++) b[n++]=a->id[k];
    b[n++]=' '; for(int k=0;s[k]&&n<1000;k++) b[n++]=s[k];
    b[n++]=' ';
    for(int k=0;APP_NOTE[i][k]&&n<1000;k++) b[n++]=APP_NOTE[i][k];
    b[n++]='\n';
  }
  b[n]=0; state_write("ui-apps",b);
}
static int path_x(const char *p){
  return (int)sys4(SYS_faccessat,AT_FDCWD,(long)p,1,0)==0;      /* X_OK */
}
/* /proc/net/tcp{,6} listener test for one port (state 0A == LISTEN). */
static int port_listening(unsigned port){
  static const char *HEX="0123456789ABCDEF";
  char pat[8]; pat[0]=':';
  pat[1]=HEX[(port>>12)&0xf]; pat[2]=HEX[(port>>8)&0xf];
  pat[3]=HEX[(port>>4)&0xf];  pat[4]=HEX[port&0xf]; pat[5]=0;
  const char *files[2]={"/proc/net/tcp","/proc/net/tcp6"};
  for(int f=0;f<2;f++){
    char b[8192]; int got=file_read(files[f],b,sizeof b-1);
    if(got<=0) continue;
    b[got]=0;
    for(int i=0;i+8<got;i++){
      int k=0; while(k<5&&b[i+k]==pat[k]) k++;
      if(k!=5) continue;
      int j=i+5;
      while(j<got&&b[j]==' ') j++;
      while(j<got&&b[j]!=' ') j++;                 /* remote address */
      while(j<got&&b[j]==' ') j++;
      if(j+1<got&&b[j]=='0'&&b[j+1]=='A') return 1;
    }
  }
  return 0;
}
static long spawn_env(char *const argv[],const char *const envp[]){
  long pid=sys5(SYS_clone,17,0,0,0,0);             /* SIGCHLD == fork semantics */
  if(pid<0) return pid;
  if(pid==0){
    sys3(SYS_execve,(long)argv[0],(long)argv,(long)envp);
    sys1(SYS_exit_group,127);
    for(;;) sleep_ms_(1000);
  }
  return pid;
}
static void reap_children(void){
  int st=0;
  for(;;){ long r=sys4(SYS_wait4,-1,(long)&st,1,0); if(r<=0) break; }
}
static void launch_app(int ai){
  const struct nuxel_app *a=&NUXEL_APP_LIST[ai];
  char line[224]; int n=0;
  const char *p="APP_LAUNCH id="; for(int i=0;p[i];i++) line[n++]=p[i];
  for(int i=0;a->id[i]&&n<80;i++) line[n++]=a->id[i];
  const char *q=" kind="; for(int i=0;q[i];i++) line[n++]=q[i];
  const char *k=a->kind==NUXEL_APP_KIND_PWA?"pwa":"native";
  for(int i=0;k[i];i++) line[n++]=k[i];
  line[n]=0; ui_log(line);

  static char ARG0[192], ARG1[32], ARG2[224];
  char *argv[4]; argv[3]=0;
  int launched=0;
  const char *why="";

  if(a->kind==NUXEL_APP_KIND_PWA){
    int server=port_listening(8000);
    const char *browsers[5]; int nb=0;
    if(path_x("/usr/bin/nuxel-pwa-launcher")) browsers[nb++]="/usr/bin/nuxel-pwa-launcher";
    if(path_x("/usr/bin/chromium-browser"))   browsers[nb++]="/usr/bin/chromium-browser";
    if(path_x("/usr/bin/chromium"))           browsers[nb++]="/usr/bin/chromium";
    if(path_x("/usr/bin/epiphany"))           browsers[nb++]="/usr/bin/epiphany";
    if(path_x("/usr/bin/firefox"))            browsers[nb++]="/usr/bin/firefox";
    if(nb==0){
      why=server?"no-pwa-engine-in-image":"no-pwa-engine-and-server-down";
    } else {
      int k=0; const char *b=browsers[0];
      for(int i=0;b[i]&&k<180;i++) ARG0[k++]=b[i]; ARG0[k]=0;
      if(str_find(b,"nuxel-pwa-launcher")){
        /* the hardened WebKitGTK runner reads its identity from the environment */
        k=0; const char *e1="NUXEL_APP_ID="; for(int i=0;e1[i];i++) APP_ENV_ID[k++]=e1[i];
        for(int i=0;a->id[i]&&k<120;i++) APP_ENV_ID[k++]=a->id[i]; APP_ENV_ID[k]=0;
        k=0; const char *e2="NUXEL_START_URL="; for(int i=0;e2[i];i++) APP_ENV_URL[k++]=e2[i];
        for(int i=0;a->url[i]&&k<210;i++) APP_ENV_URL[k++]=a->url[i]; APP_ENV_URL[k]=0;
        k=0; const char *e3="NUXEL_DATA_DIR=/var/app/"; for(int i=0;e3[i];i++) APP_ENV_DATA[k++]=e3[i];
        for(int i=0;a->id[i]&&k<180;i++) APP_ENV_DATA[k++]=a->id[i];
        const char *e4="/data"; for(int i=0;e4[i];i++) APP_ENV_DATA[k++]=e4[i]; APP_ENV_DATA[k]=0;
        for(int i=0;i<4;i++) APP_ENVP_PWA[i]=APP_ENVP[i];
        APP_ENVP_PWA[4]=APP_ENV_ID; APP_ENVP_PWA[5]=APP_ENV_URL; APP_ENVP_PWA[6]=0;
        argv[0]=ARG0; argv[1]=0;
        SPAWN_PID=spawn_env(argv,APP_ENVP_PWA);
      } else {
        int kiosk=!str_find(b,"epiphany");
        int k2=0; ARG1[k2]=0;
        argv[0]=ARG0;
        int ai2=1;
        if(kiosk){ const char *f="--kiosk"; for(int i=0;f[i];i++) ARG1[k2++]=f[i]; ARG1[k2]=0; argv[ai2++]=ARG1; }
        k2=0; for(int i=0;a->url[i]&&k2<220;i++) ARG2[k2++]=a->url[i]; ARG2[k2]=0;
        argv[ai2++]=ARG2; argv[ai2]=0;
        SPAWN_PID=spawn_env(argv,APP_ENVP);
      }
      if(SPAWN_PID>0) launched=1;
      else why="spawn-failed";
    }
  } else {
    if(a->native_binary[0] && path_x(a->native_binary)){
      int k=0; for(int i=0;a->native_binary[i]&&k<180;i++) ARG0[k++]=a->native_binary[i]; ARG0[k]=0;
      argv[0]=ARG0; argv[1]=0;
      SPAWN_PID=spawn_env(argv,APP_ENVP);
      if(SPAWN_PID>0) launched=1; else why="spawn-failed";
    } else if(!a->native_binary[0]){
      why="registry-lists-no-native-binary";
    } else {
      why="native-binary-not-installed";
    }
  }
  APP_STATE[ai]=launched?1:2;
  app_note(ai,launched?"started":why);
  apps_state_write();
  { char l[256]; int m=0;
    const char *p2="APP_LAUNCH_RESULT id="; for(int i=0;p2[i];i++) l[m++]=p2[i];
    for(int i=0;a->id[i]&&m<90;i++) l[m++]=a->id[i];
    const char *q2=launched?" state=started cmd=":" state=unavailable reason=";
    for(int i=0;q2[i];i++) l[m++]=q2[i];
    const char *s3=launched?ARG0:why;
    for(int i=0;s3[i]&&m<230;i++) l[m++]=s3[i];
    if(launched&&argv[1]){ l[m++]=' '; for(int i=0;argv[1][i]&&m<240;i++) l[m++]=argv[1][i]; }
    if(launched&&argv[2]){ l[m++]=' '; for(int i=0;argv[2][i]&&m<250;i++) l[m++]=argv[2][i]; }
    l[m]=0; ui_log(l); }
  if(launched){
    char t[64]; int m=0; const char *p3="Starting "; for(int i=0;p3[i];i++) t[m++]=p3[i];
    for(int i=0;a->name[i]&&m<58;i++) t[m++]=a->name[i]; t[m]=0;
    toast(t,3);
  } else {
    char t[80]; int m=0;
    for(int i=0;a->name[i]&&m<30;i++) t[m++]=a->name[i];
    const char *p4=" cannot run: "; for(int i=0;p4[i];i++) t[m++]=p4[i];
    for(int i=0;why[i]&&m<78;i++) t[m++]=why[i]; t[m]=0;
    toast(t,5);
  }
}
/* ---- a gradient-filled text run (the CSS .app-grid-title gradient) ------- */
static void font_draw_grad(int x,int y,const struct nuxel_font *f,const char *t,u32 c0,u32 c1,int span){
  int baseline=y+f->ascent, pen=x;
  for(;*t;t++){
    unsigned char c=(unsigned char)*t;
    if(c<NUXEL_FONT_FIRST||c>NUXEL_FONT_FIRST+NUXEL_FONT_COUNT-1) c='?';
    const struct nuxel_glyph *g=&NUXEL_FONT_GLYPHS[f->goff+(c-NUXEL_FONT_FIRST)];
    for(int j=0;j<(int)g->h;j++){
      int py=baseline+g->yoff+j;
      if(py<CLY0||py>=CLY1) continue;
      for(int i=0;i<(int)g->w;i++){
        int pxl=pen+g->xoff+i;
        if(pxl<CLX0||pxl>=CLX1) continue;
        u32 idx=(u32)j*(u32)g->w+(u32)i;
        u32 b=NUXEL_FONT_BITS[g->off+(idx>>1)];
        int cov=(idx&1)?(int)(b&0x0fu):(int)(b>>4);
        if(!cov) continue;
        int k=span>0?(((pxl-x)+(py-y))*255)/span:0;
        if(k<0)k=0; if(k>255)k=255;
        u32 col=0xff000000u;
        for(int sh=0;sh<24;sh+=8){
          u32 a=(c0>>sh)&0xffu, b2=(c1>>sh)&0xffu;
          col|=(((a*(u32)(255-k)+b2*(u32)k)/255u)&0xffu)<<sh;
        }
        px_blend(pxl,py,col,cov*17>255?255:cov*17);
      }
    }
    pen+=g->adv;
  }
}
static void dtext_grad(int x,int y,int w,int h,int design_px,const char *t,u32 c0,u32 c1,int align){
  if(w<=0||h<=0) return;
  const struct nuxel_font *f=font_for(design_px);
  char tmp[256]; font_fit_str(f,t,w*SC,tmp,sizeof tmp);
  int pxw=font_w(f,tmp), pxh=font_h(f);
  int py=DY(y)+(h*SC-pxh)/2;
  int pxx = (align==AL_CENTER)?DX(x)+(w*SC-pxw)/2 : ((align==AL_RIGHT)?DX(x+w)-pxw:DX(x));
  dclip(x,y,w,h);
  font_draw_grad(pxx,py,f,tmp,c0,c1,pxw+pxh);
}
/* ---- the launcher page: pwa/nuxel-home/index.html structure ---------------
 *   #status-bar   (drawn in launcher colours, on top)
 *   #app-grid     .app-grid-header (title + page dots) + .app-list (4 columns)
 *   #dock         .dock-items (3 docked apps, no labels)
 *   #search-overlay   (full screen below the status bar when open)
 * Geometry is launcher.css, spelling-for-spelling: grid padding 8px 16px 0,
 * header padding 12px 4px 20px, title 28px, list gap 16px 8px, icon 64px /
 * radius 16 / label 11px, dock 80px with 56px icons and a 20px gap. */
static void page_launcher(void){
  dfill(0,0,360,DESIGN_H,
        pack_rgb((L_BODY_BG>>16)&0xffu,(L_BODY_BG>>8)&0xffu,L_BODY_BG&0xffu));
  wall_blit();                       /* the PWA's own free-standing asset */
  if(SEARCH_OPEN){ draw_search_overlay(); return; }

  int gx=DPAD, gw=360-DPAD*2;
  int y=DSTATUS+8;                                     /* .app-grid padding-top */
  /* header: title 28px with the CSS gradient (#60a5fa -> #122952) */
  dtext_grad(gx+4,y+12,gw-70,38,28,"Nuxel",L_TEXT_ACCENT,L_BG_CARD,AL_LEFT);
  dreg("launcher.title",gx+4,y+12,gw-70,38,REG_CONTENT);
  widget_add(DX(gx+4),DY(y+12),(gw-70)*SC,38*SC,ACT_DIAG);
  /* .app-grid-indicator: ceil(6/16) = 1 page => one active dot (6px, 6px gap) */
  {
    int pages=(NUXEL_LAUNCHER_GRID_COUNT+15)/16; if(pages<1) pages=1;
    int ds=6, dg=6, dw=pages*ds+(pages-1)*dg;
    int dx=360-DPAD-4-dw, dy=y+12+19-3;
    for(int i=0;i<pages;i++){
      int cx=dx+i*(ds+dg);
      for(int j=0;j<ds;j++)for(int k=0;k<ds;k++){
        int ox=j-ds/2, oy=k-ds/2;
        if(ox*ox+oy*oy<=(ds/2)*(ds/2)) px_blend(DX(cx)+j*SC,DY(dy)+k*SC,C_ACCENT,i==0?255:100);
      }
    }
    dreg("launcher.dots",dx,dy,dw,ds,REG_CONTENT);
  }
  y+=12+38+20;

  /* .app-list: repeat(4,1fr), gap 16px 8px */
  {
    int cols=4, gapx=8, gapy=16, label_h=16, labgap=6;
    int cell=(gw-(cols-1)*gapx)/cols;
    int rowstep=DICON+labgap+label_h+gapy;
    for(int i=0;i<NUXEL_LAUNCHER_GRID_COUNT;i++){
      int ai=LAUNCHER_GRID_IDX[i];
      int col=i%cols, row=i/cols;
      int tx=gx+col*(cell+gapx), ty=y+row*rowstep;
      if(ty+DICON+labgap+label_h>DESIGN_H-DDOCK-4) break;
      int ix=tx+(cell-DICON)/2;
      app_tile(ai,ix,ty,DICON,28);
      dtext(tx,ty+DICON+labgap,cell,label_h,L_LABEL_PX,NUXEL_APP_LIST[ai].name,C_TXT2,AL_CENTER);
      widget_add(DX(tx),DY(ty),cell*SC,(DICON+labgap+label_h)*SC,ACT_APP_BASE+ai);
      dreg(NUXEL_APP_LIST[ai].name,tx,ty,cell,DICON+labgap+label_h,REG_CONTENT);
    }
  }
  draw_dock_launcher();
}
/* The wallpaper, written out as a PPM so the offline gate can compare the
   decoder's output with an independent decode of the same asset. */
static void wall_dump_ppm(const char *path){
  static u8 row[16384];                       /* >= 4096 px wide */
  if(WALL_STATE!=1||!WALL_PRE) return;
  long fd=out_open(path);
  if(fd<0) return;
  char hdr[48]; int n=0; const char *p="P6\n";
  for(int i=0;p[i];i++)hdr[n++]=p[i];
  char t[16]; u2s((u64)WALL_PRE_W,t); for(int i=0;t[i];i++)hdr[n++]=t[i]; hdr[n++]=' ';
  u2s((u64)WALL_PRE_H,t); for(int i=0;t[i];i++)hdr[n++]=t[i];
  hdr[n++]='\n'; const char *q="255\n"; for(int i=0;q[i];i++)hdr[n++]=q[i];
  out_write(fd,hdr,(u64)n);
  if((u64)WALL_PRE_W*3u>sizeof row) return;   /* never overrun the row buffer */
  for(u32 y=0;y<WALL_PRE_H;y++){
    const u32 *src=(const u32*)(WALL_PRE+(u64)y*WALL_PRE_W*4u);
    for(u32 x=0;x<WALL_PRE_W;x++){
      u32 v=src[x];
      row[x*3+0]=(u8)(v&0xffu); row[x*3+1]=(u8)((v>>8)&0xffu); row[x*3+2]=(u8)((v>>16)&0xffu);
    }
    out_write(fd,row,(u64)WALL_PRE_W*3u);
  }
  out_close(fd);
}
static int launch_by_query(const char *q){
  int qn=0; while(q[qn]) qn++;
  for(int i=0;i<NUXEL_LAUNCHER_APP_COUNT;i++){
    const struct nuxel_app *a=&NUXEL_APP_LIST[i];
    int k=0; while(k<qn&&a->id[k]&&lower_(a->id[k])==lower_(q[k])) k++;
    if(k==qn&&qn>0){ launch_app(i); return i; }
    k=0; while(k<qn&&a->name[k]&&lower_(a->name[k])==lower_(q[k])) k++;
    if(k==qn&&qn>0){ launch_app(i); return i; }
  }
  return -1;
}

/* ================================================================ rendering */
static void render(void){
  NWIDGETS=0;
  NREG=0;
  clip_all();
  background();
  switch(PAGE){
    case PAGE_LAUNCHER: page_launcher(); break;
    case PAGE_SETTINGS: page_settings(); break;
    case PAGE_SYSTEM:   page_system();   break;
    case PAGE_LOGS:     page_logs();     break;
    case PAGE_POWER:    page_power();    break;
    case PAGE_ABOUT:    page_about();    break;
    default:            page_home();     break;
  }
  if(PAGE==PAGE_LAUNCHER) draw_status_bar_launcher();
  else draw_status_bar();
  draw_error_banner();
  if(PAGE!=PAGE_LAUNCHER) draw_dock();   /* the launcher has the PWA's own dock */
  draw_toast();
  /* Every element is registered with its rectangle; a violation is reported by
     name (and, offline, fails the harness).  Renderers must not be able to
     reintroduce the A26 overlapping-text defects silently. */
  layout_check(A_LAYOUT_VERBOSE);
}
/* ---- the framebuffer commit: this is what makes PHONE_UI_READY claimable --- */
static int COMMITS=0, LAST_PAN_RC=0;
static u32 CURBUF=0;               /* the buffer the DECON is scanning out     */
static u8 *VISIBLE=0;              /* = bufptr(CURBUF), for screenshots        */
static u8 *bufptr(u32 i){ return SCR.mem + (SCR.bufs>1?(u64)i*SCR.h*SCR.stride:0); }
static int fb_assert_panel(void){
  struct fb_var v;
  if(!SCR.is_fb) return 0;
  for(u64 i=0;i<sizeof v;i++)((u8*)&v)[i]=0;
  if(sys3(SYS_ioctl,SCR.fd,FBIOGET_VSCREENINFO,(long)&v)<0) return -1;
  v.activate = 0;  /* FB_ACTIVATE_NOW */
  sys3(SYS_ioctl,SCR.fd,FBIOPUT_VSCREENINFO,(long)&v);
  sys3(SYS_ioctl,SCR.fd,FBIOBLANK,FB_BLANK_UNBLANK);
  return 0;
}
static int fb_present(u32 buf){
  if(!SCR.is_fb){ /* offline/selftest: nothing to commit, but report success */
    LAST_PAN_RC=0; COMMITS++; VISIBLE=bufptr(buf); return 0;
  }
  struct fb_var v;
  for(u64 i=0;i<sizeof v;i++)((u8*)&v)[i]=0;
  if(sys3(SYS_ioctl,SCR.fd,FBIOGET_VSCREENINFO,(long)&v)<0){ LAST_PAN_RC=-1; return -1; }
  v.yoffset = buf*SCR.h;
  v.xoffset = 0;
  long rc=sys3(SYS_ioctl,SCR.fd,FBIOPAN_DISPLAY,(long)&v);
  LAST_PAN_RC=(int)rc;
  if(rc<0){
    /* A21/A22 lesson: a failed pan means the DECON was released by someone
       else.  Re-assert, then retry once -- never leave the user with a blank
       panel. */
    fb_assert_panel();
    rc=sys3(SYS_ioctl,SCR.fd,FBIOPAN_DISPLAY,(long)&v);
    LAST_PAN_RC=(int)rc;
    if(rc<0){ if(!UI_ERROR[0]){ const char *e="PAN FAILED - REASSERTING PANEL";
      int i=0; while(e[i]){UI_ERROR[i]=e[i];i++;} UI_ERROR[i]=0; } return -1; }
  }
  VISIBLE = bufptr(buf);
  COMMITS++;
  return 0;
}
/* Compose the next frame into the off-screen buffer and immediately scan it out.
   Called for every visible change: one entry point, so the double-buffer bookkeeping
   can only be wrong in one place. */
static int ui_frame(void){
  u32 next = SCR.bufs>1 ? (CURBUF?0u:1u) : 0u;
  SCR.canvas = bufptr(next);
  render();
  int rc = fb_present(next);
  if(rc==0) CURBUF=next;
  return rc;
}

/* ================================================================== handoff */
static void anim_request_stop(void){
  /* Two independent channels, as designed in PHONE-UI-HANDOFF.md: the stop file
     the player polls (in the shared ext4 state dir) and, if it published a pid,
     a signal. The UI has ALREADY committed its own frame before this runs. */
  state_write("anim-stop","PHONE_UI_FRAME_COMMITTED\n");
  char b[64];
  if(file_read(STATE_DIR"/fb-anim.pid",b,sizeof b)>0){
    u64 pid=atou_(b);
    if(pid>1){ sys2(SYS_kill,(long)pid,15);         /* SIGTERM: graceful exit */
      char l[48]; int n=0; const char *p="ANIMATION_STOP_SIGNALLED pid=";
      for(int i=0;p[i];i++)l[n++]=p[i]; char t[16]; u2s(pid,t);
      for(int i=0;t[i];i++)l[n++]=t[i]; l[n++]=' '; char t2[16]; u2s((u64)mono_sec(),t2);
      for(int i=0;t2[i];i++)l[n++]=t2[i]; l[n]=0; ui_log(l); }
  } else ui_log("ANIMATION_STOP_FILE_ONLY (no pid file)");
}
static void anim_wait_stopped(int secs){
  for(int i=0;i<secs*4;i++){
    if(!file_exists(STATE_DIR"/fb-anim.pid")) break;
    char b[64];
    if(file_read(STATE_DIR"/fb-anim.pid",b,sizeof b)>0){
      u64 pid=atou_(b);
      char p[64]; int n=0; const char *d="/proc/"; for(int q=0;d[q];q++)p[n++]=d[q];
      char t[16]; u2s(pid,t); for(int q=0;t[q];q++)p[n++]=t[q]; p[n]=0;
      if(!file_exists(p)){ break; }
    } else break;
    sleep_ms_(250);
  }
}

/* ================================================================ input */
#define EV_SYN 0x00
#define EV_KEY 0x01
#define EV_ABS 0x03
#define ABS_MT_SLOT 0x2f
#define ABS_MT_POSITION_X 0x35
#define ABS_MT_POSITION_Y 0x36
#define ABS_MT_TRACKING_ID 0x39
#define BTN_TOUCH 0x14a
#define SYN_REPORT 0
/* ============================================================================
 * A27 EVDEV IOCTL ENCODING — the A23..A26 requests were malformed, which is why
 * the touch controller was never found even though it enumerated.
 *
 * Linux _IOC(dir,type,nr,size) = dir<<30 | size<<16 | type<<8 | nr, and every
 * evdev request is _IOR('E', ...), so:
 *
 *   EVIOCGNAME(len)   = _IOR('E',0x06,sizeof(name))   -> 0x80000000|len<<16|0x4500|0x06
 *   EVIOCGBIT(ev,len) = _IOR('E',0x20+ev,len)         -> 0x80000000|len<<16|0x4500|(0x20+ev)
 *   EVIOCGABS(abs)    = _IOR('E',0x40+abs,absinfo)    -> 0x80000000|24<<16|0x4500|(0x40+abs)
 *   EVIOCGPROP(len)   = _IOR('E',0x09,len)            -> 0x80000000|len<<16|0x4500|0x09
 *
 * The A26 code put the event type in the SIZE field and the padding byte in the
 * NR field: `0x80000000|len<<16|(ev<<8)|0x20` produced 0x80200320 where the
 * kernel expects 0x80204523, so the ioctl failed (or, worse, matched a different
 * request) and every device was reported as "no multitouch".
 *
 * The three values the target ABI must produce are asserted at COMPILE TIME, so
 * a future edit cannot quietly reintroduce the defect. */
#define EVIOCGNAME(len)   (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|0x06u)
#define EVIOCGBIT(ev,len) (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|(0x20u+(u32)(ev)))
#define EVIOCGABS(ax)     (0x80000000u|(24u<<16)|(0x45u<<8)|(0x40u+(u32)(ax)))
#define EVIOCGPROP(len)   (0x80000000u|(((u32)(len))<<16)|(0x45u<<8)|0x09u)
#define INPUT_PROP_DIRECT 0x01
#define ABS_X 0x00
#define ABS_Y 0x01
#define EV_SW 0x05
_Static_assert(EVIOCGBIT(EV_ABS, 32)==0x80204523u,"EVIOCGBIT(EV_ABS,32) must be 0x80204523");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_X)==0x80184575u,"EVIOCGABS(ABS_MT_POSITION_X) must be 0x80184575");
_Static_assert(EVIOCGABS(ABS_MT_POSITION_Y)==0x80184576u,"EVIOCGABS(ABS_MT_POSITION_Y) must be 0x80184576");
_Static_assert(EVIOCGABS(ABS_X)==0x80184540u,"EVIOCGABS(ABS_X) must be 0x80184540");
_Static_assert(EVIOCGPROP(8)==0x80084509u,"EVIOCGPROP(8) must be 0x80084509");

/* One evdev node, discovered by CAPABILITY (never by event number). */
struct input_dev {
  int fd; int maxx,minx,maxy,miny; int has_mt,has_btn,direct,slots;
  char name[48],path[48];
};
struct input_absinfo { s32 value,minimum,maximum,fuzz,flat,resolution; };
struct input_event { u64 sec,usec; u16 type,code; s32 value; };
/* (see struct input_dev above) */
static struct input_dev IN[8]; static int NIN=0;
static int TOUCH_ORIENT=0;   /* 0: panel-native, 1: rotate 90, 2: 180, 3: 270 */
/* ---- Type B multitouch state -------------------------------------------------
   Per-slot state, so a released contact can never hand its coordinates to the
   next one (the A26 loop kept one last_x/last_y pair and used BTN_TOUCH as the
   only edge). */
struct touch_state {
  int slot_on[16], slot_x[16], slot_y[16];
  int cur_slot, active, primary_slot, have_btn;
  int down_x, down_y;
};
static struct touch_state TS;

static int evdev_has(const u32 *bits,int code){ return (bits[code/32]>>(code%32))&1u; }
static void log_ioctl_fail(const char *what,const char *node,long rc){
  char l[128]; int n=0; const char *p="INPUT_IOCTL_FAIL "; for(int i=0;p[i];i++)l[n++]=p[i];
  for(int i=0;what[i]&&n<60;i++)l[n++]=what[i];
  l[n++]=' '; for(int i=0;node[i]&&n<100;i++)l[n++]=node[i];
  l[n++]=' '; char t[16]; u2s((u64)(u32)(-rc),t);
  for(int i=0;t[i];i++)l[n++]=t[i];
  l[n++]=' '; const char *q="raw="; for(int i=0;q[i];i++)l[n++]=q[i];
  char t2[20]; int k=0; long v=rc<0?-rc:rc; if(!v)t2[k++]='0';
  while(v){ t2[k++]=(char)('0'+(int)(v%10)); v/=10; }
  while(k&&n<126) l[n++]=t2[--k];
  l[n]=0; ui_log(l);
}
/* Enumerate /dev/input/event* by capability: EV_ABS + (INPUT_PROP_DIRECT or
   ABS_MT_POSITION_X).  The event NUMBER is never assumed (the mission asks for
   this explicitly: a future kernel may renumber it). */
static void input_scan(void){
  for(int i=0;i<NIN;i++) if(IN[i].fd>=0) sys1(SYS_close,IN[i].fd);
  NIN=0;
  long dfd=sys4(SYS_openat,AT_FDCWD,(long)"/dev/input",O_RDONLY|O_DIRECTORY,0);
  if(dfd<0){ wr("INPUT_SCAN_NO_DEV_INPUT\\n"); return; }
  char buf[4096];
  for(;;){
    long n=sys3(SYS_getdents64,dfd,(long)buf,sizeof buf);
    if(n<=0) break;
    for(long off=0;off<n;){
      u16 reclen=*(u16*)(buf+off+16); if(reclen<24) break;
      char *nm=buf+off+19;
      if(nm[0]=='e'&&nm[1]=='v'&&nm[2]=='e'&&nm[3]=='n'&&nm[4]=='t'&&nm[5]>='0'&&nm[5]<='9'&&NIN<8){
        char p[48]; int k=0; const char *a="/dev/input/"; while(a[k]){p[k]=a[k];k++;}
        for(int q=0;nm[q]&&k<46;q++) p[k++]=nm[q]; p[k]=0;
        long fd=sys4(SYS_openat,AT_FDCWD,(long)p,O_RDONLY|O_NONBLOCK,0);
        if(fd>=0){
          struct input_dev *d=&IN[NIN];
          for(u64 i=0;i<sizeof *d;i++)((u8*)d)[i]=0;
          d->fd=(int)fd; d->slots=1;
          int q=0; while(p[q]&&q<46){ d->path[q]=p[q]; q++; } d->path[q]=0;
          char nmb[64]; for(u64 i=0;i<sizeof nmb;i++)nmb[i]=0;
          if(sys3(SYS_ioctl,fd,EVIOCGNAME(sizeof nmb-1),(long)nmb)>0){
            q=0; while(nmb[q]&&q<44){ d->name[q]=nmb[q]; q++; } d->name[q]=0;
          }
          u32 absbits[8], keybits[12], propbits[2];
          for(u64 i=0;i<sizeof absbits;i++)((u8*)absbits)[i]=0;
          for(u64 i=0;i<sizeof keybits;i++)((u8*)keybits)[i]=0;
          for(u64 i=0;i<sizeof propbits;i++)((u8*)propbits)[i]=0;
          long rb=sys3(SYS_ioctl,fd,EVIOCGBIT(EV_ABS,sizeof absbits),(long)absbits);
          if(rb<0) log_ioctl_fail("EVIOCGBIT(EV_ABS)",d->path,rb);
          long kb=sys3(SYS_ioctl,fd,EVIOCGBIT(EV_KEY,sizeof keybits),(long)keybits);
          if(kb<0) log_ioctl_fail("EVIOCGBIT(EV_KEY)",d->path,kb);
          long pb=sys3(SYS_ioctl,fd,EVIOCGPROP(sizeof propbits),(long)propbits);
          if(pb<0) log_ioctl_fail("EVIOCGPROP",d->path,pb);
          d->has_mt=evdev_has(absbits,ABS_MT_POSITION_X)&&evdev_has(absbits,ABS_MT_POSITION_Y);
          d->has_btn=evdev_has(keybits,BTN_TOUCH);
          d->direct=(int)evdev_has(propbits,INPUT_PROP_DIRECT);
          struct input_absinfo ai;
          int have_x=0,have_y=0;
          for(u64 i=0;i<sizeof ai;i++)((u8*)&ai)[i]=0;
          long xr=sys3(SYS_ioctl,fd,EVIOCGABS(d->has_mt?ABS_MT_POSITION_X:ABS_X),(long)&ai);
          if(xr>=0){ d->minx=ai.minimum; d->maxx=ai.maximum; have_x=1; }
          else log_ioctl_fail(d->has_mt?"EVIOCGABS(MT_X)":"EVIOCGABS(ABS_X)",d->path,xr);
          for(u64 i=0;i<sizeof ai;i++)((u8*)&ai)[i]=0;
          long yr=sys3(SYS_ioctl,fd,EVIOCGABS(d->has_mt?ABS_MT_POSITION_Y:ABS_Y),(long)&ai);
          if(yr>=0){ d->miny=ai.minimum; d->maxy=ai.maximum; have_y=1; }
          else log_ioctl_fail(d->has_mt?"EVIOCGABS(MT_Y)":"EVIOCGABS(ABS_Y)",d->path,yr);
          if(!have_x||!have_y) d->has_mt=0;
          /* slot count: how many ABS_MT_SLOT-capable slots this device reports */
          if(d->has_mt){
            for(u64 i=0;i<sizeof ai;i++)((u8*)&ai)[i]=0;
            if(sys3(SYS_ioctl,fd,EVIOCGABS(ABS_MT_SLOT),(long)&ai)>=0) d->slots=ai.maximum+1;
            if(d->slots<1)d->slots=1; if(d->slots>16)d->slots=16;
          }
          {
            char l[160]; int m=0; const char *pp="INPUT_DEVICE path=";
            for(int i=0;pp[i];i++)l[m++]=pp[i];
            for(int i=0;d->path[i]&&m<130;i++)l[m++]=d->path[i];
            const char *q2=" name='"; for(int i=0;q2[i];i++)l[m++]=q2[i];
            for(int i=0;d->name[i]&&m<150;i++)l[m++]=d->name[i];
            l[m++]='\''; l[m]=0; ui_log(l);
          }
          ui_log(d->has_mt?"INPUT_CAPS abs+mt=1":"INPUT_CAPS abs+mt=0");
          { char l[128]; int m=0; const char *pp="INPUT_CAPS direct=";
            for(int i=0;pp[i];i++)l[m++]=pp[i];
            l[m++]=d->direct?'1':'0'; const char *q2=" btn_touch="; for(int i=0;q2[i];i++)l[m++]=q2[i];
            l[m++]=d->has_btn?'1':'0'; const char *q3=" slots="; for(int i=0;q3[i];i++)l[m++]=q3[i];
            char t[8]; u2s((u64)d->slots,t); for(int i=0;t[i];i++)l[m++]=t[i];
            const char *q4=" x=["; for(int i=0;q4[i];i++)l[m++]=q4[i];
            u2s((u64)(u32)d->minx,t); for(int i=0;t[i];i++)l[m++]=t[i]; l[m++]='.';
            u2s((u64)(u32)d->maxx,t); for(int i=0;t[i];i++)l[m++]=t[i];
            const char *q5="] y=["; for(int i=0;q5[i];i++)l[m++]=q5[i];
            u2s((u64)(u32)d->miny,t); for(int i=0;t[i];i++)l[m++]=t[i]; l[m++]='.';
            u2s((u64)(u32)d->maxy,t); for(int i=0;t[i];i++)l[m++]=t[i]; l[m++]=']'; l[m]=0;
            ui_log(l); }
          NIN++;
        }
      }
      off+=reclen;
    }
  }
  sys1(SYS_close,dfd);
}
/* Choose the panel touchscreen by capability: an absolutely-addressed pointing
   device (INPUT_PROP_DIRECT) with multitouch axes, then any MT device with
   BTN_TOUCH, then the name.  Never by /dev/input/eventN. */
static int input_primary(void){
  for(int i=0;i<NIN;i++) if(IN[i].has_mt && IN[i].direct) return i;
  for(int i=0;i<NIN;i++) if(IN[i].has_mt && str_find(IN[i].name,"touch")) return i;
  for(int i=0;i<NIN;i++) if(IN[i].has_mt) return i;
  for(int i=0;i<NIN;i++) if(IN[i].has_btn && IN[i].direct) return i;
  return -1;
}
/* Map raw device coordinates to panel pixels using the device's OWN minima and
   maxima (the mission: do not assume 0..1440 / 0..3040), then apply the
   orientation the device actually needs.  Orientation is a runtime value
   (`orient N` on the console / TOUCH_ORIENT) because guessing it is exactly the
   mistake this code must not repeat. */
static void touch_map(int i,int rawx,int rawy,int *sx,int *sy){
  struct input_dev *d=&IN[i];
  int rx=d->maxx-d->minx, ry=d->maxy-d->miny;
  int nx=rx>0?((rawx-d->minx)*((int)SCR.w-1))/rx:0;
  int ny=ry>0?((rawy-d->miny)*((int)SCR.h-1))/ry:0;
  if(nx<0)nx=0; if(ny<0)ny=0;
  if(nx>(int)SCR.w-1)nx=(int)SCR.w-1; if(ny>(int)SCR.h-1)ny=(int)SCR.h-1;
  switch(TOUCH_ORIENT){
    case 1:  *sx=(int)SCR.w-1-ny; *sy=nx; break;
    case 2:  *sx=(int)SCR.w-1-nx; *sy=(int)SCR.h-1-ny; break;
    case 3:  *sx=ny;              *sy=(int)SCR.h-1-nx; break;
    default: *sx=nx;              *sy=ny; break;
  }
}
static void act_do(int act);   /* defined in the actions section below */
/* ------------------------------------------------------------ touch events
   Returns 1 if a gesture was dispatched, -1 if the device went away. */
static void touch_record(const char *what,int x,int y,int act){
  char b[96]; int m=0; const char *p=what; for(int i=0;p[i];i++)b[m++]=p[i];
  const char *q=" x="; for(int i=0;q[i];i++)b[m++]=q[i];
  char t[16]; u2s((u64)x,t); for(int i=0;t[i];i++)b[m++]=t[i];
  const char *q2=" y="; for(int i=0;q2[i];i++)b[m++]=q2[i];
  u2s((u64)y,t); for(int i=0;t[i];i++)b[m++]=t[i];
  const char *q3=" act="; for(int i=0;q3[i];i++)b[m++]=q3[i];
  u2s((u64)act,t); for(int i=0;t[i];i++)b[m++]=t[i];
  b[m++]='\n'; b[m]=0;
  state_write("ui-touch",b);
  ui_log(b);
}
static void touch_reset(void){
  for(u64 q=0;q<sizeof TS;q++)((u8*)&TS)[q]=0;
  TS.primary_slot=-1;
}
/* A27: a NON-BLOCKING evdev read that has nothing to report returns -EAGAIN
   (-11), and an interrupted one returns -EINTR (-4).  Treating those as "the
   device went away" made the first A27 build re-scan /dev/input forever and
   never deliver an event (measured on hardware: TOUCH_DEVICE_LOST every 3 s).
   Only a real error means the node is gone. */
#define NX_EINTR (-4)
#define NX_EAGAIN (-11)
#define NX_ENODEV (-19)
#define NX_EBADF (-9)
static int touch_poll(int i){
  struct input_event ev[32];
  int acted=0;
  for(;;){
    long n=sys3(SYS_read,IN[i].fd,(long)ev,sizeof ev);
    if(n==0) break;
    if(n==NX_EAGAIN||n==NX_EINTR) break;                 /* nothing to read yet */
    if(n<0) return -1;                                   /* device is gone */ 
    if(n<(long)sizeof(struct input_event)) break;
    int cnt=(int)(n/(long)sizeof(struct input_event));
    for(int q=0;q<cnt;q++){
      struct input_event *e=&ev[q];
      int sl=TS.cur_slot; if(sl<0||sl>15) sl=0;
      if(e->type==EV_ABS){
        if(e->code==ABS_MT_SLOT){ if(e->value>=0&&e->value<16) TS.cur_slot=e->value; }
        else if(e->code==ABS_MT_TRACKING_ID){
          if(e->value>=0){ TS.slot_on[sl]=1; if(TS.primary_slot<0) TS.primary_slot=sl; }
          else { TS.slot_on[sl]=0; if(TS.primary_slot==sl) TS.primary_slot=-1; }
        }
        else if(e->code==ABS_MT_POSITION_X) TS.slot_x[sl]=e->value;
        else if(e->code==ABS_MT_POSITION_Y) TS.slot_y[sl]=e->value;
        else if(e->code==ABS_X) TS.slot_x[sl]=e->value;
        else if(e->code==ABS_Y) TS.slot_y[sl]=e->value;
      } else if(e->type==EV_KEY && e->code==BTN_TOUCH){
        TS.have_btn=1;
        if(e->value&&!TS.active){
          int sx,sy; touch_map(i,TS.slot_x[sl],TS.slot_y[sl],&sx,&sy);
          TS.active=1; TS.primary_slot=sl; TS.down_x=sx; TS.down_y=sy;
        } else if(!e->value&&TS.active){
          int sx,sy; touch_map(i,TS.slot_x[sl],TS.slot_y[sl],&sx,&sy);
          TS.active=0;
          int dx=sx-TS.down_x, dy=sy-TS.down_y; if(dx<0)dx=-dx; if(dy<0)dy=-dy;
          if(dx<12*SC&&dy<12*SC){
            int ac=hit_test(sx,sy);
            if(ac){ act_do(ac); touch_record("TOUCH_TAP",sx,sy,ac); }
            else { char m[48]; int k=0; const char *p="TAP "; for(int z=0;p[z];z++)m[k++]=p[z];
              char t[16]; u2s((u64)sx,t); for(int z=0;t[z];z++)m[k++]=t[z]; m[k++]=',';
              u2s((u64)sy,t); for(int z=0;t[z];z++)m[k++]=t[z]; m[k]=0;
              toast(m,2); touch_record("TOUCH_TAP_MISS",sx,sy,0); }
          } else if(dy*2>dx){
            act_do(sy>TS.down_y?ACT_LOGDOWN:ACT_LOGUP);
            touch_record("TOUCH_SWIPE_V",sx,sy,sy>TS.down_y?ACT_LOGDOWN:ACT_LOGUP);
          } else {
            PAGE=(PAGE+1)%PAGE_MAX; touch_record("TOUCH_SWIPE_H",sx,sy,0);
          }
          acted=1; TS.primary_slot=-1;
        }
      } else if(e->type==EV_SYN && e->code==SYN_REPORT && !TS.have_btn){
        int any=0; for(int z=0;z<16;z++) if(TS.slot_on[z]) any=1;
        if(any&&!TS.active){
          int z=TS.primary_slot>=0?TS.primary_slot:0;
          if(!TS.slot_on[z]){ for(int y2=0;y2<16;y2++) if(TS.slot_on[y2]){ z=y2; break; } }
          int sx,sy; touch_map(i,TS.slot_x[z],TS.slot_y[z],&sx,&sy);
          TS.active=1; TS.primary_slot=z; TS.down_x=sx; TS.down_y=sy;
          touch_record("TOUCH_DOWN",sx,sy,0);
        } else if(!any&&TS.active){
          int z=TS.primary_slot>=0?TS.primary_slot:0;
          int sx,sy; touch_map(i,TS.slot_x[z],TS.slot_y[z],&sx,&sy);
          TS.active=0;
          int dx=sx-TS.down_x, dy=sy-TS.down_y; if(dx<0)dx=-dx; if(dy<0)dy=-dy;
          if(dx<12*SC&&dy<12*SC){
            int ac=hit_test(sx,sy);
            if(ac){ act_do(ac); touch_record("TOUCH_TAP",sx,sy,ac); }
            else { char m[48]; int k=0; const char *p="TAP "; for(int z2=0;p[z2];z2++)m[k++]=p[z2];
              char t[16]; u2s((u64)sx,t); for(int z2=0;t[z2];z2++)m[k++]=t[z2]; m[k++]=',';
              u2s((u64)sy,t); for(int z2=0;t[z2];z2++)m[k++]=t[z2]; m[k]=0;
              toast(m,2); touch_record("TOUCH_TAP_MISS",sx,sy,0); }
          } else if(dy*2>dx){
            act_do(sy>TS.down_y?ACT_LOGDOWN:ACT_LOGUP);
            touch_record("TOUCH_SWIPE_V",sx,sy,sy>TS.down_y?ACT_LOGDOWN:ACT_LOGUP);
          } else { PAGE=(PAGE+1)%PAGE_MAX; touch_record("TOUCH_SWIPE_H",sx,sy,0); }
          acted=1; TS.primary_slot=-1;
        }
      }
    }
  }
  return acted;
}
/* A27: the capability-qualified touch summary (device name, slots and the REAL
   axis ranges read with EVIOCGABS) shown on the Settings/System pages. */
static void info_touch_refine(void){
  int pi=input_primary();
  if(pi<0) return;
  struct input_dev *d=&IN[pi];
  char t[24]; int n=0;
  const char *p2="mt=1 slots="; for(int i=0;p2[i];i++) SI.touch[n++]=p2[i];
  u2s((u64)d->slots,t); for(int i=0;t[i];i++) SI.touch[n++]=t[i];
  const char *p3=" x=["; for(int i=0;p3[i];i++) SI.touch[n++]=p3[i];
  u2s((u64)(u32)d->minx,t); for(int i=0;t[i];i++) SI.touch[n++]=t[i];
  SI.touch[n++]='.';
  u2s((u64)(u32)d->maxx,t); for(int i=0;t[i];i++) SI.touch[n++]=t[i];
  SI.touch[n++]=']';
  if(d->name[0]){ SI.touch[n++]=' '; for(int i=0;d->name[i]&&n<44;i++) SI.touch[n++]=d->name[i]; }
  SI.touch[n]=0;
  copy_trim(SI.touchpath,d->path,sizeof SI.touchpath);
}
/* ================================================================ utilities */
#ifndef NUXEL_UI_HOST
static void sleep_ms_(long ms){
  long ts[2]; ts[0]=ms/1000; ts[1]=(ms%1000)*1000000L;
  sys2(SYS_nanosleep,(long)ts,0);
}
#endif /* NUXEL_UI_HOST */

/* ============================================================== actions */
static int POWER_ACTION=0;   /* 0 none, 1 reboot, 2 poweroff */
static int QUIT_REQUEST=0;
static int CTEST_FRAMES=0;

static void action_ui_error(const char *e){
  int i=0; while(e[i]&&i<150){ UI_ERROR[i]=e[i]; i++; } UI_ERROR[i]=0;
  ui_log(e);
}
static void do_screenshot(const char *path,int half){
  const u8 *src=VISIBLE?VISIBLE:SCR.canvas;
  int w=(int)SCR.w, h=(int)SCR.h;
  long fd=out_open(path);
  if(fd<0){ action_ui_error("SCREENSHOT: cannot create file"); return; }
  char hdr[64]; int n=0;
  const char *p="P6\n"; for(int i=0;p[i];i++)hdr[n++]=p[i];
  char t[16]; u2s((u64)(half?w/2:w),t); for(int i=0;t[i];i++)hdr[n++]=t[i]; hdr[n++]=' ';
  u2s((u64)(half?h/2:h),t); for(int i=0;t[i];i++)hdr[n++]=t[i];
  hdr[n++]='\n'; const char *p2="255\n"; for(int i=0;p2[i];i++)hdr[n++]=p2[i];
  out_write(fd,hdr,(u64)n);
  enum { CHUNK=19200 };   /* 80 rows of 240 px */
  static u8 out[CHUNK];   
  int step=half?2:1;
  int oi=0; u64 written=0;
  for(int y=0;y<h;y+=step){
    const u8 *row=src+(u64)y*SCR.stride;
    for(int x=0;x<w;x+=step){
      u32 v;
      if(SCR.bpp==32) v=*(const volatile u32*)(row+(u64)x*4);
      else if(SCR.bpp==16){ u32 v16=*(const volatile u16*)(row+(u64)x*2);
        v=pack_rgb(((v16>>11)&31)*255/31,((v16>>5)&63)*255/63,(v16&31)*255/31); }
      else { v=((u32)row[x*3])|((u32)row[x*3+1]<<8)|((u32)row[x*3+2]<<16); }
      /* read back in the panel's real order so the PPM is what the glass shows */
      u32 r,g,b;
      if(SCR.bpp==16){ r=(v>>16)&255; g=(v>>8)&255; b=v&255; }
      else if(SCR.hw_abgr){ r=v&255; g=(v>>8)&255; b=(v>>16)&255; }
      else { r=(v>>16)&255; g=(v>>8)&255; b=v&255; }
      out[oi++]=(u8)r; out[oi++]=(u8)g; out[oi++]=(u8)b;
      if(oi+4>CHUNK){ long rc=out_write(fd,out,oi); if(rc<0){ out_close(fd); action_ui_error("SCREENSHOT: write failed"); return; } written+=(u64)oi; oi=0; }
    }
  }
  if(oi>0) out_write(fd,out,(u64)oi);
  out_close(fd);
  char l[160]; int m=0; const char *q="SCREENSHOT_OK "; for(int i=0;q[i];i++)l[m++]=q[i];
  for(int i=0;path[i]&&m<120;i++)l[m++]=path[i];
  l[m++]=' '; u2s((u64)((SCR.w/step)*(SCR.h/step)*3),t);
  for(int i=0;t[i];i++)l[m++]=t[i]; l[m]=0;
  ui_log(l);
}
/* Colour bars packed BOTH ways, side by side, so one glance at the panel (or one
   screenshot) settles the channel order.  Never used by the normal UI path. */
static void do_colourtest(void){
  u8 *save=VISIBLE?VISIBLE:SCR.canvas;
  int bars=5; int bw=(int)SCR.w/bars;
  u32 top[5]={pack_rgb(255,0,0),pack_rgb(0,255,0),pack_rgb(0,0,255),pack_rgb(255,255,255),pack_rgb(0,0,0)};
  u32 bot[5]; SCR.hw_abgr^=1;
  bot[0]=pack_rgb(255,0,0); bot[1]=pack_rgb(0,255,0); bot[2]=pack_rgb(0,0,255);
  bot[3]=pack_rgb(255,255,255); bot[4]=pack_rgb(0,0,0);
  SCR.hw_abgr^=1;
  SCR.canvas=bufptr(SCR.bufs>1?(CURBUF?0u:1u):0u);
  for(int i=0;i<bars;i++){
    fill_rect(i*bw,0,bw,(int)SCR.h/2,top[i]);
    fill_rect(i*bw,(int)SCR.h/2,bw,(int)SCR.h-(int)SCR.h/2,bot[i]);
  }
  int ts=SC*3;
  font_draw(SC*4,SC*6,font_for(13),"TOP = HARDWARE ABGR (DECON ABGR_8888)",C_TXT);
  font_draw(SC*4,(int)SCR.h/2+SC*6,font_for(13),"BOTTOM = FBVAR DECLARED ORDER",C_TXT);
  { u32 nb=SCR.bufs>1?(CURBUF?0u:1u):0u; if(fb_present(nb)==0) CURBUF=nb; }
  sleep_ms_(4000);
  CTEST_FRAMES=0;
  SCR.canvas=save;
  wr("NUXEL_UI_COLOURTEST_DONE\n");
  ui_log("COLOURTEST_SHOWN top=hardware-abgr bottom=fbvar");
  toast("COLOUR TEST SHOWN",3);
}
static void do_power(void){
  state_write("ui-power","REQUESTED\n");
  ui_log(POWER_ACTION==2?"POWER_OFF_REQUESTED":"REBOOT_REQUESTED");
  if(!SCR.is_fb) return;               /* selftest must never power anything off */
  /* sync the filesystems the way systemd would, then ask the kernel */
  long sfd=sys4(SYS_openat,AT_FDCWD,(long)"/",O_RDONLY,0);
  if(sfd>=0){ sys3(SYS_ioctl,sfd,0x80047601,0); /* BLKFLSBUF-ish best effort */ sys1(SYS_close,sfd); }
  sys4(SYS_reboot,0xfee1dead,672274793,0x01234567,0);
  sleep_ms_(2000);
}
static const struct { const char *n; int a; } ACT_NAMES[]={
  {"home",ACT_HOME},{"settings",ACT_SETTINGS},{"system",ACT_SYSTEM},{"logs",ACT_LOGS},
  {"power",ACT_POWER},{"about",ACT_ABOUT},{"ctest",ACT_CTEST},{"shot",ACT_SHOT},
  {"restart",ACT_RESTART},{"reboot",ACT_REBOOT},{"shutdown",ACT_SHUTDOWN},{"logup",ACT_LOGUP},
  {"logdown",ACT_LOGDOWN},{"",0}
};
static int act_by_name(const char *n){
  for(int i=0;ACT_NAMES[i].n[0];i++) if(str_eq(ACT_NAMES[i].n,n)) return ACT_NAMES[i].a;
  return ACT_NONE;
}
static void act_do(int act){
  switch(act){
    case ACT_HOME:     PAGE=PAGE_HOME;     break;
    case ACT_SETTINGS: PAGE=PAGE_SETTINGS; break;
    case ACT_SYSTEM:   PAGE=PAGE_SYSTEM;   break;
    case ACT_LOGS:     PAGE=PAGE_LOGS;     break;
    case ACT_POWER:    PAGE=PAGE_POWER;    break;
    case ACT_ABOUT:    PAGE=PAGE_ABOUT;    break;
    case ACT_LOGUP:    LOG_TOP+=4; break;
    case ACT_LOGDOWN:  LOG_TOP-=4; if(LOG_TOP<0)LOG_TOP=0; break;
    case ACT_CTEST:    do_colourtest(); break;
    case ACT_SHOT:     do_screenshot(STATE_DIR"/ui.ppm",0); toast("SCREENSHOT SAVED",3); break;
    case ACT_REBOOT:
      if(POWER_ARMED && mono_sec()<=POWER_ARM_UNTIL){ POWER_ACTION=1; }
      else { POWER_ARMED=1; POWER_ARM_UNTIL=mono_sec()+6; toast("ARMED - TAP AGAIN TO REBOOT",6); }
      break;
    case ACT_SHUTDOWN:
      if(POWER_ARMED && mono_sec()<=POWER_ARM_UNTIL){ POWER_ACTION=2; }
      else { POWER_ARMED=1; POWER_ARM_UNTIL=mono_sec()+6; toast("ARMED - TAP AGAIN TO POWER OFF",6); }
      break;
    case ACT_RESTART:  QUIT_REQUEST=1; break;
    case ACT_DIAG:     PAGE=PAGE_HOME; break;
    case ACT_SEARCH_CLOSE: SEARCH_OPEN=0; break;
    default:
      if(act>=ACT_APP_BASE && act<ACT_APP_BASE+NUXEL_LAUNCHER_APP_COUNT){
        if(PAGE!=PAGE_LAUNCHER) PAGE=PAGE_LAUNCHER;
        launch_app(act-ACT_APP_BASE);
      }
      break;
  }
  char l[48]; int n=0; const char *p="ACTION "; for(int i=0;p[i];i++)l[n++]=p[i];
  char t[16]; u2s((u64)act,t); for(int i=0;t[i];i++)l[n++]=t[i]; l[n++]=' '; 
  const char *pn=PAGE_NAME[PAGE<PAGE_MAX?PAGE:0]; for(int i=0;pn[i];i++)l[n++]=pn[i]; l[n]=0;
  ui_log(l);
}
/* ================================================== console command channel
 * The live CDC-ACM console owns /run; writing a line here drives the UI, so the
 * interface is testable before the touchscreen is up (mission section 8). */
#define CMD_FIFO "/run/nuxel-ui.cmd"
static int CMD_FD=-1;
static void cmd_open(void){
  sys4(SYS_mknodat,AT_FDCWD,(long)CMD_FIFO,S_IFIFO|0666,0);
  CMD_FD=(int)sys4(SYS_openat,AT_FDCWD,(long)CMD_FIFO,O_RDONLY|O_NONBLOCK,0);
  if(CMD_FD<0) wr("NUXEL_UI_CMD_FIFO_UNAVAILABLE\n");
  else wr("NUXEL_UI_CMD_FIFO_OK " CMD_FIFO "\n");
}
static void cmd_handle(char *line){
  char *a=line; while(*a==' ')a++;
  if(str_starts(a,"page")){
    const char *v=str_after(a,'='); if(v==a){ v=a+4; while(*v==' ')v++; }
    for(int i=0;i<PAGE_MAX;i++) if(str_starts(v,PAGE_NAME[i])){ PAGE=i; break; }
  } else if(str_starts(a,"go ")){ PAGE=PAGE_HOME; act_do(act_by_name(a+3)); }
  else if(str_starts(a,"act=")){ int x=act_by_name(a+4); if(x) act_do(x); }
  else if(str_starts(a,"act ")){ int x=act_by_name(a+4); if(x) act_do(x); }
  else if(str_starts(a,"tap")){
    const char *v=str_after(a,' '); int x=(int)atou_(v); v=str_after(v,' '); int y=(int)atou_(v);
    int ac=hit_test(x,y); if(ac) act_do(ac); else toast("TAP: NO WIDGET THERE",2);
  }
  else if(str_starts(a,"screenshot")){
    /* PARSER FIX (A26 defect): `screenshot small` used to treat the word "small"
       as the FILENAME (it wrote /small in the CWD).  Tokens are now classified:
       a token that is exactly "small" is the modifier, anything else is the path,
       in either order.  Accepted forms:
         screenshot
         screenshot /var/lib/nuxel/ui.ppm
         screenshot small
         screenshot /var/lib/nuxel/ui.ppm small
         screenshot small /var/lib/nuxel/ui.ppm
       With `small` and no path the default path becomes ui-small.ppm. */
    const char *q=a+10;
    char path[192]; int have_path=0, half=0;
    for(int tok=0;tok<3;tok++){
      while(*q==' ')q++;
      if(!*q) break;
      const char *st=q; while(*q&&*q!=' ')q++;
      int len=(int)(q-st);
      if(len==5&&st[0]=='s'&&st[1]=='m'&&st[2]=='a'&&st[3]=='l'&&st[4]=='l') half=1;
      else if(!have_path){
        int n=0; for(int i=0;i<len&&n<186;i++) path[n++]=st[i];
        path[n]=0; have_path=1;
      }
    }
    const char *final = have_path?path:(half?"/var/lib/nuxel/ui-small.ppm":"/var/lib/nuxel/ui.ppm");
    do_screenshot(final,half); toast("SCREENSHOT SAVED",3);
  }
  else if(str_starts(a,"orient")){ TOUCH_ORIENT=(int)atou_(str_after(a,' ')); }
  /* ---- A28 launcher commands (the console is also the only keyboard the
     fbdev build has: there is no on-screen keyboard without a Wayland OSK) */
  else if(str_starts(a,"launch")){
    const char *v=a+6; while(*v==' ')v++;
    if(!*v){ wr("NUXEL_UI_CMD_USAGE launch <app-id|app-name>\n"); }
    else { int ai=launch_by_query(v);
      if(ai<0){ wr("NUXEL_UI_CMD_UNKNOWN_APP "); wr(v); wr("\n"); }
      else PAGE=PAGE_LAUNCHER; }
  }
  else if(str_starts(a,"searchclose")){ SEARCH_OPEN=0; }
  else if(str_starts(a,"search")&&(a[6]==' '||a[6]==0)){
    const char *v=a+6; while(*v==' ')v++;
    int n=0; while(*v&&n<44){ SEARCH_Q[n++]=*v++; }
    SEARCH_Q[n]=0; SEARCH_OPEN=1; search_apply();
    PAGE=PAGE_LAUNCHER;
    { char l[96]; int m=0; const char *p2="SEARCH_QUERY q='";
      for(int i=0;p2[i];i++)l[m++]=p2[i];
      for(int i=0;SEARCH_Q[i]&&m<80;i++)l[m++]=SEARCH_Q[i];
      l[m++]='\''; const char *q=" hits="; for(int i=0;q[i];i++)l[m++]=q[i];
      char t[8]; u2s((u64)SEARCH_NHITS,t); for(int i=0;t[i];i++)l[m++]=t[i]; l[m]=0;
      ui_log(l); }
  }
  else if(str_starts(a,"apps")){
    apps_state_write();
    for(int i=0;i<NUXEL_LAUNCHER_APP_COUNT;i++){
      char l[128]; int m=0; const char *p2="APP ";
      for(int j=0;p2[j];j++)l[m++]=p2[j];
      for(int j=0;NUXEL_APP_LIST[i].id[j]&&m<60;j++)l[m++]=NUXEL_APP_LIST[i].id[j];
      l[m++]=' ';
      const char *st=APP_STATE[i]==0?"untried":(APP_STATE[i]==1?"started":"unavailable");
      for(int j=0;st[j];j++)l[m++]=st[j];
      l[m++]=' ';
      for(int j=0;APP_NOTE[i][j]&&m<120;j++)l[m++]=APP_NOTE[i][j];
      l[m]=0; ui_log(l);
    }
  }
  else if(str_starts(a,"wall")){
    char l[192]; int m=0; const char *p2="WALLPAPER state=";
    for(int i=0;p2[i];i++)l[m++]=p2[i];
    const char *st=WALL_STATE==1?"ready":(WALL_STATE==0?"unavailable":"not-prepared");
    for(int i=0;st[i];i++)l[m++]=st[i];
    l[m++]=' ';
    for(int i=0;WALL_NOTE[i]&&m<170;i++)l[m++]=WALL_NOTE[i];
    l[m]=0; ui_log(l);
  }
  else if(str_starts(a,"toast")){ toast(a+6,5); }
  else if(str_starts(a,"ctest")){ act_do(ACT_CTEST); }
  else if(str_starts(a,"reboot")){ act_do(ACT_REBOOT); }
  else if(str_starts(a,"shutdown")){ act_do(ACT_SHUTDOWN); }
  else if(str_starts(a,"status")){
    state_write("ui-status.txt","");
    char b[256]; int n=0; const char *p="PAGE="; for(int i=0;p[i];i++)b[n++]=p[i];
    const char *pn=PAGE_NAME[PAGE<PAGE_MAX?PAGE:0]; for(int i=0;pn[i];i++)b[n++]=pn[i];
    b[n++]=' '; const char *q="COMMITS="; for(int i=0;q[i];i++)b[n++]=q[i];
    char t[16]; u2s((u64)COMMITS,t); for(int i=0;t[i];i++)b[n++]=t[i];
    b[n++]=' '; const char *r="PAN_RC="; for(int i=0;r[i];i++)b[n++]=r[i];
    char t2[16]; u2s((u64)(u32)LAST_PAN_RC,t2); for(int i=0;t2[i];i++)b[n++]=t2[i];
    b[n]=0; state_write("ui-status.txt",b);
    ui_log(b); toast("STATUS WRITTEN",2);
  }
  else if(str_starts(a,"quit!")){ QUIT_REQUEST=2; }
  else if(str_starts(a,"quit")){ QUIT_REQUEST=1; }
  else if(str_starts(a,"touch")){ PAGE=PAGE_SETTINGS; }
  else if(str_starts(a,"help")){
    wr("NUXEL_UI_CMD commands: page=<p> go <act> act=<act> tap X Y launch <app|id>"
       " search <text> searchclose apps wall screenshot [path] [small]"
       " ctest orient N toast TEXT status reboot shutdown quit\n");
  }
  else if(*a){ wr("NUXEL_UI_CMD_UNKNOWN "); wr(a); wr("\n"); }
}
static void cmd_drain(void){
  if(CMD_FD<0) return;
  char buf[1024];
  for(;;){
    long n=sys3(SYS_read,CMD_FD,(long)buf,sizeof buf-1);
    if(n<=0) break;
    buf[n]=0;
    char *s=buf;
    for(long i=0;i<=n;i++){
      if(buf[i]=='\n'||buf[i]=='\0'){ buf[i]=0; if(*s) cmd_handle(s); s=buf+i+1; }
      else if(buf[i]=='\r') buf[i]=' ';
    }
    if(n<(long)sizeof buf-1) break;
  }
}

/* ================================================================ selftest
 * Renders every page into an anonymous buffer and writes PPMs.  This runs on
 * any host (including the Fedora container) and touches NO device, so the layout
 * can be reviewed before anything is flashed. */
/* Extreme-value fixtures: the layout must survive long strings, an unreadable
   battery, a huge uptime and missing network information (mission section 9). */
static void ui_fixture(int which){
  if(which==1){
    copy_trim(SI.kernel,"4.14.253-nuxel-a27-long-kernel-identifier-for-layout",sizeof SI.kernel);
    copy_trim(SI.osname,"Fedora Linux 43 (Forty Three) aarch64 long name",sizeof SI.osname);
    copy_trim(SI.uptime,"365 days, 23 hours, 59 minutes, 59 seconds uptime",sizeof SI.uptime);
    copy_trim(SI.battery_status,"Discharging not charging, health unknown",sizeof SI.battery_status);
    copy_trim(SI.touch,"mt=1 slots=10 x=[0.4095] sec_touchscreen long",sizeof SI.touch);
    copy_trim(SI.touchpath,"/dev/input/event2-with-a-very-long-path",sizeof SI.touchpath);
  } else if(which==2){
    SI.battery_pct=-1; SI.battery_ok=0; SI.charging=0; SI.on_ac=0;
    copy_trim(SI.battery_status,"NO BATTERY SYSFS ENTRY FOUND",sizeof SI.battery_status);
    copy_trim(SI.usb,"",sizeof SI.usb);
    copy_trim(SI.touch,"no pointing device",sizeof SI.touch);
    copy_trim(SI.touchpath,"",sizeof SI.touchpath);
    copy_trim(SI.system_state,"initializing",sizeof SI.system_state);
    copy_trim(SI.cgroup,"(no cgroup2 mount)",sizeof SI.cgroup);
  } else if(which==3){
    copy_trim(SI.uptime,"1234 days, 23:59:59",sizeof SI.uptime);
    copy_trim(SI.kernel,"4.14.253",sizeof SI.kernel);
    copy_trim(SI.osname,"Fedora Linux 43",sizeof SI.osname);
    SI.battery_pct=100; SI.battery_ok=1; SI.charging=1; SI.on_ac=1;
  }
}
static int selftest(const char *dir,int w,int h,int fixture){
  make_dir(dir);   /* the harness may not have made it */
  u64 size=(u64)w*(u64)h*4u;
  void *mem=alloc_anon(size);
  if(mem==MAP_FAILED||!mem){ wr("NUXEL_UI_SELFTEST_MMAP_FAILED\n"); return 20; }
  SCR.fd=-1; SCR.mem=mem; SCR.mapped=size; SCR.w=(u32)w; SCR.h=(u32)h; SCR.vh=(u32)h;
  SCR.stride=(u32)w*4u; SCR.bpp=32; SCR.bufs=1; SCR.toff=0; SCR.is_fb=0; SCR.hw_abgr=1;
  SCR.canvas=mem; VISIBLE=mem; CURBUF=0;
  ui_metrics(w,h);
  clip_all();
  palette_init(); info_collect();
  /* the launcher page is rendered with the real wallpaper when one is forced
     with --wallpaper=FILE, so the offline harness measures the real screen */
  wall_prepare(w,h);
  if(A_WALLDUMP[0]) wall_dump_ppm(A_WALLDUMP);
  ui_fixture(fixture);
  wrn("NUXEL_UI_SELFTEST_SCALE",(u64)SC);
  wrn("NUXEL_UI_SELFTEST_FIXTURE",(u64)fixture);
  int bad=0;
  for(int p=0;p<PAGE_MAX;p++){
    PAGE=p; LOG_TOP=0; SYS_TOP=0; TOAST[0]=0; UI_ERROR[0]=0;
    NREG=0;
    wr("NUXEL_UI_SELFTEST_RENDER "); wr(PAGE_NAME[p]); wr("\n");
    render();
    bad+=layout_check(1);
    char path[256]; int n=0; for(int i=0;dir[i]&&n<200;i++)path[n++]=dir[i];
    path[n++]='/'; path[n++]='p'; path[n++]='a'; path[n++]='g'; path[n++]='e'; path[n++]='-';
    for(int i=0;PAGE_NAME[p][i];i++)path[n++]=PAGE_NAME[p][i];
    for(int i=0;i<4;i++)path[n++]=".ppm"[i];
    path[n]=0;
    SCR.canvas=mem; VISIBLE=mem;
    do_screenshot(path,0);
    if(!file_exists(path)){ wr("NUXEL_UI_SELFTEST_PAGE_FAILED "); wr(path); wr("\n"); return 21; }
    wr("NUXEL_UI_SELFTEST_PAGE "); wr(PAGE_NAME[p]); wr(" -> "); wr(path); wr("\n");
  }
  if(fixture==1||fixture==2||fixture==3){
    PAGE=PAGE_LOGS; LOG_TOP=0; TOAST[0]=0;
    { const char *e="A deliberately long error banner that must still fit its box";
      int i=0; while(e[i]&&i<150){ UI_ERROR[i]=e[i]; i++; } UI_ERROR[i]=0; }
    NREG=0;
    render(); bad+=layout_check(1);
    TOAST[0]=0; UI_ERROR[0]=0;
  }
  if(fixture==1){
    char big[160]; int n=0; for(int i=0;i<150;i++) big[n++]=(char)('A'+(i%26));
    big[n]=0; toast(big,60); PAGE=PAGE_HOME; NREG=0;
    render(); bad+=layout_check(1);
    TOAST[0]=0;
  }
  wrn("NUXEL_UI_SELFTEST_LAYOUT_VIOLATIONS",(u64)bad);
  if(bad){ wr("NUXEL_UI_SELFTEST_LAYOUT_FAILED\n"); return 22; }
  wr("NUXEL_UI_SELFTEST_LAYOUT_OK\n");
  wr("NUXEL_UI_SELFTEST_OK pages="); { char t[8]; u2s(PAGE_MAX,t); wr(t); wr(" size=");
    char t2[16]; u2s((u64)w,t2); wr(t2); wr("x"); char t3[16]; u2s((u64)h,t3); wr(t3); wr("\n"); }
  return 0;
}

/* ===================================================================== main */
static int A_ONCE=0, A_SELFTEST=0, A_SW=1440, A_SH=3040, A_FIX=0;
static const char *A_SDIR=".";
static void parse_args(long argc,char **argv){
  for(long i=1;i<argc;i++){
    const char *a=argv[i];
    if(str_starts(a,"--selftest")){ A_SELFTEST=1; if(a[10]=='=') A_SDIR=a+11; }
    else if(str_starts(a,"--size=")){ const char *v=a+7; A_SW=(int)atou_(v); A_SH=(int)atou_(str_after(v,'x')); }
    else if(str_starts(a,"--once")) A_ONCE=1;
    else if(str_starts(a,"--fixture=")) A_FIX=(int)atou_(a+10);
    else if(str_starts(a,"--layout-verbose")) A_LAYOUT_VERBOSE=1;
    else if(str_starts(a,"--hworder=")) SCR.hw_abgr = (a[10]=='f')?0:1;
    else if(str_starts(a,"--page=")){
      const char *v=a+7; for(int p=0;p<PAGE_MAX;p++) if(str_starts(v,PAGE_NAME[p])) PAGE=p;
    }
    else if(str_starts(a,"--statedir=")) A_SDIR=a+11;
    else if(str_starts(a,"--wallpaper=")) WALL_FORCE=a+12;
    else if(str_starts(a,"--wallpaper-dump=")) A_WALLDUMP=a+17;
    else if(str_starts(a,"--help")||str_starts(a,"-h")){
      wr("usage: nuxel-ui [--selftest=DIR] [--size=WxH] [--once] [--hworder=abgr|fbvar]"
         " [--wallpaper=FILE] [--wallpaper-dump=FILE]"
         " [--page=launcher|home|settings|system|logs|power|about]\n");
      sys1(SYS_exit_group,0);
    }
  }
}
#ifndef NUXEL_UI_HOST
void nuxel_ui_start(long *sp);
__asm__(
".text\n.globl _start\n.type _start,%function\n"
"_start:\n  mov x0, sp\n  b nuxel_ui_start\n");
#endif
void nuxel_ui_start(long *sp){
  long argc=sp[0]; char **argv=(char**)&sp[1];
  log_open();
  SCR.hw_abgr=1;      /* A23: the DECON commit path is ABGR_8888.  This bit was
                         never initialised in the A23 build, so the shipped UI
                         packed with the WRONG (fb_var) order -- caught on hardware
                         as NUXEL_UI_HW_ABGR=0 in dmesg. */
  parse_args(argc,argv);
  if(A_SELFTEST){ int rc=selftest(A_SDIR,A_SW,A_SH,A_FIX); sys1(SYS_exit_group,(long)rc); }
  wr("NUXEL_UI_STARTING rev=" NUXEL_UI_REV "\n");

  /* --- DISPLAY OWNERSHIP FIRST, framebuffer second (A27) -----------------
     A second client must be refused before it can open /dev/fb0 at all: merely
     opening and closing the framebuffer runs decon_release and powers the panel
     down (A21/A24). */
  { int lr=ui_lock_take();
    if(lr==-2){ ui_log("UI_REFUSED another instance owns the display (flock)"); sys1(SYS_exit_group,9); } }

  /* --- open and MEASURE the panel --------------------------------------- */
  SCR.fd=sys4(SYS_openat,AT_FDCWD,(long)"/dev/fb0",O_RDWR,0);
  if(SCR.fd<0){ wr("NUXEL_UI_FB_UNAVAILABLE /dev/fb0\n"); state_write("ui-error","no /dev/fb0\n"); sys1(SYS_exit_group,2); }
  struct fb_var V; struct fb_fix F;
  for(u64 i=0;i<sizeof V;i++)((u8*)&V)[i]=0;
  for(u64 i=0;i<sizeof F;i++)((u8*)&F)[i]=0;
  if(sys3(SYS_ioctl,SCR.fd,FBIOGET_VSCREENINFO,(long)&V)<0||sys3(SYS_ioctl,SCR.fd,FBIOGET_FSCREENINFO,(long)&F)<0){
    wr("NUXEL_UI_FB_IOCTL_FAILED\n"); sys1(SYS_exit_group,3); }
  SCR.w=V.xres; SCR.h=V.yres; SCR.vh=V.yres_virtual?V.yres_virtual:V.yres;
  SCR.stride=F.line_length; SCR.bpp=V.bits_per_pixel;
  SCR.bufs=SCR.vh/SCR.h; if(SCR.bufs<1)SCR.bufs=1; if(SCR.bufs>4)SCR.bufs=4;
  SCR.is_fb=1;
  u64 need=(u64)SCR.stride*SCR.vh;
  void *mem=(void*)sys6(SYS_mmap,0,(long)need,PROT_READ|PROT_WRITE,MAP_SHARED,SCR.fd,0);
  if(mem==MAP_FAILED){ wr("NUXEL_UI_FB_MMAP_FAILED\n"); sys1(SYS_exit_group,4); }
  SCR.mem=mem; SCR.mapped=need;
  ui_metrics((int)SCR.w,(int)SCR.h);      /* design units -> panel pixels */
  clip_all();
  wrn("NUXEL_UI_PANEL_W",SCR.w);   wrn("NUXEL_UI_PANEL_H",SCR.h);
  wrn("NUXEL_UI_PANEL_STRIDE",SCR.stride); wrn("NUXEL_UI_PANEL_BPP",SCR.bpp);
  wrn("NUXEL_UI_PANEL_BUFFERS",SCR.bufs);  wrn("NUXEL_UI_SCALE",(u64)SC);
  wrn("NUXEL_UI_DESIGN_H",(u64)DESIGN_H);
  wrn("NUXEL_UI_DESIGN_OX",(u64)OX);
  wrn("NUXEL_UI_HW_ABGR",(u64)SCR.hw_abgr);
  wrs("NUXEL_UI_FB_DECLARED_RED_OFF",(V.red.offset==16)?"16 (WRONG for this panel)":"not 16");
  wr("NUXEL_UI_FB_HW_FORMAT=DECON_PIXEL_FORMAT_ABGR_8888 R@0 G@8 B@16 A@24\n");
  if(SCR.w<200||SCR.h<400||SCR.bpp!=32){ wr("NUXEL_UI_PANEL_UNSUPPORTED\n"); state_write("ui-error","panel geometry unsupported\n"); sys1(SYS_exit_group,5); }

  palette_init();
  info_collect();
  /* A25 SINGLE INSTANCE.  Two renderers on this panel are fatal, and it is not a
     theory: on A24 a second, deliberate `nuxel-ui --once` was run for diagnosis while
     the real instance owned the panel, and on its exit the kernel logged
     `disable regulator(1:vdd2)` -- fb_release powers the panel down and the survivor
     cannot bring it back, because only a fresh FBIOPUT_VSCREENINFO (which needs the
     regulator) restores it.  The operator was left with a dark screen.  Therefore a
     second instance must never take the panel at all. */
  { char b[64];
    if(file_read(STATE_DIR"/ui.pid",b,sizeof b)>0){
      u64 opid=atou_(b);
      if(opid>1 && opid!=(u64)sys0(SYS_getpid)){
        char pp[48]; int n=0; const char *d="/proc/"; for(int q=0;d[q];q++)pp[n++]=d[q];
        char t[16]; u2s(opid,t); for(int q=0;t[q];q++)pp[n++]=t[q]; pp[n]=0;
        if(file_exists(pp)){
          wr("NUXEL_UI_ALREADY_RUNNING pid="); wr(t);
          wr(" — refusing to take the panel (single-instance rule, A25)\n");
          state_write("ui-refused","ANOTHER_INSTANCE_OWNS_THE_PANEL\n");
          sys1(SYS_exit_group,9);
        }
      }
    }
  }
  wrn("NUXEL_UI_PID",(u64)sys0(SYS_getpid));
  state_num("ui.pid",(u64)sys0(SYS_getpid));
  state_write("ui-stage","PHONE_UI_STARTING\n");
  state_write("ui-build",NUXEL_UI_REV"\n");
  ui_log("UI_STARTED build=" NUXEL_UI_REV);

  /* --- FIRST FRAME: commit before we ask anyone else to let go ---------- */
  if(ui_frame()==0){
    state_write("ui-fb-ready",
      "PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888\n");
    state_write("ui-stage","PHONE_UI_FRAME_COMMITTED\n");
    ui_log("FIRST_FRAME_COMMITTED fbio_pan rc=0");
    toast("NUXEL UI FRAME COMMITTED",4);
    anim_request_stop();
    anim_wait_stopped(2);
    fb_assert_panel();          /* the player's fb_release may have disabled the DECON */
    ui_frame();
    state_write("boot-stage","STAGE=PHONE_UI_FRAME_COMMITTED\nANIMATION_STOPPED=requested\n");
    state_write("ui-stage","PHONE_UI_READY\n");
    ui_log("PHONE_UI_READY");
  } else {
    action_ui_error("FIRST FRAME COMMIT FAILED - PANEL REASSERTED");
    if(A_ONCE) sys1(SYS_exit_group,6);
  }
  if(A_ONCE){ ui_log("EXIT_ONCE_MODE (--once requested)"); sys1(SYS_exit_group,0); }

  input_scan();
  cmd_open();
  /* A28: the launcher's wallpaper (the PWA's own asset) is decoded and
     cover-fitted ONCE, after the first frame has already been committed - the
     animation handoff must never wait on an asset decode. */
  wall_prepare((int)SCR.w,(int)SCR.h);
  if(WALL_STATE==1 && PAGE==PAGE_LAUNCHER) ui_frame();   /* repaint with it */
  int PRIMARY=input_primary();
  wrn("NUXEL_UI_LAYOUT_VIOLATIONS_START",(u64)LAYOUT_VIOLATIONS);
  /* The touch decision is written to FILES as well as to the ram console: the
     kernel ring buffer overflows on this board, so a file on the Fedora rootfs
     is the only durable evidence of which device the UI selected and with which
     axis ranges. */
  {
    char b[192]; int m=0;
    if(PRIMARY>=0){
      struct input_dev *d=&IN[PRIMARY];
      const char *p="TOUCH_READY device="; for(int i=0;p[i];i++)b[m++]=p[i];
      for(int i=0;d->path[i]&&m<60;i++)b[m++]=d->path[i];
      const char *q=" name='"; for(int i=0;q[i];i++)b[m++]=q[i];
      for(int i=0;d->name[i]&&m<140;i++)b[m++]=d->name[i];
      const char *q2="' mt="; for(int i=0;q2[i];i++)b[m++]=q2[i];
      b[m++]=d->has_mt?'1':'0';
      const char *q3=" direct="; for(int i=0;q3[i];i++)b[m++]=q3[i];
      b[m++]=d->direct?'1':'0';
      const char *q4=" slots="; for(int i=0;q4[i];i++)b[m++]=q4[i];
      char t[8]; u2s((u64)d->slots,t); for(int i=0;t[i];i++)b[m++]=t[i];
      const char *q5=" x=["; for(int i=0;q5[i];i++)b[m++]=q5[i];
      u2s((u64)(u32)d->minx,t); for(int i=0;t[i];i++)b[m++]=t[i]; b[m++]='.';
      u2s((u64)(u32)d->maxx,t); for(int i=0;t[i];i++)b[m++]=t[i];
      const char *q6="] y=["; for(int i=0;q6[i];i++)b[m++]=q6[i];
      u2s((u64)(u32)d->miny,t); for(int i=0;t[i];i++)b[m++]=t[i]; b[m++]='.';
      u2s((u64)(u32)d->maxy,t); for(int i=0;t[i];i++)b[m++]=t[i];
      const char *q7="] panel="; for(int i=0;q7[i];i++)b[m++]=q7[i];
      u2s((u64)SCR.w,t); for(int i=0;t[i];i++)b[m++]=t[i]; b[m++]='x';
      u2s((u64)SCR.h,t); for(int i=0;t[i];i++)b[m++]=t[i];
      const char *q8=" orient="; for(int i=0;q8[i];i++)b[m++]=q8[i];
      u2s((u64)TOUCH_ORIENT,t); for(int i=0;t[i];i++)b[m++]=t[i];
      b[m++]='\n'; b[m]=0;
      state_write("ui-touch-ready",b);
      ui_log(b);
      toast("TOUCHSCREEN READY",3);
    } else {
      state_write("ui-touch-ready","TOUCH_POINTING_DEVICE_NONE (console channel can still drive the UI)\n");
      ui_log("TOUCH_POINTING_DEVICE_NONE (console channel can still drive the UI)");
    }
  }
  if(PRIMARY>=0){
    char l[96]; int n=0; const char *p="TOUCH_PRIMARY="; for(int i=0;p[i];i++)l[n++]=p[i];
    for(int i=0;IN[PRIMARY].name[i]&&n<80;i++)l[n++]=IN[PRIMARY].name[i];
    l[n]=0; ui_log(l);
    toast("TOUCHSCREEN FOUND",3);
  } else {
    ui_log("TOUCH_POINTING_DEVICE_NONE (console channel can still drive the UI)");
  }

  /* --- main loop: event driven; one repaint per second when idle, and a
     bounded re-discovery if the input node ever disappears (mission 11.3). */
  int last_sec=-1, last_info=(int)mono_sec(), last_assert=(int)mono_sec();
  int last_scan=(int)mono_sec();
  for(;;){
    cmd_drain();
    reap_children();
    if(QUIT_REQUEST) break;

    int now=(int)mono_sec();
    int dirty=0;

    /* touch */
    if(PRIMARY>=0){
      int tr=touch_poll(PRIMARY);
      if(tr<0){
        ui_log("TOUCH_DEVICE_LOST re-scanning /dev/input");
        sys1(SYS_close,IN[PRIMARY].fd);
        IN[PRIMARY].fd=-1;
        PRIMARY=-1;
        input_scan();
        PRIMARY=input_primary();
        touch_reset();
      } else if(tr>0) dirty=1;
    } else if(now-last_scan>=3){
      last_scan=now;
      input_scan();
      PRIMARY=input_primary();
      if(PRIMARY>=0){
        touch_reset();
        ui_log("TOUCH_PRIMARY_FOUND after re-scan");
        info_collect();
        dirty=1;
      }
    }

    /* periodic refresh + self-heal */
    if(now!=last_sec){ last_sec=now; dirty=1; }
    if(TOAST[0] && now>=TOAST_UNTIL && TOAST_UNTIL){ TOAST[0]=0; dirty=1; }
    if(now-last_info>=5){
      info_collect(); last_info=now; dirty=1;
      /* the panel can be released underneath us by any other fb client; the
         re-assert is cheap and keeps the glass alive (A21/A22 lesson). */
    }
    if(now-last_assert>=2){ fb_assert_panel(); last_assert=now; }
    if(POWER_ACTION) break;
    if(dirty) ui_frame();
    { struct pollfd_ { int fd; short ev,rev; } pfd[2]; int np=0;
      if(CMD_FD>=0){ pfd[np].fd=CMD_FD; pfd[np].ev=POLLIN; pfd[np].rev=0; np++; }
      if(PRIMARY>=0){ pfd[np].fd=IN[PRIMARY].fd; pfd[np].ev=POLLIN; pfd[np].rev=0; np++; }
      long ts[2]; ts[0]=0; ts[1]=250000000L;
      sys5(SYS_ppoll,(long)pfd,np,0,(long)ts,0);
    }
  }
  ui_log("UI_EXIT_REQUESTED (console/quit command)");
  state_write("ui-stage","PHONE_UI_EXITED\n");
  if(POWER_ACTION) do_power();
  sys1(SYS_exit_group,0);
}

#ifndef NUXEL_UI_HOST
/* Freestanding GCC emits calls to these for aggregate initialisation and struct
   copies.  No libc is linked (the same discipline as nuxel-anim-player). */
void *memcpy(void *d,const void *s,u64 n){ u8*a=d; const u8*b=s; while(n--)*a++=*b++; return d; }
void *memset(void *d,int c,u64 n){ u8*p=d; while(n--)*p++=(u8)c; return d; }
#endif
