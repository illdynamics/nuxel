/* Nuxel S10+ first-light framebuffer test + spinning penguin.  AArch64
 * freestanding/static, no libc, no login, no compositor.  Runs from the
 * initramfs ~2 s after kernel entry and paints the real AMOLED panel through
 * /dev/fb0, then animates a rotating Tux for a few seconds.
 *
 * A15 changes (2026-10-15) - all driven by the A14 hardware capture:
 *   * every geometry field the driver reports is logged to fd 2 (= /dev/kmsg
 *     inside the initramfs) so the DECON window and the fbdev can be compared
 *     from the ram console alone: a silent exit is not evidence of anything.
 *   * the frame is painted into EVERY buffer of the virtual framebuffer
 *     (yres_virtual is 2x yres on this panel: 1440x6080 with stride 5760), so a
 *     DECON scanning the alternate buffer still shows the test pattern.  A14
 *     painted only the active yoffset buffer and the panel stayed dark.
 *   * the design is deliberately unmistakable - bright colour bars across the
 *     top, a large bright NUXEL wordmark and a white-outlined penguin on a deep
 *     blue field (never "black"), no full-white screen (AMOLED burn-in).
 *   * the penguin spins: 12 rotated frames at 250 ms each, then the last frame
 *     stays on screen.
 * Still a DISPLAY DIAGNOSTIC, NOT Phosh.
 */
#ifdef NUXEL_FIRSTLIGHT_HOST
/* Host build: only the pure NUXSPL01 parser + renderer are exercised, so the
   raw-syscall layer is replaced by stdio.  See tools/s10plus/a27/test-firstlight.c
   (same discipline as nuxel-anim-player.c's NUXEL_HOST self-test). */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#endif

typedef unsigned long u64;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef signed int s32;

#ifdef NUXEL_FIRSTLIGHT_HOST
/* Host build: the pure parser/renderer never emit to the ram console; the test
   harness reports with printf. */
static void wr(const char*t){ fputs(t,stdout); }
static void wrn(const char*t,u64 v){ printf("%s=%llu\n",t,(unsigned long long)v); }
static void wrh(const char*t,u64 v){ printf("%s=0x%llx\n",t,(unsigned long long)v); }
#else
static long sys(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0" : "+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");return x0;
}
static long op(const char*s){return sys(56,-100,(long)s,2,0,0,0);}          /* openat O_RDWR */
static int  io(long fd,long request,void* p){return (int)sys(29,fd,request,(long)p,0,0,0);}
static void closefd(long fd){sys(57,fd,0,0,0,0,0);}
static long op_rd(const char*p){return sys(56,-100,(long)p,0,0,0,0);} /* openat O_RDONLY */
static long seek_end(long fd){return sys(62,fd,0,2,0,0,0);}            /* lseek SEEK_END  */
static long map_rd(long fd,long len){return sys(222,0,len,1,2,fd,0);}  /* PROT_READ MAP_PRIVATE */
static void unmap(long p,long len){sys(215,p,len,0,0,0,0);}
static long mkfile(const char*p){return sys(56,-100,(long)p,0x241,0600,0,0);} /* openat CREAT|TRUNC|WRONLY */
static int  fexists(const char*p){long f=sys(56,-100,(long)p,0,0,0,0); if(f<0)return 0; closefd(f); return 1;}
static long getpid_(void){return sys(172,0,0,0,0,0,0);}
static void cat2(char*d,const char*a,const char*b){int i=0;while(a[i]){d[i]=a[i];i++;}int j=0;while(b[j]){d[i++]=b[j++];}d[i]=0;}
static void quit(int code){sys(93,code,0,0,0,0,0);for(;;){}}
static void sleep_ms(long ms){long ts[2];ts[0]=ms/1000;ts[1]=(ms%1000)*1000000L;sys(101,(long)ts,0,0,0,0,0);}
static void wr(const char*s){u64 n=0;while(s[n])n++;if(n)sys(64,2,(long)s,n,0,0,0);}
/* A21 FIX: A16..A20 counted the tag length but NEVER COPIED the tag bytes into
   the buffer, so every numeric evidence line (xres/stride/smem_len/READBACK)
   reached the ram console as uninitialised stack memory + the digits.  The
   measurement was always taken correctly; only the label was garbage, which is
   why no capture in this project ever contained a readable geometry value. */

static void wrn(const char*tag,u64 v){char b[96];int i=0;while(tag[i]&&i<72){b[i]=tag[i];i++;}b[i++]='=';char d[24];int k=0;if(!v)d[k++]='0';while(v){d[k++]='0'+(int)(v%10);v/=10;}while(k)b[i++]=d[--k];b[i++]='\n';sys(64,2,(long)b,i,0,0,0);}
static void wrh(const char*tag,u64 v){char b[96];int i=0;while(tag[i]&&i<70){b[i]=tag[i];i++;}b[i++]='=';b[i++]='0';b[i++]='x';char d[20];int k=0;if(!v)d[k++]='0';while(v){int h=(int)(v&15);d[k++]=h<10?('0'+h):('a'+h-10);v>>=4;}while(k)b[i++]=d[--k];b[i++]='\n';sys(64,2,(long)b,i,0,0,0);}

#endif /* NUXEL_FIRSTLIGHT_HOST / syscall layer */

struct fb_bitfield{u32 offset,length,msb_right;};
struct fb_var{u32 xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bits_per_pixel,grayscale;
 struct fb_bitfield red,green,blue,transp;u32 nonstd,activate,height,width,accel_flags;
 u32 pixclock,left_margin,right_margin,upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace,reserved[4];};
