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
#include <stddef.h>

enum ds_phase {
    DS_IDLE = 0,
    DS_SIM_CHECK,          /* confirm SIM READY */
    DS_NET_REGIST_CHECK,   /* read PS/data registration (GetDataRegState NET_REGIST) */
    DS_SET_SERVICE_DOMAIN, /* NET service domain CS_PS (SetServiceDomain sub=8) */
    DS_VERIFY_SERVICE_DOMAIN, /* require wire 1 (CS+PS), never wire 2 (CS only) */
    DS_SET_PREFERRED_NET,  /* NET preferred type LTE (SetPreferredNetType sub=10) */
    DS_VERIFY_NET_MODE,    /* read back the CP network-mode mask */
    DS_ENABLE_MOBILE_DATA, /* GPRS mobile data ON (SetMobileDataSetting sub=29) */
    DS_SYNC_PROFILE,       /* full profile sync w/ RAT (SyncProfileInfo sub=37) */
    DS_SET_DATA_PROFILE,   /* set APN/auth/protocol data profile */
    DS_IA_STATE_QUERY,     /* query actual PS registration before an IA detach */
    DS_PS_DETACH,          /* vendor DoDetachForIA: {0,0,4} */
    DS_PS_DETACHED_VERIFY, /* require actual detached PS status */
    DS_SET_LTE_ATTACH,     /* set LTE attach profile (required for LTE PS) */
    DS_MBIM_ATTACH_CONFIG, /* MBIM MS LTE Attach Config (CID 0x0A) via IpcTxRawIpc */
    DS_DEFINE_PDP,         /* define PDP context w/ APN */
    DS_ALWAYS_ON_PDN,      /* always-on PDN profile */
    DS_PS_REGIST_CHECK,    /* avoid redundant PS attach when already registered */
    DS_PS_ATTACH,          /* GPRS PS attach */
    DS_PS_REGIST_VERIFY,   /* re-query PS registration; gate data call on attach */
    DS_DATA_CALL,          /* activate PDP context */
    DS_GET_PDP_LIST,       /* query PDP context list (fetch IP config) */
    DS_WAIT_IP,            /* wait for rmnet + IP config */
    DS_RECOVER_PS_ATTACH,  /* restore PS after failed initial-attach transaction */
    DS_RECOVER_PS_REGIST,
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
    uint8_t        preferred_net; /* vendor PreferredNetType: 9=auto, 11=LTE */
    uint8_t        last_net_mode;
    bool           net_mode_valid;
    uint8_t        attach_cid;    /* GetAttachCid: RIL slot 0 -> 1, slot 1 -> 5 */
    uint8_t        attach_flag;   /* 1=profile zero, 3=always-on profile (CP) */
    uint8_t        auth_code;     /* DataAuth: 0=none, 1=PAP, 2=CHAP, 3=auto */
    uint8_t        pdp_type_wire; /* SetPdpContext payload[0] (FMT_TX_PDP_TYPE_*) */
    bool           mobile_data_on;
    bool           attached;
    bool           ps_state_valid;
    uint8_t        ps_control_state, ps_control_suspend;
    bool           ps_control_valid;
    bool           call_established;
    bool           ip_configured;
    bool           ps_attach_ack;
    bool           mobile_data_unsupported;
    bool           reattach_for_apn;
    bool           needs_ps_restore;
    enum ds_phase  failure_phase;
    uint16_t       failure_result;
    bool           failure_result_valid;
    uint8_t        expected_main, expected_sub, expected_type;
    bool           expected_valid;

    /* MBIM session sub-state for DS_MBIM_ATTACH_CONFIG. The vendor host opens
     * an MBIM session (OPEN primitive) before issuing the attach-config CID
     * command, then closes it. 0=OPEN,1=COMMAND,2=STATUS query,3=CLOSE. */
    uint8_t        mbim_substate;

    uint64_t       step_deadline_ms;
    uint64_t       phase_entered_ms;  /* monotonic ts when current phase began */

    /* Stage-06 response-decode state (populated from REAL modem responses only;
     * never from a frame write). These drive the strict FSM transitions. */
    uint16_t       last_gen_result;    /* complete LE result: 0x8000=success */
    uint8_t        last_gprs_call_state; /* GPRS_CALL_STATUS state byte */
    uint8_t        last_gprs_pdp_state;  /* GPRS_PDP_CONTEXT list state byte */
    /* NET_REGIST decoded registration states (authoritative RegState enum):
     * 0=off,1=registered,2=searching,3=denied,4=unknown,5=roaming. */
    uint8_t        last_cs_reg_state;
    uint8_t        last_ps_reg_state;
    uint8_t        last_reg_wire;
    uint8_t        last_reject_cause;   /* NET_REGIST payload[10], vendor reasonDenied */
    uint8_t        last_rat_wire;
    uint8_t        last_call_cause;
    bool           net_regist_valid;
    bool           gen_result_valid;   /* a GEN result has been correlated */
    bool           gprs_call_state_valid;
    bool           gprs_pdp_state_valid;
};

/* GetAttachCid @0x1e4500 loads GOT 0x3ad028. Its ELF relocation identifies
 * Feature::mRilIndex, NOT DataCallManager::mModelType. RIL slot 1 returns 5;
 * slot 0 returns 1. ds_detect is a board dual-SIM flag, not SIM presence.
 * The data profile id (ConvertProfileId(DEFAULT)==1) is a separate value. */
#define DS_ATTACH_CID 1u

/* AlwaysOnPdn wire payload[1] (IpcTxSetAlwaysOnPdn(bool, DataProfile, int)
 * @0x321550) is the *int* argument that DoAlwaysOnPdn() supplies as 1 (or 2
 * under an ESM-flag-zero network), NOT the attach CID and NOT a raw
 * DataProfile enum value. ConvertProfileId(DEFAULT)==1. */
#define DS_ALWAYS_ON_PDN_PROFILE 1u

/* Complete little-endian GEN result; do not discard its high byte. */
#define DS_GEN_RESULT_OK 0x8000u

enum ds_gen_status { DS_GEN_IGNORE, DS_GEN_ACCEPTED, DS_GEN_REJECTED,
                     DS_GEN_OPTIONAL_UNSUPPORTED };
void ds_expect(struct data_session_ctx *c, uint8_t main, uint8_t sub, uint8_t type);
enum ds_gen_status ds_gen_response(struct data_session_ctx *c, const uint8_t *p,
                                   size_t n);

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
