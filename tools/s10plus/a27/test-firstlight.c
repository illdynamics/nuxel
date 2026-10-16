/* ============================================================================
 * test-firstlight.c — OFF-DEVICE test harness for the A27 NUXSPL01 renderer.
 *
 * Compiles the *pure* half of tools/s10plus/nuxel-fb-phone.c (the same
 * spl_parse()/spl_render() the handset runs) for the host and dumps the rendered
 * panel buffer as raw little-endian u32 words in ABGR_8888 order.
 *
 *   cc -O1 -w -o test-firstlight tools/s10plus/a27/test-firstlight.c
 *   ./test-firstlight <asset.rawspl> <out.raw> [W H]
 *
 * tools/s10plus/a27/ref-firstlight.py renders the SAME frame from the same asset
 * with an INDEPENDENT implementation of the animation player's own maths (palette
 * expansion, integer nearest-neighbour spans, letterbox background, every virtual
 * buffer) and compares the two buffers byte-for-byte.  That is what proves the
 * early frame and the player's first committed frame are the same pixels, not
 * "looks about right".
 * ==========================================================================*/
#define NUXEL_FIRSTLIGHT_HOST 1
#include "../nuxel-fb-phone.c"

int main(int argc,char**argv){
 if(argc<3){ fprintf(stderr,"usage: %s <asset.rawspl> <out.raw> [W H]\n",argv[0]); return 2; }
 FILE*f=fopen(argv[1],"rb"); if(!f){ perror("open"); return 2; }
 fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
 unsigned char *buf=malloc((size_t)n);
 if(fread(buf,1,(size_t)n,f)!=(size_t)n){ perror("read"); return 2; }
 fclose(f);
 struct spl_frame F; int e=spl_parse(buf,(u64)n,&F);
 printf("PARSE_RC=%d\nPARSE_NAME=%s\n",e,spl_err_name(e));
 if(e) return 1;
 printf("SRC_W=%u\nSRC_H=%u\nPALETTE=%u\nFLAGS=%u\nINDEX_BYTES=%llu\n",
        F.w,F.h,F.paln,F.flags,(unsigned long long)F.bytes);
 if(argc>=5){ W=(u32)atoi(argv[3]); H=(u32)atoi(argv[4]); } else { W=1440; H=3040; }
 YVIR=H*2; STRIDE=W*4; BPP=32;
 V.red.offset=0; V.green.offset=8; V.blue.offset=16;
 V.red.length=8; V.green.length=8; V.blue.length=8;
 u64 mapped=(u64)STRIDE*(u64)YVIR;
 unsigned char *FBUF=malloc((size_t)mapped);
 for(u64 i=0;i<mapped;i++) FBUF[i]=0xA5;      /* poison: any untouched byte shows */
 u32 bufs=YVIR/H; if(bufs<1)bufs=1; if(bufs>4)bufs=4;
 int rc=spl_render(&F,FBUF,W,H,YVIR,STRIDE,BPP,mapped,bufs);
 printf("RENDER_RC=%d\n",rc);
 if(rc) return 1;
 printf("BG_INDEX=%u\nBG_DST=0x%08x\nDST_W=%u\nDST_H=%u\nDST_X=%u\nDST_Y=%u\nBUFFERS=%u\n",
        SPDBG_INDEX,SPDBG_DST,SPLDW,SPLDH,SPLOX,SPLOY,bufs);
 FILE*o=fopen(argv[2],"wb"); if(!o){ perror("write"); return 2; }
 fwrite(FBUF,1,(size_t)mapped,o); fclose(o);
 printf("WROTE=%s (%llu bytes)\n",argv[2],(unsigned long long)mapped);
 return 0;
}
