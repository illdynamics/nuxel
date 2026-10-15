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
typedef unsigned long u64;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef signed int s32;

static long sys(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0" : "+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");return x0;
}
static long op(const char*s){return sys(56,-100,(long)s,2,0,0,0);}          /* openat O_RDWR */
static int  io(long fd,long request,void* p){return (int)sys(29,fd,request,(long)p,0,0,0);}
static void closefd(long fd){sys(57,fd,0,0,0,0,0);}
static void quit(int code){sys(93,code,0,0,0,0,0);for(;;){}}
static void sleep_ms(long ms){long ts[2];ts[0]=ms/1000;ts[1]=(ms%1000)*1000000L;sys(101,(long)ts,0,0,0,0,0);}
static void wr(const char*s){u64 n=0;while(s[n])n++;if(n)sys(64,2,(long)s,n,0,0,0);}
static void wrn(const char*tag,u64 v){char b[96];int i=0;while(tag[i])i++;b[i++]='=';char d[24];int k=0;if(!v)d[k++]='0';while(v){d[k++]='0'+(int)(v%10);v/=10;}while(k)b[i++]=d[--k];b[i++]='\n';sys(64,2,(long)b,i,0,0,0);}
static void wrh(const char*tag,u64 v){char b[96];int i=0;while(tag[i])i++;b[i++]='=';b[i++]='0';b[i++]='x';char d[20];int k=0;if(!v)d[k++]='0';while(v){int h=(int)(v&15);d[k++]=h<10?('0'+h):('a'+h-10);v>>=4;}while(k)b[i++]=d[--k];b[i++]='\n';sys(64,2,(long)b,i,0,0,0);}

struct fb_bitfield{u32 offset,length,msb_right;};
struct fb_var{u32 xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bits_per_pixel,grayscale;
 struct fb_bitfield red,green,blue,transp;u32 nonstd,activate,height,width,accel_flags;
 u32 pixclock,left_margin,right_margin,upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace,reserved[4];};
struct fb_fix{char id[16];u64 smem_start;u32 smem_len,type,type_aux,visual;u16 xpanstep,ypanstep,ywrapstep;u32 line_length;u64 mmio_start;u32 mmio_len,accel;u16 capabilities,reserved[2];};

static u8 *fb;          /* mmap base of the whole virtual framebuffer */
static u8 *base;        /* current paint target (fb + TOFF*STRIDE)      */
static u64 mapped;
static u32 W,H,YVIR,STRIDE,BPP,TOFF;
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
 int hold=0; long hold_secs=0;
 for(long i=1;i<argc;i++){
   const char*a=argv[i];
   if(a[0]=='h'&&a[1]=='o'&&a[2]=='l'&&a[3]=='d'&&a[4]==0){
     hold=1;
     if(i+1<argc){ const char*n=argv[i+1]; int ok=n[0]!=0; long v=0;
       for(int j=0;n[j];j++){ if(n[j]<'0'||n[j]>'9'){ok=0;break;} v=v*10+(n[j]-'0'); }
       if(ok) hold_secs=v; }
     break;
   }
 }

 long fd=op("/dev/fb0"); if(fd<0) fd=op("/dev/graphics/fb0");
 if(fd<0){wr("NUXEL_FB_UNAVAILABLE no /dev/fb0\n");quit(2);}
 struct fb_fix F; for(u64 i=0;i<sizeof(F);i++)((u8*)&F)[i]=0;
 for(u64 i=0;i<sizeof(V);i++)((u8*)&V)[i]=0;
 if(io(fd,FBIOGET_VSCREENINFO,&V)<0||io(fd,FBIOGET_FSCREENINFO,&F)<0){wr("NUXEL_FB_IOCTL_FAILED\n");quit(3);}
 W=V.xres;H=V.yres;YVIR=V.yres_virtual?V.yres_virtual:V.yres;STRIDE=F.line_length;BPP=V.bits_per_pixel;
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

 int nb=paint_all_buffers();
 NBUFS=nb<1?1:nb;
 wrn("NUXEL_FB_BUFFERS_PAINTED",(u64)nb);

 /* Prove the store actually landed in the mapped memory the DECON scans. */
 wrh("NUXEL_FB_READBACK_px0",*(volatile u32*)(fb+0));
 wrh("NUXEL_FB_READBACK_center",*(volatile u32*)(fb+(u64)(H/2)*STRIDE+(u64)(W/2)*(BPP/8)));

 PCX=(int)W/2; PCY=(int)(H*55/100);
 PSIZE=(int)W/9; if(PSIZE<40)PSIZE=40;

 scanout_commit(fd,1);
 for(int f=1;f<12;f++){ spin_frame(f); wrn("NUXEL_FB_ANIM frame",(u64)f); scanout_commit(fd,0); sleep_ms(250); }
 wr("NUXEL_FB_ANIM_DONE frames=12\n");
 wr("NUXEL_FB_DRAW_SUCCESS first-light frame + penguin animation written; panel visibility still needs the operator\n");
 wr("NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE\n");

 if(hold){
   wr("NUXEL_FB_HOLD_START\n");
   int f=0; unsigned long fr=0;
   for(;;){
     f=(f+1)%12; if(f==0) f=1;
     spin_frame(f); scanout_commit(fd,0);
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
