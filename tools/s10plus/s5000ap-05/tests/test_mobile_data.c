#define _GNU_SOURCE
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#include "mobile_data.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
static void ack(struct mobile_stop *s,uint8_t sequence,unsigned result)
{
    uint8_t p[]={13,s->subcommand,3,result&255,result>>8};
    struct nuxel_sipc_fmt f={.main_cmd=128,.sub_cmd=1,.cmd_type=2,.ack_seq=sequence,.payload=p,.payload_len=5};
    mobile_stop_receive(s,&f);
}
int main(void)
{
    char dir[]="/tmp/nuxel-data-XXXXXX";assert(mkdtemp(dir));
    char path[256];snprintf(path,sizeof path,"%s/preference",dir);
    bool enabled=true;assert(!mobile_preference_load(path,&enabled)&&enabled);
    assert(!mobile_preference_save(path,false));enabled=true;
    assert(!mobile_preference_load(path,&enabled)&&!enabled);
    assert(!mobile_preference_save(path,true));assert(!mobile_preference_load(path,&enabled)&&enabled);
    assert(!chmod(path,0644));assert(mobile_preference_load(path,&enabled)<0&&!enabled);
    assert(!unlink(path));assert(!symlink("/nonexistent",path));
    enabled=true;assert(mobile_preference_load(path,&enabled)<0&&!enabled);unlink(path);rmdir(dir);
    struct mobile_stop stop;struct fmt_tx_frame frame;mobile_stop_begin(&stop);
    for(unsigned phase=MOBILE_STOP_SETTING;phase<=MOBILE_STOP_RELEASE;phase++) {
        assert(stop.phase==phase);assert(mobile_stop_frame(&stop,&frame));
        assert(frame.main_cmd==13); /* never radio power or PS detach */
        mobile_stop_sent(&stop,41,1000);assert(!mobile_stop_frame(&stop,&frame));
        ack(&stop,40,0x8000);assert(stop.pending&&stop.phase==phase);
        ack(&stop,41,phase==MOBILE_STOP_SETTING ? 0x8003 : 0x8000);assert(!stop.pending&&stop.phase==phase+1);
    }
    assert(mobile_stop_frame(&stop,&frame));mobile_stop_sent(&stop,42,2000);
    uint8_t active[]={1,1,1};
    struct nuxel_sipc_fmt f={.main_cmd=13,.sub_cmd=4,.cmd_type=2,.ack_seq=42,.payload=active,.payload_len=3};
    mobile_stop_receive(&stop,&f);assert(stop.phase==MOBILE_STOP_FAILED);
    stop.phase=MOBILE_STOP_VERIFY;stop.pending=true;active[2]=0;
    mobile_stop_receive(&stop,&f);assert(stop.phase==MOBILE_STOP_DONE);
    mobile_stop_begin(&stop);assert(mobile_stop_frame(&stop,&frame));mobile_stop_sent(&stop,43,3000);
    ack(&stop,43,0x8005);assert(stop.phase==MOBILE_STOP_FAILED&&stop.result==0x8005);
    mobile_stop_begin(&stop);assert(mobile_stop_frame(&stop,&frame));mobile_stop_sent(&stop,44,4000);
    mobile_stop_tick(&stop,14000);assert(stop.phase==MOBILE_STOP_FAILED&&!stop.pending);
    puts("Mobile data preference, fail-closed load, correlated release, active-bearer rejection and timeout: PASS");
    return 0;
}