struct fb_fix{char id[16];u64 smem_start;u32 smem_len,type,type_aux,visual;u16 xpanstep,ypanstep,ywrapstep;u32 line_length;u64 mmio_start;u32 mmio_len,accel;u16 capabilities,reserved[2];};

static u8 *fb;          /* mmap base of the whole virtual framebuffer */
static u8 *base;        /* current paint target (fb + TOFF*STRIDE)      */
static u64 mapped;
static u32 W,H,YVIR,STRIDE,BPP,TOFF;
static const char *STATE_DIR;   /* A21: where the hold painter publishes its pid and looks for a stop */
static struct fb_var V;

static u32 pack(u32 r,u32 g,u32 b){
 u32 R=(r*((1u<<V.red.length)-1)+127)/255, G=(g*((1u<<V.green.length)-1)+127)/255, B=(b*((1u<<V.blue.length)-1)+127)/255;
 return (R<<V.red.offset)|(G<<V.green.offset)|(B<<V.blue.offset);}
static void pixel(int x,int y,u32 color){
 if(x<0||y<0||(u32)x>=W||(u32)y>=H)return;
 u64 off=(u64)(y+TOFF)*STRIDE+(u64)x*(BPP/8);
 if(off+BPP/8>mapped)return;
 if(BPP==32){*(volatile u32*)(fb+off)=color;}
 else if(BPP==16){*(volatile u16*)(fb+off)=(u16)color;}
 else if(BPP==24){volatile u8*p=fb+off;p[0]=color&0xff;p[1]=(color>>8)&0xff;p[2]=(color>>16)&0xff;}
}
static void rect(int x,int y,int w,int h,u32 col){
 int x0=x<0?0:x,y0=y<0?0:y,x1=x+w>(int)W?(int)W:x+w,y1=y+h>(int)H?(int)H:y+h;
 for(int yy=y0;yy<y1;yy++)for(int xx=x0;xx<x1;xx++)pixel(xx,yy,col);}

/* ---- 5x7 bitmap font (as in the A12-A14 diagnostic) ---- */
static const char chars[]=" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+:-.";
static const u8 glyph[][7]={
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
 {0,4,4,31,4,4,0}, {0,0,4,0,4,0,0}, {0,0,0,31,0,0,0}, {0,0,0,0,0,6,6}
};
static void text(int x,int y,const char *t,int s,u32 c){
 for(;*t;t++,x+=6*s){int idx=0;while(chars[idx]&&chars[idx]!=*t)idx++;
 if(!chars[idx])idx=0;
 for(int row=0;row<7;row++)for(int col=0;col<5;col++)
 if(glyph[idx][row] & (1<<(4-col)))rect(x+col*s,y+row*s,s,s,c);}}
static void center(int y,const char*t,int s,u32 c){int n=0;while(t[n])n++;text(((int)W-6*n*s)/2,y,t,s,c);}

/* ---- penguin ---- */
/* local penguin coordinate system: u right, v down, 0,0 at the body centre.
 * R(cx) returns a packed colour for a local point, or -1 for "background". */
#define IN_E(u,v,cx,cy,rx,ry) (((u-(cx))*(u-(cx))*100)/((rx)*(rx))+((v-(cy))*(v-(cy))*100)/((ry)*(ry)) <= 100)
static const int CS[12]={1024,886,512,0,-512,-886,-1024,-886,-512,0,512,886};
static const int SN[12]={0,512,886,1024,886,512,0,-512,-886,-1024,-886,-512};
static u32 PU0,PU1,PU2,PU3,PU4;   /* white ring, body, belly, orange, black */

static int penguin_col(int u,int v){
 int uv=v+0;
 if(IN_E(u,uv,-46,124,32,16)||IN_E(u,uv,46,124,32,16)) return 2;  /* orange feet */
 if(IN_E(u,uv,20,-58,20,13)) return 2;                             /* orange beak */
 if(IN_E(u,uv,-92,10,26,68)||IN_E(u,uv,92,10,26,68)) return 3;  /* wings: body colour */
 if(IN_E(u,uv,0,-92,52,52)){                          /* head */
   if(IN_E(u,uv,-20,-98,11,11)||IN_E(u,uv,20,-98,11,11)) return 0;  /* eyes (white) */
   if(IN_E(u,uv,-20,-98,5,5)||IN_E(u,uv,20,-98,5,5)) return 4;      /* pupils */
   return 3;
 }
 if(IN_E(u,uv,0,10,96,124)){                          /* body + white outline */
   if(IN_E(u,uv,0,40,58,74)) return 0;                /* belly */
   if(IN_E(u,uv,0,10,88,116)) return 3;
   return 1;
 }
 return -1;
}
static void penguin(int cx,int cy,int half,int frame,u32 bgc){
 int c=CS[frame],s=SN[frame];
 int x0=cx-half,y0=cy-half,x1=cx+half,y1=cy+half;
 if(x0<0)x0=0; if(y0<0)y0=0; if(x1>(int)W)x1=(int)W; if(y1>(int)H)y1=(int)H;
 for(int y=y0;y<y1;y++){
   int dv=y-cy;
   for(int x=x0;x<x1;x++){
     int du=x-cx;
     int u=(du*c+dv*s)>>10, v=(-du*s+dv*c)>>10;
     int k=penguin_col(u,v);
     if(k==-1){ if(bgc!=0xffffffffu) pixel(x,y,bgc); continue; }
     pixel(x,y, k==0?PU0 : k==1?PU1 : k==2?PU2 : k==3?PU3 : PU4);
   }
 }
}


