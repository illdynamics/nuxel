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

#define S_IFIFO 0010000
#define S_IFDIR 0040000

static void sleep_ms_(long ms);
static void *mem_zero(void *d,u64 n){ u8*p=d; while(n--)*p++=0; return d; }
static u64 slen(const char *s){ u64 n=0; while(s[n])n++; return n; }
static void mem_copy(void *d,const void *s,u64 n){ u8*a=d; const u8*b=s; while(n--)*a++=*b++; }
static int str_eq(const char *a,const char *b){ while(*a&&*a==*b){a++;b++;} return *a==*b; }
static int str_starts(const char *a,const char *b){ while(*b){ if(*a++!=*b++)return 0;} return 1; }
static const char *str_after(const char *s,char c){ while(*s&&*s!=c)s++; return *s?s+1:s; }
static int str_find(const char *h,const char *n){ for(const char*p=h;*p;p++){ const char*a=p,*b=n; while(*b&&*a==*b){a++;b++;} if(!*b)return 1;} return 0; }
static u64 atou_(const char *s){ u64 v=0; while(*s>='0'&&*s<='9')v=v*10+(u64)(*s++-'0'); return v; }

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
#define STATE_DIR "/var/lib/nuxel"
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
static int file_exists(const char *path){
  long fd=sys4(SYS_openat,AT_FDCWD,(long)path,O_RDONLY,0);
  if(fd<0) return 0; sys1(SYS_close,fd); return 1;
}

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
 * 5x7 bitmap font, uppercase (lowercase folds to uppercase).  Same provenance
 * as the A12-A19 diagnostic renderer: proven on the panel at 6 scales. */
static const char FONT_CHARS[] =
  " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+:-.,/%=";
static const u8 GLYPHS[][7] = {
 {0,0,0,0,0,0,0},
 {14,17,17,31,17,17,17}, {30,17,17,30,17,17,30}, {14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30}, {31,16,16,30,16,16,31}, {31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15}, {17,17,17,31,17,17,17}, {14,4,4,4,4,4,14},
 {1,1,1,1,17,17,14}, {17,18,20,24,20,18,17}, {16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17}, {17,25,21,19,17,17,17}, {14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16}, {14,17,17,17,21,18,13}, {30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30}, {31,4,4,4,4,4,4}, {17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4}, {17,17,17,21,21,21,10}, {17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4}, {31,1,2,4,8,16,31},
 {14,17,19,21,25,17,14}, {4,12,4,4,4,4,14}, {14,17,1,2,4,8,31},
 {30,1,1,14,1,1,30}, {2,6,10,18,31,2,2}, {31,16,16,30,1,1,30},
 {14,16,16,30,17,17,14}, {31,1,2,4,4,4,4}, {14,17,17,14,17,17,14},
 {14,17,17,15,1,1,14},
 {0,4,4,31,4,4,0}, {0,0,4,0,4,0,0}, {0,0,0,31,0,0,0}, {0,0,0,0,0,6,6},
 {0,0,0,0,6,6,4}, {1,2,2,4,8,8,16}, {17,2,4,8,16,0,17}, {0,0,31,0,31,0,0}
};
static int glyph_index(char c){
  if(c>='a'&&c<='z') c=(char)(c-'a'+'A');
  for(int i=0;FONT_CHARS[i];i++) if(FONT_CHARS[i]==c) return i;
  if(c=='\n'||c=='\0') return 0;
  return 0;   /* unknown -> space */
}
static void text(int x,int y,const char *t,int s,u32 c){
  for(;*t;t++,x+=6*s){
    int gi=glyph_index(*t);
    for(int row=0;row<7;row++)for(int col=0;col<5;col++)
      if(GLYPHS[gi][row] & (1<<(4-col))) fill_rect(x+col*s,y+row*s,s,s,c);
  }
}
static int text_w(const char *t,int s){ int n=0; while(t[n])n++; return n*6*s; }
static void text_center(int cx,int y,const char *t,int s,u32 c){ text(cx-text_w(t,s)/2,y,t,s,c); }
static void text_right(int rx,int y,const char *t,int s,u32 c){ text(rx-text_w(t,s),y,t,s,c); }
/* letter-spaced wordmark (the Nuxel logo line, as in the PWA header) */
static void text_spaced(int cx,int y,const char *t,int s,int extra,u32 c){
  int n=0; while(t[n])n++;
  int w=n*6*s+(n-1)*extra, x=cx-w/2;
  for(int i=0;i<n;i++){ char b[2]={t[i],0}; text(x,y,b,s,c); x+=6*s+extra; }
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
static void palette_init(void){
  C_BG     = pack_rgb(0x0a,0x16,0x28);   /* --bg-primary */
  C_BG2    = pack_rgb(0x0d,0x1f,0x3c);   /* --bg-secondary */
  C_CARD   = pack_rgb(0x12,0x29,0x52);   /* --bg-card */
  C_CARD_HI= pack_rgb(0x1a,0x34,0x66);   /* --bg-card-hover */
  C_TXT    = pack_rgb(0xff,0xff,0xff);
  C_TXT2   = pack_rgb(0xb8,0xc7,0xe0);   /* --text-secondary */
  C_ACCENT = pack_rgb(0x3b,0x82,0xf6);   /* --accent-light */
  C_ACCENT_D=pack_rgb(0x1e,0x40,0xaf);   /* --accent */
  C_OK     = pack_rgb(0x4c,0xaf,0x50);
  C_WARN   = pack_rgb(0xff,0x98,0x00);
  C_ERR    = pack_rgb(0xf4,0x43,0x36);
  C_WHITE  = pack_rgb(0xff,0xff,0xff);
  C_BLACK  = pack_rgb(0,0,0);
  C_LINE   = pack_rgb(0x1c,0x33,0x5e);
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
    int n=0; const char *pre="evdev events="; 
    for(int i=0;pre[i];i++) SI.touch[n++]=pre[i];
    for(int i=0;t[i];i++) SI.touch[n++]=t[i];
    SI.touch[n]=0;
    copy_trim(SI.touchpath,first,sizeof SI.touchpath);
  }
}
static void info_collect(void){
  info_kernel(); info_osrelease(); info_pid1(); info_cgroup(); info_uptime();
  info_rootfs(); info_battery(); info_usb(); info_touch();
}

