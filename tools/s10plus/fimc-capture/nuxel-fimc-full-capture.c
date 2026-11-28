/*
 * nuxel-fimc-full-capture — complete Samsung FIMC-IS2 capture for Nuxel S10+.
 *
 * Drives the Exynos9820 FIMC-IS2 vendor pipeline with the correct Samsung
 * private-control + ION DMABUF sequence:
 *   1. sensor node (ss0, /dev/video101): S_INPUT(rear) + S_CTRL(S_STREAM, enable)
 *   2. ISP capture node (i0c, /dev/video131): S_INPUT + S_FMT(YUYV 2 planes)
 *      + REQBUFS(DMABUF from ION camera_heap) + QBUF + STREAMON + DQBUF
 *   3. mmap the ION buffer fd to read the frame bytes back.
 *
 * Physical-frame evidence only; never fabricates pixels.
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
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <linux/videodev2.h>
#include <linux/videodev2_exynos_camera.h> /* may not exist on host; define below */

/* Fallbacks if the exynos header is absent on host */
#ifndef V4L2_CID_FIMC_IS_BASE
#define V4L2_CTRL_CLASS_CAMERA 0x009A0000
#define V4L2_CID_FIMC_IS_BASE (V4L2_CTRL_CLASS_CAMERA | 0x1000)
#define V4L2_CID_IS_S_STREAM   (V4L2_CID_FIMC_IS_BASE + 14)
#define V4L2_CID_IS_G_STREAM   (V4L2_CID_FIMC_IS_BASE + 15)
#define IS_DISABLE_STREAM 0
#define IS_ENABLE_STREAM  1
#endif
#define SENSOR_SSTREAM_MASK 0x0000000F
#define SENSOR_SSTREAM_SHIFT 0

/* Samsung 4.14 ION (fd returned in .fd) */
#define ION_IOC_MAGIC 'I'
struct ion_allocation_data { uint64_t len; uint32_t heap_id_mask; uint32_t flags; uint32_t fd; uint32_t unused; };
#define ION_FLAG_CACHED 1
#define ION_IOC_ALLOC 0xC0184900UL /* _IOWR('I',0,sizeof ion_allocation_data=24) */
#define CAMERA_HEAP_ID 5
#define MAX_BUFS 6
#define MAX_PLANES 8

struct opts { const char *sensor_node; const char *cap_node; const char *raw; int heap_id;
    unsigned width, height, buffers, frames, timeout_ms; };
static struct opts O = { .sensor_node="/dev/video101", .cap_node="/dev/video131", .raw=NULL,
    .heap_id=CAMERA_HEAP_ID, .width=1440, .height=1080, .buffers=4, .frames=1, .timeout_ms=4000 };

static const char *stage="none"; static int lasterr=0;
static int dio(int fd, unsigned long req, void *a, const char *n){ stage=n; errno=0; int r=ioctl(fd,req,a); lasterr=r<0?errno:0; return r; }