/* ============================================================================
 * A27 — NUXSPL01 FIRST LIGHT: the animation's frame 0 lights the panel.
 *
 * WHY: tools/s10plus/a26/make-firstlight-asset.py extracts frame 0 of the ORIGINAL
 * MP4-derived container (NUXANM01) into a standalone, deterministic asset:
 *
 *    0    8  magic "NUXSPL01"
 *    8    4  u32 width            1080
 *   12    4  u32 height           1920
 *   16    4  u32 palette_count    256
 *   20    4  u32 flags            bit0 = index plane is raw DEFLATE
 *   24    4  u32 blob_size        size of the index plane as stored
 *   28    4  u32 reserved
 *   32  ...  palette            palette_count x RGB565 LE (verbatim from NUXANM01)
 *   ..  ...  index plane        width*height palette indices
 *
 * Everything below is deliberately the SAME maths nuxel-anim-player.c uses for
 * its first committed frame (palette expansion into the DECON's real ABGR_8888
 * order, integer nearest-neighbour spans, letterbox filled with the artwork's own
 * most-frequent colour, every virtual buffer painted).  The consequence is the
 * property the mission actually needs: the frame that lights the panel at first
 * light is byte-identical to the frame the player commits seconds later, so the
 * handoff is not a transition at all -- nothing to flash, no black gap, no colour
 * change, no second graphics implementation to disagree with.
 *
 * The parser is pure (no syscalls, no I/O), so tools/s10plus/a27/test-firstlight.c
 * exercises it and the renderer against a reference implementation off-device.
 * ==========================================================================*/
#define SPL_MAX_DIM 8192

#define SPL_OK            0
#define SPL_ERR_SHORT     1
#define SPL_ERR_MAGIC     2
#define SPL_ERR_RESERVED  3
#define SPL_ERR_FLAGS     4
#define SPL_ERR_PALETTE   5
#define SPL_ERR_DIM       6
#define SPL_ERR_OVERFLOW  7
#define SPL_ERR_TRUNC     8
#define SPL_ERR_SIZE      9

struct spl_frame { u32 w,h,paln,flags,blob; const u8 *pal; const u8 *idx; u64 bytes; };

static u32 spl_rd32(const u8*p){ return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24); }

static const char *spl_err_name(int e){
 switch(e){
  case SPL_ERR_SHORT:    return "SHORT_HEADER";
  case SPL_ERR_MAGIC:    return "BAD_MAGIC";
  case SPL_ERR_RESERVED: return "RESERVED_NOT_ZERO";
  case SPL_ERR_FLAGS:    return "UNSUPPORTED_FLAGS";
  case SPL_ERR_PALETTE:  return "BAD_PALETTE";
  case SPL_ERR_DIM:      return "BAD_DIMENSIONS";
  case SPL_ERR_OVERFLOW: return "BUFFER_SIZE_OVERFLOW";
  case SPL_ERR_TRUNC:    return "TRUNCATED_PIXEL_PLANE";
  case SPL_ERR_SIZE:     return "TRAILING_BYTES";
  default:               return "OK";
 }
}

static int spl_parse(const u8 *d,u64 len,struct spl_frame *f){
 const char *mg="NUXSPL01";
 if(len<32) return SPL_ERR_SHORT;
 for(int i=0;i<8;i++) if(d[i]!=(u8)mg[i]) return SPL_ERR_MAGIC;
 f->w=spl_rd32(d+8); f->h=spl_rd32(d+12); f->paln=spl_rd32(d+16);
 f->flags=spl_rd32(d+20); f->blob=spl_rd32(d+24);
 if(spl_rd32(d+28)) return SPL_ERR_RESERVED;
 /* bit0 = the index plane is raw DEFLATE.  This freestanding painter has no
    inflate (the animation player carries the only decoder), so a compressed
    asset is REJECTED by name instead of being painted as garbage.  The shipped
    asset is uncompressed on purpose: 1.9 MB vs an 18.5 MB container. */
 if(f->flags) return SPL_ERR_FLAGS;
 if(f->paln<2||f->paln>256) return SPL_ERR_PALETTE;
 if(!f->w||!f->h||f->w>SPL_MAX_DIM||f->h>SPL_MAX_DIM) return SPL_ERR_DIM;
 if((u64)f->w*(u64)f->h>64000000ull) return SPL_ERR_OVERFLOW;
 if(f->blob!=(u32)((u64)f->w*(u64)f->h)) return SPL_ERR_DIM;
 u64 need=32ull+(u64)f->paln*2ull+(u64)f->w*(u64)f->h;
 if(len<need) return SPL_ERR_TRUNC;
 if(len>need) return SPL_ERR_SIZE;
 f->pal=d+32; f->idx=d+32+(u64)f->paln*2ull; f->bytes=need;
 /* A palette of one single colour (or an all-zero palette) is not the
    animation's frame 0; refuse it rather than light the panel with a flat
    rectangle that looks like a hang. */
 { u16 seen[24]; int n=0;
   for(u32 i=0;i<f->paln;i++){
     u16 c=(u16)((u16)f->pal[i*2]|((u16)f->pal[i*2+1]<<8)); int dup=0;
     for(int j=0;j<n;j++) if(seen[j]==c){ dup=1; break; }
     if(!dup&&n<24) seen[n++]=c;
   }
   if(n<2) return SPL_ERR_PALETTE; }
 return SPL_OK;
}

/* Per-source-pixel destination spans: copied verbatim from nuxel-anim-player.c
   (nuxel_anim_start: "DW=PW; DH=...; for(x) DX0[x]=OX+x*DW/AW ...").  Integer
   only, so the early frame and the player's first commit cannot differ by a
   rounding step even in principle. */