/* ============================================================== UI structure */
#define NUXEL_UI_REV "A23-fbdev-phone-ui-1"
#define PAGE_HOME 0
#define PAGE_SETTINGS 1
#define PAGE_SYSTEM 2
#define PAGE_LOGS 3
#define PAGE_POWER 4
#define PAGE_ABOUT 5
#define PAGE_MAX 6
static const char *PAGE_NAME[PAGE_MAX]={"home","settings","system","logs","power","about"};

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

static int PAGE=PAGE_HOME;
static int POWER_ARMED=0;
static u64 POWER_ARM_UNTIL=0;
static int SC=4;                 /* UI scale: panel width / 360 (phone CSS px) */
static int SB_H, DOCK_H, MARGIN;
static char TOAST[160];
static int  TOAST_UNTIL=0;       /* monotonic seconds */
static char UI_ERROR[160];       /* last error, drawn on EVERY page */
static int  LOG_TOP=0;           /* first visible log line */

static u64 mono_sec(void){ long ts[2]; sys2(SYS_clock_gettime,CLOCK_MONOTONIC,(long)ts); return (u64)ts[0]; }
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
  long ts[2]; sys2(SYS_clock_gettime,CLOCK_REALTIME,(long)ts);
  s64 t=(s64)ts[0]; s64 days=t/86400; s64 rem=t-days*86400;
  c->hh=(int)(rem/3600); c->mm=(int)((rem%3600)/60); c->ss=(int)(rem%60);
  civil_from_days(days,&c->y,&c->mo,&c->d);
}

/* --------------------------------------------------------------- status bar */
static const char *MONTHS[12]={"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"};
static void battery_glyph(int x,int y,int h,int pct,int charging){
  int w=h/2, t=h/12; if(t<2)t=2;
  frame_rect(x,y,w,h,t,C_TXT2);
  fill_rect(x+w,y+h/4,t*2,h/2,C_TXT2);                 /* the nub */
  int inner_w=w-2*t, fill=(inner_w*(pct<0?0:(pct>100?100:pct)))/100;
  u32 c = charging? C_OK : (pct<0? C_TXT2 : (pct<=15? C_ERR : (pct<=30? C_WARN : C_OK)));
  /* draw the charge bar from the bottom up */
  int bh=(h-2*t)*fill/inner_w;
  if(bh>0) fill_rect(x+t,y+h-t-bh,inner_w,bh,c);
  if(charging){ /* a small + to make "charging" unmistakable */
    int cx=x+w/2, cy=y+h/2, arm=h/5;
    fill_rect(cx-arm,cy- (t/2),arm*2,t,C_WHITE);
    fill_rect(cx-(t/2),cy-arm,t,arm*2,C_WHITE);
  }
}
static void draw_status_bar(void){
  fill_rect(0,0,(int)SCR.w,SB_H,C_BG2);
  hline(0,SB_H-1,(int)SCR.w,C_LINE);
  struct clock_ui c; clock_read(&c);
  char hh[4],mm[4]; u2s2((u64)c.hh,hh); u2s2((u64)c.mm,mm);
  char t[8]; t[0]=hh[0];t[1]=hh[1];t[2]=':';t[3]=mm[0];t[4]=mm[1];t[5]=0;
  int ts=SB_H/9; if(ts<3)ts=3;              /* 7*ts <= SB_H, verified offline */
  text(MARGIN,(SB_H-7*ts)/2,t,ts,C_TXT);
  /* centre: Nuxel mark + link state */
  text_center((int)SCR.w/2,(SB_H-7*ts)/2,"NUXEL",ts,C_ACCENT);
  /* right: AC/USB dot, battery glyph, percent */
  int pct=SI.battery_pct;
  char pb[8]; if(pct<0){ pb[0]='-';pb[1]='-';pb[2]=0; } else { u2s((u64)pct,pb); }
  char pbs[8]; int n=0; for(int i=0;pb[i];i++)pbs[n++]=pb[i]; pbs[n++]='%'; pbs[n]=0;
  int pw=text_w(pbs,ts);
  int gh=SB_H/2;
  int right=(int)SCR.w-MARGIN;
  text_right(right,(SB_H-7*ts)/2,pbs,ts,C_TXT);
  battery_glyph(right-pw-MARGIN/2-SB_H/2,(SB_H-gh)/2,gh,pct,SI.charging);
  if(SI.on_ac||SI.charging){
    /* a filled dot = external power, as in the PWA's status bar accent */
    int r=SB_H/8; fill_rect(MARGIN+text_w(t,ts)+MARGIN, SB_H/2-r, r*2, r*2, C_OK);
  }
}

/* ---------------------------------------------------------------------- icons
 * Small procedural glyphs so the UI needs no image decoder. */
static void icon_gear(int cx,int cy,int r,u32 col){
  int t=r/4; if(t<2)t=2;
  for(int a=0;a<12;a++){
    int ax=cx + (a%2? (r*90)/100 : (r*60)/100);
    int ay=cy + (a%2? (r*90)/100 : (r*60)/100);
    fill_rect(ax-t,ay-t,t*2,t*2,col);
  }
  for(int j=-r;j<=r;j++)for(int i=-r;i<=r;i++){
    int d2=i*i+j*j;
    if(d2<=(r-t)*(r-t) && d2>=(r/3)*(r/3)) px(cx+i,cy+j,col);
  }
}
static void icon_grid(int cx,int cy,int r,u32 col){
  int s=(r*2)/3, t=r/6; if(t<2)t=2;
  for(int a=0;a<2;a++)for(int b=0;b<2;b++)
    round_rect(cx-r+a*(s+t/2)+ (a?t/2:0),cy-r+b*(s+t/2)+(b?t/2:0),s,s,t,col);
}
static void icon_terminal(int cx,int cy,int r,u32 col){
  int t=r/5; if(t<2)t=2;
  round_rect(cx-r,cy-r*7/10,r*2,r*7/5,t,col);
  for(int k=0;k<r;k++){ fill_rect(cx-r/2+k,cy-r/3+k,t,t,C_BG); }
  fill_rect(cx,cy+r/3,r/2,t,C_BG);
}
static void icon_power(int cx,int cy,int r,u32 col){
  int t=r/3; if(t<2)t=2;
  fill_rect(cx-t/2,cy-r,t,r,col);
  for(int j=-r;j<=r;j++)for(int i=-r;i<=r;i++){
    int d2=i*i+j*j;
    if(d2<=(r)*(r) && d2>=(r-t)*(r-t) && j> (s32)(-t)) px(cx+i,cy+j,col);
  }
}
static void icon_display(int cx,int cy,int r,u32 col){
  int t=r/6; if(t<2)t=2;
  round_rect(cx-r*6/10,cy-r,r*12/10,r*2,t,col);
  fill_rect(cx-r*6/10+t,cy-r+t,r*12/10-2*t,r*2-2*t,C_BG);
  fill_rect(cx-t/2,cy+r,r,t*2,col);
}
static void icon_about(int cx,int cy,int r,u32 col){
  int t=r/4; if(t<2)t=2;
  for(int j=-r;j<=r;j++)for(int i=-r;i<=r;i++) if(i*i+j*j<=r*r) px(cx+i,cy+j,col);
  text_center(cx,cy-7*t/2,"I",t*2,C_BG);
}
struct tile { const char *label; int act; void(*icon)(int,int,int,u32); };
static void icon_home(int cx,int cy,int r,u32 col){
  int t=r/5; if(t<2)t=2;
  for(int k=0;k<=r;k++) fill_rect(cx-r+k,cy-r/3+k/2,(r*2)-2*k,t,col);
  fill_rect(cx-r*7/10,cy+r/4,r*14/10,r*7/10-t,col);
}
static const struct tile TILES[6]={
  {"SETTINGS",ACT_SETTINGS,icon_gear},
  {"SYSTEM",ACT_SYSTEM,icon_grid},
  {"LOGS",ACT_LOGS,icon_terminal},
  {"DISPLAY",ACT_CTEST,icon_display},
  {"POWER",ACT_POWER,icon_power},
  {"ABOUT",ACT_ABOUT,icon_about}
};

