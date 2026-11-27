/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_store.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static bool sql(struct sms_store *s,const char *q)
{ return s && s->db && sqlite3_exec(s->db,q,NULL,NULL,NULL)==SQLITE_OK; }
static sqlite3_stmt *prepare(struct sms_store *s,const char *q)
{
    sqlite3_stmt *p=NULL;
    if (!s || !s->db || sqlite3_prepare_v2(s->db,q,-1,&p,NULL)!=SQLITE_OK) return NULL;
    return p;
}
static bool done(sqlite3_stmt *p)
{
    if (!p) return false;
    bool ok=sqlite3_step(p)==SQLITE_DONE;
    return sqlite3_finalize(p)==SQLITE_OK && ok;
}
static bool text(sqlite3_stmt *p,int col,const char *v)
{ return p && sqlite3_bind_text(p,col,v,-1,SQLITE_TRANSIENT)==SQLITE_OK; }
static bool integer(sqlite3_stmt *p,int col,sqlite3_int64 v)
{ return p && sqlite3_bind_int64(p,col,v)==SQLITE_OK; }
static bool blob(sqlite3_stmt *p,int col,const uint8_t *v,size_t n)
{ return p && n<=INT_MAX && sqlite3_bind_blob(p,col,v,(int)n,SQLITE_TRANSIENT)==SQLITE_OK; }
static bool rollback(struct sms_store *s) { (void)sql(s,"ROLLBACK");return false; }

void sms_store_close(struct sms_store *s)
{ if (s && s->db) { sqlite3_close(s->db);s->db=NULL; } }

bool sms_store_open(struct sms_store *s,const char *path)
{
    if (!s || !path) return false;
    s->db=NULL;bool memory=!strcmp(path,":memory:");
    struct stat st;
    if (!memory && lstat(path,&st)==0) {
        if (!S_ISREG(st.st_mode) || st.st_uid!=geteuid() || (st.st_mode&0077)) return false;
    } else if (!memory && errno!=ENOENT) return false;
    mode_t mask=umask(0077);
    int rc=sqlite3_open_v2(path,&s->db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,NULL);
    umask(mask);
    if (rc!=SQLITE_OK) { sms_store_close(s);return false; }
    sqlite3_busy_timeout(s->db,1000);
    (void)sqlite3_db_config(s->db,SQLITE_DBCONFIG_DEFENSIVE,1,NULL);
    sqlite3_stmt *p=prepare(s,"PRAGMA user_version");
    if (!p || sqlite3_step(p)!=SQLITE_ROW) { if(p)sqlite3_finalize(p);goto fail; }
    int version=sqlite3_column_int(p,0);sqlite3_finalize(p);
    if (version!=0 && version!=1) goto fail;
    if (!sql(s,"PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;"
        "CREATE TABLE IF NOT EXISTS messages("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,direction TEXT NOT NULL,peer TEXT NOT NULL,"
        "text TEXT NOT NULL,state TEXT NOT NULL,total INTEGER NOT NULL,concat_ref INTEGER,"
        "stamp TEXT NOT NULL DEFAULT '',error INTEGER NOT NULL DEFAULT 0,"
        "created INTEGER NOT NULL DEFAULT(unixepoch()));"
        "CREATE TABLE IF NOT EXISTS parts("
        "message INTEGER NOT NULL REFERENCES messages(id),part INTEGER NOT NULL,"
        "pdu BLOB NOT NULL,text TEXT NOT NULL DEFAULT '',mr INTEGER NOT NULL DEFAULT 0,"
        "state TEXT NOT NULL,result INTEGER NOT NULL DEFAULT 0,status INTEGER NOT NULL DEFAULT -1,"
        "PRIMARY KEY(message,part));"
        "CREATE TABLE IF NOT EXISTS seen(pdu BLOB PRIMARY KEY,message INTEGER,"
        "created INTEGER NOT NULL DEFAULT(unixepoch()));"
        "CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "message INTEGER,stamp TEXT NOT NULL DEFAULT '',event TEXT NOT NULL,"
        "detail TEXT NOT NULL DEFAULT '');"
        "CREATE TABLE IF NOT EXISTS retry_authorizations(original INTEGER PRIMARY KEY REFERENCES messages(id),"
        "replacement INTEGER UNIQUE REFERENCES messages(id));"
        "CREATE TABLE IF NOT EXISTS submission_results(id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "stamp INTEGER NOT NULL DEFAULT(unixepoch()),candidate INTEGER,type INTEGER,plen INTEGER,"
        "ack INTEGER,result INTEGER,mr INTEGER,correlated INTEGER,state TEXT,reason TEXT);"
        "PRAGMA user_version=1;"
        /* A crash after write but before response is ambiguous, not permission
         * to resend the same SMS. Hold the entire message for explicit review. */
        "UPDATE messages SET state='unknown',error=-2 WHERE id IN"
        "(SELECT message FROM parts WHERE state='sending');"
        "UPDATE parts SET state='unknown',result=-2 WHERE state='sending';"
        "DELETE FROM seen WHERE created<unixepoch()-86400;")) goto fail;
    return true;
fail:sms_store_close(s);return false;
}

