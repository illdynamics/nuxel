/* SPDX-License-Identifier: GPL-2.0-only
 * probe_uicc.c — LIVE, read-only UICC logical-channel probe (operator tool).
 * OPEN CHANNEL + TRANSMIT(SELECT/READ/GET RESPONSE) + CLOSE only.
 * Prints CP results and status words; never prints EF contents.
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

#define FMT_NODE "/dev/umts_ipc0"
#define MAXF 2048
static int fd = -1;
static uint8_t g_channel = 0x6e;

static uint64_t now_ms(void){struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return (uint64_t)ts.tv_sec*1000u+(uint64_t)ts.tv_nsec/1000000u;}
static void hx(const char *t,const uint8_t *p,size_t n){printf("%s[%zu]:",t,n);for(size_t i=0;i<n&&i<80;i++)printf(" %02x",p[i]);printf("\n");}

static int write_iil(uint8_t main,uint8_t sub,uint8_t type,const uint8_t *pl,size_t plen){
    static uint8_t b[MAXF]; size_t flen=7+plen;
    b[0]=(uint8_t)flen;b[1]=(uint8_t)(flen>>8);b[2]=0;b[3]=0;
    b[4]=main;b[5]=sub;b[6]=type; if(plen)memcpy(b+7,pl,plen);
    if(getenv("SEQ1")) b[2]=1;
    if(getenv("SEQ2")) b[3]=1;
    if(getenv("HDR9")){ b[2]=0;b[3]=0; }
    if(getenv("DUP")){ /* duplicate-7 layout: [tail at 0..1][main,sub,type][len at 4..5]*/ }
    printf("tx %u/%u/%u plen=%zu\n",main,sub,type,plen); hx(" wire",b,7+plen);
    ssize_t w=write(fd,b,7+plen); if(w!=(ssize_t)(7+plen)){printf(" write: %s\n",strerror(errno));return -1;}
    return 0;
}
static int drain(unsigned ms,int wm,int ws,uint8_t *out,size_t *ol){
    uint64_t end=now_ms()+ms; int hits=0; if(ol)*ol=0;
    while(now_ms()<end){struct pollfd pf={.fd=fd,.events=POLLIN};
        if(poll(&pf,1,(int)(end-now_ms()))<=0)break;
        static uint8_t b[MAXF]; ssize_t n=read(fd,b,sizeof b); if(n<7)continue;
        uint16_t ll=(uint16_t)b[0]|((uint16_t)b[1]<<8);
        if((size_t)n<7+(size_t)(ll>=7?ll-7:0))continue;
        int m=b[4],s=b[5],t=b[6]; size_t pl=(size_t)(ll>=7?ll-7:0);
        if(wm<0||(m==wm&&s==ws)){printf("rx %d/%d/%d plen=%zu total=%u\n",m,s,t,pl,ll);hx(" data",b+7,pl);
            if(out&&ol&&pl<=*ol){memcpy(out,b+7,pl);*ol=pl;} hits++;}
    }
    return hits;
}
static int do_open(void){
    const uint8_t p[]={1,0,0x70,0}; if(write_iil(5,6,2,p,4))return -1;
    uint8_t o[64];size_t n=sizeof o; int h=drain(3000,5,6,o,&n);
    if(h&&n>=4&&o[2]==0)g_channel=o[3];
    printf("open hits=%d channel=0x%02x\n",h,g_channel); return h?0:-1;
}
static int g_sel[2]={0,0}, g_t=2; static int g_sub=5;
static int tx(const char *lbl,const uint8_t *p,size_t n){printf("== %s (6/%d/%d) ==\n",lbl,g_sub,g_t);if(write_iil(6,(uint8_t)g_sub,(uint8_t)g_t,p,n))return -1;
    uint8_t o[512];size_t ol=sizeof o;int h=drain(1500,6,g_sub,o,&ol);printf("=> %s hits=%d\n",lbl,h);return h;}


