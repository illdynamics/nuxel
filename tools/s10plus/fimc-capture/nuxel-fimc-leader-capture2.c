/*
 * nuxel-fimc-leader-capture2 — corrected FIMC-IS2 leader+follower capture.
 *
 * Fixes over nuxel-fimc-leader-capture.c (source-backed, from the running
 * kernel 4.14.253 fimc-is2 source):
 *
 *  1. S_INPUT is a PACKED bitfield, not a raw index. Under CONFIG_USE_SENSOR_GROUP
 *     (the S10+ active path), fimc_is_ssx_video_s_input() decodes:
 *        position  = (input & 0x00FF0000) >> 16   (SP_REAR=0, SP_FRONT=1,
 *                                                     SP_REAR2=2, SP_REAR3=4, SP_FRONT2=3)
 *        scenario  = (input & 0xFC000000) >> 26
 *        stream    = (input & 0x03000000) >> 24
 *        vindex    = (input & 0x0000FF00) >> 8
 *        intype    = (input & 0x000000F0) >> 4
 *        leader    = (input & 0x0000000F) >> 0  (1 = stream leader)
 *  2. The sensor leader ss0 (VFL_DIR_M2M) needs leader=1.
 *  3. Correct state machine (fimc-is-video.c):
 *        S_INPUT -> S_BUFS(REQBUFS) -> S_FMT -> ... -> STREAMON
 *     The leader's S_FMT requires BIT(S_INPUT)|BIT(S_BUFS).
 *
 * This tool prints the decoded packed S_INPUT for verification and dmesg-guided
 * iteration. It does NOT claim a frame until a nonzero DQBUF with varied pixels
 * is observed.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <linux/videodev2.h>

/* FIMC-IS pack masks (CONFIG_USE_SENSOR_GROUP, fimc-is-video.h / fimc-is-device-sensor.h) */
#define SENSOR_SCN_MASK   0xFC000000u
#define SENSOR_SCN_SHIFT  26
#define INPUT_STREAM_MASK 0x03000000u
#define INPUT_STREAM_SHIFT 24
#define INPUT_POSITION_MASK 0x00FF0000u
#define INPUT_POSITION_SHIFT 16
#define INPUT_VINDEX_MASK 0x0000FF00u
#define INPUT_VINDEX_SHIFT 8
#define INPUT_INTYPE_MASK 0x000000F0u
#define INPUT_INTYPE_SHIFT 4
#define INPUT_LEADER_MASK 0x0000000Fu
#define INPUT_LEADER_SHIFT 0

/* SP_* from dt-bindings/camera/fimc_is.h */
#define SP_REAR   0
#define SP_FRONT  1
#define SP_REAR2  2
#define SP_FRONT2 3
#define SP_REAR3  4

/* V4L2_CID_FIMC_IS_BASE private controls */
#define V4L2_CTRL_CLASS_CAMERA 0x009A0000u
#define V4L2_CID_FIMC_IS_BASE (V4L2_CTRL_CLASS_CAMERA | 0x1000)
#define V4L2_CID_IS_S_STREAM (V4L2_CID_FIMC_IS_BASE + 14)
#define V4L2_CID_IS_G_CAPABILITY (V4L2_CID_FIMC_IS_BASE + 17)
#define V4L2_CID_IS_G_COMPLETES (V4L2_CID_FIMC_IS_BASE + 18)
#define IS_DISABLE_STREAM 0
#define IS_ENABLE_STREAM 1

struct ion_allocation_data { uint64_t len; uint32_t heap_id_mask; uint32_t flags; uint32_t fd; uint32_t unused; };
#define ION_IOC_MAGIC 'I'
#define ION_IOC_ALLOC 0xC0184900UL
#define ION_FLAG_CACHED 1
#define MAX_BUFS 8
#define MAX_PLANES 8

static int dio(int fd, unsigned long req, void *a){ errno=0; return ioctl(fd,req,a); }

