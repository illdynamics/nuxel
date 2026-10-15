/* nuxel-anim-player — play the ORIGINAL Nuxel boot animation MP4 (packed as a
 * NUXANM01 container by tools/s10plus/nuxel-anim-pack.py) on the Samsung S10+
 * AMOLED through the hardware-proven Exynos DECON/DSIM *fbdev* path.
 *
 * WHY THIS EXISTS
 *   The shipped Nuxel boot animation is an H.264 MP4 rendered by a Plymouth
 *   "script" theme on the desktop/VM builds.  Plymouth needs DRM/KMS; this
 *   Samsung 4.14 downstream kernel reports `# CONFIG_DRM is not set` and only
 *   exposes /dev/fb0, so Plymouth cannot run here at all.  Rather than replace
 *   the artwork with a diagnostic, the original frames are re-encoded into a
 *   palette + changed-span stream and decoded by this freestanding player.
 *   The artwork, timing and loop behaviour of the source MP4 are preserved.
 *
 * PROPERTIES REQUIRED BY THE MISSION
 *   * no libc, no dynamic linking, no compositor, no systemd dependency
 *   * reads the REAL framebuffer geometry at runtime and never trusts history
 *   * bounded memory: the index plane + one inflate buffer + the mmap'd container
 *   * only changed pixels are written, so the cost per frame is proportional to
 *     what actually moved
 *   * if playback falls behind it keeps decoding and drops the *sleep*, never
 *     accumulating unbounded lag, and never queuing frames
 *   * stops only on an explicit request (signal or stop-file); never on a timer
 *
 * Output goes to fd 2, which init.sh points at /dev/kmsg, so every verdict line
 * lands in the ram console.
 */
typedef unsigned long  u64;
typedef long           s64;
typedef unsigned int   u32;
typedef int            s32;
typedef unsigned short u16;
typedef unsigned char  u8;

/* ---------------------------------------------------------------- syscalls -- */
#ifndef NUXEL_HOST            /* --- kernel syscalls --- */
static long sys(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0" : "+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");
 return x0; }
#define SYS_openat 56
#define SYS_close  57
#define SYS_read   63
#define SYS_write  64
#define SYS_pread64 67
#define SYS_lseek  62
#define SYS_nanosleep 101
#define SYS_clock_gettime 113
#define SYS_exit   93
#define SYS_mmap   222
#define SYS_getpid 172
#define SYS_kill   129
#define SYS_rt_sigaction 134
#define SYS_getdents64 61
/* A21 (measured on the handset): this kernel's arm64 ABI defines
 *     O_DIRECTORY = 040000 (16384)     O_DIRECT = 0200000 (0x10000)   O_NOFOLLOW = 0100000
 * (arch/arm64/include/uapi/asm/fcntl.h overrides the asm-generic values, and glibc
 * for aarch64 agrees: __O_DIRECTORY 040000).  A16..A20 passed 0x10000 as
 * "O_RDONLY|O_DIRECTORY"; that is O_DIRECT, and procfs rejects it with -EINVAL, so
 * every directory open in this player failed:
 *     openat(/proc, 040000) = ok    <- true O_DIRECTORY
 *     openat(/proc, 0x10000) = -1 errno=22 EINVAL
 * Never write 0x10000 for O_DIRECTORY on this board.  Directories below are opened
 * with a plain O_RDONLY, which is sufficient for getdents64 and for use as a dirfd. */
#define ARM64_O_DIRECTORY 040000

static long openrd(const char*p){ return sys(SYS_openat,-100,(long)p,0,0,0,0); } /* O_RDONLY */
static long openwr(const char*p){ return sys(SYS_openat,-100,(long)p,0x241,0600,0,0); } /* RDWR|CREAT|TRUNC */
static long openfb(const char*p){ return sys(SYS_openat,-100,(long)p,2,0,0,0); }    /* O_RDWR */
static long pread64(long fd,void*b,long n,long off){ return sys(SYS_pread64,fd,(long)b,n,off,0,0); }
static long readn(long fd,void*b,long n){ return sys(SYS_read,fd,(long)b,n,0,0,0); }
static long writen(long fd,const void*b,long n){ return sys(SYS_write,fd,(long)b,n,0,0,0); }
static void closefd(long fd){ sys(SYS_close,fd,0,0,0,0,0); }
static void quit(int c){ sys(SYS_exit,c,0,0,0,0,0); for(;;){} }
static long ioc(long fd,long req,long arg){ return sys(29,fd,req,arg,0,0,0); } /* ioctl */
static long pidnow(void){ return sys(SYS_getpid,0,0,0,0,0,0); }
#endif /* NUXEL_HOST */


static u64 slen(const char*s){ u64 n=0; while(s[n])n++; return n; }

/* ------------------------------------------------------------------- output -- */
#ifndef NUXEL_HOST            /* --- output (host: printf) --- */
static void wr(const char*s){ long n=0; while(s[n])n++; if(n) writen(2,s,n); }
static void wru(const char*tag,u64 v){ /* tag + '=' + unsigned decimal + '\n' */
 /* A21 FIX: A16..A20 advanced `i` past the tag but NEVER COPIED the tag bytes,
    so every numeric evidence line this player produced (geometry, pid, rc codes,
    takeover pids) reached the log as uninitialised stack memory plus the digits.
    Proven on hardware: the string "  xres=1440" arrived as "\0\0\0\0\0=1440". */
 char b[96]; int i=0; while(tag[i]&&i<76){ b[i]=tag[i]; i++; } b[i++]='=';
 char d[24]; int k=0; if(!v)d[k++]='0'; while(v){d[k++]='0'+(int)(v%10);v/=10;} while(k)b[i++]=d[--k];
 if(i>=94)i=94; b[i++]='\n'; writen(2,b,i); }
static void wrns(const char*tag,const char*s)
{ writen(2,tag,slen(tag)); writen(2,"=",1); writen(2,s,slen(s)); writen(2,"\n",1); }
#endif /* NUXEL_HOST */

/* ------------------------------------------------------------- fb geometry --- */
struct fb_bitfield{u32 offset,length,msb_right;};
struct fb_var{u32 xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bits_per_pixel,grayscale;
 struct fb_bitfield red,green,blue,transp;u32 nonstd,activate,height,width,accel_flags;
 u32 pixclock,left_margin,right_margin,upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace,reserved[4];};
struct fb_fix{char id[16];u64 smem_start;u32 smem_len,type,type_aux,visual;u16 xpanstep,ypanstep,ywrapstep;u32 line_length;u64 mmio_start;u32 mmio_len,accel;u16 capabilities,reserved[2];};
#define FBIOGET_VSCREENINFO 0x4600
#define FBIOPUT_VSCREENINFO 0x4601
#define FBIOGET_FSCREENINFO 0x4602
#define FBIOPAN_DISPLAY     0x4606
#define FBIOBLANK           0x4611
#define FB_ACTIVATE_NOW     0x0080
#define FB_BLANK_UNBLANK    0

static u8 *FB;                 /* mmap base of the whole virtual framebuffer   */
static u32 PW,PH,YVIR,STRIDE,BPP,BYTESPP,NBUFS;
static struct fb_var V;
static long FBFD=-1;

/* Per-source-pixel destination spans (nearest-neighbour, integer maths, so the
   animation is resolution-independent and never assumes the S10+ panel). */
static u16 PAL565[256];          /* source palette, RGB565 as decoded from the container */
static u32 DSTPIX[256];          /* the SAME colours pre-converted to the destination pixel format */
static u32 FB_BG;                /* artwork background, used for the letterbox bars */
static u32 RLEN,GLEN,BLEN,ROFF,GOFF,BOFF;
static u8 *IDX;
static u32 PALN;
static u32 AW,AH;                  /* animation (source) raster      */
static u32 *DX0,*DX1,*DY0,*DY1;
static u32 DW,DH,OX,OY;        /* destination rect inside the panel */

static void fill_span(u8 *row,u32 x0,u32 x1,u32 color){
 switch(BYTESPP){
  case 4:{ volatile u32*p=(volatile u32*)(row+(u64)x0*4); for(u32 x=x0;x<x1;x++)*p++=color; } break;
  case 2:{ volatile u16*p=(volatile u16*)(row+(u64)x0*2); for(u32 x=x0;x<x1;x++)*p++=(u16)color; } break;
  case 3:{ volatile u8*p=row+(u64)x0*3; for(u32 x=x0;x<x1;x++){p[0]=color&0xff;p[1]=(color>>8)&0xff;p[2]=(color>>16)&0xff;p+=3;} } break;
  default: break;
 }
}
/* Fill the whole panel (every virtual buffer) with one colour: this paints the
   letterbox bars and guarantees a deterministic starting surface. */
