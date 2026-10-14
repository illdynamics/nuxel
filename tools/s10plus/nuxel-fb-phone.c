/* Nuxel S10+ first-light framebuffer diagnostic. AArch64 freestanding/static.
 * No libc, userspace dependencies or login. Only runs when /dev/fb0 is exposed.
 * This is a DISPLAY DIAGNOSTIC, NOT Phosh or a complete mobile OS shell.
 * See README: tested as ARM64 ELF, not tested on physical S10+ framebuffer.
 */
typedef unsigned long u64;
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
static long sys(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0" : "+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory");return x0;
}
static long op(const char*s){return sys(56,-100,(long)s,2,0,0,0);} /* openat */
static int io(long fd,long request,void* p){return (int)sys(29,fd,request,(long)p,0,0,0);}
static void closefd(long fd){sys(57,fd,0,0,0,0,0);}
static void quit(int code){sys(93,code,0,0,0,0,0);for(;;){}}
static void write2(const char*s){u64 n=0;while(s[n])n++;sys(64,2,(long)s,n,0,0,0);}
struct fb_bitfield{u32 offset,length,msb_right;};
struct fb_var{u32 xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bits_per_pixel,grayscale;
 struct fb_bitfield red,green,blue,transp;u32 nonstd,activate,height,width,accel_flags;
 u32 pixclock,left_margin,right_margin,upper_margin,lower_margin,hsync_len,vsync_len,sync,vmode,rotate,colorspace,reserved[4];};
struct fb_fix{char id[16];u64 smem_start;u32 smem_len,type,type_aux,visual;u16 xpanstep,ypanstep,ywrapstep;u32 line_length;u64 mmio_start;u32 mmio_len,accel;u16 capabilities,reserved[2];};
static u8 *base;static u64 mapped;static u32 W,H,STRIDE,BPP;static struct fb_var V;
static u32 pack(u32 r,u32 g,u32 b){
 u32 R=(r*((1u<<V.red.length)-1)+127)/255, G=(g*((1u<<V.green.length)-1)+127)/255, B=(b*((1u<<V.blue.length)-1)+127)/255;
 return (R<<V.red.offset)|(G<<V.green.offset)|(B<<V.blue.offset);}
static void pixel(int x,int y,u32 color){
 if(x<0||y<0||(u32)x>=W||(u32)y>=H)return;
 u64 off=(u64)(y+V.yoffset)*STRIDE+(u64)(x+V.xoffset)*(BPP/8);
 if(off+BPP/8>mapped)return;
 if(BPP==32){*(volatile u32*)(base+off)=color;}
 else if(BPP==16){*(volatile u16*)(base+off)=(u16)color;}
}
static void rect(int x,int y,int w,int h,u32 col){
 int x0=x<0?0:x,y0=y<0?0:y,x1=x+w>(int)W?(int)W:x+w,y1=y+h>(int)H?(int)H:y+h;
 for(int yy=y0;yy<y1;yy++)for(int xx=x0;xx<x1;xx++)pixel(xx,yy,col);
}
/* A fixed-width, small bitmap font for the diagnostic banner. */
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
 if(glyph[idx][row] & (1<<(4-col)))rect(x+col*s,y+row*s,s,s,c);
 }
}
static void center(int y,const char*t,int s,u32 c){int n=0;while(t[n])n++;text(((int)W-6*n*s)/2,y,t,s,c);}
void _start(void){
 long fd=op("/dev/fb0");if(fd<0)fd=op("/dev/graphics/fb0");
 if(fd<0){write2("NUXEL_FB_UNAVAILABLE no /dev/fb0\n");quit(2);}
 struct fb_fix F={0};V=(struct fb_var){0};
 if(io(fd,0x4600,&V)<0||io(fd,0x4602,&F)<0){write2("NUXEL_FB_IOCTL_FAILED\n");quit(3);}
 W=V.xres;H=V.yres;STRIDE=F.line_length;BPP=V.bits_per_pixel;
 if(W<64||H<64||W>10000||H>10000||(BPP!=16&&BPP!=32)||!V.red.length||!V.green.length||!V.blue.length||V.red.length>16||V.green.length>16||V.blue.length>16||STRIDE<(W*BPP/8)){
 write2("NUXEL_FB_UNSUPPORTED_PIXEL_FORMAT\n");quit(4);}
 mapped=F.smem_len;
 u64 min=(u64)STRIDE*(H+V.yoffset);if(mapped<min){write2("NUXEL_FB_SIZE_MISMATCH\n");quit(5);}
 long map=sys(222,0,mapped,3,1,fd,0); /* mmap: PROT_READ|WRITE MAP_SHARED */
 if(map<0){write2("NUXEL_FB_MMAP_FAILED\n");quit(6);}base=(u8*)map;
 u32 bg=pack(8,14,25),panel=pack(19,30,46),orange=pack(255,133,29),white=pack(233,241,249),muted=pack(141,159,180);
 rect(0,0,W,H,bg);rect(0,0,W,H/100+3,orange);
 int s=(int)W/170;if(s<2)s=2;if(s>12)s=12;
 center(H/5,"NUXEL",s*2,orange);
 center(H/5+19*s,"LINUX PHONE",s,white);
 int cardW=(int)(W*8/10),cardY=(int)(H*43/100),cardH=(int)(H*27/100);
 rect(((int)W-cardW)/2,cardY,cardW,cardH,panel);
 center(cardY+4*s,"GALAXY S10+",s,white);
 center(cardY+15*s,"DISPLAY TEST",s,orange);
 center(cardY+25*s,"EARLY BOOT",s,muted);
 center(H*84/100,"ARM64 - BEYOND2LTE",s,muted);
 write2("NUXEL_FB_DRAW_SUCCESS frame written; display visibility unverified\n");
 sys(11,(long)base,mapped,0,0,0,0);closefd(fd);quit(0);
}
void *memset(void*dest,int value,u64 len){volatile u8*p=(volatile u8*)dest;while(len--)*p++=(u8)value;return dest;}