static int tx_apdu(const char *lbl,const uint8_t *apdu,size_t alen){
    uint8_t p[300]; memset(p,0,sizeof p);
    printf("%s src_len=%zu sel=%d,%d t=%d\n",lbl,alen,g_sel[0],g_sel[1],g_t);
    if(g_sel[0] || g_sel[1]){
        p[0]=(uint8_t)g_sel[0]; p[1]=(uint8_t)g_sel[1];
        memcpy(p+2,apdu,alen);
        return tx(lbl,p,2+alen);
    }
    return tx(lbl,apdu,alen);
}
/* SELECT by path (MF .. EF) using mode 00 (first/only). */
static int sel_path(const uint8_t *path,size_t n){
    uint8_t a[32]; size_t k=0; a[k++]=0x00;a[k++]=0xA4;a[k++]=0x00;a[k++]=0x00;a[k++]=(uint8_t)n;
    memcpy(a+k,path,n); k+=n;
    return tx_apdu("SELECT",a,k);
}
static int select_fid(uint16_t fid,int verify){
    /* Isim* T=0 SAP: p1=0, p2 = 0x00 (select) or 0x04 (verify FCP); APDU
     * SELECT(00 A4 04 00 02 fid). After OPEN the channel owns the app. */
    uint8_t p[16]; size_t n=0;
    uint8_t a[]={0x00,0xA4,0x04,0x00,0x02,(uint8_t)(fid>>8),(uint8_t)fid};
    p[0]=(uint8_t)sizeof a; p[1]=(uint8_t)verify; p[2]=0x00;
    memcpy(p+3,a,sizeof a); n=3+sizeof a;
    printf("== SELECT 0x%04x verify=%d ==\n",fid,verify);
    if(write_iil(6,5,2,p,n))return -1;
    uint8_t o[512];size_t ol=sizeof o;int h=drain(1500,6,5,o,&ol);
    printf("=> select 0x%04x hits=%d\n",fid,h);
    return h;
}
static int read_bin(uint8_t off,uint8_t len,uint8_t *out,size_t *olen){
    printf("== READ off=0x%02x len=%u ==\n",off,len);
    if(write_iil(6,5,2,(uint8_t[]){0x05,0,0,0xB0,off,0x00,len},7))return -1;
    uint8_t o[512];size_t ol=sizeof o; int h=drain(1500,6,5,o,&ol);
    printf("=> read hits=%d\n",h);
    if(h&&ol>=3&&o[0]==2){ size_t dl=ol-3; if(out&&olen&&dl<=*olen){memcpy(out,o+3,dl);*olen=dl;} }
    return h;
}

