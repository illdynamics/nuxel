#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/ioctl.h>

#define MAX_DECON_WIN 6
#define MAX_PLANE_CNT 3
typedef uint64_t dma_addr_t;
typedef uint32_t u32;

enum dpp_rotate { DPP_ROT_NORMAL=0 };
enum dpp_csc_eq { CSC_BT_601=0 };
enum dpp_comp_src { DPP_COMP_SRC_NONE=0 };
enum dpp_hdr_standard { DPP_HDR_OFF=0 };
enum decon_idma_type { IDMA_G0=0, IDMA_G1, IDMA_VG0, IDMA_VG1, IDMA_VGF0, IDMA_VGF1, ODMA_WB, MAX_DECON_DMA_TYPE };
enum decon_blending { DECON_BLENDING_NONE=0, DECON_BLENDING_PREMULT=1, DECON_BLENDING_COVERAGE=2, DECON_BLENDING_MAX=3 };
enum decon_pixel_format { DECON_PIXEL_FORMAT_ARGB_8888=0, DECON_PIXEL_FORMAT_ABGR_8888, DECON_PIXEL_FORMAT_RGBA_8888, DECON_PIXEL_FORMAT_BGRA_8888, DECON_PIXEL_FORMAT_XRGB_8888, DECON_PIXEL_FORMAT_XBGR_8888, DECON_PIXEL_FORMAT_RGBX_8888, DECON_PIXEL_FORMAT_BGRX_8888, DECON_PIXEL_FORMAT_RGBA_5551, DECON_PIXEL_FORMAT_BGRA_5551, DECON_PIXEL_FORMAT_ABGR_4444, DECON_PIXEL_FORMAT_RGBA_4444, DECON_PIXEL_FORMAT_BGRA_4444, DECON_PIXEL_FORMAT_RGB_565, DECON_PIXEL_FORMAT_BGR_565 };

struct decon_win_rect { int x; int y; u32 w; u32 h; };
struct dpp_params { dma_addr_t addr[MAX_PLANE_CNT]; enum dpp_rotate rot; enum dpp_csc_eq eq_mode; enum dpp_comp_src comp_src; enum dpp_hdr_standard hdr_std; u32 min_luminance; u32 max_luminance; };
struct decon_frame { int x; int y; u32 w; u32 h; u32 f_w; u32 f_h; };
struct decon_win_config {
    enum { DECON_WIN_STATE_DISABLED=0, DECON_WIN_STATE_COLOR, DECON_WIN_STATE_BUFFER, DECON_WIN_STATE_UPDATE, DECON_WIN_STATE_CURSOR, DECON_WIN_STATE_MRESOL=0x10000 } state;
    union {
        u32 color;
        struct {
            int fd_idma[3]; int acq_fence; int rel_fence; int plane_alpha;
            enum decon_blending blending; enum decon_idma_type idma_type; enum decon_pixel_format format;
            struct dpp_params dpp_parm;
            struct decon_win_rect block_area, transparent_area, opaque_area;
            struct decon_frame src;
        };
    };
    struct decon_frame dst;
    bool protection; bool compression; u32 wcg_mode;
};
struct decon_win_config_extra { int remained_frames; u32 reserved[7]; };
struct decon_win_config_data { int retire_fence; int fd_odma; struct decon_win_config config[MAX_DECON_WIN+1]; struct decon_win_config_extra extra; };

#define S3CFB_WIN_CONFIG _IOW('F', 209, struct decon_win_config_data)
#define FBIOBLANK 0x4611
#define FB_BLANK_UNBLANK 0

struct ion_allocation_data { uint64_t len; uint32_t heap_id_mask; uint32_t flags; uint32_t fd; uint32_t unused; };
#define ION_IOC_MAGIC 'I'
#define ION_IOC_ALLOC _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)

