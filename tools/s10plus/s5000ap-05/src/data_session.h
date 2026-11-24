/*
 * data_session.h — S5000AP Stage-06 native data-session state machine.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Drives the verified FMT data-path commands (mobile-data, set-data-profile,
 * set-lte-attach-profile, define PDP context, always-on PDN, PS attach,
 * data-call establish) in a bounded, step-wise, response-correlated sequence.
 * This module is PURE re: I/O — it only advances the FSM state; the caller
 * (radiod) performs the actual bounded device writes via fmt_tx + the
 * transport, and feeds back modem responses.
 *
 * TRUTH CONTRACT:
 *  - A step does NOT "succeed" merely because a frame was written. It advances
 *    ONLY when the corresponding modem response is authenticated.
 *  - Retries are bounded. On a modem rejection the FSM stops and reports the
 *    exact failure; it never brute-forces commands/APNs/flags.
 *  - No PIN/PUK/IMSI/ICCID/IMEI/MSISDN is ever stored or logged.
 */
#ifndef NUXEL_DATA_SESSION_H
#define NUXEL_DATA_SESSION_H

#include <stdint.h>
#include <stdbool.h>

enum ds_phase {
    DS_IDLE = 0,
    DS_SIM_CHECK,          /* confirm SIM READY */
    DS_NET_REGIST_CHECK,   /* read PS/data registration (GetDataRegState NET_REGIST) */
    DS_SET_SERVICE_DOMAIN, /* NET service domain CS_PS (SetServiceDomain sub=8) */
    DS_SET_PREFERRED_NET,  /* NET preferred type LTE (SetPreferredNetType sub=10) */
    DS_ENABLE_MOBILE_DATA, /* GPRS mobile data ON (SetMobileDataSetting sub=29) */
    DS_SYNC_PROFILE,       /* full profile sync w/ RAT (SyncProfileInfo sub=37) */
    DS_SET_DATA_PROFILE,   /* set APN/auth/protocol data profile */
    DS_SET_LTE_ATTACH,     /* set LTE attach profile (required for LTE PS) */
    DS_MBIM_ATTACH_CONFIG, /* MBIM MS LTE Attach Config (CID 0x0A) via IpcTxRawIpc */
    DS_DEFINE_PDP,         /* define PDP context w/ APN */
    DS_ALWAYS_ON_PDN,      /* always-on PDN profile */
    DS_PS_ATTACH,          /* GPRS PS attach */
    DS_PS_REGIST_VERIFY,   /* re-query PS registration; gate data call on attach */
    DS_DATA_CALL,          /* activate PDP context */
    DS_GET_PDP_LIST,       /* query PDP context list (fetch IP config) */
    DS_WAIT_IP,            /* wait for rmnet + IP config */
    DS_ACTIVE,             /* data active */
    DS_REJECTED,           /* modem rejected (terminal for this attempt) */
    DS_FAILED,             /* timeout/generic failure */
};

struct data_session_ctx {
    enum ds_phase  phase;
    uint8_t        attempt;      /* bounded attempt counter */
    uint8_t        apn[128];     /* configured APN (owner-approved) */
    uint8_t        apn_len;
    uint8_t        profile_id;
    uint8_t        protocol;      /* IP family for PDP/attach (FMT_TX_PROTO_*) */
    uint8_t        attach_cid;    /* attach/context CID (GetAttachCid: single-SIM=1, DSDS=5) */
    uint8_t        attach_flag;   /* SetLteAttachProfile payload[0] (3=apply, 1=define) */
    uint8_t        auth_code;     /* DataAuth region code (1=none, 2=PAP, 3=CHAP); SetPdpContext converts 1->0 */
    uint8_t        pdp_type_wire; /* SetPdpContext payload[0] (FMT_TX_PDP_TYPE_*) */
    bool           mobile_data_on;
    bool           attached;
    bool           call_established;
    bool           ip_configured;
    uint64_t       step_deadline_ms;
    uint64_t       phase_entered_ms;  /* monotonic ts when current phase began */

    /* Stage-06 response-decode state (populated from REAL modem responses only;
     * never from a frame write). These drive the strict FSM transitions. */
    uint8_t        last_gen_result;    /* GEN echo result byte (0=success) */
    uint8_t        last_gprs_call_state; /* GPRS_CALL_STATUS state byte */
    uint8_t        last_gprs_pdp_state;  /* GPRS_PDP_CONTEXT list state byte */
    /* NET_REGIST decoded registration states (authoritative RegState enum):
     * 0=off,1=registered,2=searching,3=denied,4=unknown,5=roaming. */
    uint8_t        last_cs_reg_state;
    uint8_t        last_ps_reg_state;
    uint8_t        last_reject_cause;   /* NET_REGIST payload[10] reject byte */
    bool           net_regist_valid;
    bool           gen_result_valid;   /* a GEN result has been correlated */
    bool           gprs_call_state_valid;
    bool           gprs_pdp_state_valid;
};