/* ============================================================================
 * colour conversion — the ONE place that knows the DECON pixel layout
 *
 * The framebuffer geometry is read at runtime and this is built from the driver's
 * OWN red/green/blue bitfields (the same maths the hardware-proven
 * nuxel-fb-phone first-light renderer uses), so it is correct on BGRA8888,
 * RGBA8888, RGB565 or any other layout the panel driver reports, and it cannot
 * silently drift from the driver.
 * ==========================================================================*/
static u32 packcol(u32 r,u32 g,u32 b){ /* 8-bit channel -> driver field */
 u32 R=RLEN?((r*((1u<<RLEN)-1u)+127u)/255u):0u;
 u32 G=GLEN?((g*((1u<<GLEN)-1u)+127u)/255u):0u;
 u32 B=BLEN?((b*((1u<<BLEN)-1u)+127u)/255u):0u;
 return (R<<ROFF)|(G<<GOFF)|(B<<BOFF);
}
static u32 five6to8(u32 v,u32 bits){ return (v*255u)/((1u<<bits)-1u); }

static void fill_panel(u32 color){
 for(u32 buf=0;buf<NBUFS;buf++)
  for(u32 y=0;y<PH;y++)
   fill_span(FB+(u64)(buf*PH+y)*STRIDE,0,PW,color);
}

/* Blit a horizontal run of source pixels at source row sy -> the displayed rects. */
static void blit_run(u32 sy,u32 sx0,u32 sx1,const u8 *idx){
 if(sy>=AH||sx0>=sx1||sx1>AW) return;
 u32 y0=DY0[sy],y1=DY1[sy];
 for(u32 buf=0;buf<NBUFS;buf++){
  for(u32 y=y0;y<y1;y++){
   u8 *row=FB+(u64)(buf*PH+y)*STRIDE;
   /* A21: DSTPIX[], not PAL565[].  Writing the raw RGB565 value of a palette
      entry into a 32-bpp DECON pixel put the low 5 bits (BLUE) into whichever
      channel the driver maps to bits 0..7 -- measured on the S10+ as the RED
      field -- so the dark navy artwork with blue circuitry rendered as a RED
      background with red circuitry. */
   for(u32 sx=sx0;sx<sx1;sx++) fill_span(row,DX0[sx],DX1[sx],DSTPIX[idx[sx]]);
  }
 }
}

/* ============================================================================
 * Inflate — raw DEFLATE (RFC 1951), no zlib header, no libc, no allocation.
 *
 * The span stream makes the decode workload tiny (a frame's compressed blob is
 * ~100 KB and expands to ~220 KB, versus 2 MB for a whole index plane), so a
 * small, obviously-correct bit-at-a-time Huffman decoder is the right trade:
 * it cannot mis-optimise, and it is still ~10x faster than the frame rate needs.
 * ==========================================================================*/
typedef struct { const u8 *in; u32 len, pos; u64 buf; int cnt; int err; } bits_t;

static u32 getbits(bits_t *b,int need){
 while(b->cnt<need){
  if(b->pos>=b->len){ b->err=1; return 0; }
  b->buf |= (u64)b->in[b->pos++] << b->cnt;
  b->cnt += 8;
 }
 u32 v=(u32)(b->buf & ((1u<<need)-1));
 b->buf >>= need; b->cnt -= need;
 return v;
}
static void align_byte(bits_t *b){ b->buf >>= (b->cnt&7); b->cnt -= (b->cnt&7); }

#define MAXBITS 15
typedef struct { short count[MAXBITS+1]; short symbol[320]; } huff_t;

static int huff_build(huff_t *h,const short *lens,int n){
 int i;
 for(i=0;i<=MAXBITS;i++) h->count[i]=0;
 for(i=0;i<n;i++) h->count[lens[i]]++;
 if(h->count[0]==n) return 0;                 /* no codes at all (legal) */
 int left=1;
 for(i=1;i<=MAXBITS;i++){ left<<=1; left-=h->count[i]; if(left<0) return -1; }
 short offs[MAXBITS+1];
 offs[1]=0;
 for(i=1;i<MAXBITS;i++) offs[i+1]=(short)(offs[i]+h->count[i]);
 for(i=0;i<n;i++) if(lens[i]) h->symbol[offs[lens[i]]++]=(short)i;
 return 0;
}
static int huff_decode(bits_t *b,const huff_t *h){
 int code=0,first=0,index=0,len;
 for(len=1;len<=MAXBITS;len++){
  code |= (int)getbits(b,1);
  int count=h->count[len];
  if(code-first<count) return h->symbol[index+(code-first)];
  index+=count; first+=count; first<<=1; code<<=1;
 }
 return -1;
}

