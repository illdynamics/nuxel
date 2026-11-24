/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_call.h"
#include <stdio.h>
#include <string.h>
#include "vendor_call_vectors.h"
static unsigned failures;
#define CHECK(c) do { if(!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while(0)
#define VECTOR(v) CHECK(f.len==sizeof(v) && !memcmp(f.buf,v,sizeof(v)))
int main(void)
{
    struct fmt_tx_frame f;
    CHECK(fmt_call_dial(&f,"+12345678901"));VECTOR(golden_call_dial_international);
    CHECK(fmt_call_dial(&f,"0123456789"));VECTOR(golden_call_dial_national);
    CHECK(fmt_call_answer(&f));VECTOR(golden_call_answer);
    CHECK(fmt_call_release(&f));VECTOR(golden_call_release);
    CHECK(fmt_call_get_list(&f));VECTOR(golden_call_get_list);
    CHECK(fmt_call_voice_registration(&f));VECTOR(golden_call_get_voice_registration);
    CHECK(!fmt_call_dial(&f,""));CHECK(!fmt_call_dial(&f,"+"));CHECK(!fmt_call_dial(&f,"123;4"));CHECK(!fmt_call_dial(NULL,"1"));
    uint8_t one[]={1,0,1,3,2,5,0,5,0x11,'1','2','3','4','5'};
    struct fmt_call_list list;
    CHECK(fmt_call_list(one,sizeof one,&list));CHECK(list.count==1 && list.calls[0].id==3 && list.calls[0].state==5);
    CHECK(!strcmp(list.calls[0].number,"+12345") && !strcmp(fmt_call_state_name(list.calls[0].state),"incoming"));
    for(size_t i=0;i<sizeof one;i++)CHECK(!fmt_call_list(one,i,&list));
    one[5]=7;CHECK(!fmt_call_list(one,sizeof one,&list));one[5]=5;
    one[7]=83;CHECK(!fmt_call_list(one,sizeof one,&list));one[7]=5;
    uint8_t empty[]={0};CHECK(fmt_call_list(empty,sizeof empty,&list) && list.count==0);
    uint8_t status[]={0,1,3,7,9,0x11};struct fmt_call_status st;
    CHECK(fmt_call_status(status,sizeof status,&st) && st.type==0x100 && st.id==3 && st.cause_class==9 && st.cause==0x11);
    CHECK(!fmt_call_status(status,5,&st));
    uint8_t fuzz[255];uint32_t random=0x43;
    for(unsigned i=0;i<10000;i++) {
        size_t n=i%sizeof fuzz;
        for(size_t j=0;j<n;j++) { random=random*1664525u+1013904223u;fuzz[j]=(uint8_t)(random>>24); }
        (void)fmt_call_list(fuzz,n,&list);(void)fmt_call_status(fuzz,n,&st);
    }
    printf("Call vendor vectors/parser: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);return failures ? 1 : 0;
}