static u32 SPDX0[SPL_MAX_DIM],SPDX1[SPL_MAX_DIM],SPDY0[SPL_MAX_DIM],SPDY1[SPL_MAX_DIM];
static u32 SPDST[256];

static u32 SPDBG_INDEX,SPDBG_DST,SPLDW,SPLDH,SPLOX,SPLOY;

static void spl_span(u8 *row,u32 x0,u32 x1,u32 color,u32 bytespp){
 if(bytespp==4){ volatile u32*p=(volatile u32*)(row+(u64)x0*4); for(u32 x=x0;x<x1;x++)*p++=color; }
 else if(bytespp==2){ volatile u16*p=(volatile u16*)(row+(u64)x0*2); for(u32 x=x0;x<x1;x++)*p++=(u16)color; }
 else if(bytespp==3){ volatile u8*p=row+(u64)x0*3; for(u32 x=x0;x<x1;x++){p[0]=color&0xff;p[1]=(color>>8)&0xff;p[2]=(color>>16)&0xff;p+=3;} }
}

/* Render the first-light frame into EVERY virtual buffer of the mapped panel.
   Returns 0, or a negative reason code.  `mapped` is the byte size actually
   mapped, so a bogus STRIDE*YVIR can never write outside the mapping. */
static int spl_render(const struct spl_frame *f,u8 *fbp,u32 W,u32 H,u32 YVIR,
                      u32 STRIDE,u32 bpp,u64 mapped,u32 bufs){
 u32 bytespp=bpp/8;
 if(!bytespp||bytespp>4) return -1;
 if(f->w>SPL_MAX_DIM||f->h>SPL_MAX_DIM) return -2;
 if(!W||!H||STRIDE<(u32)((u64)W*bytespp)) return -2;
 /* palette: RGB565 (verbatim from NUXANM01) expanded ONCE, with the same
    pack() the rest of this binary uses -- which by now carries the A23 hardware
    order (R@0 G@8 B@16 for ABGR_8888), not the driver's declared bitfields. */
 for(u32 i=0;i<f->paln;i++){
   u32 c=(u32)((u32)f->pal[i*2]|((u32)f->pal[i*2+1]<<8));
   u32 r=((c>>11)&31u)*255u/31u, g=((c>>5)&63u)*255u/63u, b=(c&31u)*255u/31u;
   SPDST[i]=pack(r,g,b);
 }
 u32 DW=W, DH=(u32)(((u64)f->h*(u64)W)/(u64)f->w);
 if(DH>H){ DH=H; DW=(u32)(((u64)f->w*(u64)H)/(u64)f->h); }
 if(!DW||!DH) return -3;
 u32 OX=(W-DW)/2, OY=(H-DH)/2;
 u32 maxx=STRIDE/bytespp; if(maxx>W) maxx=W;
 for(u32 x=0;x<f->w;x++){
   u32 a=OX+(u32)(((u64)x*(u64)DW)/(u64)f->w);
   u32 b=OX+(u32)(((u64)(x+1)*(u64)DW)/(u64)f->w);
   if(b<=a)b=a+1; if(b>W)b=W; if(a>=W)a=W-1; if(b>maxx)b=maxx;
   SPDX0[x]=a; SPDX1[x]=b;
 }
 for(u32 y=0;y<f->h;y++){
   u32 a=OY+(u32)(((u64)y*(u64)DH)/(u64)f->h);
   u32 b=OY+(u32)(((u64)(y+1)*(u64)DH)/(u64)f->h);
   if(b<=a)b=a+1; if(b>H)b=H; if(a>=H)a=H-1;
   SPDY0[y]=a; SPDY1[y]=b;
 }
 /* Letterbox: the artwork's OWN most frequent index, exactly as the player does
    (an arbitrary black bar would be an invented visible rectangle). */
 { u64 hist[256]; u32 n=f->paln>256u?256u:f->paln;
   for(u32 i=0;i<n;i++) hist[i]=0;
   for(u64 i=0;i<(u64)f->w*(u64)f->h;i++) hist[f->idx[i]&255u]++;
   u32 best=0; for(u32 i=1;i<n;i++) if(hist[i]>hist[best]) best=i;
   SPDBG_INDEX=best; SPDBG_DST=SPDST[best]; }
 for(u32 buf=0;buf<bufs;buf++){
   u32 y0=buf*H;
   if((u64)(y0+H)*STRIDE>mapped) break;
   for(u32 y=0;y<H;y++){
     u8 *row=fbp+(u64)(y0+y)*STRIDE;
     spl_span(row,0,maxx,SPDBG_DST,bytespp);
   }
   for(u32 sy=0;sy<f->h;sy++){
     u8 *src=(u8*)f->idx+(u64)sy*(u64)f->w;
     u32 dy0=SPDY0[sy],dy1=SPDY1[sy];
     for(u32 y=dy0;y<dy1;y++){
       u8 *row=fbp+(u64)(y0+y)*STRIDE;
       for(u32 sx=0;sx<f->w;sx++) spl_span(row,SPDX0[sx],SPDX1[sx],SPDST[src[sx]],bytespp);
     }
   }
 }
 SPLDW=DW; SPLDH=DH; SPLOX=OX; SPLOY=OY;
 return 0;
}