static const short LEN_BASE[29]={3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
static const short LEN_EXTRA[29]={0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
static const short DIST_BASE[30]={1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
static const short DIST_EXTRA[30]={0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};
static const short CLEN_ORDER[19]={16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};

static huff_t HLIT, HDIST, HCLEN;
static short LENS[320];

static int inflate_block_body(bits_t *b,u8 *out,u32 cap,u32 *op){
 for(;;){
  int sym=huff_decode(b,&HLIT);
  if(sym<0) return -1;
  if(sym<256){ if(*op>=cap) return -1; out[(*op)++]=(u8)sym; continue; }
  if(sym==256) return 0;
  sym-=257;
  if(sym>=29) return -1;
  u32 len=(u32)LEN_BASE[sym]+getbits(b,LEN_EXTRA[sym]);
  int dsym=huff_decode(b,&HDIST);
  if(dsym<0||dsym>=30) return -1;
  u32 dist=(u32)DIST_BASE[dsym]+getbits(b,DIST_EXTRA[dsym]);
  if(dist>*op) return -1;
  if(*op+len>cap) return -1;
  u32 from=*op-dist;
  for(u32 i=0;i<len;i++) out[*op+i]=out[from+i];
  *op+=len;
 }
}

static long inflate_raw(const u8 *in,u32 inlen,u8 *out,u32 cap){
 bits_t b; b.in=in; b.len=inlen; b.pos=0; b.buf=0; b.cnt=0; b.err=0;
 u32 op=0;
 int last;
 do{
  last=(int)getbits(&b,1);
  u32 type=getbits(&b,2);
  if(b.err) return -1;
  if(type==0){                                  /* stored */
   align_byte(&b);
   if(b.pos+4>b.len) return -1;
   u32 l=(u32)b.in[b.pos]|((u32)b.in[b.pos+1]<<8);
   u32 nl=(u32)b.in[b.pos+2]|((u32)b.in[b.pos+3]<<8);
   b.pos+=4;
   if((l^0xffff)!=nl) return -1;
   if(b.pos+l>b.len||op+l>cap) return -1;
   for(u32 i=0;i<l;i++) out[op++]=b.in[b.pos++];
  } else if(type==1||type==2){
   if(type==1){                                 /* fixed Huffman */
    int i;
    for(i=0;i<144;i++)LENS[i]=8;
    for(;i<256;i++)LENS[i]=9;
    for(;i<280;i++)LENS[i]=7;
    for(;i<288;i++)LENS[i]=8;
    if(huff_build(&HLIT,LENS,288)<0) return -1;
    for(i=0;i<30;i++)LENS[i]=5;
    if(huff_build(&HDIST,LENS,30)<0) return -1;
   } else {                                     /* dynamic Huffman */
    u32 hlit=getbits(&b,5)+257, hdist=getbits(&b,5)+1, hclen=getbits(&b,4)+4;
    if(b.err||hlit>288||hdist>30) return -1;
    short cl[19];
    for(u32 i=0;i<19;i++) cl[i]=0;
    for(u32 i=0;i<hclen;i++) cl[CLEN_ORDER[i]]=(short)getbits(&b,3);
    if(b.err) return -1;
    if(huff_build(&HCLEN,cl,19)<0) return -1;
    u32 n=0; u32 total=hlit+hdist;
    while(n<total){
     int s=huff_decode(&b,&HCLEN);
     if(s<0) return -1;
     if(s<16){ LENS[n++]=(short)s; }
     else if(s==16){ if(n==0) return -1; short p=LENS[n-1]; u32 r=3+getbits(&b,2); while(r--&&n<total) LENS[n++]=p; }
     else if(s==17){ u32 r=3+getbits(&b,3); while(r--&&n<total) LENS[n++]=0; }
     else if(s==18){ u32 r=11+getbits(&b,7); while(r--&&n<total) LENS[n++]=0; }
     if(b.err) return -1;
    }
    if(huff_build(&HLIT,LENS,(int)hlit)<0) return -1;
    if(huff_build(&HDIST,LENS+hlit,(int)hdist)<0) return -1;
   }
   if(inflate_block_body(&b,out,cap,&op)!=0) return -1;
  } else return -1;
 } while(!last);
 return (long)op;
}

/* ============================================================================
 * small string / time / file helpers (no libc)
 * ==========================================================================*/
static int streq(const char*a,const char*b){ int i=0; for(;;){ if(a[i]!=b[i])return 0; if(!a[i])return 1; i++; } }
static u64 atou(const char*s){ u64 v=0; while(*s>='0'&&*s<='9') v=v*10+(u64)(*s++-'0'); return v; }

#ifndef NUXEL_HOST            /* --- timing + file side effects --- */
typedef struct { s64 s; s64 ns; } ts_t;
#define CLOCK_MONOTONIC 1
static u64 now_ns(void){ ts_t t; t.s=0; t.ns=0; sys(SYS_clock_gettime,CLOCK_MONOTONIC,(long)&t,0,0,0,0); return (u64)t.s*1000000000ull+(u64)t.ns; }
static void sleep_ns(u64 ns){ if(!ns)return; ts_t t; t.s=(s64)(ns/1000000000ull); t.ns=(s64)(ns%1000000000ull);
 sys(SYS_nanosleep,(long)&t,0,0,0,0,0); }

static void write_file(const char *path,const char *text){
 if(!path)return;
 long fd=openwr(path); if(fd<0)return;
 writen(fd,text,slen(text)); closefd(fd);
}
static int file_exists(const char *path){
 if(!path)return 0;
 long fd=sys(SYS_openat,-100,(long)path,0,0,0,0);
 if(fd<0)return 0; closefd(fd); return 1;
}

/* The player outlives `switch_root`: the rootfs it was launched against is moved
 * from ${ROOT_MNT} to / by init, so every absolute path in the initramfs
 * namespace stops resolving at that instant.  A directory fd opened on the state
 * directory BEFORE switch_root keeps working on both sides of the pivot, so the
 * stop-file poll and the state writes are valid for the whole lifetime. */
static long STATEDIR_FD=-1;
static long open_at(const char *path,int flags,int mode){
 if(!path) return -1;
 if(path[0]=='/'||STATEDIR_FD<0) return sys(SYS_openat,-100,(long)path,flags,mode,0,0);
 return sys(SYS_openat,STATEDIR_FD,(long)path,flags,mode,0,0);
}
static void write_file_at(const char *path,const char *text){
 if(!path)return;
 long fd=open_at(path,0x241,0600); if(fd<0)return;
 writen(fd,text,slen(text)); closefd(fd);
}
static int file_exists_at(const char *path){
 if(!path)return 0;
 long fd=open_at(path,0,0);
 if(fd<0)return 0; closefd(fd); return 1;
}
#endif /* NUXEL_HOST */

/* ============================================================================
 * stop signals — the ONLY way the animation ends.  Never a timer.
 * ==========================================================================*/
static volatile int STOP=0;
static void on_sig(int s){ (void)s; STOP=1; }
struct ksa { void (*handler)(int); u64 flags; u64 mask; };
#ifndef NUXEL_HOST
static void install_sig(int sig){
 struct ksa a; a.handler=on_sig; a.flags=0x10000000ull; a.mask=0;   /* SA_RESTART */
 sys(SYS_rt_sigaction,sig,(long)&a,0,8,0,0);
}
#endif /* NUXEL_HOST */

/* ============================================================================
 * container
 * ==========================================================================*/
#define ANIM_MAGIC0 0x4d414e58554full /* "NUXANM01" little-endian dword pair */
struct anim_hdr {
 u8  magic[8];
 u32 width,height,frames,fps_num,fps_den,palette_count;
 u16 palette[256];
 u32 flags,reserved;
};
#define ANIM_HDR_BYTES 552u
#define FTR_STOP 0xffffffffu

static const u8 *CONT;      /* mmap of the whole container */
static u32 CONT_LEN;
static const struct anim_hdr *HDR;
static u32 NF, FPSN, FPSD, CS;

static void rl32(const u8*p,u32 *o,u32 *s){ *o=(u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);
                                            *s=(u32)p[4]|((u32)p[5]<<8)|((u32)p[6]<<16)|((u32)p[7]<<24); }

/* ============================================================================
 * framebuffer takeover
 *
 * A15..A19 leave `nuxel-fb-phone hold` running as the resident painter; it is the
 * proven "panel stays alive" fallback and must be preserved.  The animation player
 * therefore has to take the framebuffer over explicitly: two painters writing the
 * same surface would tear, and the mission forbids the animation and the UI
 * overwriting each other.  The handoff is done here, in C, by walking /proc with
 * getdents64 - the shell-based /proc scan in A18/A19 never resolved a PID because
 * of toybox defects, and a PID file the animator cannot be trusted to own.
 * ==========================================================================*/
static void u2s(char *b, u64 v){ char d[24]; int k=0; if(!v)d[k++]='0'; while(v){d[k++]='0'+(int)(v%10);v/=10;} int i=0; while(k)b[i++]=d[--k]; b[i]=0; }
static int name_is_pid(const char *nm){
 if(!nm[0]) return 0;
 for(int i=0;nm[i];i++) if(nm[i]<'0'||nm[i]>'9') return 0;
 return 1;
}
static int cstr_eq(const char *a,const char *b,int maxlen){
 for(int i=0;i<maxlen;i++){ if(a[i]!=b[i])return 0; if(!a[i])return 1; }
 return 1;
}
static u64 TAKEOVER_PIDS[8];
static int TAKEOVER_N=0;
static const char *A_HOLDPID=0;
#ifndef NUXEL_HOST
struct linux_dirent64 { u64 ino; s64 off; u16 reclen; u8 type; char name[]; };
static int takeover_painters(void){
 /* A21: measured on the S10+ (TWRP AND the Nuxel initramfs), openat("/proc",
    O_RDONLY|O_DIRECTORY) returns -EINVAL, while a plain O_RDONLY open of the same
    directory succeeds -- and getdents64 works on the resulting fd.  Both are tried,
    in that order, and the return codes are recorded so the quirk can never again
    hide behind a single unhelpful "no /proc". */
 long fd=sys(SYS_openat,-100,(long)"/proc",0,0,0,0);
 long rcb=sys(SYS_openat,-100,(long)"/proc",0x10000,0,0,0);
 wru("NUXEL_ANIM_PROC_OPEN_RC_PLAIN",(u64)fd);
 wru("NUXEL_ANIM_PROC_OPEN_RC_DIRECTORY",(u64)rcb);
 if(fd<0&&rcb>=0) fd=rcb;
 if(fd<0){ wr("NUXEL_ANIM_TAKEOVER no /proc\n");
            wru("NUXEL_ANIM_TAKEOVER_PROC_OPEN_RC",(u64)fd); return -1; }
 static u8 dbuf[32768];
 long n; int killed=0;
 n=sys(SYS_getdents64,fd,(long)dbuf,sizeof dbuf,0,0,0);
 if(n<0) wru("NUXEL_ANIM_TAKEOVER_GETDENTS_RC",(u64)n);
 while(n>0){
  for(long o=0;o<n;){
   struct linux_dirent64 *d=(struct linux_dirent64*)(dbuf+o);
   if(!d->reclen) break;
   o+=d->reclen;
   if(!name_is_pid(d->name)) continue;
   char path[64]; int i=0;
   const char *pre="/proc/"; while(pre[i]){path[i]=pre[i];i++;}
   { char t[24]; u2s(t,atou(d->name)); for(int k=0;t[k];k++) path[i++]=t[k]; }
   path[i]=0;
   char p2[80]; int j=0; while(path[j]){p2[j]=path[j];j++;}
   const char *suf="/comm"; for(int k=0;suf[k];k++) p2[j++]=suf[k]; p2[j]=0;
   long cf=sys(SYS_openat,-100,(long)p2,0,0,0,0);
   if(cf<0) continue;
   char comm[32]; long r=readn(cf,comm,31); closefd(cf);
   if(r<=0) continue;
   comm[r]=0;
   /* strip the newline the kernel appends */
   for(int k=0;k<r;k++) if(comm[k]=='\n'){ comm[k]=0; break; }
   if(cstr_eq(comm,"nuxel-fb-phone",31)){
    u64 kp=atou(d->name);
    sys(SYS_kill,kp,15,0,0,0,0);              /* SIGTERM */
    char kb[32]; int ki=0; char kd[24]; int kk=0; u64 kv=kp;
    if(!kv)kd[kk++]='0'; while(kv){kd[kk++]='0'+(int)(kv%10);kv/=10;} while(kk)kb[ki++]=kd[--kk];
    kb[ki++]='\n'; kb[ki]=0;
    wrns("NUXEL_ANIM_TAKEOVER_PID",kb);
    if(TAKEOVER_N<8) TAKEOVER_PIDS[TAKEOVER_N++]=kp;
    killed++;
   }
  }
  n=sys(SYS_getdents64,fd,(long)dbuf,sizeof dbuf,0,0,0);
 }
 closefd(fd);
 if(rcb>=0) closefd(rcb);
 return killed;
}
#endif
#ifndef NUXEL_HOST
/* Bounded acknowledgement: is pid still alive AND still that process?  Identity
   is re-checked from /proc/<pid>/comm so a recycled pid can never be mistaken for
   the painter we signalled (mission section 7: verify process identity). */
static int pid_alive_comm(u64 pid,const char*want){
 char path[64]; int i=0; const char*pre="/proc/";
 while(pre[i]){path[i]=pre[i];i++;}
 char t[24]; u2s(t,pid); for(int k=0;t[k];k++) path[i++]=t[k];
 const char*suf="/comm"; for(int k=0;suf[k];k++) path[i++]=suf[k];
 path[i]=0;
 long fd=sys(SYS_openat,-100,(long)path,0,0,0,0);
 if(fd<0) return 0;                      /* gone = stopped */
 char comm[32]; long r=readn(fd,comm,31); closefd(fd);
 if(r<=0) return 0;
 comm[r]=0; for(int k=0;k<r;k++) if(comm[k]=='\n'){comm[k]=0;break;}
 return cstr_eq(comm,want,31);
}
#endif /* NUXEL_HOST */
static u64 A_TAKEOVER=1;
static u64 REASSERT=0,PANFAIL=0;   /* A22: DECON self-heal counters */

/* ============================================================================
 * argument state
 * ==========================================================================*/
static const char *A_FILE=0,*A_STATE=0,*A_PID=0,*A_STOPFILE=0,*A_STATEDIR=0;
static u64 A_LOOPS=0;      /* 0 = loop forever                                  */
static u64 A_CTEST=0;      /* >0: paint the colour bars for N seconds and exit  */
static u64 A_SECS=0;       /* 0 = no time limit                                 */
static int A_VERBOSE=0;
/* A23: HARDWARE colour order.  1 = pack for DECON_PIXEL_FORMAT_ABGR_8888 (the
   format the only commit path actually programs).  0 = trust fb_var bitfields. */
static u32 HW_ABGR=1;

static void parse_args(long argc,char **argv){
 for(long i=1;i<argc;i++){
  const char *a=argv[i];
  if(!a||a[0]!='-'||a[1]!='-') continue;
  const char *k=a+2; const char *v=0;
  for(const char*p=k;*p;p++) if(*p=='='){ v=p+1; break; }
  u64 klen = v ? (u64)(v-1-k) : slen(k);
  if(klen==4 && k[0]=='f'&&k[1]=='i'&&k[2]=='l'&&k[3]=='e') A_FILE=v;
  else if(klen==5 && k[0]=='s'&&k[1]=='t'&&k[2]=='a'&&k[3]=='t'&&k[4]=='e') A_STATE=v;
  else if(klen==3 && k[0]=='p'&&k[1]=='i'&&k[2]=='d') A_PID=v;
  else if(klen==8 && k[0]=='s'&&k[1]=='t'&&k[2]=='o'&&k[3]=='p'&&k[4]=='f'&&k[5]=='i'&&k[6]=='l'&&k[7]=='e') A_STOPFILE=v;
  else if(klen==5 && k[0]=='l'&&k[1]=='o'&&k[2]=='o'&&k[3]=='p'&&k[4]=='s') A_LOOPS=v?atou(v):1;
  else if(klen==4 && k[0]=='s'&&k[1]=='e'&&k[2]=='c'&&k[3]=='s') A_SECS=v?atou(v):0;
  /* --colourtest[=secs]: diagnostic only, never used by the boot path.  Paints the
     five colours the mission asks to be tested independently (pure red, green, blue,
     white, black) packed with the DRIVER's own bitfields, so one photograph settles
     the channel mapping of this panel beyond doubt. */
  else if(klen==10 && k[0]=='c'&&k[1]=='o'&&k[2]=='l'&&k[3]=='o'&&k[4]=='u'&&k[5]=='r'&&k[6]=='t'&&k[7]=='e'&&k[8]=='s'&&k[9]=='t') A_CTEST=v?atou(v):5;
  else if(klen==7 && k[0]=='v'&&k[1]=='e'&&k[2]=='r'&&k[3]=='b'&&k[4]=='o'&&k[5]=='s'&&k[6]=='e') A_VERBOSE=1;
  /* A23: --hworder=abgr|fbvar -- which channel order the PANEL really uses. */
  else if(klen==7 && k[0]=='h'&&k[1]=='w'&&k[2]=='o'&&k[3]=='r'&&k[4]=='d'&&k[5]=='e'&&k[6]=='r'){
    if(v && v[0]=='f'&&v[1]=='b') HW_ABGR=0; else HW_ABGR=1; }
  else if(klen==8 && k[0]=='t'&&k[1]=='a'&&k[2]=='k'&&k[3]=='e'&&k[4]=='o'&&k[5]=='v'&&k[6]=='e'&&k[7]=='r') A_TAKEOVER=v?atou(v):1;
  else if(klen==7 && k[0]=='h'&&k[1]=='o'&&k[2]=='l'&&k[3]=='d'&&k[4]=='p'&&k[5]=='i'&&k[6]=='d') A_HOLDPID=v;
  else if(klen==8 && k[0]=='s'&&k[1]=='t'&&k[2]=='a'&&k[3]=='t'&&k[4]=='e'&&k[5]=='d'&&k[6]=='i'&&k[7]=='r') A_STATEDIR=v;
 }
}

/* ============================================================================
 * main
 * ==========================================================================*/
#ifndef NUXEL_HOST            /* --- entry point + daemon body --- */
void nuxel_anim_start(long *sp);
__asm__(
".text\n.globl _start\n.type _start,%function\n"
"_start:\n  mov x0, sp\n  b nuxel_anim_start\n");

void nuxel_anim_start(long *sp){
 long argc=sp[0]; char **argv=(char**)&sp[1];
 parse_args(argc,argv);

 wr("NUXEL_ANIM_PLAYER start\n");
 wru("NUXEL_ANIM_ARG_PARSE_REV",(u64)2);   /* bumped whenever the option table changes */
 wru("NUXEL_ANIM_OPT_SECS",A_SECS);
 wru("NUXEL_ANIM_OPT_LOOPS",A_LOOPS);
 wru("NUXEL_ANIM_OPT_HAS_STOPFILE",(u64)(A_STOPFILE?1:0));
 wru("NUXEL_ANIM_OPT_HAS_STATE",(u64)(A_STATE?1:0));
 wru("NUXEL_ANIM_OPT_HAS_PIDFILE",(u64)(A_PID?1:0));
 if(A_STATEDIR){
  /* plain O_RDONLY first: proven to work as a dirfd for openat() on this kernel. */
  STATEDIR_FD=sys(SYS_openat,-100,(long)A_STATEDIR,0,0,0,0);
  if(STATEDIR_FD<0) STATEDIR_FD=sys(SYS_openat,-100,(long)A_STATEDIR,ARM64_O_DIRECTORY,0,0,0);
  wru("NUXEL_ANIM_STATEDIR_FD_OK",(u64)(STATEDIR_FD>=0?1:0));
  wru("NUXEL_ANIM_STATEDIR_FD_RC",(u64)STATEDIR_FD);
  wrns("NUXEL_ANIM_STATEDIR",A_STATEDIR);
  wru("NUXEL_ANIM_STATEDIR_FD",(u64)(STATEDIR_FD<0?0:1));
 }
 if(!A_FILE) A_FILE="/usr/share/nuxel/boot/nuxel-animation.nux";
 wrns("NUXEL_ANIM_FILE",A_FILE);

 /* --- framebuffer ------------------------------------------------------- */
 FBFD=openfb("/dev/fb0"); if(FBFD<0) FBFD=openfb("/dev/graphics/fb0");
 if(FBFD<0){ wr("NUXEL_ANIM_FB_UNAVAILABLE no /dev/fb0\n"); quit(2); }
 for(u64 i=0;i<sizeof(V);i++)((u8*)&V)[i]=0;
 struct fb_fix F; for(u64 i=0;i<sizeof(F);i++)((u8*)&F)[i]=0;
 if(ioc(FBFD,FBIOGET_VSCREENINFO,(long)&V)<0||ioc(FBFD,FBIOGET_FSCREENINFO,(long)&F)<0){
  wr("NUXEL_ANIM_FB_IOCTL_FAILED\n"); quit(3); }
 PW=V.xres; PH=V.yres; YVIR=V.yres_virtual?V.yres_virtual:V.yres;
 STRIDE=F.line_length; BPP=V.bits_per_pixel;
 if(!PW||!PH||!STRIDE||(BPP!=16&&BPP!=24&&BPP!=32)){ wr("NUXEL_ANIM_FB_UNSUPPORTED\n"); quit(4); }
 BYTESPP=BPP/8;
 if(YVIR<PH||YVIR>(u32)PH*4u) YVIR=PH;
 NBUFS=YVIR/PH; if(NBUFS<1)NBUFS=1; if(NBUFS>4)NBUFS=4;
 wru("NUXEL_ANIM_FB_WIDTH",PW);   wru("NUXEL_ANIM_FB_HEIGHT",PH);
 wru("NUXEL_ANIM_FB_VIRTUAL_HEIGHT",YVIR); wru("NUXEL_ANIM_FB_STRIDE",STRIDE);
 wru("NUXEL_ANIM_FB_BPP",BPP);    wru("NUXEL_ANIM_FB_BUFFERS",NBUFS);
 /* A21: the pixel layout the conversion below is derived from -- logged so the
    next capture can never be ambiguous about it again. */
 wru("NUXEL_ANIM_FB_RED_OFF",V.red.offset);     wru("NUXEL_ANIM_FB_RED_LEN",V.red.length);
 wru("NUXEL_ANIM_FB_GREEN_OFF",V.green.offset); wru("NUXEL_ANIM_FB_GREEN_LEN",V.green.length);
 wru("NUXEL_ANIM_FB_BLUE_OFF",V.blue.offset);   wru("NUXEL_ANIM_FB_BLUE_LEN",V.blue.length);
 wru("NUXEL_ANIM_FB_TRANSP_OFF",V.transp.offset); wru("NUXEL_ANIM_FB_TRANSP_LEN",V.transp.length);
 RLEN=V.red.length; GLEN=V.green.length; BLEN=V.blue.length;
 ROFF=V.red.offset; GOFF=V.green.offset; BOFF=V.blue.offset;
/* ---------------------------------------------------------------------------
   A23 -- THE PANEL'S REAL CHANNEL ORDER (proof in NUXEL-COLOUR-ORDER.md).

   decon_check_var() in drivers/video/fbdev/exynos/dpu20/decon_dsi.c DECLARES
   red.offset=16 / green.offset=8 / blue.offset=0 for 24/32 bpp.  But the ONLY
   path that programs the DECON window -- decon_pan_display(), same file, line
   ~1204 -- hard-codes:

       case 24: case 32: config.format = DECON_PIXEL_FORMAT_ABGR_8888;

   and include/dt-bindings/display/exynos-display.h numbers the formats in the
   DRM fourcc order (ARGB_8888=0, ABGR_8888=1, RGBA_8888=2, BGRA_8888=3 ...),
   where ABGR8888 means the memory word is A[31:24] B[23:16] G[15:8] R[7:0].
   So the panel reads RED from bits 0..7 and BLUE from bits 23..16: exactly the
   opposite of what fb_var tells userspace, and exactly what the operator's A20
   photograph showed (the artwork's blue circuitry rendered RED).

   Consequence: on this board fb_var's colour bitfields are NOT usable for
   packing.  A16-A22 packed with them, so every frame since A16 was R/B swapped.
   We therefore derive the packing from the hardware format, not from fb_var.
   --hworder=fbvar restores the old (wrong) behaviour for A/B testing.
   --------------------------------------------------------------------------- */
 if(HW_ABGR){
  if(BPP==32){ ROFF=0; GOFF=8; BOFF=16; RLEN=8; GLEN=8; BLEN=8;
   wru("NUXEL_ANIM_HW_ORDER",1);       wr("NUXEL_ANIM_HW_ORDER_NAME=abgr8888 R@0 G@8 B@16 A@24\n");
   wru("NUXEL_ANIM_HW_DECON_FMT",1);   wr("NUXEL_ANIM_HW_DECON_FMT_NAME=DECON_PIXEL_FORMAT_ABGR_8888\n");
  } else if(BPP==16){ ROFF=11; GOFF=5; BOFF=0; RLEN=5; GLEN=6; BLEN=5;
   wr("NUXEL_ANIM_HW_ORDER_NAME=rgb565 (channel positions unambiguous)\n"); }
 } else {
  wr("NUXEL_ANIM_HW_ORDER_NAME=fbvar-declared (A21/A22 behaviour)\n");
 }
 /* Refuse to paint rather than paint wrong: with no usable colour bitfields the
    first-light frame is left untouched and init.sh starts the penguin fallback. */
 if(!RLEN||!GLEN||!BLEN||RLEN>8||GLEN>8||BLEN>8||
    ROFF+RLEN>BPP||GOFF+GLEN>BPP||BOFF+BLEN>BPP){
  wr("NUXEL_ANIM_FB_BAD_COLOUR_FORMAT\n");
  wru("NUXEL_ANIM_FB_BAD_RED",(u64)ROFF*100+RLEN);
  wru("NUXEL_ANIM_FB_BAD_GREEN",(u64)GOFF*100+GLEN);
  wru("NUXEL_ANIM_FB_BAD_BLUE",(u64)BOFF*100+BLEN);
  if(A_STATEDIR) write_file_at("fb-anim-failed","FB_BAD_COLOUR_FORMAT\n");
  quit(21);
 }
 u64 need=(u64)STRIDE*YVIR;
 if(F.smem_len<need){ wr("NUXEL_ANIM_FB_SIZE_MISMATCH\n"); quit(5); }
 long map=sys(SYS_mmap,0,(long)need,3,1,FBFD,0);
 if(map<0){ wr("NUXEL_ANIM_FB_MMAP_FAILED\n"); quit(6); }
 FB=(u8*)map;

 /* --- optional diagnostic: colour bars, packed with the driver bitfields --- */
 if(A_CTEST){
  u32 cR=packcol(255,0,0), cG=packcol(0,255,0), cB=packcol(0,0,255);
  u32 cW=packcol(255,255,255), cK=packcol(0,0,0);
  wru("NUXEL_COLOURTEST_RED",(u64)cR);   wru("NUXEL_COLOURTEST_GREEN",(u64)cG);
  wru("NUXEL_COLOURTEST_BLUE",(u64)cB);  wru("NUXEL_COLOURTEST_WHITE",(u64)cW);
  wru("NUXEL_COLOURTEST_BLACK",(u64)cK);
  /* A/B screen.  TOP half: the HARDWARE order (ABGR_8888 -- R@0 B@16, what
     decon_pan_display really programs).  BOTTOM half: red and blue fed to the
     OPPOSITE fields, i.e. the fb_var-declared layout A16-A22 used.  With A23's
     default the TOP half must read red-green-blue-white-black left to right. */
  u32 cRs=packcol(0,0,255), cBs=packcol(255,0,0);   /* swapped R/B, same source colours */
  for(u32 buf=0;buf<NBUFS;buf++)
   for(u32 y=0;y<PH;y++){
    u8 *row=FB+(u64)(buf*PH+y)*STRIDE;
    u32 a=cR,b=cG,c=cB;
    if(y>=PH/2){ a=cRs; c=cBs; }
    fill_span(row,0,PW/5,a); fill_span(row,PW/5,(2u*PW)/5,b);
    fill_span(row,(2u*PW)/5,(3u*PW)/5,c); fill_span(row,(3u*PW)/5,(4u*PW)/5,cW);
    fill_span(row,(4u*PW)/5,PW,cK);
   }
  wru("NUXEL_COLOURTEST_SWAP_RED",(u64)cRs);
  wru("NUXEL_COLOURTEST_SWAP_BLUE",(u64)cBs);
  wr("NUXEL_COLOURTEST_TOPHALF=declared(B,G,R order in memory) BOTTOMHALF=swapped\n");
  V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
  ioc(FBFD,FBIOBLANK,FB_BLANK_UNBLANK);
  ioc(FBFD,FBIOPUT_VSCREENINFO,(long)&V);
  ioc(FBFD,FBIOPAN_DISPLAY,(long)&V);
  wru("NUXEL_COLOURTEST_READBACK_RED",(u64)(*(volatile u32*)(FB+2u*STRIDE)));
  wru("NUXEL_COLOURTEST_READBACK_BLUE",(u64)(*(volatile u32*)(FB+2u*STRIDE+(u64)(PW/2)*BYTESPP)));
  wr("NUXEL_COLOURTEST_BARS red green blue white black, left to right, in BOTH halves\n");
  sleep_ns(A_CTEST*1000000000ull);
  wr("NUXEL_COLOURTEST_DONE\n");
  quit(0);
 }

 /* --- container ---------------------------------------------------------- */
 long cfd=openrd(A_FILE);
 if(cfd<0){ wr("NUXEL_ANIM_CONTAINER_MISSING\n"); quit(7); }
 long csize=sys(SYS_lseek,cfd,0,2,0,0,0);
 if(csize<(long)(ANIM_HDR_BYTES+8)){ wr("NUXEL_ANIM_CONTAINER_TRUNCATED\n"); quit(8); }
 long cmap=sys(SYS_mmap,0,csize,1,2,cfd,0);
 if(cmap<0){ wr("NUXEL_ANIM_CONTAINER_MMAP_FAILED\n"); quit(9); }
 CONT=(const u8*)cmap; CONT_LEN=(u32)csize;
 HDR=(const struct anim_hdr*)CONT;
 const char *mg="NUXANM01";
 for(int i=0;i<8;i++) if(HDR->magic[i]!=(u8)mg[i]){ wr("NUXEL_ANIM_BAD_MAGIC\n"); quit(10); }
 AW=HDR->width; AH=HDR->height; NF=HDR->frames; FPSN=HDR->fps_num; FPSD=HDR->fps_den?HDR->fps_den:1;
 PALN=HDR->palette_count; CS=HDR->flags;
 if(!AW||!AH||!NF||AW>8192||AH>8192||(u64)AW*AH>64000000ull){ wr("NUXEL_ANIM_BAD_GEOMETRY\n"); quit(11); }
 if(PALN<2||PALN>256){ wr("NUXEL_ANIM_BAD_PALETTE\n"); quit(12); }
 for(u32 i=0;i<PALN;i++) PAL565[i]=HDR->palette[i];
 /* Expand the container's RGB565 palette into the destination pixel format ONCE,
    with the driver's own bitfields.  This is the fix for the red-for-blue
    artefact seen on the AMOLED. */
 for(u32 i=0;i<PALN;i++){
  u32 c=PAL565[i];
  u32 r=five6to8((c>>11)&31u,5u), g=five6to8((c>>5)&63u,6u), b=five6to8(c&31u,5u);
  DSTPIX[i]=packcol(r,g,b);
 }
 wru("NUXEL_ANIM_PAL0_SRC565",(u64)PAL565[0]);      wru("NUXEL_ANIM_PAL0_DST",(u64)DSTPIX[0]);
 wru("NUXEL_ANIM_PAL1_SRC565",(u64)PAL565[1]);      wru("NUXEL_ANIM_PAL1_DST",(u64)DSTPIX[1]);
 wru("NUXEL_ANIM_PAL2_SRC565",(u64)PAL565[2]);      wru("NUXEL_ANIM_PAL2_DST",(u64)DSTPIX[2]);
 wru("NUXEL_ANIM_PALMAX_SRC565",(u64)PAL565[PALN-1]); wru("NUXEL_ANIM_PALMAX_DST",(u64)DSTPIX[PALN-1]);
 wru("NUXEL_ANIM_SRC_WIDTH",AW); wru("NUXEL_ANIM_SRC_HEIGHT",AH);
 wru("NUXEL_ANIM_FRAMES",NF); wru("NUXEL_ANIM_FPS",FPSN/(FPSD?FPSD:1));

 /* --- destination mapping (integer nearest-neighbour, panel-independent) -- */
 DW=PW; DH=(u32)(((u64)AH*(u64)PW)/(u64)AW);
 if(DH>PH){ DH=PH; DW=(u32)(((u64)AW*(u64)PH)/(u64)AH); }
 if(!DW||!DH){ wr("NUXEL_ANIM_SCALE_FAILED\n"); quit(13); }
 OX=(PW-DW)/2; OY=(PH-DH)/2;
 u64 idxbytes=(u64)AW*AH;
 u64 tablebytes=((u64)AW+AH+16)*4u*4u;
 long tab=sys(SYS_mmap,0,(long)tablebytes,3,0x22,-1,0);
 long idxm=sys(SYS_mmap,0,(long)idxbytes,3,0x22,-1,0);
 u32 scratch_cap=(u32)(idxbytes>0x400000ull?idxbytes:0x400000ull);   /* >= index plane */
 long scr=sys(SYS_mmap,0,(long)scratch_cap,3,0x22,-1,0);
 if(tab<0||idxm<0||scr<0){ wr("NUXEL_ANIM_ALLOC_FAILED\n"); quit(14); }
 DX0=(u32*)tab; DX1=DX0+AW; DY0=DX1+AW; DY1=DY0+AH;
 IDX=(u8*)idxm; u8 *SCR=(u8*)scr;
 for(u32 x=0;x<AW;x++){ u32 a=OX+(u32)(((u64)x*(u64)DW)/(u64)AW);
                       u32 b=OX+(u32)(((u64)(x+1)*(u64)DW)/(u64)AW);
                       if(b<=a)b=a+1; if(b>PW)b=PW; if(a>=PW)a=PW-1; DX0[x]=a; DX1[x]=b; }
 for(u32 y=0;y<AH;y++){ u32 a=OY+(u32)(((u64)y*(u64)DH)/(u64)AH);
                       u32 b=OY+(u32)(((u64)(y+1)*(u64)DH)/(u64)AH);
                       if(b<=a)b=a+1; if(b>PH)b=PH; if(a>=PH)a=PH-1; DY0[y]=a; DY1[y]=b; }
 wru("NUXEL_ANIM_DEST_WIDTH",DW); wru("NUXEL_ANIM_DEST_HEIGHT",DH);
 wru("NUXEL_ANIM_DEST_X",OX); wru("NUXEL_ANIM_DEST_Y",OY);
 wru("NUXEL_ANIM_SCRATCH_BYTES",scratch_cap);

 /* --- publish identity so the initramfs/UI can find and stop us ---------- */
 install_sig(10);  /* SIGUSR1 */
 install_sig(15);  /* SIGTERM */
 install_sig(2);   /* SIGINT  */
 if(A_PID){
   char b[32]; int i=0; u64 p=(u64)pidnow(); char d[24]; int k=0;
   if(!p)d[k++]='0'; while(p){d[k++]='0'+(int)(p%10);p/=10;} while(k)b[i++]=d[--k];
   b[i++]='\n'; b[i]=0;
   write_file_at(A_PID,b);
   wru("NUXEL_ANIM_PID",(u64)pidnow());
 }
 /* Handshake with the initramfs: the player owns the panel from here.
    init.sh does NOT switch_root until this file appears (bounded), which is what
    keeps /proc and every absolute path valid for the takeover below.  Before A21
    the player was left racing switch_root, whose mount moves and old-root delete
    pulled /proc out from under it -- hardware log: "NUXEL_ANIM_TAKEOVER no /proc". */
 if(A_STATEDIR) write_file_at("fb-anim-starting","PLAYER_RUNNING\n");

 /* --- bring the DECON up through the blank/unblank path ---------------------
    A22: this is now re-issuable.  Measured on the handset (A21): ANY process that
    opens and then CLOSES /dev/fb0 runs the DECON's fb_release path and disables the
    display; the panel only comes back through FBIOPUT_VSCREENINFO (fb_blank alone
    does nothing -- proved live with `echo 0 > /sys/class/graphics/fb0/blank`,
    which re-enabled the panel but left every subsequent pan failing with
        decon_pan_display: decon0 state(6), UNBLANK missed
    1289 times until a FBIOPUT_VSCREENINFO was issued).  A long-running animation
    must therefore repair the panel itself instead of assuming the one-shot
    bring-up at startup is permanent. */
 long r1=ioc(FBFD,FBIOBLANK,FB_BLANK_UNBLANK);
 V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
 long r2=ioc(FBFD,FBIOPUT_VSCREENINFO,(long)&V);
 long r3=ioc(FBFD,FBIOPAN_DISPLAY,(long)&V);
 wru("NUXEL_ANIM_UNBLANK_rc",(u64)r1); wru("NUXEL_ANIM_ACTIVATE_rc",(u64)r2); wru("NUXEL_ANIM_PAN_rc",(u64)r3);

 /* --- take the framebuffer over from the first-light painter -------------- */
 if(A_TAKEOVER){
  /* Bounded retry: the player may start a few milliseconds before the rootfs
     handoff finishes, and /proc must be reachable for a VERIFIED kill (mission
     section 7: never trust a pid file, always check the process identity). */
  int k=-1, attempts=0;
  for(attempts=0;attempts<24;attempts++){
   k=takeover_painters();
   if(k>=0) break;
   sleep_ns(50000000ull);      /* 50 ms -> at most 1.2 s, never unbounded */
  }
  wru("NUXEL_ANIM_TAKEOVER_ATTEMPTS",(u64)attempts);
  wru("NUXEL_ANIM_TAKEOVER_SCAN_RC",(u64)(k<0?1:0));
  wru("NUXEL_ANIM_TAKEOVER_KILLED",(u64)(k<0?0:k));
  if(k<0) wr("NUXEL_ANIM_TAKEOVER_UNRESOLVED\n");
  if(k>0){
   if(A_HOLDPID){ char hb[128]; int hi=0;
     for(int q=0;q<TAKEOVER_N;q++){ char td[24]; int tk=0; u64 tv=TAKEOVER_PIDS[q];
       if(!tv)td[tk++]='0'; while(tv){td[tk++]='0'+(int)(tv%10);tv/=10;}
       while(tk&&hi<120)hb[hi++]=td[--tk];
       if(q+1<TAKEOVER_N&&hi<120)hb[hi++]=','; }
     hb[hi++]='\n'; hb[hi]=0; write_file_at(A_HOLDPID,hb);
   }
   sleep_ns(400000000ull);   /* let the penguin painter actually stop */
  }
 }

 /* --- wait, bounded, for the painter we signalled to actually go away ------- */
 if(A_TAKEOVER&&TAKEOVER_N>0){
  int gone=0;
  for(int t=0;t<40;t++){                    /* <=1.0 s bounded acknowledgement */
   gone=1;
   for(int q=0;q<TAKEOVER_N;q++) if(pid_alive_comm(TAKEOVER_PIDS[q],"nuxel-fb-phone")){ gone=0; break; }
   if(gone) break;
   sleep_ns(25000000ull);
  }
  wru("NUXEL_ANIM_TAKEOVER_STOPPED",(u64)gone);
 }

 /* --- frame 0: full index plane, full repaint into every buffer ---------- */
 const u8 *ft=CONT+ANIM_HDR_BYTES;
 u32 o0,s0; rl32(ft,&o0,&s0);
 if(o0+s0>CONT_LEN){ wr("NUXEL_ANIM_BAD_TABLE\n"); quit(15); }
 long n0=inflate_raw(CONT+o0,s0,SCR,scratch_cap);
 if(n0!=(long)idxbytes){ wru("NUXEL_ANIM_FRAME0_INFLATE_BAD",(u64)(n0<0?-1:n0)); quit(16); }
 for(u64 i=0;i<idxbytes;i++) IDX[i]=SCR[i];
 /* Letterbox bars in the ARTWORK's own background colour (the most frequent index
    of frame 0), not an arbitrary black: the mission forbids inventing a visible
    rectangle, and a mismatched bar would be exactly that. */
 { u64 hist[256]; for(int q=0;q<256;q++) hist[q]=0;
   for(u64 i=0;i<idxbytes;i++) hist[IDX[i]]++;
   u32 best=0; for(int q=1;q<(int)PALN;q++) if(hist[q]>hist[best]) best=(u32)q;
   FB_BG=DSTPIX[best];
   wru("NUXEL_ANIM_BG_INDEX",(u64)best);
   wru("NUXEL_ANIM_BG_SRC565",(u64)PAL565[best]);
   wru("NUXEL_ANIM_BG_DST",(u64)FB_BG);
 }
 fill_panel(FB_BG);
 for(u32 y=0;y<AH;y++) blit_run(y,0,AW,IDX+y*AW);
 ioc(FBFD,FBIOPAN_DISPLAY,(long)&V);
 wr("NUXEL_ANIM_MARKER FIRST_FRAME_COMMITTED\n");
 /* Ownership handshake: the panel is now demonstrably MP4, so init.sh may hand
    the rootfs over and must NOT start the first-light penguin painter. */
 if(A_STATEDIR) write_file_at("fb-anim-ready","MP4_FIRST_FRAME_COMMITTED\n");
 wru("NUXEL_ANIM_MARKER_ORIGINAL_MP4_ANIMATION_FRAMES",NF);
 if(A_STATE) write_file_at(A_STATE,"ANIM_STAGE=MP4_PLAYER_ACTIVE\n");

 /* --- playback ----------------------------------------------------------- */
 u64 frame_ns = (u64)(1000000000ull*(u64)FPSD/(u64)(FPSN?FPSN:1));
 if(!frame_ns) frame_ns=1000000000ull/24u;
 const u64 START=now_ns();
 u64 deadline=START;
 u64 drawn=0,skipped=0,loops=0,REASSERT=0,PANFAIL=0;
 for(;;){
  for(u32 f=1;f<NF;f++){
   if(STOP) break;
   u32 off,sz; rl32(ft+8u*(u64)f,&off,&sz);
   if(off+sz>CONT_LEN){ wr("NUXEL_ANIM_BAD_TABLE\n"); quit(17); }
   long n=inflate_raw(CONT+off,sz,SCR,scratch_cap);
   if(n<0){ wru("NUXEL_ANIM_INFLATE_FAILED_FRAME",(u64)f); quit(18); }
   const u8 *p=SCR,*e=SCR+n; u32 pos=0;
   while(p<e){
    u32 gap=0,sh=0;
    for(;;){ if(p>=e){ wr("NUXEL_ANIM_SPAN_OVERRUN\n"); quit(19); }
             u8 b=*p++; gap|=(u32)(b&0x7f)<<sh; sh+=7; if(!(b&0x80))break; }
    if(gap==FTR_STOP) break;
    if(p+2>e){ wr("NUXEL_ANIM_SPAN_OVERRUN\n"); quit(19); }
    u32 len=(u32)p[0]|((u32)p[1]<<8); p+=2;
    if(p+len>e){ wr("NUXEL_ANIM_SPAN_OVERRUN\n"); quit(19); }
    pos+=gap;
    if((u64)pos+(u64)len>idxbytes){ wr("NUXEL_ANIM_SPAN_OUT_OF_RANGE\n"); quit(20); }
    u32 sy=pos/AW, sx0=pos%AW, done=0;
    while(done<len){
     u32 take=AW-sx0; if(take>len-done) take=len-done;
     for(u32 i=0;i<take;i++) IDX[pos+i]=p[i];
     blit_run(sy,sx0,sx0+take,IDX+ (u64)sy*AW);
     pos+=take; done+=take; sx0=0; sy++;
    }
    p+=len;
   }
   { long pr=ioc(FBFD,FBIOPAN_DISPLAY,(long)&V);
     if(pr!=0){
      PANFAIL++;
      if(PANFAIL==1||(PANFAIL%240u)==0){
       wru("NUXEL_ANIM_PAN_FAILED_TOTAL",PANFAIL);
       wru("NUXEL_ANIM_PAN_LAST_RC",(u64)pr);
      }
      /* the display was released underneath us: re-enable it and carry on */
      V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
      ioc(FBFD,FBIOBLANK,FB_BLANK_UNBLANK);
      ioc(FBFD,FBIOPUT_VSCREENINFO,(long)&V);
      REASSERT++;
      if(REASSERT<=3||(REASSERT%60u)==0) wru("NUXEL_ANIM_PAN_REASSERTED",REASSERT);
     } }
   drawn++;
   /* pace: sleep to the deadline; if we are already late, resynchronise instead
      of accumulating unbounded lag (late frames are effectively dropped). */
   deadline+=frame_ns;
   u64 t=now_ns();
   if(t+frame_ns*2ull<deadline){ skipped++; deadline=t+frame_ns; }
   else if(t<deadline) sleep_ns(deadline-t);
   if(A_STOPFILE && (drawn&7u)==0 && file_exists_at(A_STOPFILE)){ STOP=1; }
   if(STOP) break;
   if(A_SECS && (t-START)>=A_SECS*1000000000ull) break;
   /* Playback evidence, one line set every ~10 s (240 frames at 24 fps). */
   /* every ~10 s, re-assert the DECON unconditionally: two cheap ioctls against a
      panel that can be released by any other process on the system. */
   if((drawn%240u)==0){
    { V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
      ioc(FBFD,FBIOBLANK,FB_BLANK_UNBLANK); ioc(FBFD,FBIOPUT_VSCREENINFO,(long)&V); }
    u64 el=(t>START)?(t-START):0;
    wru("NUXEL_ANIM_HEARTBEAT_FRAMES",drawn);
    wru("NUXEL_ANIM_HEARTBEAT_MS",el/1000000ull);
    wru("NUXEL_ANIM_HEARTBEAT_SKIPS",skipped);
    wru("NUXEL_ANIM_HEARTBEAT_LOOPS",loops);
    wru("NUXEL_ANIM_EXPECTED_MS",(drawn*(frame_ns/1000000ull)));
   }
  }
  if(STOP) break;
  loops++;
  if(A_SECS && (now_ns()-START)>=A_SECS*1000000000ull) break;
  if(A_LOOPS && loops>=A_LOOPS) break;
  /* loop: frame 0 is a full index plane, so re-decode it and repaint in full.
     The span stream is a delta chain, so a wrap MUST re-anchor on frame 0. */
  long nr=inflate_raw(CONT+o0,s0,SCR,scratch_cap);
  if(nr!=(long)idxbytes){ wr("NUXEL_ANIM_LOOP_INFLATE_FAILED\n"); STOP=1; break; }
  for(u64 i=0;i<idxbytes;i++) IDX[i]=SCR[i];
  for(u32 y=0;y<AH;y++) blit_run(y,0,AW,IDX+(u64)y*AW);
  { long pr=ioc(FBFD,FBIOPAN_DISPLAY,(long)&V);
    if(pr!=0){ V.activate=FB_ACTIVATE_NOW; V.xoffset=0; V.yoffset=0;
      ioc(FBFD,FBIOBLANK,FB_BLANK_UNBLANK); ioc(FBFD,FBIOPUT_VSCREENINFO,(long)&V); REASSERT++; } }
  wru("NUXEL_ANIM_LOOP",loops);
 }
 wr("NUXEL_ANIM_MARKER ANIMATION_STOPPED\n");
 wru("NUXEL_ANIM_DRAWN_FRAMES",drawn); wru("NUXEL_ANIM_LAG_SKIPS",skipped); wru("NUXEL_ANIM_LOOPS",loops);
 wru("NUXEL_ANIM_PAN_FAILED_TOTAL",PANFAIL); wru("NUXEL_ANIM_PAN_REASSERTED",REASSERT);
 if(A_STATE) write_file_at(A_STATE,"ANIM_STAGE=ANIMATION_STOPPED\n");
 quit(0);
}

/* freestanding GCC still emits a memset reference for aggregate init in places */
void *memset(void*d,int c,u64 n){ volatile u8*p=(volatile u8*)d; while(n--)*p++=(u8)c; return d; }
void *memcpy(void*d,const void*s,u64 n){ u8*a=(u8*)d; const u8*b=(const u8*)s; while(n--)*a++=*b++; return d; }
#endif /* NUXEL_HOST */


/* ============================================================================
 * HOST SELF-TEST  (cc -DNUXEL_HOST ... -o anim-selftest)
 *
 * Decodes the container with the SAME inflate + span code the device runs and
 * prints a CRC32 per frame.  tools/s10plus/test-anim-player.sh compares those
 * CRCs with an independent Python decoder, so the device binary's decoder is
 * proven correct off-device instead of "looks right in review".
 * ==========================================================================*/
#ifdef NUXEL_HOST
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

static void wr(const char*s){ fputs(s,stdout); }
static void wru(const char*tag,u64 v){ printf("%s=%llu\n",tag,(unsigned long long)v); }
static void wrns(const char*tag,const char*s){ printf("%s=%s\n",tag,s); }

static uint32_t crc32b(const unsigned char*b,size_t n){
 uint32_t c=0xffffffffu;
 for(size_t i=0;i<n;i++){ c^=b[i]; for(int k=0;k<8;k++) c=(c>>1)^(0xEDB88320u & (uint32_t)(-(int)(c&1))); }
 return ~c;
}

int main(int argc,char**argv){
 if(argc<2){ fprintf(stderr,"usage: %s <container.nux> [--dump N --out DIR]\n",argv[0]); return 2; }
 FILE*f=fopen(argv[1],"rb"); if(!f){ perror("open"); return 2; }
 fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
 unsigned char *buf=malloc(n); if(fread(buf,1,n,f)!=(size_t)n){ fprintf(stderr,"short read\n"); return 2; }
 fclose(f);
 CONT=buf; CONT_LEN=(u32)n; HDR=(const struct anim_hdr*)buf;
 for(int i=0;i<8;i++) if(HDR->magic[i]!="NUXANM01"[i]){ fprintf(stderr,"bad magic\n"); return 3; }
 AW=HDR->width; AH=HDR->height; NF=HDR->frames; FPSN=HDR->fps_num; FPSD=HDR->fps_den?HDR->fps_den:1;
 PALN=HDR->palette_count; CS=HDR->flags;
 for(u32 i=0;i<PALN;i++) PAL565[i]=HDR->palette[i];
 printf("width=%u\nheight=%u\nframes=%u\nfps=%u\npalette=%u\nflags=%u\n",
        AW,AH,NF,FPSN/FPSD,PALN,CS);
 u64 idxbytes=(u64)AW*AH;
 u32 scratch_cap=(u32)(idxbytes>0x400000ull?idxbytes:0x400000ull);
 unsigned char *SCR=malloc(scratch_cap), *IDX=malloc(idxbytes);
 const u8 *ft=CONT+ANIM_HDR_BYTES;
 u32 o0,s0; rl32(ft,&o0,&s0);
 long g=inflate_raw(CONT+o0,s0,SCR,scratch_cap);
 if(g!=(long)idxbytes){ fprintf(stderr,"frame0 inflate %ld != %llu\n",g,(unsigned long long)idxbytes); return 4; }
 memcpy(IDX,SCR,idxbytes);
 printf("frame %u crc=%08x\n",0,crc32b(IDX,idxbytes));
 const char *dumpdir=NULL; long dumpframe=-1;
 for(int i=2;i<argc;i++){
   if(!strcmp(argv[i],"--dump")&&i+1<argc) dumpframe=atol(argv[++i]);
   else if(!strcmp(argv[i],"--out")&&i+1<argc) dumpdir=argv[++i];
 }
 for(u32 fr=1;fr<NF;fr++){
  u32 off,sz; rl32(ft+8u*(u64)fr,&off,&sz);
  long dn=inflate_raw(CONT+off,sz,SCR,scratch_cap);
  if(dn<0){ fprintf(stderr,"inflate failed at frame %u\n",fr); return 5; }
  const u8 *p=SCR,*e=SCR+dn; u32 pos=0;
  while(p<e){
   u32 gap=0,sh=0;
   for(;;){ u8 b=*p++; gap|=(u32)(b&0x7f)<<sh; sh+=7; if(!(b&0x80))break; }
   if(gap==FTR_STOP) break;
   u32 len=(u32)p[0]|((u32)p[1]<<8); p+=2;
   pos+=gap;
   if((u64)pos+(u64)len>idxbytes){ fprintf(stderr,"span oob frame %u\n",fr); return 6; }
   memcpy(IDX+pos,p,len); p+=len; pos+=len;
  }
  printf("frame %u crc=%08x\n",fr,crc32b(IDX,idxbytes));
  if((long)fr==dumpframe&&dumpdir){
    char path[512]; snprintf(path,sizeof(path),"%s/frame-%04u.ppm",dumpdir,fr);
    FILE*o=fopen(path,"wb"); fprintf(o,"P6\n%u %u\n255\n",AW,AH);
    for(u64 i=0;i<idxbytes;i++){ u16 c=PAL565[IDX[i]];
      unsigned char rgb[3]={(unsigned char)(((c>>11)&31)*255/31),(unsigned char)(((c>>5)&63)*255/63),(unsigned char)((c&31)*255/31)};
      fwrite(rgb,1,3,o); }
    fclose(o); printf("dumped %s\n",path);
  }
 }
 return 0;
}
#endif /* NUXEL_HOST */