/* ----------------------------------------------------------------- dock/nav */
static void draw_dock(void){
  int y=(int)SCR.h-DOCK_H;
  fill_rect(0,y,(int)SCR.w,DOCK_H,C_BG2);
  hline(0,y,(int)SCR.w,C_LINE);
  const char *lbl[5]={"HOME","SETTINGS","SYSTEM","LOGS","POWER"};
  const int   act[5]={ACT_HOME,ACT_SETTINGS,ACT_SYSTEM,ACT_LOGS,ACT_POWER};
  int bw=(int)SCR.w/5;
  int ts=DOCK_H/6; if(ts<3)ts=3; if(ts>8)ts=8;
  for(int i=0;i<5;i++){
    int x=i*bw;
    int active=(act[i]==ACT_HOME&&PAGE==PAGE_HOME)||(act[i]==ACT_SETTINGS&&PAGE==PAGE_SETTINGS)||
               (act[i]==ACT_SYSTEM&&PAGE==PAGE_SYSTEM)||(act[i]==ACT_LOGS&&PAGE==PAGE_LOGS)||
               (act[i]==ACT_POWER&&PAGE==PAGE_POWER);
    if(active) round_rect(x+bw/8,y+DOCK_H/5,bw*3/4,DOCK_H*3/5,DOCK_H/8,C_CARD);
    u32 col = act[i]==ACT_POWER? C_ERR : (active? C_TXT : C_TXT2);
    text_center(x+bw/2, y+(DOCK_H-7*ts)/2, lbl[i], ts, col);
    widget_add(x,y,bw,DOCK_H,act[i]);
  }
}
/* ------------------------------------------------------------------ toasts */
static void draw_toast(void){
  if(TOAST[0] && (int)mono_sec()<TOAST_UNTIL){
    int th=DOCK_H*3/4, y=(int)SCR.h-DOCK_H-th-DOCK_H/4;
    int ts=th/10; if(ts<3)ts=3;
    round_rect(MARGIN,y,(int)SCR.w-2*MARGIN,th,th/3,C_CARD_HI);
    text_center((int)SCR.w/2,y+(th-7*ts)/2,TOAST,ts,C_TXT);
  }
}
static void draw_error_banner(void){
  if(!UI_ERROR[0]) return;
  int th=DOCK_H*2/3, y=SB_H+MARGIN/2;
  int ts=th/10; if(ts<3)ts=3;
  round_rect(MARGIN,y,(int)SCR.w-2*MARGIN,th,th/3,pack_rgb(0x4a,0x10,0x10));
  text_center((int)SCR.w/2,y+(th-7*ts)/2,UI_ERROR,ts,C_TXT);
}
/* --------------------------------------------------------------- card helper */
static void card(int x,int y,int w,int h,const char *title,u32 accent){
  round_rect(x,y,w,h,MARGIN/1,C_CARD);
  fill_rect(x+MARGIN/2,y+MARGIN/2,4*SC,h-MARGIN,accent);
  if(title) text(x+MARGIN,y+MARGIN/2,title,SC*2,C_TXT2);
}
static void kv_row(int x,int y,int w,const char *k,const char *v,int vs){
  int rh=SC*11;                    /* > 7*vs + padding: rows can never overlap */
  int ks=SC; if(ks<3)ks=3;
  text(x,y+(rh-7*ks)/2,k,ks,C_TXT2);
  int keyw=text_w(k,ks)+SC*3;
  int room=w-keyw; if(room<0)room=0;
  int fit=room/(6*vs);             /* characters that actually fit */
  char tmp[160]; int n=0;
  while(v[n]&&n<fit-1&&n<150) tmp[n]=v[n],n++;
  tmp[n]=0;
  text_right(x+w,y+(rh-7*vs)/2,tmp,vs,C_TXT);
  hline(x,y+rh,w,C_LINE);
}