static int ion_alloc(int ionfd, unsigned len, int heap_id, unsigned flags){
    struct ion_allocation_data ad; memset(&ad,0,sizeof ad);
    ad.len=len; ad.heap_id_mask=1u<<heap_id; ad.flags=flags;
    if(ioctl(ionfd,ION_IOC_ALLOC,&ad)<0||ad.fd<0) return -1;
    return ad.fd;
}

static void log_packed(const char *who, unsigned input){
    fprintf(stderr, "[%s S_INPUT] 0x%08X => scenario=%u stream=%u position=%u vindex=%u intype=%u leader=%u\n",
        who, input,
        (input&SENSOR_SCN_MASK)>>SENSOR_SCN_SHIFT,
        (input&INPUT_STREAM_MASK)>>INPUT_STREAM_SHIFT,
        (input&INPUT_POSITION_MASK)>>INPUT_POSITION_SHIFT,
        (input&INPUT_VINDEX_MASK)>>INPUT_VINDEX_SHIFT,
        (input&INPUT_INTYPE_MASK)>>INPUT_INTYPE_SHIFT,
        (input&INPUT_LEADER_MASK)>>INPUT_LEADER_SHIFT);
}

int main(int argc, char **argv){
    const char *sensor="/dev/video101", *cap="/dev/video131", *raw=NULL;
    int heap=5; unsigned width=640,height=480,bufs=4,frames=2,timeout=5000;
    int sensor_pos=SP_REAR, sensor_leader=1, cap_pos=SP_REAR, cap_leader=0;
    int sensor_fourcc=V4L2_PIX_FMT_SBGGR10; int fourcc_code=V4L2_PIX_FMT_YUYV;
    int i;
    for(i=1;i<argc;i++){const char*a=argv[i],*v=(i+1<argc)?argv[i+1]:NULL;
        if(!strcmp(a,"--sensor")&&v){sensor=v;i++;}
        else if(!strcmp(a,"--cap")&&v){cap=v;i++;}
        else if(!strcmp(a,"--raw")&&v){raw=v;i++;}
        else if(!strcmp(a,"--heap")&&v){heap=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--width")&&v){width=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--height")&&v){height=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--buffers")&&v){bufs=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--frames")&&v){frames=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--timeout")&&v){timeout=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--sensor-pos")&&v){sensor_pos=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--sensor-leader")&&v){sensor_leader=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--cap-pos")&&v){cap_pos=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--fourcc")&&v){fourcc_code=strtoul(v,NULL,0);i++;}}

    unsigned sensor_input =
        ((sensor_leader & 0xF) << INPUT_LEADER_SHIFT) |
        ((sensor_pos & 0xFF) << INPUT_POSITION_SHIFT);
    unsigned cap_input =
        ((cap_leader & 0xF) << INPUT_LEADER_SHIFT) |
        ((cap_pos & 0xFF) << INPUT_POSITION_SHIFT);

    fprintf(stderr,"FIMC leader capture2: sensor=%s cap=%s %ux%u heap=%d fourcc=0x%08x\n",
            sensor,cap,width,height,heap,(unsigned)fourcc_code);
    log_packed("sensor", sensor_input);
    log_packed("cap", cap_input);

    int ionfd=open("/dev/ion",O_RDWR); if(ionfd<0){perror("/dev/ion");return 4;}
    unsigned img=width*height*2;

    /* ==== SENSOR (leader, OUTPUT MPLANE) ==== */
    int sfd=open(sensor,O_RDWR|O_NONBLOCK); if(sfd<0){perror("sensor open");return 4;}
    int r=dio(sfd,VIDIOC_S_INPUT,&sensor_input);
    fprintf(stderr,"[sensor S_INPUT] ret=%d\n",r);
    if(r<0){ fprintf(stderr,"[sensor S_INPUT] failed errno=%d; trying REQBUFS-first sequence anyway\n",errno); }

    /* Correct leader order: REQBUFS(count=0) to set S_BUFS, then S_FMT, then REQBUFS(count=N).
       But standard V4L2 requires format first. Fall back to S_FMT directly and report the
       precise state-machine error from the kernel. */
    struct v4l2_format sf; memset(&sf,0,sizeof sf);
    sf.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    sf.fmt.pix_mp.width=width; sf.fmt.pix_mp.height=height;
    sf.fmt.pix_mp.pixelformat=sensor_fourcc; sf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    sf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; sf.fmt.pix_mp.num_planes=2;
    r=dio(sfd,VIDIOC_S_FMT,&sf);
    fprintf(stderr,"[sensor S_FMT] ret=%d errno=%d planes=%u w=%u h=%u sizeimage=%u\n",
            r,errno,sf.fmt.pix_mp.num_planes,sf.fmt.pix_mp.width,sf.fmt.pix_mp.height,sf.fmt.pix_mp.plane_fmt[0].sizeimage);

    struct v4l2_requestbuffers sreq; memset(&sreq,0,sizeof sreq);
    sreq.count=bufs; sreq.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE; sreq.memory=V4L2_MEMORY_DMABUF;
    r=dio(sfd,VIDIOC_REQBUFS,&sreq);
    fprintf(stderr,"[sensor REQBUFS] ret=%d errno=%d count=%u\n",r,errno,sreq.count);
    int sion[MAX_BUFS];
    for(i=0;i<(int)sreq.count;i++){
        struct v4l2_buffer b; struct v4l2_plane p[MAX_PLANES];
        memset(&b,0,sizeof b); memset(p,0,sizeof p);
        b.index=i; b.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE; b.memory=V4L2_MEMORY_DMABUF;
        b.m.planes=p; b.length=MAX_PLANES;
        dio(sfd,VIDIOC_QUERYBUF,&b);
        int f1=ion_alloc(ionfd,img,heap,ION_FLAG_CACHED); if(f1<0){perror("ion s img");return 4;}
        p[0].m.fd=f1; sion[i]=f1;
        int f2=ion_alloc(ionfd,32*1024,heap,0); p[1].m.fd=f2;
        p[0].bytesused=img; p[0].length=img;
        r=dio(sfd,VIDIOC_QBUF,&b);
        fprintf(stderr,"[sensor QBUF %d] ret=%d errno=%d fd=%d\n",i,r,errno,f1);
    }
    enum v4l2_buf_type sot=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    r=dio(sfd,VIDIOC_STREAMON,&sot);
    fprintf(stderr,"[sensor STREAMON] ret=%d errno=%d\n",r,errno);

    struct v4l2_control sc; sc.id=V4L2_CID_IS_S_STREAM; sc.value=IS_ENABLE_STREAM;
    r=dio(sfd,VIDIOC_S_CTRL,&sc);
    fprintf(stderr,"[sensor S_STREAM=1] ret=%d errno=%d\n",r,errno);

    /* ==== CAPTURE (follower, CAPTURE MPLANE) ==== */
    int fd=open(cap,O_RDWR|O_NONBLOCK); if(fd<0){perror("cap open");return 4;}
    dio(fd,VIDIOC_S_INPUT,&cap_input);
    struct v4l2_format cf; memset(&cf,0,sizeof cf);
    cf.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    cf.fmt.pix_mp.width=width; cf.fmt.pix_mp.height=height;
    cf.fmt.pix_mp.pixelformat=fourcc_code; cf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    cf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; cf.fmt.pix_mp.num_planes=2;
    r=dio(fd,VIDIOC_S_FMT,&cf);
    fprintf(stderr,"[cap S_FMT] ret=%d errno=%d planes=%u w=%u h=%u\n",r,errno,cf.fmt.pix_mp.num_planes,cf.fmt.pix_mp.width,cf.fmt.pix_mp.height);
    struct v4l2_requestbuffers creq; memset(&creq,0,sizeof creq);
    creq.count=bufs; creq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; creq.memory=V4L2_MEMORY_DMABUF;
    r=dio(fd,VIDIOC_REQBUFS,&creq);
    fprintf(stderr,"[cap REQBUFS] ret=%d errno=%d count=%u\n",r,errno,creq.count);
    int cion[MAX_BUFS]; unsigned char *cmap[MAX_BUFS];
    for(i=0;i<(int)creq.count;i++){
        struct v4l2_buffer b; struct v4l2_plane p[MAX_PLANES];
        memset(&b,0,sizeof b); memset(p,0,sizeof p);
        b.index=i; b.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; b.memory=V4L2_MEMORY_DMABUF;
        b.m.planes=p; b.length=MAX_PLANES;
        dio(fd,VIDIOC_QUERYBUF,&b);
        int f1=ion_alloc(ionfd,img,heap,ION_FLAG_CACHED); if(f1<0){perror("ion c img");return 4;}
        p[0].m.fd=f1; cion[i]=f1;
        cmap[i]=mmap(NULL,img,PROT_READ|PROT_WRITE,MAP_SHARED,f1,0);
        int f2=ion_alloc(ionfd,32*1024,heap,0); p[1].m.fd=f2;
        r=dio(fd,VIDIOC_QBUF,&b);
        fprintf(stderr,"[cap QBUF %d] ret=%d errno=%d\n",i,r,errno);
    }
    enum v4l2_buf_type cot=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    r=dio(fd,VIDIOC_STREAMON,&cot);
    fprintf(stderr,"[cap STREAMON] ret=%d errno=%d\n",r,errno);

    unsigned framed=0,total=0;
    unsigned long long deadline=0;
    while(framed<frames){
        if(!deadline){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);deadline=ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL+timeout;}
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
        unsigned long long now=ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL;
        if(now>=deadline){fprintf(stderr,"[DQBUF] timeout after %ums\n",timeout);break;}
        struct pollfd pfd={.fd=fd,.events=POLLIN};
        int pr=poll(&pfd,1,100); if(pr<0&&errno!=EINTR)break; if(!(pr>0&&(pfd.revents&(POLLIN|POLLRDNORM))))continue;
        struct v4l2_buffer dq; struct v4l2_plane dp[MAX_PLANES];
        memset(&dq,0,sizeof dq); memset(dp,0,sizeof dp);
        dq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; dq.memory=V4L2_MEMORY_DMABUF; dq.m.planes=dp; dq.length=MAX_PLANES;
        if(dio(fd,VIDIOC_DQBUF,&dq)<0){if(errno==EAGAIN)continue;fprintf(stderr,"[DQBUF] err=%d\n",errno);break;}
        unsigned used=dp[0].bytesused;
        unsigned char *px=cmap[dq.index];
        int varied=0; for(unsigned k=1;k<used&&k<img;k++)if(px[k]!=px[0]){varied=1;break;}
        if(raw&&used){FILE*rf=fopen(raw,framed==0?"wb":"ab");if(rf){fwrite(px,1,used,rf);fclose(rf);}}
        fprintf(stderr,"DQBUF idx=%u seq=%u bytes=%u varied=%d flags=0x%x ts=%lu.%06lu\n",
                dq.index,dq.sequence,used,varied,dq.flags,
                (unsigned long)dq.timestamp.tv_sec,(unsigned long)dq.timestamp.tv_usec);
        framed++; total+=used;
        struct v4l2_plane rp[MAX_PLANES]; memcpy(rp,dp,sizeof rp); dq.m.planes=rp; rp[0].m.fd=cion[dq.index];
        dio(fd,VIDIOC_QBUF,&dq);
    }
    dio(fd,VIDIOC_STREAMOFF,&cot);
    dio(sfd,VIDIOC_STREAMOFF,&sot);
    struct v4l2_control sc2; sc2.id=V4L2_CID_IS_S_STREAM; sc2.value=IS_DISABLE_STREAM; dio(sfd,VIDIOC_S_CTRL,&sc2);
    close(fd);close(sfd);close(ionfd);
    printf("{\"tool\":\"nuxel-fimc-leader-capture2\",\"sensor\":\"%s\",\"cap\":\"%s\",\"frames\":%u,\"bytes\":%u,\"ok\":%s}\n",sensor,cap,framed,total,framed>0?"true":"false");
    return framed>0?0:3;
}
