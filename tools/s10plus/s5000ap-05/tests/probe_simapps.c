/* SPDX-License-Identifier: GPL-2.0-only
 * probe_simapps.c — read-only SIM application inventory via SEC_SIMAPPS_INFO
 * (main=5 sub=15). Issues the exact 7-byte vendor request over FMT and prints
 * the response for USIM/ISIM classification. No writes to the SIM; no APDU. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <poll.h>
#include <time.h>
#include <stdint.h>
#define FMT_NODE "/dev/umts_ipc0"
static uint64_t now_ms(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return (uint64_t)ts.tv_sec*1000u+ts.tv_nsec/1000000u;}
static int fd;
static int wr(uint8_t main,uint8_t sub,uint8_t type,const uint8_t*pl,size_t plen){
  uint8_t b[64]; size_t fl=7+plen; b[0]=(uint8_t)fl;b[1]=(uint8_t)(fl>>8);b[2]=0;b[3]=0;b[4]=main;b[5]=sub;b[6]=type;
  if(plen)memcpy(b+7,pl,plen);
  ssize_t w=write(fd,b,fl);
  printf("tx %u/%u/%u plen=%zu -> %zd %s\n",main,sub,type,plen,w,w<0?strerror(errno):"");
  return w==(ssize_t)fl?0:-1;
}
int main(void){
  fd=open(FMT_NODE,O_RDWR|O_NONBLOCK|O_CLOEXEC);
  if(fd<0){perror("open");return 2;}
  /* drain any pending */
  uint8_t b[2048]; while(read(fd,b,sizeof b)>0){}
  /* SEC_SIMAPPS_INFO: IpcTxGetSimAppsInfo @0x341000 frame [07 00 00 00 05 0f 02] */
  uint8_t req[]={7,0,0,0,5,15,2};
  if(write(fd,req,sizeof req)!=(ssize_t)sizeof req){perror("write");return 3;}
  printf("tx SEC_SIMAPPS_INFO 7-byte\n");
  uint64_t end=now_ms()+3000;
  while(now_ms()<end){
    struct pollfd pf={.fd=fd,.events=POLLIN};
    if(poll(&pf,1,(int)(end-now_ms()))<=0)break;
    ssize_t n=read(fd,b,sizeof b); if(n<7)continue;
    uint16_t ll=(uint16_t)b[0]|((uint16_t)b[1]<<8);
    if((size_t)n<(size_t)ll)continue;
    printf("rx main=%u sub=%u type=%u plen=%u:",b[4],b[5],b[6],ll>=7?ll-7:0);
    for(size_t i=7;i<(size_t)ll && i<48;i++)printf(" %02x",b[i]);
    printf("\n");
  }
  close(fd);return 0;
}