static int paint(void){
 u32 bg=pack(10,32,58), white=pack(236,242,250), orange=pack(255,138,27), black=pack(4,7,12);
 u32 bars[4]; bars[0]=pack(240,240,240); bars[1]=pack(220,40,40); bars[2]=pack(40,190,80); bars[3]=pack(50,110,240);
 PU0=white;PU1=white;PU2=orange;PU3=black;PU4=black;
 rect(0,0,W,H,bg);
 int bh=(int)H/48; if(bh<8)bh=8;
 for(int i=0;i<4;i++) rect((int)(W/4)*i,0,(int)(W/4)+1,bh,bars[i]);
 int s=(int)W/170; if(s<2)s=2; if(s>14)s=14;
 center((int)H/16,"NUXEL",s*3,white);
 center((int)H/16+22*s,"LINUX PHONE",s,orange);
 int pcx=(int)W/2, pcy=(int)(H*55/100);
 int psize=(int)W/9; if(psize<40)psize=40;
 penguin(pcx,pcy,psize,0,0xffffffffu);
 center((int)(H*84/100),"FIRST LIGHT - S10+ AMOLED",s,white);
 center((int)(H*84/100)+10*s,"ARM64 - BEYOND2LTE",(s/2)>0?(s/2):1,orange);
 return 0;
}

#ifndef NUXEL_FIRSTLIGHT_HOST
#define FBIOGET_VSCREENINFO 0x4600
#define FBIOPUT_VSCREENINFO 0x4601
#define FBIOGET_FSCREENINFO 0x4602
#define FBIOPAN_DISPLAY     0x4606
#define FBIOBLANK           0x4611
#define FB_ACTIVATE_NOW     0x0080
#define FB_BLANK_UNBLANK    0

static int ioc(long fd,long req,long arg){return (int)sys(29,fd,req,arg,0,0,0);}
static void wrc(const char*tag,long v){ if(v<0) wrh(tag,(u64)v); else wrn(tag,(u64)v); }

/* Paint one full screen into EVERY buffer of the virtual framebuffer.
   The S10+ panel reports 1440x3040 with yres_virtual=6080 and stride 5760, so
   the DECON may be scanning the alternate buffer; leaving a buffer untouched is
   what made A14's frame invisible.  Returns the number of buffers painted. */
static int paint_all_buffers(void){
 int nb=0;
 /* Hard bound: a bogus yres_virtual must never turn this into an unbounded
    repaint loop inside the initramfs and hang the boot. */
 for(u32 off=0; off+H<=YVIR && nb<4; off+=H){ TOFF=off; paint(); nb++; }
 TOFF=0; paint();
 return nb;
}

static int PCX,PCY,PSIZE;
static int NBUFS=1;
/* The DECON may be scanning ANY of the virtual framebuffer's buffers, so the
   animated frame must be drawn into every buffer that was painted, not just
   buffer 0 (A14 painted only the active yoffset and stayed dark). */
static void spin_frame(int f){
 u32 bg=pack(10,32,58);
 int n=NBUFS<1?1:NBUFS;
 for(int b=0;b<n;b++){ TOFF=(u32)b*H; penguin(PCX,PCY,PSIZE,f,bg); }
 TOFF=0;
}

/* Command-mode DECON: the controller only latches a new frame when the fbdev
   asks it to.  A15 painted the memory and never asked, and the capture shows no
   `decon_enable`/`FRAME_DONE` for the whole Nuxel boot (only probe).  Try every
   documented way to make the driver commit the window and LOG each return code,
   so the next capture states which one the Samsung driver accepts.  FBIOBLANK
   with FB_BLANK_UNBLANK turns the panel ON; it never disables a safety. */
static void scanout_commit(long fd,int verbose){
 int r1,r2,r3;
 r1 = ioc(fd,FBIOBLANK,FB_BLANK_UNBLANK);
 V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
 r2 = ioc(fd,FBIOPUT_VSCREENINFO,(long)&V);
 r3 = ioc(fd,FBIOPAN_DISPLAY,(long)&V);
 if(verbose){
   wrc("NUXEL_FB_UNBLANK_rc",r1);
   wrc("NUXEL_FB_ACTIVATE_rc",r2);
   wrc("NUXEL_FB_PAN_rc",r3);
 }
}

/* A21: deterministic colour round-trip.  Packs pure red/green/blue/white/black
   with whatever packing is in force and reads the u32 back, so the conversion the
   animation player shares is provable from the console alone.  A27 moved this
   into a function so the FIRST-LIGHT path can run it BEFORE the frame is painted:
   these five pixels live in the letterbox and must not survive on the glass. */
static void color_probe(void){
 u32 cR=pack(255,0,0),cG=pack(0,255,0),cB=pack(0,0,255),cW=pack(255,255,255),cK=pack(0,0,0);
 volatile u32*probe=(volatile u32*)(fb+(u64)(H-4)*STRIDE);
 probe[0]=cR; probe[1]=cG; probe[2]=cB; probe[3]=cW; probe[4]=cK;
 wrn("NUXEL_FB_COLOR_PACK_R_expected",cR); wrn("NUXEL_FB_COLOR_PACK_R_readback",probe[0]);
 wrn("NUXEL_FB_COLOR_PACK_G_expected",cG); wrn("NUXEL_FB_COLOR_PACK_G_readback",probe[1]);
 wrn("NUXEL_FB_COLOR_PACK_B_expected",cB); wrn("NUXEL_FB_COLOR_PACK_B_readback",probe[2]);
 wrn("NUXEL_FB_COLOR_PACK_W_expected",cW); wrn("NUXEL_FB_COLOR_PACK_W_readback",probe[3]);
 wrn("NUXEL_FB_COLOR_PACK_K_expected",cK); wrn("NUXEL_FB_COLOR_PACK_K_readback",probe[4]);
}

