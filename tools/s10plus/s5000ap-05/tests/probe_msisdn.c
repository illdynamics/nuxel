/* SPDX-License-Identifier: GPL-2.0-only
 * probe_msisdn.c — LIVE, read-only EF_MSISDN probe (operator tool).
 * Never prints the decoded MSISDN; reports only success + digit count.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <poll.h>
#include <time.h>
#include <stdint.h>
#include "ims_msisdn.h"

#define FMT_NODE "/dev/umts_ipc0"
#define MAXF 4096
static int fd = -1;

static uint64_t now_ms(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return (uint64_t)ts.tv_sec*1000u+(uint64_t)ts.tv_nsec/1000000u;}

static int write_iil(uint8_t main,uint8_t sub,uint8_t type,const uint8_t *pl,size_t plen){
    static uint8_t b[MAXF]; size_t flen=7+plen;
    b[0]=(uint8_t)flen;b[1]=(uint8_t)(flen>>8);b[2]=0;b[3]=0;
    b[4]=main;b[5]=sub;b[6]=type; if(plen)memcpy(b+7,pl,plen);
    ssize_t w=write(fd,b,7+plen); if(w!=(ssize_t)(7+plen)){fprintf(stderr,"write: %s\n",strerror(errno));return -1;}
    return 0;
}

/* Drain ALL frames for `ms` ms. Return count and, optionally, collect the
 * first main/sub match into `out`. `gen` collects the latest GEN result. */
static int drain_all(unsigned ms){
    uint64_t end=now_ms()+ms; int hits=0;
    while(now_ms()<end){struct pollfd pf={.fd=fd,.events=POLLIN};
        if(poll(&pf,1,(int)(end-now_ms()))<=0)break;
        static uint8_t b[MAXF]; ssize_t n=read(fd,b,sizeof b); if(n<7)continue;
        uint16_t ll=(uint16_t)b[0]|((uint16_t)b[1]<<8);
        int m=b[4],s=b[5],t=b[6]; size_t pl=(size_t)(ll>=7?ll-7:0);
        hits++;
        /* Redacted: print only main/sub/type/plen and (for GEN) the result code. */
        if (m==128 && pl>=5) {
            uint16_t r=(uint16_t)b[12]|((uint16_t)b[13]<<8);
            printf("  rx GEN main=%d sub=%d type=%d plen=%zu result=0x%04x\n", m,s,t,pl,r);
        } else {
            printf("  rx main=%d sub=%d type=%d plen=%zu\n", m,s,t,pl);
        }
        /* If a main=6 sub=5 data response arrived, save its payload. */
        if (m==6 && s==5 && pl>=3) {
            /* first 8 payload bytes as generic hex is fine (no MSISDN yet) */
            printf("    main6sub5 first=%02x %02x %02x\n", b[7], b[8], b[9]);
        }
    }
    return hits;
}

static int transmit(const uint8_t *apdu, size_t alen){
    uint8_t p[300]; memset(p,0,sizeof p);
    p[0]=0x01; p[1]=0x00; memcpy(p+2,apdu,alen);
    printf("  tx APDU (%zu):", alen); for(size_t i=0;i<alen;i++) printf(" %02x", apdu[i]); printf("\n");
    return write_iil(6,5,2,p,2+alen);
}

int main(void){
    fd=open(FMT_NODE,O_RDWR|O_NONBLOCK|O_CLOEXEC); if(fd<0){perror("open");return 1;}
    const uint8_t openp[]={0x01,0x00,0x70,0x00};
    if(write_iil(5,6,2,openp,sizeof openp)){close(fd);return 1;}
    printf("open -> "); drain_all(2000);

    /* Try both DF_GSM (7F20) and DF_TELECOM (7F10) paths to EF_MSISDN 6F40. */
    const uint8_t sel_mf[]    = {0x00,0xA4,0x00,0x00,0x02,0x3F,0x00};
    const uint8_t sel_gsm[]   = {0x00,0xA4,0x00,0x00,0x02,0x7F,0x20};
    const uint8_t sel_tele[]  = {0x00,0xA4,0x00,0x00,0x02,0x7F,0x10};
    const uint8_t sel_msisdn[]= {0x00,0xA4,0x00,0x00,0x02,0x6F,0x40};
    const uint8_t read_all[]  = {0x00,0xB0,0x00,0x00,0x20};

    transmit(sel_mf,sizeof sel_mf); drain_all(800);
    transmit(sel_gsm,sizeof sel_gsm); drain_all(800);
    transmit(sel_msisdn,sizeof sel_msisdn); drain_all(800);
    transmit(read_all,sizeof read_all); drain_all(1200);

    printf("trying DF_TELECOM path...\n");
    transmit(sel_mf,sizeof sel_mf); drain_all(500);
    transmit(sel_tele,sizeof sel_tele); drain_all(800);
    transmit(sel_msisdn,sizeof sel_msisdn); drain_all(800);
    transmit(read_all,sizeof read_all); drain_all(1200);

    close(fd);
    return 0;
}