/* ==================================================================== pages */
static void page_home(void){
  int cx=(int)SCR.w/2;
  struct clock_ui c; clock_read(&c);
  text_spaced(cx,SB_H+MARGIN*2,"NUXEL",SC*5,SC,C_ACCENT);
  char hh[4],mm[4]; u2s2((u64)c.hh,hh); u2s2((u64)c.mm,mm);
  char t[8]; t[0]=hh[0];t[1]=hh[1];t[2]=':';t[3]=mm[0];t[4]=mm[1];t[5]=0;
  int cs=SC*14;
  text_center(cx,SB_H+MARGIN*6,t,cs,C_TXT);
  char date[40]; int n=0;
  const char *mo=MONTHS[(c.mo>=1&&c.mo<=12)?c.mo-1:0];
  for(int i=0;mo[i];i++)date[n++]=mo[i];
  date[n++]=' ';
  char dd[4]; u2s((u64)c.d,dd);
  for(int i=0;dd[i];i++)date[n++]=dd[i];
  date[n++]=','; date[n++]=' ';
  char yy[8]; u2s((u64)c.y,yy);
  for(int i=0;yy[i];i++)date[n++]=yy[i];
  date[n++]=' '; date[n++]='U'; date[n++]='T'; date[n++]='C'; date[n]=0;
  text_center(cx,SB_H+MARGIN*6+cs+SC*4,date,SC*3,C_TXT2);

  /* device card: battery + power + link */
  int cw=(int)SCR.w-2*MARGIN, chh=SC*26, cy=SB_H+MARGIN*6+cs+SC*12;
  round_rect(MARGIN,cy,cw,chh,MARGIN,C_CARD);
  int gh=SC*12, gx=MARGIN+SC*4, gy=cy+(chh-gh)/2;
  battery_glyph(gx,gy,gh,SI.battery_pct,SI.charging);
  char bs[48]; int m=0;
  if(SI.battery_ok){ char pb[8]; u2s((u64)(SI.battery_pct<0?0:SI.battery_pct),pb);
    for(int i=0;pb[i];i++)bs[m++]=pb[i]; bs[m++]='%'; bs[m++]=' '; }
  else { const char *u="NO BATTERY SYSFS "; for(int i=0;u[i];i++)bs[m++]=u[i]; }
  for(int i=0;SI.battery_status[i]&&m<44;i++)bs[m++]=SI.battery_status[i];
  bs[m]=0;
  text(gx+gh+MARGIN/2,cy+chh/2-SC*4,bs,SC*3,C_TXT);
  char us[64]; int k=0; const char *pr="LINK "; for(int i=0;pr[i];i++)us[k++]=pr[i];
  for(int i=0;SI.usb[i]&&k<60;i++)us[k++]=SI.usb[i];
  us[k]=0;
  text(gx+gh+MARGIN/2,cy+chh/2+SC*2,us,SC*2,C_TXT2);
  text_right(MARGIN+cw-SC*3,cy+chh/2-SC*4,SI.uptime,SC*3,C_TXT2);

  /* app grid: 3 columns x 2 rows, touch-friendly (mission section 7) */
  int grid_top=cy+chh+MARGIN*2;
  int avail=(int)SCR.h-grid_top-DOCK_H-MARGIN*2;
  int tw=(cw-SC*8)/3, th=avail/2-SC*4, gap=SC*4;
  for(int i=0;i<6;i++){
    int col=i%3, row=i/3;
    int x=MARGIN+col*(tw+gap/2), y=grid_top+row*(th+gap);
    round_rect(x,y,tw,th,MARGIN,C_CARD);
    TILES[i].icon(x+tw/2,y+th/3,SC*7,C_ACCENT);
    int ls=SC*2; if(ls<3)ls=3;
    text_center(x+tw/2,y+th-th/4,TILES[i].label,ls,C_TXT);
    widget_add(x,y,tw,th,TILES[i].act);
  }
}
static void page_settings(void){
  int x=MARGIN, w=(int)SCR.w-2*MARGIN, y=SB_H+MARGIN*2;
  text(x,y,"SETTINGS",SC*5,C_TXT); y+=SC*13;
  char b[64];
  char res[48]; int n=0;
  { char t[24]; u2s((u64)SCR.w,t); for(int i=0;t[i];i++)res[n++]=t[i]; res[n++]='X';
    u2s((u64)SCR.h,t); for(int i=0;t[i];i++)res[n++]=t[i]; res[n]=0; }
  kv_row(x,y,w,"PANEL",res,SC*3); y+=SC*11;
  { char t[16]; u2s((u64)SCR.stride,t); int m=0; b[0]='S';b[1]='T';b[2]='R';b[3]='I';b[4]='D';b[5]='E';b[6]='=';
    m=7; for(int i=0;t[i];i++)b[m++]=t[i]; b[m++]=' '; b[m++]='B'; u2s((u64)SCR.bpp,t);
    for(int i=0;t[i];i++)b[m++]=t[i]; b[m++]=' '; b[m++]='B';b[m++]='U';b[m++]='F';b[m++]='=';
    u2s((u64)SCR.bufs,t); for(int i=0;t[i];i++)b[m++]=t[i]; b[m]=0; }
  kv_row(x,y,w,"FRAMEBUFFER",b,SC*3); y+=SC*11;
  kv_row(x,y,w,"COLOUR ORDER",SCR.hw_abgr?"ABGR8888 HARDWARE":"FBVAR DECLARED",SC*3); y+=SC*11;
  kv_row(x,y,w,"BUILD",NUXEL_UI_REV,SC*3); y+=SC*11;
  kv_row(x,y,w,"ANIMATION",file_exists("/var/lib/nuxel/animation")?"state file present":"no state file",SC*3); y+=SC*11;
  { char s[80]; int m=0; const char *p=SI.touch; for(int i=0;p[i]&&m<70;i++)s[m++]=p[i]; s[m]=0;
    kv_row(x,y,w,"TOUCH",s,SC*3); y+=SC*11; }
  { char s[80]; int m=0; const char *p=SI.touchpath; for(int i=0;p[i]&&m<70;i++)s[m++]=p[i]; s[m]=0;
    kv_row(x,y,w,"INPUT NODE",s,SC*3); y+=SC*11; }
  y+=SC*3;
  struct { const char *l; int a; u32 c; } btns[4]={
    {"RUN COLOUR TEST",ACT_CTEST,C_ACCENT_D},
    {"SAVE SCREENSHOT",ACT_SHOT,C_ACCENT_D},
    {"RESTART UI",ACT_RESTART,C_ACCENT_D},
    {"POWER MENU",ACT_POWER,C_ACCENT_D}
  };
  int bh=SC*10;
  for(int i=0;i<4;i++){
    round_rect(x,y,w,bh,MARGIN,btns[i].c);
    text_center(x+w/2,y+(bh-SC*4)/2,btns[i].l,SC*3,C_TXT);
    widget_add(x,y,w,bh,btns[i].a);
    y+=bh+SC*3;
  }
}
static void page_system(void){
  int x=MARGIN, w=(int)SCR.w-2*MARGIN, y=SB_H+MARGIN*2;
  text(x,y,"SYSTEM",SC*5,C_TXT); y+=SC*13;
  char b[96];
  kv_row(x,y,w,"KERNEL",SI.kernel,SC*3); y+=SC*11;
  kv_row(x,y,w,"OS",SI.osname,SC*3); y+=SC*11;
  kv_row(x,y,w,"PID1",SI.pid1,SC*3); y+=SC*11;
  kv_row(x,y,w,"STATE",SI.system_state,SC*3); y+=SC*11;
  kv_row(x,y,w,"CGROUP",SI.cgroup,SC*3); y+=SC*11;
  kv_row(x,y,w,"UPTIME",SI.uptime,SC*3); y+=SC*11;
  kv_row(x,y,w,"ROOTFS",SI.root_fs,SC*3); y+=SC*11;
  kv_row(x,y,w,"BATTERY",SI.battery_status,SC*3); y+=SC*11;
  kv_row(x,y,w,"USB CONSOLE",SI.usb,SC*3); y+=SC*11;
  kv_row(x,y,w,"INPUT",SI.touch,SC*3); y+=SC*11;
  { char st[96]; int n=file_read("/var/lib/nuxel/animation",st,sizeof st);
    if(n>0){ for(int i=0;i<n;i++) if(st[i]=='\n')st[i]=' ';
      char s2[80]; int m=0; for(int i=0;st[i]&&m<70;i++)s2[m++]=st[i]; s2[m]=0;
      kv_row(x,y,w,"ANIM STAGE",s2,SC*3); y+=SC*11; } }
  { char st[128]; int n=file_read("/var/lib/nuxel/ui-stage",st,sizeof st);
    if(n>0){ for(int i=0;i<n;i++) if(st[i]=='\n')st[i]=' ';
      char s2[80]; int m=0; for(int i=0;st[i]&&m<70;i++)s2[m++]=st[i]; s2[m]=0;
      kv_row(x,y,w,"UI STAGE",s2,SC*3); y+=SC*11; } }
  (void)b;
}
/* A real log viewer: tail of the persistent Nuxel records, scrollable with the
   on-screen buttons or a vertical swipe.  Reads only files that exist. */
