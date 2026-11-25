/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_store.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static unsigned failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while (0)
static void state(struct sms_store *s,uint32_t id,const char *expected)
{
    struct sms_record r;
    CHECK(sms_store_get(s,id,&r));CHECK(!strcmp(r.state,expected));
}
static bool retry_link(struct sms_store *s,uint32_t original,uint32_t replacement)
{
    sqlite3_stmt *p=NULL;
    if (sqlite3_prepare_v2(s->db,
        "SELECT replacement FROM retry_authorizations WHERE original=?",-1,&p,NULL)!=SQLITE_OK)
        return false;
    sqlite3_bind_int64(p,1,original);
    bool ok=sqlite3_step(p)==SQLITE_ROW && sqlite3_column_type(p,0)!=SQLITE_NULL &&
            (uint32_t)sqlite3_column_int64(p,0)==replacement;
    sqlite3_finalize(p);return ok;
}
int main(void)
{
    struct sms_store s;struct sms_job job;struct sms_record record;
    CHECK(sms_store_open(&s,":memory:"));
    CHECK(!sms_store_any_delivered(&s));
    uint32_t a=0,b=0,received=0;bool changed=false;
    CHECK(sms_store_queue(&s,"+12345678901","hello",&a));
    CHECK(!sms_store_queue(&s,"+12345678901","hello",&b));
    CHECK(sms_store_next(&s,&job) && job.id==a && job.part==1 && job.total==1);
    uint8_t mr=job.pdu.reference;
    CHECK(sms_store_sending(&s,a,1));state(&s,a,"sending");
    CHECK(!sms_store_sending(&s,a,1));
    CHECK(sms_store_submit(&s,a,1,mr,0));state(&s,a,"submitted");
    struct sms_decoded report={.kind=SMS_STATUS_REPORT,.reference=mr,.status=1};
    strcpy(report.peer,"+12345678901");
    uint8_t raw[3]={1,2,3};
    CHECK(sms_store_receive(&s,raw,sizeof raw,&report,&received,&changed));
    CHECK(received==a && changed);state(&s,a,"submitted"); /* forwarded != delivered */
    report.status=0;raw[2]++;
    CHECK(sms_store_receive(&s,raw,sizeof raw,&report,&received,&changed));state(&s,a,"delivered");
    CHECK(changed);
    CHECK(sms_store_any_delivered(&s));
    /* The aggregate is a live query over per-message state, not a latch; a
     * fresh store above already returned false before any delivered row. */
    CHECK(sms_store_receive(&s,raw,sizeof raw,&report,&received,&changed) && !changed);
    CHECK(sms_store_queue(&s,"+12345678901","next",&b));
    CHECK(sms_store_next(&s,&job) && job.id==b && job.pdu.reference!=mr);
    CHECK(sms_store_sending(&s,b,1));
    CHECK(sms_store_fail(&s,b,1,-2,true));state(&s,b,"unknown");
    CHECK(!sms_store_next(&s,&job));
    report.reference=job.pdu.reference;raw[2]++;
    CHECK(sms_store_receive(&s,raw,sizeof raw,&report,&received,&changed));state(&s,b,"delivered");
    CHECK(sms_store_get(&s,b,&record) && record.error==0);
    char body[200];memset(body,'A',sizeof body-1);body[sizeof body-1]=0;
    CHECK(sms_store_queue(&s,"+12345678901",body,&b));
    CHECK(sms_store_next(&s,&job) && job.id==b && job.part==1 && job.total==2);
    CHECK(sms_store_sending(&s,b,1));CHECK(!sms_store_next(&s,&job));
    CHECK(sms_store_submit(&s,b,1,job.pdu.reference,0));
    CHECK(sms_store_next(&s,&job) && job.id==b && job.part==2);
    CHECK(sms_store_fail(&s,b,2,0x8016,false));state(&s,b,"failed");CHECK(!sms_store_next(&s,&job));
    struct sms_decoded incoming={.kind=SMS_DELIVER,.multipart=true,.concat_reference=42,.part=2,.total=2};
    strcpy(incoming.peer,"+12345678901");strcpy(incoming.text,"world");raw[0]=9;
    CHECK(sms_store_receive(&s,raw,sizeof raw,&incoming,&received,&changed) && !changed);a=received;
    state(&s,a,"receiving");
    raw[1]++;strcpy(incoming.text,"conflict");
    CHECK(!sms_store_receive(&s,raw,sizeof raw,&incoming,&received,&changed));state(&s,a,"receiving");
    incoming.part=1;strcpy(incoming.text,"hello ");
    CHECK(sms_store_receive(&s,raw,sizeof raw,&incoming,&received,&changed) && changed && received==a);
    CHECK(sms_store_get(&s,a,&record) && !strcmp(record.text,"hello world"));state(&s,a,"received");
    CHECK(sms_store_receive(&s,raw,sizeof raw,&incoming,&received,&changed) && !changed);
    CHECK(!sms_store_queue(&s,"bad","body",&b));
    /* Force a storage failure: the caller must not positively ACK this PDU. */
    CHECK(sqlite3_exec(s.db,"PRAGMA query_only=ON",NULL,NULL,NULL)==SQLITE_OK);
    raw[2]++;incoming.multipart=false;
    CHECK(!sms_store_receive(&s,raw,sizeof raw,&incoming,&received,&changed));
    sms_store_close(&s);
    char path[]="/tmp/nuxel-sms-test-XXXXXX";int fd=mkstemp(path);CHECK(fd>=0);if(fd>=0)close(fd);
    CHECK(sms_store_open(&s,path));
    CHECK(sms_store_queue(&s,"+12345678901","persistent",&a));
    CHECK(sms_store_sending(&s,a,1));sms_store_close(&s);
    CHECK(sms_store_open(&s,path));state(&s,a,"unknown");CHECK(!sms_store_next(&s,&job));
    CHECK(sms_store_get(&s,a,&record) && !strcmp(record.text,"persistent"));
    /* Safe reconciliation: resolve the unresolved message to failed, without
     * resending. It must move out of 'unknown' and become available again. */
    CHECK(sms_store_resolve(&s,a,"failed"));state(&s,a,"failed");
    CHECK(!sms_store_resolve(&s,a,"failed")); /* not unknown anymore */
    CHECK(!sms_store_resolve(&s,a,"bogus"));  /* only failed/delivered/superseded allowed */
    uint32_t ids[10];CHECK(sms_store_list(&s,ids,10)>=1 && ids[0]==a);
    /* Owner-authorized "superseded" outcome: original stays unknown
     * (not failed, not delivered), yet it is terminal and no longer blocks. */
    CHECK(sms_store_queue(&s,"+12345678901","uncertain",&a));
    CHECK(sms_store_sending(&s,a,1));sms_store_close(&s);
    CHECK(sms_store_open(&s,path));state(&s,a,"unknown");
    CHECK(sms_store_blocked(&s));
    CHECK(!sms_store_queue(&s,"+12345678901","uncertain",&b));
    CHECK(sms_store_resolve(&s,a,"superseded"));state(&s,a,"unknown");
    CHECK(!sms_store_blocked(&s));
    CHECK(!sms_store_resolve(&s,a,"superseded"));
    sms_store_close(&s);CHECK(sms_store_open(&s,path));state(&s,a,"unknown");
    CHECK(!sms_store_blocked(&s));
    CHECK(!sms_store_next(&s,&job)); /* superseded is never re-queued */
    /* Audit row records the owner authorization + residual uncertainty. */
    sqlite3_stmt *audit=NULL;
    CHECK(sqlite3_prepare_v2(s.db,"SELECT event FROM audit ORDER BY id DESC LIMIT 1",-1,&audit,NULL)==SQLITE_OK);
    CHECK(audit && sqlite3_step(audit)==SQLITE_ROW && !strcmp((const char*)sqlite3_column_text(audit,0),"superseded"));
    sqlite3_finalize(audit);
    uint32_t original=a;
    CHECK(sms_store_queue(&s,"+12345678901","uncertain",&a));CHECK(a!=original);
    CHECK(!sms_store_queue(&s,"+12345678901","uncertain",&b));
    state(&s,original,"unknown");
    CHECK(sms_store_next(&s,&job) && job.id==a); /* fresh message now flows */

    /* Multi-round regression: TWO unknown messages share peer+text, one with a
     * CONSUMED authorization and one with an UNCONSUMED authorization. A fresh
     * send must link only to the unconsumed one and never be blocked by the
     * historical consumed row. (Reproduces the real Round02 SendSms refusal.)
     * Uses a distinct peer so this scenario is isolated from the messages
     * already created above. */
    uint32_t r1=0,r2=0,r3=0;
    CHECK(sms_store_queue(&s,"+15550001001","multi",&r1));         /* round1 */
    CHECK(sms_store_sending(&s,r1,1));sms_store_close(&s);CHECK(sms_store_open(&s,path));
    state(&s,r1,"unknown");CHECK(sms_store_blocked(&s));
    CHECK(sms_store_resolve(&s,r1,"superseded"));                  /* authorizes round2 */
    state(&s,r1,"unknown");CHECK(!sms_store_blocked(&s));
    CHECK(sms_store_queue(&s,"+15550001001","multi",&r2));         /* round2 links to r1 */
    CHECK(r2!=r1 && r2!=0);state(&s,r1,"unknown");
    CHECK(retry_link(&s,r1,r2));                                    /* r1 now consumed */
    CHECK(sms_store_sending(&s,r2,1));sms_store_close(&s);CHECK(sms_store_open(&s,path));
    state(&s,r2,"unknown");CHECK(sms_store_blocked(&s));
    CHECK(sms_store_resolve(&s,r2,"superseded"));                  /* authorizes round3 */
    state(&s,r2,"unknown");CHECK(!sms_store_blocked(&s));
    CHECK(sms_store_queue(&s,"+15550001001","multi",&r3));         /* must link to r2 only */
    CHECK(r3!=0 && r3!=r1 && r3!=r2);
    CHECK(retry_link(&s,r2,r3));                                   /* r2 now consumed by r3 */
    CHECK(!retry_link(&s,r1,r3));                                  /* r1 stays consumed by r2 */
    state(&s,r1,"unknown");state(&s,r2,"unknown");                  /* both preserved unknown */
    state(&s,r3,"queued");                                        /* fresh message is queued to flow */

    sms_store_close(&s);CHECK(chmod(path,0644)==0);CHECK(!sms_store_open(&s,path));unlink(path);
    printf("SMS durable store: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);
    return failures ? 1 : 0;
}
