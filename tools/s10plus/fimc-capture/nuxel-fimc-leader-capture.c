/*
 * nuxel-fimc-leader-capture — full FIMC-IS2 leader+follower stream capture.
 *
 * Samsung FIMC-IS2 (CONFIG_USE_SENSOR_GROUP) makes the sensor node (ss0) a
 * VIDEO_OUTPUT_MPLANE "leader" (M2M).  The ISP capture node (i0c) is the
 * follower.  Correct sequence:
 *   1. sensor ss0: S_INPUT(rear) + S_FMT(VIDEO_OUTPUT_MPLANE) + REQBUFS/QBUF(DMABUF)
 *      + STREAMON  -> starts the ISP firmware + sensor MIPI stream
 *   2. capture i0c: S_INPUT + S_FMT(VIDEO_CAPTURE_MPLANE) + REQBUFS/QBUF(DMABUF)
 *      + STREAMON -> DQBUF real frames
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

#define V4L2_CTRL_CLASS_CAMERA 0x009A0000
#define V4L2_CID_FIMC_IS_BASE (V4L2_CTRL_CLASS_CAMERA | 0x1000)
#define V4L2_CID_IS_S_STREAM (V4L2_CID_FIMC_IS_BASE + 14)
#define IS_DISABLE_STREAM 0
#define IS_ENABLE_STREAM 1

#define ION_IOC_MAGIC 'I'
struct ion_allocation_data { uint64_t len; uint32_t heap_id_mask; uint32_t flags; uint32_t fd; uint32_t unused; };
#define ION_FLAG_CACHED 1
#define ION_IOC_ALLOC 0xC0184900UL
#define MAX_BUFS 6
#define MAX_PLANES 8

static int dio(int fd, unsigned long req, void *a){ errno=0; int r=ioctl(fd,req,a); return r; }
static int ion_alloc(int ionfd, unsigned len, int heap_id, unsigned flags){
    struct ion_allocation_data ad; memset(&ad,0,sizeof ad);
    ad.len=len; ad.heap_id_mask=1u<<heap_id; ad.flags=flags;
    if(dio(ionfd,ION_IOC_ALLOC,&ad)<0||ad.fd<0) return -1;
    return ad.fd;
}

int main(int argc, char **argv){
    const char *sensor="/dev/video101", *cap="/dev/video131", *raw=NULL;
    int heap=5; unsigned width=640,height=480,bufs=4,frames=2,timeout=4000;
    int i;
    for(i=1;i<argc;i++){const char*a=argv[i],*v=(i+1<argc)?argv[i+1]:NULL;
        if(!strcmp(a,"--sensor")&&v){sensor=v;i++;}else if(!strcmp(a,"--cap")&&v){cap=v;i++;}
        else if(!strcmp(a,"--raw")&&v){raw=v;i++;}else if(!strcmp(a,"--heap")&&v){heap=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--width")&&v){width=strtoul(v,NULL,0);i++;}else if(!strcmp(a,"--height")&&v){height=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--buffers")&&v){bufs=strtoul(v,NULL,0);i++;}else if(!strcmp(a,"--frames")&&v){frames=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--timeout")&&v){timeout=strtoul(v,NULL,0);i++;}}
    fprintf(stderr,"FIMC leader capture: sensor=%s cap=%s %ux%u heap=%d\n",sensor,cap,width,height,heap);

    int ionfd=open("/dev/ion",O_RDWR); if(ionfd<0){perror("/dev/ion");return 4;}
    unsigned img=width*height*2;

    /* ==== SENSOR (leader, OUTPUT MPLANE) ==== */
    int sfd=open(sensor,O_RDWR|O_NONBLOCK); if(sfd<0){perror("sensor open");return 4;}
    unsigned inp=0; dio(sfd,VIDIOC_S_INPUT,&inp);
    struct v4l2_format sf; memset(&sf,0,sizeof sf);
    sf.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    sf.fmt.pix_mp.width=width; sf.fmt.pix_mp.height=height;
    sf.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_YUYV; sf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    sf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; sf.fmt.pix_mp.num_planes=2;
    int r=dio(sfd,VIDIOC_S_FMT,&sf);
    fprintf(stderr,"[sensor S_FMT] ret=%d planes=%u w=%u h=%u\n",r,sf.fmt.pix_mp.num_planes,sf.fmt.pix_mp.width,sf.fmt.pix_mp.height);
    struct v4l2_requestbuffers sreq; memset(&sreq,0,sizeof sreq);
    sreq.count=bufs; sreq.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE; sreq.memory=V4L2_MEMORY_DMABUF;
    r=dio(sfd,VIDIOC_REQBUFS,&sreq);
    fprintf(stderr,"[sensor REQBUFS] ret=%d count=%u\n",r,sreq.count);
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
        r=dio(sfd,VIDIOC_QBUF,&b);
        fprintf(stderr,"[sensor QBUF %d] ret=%d fd=%d\n",i,r,f1);
    }
    enum v4l2_buf_type sot=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    r=dio(sfd,VIDIOC_STREAMON,&sot);
    fprintf(stderr,"[sensor STREAMON] ret=%d errno=%d\n",r,errno);
    if(r<0){ perror("sensor STREAMON"); /* continue: maybe already streaming via S_STREAM */ }

    /* start sensor MIPI stream AFTER leader streamon */
    struct v4l2_control sc; sc.id=V4L2_CID_IS_S_STREAM; sc.value=IS_ENABLE_STREAM;
    dio(sfd,VIDIOC_S_CTRL,&sc);

    /* ==== CAPTURE (follower, CAPTURE MPLANE) ==== */
    int fd=open(cap,O_RDWR|O_NONBLOCK); if(fd<0){perror("cap open");return 4;}
    unsigned cinp=0; dio(fd,VIDIOC_S_INPUT,&cinp);
    struct v4l2_format cf; memset(&cf,0,sizeof cf);
    cf.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    cf.fmt.pix_mp.width=width; cf.fmt.pix_mp.height=height;
    cf.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_YUYV; cf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    cf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; cf.fmt.pix_mp.num_planes=2;
    dio(fd,VIDIOC_S_FMT,&cf);
    struct v4l2_requestbuffers creq; memset(&creq,0,sizeof creq);
    creq.count=bufs; creq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; creq.memory=V4L2_MEMORY_DMABUF;
    dio(fd,VIDIOC_REQBUFS,&creq);
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
        dio(fd,VIDIOC_QBUF,&b);
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
        if(now>=deadline){fprintf(stderr,"[DQBUF] timeout\n");break;}
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
        fprintf(stderr,"DQBUF idx=%u seq=%u bytes=%u varied=%d flags=0x%x\n",dq.index,dq.sequence,used,varied,dq.flags);
        framed++; total+=used;
        struct v4l2_plane rp[MAX_PLANES]; memcpy(rp,dp,sizeof rp); dq.m.planes=rp; rp[0].m.fd=cion[dq.index];
        dio(fd,VIDIOC_QBUF,&dq);
    }
    dio(fd,VIDIOC_STREAMOFF,&cot);
    dio(sfd,VIDIOC_STREAMOFF,&sot);
    struct v4l2_control sc2; sc2.id=V4L2_CID_IS_S_STREAM; sc2.value=IS_DISABLE_STREAM; dio(sfd,VIDIOC_S_CTRL,&sc2);
    close(fd);close(sfd);close(ionfd);
    printf("{\"tool\":\"nuxel-fimc-leader-capture\",\"sensor\":\"%s\",\"cap\":\"%s\",\"frames\":%u,\"bytes\":%u,\"ok\":%s}\n",sensor,cap,framed,total,framed>0?"true":"false");
    return framed>0?0:3;
}