static void page_logs(void){
  int x=MARGIN, w=(int)SCR.w-2*MARGIN, y=SB_H+MARGIN*2;
  text(x,y,"LOGS",SC*5,C_TXT);
  int bs=SC*4;
  round_rect((int)SCR.w-MARGIN-bs*8,y-bs/2,bs*4,bs*3,MARGIN/2,C_CARD);
  text_center((int)SCR.w-MARGIN-bs*6,y+bs/2,"UP",SC*2,C_TXT);
  widget_add((int)SCR.w-MARGIN-bs*8,y-bs/2,bs*4,bs*3,ACT_LOGUP);
  round_rect((int)SCR.w-MARGIN-bs*3,y-bs/2,bs*4,bs*3,MARGIN/2,C_CARD);
  text_center((int)SCR.w-MARGIN-bs,y+bs/2,"DN",SC*2,C_TXT);
  widget_add((int)SCR.w-MARGIN-bs*3,y-bs/2,bs*4,bs*3,ACT_LOGDOWN);
  y+=SC*7;
  static char LB[8192];
  const char *src="/var/lib/nuxel/ui.log";
  if(!file_exists(src)) src="/var/log/nuxel-bootreport.txt";
  int got=file_read(src,LB,sizeof LB-1);
  if(got<=0){ text(x,y,"(no /var/lib/nuxel/ui.log or /var/log/nuxel-bootreport.txt yet)",SC*2,C_TXT2); return; }
  /* split into lines */
  static int loff[256]; int nlines=0;
  loff[0]=0; nlines=1;
  for(int i=0;i<got&&nlines<256;i++) if(LB[i]=='\n'){ LB[i]=0; loff[nlines++]=i+1; }
  if(nlines>1&&loff[nlines-1]>=got) nlines--;
  int rh=SC*5, ts=SC*2, maxrows=((int)SCR.h-DOCK_H-y-MARGIN*2)/rh;
  if(maxrows<1) maxrows=1;
  int first=nlines-maxrows-LOG_TOP; if(first<0)first=0;
  char tag[64]; int m=0;
  const char *p=src; while(*p&&m<40)tag[m++]=*p++;
  tag[m++]=' '; char t2[16]; u2s((u64)nlines,t2); for(int i=0;t2[i];i++)tag[m++]=t2[i];
  tag[m++]='L'; tag[m]=0;
  text(x,y,tag,ts,C_TXT2); y+=rh;
  for(int i=first;i<nlines&&i<first+maxrows-1;i++){
    char *l=LB+loff[i];
    /* one line, clipped to the panel; tabs expanded */
    char out[120]; int k=0;
    for(int q=0;l[q]&&k<110;q++) out[k++]= (l[q]=='\t')?' ':l[q];
    out[k]=0;
    text(x,y,out,ts,C_TXT); y+=rh;
  }
}
static void page_power(void){
  int x=MARGIN, w=(int)SCR.w-2*MARGIN, y=SB_H+MARGIN*3;
  text_center((int)SCR.w/2,y,"POWER",SC*6,C_TXT); y+=SC*14;
  text_center((int)SCR.w/2,y,"CONTROLLED ACTIONS. TAP ONCE TO ARM, TAP AGAIN TO EXECUTE.",SC*2,C_TXT2);
  y+=SC*8;
  int bh=SC*14;
  int armed=POWER_ARMED && (int)mono_sec()<(int)POWER_ARM_UNTIL;
  round_rect(x,y,w,bh,MARGIN,armed?pack_rgb(0x7a,0x1c,0x10):C_CARD);
  text_center(x+w/2, y+bh/2-SC*4, armed?"TAP AGAIN: REBOOT NOW":"REBOOT",SC*4,armed?C_WHITE:C_TXT);
  widget_add(x,y,w,bh,ACT_REBOOT); y+=bh+SC*4;
  round_rect(x,y,w,bh,MARGIN,armed?pack_rgb(0x7a,0x1c,0x10):C_CARD);
  text_center(x+w/2, y+bh/2-SC*4, armed?"TAP AGAIN: SHUT DOWN":"SHUT DOWN",SC*4,armed?C_WHITE:C_TXT);
  widget_add(x,y,w,bh,ACT_SHUTDOWN); y+=bh+SC*4;
  round_rect(x,y,w,bh,MARGIN,C_CARD);
  text_center(x+w/2, y+bh/2-SC*4,"CANCEL",SC*4,C_TXT2);
  widget_add(x,y,w,bh,ACT_HOME); y+=bh+SC*6;
  if(armed){
    char t[64]; int m=0; const char *p="ARMED FOR "; for(int i=0;p[i];i++)t[m++]=p[i];
    char s[8]; u2s((u64)(POWER_ARM_UNTIL-mono_sec()),s);
    for(int i=0;s[i];i++)t[m++]=s[i]; t[m++]='S'; t[m]=0;
    text_center((int)SCR.w/2,y,t,SC*2,C_WARN);
  }
}
static void page_about(void){
  int x=MARGIN, w=(int)SCR.w-2*MARGIN, y=SB_H+MARGIN*3;
  text_center((int)SCR.w/2,y,"NUXEL",SC*8,C_ACCENT); y+=SC*12;
  text_center((int)SCR.w/2,y,"A FEDORA LINUX PHONE",SC*3,C_TXT2); y+=SC*10;
  kv_row(x,y,w,"BUILD",NUXEL_UI_REV,SC*3); y+=SC*11;
  kv_row(x,y,w,"DEVICE","SAMSUNG GALAXY S10+ (BEYOND2LTE)",SC*3); y+=SC*11;
  kv_row(x,y,w,"SOC","EXYNOS 9820",SC*3); y+=SC*11;
  kv_row(x,y,w,"DISPLAY","1440X3040 AMOLED FBDEV",SC*3); y+=SC*11;
  kv_row(x,y,w,"GRAPHICS","DECON/DSIM FBDEV (NO DRM/KMS)",SC*3); y+=SC*11;
  kv_row(x,y,w,"SHELL","FBDEV-NATIVE (TRANSITIONAL)",SC*3); y+=SC*11;
  y+=SC*4;
  text(x,y,"THE BOOT ANIMATION IS THE ORIGINAL NUXEL MP4,",SC*2,C_TXT2); y+=SC*4;
  text(x,y,"DECODED ON THIS PANEL BY NUXEL-ANIM-PLAYER.",SC*2,C_TXT2); y+=SC*4;
  text(x,y,"PHOSH NEEDS DRM/KMS: NOT AVAILABLE ON 4.14.",SC*2,C_WARN);
}