/* entry point: read argc/argv off the initial process stack (there is no libc
   here, so the C `main` convention does not exist). */
void nuxel_start(long *sp);
__asm__(
".text\n"
".globl _start\n"
".type _start,%function\n"
"_start:\n"
"  mov x0, sp\n"
"  b nuxel_start\n"
);

void nuxel_start(long *sp){
 long argc=sp[0];
 char **argv=(char**)&sp[1];
 int hold=0; long hold_secs=0; STATE_DIR=0; int FBVAR_ORDER=0;
 /* A27: the first-light frame IS frame 0 of the original animation.  The asset
    carries no compression (flags bit0 = 0), so this freestanding binary needs no
    inflate; a compressed or malformed asset is rejected BY NAME below and the
    proven A16 diagnostic frame is painted instead. */
 const char *FL_PATH="/opt/nuxel/nuxel-firstlight.rawspl"; int FL_ON=1;
 for(long i=1;i<argc;i++){
   const char*a=argv[i];
   if(a[0]=='-'&&a[1]=='-'&&a[2]=='s'&&a[3]=='t'&&a[4]=='a'&&a[5]=='t'&&a[6]=='e'&&a[7]=='d'&&a[8]=='i'&&a[9]=='r'&&a[10]=='='){
     STATE_DIR=a+11; continue;
   }
   if(a[0]=='-'&&a[1]=='-'&&a[2]=='f'&&a[3]=='b'&&a[4]=='v'&&a[5]=='a'&&a[6]=='r'&&a[7]=='-'
      &&a[8]=='o'&&a[9]=='r'&&a[10]=='d'&&a[11]=='e'&&a[12]=='r'){ FBVAR_ORDER=1; continue; }
   if(a[0]=='-'&&a[1]=='-'&&a[2]=='f'&&a[3]=='i'&&a[4]=='r'&&a[5]=='s'&&a[6]=='t'
      &&a[7]=='l'&&a[8]=='i'&&a[9]=='g'&&a[10]=='h'&&a[11]=='t'){
     if(a[12]=='='&&a[13]) FL_PATH=a+13;
     else if(a[12]==0&&i+1<argc){ FL_PATH=argv[i+1]; i++; }
     FL_ON=1; continue;
   }
   if(a[0]=='-'&&a[1]=='-'&&a[2]=='n'&&a[3]=='o'&&a[4]=='-'&&a[5]=='f'&&a[6]=='i'
      &&a[7]=='r'&&a[8]=='s'&&a[9]=='t'&&a[10]=='l'&&a[11]=='i'&&a[12]=='g'
      &&a[13]=='h'&&a[14]=='t'&&a[15]==0){ FL_ON=0; continue; }
   if(a[0]=='h'&&a[1]=='o'&&a[2]=='l'&&a[3]=='d'&&a[4]==0){
     hold=1;
     if(i+1<argc){ const char*n=argv[i+1]; int ok=n[0]!=0; long v=0;
       for(int j=0;n[j];j++){ if(n[j]<'0'||n[j]>'9'){ok=0;break;} v=v*10+(n[j]-'0'); }
       if(ok) hold_secs=v; }
     /* A21: do NOT break here -- the option scan must keep going so that
        `--statedir=...` is honoured wherever it appears in argv. */
     continue;
   }
 }

 long fd=op("/dev/fb0"); if(fd<0) fd=op("/dev/graphics/fb0");
 if(fd<0){wr("NUXEL_FB_UNAVAILABLE no /dev/fb0\n");quit(2);}
 struct fb_fix F; for(u64 i=0;i<sizeof(F);i++)((u8*)&F)[i]=0;
 for(u64 i=0;i<sizeof(V);i++)((u8*)&V)[i]=0;
 if(io(fd,FBIOGET_VSCREENINFO,&V)<0||io(fd,FBIOGET_FSCREENINFO,&F)<0){wr("NUXEL_FB_IOCTL_FAILED\n");quit(3);}
 W=V.xres;H=V.yres;YVIR=V.yres_virtual?V.yres_virtual:V.yres;STRIDE=F.line_length;BPP=V.bits_per_pixel;
 /* A23: hardware colour order unless --fbvar-order was given. */
 if(!FBVAR_ORDER&&BPP==32){ V.red.offset=0; V.green.offset=8; V.blue.offset=16;
   V.red.length=8; V.green.length=8; V.blue.length=8;
   wr("NUXEL_FB_HW_ORDER=abgr8888 R@0 G@8 B@16 (overrides fb_var)\n"); }
 /* Geometry sanity: refuse anything we cannot reason about, and never trust a
    yres_virtual that is wildly larger than the panel (S10+ reports 2x, 6080). */
 if(STRIDE==0){wr("NUXEL_FB_ZERO_STRIDE\n");quit(7);}
 if(YVIR<H || YVIR>(u64)H*4u){ wrn("NUXEL_FB_YVIR_CLAMPED_from",YVIR); YVIR=H; }
 wr("NUXEL_FB_INFO:\n");
 wrn("  xres",W); wrn("  yres",H); wrn("  yres_virtual",YVIR);
 wrn("  xoffset",V.xoffset); wrn("  yoffset",V.yoffset);
 wrn("  bpp",BPP); wrn("  stride",STRIDE);
 wrh("  smem_start",F.smem_start); wrn("  smem_len",F.smem_len);
 wrh("  mmio_start",F.mmio_start); wrn("  mmio_len",F.mmio_len);
 wrn("  red.len",V.red.length); wrn("  green.len",V.green.length); wrn("  blue.len",V.blue.length);
 wrh("  red.off",V.red.offset);   wrh("  green.off",V.green.offset);
 wrh("  blue.off",V.blue.offset); wrh("  transp.off",V.transp.offset);
 wrn("  transp.len",V.transp.length);

/* ============================================================================
 * A23 -- THE PANEL'S REAL CHANNEL ORDER.
 *
 * The values just logged are what decon_check_var() DECLARES (red@16, blue@0).
 * They are not what the panel does.  decon_pan_display() -- the only path that
 * programs a DECON window on this board, drivers/video/fbdev/exynos/dpu20/
 * decon_dsi.c ~line 1204 -- hard-codes
 *     case 24: case 32: config.format = DECON_PIXEL_FORMAT_ABGR_8888;
 * and include/dt-bindings/display/exynos-display.h numbers those formats in the
 * DRM fourcc order (ARGB_8888=0, ABGR_8888=1, RGBA_8888=2, BGRA_8888=3, ...),
 * where ABGR8888 is the memory word A[31:24] B[23:16] G[15:8] R[7:0].
 * So the glass reads RED from bits 0..7.  Packing with V's offsets put red and
 * blue in each other's place: A16-A22's first-light frames and the A20
 * photograph ("red background with circuitry") are both explained by this.
 * We therefore OVERRIDE the declared fields with the hardware truth before any
 * colour is packed.  --fbvar-order (below) restores the old behaviour for A/B.
 * ==========================================================================*/

 if(W<64||H<64||W>10000||H>10000||(BPP!=16&&BPP!=24&&BPP!=32)||!V.red.length||!V.green.length||!V.blue.length){
   wr("NUXEL_FB_UNSUPPORTED_PIXEL_FORMAT\n");quit(4);}
 u64 need=(u64)STRIDE*H;
 if(F.smem_len<(u32)(need>0xffffffffu?0xffffffffu:need)){
   wr("NUXEL_FB_SIZE_MISMATCH\n"); wrh("  need_bytes",need); wrn("  smem_len",F.smem_len); quit(5);}
 mapped=F.smem_len;
 { u64 want=(u64)STRIDE*YVIR; if(want<mapped) mapped=want; }
 long map=sys(222,0,mapped,3,1,fd,0);
 if(map<0){wr("NUXEL_FB_MMAP_FAILED\n");quit(6);}
 fb=(u8*)map;
 wrn("NUXEL_FB_MAPPED_BYTES",mapped);

 /* The buffer count the DECON may be scanning, resolved the same way the
    animation player resolves it (YVIR/PH, 1..4) BEFORE anything is painted: the
    first-light frame must reach exactly the buffers the player will. */
 { u32 nbc=YVIR/H; if(nbc<1)nbc=1; if(nbc>4)nbc=4; NBUFS=nbc; }
 wrn("NUXEL_FB_BUFFERS",(u64)NBUFS);

/* ============================================================================
 * A27 -- FIRST LIGHT.  Light the panel with the animation's own frame 0.
 *
 * The asset is validated in full before a single pixel is written (magic,
 * reserved, flags, palette count, dimensions, blob/geometry agreement, exact
 * declared size, non-degenerate palette).  ANY failure falls back to the
 * hardware-proven A16 diagnostic frame, by name, so "no panel" is never confused
 * with "bad asset".  On success the frame is painted into every virtual buffer
 * with the player's own spans/packing, the DECON is committed, and this process
 * EXITS -- the DECON keeps scanning the buffer, so no framebuffer descriptor is
 * left open (A21: closing one runs decon_release and powers the panel down).
 * ==========================================================================*/
 int FL_DONE=0;
 if(FL_ON){
   long afd=op_rd(FL_PATH);
   if(afd<0){ wr("NUXEL_FIRSTLIGHT_ASSET_MISSING "); wr(FL_PATH);
              wr(" -> A16 diagnostic fallback\n"); }
   else {
     long asz=seek_end(afd);
     wrn("NUXEL_FIRSTLIGHT_ASSET_BYTES",(u64)(asz<0?0:asz));
     if(asz<32||asz>(8L*1024*1024)){ wr("NUXEL_FIRSTLIGHT_BAD_ASSET_SIZE -> A16 diagnostic fallback\n"); }
     else {
       long am=map_rd(afd,asz);
       if(am<0){ wr("NUXEL_FIRSTLIGHT_MMAP_FAILED -> A16 diagnostic fallback\n"); }
       else {
         static struct spl_frame FLF;
         int pe=spl_parse((const u8*)am,(u64)asz,&FLF);
         wrn("NUXEL_FIRSTLIGHT_PARSE_RC",(u64)pe);
         if(pe!=SPL_OK){
           wr("NUXEL_FIRSTLIGHT_REJECTED="); wr(spl_err_name(pe));
           wr(" -> A16 diagnostic fallback\n");
         } else {
           wrn("NUXEL_FIRSTLIGHT_SRC_WIDTH",FLF.w);  wrn("NUXEL_FIRSTLIGHT_SRC_HEIGHT",FLF.h);
           wrn("NUXEL_FIRSTLIGHT_PALETTE",FLF.paln); wrn("NUXEL_FIRSTLIGHT_FLAGS",FLF.flags);
           wrn("NUXEL_FIRSTLIGHT_INDEX_BYTES",FLF.bytes);
           color_probe();   /* diagnostics first: painted over by the frame below */
           int rr=spl_render(&FLF,fb,W,H,YVIR,STRIDE,BPP,mapped,NBUFS);
           wrn("NUXEL_FIRSTLIGHT_RENDER_RC",(u64)rr);
           if(rr==0){
             FL_DONE=1;
             wrn("NUXEL_FIRSTLIGHT_BG_INDEX",SPDBG_INDEX); wrh("NUXEL_FIRSTLIGHT_BG_DST",SPDBG_DST);
             wrn("NUXEL_FIRSTLIGHT_DST_WIDTH",SPLDW);  wrn("NUXEL_FIRSTLIGHT_DST_HEIGHT",SPLDH);
             wrn("NUXEL_FIRSTLIGHT_DST_X",SPLOX);      wrn("NUXEL_FIRSTLIGHT_DST_Y",SPLOY);
             wrn("NUXEL_FIRSTLIGHT_BUFFERS",(u64)NBUFS);
             wr("NUXEL_FIRSTLIGHT_FRAME0_PAINTED nuxspl=animation-frame0 (same palette, same spans, same packing as the player)\n");
           } else {
             wr("NUXEL_FIRSTLIGHT_RENDER_FAILED -> A16 diagnostic fallback\n");
           }
         }
         unmap(am,asz);
       }
     }
     closefd(afd);
   }
 }
 if(!FL_DONE){
   int nb=paint_all_buffers();
   NBUFS=nb<1?1:nb;
   wrn("NUXEL_FB_BUFFERS_PAINTED",(u64)nb);
 }

 /* Prove the store actually landed in the mapped memory the DECON scans. */
 wrh("NUXEL_FB_READBACK_px0",*(volatile u32*)(fb+0));
 wrh("NUXEL_FB_READBACK_center",*(volatile u32*)(fb+(u64)(H/2)*STRIDE+(u64)(W/2)*(BPP/8)));
 if(!FL_DONE) color_probe();


 PCX=(int)W/2; PCY=(int)(H*55/100);
 PSIZE=(int)W/9; if(PSIZE<40)PSIZE=40;

 if(FL_DONE){
   /* The panel already shows frame 0 of the animation: commit it and go.  The
      DECON scans framebuffer memory, so the image stays without a resident
      painter -- no competing writer, no open descriptor. */
   scanout_commit(fd,1);
   wr("NUXEL_FIRSTLIGHT_MARKER FIRST_LIGHT_IS_ANIMATION_FRAME0\n");
   if(!hold){
     wr("NUXEL_FB_EXIT first-light frame committed; exiting without holding a fb descriptor\n");
     sys(215,(long)fb,mapped,0,0,0,0);
     closefd(fd); quit(0);
   }
 } else {
 scanout_commit(fd,1);
 for(int f=1;f<12;f++){ spin_frame(f); wrn("NUXEL_FB_ANIM frame",(u64)f); scanout_commit(fd,0); sleep_ms(250); }
 wr("NUXEL_FB_ANIM_DONE frames=12\n");
 }
 wr("NUXEL_FB_DRAW_SUCCESS first-light frame + penguin animation written; panel visibility still needs the operator\n");
 wr("NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE\n");

 if(hold){
   wr("NUXEL_FB_HOLD_START\n");
   /* A21: publish our own pid and honour a stop file, so the resident painter can
      be stopped deterministically.  A16..A20 relied on `$!`, which toybox never
      sets, and on a /proc scan performed after switch_root had already moved
      /proc -- so nothing could ever stop this painter. */
   char holdpid_path[160]; char stop_path[160]; char ready_path[160];
   holdpid_path[0]=0; stop_path[0]=0; ready_path[0]=0;
   if(STATE_DIR){ cat2(holdpid_path,STATE_DIR,"/fb-hold.pid");
                  cat2(stop_path,STATE_DIR,"/fb-hold-stop");
                  cat2(ready_path,STATE_DIR,"/fb-anim-ready"); }
   if(holdpid_path[0]){ long pf=mkfile(holdpid_path); if(pf>=0){
       /* write the pid INTO the file as well as to the log: init.sh and the MP4
          player must be able to stop this painter deterministically. */
       u64 v=(u64)getpid_(); char pd[24]; int kk=0; if(!v) pd[kk++]='0';
       while(v){ pd[kk++]='0'+(int)(v%10); v/=10; }
       { char pb[24]; int q=0; while(kk) pb[q++]=pd[--kk]; pb[q++]='\n';
         sys(64,pf,(long)pb,q,0,0,0); }
       closefd(pf); }
     wrn("NUXEL_FB_HOLD_PID",(u64)getpid_()); }
   int f=0; unsigned long fr=0;
   for(;;){
     if(STATE_DIR && (fr%4)==0 && (fexists(stop_path)||fexists(ready_path))){
        wr("NUXEL_FB_HOLD_STOPPED stop-file-or-mp4-ready\n"); break; }
     /* A27: with the animation's frame 0 on the glass the hold is a STATIC
        hold -- re-committing the DECON, never repainting the old artwork. */
     if(!FL_DONE){ f=(f+1)%12; if(f==0) f=1; spin_frame(f); }
     scanout_commit(fd,0);
     fr++;
     /* keep the ram console usable: one line every ~10 s, not 4 per second */
     if((fr%40)==0) wrn("NUXEL_FB_HOLD frame",(u64)fr);
     if(hold_secs && (long)(fr/4)>=hold_secs) break;
     sleep_ms(250);
   }
   wrn("NUXEL_FB_HOLD_DONE frames",(u64)fr);
 }
 sys(215,(long)fb,mapped,0,0,0,0);
 closefd(fd); quit(0);
}

void *memset(void*dest,int value,u64 len){volatile u8*p=(volatile u8*)dest;while(len--)*p++=(u8)value;return dest;}
#endif /* !NUXEL_FIRSTLIGHT_HOST (device build) */
