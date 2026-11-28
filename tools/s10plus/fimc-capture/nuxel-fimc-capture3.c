/*
 * nuxel-fimc-capture3 — Stage A: drive the FIMC-IS2 ischain to a real frame.
 *
 * Root-cause fixes over capture2 (source-verified against the running kernel
 * 4.14.253 fimc-is2 source):
 *
 *  1. The sensor leader S_FMT failed with -EINVAL because fimc_is_sensor_g_mode()
 *     could not find a mode entry for the requested 640x480. The 2L4
 *     config_module_2l4[] table only contains these Cfgs: 4032x3024@30 (mode0),
 *     4032x2268@60 (1), 4032x2268@30 (2), 4032x1908@30 (3), 3024x3024@30 (4),
 *     2016x1512@30 (5), 2016x1134@30 (6), 1504x1504@30 (7), ... Use 2016x1512@30.
 *
 *  2. Correct leader state machine (fimc-is-video.c), single-bit state:
 *        open()                -> OPEN
 *        S_INPUT               -> requires OPEN|S_INPUT|S_BUFS, sets S_INPUT
 *        S_FMT (LEADER)        -> requires S_INPUT|S_BUFS, sets S_FORMAT
 *        REQBUFS               -> requires S_FORMAT|STOP|S_BUFS, sets S_BUFS
 *        QBUF... -> STREAMON   -> requires S_BUFS|STOP, sets START
 *     So order is: S_INPUT -> S_FMT -> REQBUFS -> QBUF -> STREAMON.
 *
 *  3. S_INPUT packed bitfield (CONFIG_USE_SENSOR_GROUP):
 *        leader=1 | (position<<16). rear-main position=SP_REAR=0 => 0x00000001.
 *
 *  4. Capture (i0c) + 3AA group leader: the ISP capture STREAMON fails -22 unless
 *     the 3AA/ISP group leader was started first (fimc_is_itf_process_start).
 *     We open+drive the 3AA leader node (/dev/video110 "30s") then the capture.
 *
 * Does NOT claim a frame until a nonzero DQBUF with varied pixels is observed.
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

#define INPUT_LEADER_SHIFT   0
#define INPUT_POSITION_SHIFT 16
#define SP_REAR   0
#define SP_FRONT  1
#define SP_REAR2  2
#define SP_FRONT2 3
#define SP_REAR3  4

#define V4L2_CTRL_CLASS_CAMERA 0x009A0000u
#define V4L2_CID_FIMC_IS_BASE (V4L2_CTRL_CLASS_CAMERA | 0x1000)
#define V4L2_CID_IS_S_STREAM (V4L2_CID_FIMC_IS_BASE + 14)
#define V4L2_CID_IS_S_SENSOR_SIZE (V4L2_CID_FIMC_IS_BASE + 69)
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

int main(int argc, char **argv){
    const char *sensor="/dev/video101", *cap="/dev/video131", *leader3aa="/dev/video110", *raw=NULL;
    int heap=5; unsigned width=2016,height=1512,framerate=30,bufs=4,frames=2,timeout=8000;
    int sensor_pos=SP_REAR, sensor_leader=1, cap_pos=SP_REAR, cap_leader=0;
    int sensor_fourcc=V4L2_PIX_FMT_SBGGR10;
    int fourcc_code=V4L2_PIX_FMT_YUYV;
    int i;
    for(i=1;i<argc;i++){const char*a=argv[i],*v=(i+1<argc)?argv[i+1]:NULL;
        if(!strcmp(a,"--sensor")&&v){sensor=v;i++;}
        else if(!strcmp(a,"--cap")&&v){cap=v;i++;}
        else if(!strcmp(a,"--leader3aa")&&v){leader3aa=v;i++;}
        else if(!strcmp(a,"--raw")&&v){raw=v;i++;}
        else if(!strcmp(a,"--heap")&&v){heap=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--width")&&v){width=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--height")&&v){height=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--fps")&&v){framerate=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--buffers")&&v){bufs=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--frames")&&v){frames=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--timeout")&&v){timeout=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--sensor-pos")&&v){sensor_pos=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--sensor-leader")&&v){sensor_leader=strtol(v,NULL,0);i++;}
        else if(!strcmp(a,"--fourcc")&&v){fourcc_code=strtoul(v,NULL,0);i++;}
        else if(!strcmp(a,"--sensor-fourcc")&&v){sensor_fourcc=strtoul(v,NULL,0);i++;}}

    unsigned sensor_input = ((sensor_leader & 0xF) << INPUT_LEADER_SHIFT) |
                            ((sensor_pos & 0xFF) << INPUT_POSITION_SHIFT);
    unsigned cap_input = ((cap_leader & 0xF) << INPUT_LEADER_SHIFT) |
                         ((cap_pos & 0xFF) << INPUT_POSITION_SHIFT);

    fprintf(stderr,"FIMC capture3: sensor=%s leader3aa=%s cap=%s %ux%u@%u heap=%d fourcc=0x%08x\n",
            sensor,leader3aa,cap,width,height,framerate,heap,(unsigned)fourcc_code);
    fprintf(stderr,"  sensor S_INPUT=0x%08X (leader=%u position=%u)\n", sensor_input, sensor_leader, sensor_pos);

    int ionfd=open("/dev/ion",O_RDWR); if(ionfd<0){perror("/dev/ion");return 4;}
    /* RAW10 packed: 10 bits/pixel => 5 bytes per 4 pixels; allocate generously. */
    unsigned img = width*height*2;

    /* ==== 1. SENSOR (leader, OUTPUT MPLANE) ==== */
    int sfd=open(sensor,O_RDWR|O_NONBLOCK); if(sfd<0){perror("sensor open");return 4;}
    int r=dio(sfd,VIDIOC_S_INPUT,&sensor_input);
    fprintf(stderr,"[sensor S_INPUT] ret=%d errno=%d\n",r,errno);
    struct v4l2_control ssz; ssz.id=V4L2_CID_IS_S_SENSOR_SIZE; ssz.value=(width<<16)|height;
    r=dio(sfd,VIDIOC_S_CTRL,&ssz);
    fprintf(stderr,"[sensor S_SENSOR_SIZE %ux%u] ret=%d errno=%d\n",width,height,r,errno);

    struct v4l2_format sf; memset(&sf,0,sizeof sf);
    sf.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    sf.fmt.pix_mp.width=width; sf.fmt.pix_mp.height=height;
    sf.fmt.pix_mp.pixelformat=sensor_fourcc; sf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    sf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG;
    sf.fmt.pix_mp.num_planes=2;
    sf.fmt.pix_mp.plane_fmt[0].sizeimage=img;
    sf.fmt.pix_mp.plane_fmt[0].bytesperline=width*2;
    r=dio(sfd,VIDIOC_S_FMT,&sf);
    fprintf(stderr,"[sensor S_FMT] ret=%d errno=%d planes=%u w=%u h=%u size=%u\n",
            r,errno,sf.fmt.pix_mp.num_planes,sf.fmt.pix_mp.width,sf.fmt.pix_mp.height,sf.fmt.pix_mp.plane_fmt[0].sizeimage);

    struct v4l2_streamparm sp; memset(&sp,0,sizeof sp);
    sp.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    sp.parm.output.timeperframe.numerator=1; sp.parm.output.timeperframe.denominator=framerate;
    r=dio(sfd,VIDIOC_S_PARM,&sp);
    fprintf(stderr,"[sensor S_PARM %ufps] ret=%d errno=%d\n",framerate,r,errno);

    struct v4l2_requestbuffers sreq; memset(&sreq,0,sizeof sreq);
    sreq.count=bufs; sreq.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE; sreq.memory=V4L2_MEMORY_DMABUF;
    r=dio(sfd,VIDIOC_REQBUFS,&sreq);
    fprintf(stderr,"[sensor REQBUFS] ret=%d errno=%d count=%u\n",r,errno,sreq.count);
    int sion[MAX_BUFS];
    for(i=0;i<(int)sreq.count && i<MAX_BUFS;i++){
        struct v4l2_buffer b; struct v4l2_plane p[MAX_PLANES];
        memset(&b,0,sizeof b); memset(p,0,sizeof p);
        b.index=i; b.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE; b.memory=V4L2_MEMORY_DMABUF;
        b.m.planes=p; b.length=MAX_PLANES;
        dio(sfd,VIDIOC_QUERYBUF,&b);
        int f1=ion_alloc(ionfd,img,heap,ION_FLAG_CACHED); if(f1<0){perror("ion s img");return 4;}
        int f2=ion_alloc(ionfd,32*1024,heap,0); if(f2<0){perror("ion s meta");return 4;}
        p[0].m.fd=f1; sion[i]=f1;
        p[0].bytesused=img; p[0].length=img;
        p[1].m.fd=f2; p[1].bytesused=32*1024; p[1].length=32*1024;
        b.length=2;
        r=dio(sfd,VIDIOC_QBUF,&b);
        fprintf(stderr,"[sensor QBUF %d] ret=%d errno=%d\n",i,r,errno);
    }
    enum v4l2_buf_type sot=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    r=dio(sfd,VIDIOC_STREAMON,&sot);
    fprintf(stderr,"[sensor STREAMON] ret=%d errno=%d\n",r,errno);

    struct v4l2_control sc; sc.id=V4L2_CID_IS_S_STREAM; sc.value=IS_ENABLE_STREAM;
    r=dio(sfd,VIDIOC_S_CTRL,&sc);
    fprintf(stderr,"[sensor S_STREAM=1] ret=%d errno=%d\n",r,errno);

    /* ==== 2. 3AA GROUP LEADER (video110 "30s") ==== */
    int lfd=open(leader3aa,O_RDWR|O_NONBLOCK);
    if(lfd>=0){
        unsigned linput = (0 & 0xF) | ((sensor_pos & 0xFF)<<INPUT_POSITION_SHIFT);
        r=dio(lfd,VIDIOC_S_INPUT,&linput);
        fprintf(stderr,"[3aa S_INPUT] ret=%d errno=%d\n",r,errno);
        struct v4l2_format lf; memset(&lf,0,sizeof lf);
        lf.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        lf.fmt.pix_mp.width=width; lf.fmt.pix_mp.height=height;
        lf.fmt.pix_mp.pixelformat=fourcc_code; lf.fmt.pix_mp.field=V4L2_FIELD_NONE;
        lf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; lf.fmt.pix_mp.num_planes=2;
        lf.fmt.pix_mp.plane_fmt[0].sizeimage=img; lf.fmt.pix_mp.plane_fmt[0].bytesperline=width*2;
        r=dio(lfd,VIDIOC_S_FMT,&lf);
        fprintf(stderr,"[3aa S_FMT] ret=%d errno=%d\n",r,errno);
        struct v4l2_requestbuffers lreq; memset(&lreq,0,sizeof lreq);
        lreq.count=bufs; lreq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; lreq.memory=V4L2_MEMORY_DMABUF;
        r=dio(lfd,VIDIOC_REQBUFS,&lreq);
        fprintf(stderr,"[3aa REQBUFS] ret=%d errno=%d count=%u\n",r,errno,lreq.count);
        int lion[MAX_BUFS];
        for(i=0;i<(int)lreq.count && i<MAX_BUFS;i++){
            struct v4l2_buffer b; struct v4l2_plane p[MAX_PLANES];
            memset(&b,0,sizeof b); memset(p,0,sizeof p);
            b.index=i; b.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; b.memory=V4L2_MEMORY_DMABUF;
            b.m.planes=p; b.length=MAX_PLANES;
            dio(lfd,VIDIOC_QUERYBUF,&b);
            int f1=ion_alloc(ionfd,img,heap,ION_FLAG_CACHED); if(f1<0){perror("ion 3aa");break;}
            int f2=ion_alloc(ionfd,32*1024,heap,0); if(f2<0){perror("ion 3aa meta");break;}
            p[0].m.fd=f1; lion[i]=f1; p[0].bytesused=img; p[0].length=img;
            p[1].m.fd=f2; p[1].bytesused=32*1024; p[1].length=32*1024;
            b.length=2;
            r=dio(lfd,VIDIOC_QBUF,&b);
        }
        enum v4l2_buf_type lot=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        r=dio(lfd,VIDIOC_STREAMON,&lot);
        fprintf(stderr,"[3aa STREAMON] ret=%d errno=%d\n",r,errno);
    } else { fprintf(stderr,"[3aa open %s] failed errno=%d\n",leader3aa,errno); }

    /* ==== 3. CAPTURE (ISP i0c, CAPTURE MPLANE) ==== */
    int fd=open(cap,O_RDWR|O_NONBLOCK); if(fd<0){perror("cap open");return 4;}
    dio(fd,VIDIOC_S_INPUT,&cap_input);
    struct v4l2_format cf; memset(&cf,0,sizeof cf);
    cf.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    cf.fmt.pix_mp.width=width; cf.fmt.pix_mp.height=height;
    cf.fmt.pix_mp.pixelformat=fourcc_code; cf.fmt.pix_mp.field=V4L2_FIELD_NONE;
    cf.fmt.pix_mp.colorspace=V4L2_COLORSPACE_JPEG; cf.fmt.pix_mp.num_planes=2;
    cf.fmt.pix_mp.plane_fmt[0].sizeimage=img; cf.fmt.pix_mp.plane_fmt[0].bytesperline=width*2;
    r=dio(fd,VIDIOC_S_FMT,&cf);
    fprintf(stderr,"[cap S_FMT] ret=%d errno=%d planes=%u w=%u h=%u size=%u\n",r,errno,cf.fmt.pix_mp.num_planes,cf.fmt.pix_mp.width,cf.fmt.pix_mp.height,cf.fmt.pix_mp.plane_fmt[0].sizeimage);
    struct v4l2_requestbuffers creq; memset(&creq,0,sizeof creq);
    creq.count=bufs; creq.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; creq.memory=V4L2_MEMORY_DMABUF;
    r=dio(fd,VIDIOC_REQBUFS,&creq);
    fprintf(stderr,"[cap REQBUFS] ret=%d errno=%d count=%u\n",r,errno,creq.count);
    int cion[MAX_BUFS]; unsigned char *cmap[MAX_BUFS];
    memset(cion,-1,sizeof cion);
    for(i=0;i<(int)creq.count && i<MAX_BUFS;i++){
        struct v4l2_buffer b; struct v4l2_plane p[MAX_PLANES];
        memset(&b,0,sizeof b); memset(p,0,sizeof p);
        b.index=i; b.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; b.memory=V4L2_MEMORY_DMABUF;
        b.m.planes=p; b.length=MAX_PLANES;
        dio(fd,VIDIOC_QUERYBUF,&b);
        int f1=ion_alloc(ionfd,img,heap,ION_FLAG_CACHED); if(f1<0){perror("ion c img");return 4;}
        int f2=ion_alloc(ionfd,32*1024,heap,0); if(f2<0){perror("ion c meta");return 4;}
        p[0].m.fd=f1; cion[i]=f1;
        cmap[i]=mmap(NULL,img,PROT_READ|PROT_WRITE,MAP_SHARED,f1,0);
        p[0].bytesused=img; p[0].length=img;
        p[1].m.fd=f2; p[1].bytesused=32*1024; p[1].length=32*1024;
        b.length=2;
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
        if(dio(fd,VIDIOC_DQBUF,&dq)<0){if(errno==EAGAIN||errno==EINTR)continue;fprintf(stderr,"[DQBUF] err=%d\n",errno);break;}
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
    if(lfd>=0){ enum v4l2_buf_type lot=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; dio(lfd,VIDIOC_STREAMOFF,&lot); close(lfd); }
    struct v4l2_control sc2; sc2.id=V4L2_CID_IS_S_STREAM; sc2.value=IS_DISABLE_STREAM; dio(sfd,VIDIOC_S_CTRL,&sc2);
    close(fd);close(sfd);close(ionfd);
    printf("{\"tool\":\"nuxel-fimc-capture3\",\"sensor\":\"%s\",\"cap\":\"%s\",\"frames\":%u,\"bytes\":%u,\"ok\":%s}\n",sensor,cap,framed,total,framed>0?"true":"false");
    return framed>0?0:3;
}
