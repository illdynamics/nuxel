/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include "mobile_data.h"
#include "fmt_rx.h"
#include "data_session.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
int mobile_preference_load(const char *path,bool *enabled)
{
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0) { if(errno==ENOENT)return 0;*enabled=false;return -1; }
    struct stat st;char value[16];ssize_t n=read(fd,value,sizeof value);
    int valid=fstat(fd,&st)==0 && S_ISREG(st.st_mode) && st.st_uid==geteuid() && !(st.st_mode&077);
    close(fd);
    if(valid && n==8 && !memcmp(value,"enabled\n",8)) { *enabled=true;return 0; }
    if(valid && n==9 && !memcmp(value,"disabled\n",9)) { *enabled=false;return 0; }
    *enabled=false;errno=EINVAL;return -1;
}
int mobile_preference_save(const char *path,bool enabled)
{
    char tmp[512],dir[512];
    if(snprintf(tmp,sizeof tmp,"%s.XXXXXX",path)>=(int)sizeof tmp || strlen(path)>=sizeof dir) { errno=ENAMETOOLONG;return -1; }
    strcpy(dir,path);char *slash=strrchr(dir,'/');if(!slash) { errno=EINVAL;return -1; }*slash=0;
    int dfd=open(*dir?dir:"/",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(dfd<0)return -1;
    int fd=mkstemp(tmp);if(fd<0) { close(dfd);return -1; }
    const char *value=enabled?"enabled\n":"disabled\n";size_t n=strlen(value);
    int result=-1;
    if(write(fd,value,n)==(ssize_t)n && fsync(fd)==0 && rename(tmp,path)==0 && fsync(dfd)==0)result=0;
    int saved=errno;close(fd);close(dfd);unlink(tmp);errno=saved;return result;
}
bool mobile_stop_busy(const struct mobile_stop *s)
{ return s->phase>=MOBILE_STOP_SETTING && s->phase<=MOBILE_STOP_VERIFY; }
void mobile_stop_begin(struct mobile_stop *s)
{ memset(s,0,sizeof *s);s->phase=MOBILE_STOP_SETTING; }
bool mobile_stop_frame(struct mobile_stop *s,struct fmt_tx_frame *f)
{
    if(s->pending)return false;
    bool result=false;
    switch(s->phase) {
    case MOBILE_STOP_SETTING: result=fmt_tx_mobile_data(f,false,false);break;
    case MOBILE_STOP_ALWAYS: result=fmt_tx_set_always_on_pdn(f,false,DS_ALWAYS_ON_PDN_PROFILE);break;
    case MOBILE_STOP_RELEASE: result=fmt_tx_release_pdp_context(f,1);break;
    case MOBILE_STOP_VERIFY: result=fmt_tx_get_pdp_context(f);break;
    default: break;
    }
    if(result)s->subcommand=f->sub_cmd;
    return result;
}
void mobile_stop_sent(struct mobile_stop *s,uint8_t seq,uint64_t now)
{ s->sequence=seq;s->pending=true;s->deadline=now+10000; }
void mobile_stop_tick(struct mobile_stop *s,uint64_t now)
{ if(s->pending && now>=s->deadline) { s->pending=false;s->phase=MOBILE_STOP_FAILED;s->result=-ETIMEDOUT; } }
void mobile_stop_receive(struct mobile_stop *s,const struct nuxel_sipc_fmt *f)
{
    if(!s->pending || f->ack_seq!=s->sequence || f->cmd_type!=2)return;
    if(f->main_cmd==128 && f->sub_cmd==1 && f->payload_len==5 &&
       f->payload[0]==13 && f->payload[1]==s->subcommand &&
       f->payload[2]==(s->phase==MOBILE_STOP_VERIFY ? 2 : 3)) {
        s->result=f->payload[3]|((unsigned)f->payload[4]<<8);
        if(s->result!=0x8000 && !(s->phase==MOBILE_STOP_SETTING && s->result==0x8003)) { s->pending=false;s->phase=MOBILE_STOP_FAILED; }
        else if(s->phase!=MOBILE_STOP_VERIFY) { s->pending=false;s->phase++; }
    } else if(s->phase==MOBILE_STOP_VERIFY && f->main_cmd==13 && f->sub_cmd==4) {
        uint8_t state;
        if(fmt_rx_pdp_state(f->payload,f->payload_len,1,&state)) {
            s->pending=false;s->phase=state==0 ? MOBILE_STOP_DONE : MOBILE_STOP_FAILED;
            s->result=state==0 ? 0 : -EBUSY;
        }
    }
}