int main(int argc, char **argv) {
    (void)argc;
    printf("sizeof win_config=%zu data=%zu offset dst=%zu prot=%zu comp=%zu wcg=%zu\n",
        sizeof(struct decon_win_config), sizeof(struct decon_win_config_data),
        offsetof(struct decon_win_config,dst), offsetof(struct decon_win_config,protection),
        offsetof(struct decon_win_config,compression), offsetof(struct decon_win_config,wcg_mode));
    int W=640,H=480;
    if (getenv("W")) W=atoi(getenv("W"));
    if (getenv("H")) H=atoi(getenv("H"));
    int ifd=open("/dev/ion", O_RDWR);
    if (ifd<0){ perror("open ion"); return 1; }
    struct ion_allocation_data a; memset(&a,0,sizeof(a));
    a.len=(uint64_t)W*H*4; a.heap_id_mask=1u<<0; a.flags=0;
    if (ioctl(ifd, ION_IOC_ALLOC, &a)<0){ perror("ION_IOC_ALLOC"); return 1; }
    printf("ion fd=%u len=%llu\n", a.fd, (unsigned long long)a.len);
    uint32_t *p=mmap(NULL,(size_t)a.len,PROT_READ|PROT_WRITE,MAP_SHARED,a.fd,0);
    if (p==MAP_FAILED){ perror("mmap ion"); return 1; }
    for (int y=0;y<H;y++) for(int x=0;x<W;x++){
        uint32_t v=0xff000000u;
        if (x<40||y<40||x>=W-40||y>=H-40) v=0xffffffffu;
        else if (x<W/3) v=0xff0000ffu;
        else if (x<2*W/3) v=0xff00ff00u;
        else v=0xffff0000u;
        p[y*W+x]=v;
    }
    msync(p,(size_t)a.len,MS_SYNC);
    int fb=open("/dev/fb1",O_RDWR);
    if(fb<0){perror("open fb1");return 1;}
    if(ioctl(fb,FBIOBLANK,FB_BLANK_UNBLANK)<0) perror("FBIOBLANK");
    else printf("unblank ok\n");
    struct decon_win_config_data wd; memset(&wd,0,sizeof(wd));
    wd.retire_fence=-1; wd.fd_odma=-1;
    for(int i=0;i<=MAX_DECON_WIN;i++){ wd.config[i].state=DECON_WIN_STATE_DISABLED; wd.config[i].fd_idma[0]=wd.config[i].fd_idma[1]=wd.config[i].fd_idma[2]=-1; wd.config[i].acq_fence=-1; wd.config[i].rel_fence=-1; }
    struct decon_win_config *c=&wd.config[4];
    c->state=DECON_WIN_STATE_BUFFER;
    c->fd_idma[0]=a.fd; c->fd_idma[1]=-1; c->fd_idma[2]=-1;
    c->acq_fence=-1; c->rel_fence=-1; c->plane_alpha=255;
    c->blending=DECON_BLENDING_NONE;
    c->idma_type=IDMA_G1;
    c->format=DECON_PIXEL_FORMAT_ABGR_8888;
    c->dpp_parm.rot=DPP_ROT_NORMAL; c->dpp_parm.eq_mode=CSC_BT_601; c->dpp_parm.comp_src=DPP_COMP_SRC_NONE; c->dpp_parm.hdr_std=DPP_HDR_OFF;
    c->src.x=0;c->src.y=0;c->src.w=W;c->src.h=H;c->src.f_w=W;c->src.f_h=H;
    c->dst.x=0;c->dst.y=0;c->dst.w=W;c->dst.h=H;c->dst.f_w=W;c->dst.f_h=H;
    c->protection=0;c->compression=0;c->wcg_mode=0;
    errno=0;
    int r=ioctl(fb,S3CFB_WIN_CONFIG,&wd);
    printf("WIN_CONFIG ret=%d errno=%d (%s) retire_fence=%d\n", r, errno, strerror(errno), wd.retire_fence);
    if (r==0 && wd.retire_fence>=0) close(wd.retire_fence);
    sleep(8);
    printf("done\n");
    return 0;
}