/* ================================================================ rendering */
static void render(void){
  NWIDGETS=0;
  background();
  switch(PAGE){
    case PAGE_SETTINGS: page_settings(); break;
    case PAGE_SYSTEM:   page_system();   break;
    case PAGE_LOGS:     page_logs();     break;
    case PAGE_POWER:    page_power();    break;
    case PAGE_ABOUT:    page_about();    break;
    default:            page_home();     break;
  }
  draw_status_bar();
  draw_error_banner();
  draw_dock();
  draw_toast();
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
#define EVIOCGNAME(len) (0x80000000u|(((u32)(len))<<16)|((u32)0x06<<8)|0x45)
#define EVIOCGBIT(ev,len) (0x80000000u|(((u32)(len))<<16)|((u32)(ev)<<8)|0x20)
#define EVIOCGABS(ax) (0x80140000u|((u32)(ax)<<8)|0x40)
struct input_absinfo { s32 value,minimum,maximum,fuzz,flat,resolution; };
struct input_event { u64 sec,usec; u16 type,code; s32 value; };
struct input_dev { int fd; int maxx,maxy; int has_mt; char name[48]; int active; };
static struct input_dev IN[8]; static int NIN=0;
static int TOUCH_ORIENT=0;   /* 0: panel-native, 1: rotate 90, 2: 180, 3: 270 */

static int evdev_has(u32 *bits,int code){ return (bits[code/32]>>(code%32))&1u; }
static void input_scan(void){
  NIN=0;
  long dfd=sys4(SYS_openat,AT_FDCWD,(long)"/dev/input",O_RDONLY|O_DIRECTORY,0);
  if(dfd<0) return;
  char buf[4096];
  for(;;){
    long n=sys3(SYS_getdents64,dfd,(long)buf,sizeof buf);
    if(n<=0) break;
    for(long off=0;off<n;){
      u16 reclen=*(u16*)(buf+off+16); if(reclen<24) break;
      char *nm=buf+off+19;
      if(nm[0]=='e'&&nm[1]=='v'&&nm[2]=='e'&&nm[3]=='n'&&nm[4]=='t'&&nm[5]>='0'&&nm[5]<='9'&&NIN<8){
        char p[64]; int k=0; const char *a="/dev/input/"; while(a[k]){p[k]=a[k];k++;}
        for(int q=0;nm[q]&&k<60;q++) p[k++]=nm[q]; p[k]=0;
        long fd=sys4(SYS_openat,AT_FDCWD,(long)p,O_RDONLY|O_NONBLOCK,0);
        if(fd>=0){
          struct input_dev *d=&IN[NIN];
          d->fd=(int)fd; d->maxx=0; d->maxy=0; d->has_mt=0; d->name[0]=0; d->active=0;
          char nmb[48]; for(u64 i=0;i<sizeof nmb;i++)nmb[i]=0;
          if(sys3(SYS_ioctl,fd,EVIOCGNAME(sizeof nmb),(long)nmb)>0){
            int q=0; while(nmb[q]&&q<44){ d->name[q]=nmb[q]; q++; } d->name[q]=0;
          }
          u32 absbits[8]; for(u64 i=0;i<sizeof absbits;i++)((u8*)absbits)[i]=0;
          if(sys3(SYS_ioctl,fd,EVIOCGBIT(EV_ABS,sizeof absbits),(long)absbits)>0){
            if(evdev_has(absbits,ABS_MT_POSITION_X)){
              d->has_mt=1;
              struct input_absinfo ai; for(u64 i=0;i<sizeof ai;i++)((u8*)&ai)[i]=0;
              if(sys3(SYS_ioctl,fd,EVIOCGABS(ABS_MT_POSITION_X),(long)&ai)>=0) d->maxx=ai.maximum;
              for(u64 i=0;i<sizeof ai;i++)((u8*)&ai)[i]=0;
              if(sys3(SYS_ioctl,fd,EVIOCGABS(ABS_MT_POSITION_Y),(long)&ai)>=0) d->maxy=ai.maximum;
            }
          }
          NIN++;
        }
      }
      off+=reclen;
    }
  }
  sys1(SYS_close,dfd);
  for(int i=0;i<NIN;i++){
    char l[96]; int n=0; const char *p="INPUT_DEVICE name='";
    for(int q=0;p[q];q++)l[n++]=p[q];
    for(int q=0;IN[i].name[q]&&n<80;q++)l[n++]=IN[i].name[q];
    l[n++]='\''; l[n++]=' '; l[n++]='m'; l[n++]='t'; l[n++]='=';
    l[n++]=IN[i].has_mt?'1':'0'; l[n++]=' '; l[n++]='x'; l[n++]='m'; l[n++]='a'; l[n++]='x'; l[n++]='=';
    char t[16]; u2s((u64)IN[i].maxx,t); for(int q=0;t[q];q++)l[n++]=t[q];
    l[n++]=' '; l[n++]='y'; l[n++]='m'; l[n++]='a'; l[n++]='x'; l[n++]='=';
    u2s((u64)IN[i].maxy,t); for(int q=0;t[q];q++)l[n++]=t[q];
    l[n]=0; ui_log(l);
  }
}
static int input_primary(void){
  for(int i=0;i<NIN;i++) if(IN[i].has_mt && str_find(IN[i].name,"touch")) return i;
  for(int i=0;i<NIN;i++) if(IN[i].has_mt) return i;
  return -1;
}
/* ================================================================ utilities */
static void sleep_ms_(long ms){
  long ts[2]; ts[0]=ms/1000; ts[1]=(ms%1000)*1000000L;
  sys2(SYS_nanosleep,(long)ts,0);
}

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
  long fd=sys4(SYS_openat,AT_FDCWD,(long)path,O_WRONLY|O_CREAT|O_TRUNC,0644);
  if(fd<0){ action_ui_error("SCREENSHOT: cannot create file"); return; }
  char hdr[64]; int n=0;
  const char *p="P6\n"; for(int i=0;p[i];i++)hdr[n++]=p[i];
  char t[16]; u2s((u64)(half?w/2:w),t); for(int i=0;t[i];i++)hdr[n++]=t[i]; hdr[n++]=' ';
  u2s((u64)(half?h/2:h),t); for(int i=0;t[i];i++)hdr[n++]=t[i];
  hdr[n++]='\n'; const char *p2="255\n"; for(int i=0;p2[i];i++)hdr[n++]=p2[i];
  sys3(SYS_write,fd,(long)hdr,n);
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
      if(oi+4>CHUNK){ long rc=sys3(SYS_write,fd,(long)out,oi); if(rc<0){ sys1(SYS_close,fd); action_ui_error("SCREENSHOT: write failed"); return; } written+=(u64)oi; oi=0; }
    }
  }
  if(oi>0) sys3(SYS_write,fd,(long)out,oi);
  sys1(SYS_close,fd);
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
  text(SC*4,SC*6,"TOP=HARDWARE ABGR",ts,C_TXT); 
  text(SC*4,(int)SCR.h/2+SC*6,"BOTTOM=FBVAR ORDER",ts,C_TXT);
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
    default: break;
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
    const char *v=str_after(a,' '); const char *path = (v==a)?"/var/lib/nuxel/ui.ppm":v;
    int half = str_find(a,"small")?1:0;
    do_screenshot(path,half); toast("SCREENSHOT SAVED",3);
  }
  else if(str_starts(a,"orient")){ TOUCH_ORIENT=(int)atou_(str_after(a,' ')); }
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
    wr("NUXEL_UI_CMD commands: page=<p> go <act> act=<act> tap X Y screenshot [path] [small]"
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
static int selftest(const char *dir,int w,int h){
  sys3(SYS_mkdirat,AT_FDCWD,(long)dir,0755);   /* the harness may not have made it */
  u64 size=(u64)w*(u64)h*4u;
  void *mem=(void*)sys6(SYS_mmap,0,(long)size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(mem==MAP_FAILED){ wr("NUXEL_UI_SELFTEST_MMAP_FAILED\n"); return 20; }
  SCR.fd=-1; SCR.mem=mem; SCR.mapped=size; SCR.w=(u32)w; SCR.h=(u32)h; SCR.vh=(u32)h;
  SCR.stride=(u32)w*4u; SCR.bpp=32; SCR.bufs=1; SCR.toff=0; SCR.is_fb=0; SCR.hw_abgr=1;
  SCR.canvas=mem; VISIBLE=mem; CURBUF=0;
  SC=w/360; if(SC<2)SC=2;
  SB_H=36*SC; DOCK_H=80*SC; MARGIN=16*SC;
  palette_init(); info_collect();
  for(int p=0;p<PAGE_MAX;p++){
    PAGE=p; LOG_TOP=0; TOAST[0]=0; UI_ERROR[0]=0;
    render();
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
  wr("NUXEL_UI_SELFTEST_OK pages="); { char t[8]; u2s(PAGE_MAX,t); wr(t); wr(" size=");
    char t2[16]; u2s((u64)w,t2); wr(t2); wr("x"); char t3[16]; u2s((u64)h,t3); wr(t3); wr("\n"); }
  return 0;
}

/* ===================================================================== main */
static int A_ONCE=0, A_SELFTEST=0, A_SW=1440, A_SH=3040;
static const char *A_SDIR=".";
static void parse_args(long argc,char **argv){
  for(long i=1;i<argc;i++){
    const char *a=argv[i];
    if(str_starts(a,"--selftest")){ A_SELFTEST=1; if(a[10]=='=') A_SDIR=a+11; }
    else if(str_starts(a,"--size=")){ const char *v=a+7; A_SW=(int)atou_(v); A_SH=(int)atou_(str_after(v,'x')); }
    else if(str_starts(a,"--once")) A_ONCE=1;
    else if(str_starts(a,"--hworder=")) SCR.hw_abgr = (a[10]=='f')?0:1;
    else if(str_starts(a,"--page=")){
      const char *v=a+7; for(int p=0;p<PAGE_MAX;p++) if(str_starts(v,PAGE_NAME[p])) PAGE=p;
    }
    else if(str_starts(a,"--statedir=")) A_SDIR=a+11;
    else if(str_starts(a,"--help")||str_starts(a,"-h")){
      wr("usage: nuxel-ui [--selftest=DIR] [--size=WxH] [--once] [--hworder=abgr|fbvar]"
         " [--page=home|settings|system|logs|power|about]\n");
      sys1(SYS_exit_group,0);
    }
  }
}
void nuxel_ui_start(long *sp);
__asm__(
".text\n.globl _start\n.type _start,%function\n"
"_start:\n  mov x0, sp\n  b nuxel_ui_start\n");
void nuxel_ui_start(long *sp){
  long argc=sp[0]; char **argv=(char**)&sp[1];
  log_open();
  SCR.hw_abgr=1;      /* A23: the DECON commit path is ABGR_8888.  This bit was
                         never initialised in the A23 build, so the shipped UI
                         packed with the WRONG (fb_var) order -- caught on hardware
                         as NUXEL_UI_HW_ABGR=0 in dmesg. */
  parse_args(argc,argv);
  if(A_SELFTEST){ int rc=selftest(A_SDIR,A_SW,A_SH); sys1(SYS_exit_group,(long)rc); }
  wr("NUXEL_UI_STARTING rev=" NUXEL_UI_REV "\n");

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
  SC=(int)(SCR.w/360); if(SC<2)SC=2;
  SB_H=36*SC; DOCK_H=80*SC; MARGIN=16*SC;   /* the PWA's design tokens, in px */
  wrn("NUXEL_UI_PANEL_W",SCR.w);   wrn("NUXEL_UI_PANEL_H",SCR.h);
  wrn("NUXEL_UI_PANEL_STRIDE",SCR.stride); wrn("NUXEL_UI_PANEL_BPP",SCR.bpp);
  wrn("NUXEL_UI_PANEL_BUFFERS",SCR.bufs);  wrn("NUXEL_UI_SCALE",(u64)SC);
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
  int PRIMARY=input_primary();
  if(PRIMARY>=0){
    char l[96]; int n=0; const char *p="TOUCH_PRIMARY="; for(int i=0;p[i];i++)l[n++]=p[i];
    for(int i=0;IN[PRIMARY].name[i]&&n<80;i++)l[n++]=IN[PRIMARY].name[i];
    l[n]=0; ui_log(l);
    toast("TOUCHSCREEN FOUND",3);
  } else {
    ui_log("TOUCH_POINTING_DEVICE_NONE (console channel can still drive the UI)");
  }

  /* --- main loop: event driven, one repaint per second when idle --------- */
  int last_sec=-1, last_info=(int)mono_sec(), last_assert=(int)mono_sec();
  int down=0, down_x=0, down_y=0, last_x=0, last_y=0, moved=0, slot_active=0;
  for(;;){
    /* touch */
    if(PRIMARY>=0){
      struct input_event ev;
      for(;;){
        long n=sys3(SYS_read,IN[PRIMARY].fd,(long)&ev,sizeof ev);
        if(n<(long)sizeof ev) break;
        if(ev.type==EV_ABS){
          if(ev.code==ABS_MT_POSITION_X||ev.code==ABS_MT_POSITION_Y){
            if(ev.code==ABS_MT_POSITION_X) last_x=ev.value; else last_y=ev.value;
            slot_active=1;
          }
        } else if(ev.type==EV_KEY && ev.code==BTN_TOUCH){
          if(ev.value==1){ down=1; moved=0; down_x=last_x; down_y=last_y; }
          else if(ev.value==0){
            if(down){
              int sx,sy,sx0,sy0;
              int mi=PRIMARY;
              int mx=IN[mi].maxx, my=IN[mi].maxy;
              int x=last_x,y=last_y;
              if(TOUCH_ORIENT==0){
                sx=mx?(x*((int)SCR.w-1))/mx:x; sy=my?(y*((int)SCR.h-1))/my:y;
                sx0=mx?(down_x*((int)SCR.w-1))/mx:down_x; sy0=my?(down_y*((int)SCR.h-1))/my:down_y;
              } else if(TOUCH_ORIENT==1){
                sx=my?((my-y)*((int)SCR.w-1))/my:x; sy=mx?(x*((int)SCR.h-1))/mx:y;
                sx0=my?((my-down_y)*((int)SCR.w-1))/my:down_x; sy0=mx?(down_x*((int)SCR.h-1))/mx:down_y;
              } else if(TOUCH_ORIENT==2){
                sx=mx?((mx-x)*((int)SCR.w-1))/mx:x; sy=my?((my-y)*((int)SCR.h-1))/my:y;
                sx0=mx?((mx-down_x)*((int)SCR.w-1))/mx:down_x; sy0=my?((my-down_y)*((int)SCR.h-1))/my:down_y;
              } else {
                sx=my?(y*((int)SCR.w-1))/my:x; sy=mx?((mx-x)*((int)SCR.h-1))/mx:y;
                sx0=my?(down_y*((int)SCR.w-1))/my:down_x; sy0=mx?((mx-down_x)*((int)SCR.h-1))/mx:down_y;
              }
              int dx=sx-sx0, dy=sy-sy0; if(dx<0)dx=-dx; if(dy<0)dy=-dy;
              if(dx<SC*3&&dy<SC*3){
                int ac=hit_test(sx,sy);
                if(ac) act_do(ac);
                else { char m[48]; int k=0; const char *q="TAP "; for(int i=0;q[i];i++)m[k++]=q[i];
                  char t[16]; u2s((u64)sx,t); for(int i=0;t[i];i++)m[k++]=t[i]; m[k++]=',';
                  u2s((u64)sy,t); for(int i=0;t[i];i++)m[k++]=t[i]; m[k]=0; toast(m,2); }
              } else if(dy*2>dx){
                if(dy>0) act_do(ACT_LOGDOWN); else act_do(ACT_LOGUP);
              } else { PAGE=(PAGE+1)%PAGE_MAX; }
              down=0;
            }
          }
        }
        if(ev.type==EV_KEY && ev.code==BTN_TOUCH && ev.value==1) moved=1;
      }
      (void)slot_active;(void)moved;
    }
    /* console commands */
    cmd_drain();
    if(QUIT_REQUEST) break;

    /* periodic refresh + self-heal */
    int now=(int)mono_sec();
    int dirty=0;
    if(now!=last_sec){ last_sec=now; dirty=1; }
    if(TOAST[0] && now>=TOAST_UNTIL && TOAST_UNTIL){ TOAST[0]=0; dirty=1; }
    if(now-last_info>=5){ info_collect(); last_info=now; dirty=1; }
    if(now-last_assert>=2){ fb_assert_panel(); last_assert=now; }
    if(POWER_ACTION) break;
    if(dirty) ui_frame();
    /* wait for input/commands or the next 250 ms tick */
    {
      struct pollfd_ { int fd; short ev,rev; } pfd[2]; int np=0;
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