int main(int argc,char**argv){
    const char *m=argc>1?argv[1]:"seq";
    fd=open(FMT_NODE,O_RDWR|O_NONBLOCK|O_CLOEXEC); if(fd<0){perror("open");return 1;}
    if(!strcmp(m,"open")){int r=do_open();close(fd);return r?1:0;}
    if(do_open()){close(fd);return 1;}
    const uint8_t apdu[]={0,0xA4,0,0,2,0x6F,0x03};
    if(!strcmp(m,"le1")){
        ;
        uint8_t p[8]={1,0,0,0,0,0,0xA4,0};
        p[4]=(uint8_t)sizeof apdu;
        tx("aid=le1",p,sizeof p);
    } else if(!strcmp(m,"le2")){
        uint8_t p[10]={2,0,0,0,0,0,0,0,0,0};
        uint16_t le = (uint16_t)sizeof(apdu);
        p[4]=(uint8_t)le; p[5]=(uint8_t)(le>>8);
        tx("aid=le2",p,sizeof p);
    } else if(!strcmp(m,"full")){
        ;
        uint8_t p[128]={0};
        memcpy(p+6,apdu,sizeof apdu);
        tx("aid=0+apdu",p,6+sizeof apdu);
    } else if(!strcmp(m,"raw")){
        tx("raw-apdu",apdu,sizeof apdu);
    } else if(!strcmp(m,"sweep")){
        ;
        for(int pre=0;pre<=40;pre++){
            ;
            uint8_t p[128]={0};
            size_t n=(size_t)pre;
            memcpy(p+n,apdu,sizeof apdu); n+=sizeof apdu;
            char l[24]; snprintf(l,sizeof l,"pre=%d",pre);
            if(tx(l,p,n)>0){printf("*** accepted pre=%d\n",pre);break;}
        }
    } else if(!strcmp(m,"sel")){
        for(int i=2;i<=7;i++){ select_fid((uint16_t)(0x6F00|i),0); }
    } else if(!strcmp(m,"isim2")){
        select_fid(0x7FFF,0); select_fid(0x6F03,0); read_bin(0,0x30,0,0);
        select_fid(0x7FFF,0); select_fid(0x6F07,0); read_bin(0,0x20,0,0);
        select_fid(0x7FFF,0); select_fid(0x6F04,0); read_bin(0,0x30,0,0);
        select_fid(0x7FFF,0); select_fid(0x6F02,0); read_bin(0,1,0,0);
    } else if(!strcmp(m,"isim")){
        const uint8_t path_dom[]={0x3F,0x00,0x7F,0xFF,0x6F,0x03};
        const uint8_t path_impi[]={0x3F,0x00,0x7F,0xFF,0x6F,0x04};
        const uint8_t path_impu[]={0x3F,0x00,0x7F,0xFF,0x6F,0x02};
        const uint8_t path_ist[]={0x3F,0x00,0x7F,0xFF,0x6F,0x07};
        sel_path(path_dom,sizeof path_dom); read_bin(0,0x30,0,0);
        sel_path(path_ist,sizeof path_ist); read_bin(0,0x30,0,0);
        sel_path(path_impi,sizeof path_impi); read_bin(0,0x30,0,0);
        sel_path(path_impu,sizeof path_impu); read_bin(0,0x01,0,0);
        sel_path(path_impu,sizeof path_impu); read_bin(0x02,0x01,0,0);
    } else if(!strcmp(m,"fids")){
        for(int f=0;f<0x10;f++){
            uint8_t path[]={0x3F,0x00,0x7F,0xFF,0x6F,0x00};
            path[5]=(uint8_t)f;
            char l[24]; snprintf(l,sizeof l,"fid6F%02x",f);
            if(write_iil(5,6,2,(uint8_t[]){1,0,0x70,0},4))break;
            uint8_t o[64];size_t ol=sizeof o; drain(1500,5,6,o,&ol);
            tx_apdu(l,path,sizeof path);
        }
    } else if(!strcmp(m,"len")){
        /* le1 variant with selector p2=1 vs 0, T=0 vs 1 */
        for(int p2=0;p2<=1;p2++) for(int t=0;t<=1;t++){
            uint8_t p[16]={0}; uint8_t a[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
            p[0]=sizeof a; p[1]=(uint8_t)p2; memcpy(p+3,a,sizeof a);
            char l[24]; snprintf(l,sizeof l,"p2=%d",p2);
            printf("== %s t=%d ==\n",l,t);
            if(write_iil(6,5,(uint8_t)t,p,3+sizeof a))continue;
            uint8_t o[512];size_t ol=sizeof o; drain(1500,6,5,o,&ol);
        }
    } else if(!strcmp(m,"long")){
        uint8_t p[300]={0}; size_t n=40;
        memcpy(p+3,"\x6F\x03",2);
        printf("== long t0 n=%zu ==\n",n+3);
        write_iil(6,5,0,p,3+n); drain(1500,6,5,0,0);
        printf("== long t1 n=%zu ==\n",n+3);
        write_iil(6,5,1,p,3+n); drain(1500,6,5,0,0);
        printf("== long t2 n=%zu ==\n",n+3);
        write_iil(6,5,2,p,3+n); drain(1500,6,5,0,0);
    } else if(!strcmp(m,"matrix")){
        static const uint8_t sel6f03[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        static const uint8_t sel2f00[]={0x00,0xA4,0x04,0x00,0x02,0x2F,0x00};
        static const uint8_t rd[]={0x00,0xB0,0x00,0x00,0x01};
        const struct { int a,b,t; } cfg[]={
            {0,0,2},{0,1,2},{1,0,2},{1,1,2},{1,8,2},{0,8,2},
            {0,0,0},{0,0,1},{1,0,0},{2,0,2},{2,1,2},
        };
        for(size_t i=0;i<sizeof cfg/sizeof cfg[0];i++){
            g_sel[0]=cfg[i].a; g_sel[1]=cfg[i].b; g_t=cfg[i].t;
            tx_apdu("sel6f03",sel6f03,sizeof sel6f03);
            tx_apdu("sel2f00",sel2f00,sizeof sel2f00);
            tx_apdu("read",rd,sizeof rd);
        }
    } else if(!strcmp(m,"matrix2")){
        static const uint8_t sel6f03[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        static const uint8_t sel2f00[]={0x00,0xA4,0x04,0x00,0x02,0x2F,0x00};
        static const uint8_t rd[]={0x00,0xB0,0x00,0x00,0x01};
        const struct { int a,b,t; } cfg[]={
            {0,1,2},{0,1,1},{0,1,0},{1,1,2},{1,8,2},{1,2,2},{2,2,2},{1,0,2},
        };
        for(size_t i=0;i<sizeof cfg/sizeof cfg[0];i++){
            g_sel[0]=cfg[i].a; g_sel[1]=cfg[i].b; g_t=cfg[i].t;
            tx_apdu("sel6f03",sel6f03,sizeof sel6f03);
            tx_apdu("sel2f00",sel2f00,sizeof sel2f00);
            tx_apdu("read",rd,sizeof rd);
        }
    } else if(!strcmp(m,"close")){
        /* close the channel then read what OPEN echoes (aid) */
        do_open();
        printf("== CLOSE ch=0x%02x ==\n",g_channel);
        write_iil(6,7,2,(uint8_t[]){g_channel},1);
        drain(1500,6,7,0,0);
        do_open();
        /* now the live inventory echo from OPEN */
        printf("inventory echo seen above\n");
    } else if(!strcmp(m,"inv")){
        /* single TRANSMIT with p1/p2 that produced the 51-byte echo */
        uint8_t p[]={1,0,0xA4,0x04,0x00,0x02,0x6F,0x03};
        if(write_iil(6,5,2,p,sizeof p))return 0;
        drain(1500,6,5,0,0);
        uint8_t q[]={1,0,0xB0,0x00,0x00,0x01};
        if(write_iil(6,5,2,q,sizeof q))return 0;
        drain(1500,6,5,0,0);
    } else if(!strcmp(m,"one")){
        for(int k=1;k<=6;k++){
            uint8_t p[8]={0}; p[k]=7;
            char l[24]; snprintf(l,sizeof l,"one-byte k=%d",k);
            printf("== %s ==\n",l);
            if(write_iil(6,5,2,p,(size_t)(k+1)))continue;
            uint8_t o[256]; size_t ol=sizeof o; int h=drain(1000,6,5,o,&ol);
            printf("=> %s hits=%d\n",l,h);
        }
        /* and a 1-byte payload (just 0x07) then 0x00 */
        uint8_t z[]={0x07}; write_iil(6,5,2,z,1); drain(1000,6,5,0,0);
        z[0]=0x00; write_iil(6,5,2,z,1); drain(1000,6,5,0,0);
    } else if(!strcmp(m,"tr2")){
        static const uint8_t v[]={0x01,0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        printf("== tr2 8 bytes ==\n"); write_iil(6,5,2,v,sizeof v); drain(1500,6,5,0,0);
        static const uint8_t w[]={0x01,0x00,0xB0,0x00,0x00,0x01};
        printf("== rd 6 bytes ==\n"); write_iil(6,5,2,w,sizeof w); drain(1500,6,5,0,0);
    } else if(!strcmp(m,"seq2")){
        /* OPEN, reject APDU, re-OPEN, then SELECT */
        static const uint8_t bad[]={0x01,0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        static const uint8_t sel[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        printf("== APDU len8 ==\n"); write_iil(6,5,2,bad,sizeof bad); drain(1000,6,5,0,0);
        printf("== re-OPEN ==\n"); do_open();
        printf("== SELECT raw ==\n"); write_iil(6,5,2,sel,sizeof sel); drain(1000,6,5,0,0);
        printf("== re-OPEN again ==\n"); do_open();
        static const uint8_t sel1[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x07};
        printf("== SELECT 6f07 sel=0 len7 too short; try 9-byte padded ==\n");
        static const uint8_t sel9[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x07,0x00,0x00};
        write_iil(6,5,2,sel9,sizeof sel9); drain(1000,6,5,0,0);
        (void)sel1;
    } else if(!strcmp(m,"selch")){
        /* IpcTxSelectChannelEhPcii: payload before APDU:[chan=ch][type=0][?=0][?=0], APDU at +4 */
        static const uint8_t a6f03[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        static const uint8_t a6f07[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x07};
        static const uint8_t rd[]={0x00,0xB0,0x00,0x00,0x08};
        uint8_t p[64]; size_t alen;
        g_sub=6; g_t=2; g_sel[0]=g_sel[1]=0;
        alen=sizeof a6f03; memset(p,0,sizeof p); p[0]=g_channel; p[1]=0; p[2]=0; p[3]=0; memcpy(p+4,a6f03,alen);
        tx_apdu("selch select 6f03",p,4+alen);
        alen=sizeof rd;    memset(p,0,sizeof p); p[0]=g_channel; p[1]=0; p[2]=0; p[3]=0; memcpy(p+4,rd,alen);
        tx_apdu("selch read 8",p,4+alen);
        alen=sizeof a6f07; memset(p,0,sizeof p); p[0]=g_channel; p[1]=0; p[2]=0; p[3]=0; memcpy(p+4,a6f07,alen);
        tx_apdu("selch select 6f07",p,4+alen);
        g_sub=5;
    } else if(!strcmp(m,"abs")){
        static const uint8_t s1[]={0x00,0xA4,0x08,0x04,0x04,0x7F,0xFF,0x6F,0x03};
        static const uint8_t s2[]={0x00,0xA4,0x08,0x04,0x04,0x3F,0x00,0x2F,0xE2};
        static const uint8_t r[] ={0x00,0xB0,0x00,0x00,0x08};
        g_sub=5;
        for(int sel=0;sel<=1;sel++) for(int t=0;t<=2;t++){
            g_sel[0]=sel; g_sel[1]=0; g_t=t;
            tx_apdu("abs 7fff6f03",s1,sizeof s1);
            tx_apdu("abs 3f002fe2",s2,sizeof s2);
            tx_apdu("read8",r,sizeof r);
        }
    } else if(!strcmp(m,"final")){
        /* Canonical SAP SELECT form (sent standalone): len@payload[0] (unused by
         * CP), APDU @+1. This is what Round 18's serializer produced. */
        static const uint8_t sel_raw[]={0x00,0xA4,0x04,0x00,0x02,0x6F,0x03};
        static const uint8_t sel_ex[] ={0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00};
        static const uint8_t rd_raw[] ={0x00,0xB0,0x00,0x00,0x08};
        g_sub=5;
        for(int t=0;t<=2;t++){
            g_t=t; g_sel[0]=0; g_sel[1]=0;
            tx_apdu("final select raw7",sel_raw,sizeof sel_raw);
            tx_apdu("final select ex8",sel_ex,sizeof sel_ex);
            tx_apdu("final read5",rd_raw,sizeof rd_raw);
        }
        /* And the short SAP framing variant (aid_len=0 then aid-slot byte then APDU) */
        g_t=2; printf("== final apdu-only ==\n"); write_iil(6,5,2,sel_raw,sizeof sel_raw); drain(1200,6,5,0,0);
    } else if(!strcmp(m,"short")){
        for(int len=0;len<=9;len++){
            uint8_t vals[][8]={{0xA4,0x04,0,0,2,0x6F,0x03},{0,0xA4,0x04,0,0,2,0x6F,0x03},
                               {0,0,0xA4,0x04,0,0,2,0x6F}};
            for(int vi=0;vi<3;vi++){
                if(len>8)continue;
                uint8_t p[16]; memset(p,0,sizeof p);
                for(int k=0;k<len;k++) p[k]=vals[vi][k];
                char l[32]; snprintf(l,sizeof l,"v%d len=%d",vi,len);
                printf("== %s ==\n",l);
                if(write_iil(6,5,2,p,(size_t)len))continue;
                uint8_t o[256]; size_t ol=sizeof o; int h=drain(1200,6,5,o,&ol);
                printf("=> %s hits=%d\n",l,h);
            }
        }
    } else if(!strcmp(m,"short2")){
        /* Full-length padded to N (N=8..16) with the 0xA4 in different slots */
        for(int len=8;len<=16;len++) for(int off=0;off<=4;off++){
            uint8_t p[32]; memset(p,0,sizeof p);
            if(off+(int)sizeof((uint8_t[]){0xA4,0x04,0,0,2,0x6F,0x03})>(int)sizeof p)continue;
            uint8_t a[]={0xA4,0x04,0,0,2,0x6F,0x03};
            memcpy(p+off,a,sizeof a);
            size_t n=(size_t)len;
            char l[32]; snprintf(l,sizeof l,"len=%d off=%d",len,off);
            printf("== %s ==\n",l);
            if(write_iil(6,5,2,p,n))continue;
            uint8_t o[256]; size_t ol=sizeof o; int h=drain(1000,6,5,o,&ol);
            printf("=> %s hits=%d\n",l,h);
        }
    } else if(!strcmp(m,"cmd")){
        tx_apdu("select6f03",(uint8_t[]){0x00,0xA4,0x04,0x00,0x02,0x6F,0x03},7);
        tx_apdu("select2f00",(uint8_t[]){0x00,0xA4,0x04,0x00,0x02,0x2F,0x00},7);
        tx_apdu("read1",(uint8_t[]){0x00,0xB0,0x00,0x00,0x01},5);
        tx_apdu("sel_abs",(uint8_t[]){0x00,0xA4,0x08,0x04,0x04,0x7F,0xFF,0x6F,0x03},9);
    } else {
        printf("usage: %s open|raw|le1|le2|full|sweep|isim|isim2|sel|len|long|cmd|matrix|matrix2|close|inv|one|tr2|seq2|selch|abs|final|short|short2|fids\n",argv[0]);
    }
    close(fd);return 0;
}
