/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_SMS_SERVICE_H
#define NUXEL_SMS_SERVICE_H
#include "fmt_sms.h"
#include "sms_store.h"
#include "sipc5_fmt.h"
typedef bool (*sms_write_fn)(const struct fmt_tx_frame *,uint8_t *sequence,void *);
typedef void (*sms_notify_fn)(uint32_t id,bool incoming,void *user);

/* Redacted metadata for a validated SMS submission-result notification.
 * Contains NO recipient number, message body, or PDU bytes. */
struct sms_submit_result_diag {
    uint8_t  cmd_type;       /* 2 = CP response (ack_seq echo), 3 = CP notification */
    uint32_t payload_len;    /* frame payload length */
    uint8_t  ack_seq;        /* SIPC ack/correlation sequence (0 for notifications) */
    uint16_t result_code;    /* decoded raw submit result; 0 = submitted, never delivered */
    uint32_t message_id;
    uint8_t  modem_ref;      /* message reference returned by the CP */
    bool     correlated;     /* true only when matched to the single in-flight segment */
    const char *reason;
    const char *state;       /* durable result when correlated: "submitted" or "failed" */
};
typedef void (*sms_result_fn)(const struct sms_submit_result_diag *,void *user);

/* Optional transport-independent SMS-over-IMS submit hook. When set and the
 * CS domain is unavailable but IMS is registered, the service hands the
 * segment's SMSC-prefixed PDU to this callback, which encapsulates it in a SIP
 * MESSAGE (application/vnd.3gpp.sms RP-DATA). Returns true only if the SIP
 * MESSAGE was fully handed to the transport (a send, NOT a delivery). The
 * final outcome still arrives as a RP-ACK/RP-ERROR or timeout. */
typedef bool (*sms_ims_submit_fn)(const char *peer, const uint8_t *tpdu,
                                  size_t tpdu_len, uint8_t mr, void *user);

struct sms_service {
    struct sms_store store;
    sms_write_fn write;
    sms_notify_fn notify;
    sms_result_fn result_diag;
    sms_ims_submit_fn ims_submit;
    void *user; /* shared argument for write/notify/result_diag callbacks */
    uint8_t smsc[12],sequence,ready_sequence;
    size_t smsc_len;
    bool ready_sent,ready_ack,ready_rejected,active,blocked,online;
    unsigned setup_attempts;
    uint64_t next_setup_ms,deadline_ms;
    struct sms_job job;
    unsigned received,decode_errors,store_errors,ack_errors,unmatched;
    /* Registration observation only. The CP FMT writer is not an IMS
     * transport; ModemType 8 must never be serialized as a domain byte. */
    bool ims_registered;
    /* Authoritative native SIP 200 OK to OUR REGISTER, distinct from the
     * modem's IIL relay. Set by the caller (radiod) each tick; the IMS
     * transport is selected only when this is true. */
    bool ims_registered_native;
    uint8_t selected_domain;
    /* In-flight SMS-over-IMS submission. The SIP MESSAGE result is correlated
     * separately from the CP FMT submission result: the IMS hook send only
     * proves the MESSAGE left the UE. `ims_await_ack` is cleared by
     * sms_service_ims_result() (SIP 2xx accepted) or by the send deadline
     * (uncertain). It never advances the CP correlation `sequence`. */
    bool ims_await_ack;
    uint64_t ims_deadline_ms;
};
bool sms_service_open(struct sms_service *s,const char *path,sms_write_fn write,sms_notify_fn notify,void *user);
void sms_service_set_result_diag(struct sms_service *s,sms_result_fn fn);
void sms_service_set_ims_submit(struct sms_service *s,sms_ims_submit_fn fn);
void sms_service_close(struct sms_service *s);
void sms_service_tick(struct sms_service *s,uint64_t now,bool online,bool sim_ready,bool cs_registered,bool ims_registered,bool writable);
void sms_service_receive(struct sms_service *s,const struct nuxel_sipc_fmt *frame);
/* Resolve one unresolved outbound message without resending it. Re-derives the
 * blocked flag from the remaining store contents. */
bool sms_service_resolve(struct sms_service *s,uint32_t id,const char *outcome);
/* Consume a SIP MESSAGE transaction result for the in-flight SMS-over-IMS
 * submission. accepted=true on a 2xx (SIP accepted; the message is "submitted",
 * NOT delivered — only a STATUS-REPORT proves delivery). accepted=false on a
 * non-2xx final (the message is "failed" with the SIP code as error). Returns
 * true only when it applied to an in-flight IMS submission. Caller passes an
 * opaque SIP result (a status code) only; the service never sees SIP text. */
bool sms_service_ims_result(struct sms_service *s,bool accepted,int sip_code);
/* True while a SIP MESSAGE has been sent but its transaction result has not
 * yet been observed (used to classify stray/late replies). */
bool sms_service_ims_pending(const struct sms_service *s);
#endif