/* ATTACH CID — corrected round-17 disassembly of GetAttachCid() @0x1e4500:
 *
 *     mov  w9, #5
 *     cmp  w8, #1            ; DataCallManager::mModelType
 *     csinc w9, w9, wzr, eq  ; model_type==1 -> w9=5, else w9=1
 *     cmp  w8, #0
 *     csinc w0, w9, wzr, ne  ; model_type!=0 -> w0=w9, else w0=1
 *
 *   => model_type==1 -> 5 ; model_type==0 -> 1 ; model_type>=2 -> 1
 *
 * The device is SM-G975F/beyond2lte EUR OPEN "_EUR0" (single physical SIM),
 * i.e. NOT dual-sim model_type 1. The corrected GetAttachCid is therefore 1,
 * NOT 5. (The prior "returns 5 for the standard LTE model" comment was a
 * mis-read of the csinc chain; only model_type==1 yields 5.)
 *
 * The DATA PROFILE default id is a SEPARATE value (ConvertProfileId(DEFAULT)
 * == 1, non-NTC). Keep attach CID and profile id as distinct names. */
#define DS_ATTACH_CID 1u

/* AlwaysOnPdn wire payload[1] (IpcTxSetAlwaysOnPdn(bool, DataProfile, int)
 * @0x321550) is the *int* argument that DoAlwaysOnPdn() supplies as 1 (or 2
 * under an ESM-flag-zero network), NOT the attach CID and NOT a raw
 * DataProfile enum value. ConvertProfileId(DEFAULT)==1. */
#define DS_ALWAYS_ON_PDN_PROFILE 1u

/* Gen echo result codes recovered live + source-backed (vendor IpcRxGeneral):
 * 0 == success; non-zero == rejection/failure. We deliberately do NOT map a
 * specific enum for 0x01/0x03 yet — non-zero is sufficient to fail-closed. */
#define DS_GEN_RESULT_OK 0u

/* GPRS data-call state (IpcRxGprsCallStatus @0x321ab0): the CP reports
 * payload[1] as the data-call state. 1/10/11 -> connected (4/5/6 internal); any
 * other value (incl. 3, observed live) -> 0 = NOT connected. */
#define DS_GPRS_CALL_NOT_CONNECTED 0u
#define DS_GPRS_CALL_ACTIVE_4      1u  /* payload[1]==1  -> internal 4 */
#define DS_GPRS_CALL_ACTIVE_5      10u /* payload[1]==10 -> internal 5 */
#define DS_GPRS_CALL_ACTIVE_6      11u /* payload[1]==11 -> internal 6 */

/* Returns true when a GPRS_CALL_STATUS state byte means "data call established". */
static inline bool ds_gprs_call_connected(uint8_t state) {
    return state == DS_GPRS_CALL_ACTIVE_4 || state == DS_GPRS_CALL_ACTIVE_5 ||
           state == DS_GPRS_CALL_ACTIVE_6;
}

/* Advance the FSM given: current phase, whether the last modem response
 * acknowledged the step, and a monotonic timestamp. Returns the phase to
 * surface. Pure: does not write anything. */
enum ds_phase ds_step(struct data_session_ctx *c, bool ack, uint64_t now_ms);

/* Reset for a new bounded attempt. */
void ds_reset(struct data_session_ctx *c, const char *apn, uint8_t profile_id);

/* Human-readable phase name (diagnostics, no secrets). */
const char *ds_phase_name(enum ds_phase p);

/* Feed a decoded REAL modem response into the FSM and determine whether the
 * current phase is actually satisfied. Unlike ds_step(ack=true), this version
 * uses the RESULT of the specific command (GEN result byte / GPRS call state /
 * PDP list state), so a generic GEN echo with a non-zero result never advances.
 * Returns the current phase (callers read ctx fields to know the outcome). */
enum ds_phase ds_feedback(struct data_session_ctx *c, bool success, uint64_t now_ms);

/* True if the FSM has reached a terminal phase (ACTIVE/REJECTED/FAILED). */
bool ds_terminal(const struct data_session_ctx *c);

#endif /* NUXEL_DATA_SESSION_H */