int main(int argc, char **argv) {
    int i;
    for (i=1;i<argc;i++){ const char *a=argv[i],*v=(i+1<argc)?argv[i+1]:NULL;
        if(!strcmp(a,"--sensor")&&v){O.sensor_node=v;i++;} else if(!strcmp(a,"--cap")&&v){O.cap_node=v;i++;}
        else if(!strcmp(a,"--raw")&&v){O.raw=v;i++;} else if(!strcmp(a,"--heap")&&v){O.heap_id=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--width")&&v){O.width=strtoul(v,NULL,0);i++;} else if(!strcmp(a,"--height")&&v){O.height=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--buffers")&&v){O.buffers=strtoul(v,NULL,0);i++;} else if(!strcmp(a,"--frames")&&v){O.frames=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--timeout")&&v){O.timeout_ms=strtoul(v,NULL,0);i++;}
        else {fprintf(stderr,"unknown: %s\n",a);return 2;} }

    /* ---- 1. sensor node: select rear + start sensor stream ---- */
    int sfd = open(O.sensor_node, O_RDWR | O_NONBLOCK);
    if (sfd<0){fprintf(stderr,"[sensor open] %s: %s\n",O.sensor_node,strerror(errno)); return 4;}
    struct v4l2_capability scap; memset(&scap,0,sizeof scap);
    if (dio(sfd, VIDIOC_QUERYCAP, &scap, "sensor QUERYCAP")<0){fprintf(stderr,"[sensor QUERYCAP] %s\n",strerror(lasterr));return 4;}
    fprintf(stderr,"[sensor] %s caps=0x%08x\n", O.sensor_node, scap.capabilities);
    unsigned inp=0; /* rear position 0 */
    if (dio(sfd, VIDIOC_S_INPUT, &inp, "sensor S_INPUT")<0){fprintf(stderr,"[sensor S_INPUT] %s\n",strerror(lasterr));return 4;}
    fprintf(stderr,"[sensor S_INPUT] OK (rear)\n");
    struct v4l2_control sc; sc.id=V4L2_CID_IS_S_STREAM; sc.value=IS_ENABLE_STREAM; /* sstream=1 */
    if (dio(sfd, VIDIOC_S_CTRL, &sc, "sensor S_CTRL(S_STREAM)")<0){fprintf(stderr,"[sensor S_STREAM] %s (continuing)\n",strerror(lasterr));}
    else fprintf(stderr,"[sensor S_STREAM] enabled\n");

    /* ---- 2. ION DMABUF allocation ---- */
    int ionfd=open("/dev/ion",O_RDWR);
    if(ionfd<0){fprintf(stderr,"[ion open] %s\n",strerror(errno));return 4;}
    unsigned img_size=O.width*O.height*2; int heap_mask=1u<<O.heap_id;
    int ionfds[MAX_BUFS]; unsigned char *ionmaps[MAX_BUFS];
    for(i=0;i<(int)O.buffers;i++){
        struct ion_allocation_data ad; memset(&ad,0,sizeof ad);
        ad.len=img_size; ad.heap_id_mask=heap_mask; ad.flags=ION_FLAG_CACHED;
        if(dio(ionfd,ION_IOC_ALLOC,&ad,"ion_alloc")<0||ad.fd<0){fprintf(stderr,"[ion_alloc] %d failed: %s\n",i,strerror(lasterr));return 4;}
        ionfds[i]=ad.fd; ionmaps[i]=mmap(NULL,img_size,PROT_READ|PROT_WRITE,MAP_SHARED,ad.fd,0);
        if(ionmaps[i]==MAP_FAILED){fprintf(stderr,"[ion mmap] %s\n",strerror(errno));return 4;}
        fprintf(stderr,"[ion] buf %d fd=%d heap=%d size=%u\n",i,ad.fd,O.heap_id,img_size);
    }

    /* ---- 3. capture node setup ---- */
    int fd=open(O.cap_node,O_RDWR|O_NONBLOCK);
    if(fd<0){fprintf(stderr,"[cap open] %s: %s\n",O.cap_node,strerror(errno));return 4;}
    struct v4l2_capability cap; memset(&cap,0,sizeof cap);
    if(dio(fd,VIDIOC_QUERYCAP,&cap,"QUERYCAP")<0){fprintf(stderr,"[QUERYCAP] %s\n",strerror(lasterr));return 4;}
    fprintf(stderr,"[cap] %s caps=0x%08x\n",O.cap_node,cap.capabilities);
    unsigned cinp=0;
    if(dio(fd,VIDIOC_S_INPUT,&cinp,"S_INPUT")<0){fprintf(stderr,"[S_INPUT] %s\n",strerror(lasterr));return 4;}
    struct v4l2_format fmt; memset(&fmt,0,sizeof fmt);
    fmt.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    fmt.fmt.pix_mp.width=O.width; fmt.fmt.pix_mp.height=O.height;
    fmt.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_YUYV; fmt.fmt.pix_mp.field=V4L2_FIELD_NONE;
    fmt.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; fmt.fmt.pix_mp.num_planes=2;
    if(dio(fd,VIDIOC_S_FMT,&fmt,"S_FMT")<0){fprintf(stderr,"[S_FMT] %s\n",strerror(lasterr));return 4;}
    fprintf(stderr,"[S_FMT] OK %ux%u planes=%u\n",fmt.fmt.pix_mp.width,fmt.fmt.pix_mp.height,fmt.fmt.pix_mp.num_planes);
    struct v4l2_requestbuffers req; memset(&req,0,sizeof req);
    req.count=O.buffers; req.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; req.memory=V4L2_MEMORY_DMABUF;
    if(dio(fd,VIDIOC_REQBUFS,&req,"REQBUFS")<0||req.count==0){fprintf(stderr,"[REQBUFS] %s\n",strerror(lasterr));return 4;}
    struct v4l2_buffer bufs[MAX_BUFS]; struct v4l2_plane pl[MAX_BUFS][MAX_PLANES];
    for(i=0;i<(int)req.count;i++){
        memset(&bufs[i],0,sizeof bufs[i]); memset(&pl[i],0,sizeof pl[i]);
        bufs[i].index=i; bufs[i].type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; bufs[i].memory=V4L2_MEMORY_DMABUF;
        bufs[i].m.planes=pl[i]; bufs[i].length=MAX_PLANES;
        if(dio(fd,VIDIOC_QUERYBUF,&bufs[i],"QUERYBUF")<0){fprintf(stderr,"[QUERYBUF %d] %s\n",i,strerror(lasterr));return 4;}
        pl[i][0].m.fd=ionfds[i];
        struct ion_allocation_data am; memset(&am,0,sizeof am);
        am.len=32*1024; am.heap_id_mask=heap_mask; am.flags=0;
        int metapl = (bufs[i].length>1)?1:0;
        if(metapl){ if(dio(ionfd,ION_IOC_ALLOC,&am,"ion_meta")<0||am.fd<0){fprintf(stderr,"[ion_meta] %s\n",strerror(lasterr));return 4;} pl[i][1].m.fd=am.fd; }
        if(dio(fd,VIDIOC_QBUF,&bufs[i],"QBUF")<0){fprintf(stderr,"[QBUF %d] %s\n",i,strerror(lasterr));return 4;}
        fprintf(stderr,"[QBUF %d] OK\n",i);
    }
    enum v4l2_buf_type bt=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    if(dio(fd,VIDIOC_STREAMON,&bt,"STREAMON")<0){fprintf(stderr,"[STREAMON] %s\n",strerror(lasterr));return 4;}
    fprintf(stderr,"[STREAMON] OK\n");

    /* ---- 4. DQBUF loop ---- */
    unsigned framed=0,total=0;
    unsigned long long deadline=0;
    while(framed<O.frames){
        if(!deadline){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);deadline=ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL+O.timeout_ms;}
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
        unsigned long long now=ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL;
        if(now>=deadline){fprintf(stderr,"[DQBUF] timeout\n");break;}
        struct pollfd pfd={.fd=fd,.events=POLLIN};
        int pr=poll(&pfd,1,100); if(pr<0&&errno!=EINTR){break;} if(!(pr>0&&(pfd.revents&(POLLIN|POLLRDNORM))))continue;
        struct v4l2_buffer dq; struct v4l2_plane dpl[MAX_PLANES];
        memset(&dq,0,sizeof dq); memset(dpl,0,sizeof dpl);
        dq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; dq.memory=V4L2_MEMORY_DMABUF; dq.m.planes=dpl; dq.length=MAX_PLANES;
        if(dio(fd,VIDIOC_DQBUF,&dq,"DQBUF")<0){if(errno==EAGAIN)continue;fprintf(stderr,"[DQBUF] %s\n",strerror(lasterr));break;}
        if(dq.index>=req.count){fprintf(stderr,"[DQBUF] bad idx\n");break;}
        unsigned bytesused=dpl[0].bytesused;
        unsigned char *px=ionmaps[dq.index];
        int varied=0; for(unsigned k=1;k<bytesused&&k<img_size;k++)if(px[k]!=px[0]){varied=1;break;}
        if(O.raw&&bytesused){FILE *rf=fopen(O.raw,framed==0?"wb":"ab");if(rf){fwrite(px,1,bytesused,rf);fclose(rf);}}
        fprintf(stderr,"DQBUF idx=%u seq=%u bytes=%u varied=%d flags=0x%x\n",dq.index,dq.sequence,bytesused,varied,dq.flags);
        framed++; total+=bytesused;
        struct v4l2_plane rpl[MAX_PLANES]; memcpy(rpl,dpl,sizeof rpl); dq.m.planes=rpl;
        rpl[0].m.fd=ionfds[dq.index];
        dio(fd,VIDIOC_QBUF,&dq,"QBUF(requeue)");
    }
    dio(fd,VIDIOC_STREAMOFF,&bt,"STREAMOFF");
    /* stop sensor */
    struct v4l2_control sc2; sc2.id=V4L2_CID_IS_S_STREAM; sc2.value=IS_DISABLE_STREAM;
    dio(sfd,VIDIOC_S_CTRL,&sc2,"sensor S_CTRL(S_STREAM off)");
    close(fd); close(sfd); close(ionfd);
    printf("{\"tool\":\"nuxel-fimc-full-capture\",\"sensor\":\"%s\",\"cap\":\"%s\",\"frames\":%u,\"bytes\":%u,\"ok\":%s,\"stage\":\"%s\",\"errno\":%d}\n",
        O.sensor_node,O.cap_node,framed,total,framed>0?"true":"false",stage,lasterr);
    return framed>0?0:3;
}