static bool recalc(struct sms_store *s,uint32_t id)
{
    sqlite3_stmt *p=prepare(s,
        "UPDATE messages SET state=CASE "
        "WHEN EXISTS(SELECT 1 FROM parts WHERE message=messages.id AND state='failed') THEN 'failed' "
        "WHEN EXISTS(SELECT 1 FROM parts WHERE message=messages.id AND state='unknown') THEN 'unknown' "
        "WHEN NOT EXISTS(SELECT 1 FROM parts WHERE message=messages.id AND state!='delivered') THEN 'delivered' "
        "WHEN EXISTS(SELECT 1 FROM parts WHERE message=messages.id AND state='sending') THEN 'sending' "
        "WHEN EXISTS(SELECT 1 FROM parts WHERE message=messages.id AND state='queued') THEN 'queued' "
        "ELSE 'submitted' END,error=COALESCE((SELECT result FROM parts WHERE message=messages.id "
        "AND result!=0 ORDER BY part LIMIT 1),0) WHERE id=? AND direction='out'");
    integer(p,1,id);return done(p);
}

bool sms_store_queue(struct sms_store *s,const char *to,const char *body,uint32_t *id)
{
    struct sms_encoded encoded;
    if (!id || sms_encode(to,body,0,0,&encoded)!=SMS_CODEC_OK || !sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *duplicate=prepare(s,"SELECT 1 FROM messages WHERE direction='out' "
        "AND peer=? AND text=? AND state IN('queued','sending') LIMIT 1");
    text(duplicate,1,to);text(duplicate,2,body);
    if (!duplicate) return rollback(s);
    int dr=sqlite3_step(duplicate);sqlite3_finalize(duplicate);
    if (dr!=SQLITE_DONE) return rollback(s);
    /* A retry is a new intent, authorized exactly once for this exact unknown
     * message. For every unknown message sharing (peer,text): an authorization
     * with replacement still NULL is the single live retry token; an
     * authorization whose replacement is already set is historical evidence,
     * never a re-authorization; and a message with NO authorization is an
     * unresolved blocker that must fail closed. */
    sqlite3_stmt *p=prepare(s,
        "SELECT m.id,a.original,a.replacement FROM messages m LEFT JOIN retry_authorizations a "
        "ON a.original=m.id WHERE m.direction='out' AND m.peer=? AND m.text=? AND m.state='unknown'");
    text(p,1,to);text(p,2,body);
    if (!p) return rollback(s);
    uint32_t original=0;unsigned live=0;int check;
    while ((check=sqlite3_step(p))==SQLITE_ROW) {
        uint32_t candidate=(uint32_t)sqlite3_column_int64(p,0);
        if (sqlite3_column_type(p,1)==SQLITE_NULL) { /* no authorization row at all */
            sqlite3_finalize(p);return rollback(s); /* unresolved blocker, fail closed */
        }
        if (sqlite3_column_type(p,2)==SQLITE_NULL) { /* authorized, not yet consumed */
            if (live++) { sqlite3_finalize(p);return rollback(s); } /* ambiguous tokens */
            original=candidate;
        }
        /* a.replacement set: consumed historical authorization, ignore. */
    }
    sqlite3_finalize(p);if(check!=SQLITE_DONE)return rollback(s);
    /* Reserve original and returned references for pending delivery reports.
     * Unsequenced submission results are not correlated using these values. */
    bool used[256]={0};p=prepare(s,
        "SELECT mr,pdu FROM parts JOIN messages ON messages.id=parts.message WHERE direction='out' "
        "AND (parts.state IN('queued','sending','submitted','unknown') OR messages.created>unixepoch()-86400)");
    if (!p) return rollback(s);
    int rc;
    while ((rc=sqlite3_step(p))==SQLITE_ROW) {
        used[(unsigned)sqlite3_column_int(p,0)&255]=true;
        if (sqlite3_column_bytes(p,1)>=2) used[((const uint8_t *)sqlite3_column_blob(p,1))[1]]=true;
    }
    sqlite3_finalize(p);if (rc!=SQLITE_DONE) return rollback(s);
    unsigned first;
    for (first=0;first<256;first++) {
        bool free=true;
        for (size_t i=0;i<encoded.count;i++) if (used[(first+i)&255]) free=false;
        if (free) break;
    }
    if (first==256) return rollback(s);
    p=prepare(s,"INSERT INTO messages(direction,peer,text,state,total) VALUES('out',?,?,'queued',?)");
    text(p,1,to);text(p,2,body);integer(p,3,(sqlite3_int64)encoded.count);
    if (!done(p)) return rollback(s);
    sqlite3_int64 row=sqlite3_last_insert_rowid(s->db);
    if (row<=0 || row>UINT32_MAX || sms_encode(to,body,(uint8_t)first,(uint8_t)row,&encoded)!=SMS_CODEC_OK) return rollback(s);
    for (size_t i=0;i<encoded.count;i++) {
        p=prepare(s,"INSERT INTO parts(message,part,pdu,mr,state) VALUES(?,?,?,?,'queued')");
        integer(p,1,row);integer(p,2,(sqlite3_int64)i+1);blob(p,3,encoded.parts[i].data,encoded.parts[i].len);integer(p,4,encoded.parts[i].reference);
        if (!done(p)) return rollback(s);
    }
    if (original) {
        p=prepare(s,"UPDATE retry_authorizations SET replacement=? WHERE original=? AND replacement IS NULL");
        integer(p,1,row);integer(p,2,original);
        if (!done(p) || sqlite3_changes(s->db)!=1) return rollback(s);
    }
    if (!sql(s,"COMMIT")) return rollback(s);
    *id=(uint32_t)row;return true;
}

bool sms_store_next(struct sms_store *s,struct sms_job *job)
{
    if (!job) return false;
    sqlite3_stmt *p=prepare(s,"SELECT m.id,p.part,m.total,p.pdu,p.mr FROM parts p JOIN messages m ON m.id=p.message "
        "WHERE m.direction='out' AND m.state IN('queued','sending','submitted') AND p.state='queued' "
        "AND NOT EXISTS(SELECT 1 FROM parts earlier WHERE earlier.message=m.id AND earlier.part<p.part "
        "AND earlier.state NOT IN('submitted','delivered')) ORDER BY m.id,p.part LIMIT 1");
    if (!p) return false;
    bool ok=false;
    if (sqlite3_step(p)==SQLITE_ROW) {
        int n=sqlite3_column_bytes(p,3);
        if (n>0 && n<=SMS_MAX_PDU) {
            memset(job,0,sizeof *job);job->id=(uint32_t)sqlite3_column_int64(p,0);
            job->part=(unsigned)sqlite3_column_int(p,1);job->total=(unsigned)sqlite3_column_int(p,2);
            job->pdu.len=(size_t)n;memcpy(job->pdu.data,sqlite3_column_blob(p,3),(size_t)n);
            job->pdu.reference=(uint8_t)sqlite3_column_int(p,4);ok=true;
        }
    }
    sqlite3_finalize(p);return ok;
}

bool sms_store_sending(struct sms_store *s,uint32_t id,unsigned part)
{
    if (!sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *p=prepare(s,"UPDATE parts SET state='sending' WHERE message=? AND part=? AND state='queued'");
    integer(p,1,id);integer(p,2,part);
    if (!done(p) || sqlite3_changes(s->db)!=1 || !recalc(s,id)) return rollback(s);
    return sql(s,"COMMIT") || rollback(s);
}

bool sms_store_submit(struct sms_store *s,uint32_t id,unsigned part,uint8_t mr,uint16_t result)
{
    if (!sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *p=prepare(s,"UPDATE parts SET state=CASE WHEN state='delivered' AND ?=0 THEN state ELSE ? END,"
        "mr=?,result=? WHERE message=? AND part=? AND state IN('sending','delivered')");
    integer(p,1,result);text(p,2,result ? "failed" : "submitted");integer(p,3,mr);integer(p,4,result);integer(p,5,id);integer(p,6,part);
    if (!done(p) || sqlite3_changes(s->db)!=1 || !recalc(s,id)) return rollback(s);
    return sql(s,"COMMIT") || rollback(s);
}

bool sms_store_fail(struct sms_store *s,uint32_t id,unsigned part,int error,bool uncertain)
{
    if (!sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *p=prepare(s,"UPDATE parts SET state=?,result=? WHERE message=? AND part=? AND state IN('queued','sending')");
    text(p,1,uncertain ? "unknown" : "failed");integer(p,2,error);integer(p,3,id);integer(p,4,part);
    if (!done(p) || sqlite3_changes(s->db)!=1 || !recalc(s,id)) return rollback(s);
    return sql(s,"COMMIT") || rollback(s);
}

static bool delivery(struct sms_store *s,const struct sms_decoded *v,uint32_t *id,bool *changed)
{
    sqlite3_stmt *p=prepare(s,"SELECT p.message,p.part,p.status FROM parts p JOIN messages m ON m.id=p.message "
        "WHERE m.direction='out' AND m.peer=? AND p.mr=? AND p.state IN('sending','submitted','unknown','delivered') "
        "ORDER BY m.id DESC LIMIT 1");
    text(p,1,v->peer);integer(p,2,v->reference);if (!p) return false;
    int rc=sqlite3_step(p);unsigned part=0;int prior=-1;
    if (rc==SQLITE_ROW) { *id=(uint32_t)sqlite3_column_int64(p,0);part=(unsigned)sqlite3_column_int(p,1);prior=sqlite3_column_int(p,2); }
    sqlite3_finalize(p);
    if (rc!=SQLITE_ROW) return rc==SQLITE_DONE;
    /* Only TP-ST=0 proves recipient delivery. 1 means forwarded without
     * confirmation; reserved/completed and temporary states stay submitted. */
    const char *state=v->status==0 ? "delivered" : v->status>=0x40 && v->status<0x80 ? "failed" : "submitted";
    p=prepare(s,"UPDATE parts SET state=CASE WHEN state='delivered' THEN state ELSE ? END,status=?,"
        "result=CASE WHEN state='delivered' OR ?='delivered' THEN 0 WHEN ?='failed' THEN ? ELSE result END WHERE message=? AND part=?");
    text(p,1,state);integer(p,2,v->status);text(p,3,state);text(p,4,state);integer(p,5,0x10000+v->status);integer(p,6,*id);integer(p,7,part);
    if (!done(p) || !recalc(s,*id)) return false;
    *changed=prior!=v->status;return true;
}

bool sms_store_receive(struct sms_store *s,const uint8_t *pdu,size_t len,
                       const struct sms_decoded *v,uint32_t *id,bool *changed)
{
    if (!pdu || !len || len>SMS_MAX_PDU || !v || !id || !changed ||
        (v->kind!=SMS_DELIVER && v->kind!=SMS_STATUS_REPORT) ||
        (v->multipart && (!v->total || v->total>SMS_MAX_PARTS || !v->part || v->part>v->total)) ||
        !sql(s,"BEGIN IMMEDIATE")) return false;
    *id=0;*changed=false;
    sqlite3_stmt *p=prepare(s,"SELECT message FROM seen WHERE pdu=?");blob(p,1,pdu,len);
    if (!p) return rollback(s);
    int rc=sqlite3_step(p);
    if (rc==SQLITE_ROW) { *id=(uint32_t)sqlite3_column_int64(p,0);sqlite3_finalize(p);return sql(s,"COMMIT") || rollback(s); }
    sqlite3_finalize(p);if (rc!=SQLITE_DONE) return rollback(s);
    if (v->kind==SMS_STATUS_REPORT) {
        if (!delivery(s,v,id,changed)) return rollback(s);
    } else {
        if (v->multipart) {
            p=prepare(s,"SELECT id FROM messages WHERE direction='in' AND peer=? AND concat_ref=? AND total=? "
                "AND state='receiving' AND created>unixepoch()-86400 ORDER BY id DESC LIMIT 1");
            text(p,1,v->peer);integer(p,2,v->concat_reference);integer(p,3,v->total);
            if (!p) return rollback(s);
            rc=sqlite3_step(p);if (rc==SQLITE_ROW) *id=(uint32_t)sqlite3_column_int64(p,0);
            sqlite3_finalize(p);if (rc!=SQLITE_ROW && rc!=SQLITE_DONE) return rollback(s);
        }
        if (!*id) {
            p=prepare(s,"INSERT INTO messages(direction,peer,text,state,total,concat_ref,stamp) VALUES('in',?,'','receiving',?,?,?)");
            text(p,1,v->peer);integer(p,2,v->multipart ? v->total : 1);integer(p,3,v->concat_reference);text(p,4,v->timestamp);
            if (!done(p)) return rollback(s);
            sqlite3_int64 row=sqlite3_last_insert_rowid(s->db);
            if (row<=0 || row>UINT32_MAX) return rollback(s);
            *id=(uint32_t)row;
        }
        /* A conflicting segment with the same concatenation reference must
         * not be acknowledged and silently discarded or mixed into a message. */
        p=prepare(s,"INSERT INTO parts(message,part,pdu,text,state) VALUES(?,?,?,?,'received')");
        integer(p,1,*id);integer(p,2,v->multipart ? v->part : 1);blob(p,3,pdu,len);text(p,4,v->text);
        if (!done(p)) return rollback(s);
        p=prepare(s,"SELECT part,text FROM parts WHERE message=? ORDER BY part");integer(p,1,*id);
        if (!p) return rollback(s);
        char combined[SMS_MAX_TEXT]={0};size_t used=0;unsigned count=0;bool valid=true;
        while ((rc=sqlite3_step(p))==SQLITE_ROW) {
            count++;if ((unsigned)sqlite3_column_int(p,0)!=count) valid=false;
            const char *t=(const char *)sqlite3_column_text(p,1);int n=sqlite3_column_bytes(p,1);
            if (!t || n<0 || (size_t)n>=sizeof combined-used) { valid=false;break; }
            memcpy(combined+used,t,(size_t)n);used+=(size_t)n;combined[used]=0;
        }
        sqlite3_finalize(p);
        if (rc!=SQLITE_DONE) return rollback(s);
        if (valid && count==(v->multipart ? v->total : 1)) {
            p=prepare(s,"UPDATE messages SET state='received',text=? WHERE id=?");text(p,1,combined);integer(p,2,*id);
            if (!done(p)) return rollback(s);
            *changed=true;
        }
    }
    p=prepare(s,"INSERT INTO seen(pdu,message) VALUES(?,?)");blob(p,1,pdu,len);integer(p,2,*id);
    if (!done(p) || !sql(s,"COMMIT")) return rollback(s);
    return true;
}

static bool column_text(sqlite3_stmt *p,int col,char *out,size_t cap)
{
    const char *v=(const char *)sqlite3_column_text(p,col);int n=sqlite3_column_bytes(p,col);
    if (!v || n<0 || (size_t)n>=cap) return false;
    memcpy(out,v,(size_t)n);out[n]=0;return true;
}

bool sms_store_get(struct sms_store *s,uint32_t id,struct sms_record *out)
{
    if (!out) return false;
    sqlite3_stmt *p=prepare(s,"SELECT id,direction,peer,text,state,total,stamp,error FROM messages WHERE id=?");integer(p,1,id);
    if (!p) return false;
    bool ok=false;struct sms_record v={0};
    if (sqlite3_step(p)==SQLITE_ROW) {
        v.id=(uint32_t)sqlite3_column_int64(p,0);v.parts=(unsigned)sqlite3_column_int(p,5);v.error=sqlite3_column_int(p,7);
        ok=column_text(p,1,v.direction,sizeof v.direction) && column_text(p,2,v.peer,sizeof v.peer) &&
           column_text(p,3,v.text,sizeof v.text) && column_text(p,4,v.state,sizeof v.state) && column_text(p,6,v.timestamp,sizeof v.timestamp);
    }
    sqlite3_finalize(p);if (ok) *out=v;return ok;
}

bool sms_store_peer(struct sms_store *s,uint32_t id,char *out,size_t cap)
{
    if (!out || !cap) return false;
    sqlite3_stmt *p=prepare(s,"SELECT peer FROM messages WHERE id=? AND direction='out'");
    integer(p,1,id);
    if (!p) return false;
    bool ok=false;
    if (sqlite3_step(p)==SQLITE_ROW) ok=column_text(p,0,out,cap);
    sqlite3_finalize(p);return ok;
}

/* Revert a part from 'sending' back to 'queued' after a send that never
 * reached the network (e.g. the SIP transport refused the MESSAGE). No
 * message state changes are fabricated; recalc keeps the aggregate truthful. */
bool sms_store_requeue(struct sms_store *s,uint32_t id,unsigned part)
{
    if (!sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *p=prepare(s,"UPDATE parts SET state='queued' WHERE message=? AND part=? AND state='sending'");
    integer(p,1,id);integer(p,2,part);
    if (!done(p) || sqlite3_changes(s->db)!=1 || !recalc(s,id)) return rollback(s);
    return sql(s,"COMMIT") || rollback(s);
}

size_t sms_store_list(struct sms_store *s,uint32_t *ids,size_t cap)
{
    if (!ids || !cap) return 0;
    sqlite3_stmt *p=prepare(s,"SELECT id FROM messages ORDER BY id DESC LIMIT ?");integer(p,1,cap>256 ? 256 : (sqlite3_int64)cap);
    if (!p) return 0;
    size_t n=0;while (n<cap && sqlite3_step(p)==SQLITE_ROW) ids[n++]=(uint32_t)sqlite3_column_int64(p,0);
    sqlite3_finalize(p);return n;
}

bool sms_store_any_delivered(struct sms_store *s)
{
    if (!s || !s->db) return false;
    sqlite3_stmt *p=prepare(s,
        "SELECT 1 FROM messages WHERE direction='out' AND state='delivered' LIMIT 1");
    if (!p) return false;
    bool any=sqlite3_step(p)==SQLITE_ROW;
    sqlite3_finalize(p);
    return any;
}

bool sms_store_resolve(struct sms_store *s,uint32_t id,const char *outcome)
{
    if (!s || !s->db || !outcome) return false;
    if (strcmp(outcome,"failed") && strcmp(outcome,"delivered") && strcmp(outcome,"superseded")) return false;
    if (!sql(s,"BEGIN IMMEDIATE")) return false;
    sqlite3_stmt *p;
    if (!strcmp(outcome,"superseded")) {
        p=prepare(s,"INSERT INTO retry_authorizations(original) SELECT id FROM messages "
            "WHERE id=? AND direction='out' AND state='unknown'");
        integer(p,1,id);
    } else {
        p=prepare(s,"UPDATE parts SET state=?1,result=CASE ?1 WHEN 'failed' THEN -1 ELSE 0 END "
            "WHERE message=?2 AND state='unknown'");
        text(p,1,outcome);integer(p,2,id);
    }
    if (!done(p) || sqlite3_changes(s->db)==0) return rollback(s);
    p=prepare(s,"INSERT INTO audit(message,stamp,event,detail) VALUES(?,unixepoch(),?,?)");
    integer(p,1,id);text(p,2,outcome);
    text(p,3,!strcmp(outcome,"superseded")
        ? "owner reports non-reception; original submission unknown; one new submission authorized"
        : !strcmp(outcome,"delivered") ? "owner-confirmed receipt" : "owner-confirmed failure");
    if (!done(p) || !recalc(s,id)) return rollback(s);
    return sql(s,"COMMIT") || rollback(s);
}

bool sms_store_blocked(struct sms_store *s)
{
    sqlite3_stmt *p=prepare(s,"SELECT 1 FROM parts p WHERE p.state='unknown' AND NOT EXISTS "
        "(SELECT 1 FROM retry_authorizations a WHERE a.original=p.message) LIMIT 1");
    if (!p) return true;
    int rc=sqlite3_step(p);sqlite3_finalize(p);
    return rc!=SQLITE_DONE;
}

bool sms_store_result(struct sms_store *s,uint32_t candidate,unsigned type,unsigned len,
                      unsigned ack,unsigned result,unsigned mr,bool correlated,
                      const char *state,const char *reason)
{
    sqlite3_stmt *p=prepare(s,"INSERT INTO submission_results"
        "(candidate,type,plen,ack,result,mr,correlated,state,reason) VALUES(?,?,?,?,?,?,?,?,?)");
    integer(p,1,candidate);integer(p,2,type);integer(p,3,len);integer(p,4,ack);
    integer(p,5,result);integer(p,6,mr);integer(p,7,correlated);
    text(p,8,state);text(p,9,reason);return done(p);
}
