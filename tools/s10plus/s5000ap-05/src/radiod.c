/*
 * radiod.c — nuxel-radiod: native S5000AP SIPC5 radio service.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Responsibilities (this file):
 *   - lifecycle: open/modem endpoints, exclusive ownership, graceful shutdown
 *   - receive path: bounded per-endpoint buffer, incremental FMT reassembly
 *   - validation: sipc5_parse_fmt framing checks + knowledge-table classification
 *   - dispatch: async notifications to D-Bus signals; request/response
 *     correlation for authorized writes
 *   - device disconnect: detect, free, and (when CP is ONLINE) reopen
 *   - D-Bus: nl.nuxel.Radio1 (sd-bus), truthful state, never fabricated fields
 *   - structured, privacy-safe diagnostics to stderr (no payload bytes/IDs)
 *
 * TRUTH CONTRACT: CP state comes ONLY from the kernel's modem_state sysfs and
 * IOCTL_MODEM_STATUS via /dev/umts_boot0. Telephony fields (SIM/registration/
 * signal/bearer) are populated ONLY if a real FMT source exists; otherwise they
 * report not-supported/absent. We never send speculative commands.
 */
#define _GNU_SOURCE
#include "radiod.h"
#include "sipc5_proto_table.h"
#include "rfs_proto.h"
#include "rfs_respond.h"
#include "sipc5_fmt.h"
#include "ipc41_cmdmap.h"
#include "transport.h"
#include "fmt_tx.h"
#include "fmt_rx.h"
#include "data_session.h"
#include "mbim_tx.h"
#include "rfs_nv.h"
#include "efs_nv.h"
#include "oes_cert.h"
#include "sms_service.h"
#include "ims_service.h"
#include "ims_pdn.h"
#include "ims_iil.h"
#include "ims_iil_rx.h"
#include "iil_pdn.h"
#include "iil_auth.h"
#include "ims_sdm.h"
#include "ims_init.h"
#include "call_service.h"
#include "cellular_link.h"
#include "mobile_data.h"
#include "ims_sip_tr.h"
#include "ims_sip.h"   /* ims_base64_decode for the 401 AKA nonce (RAND||AUTN) */
#define MOBILE_PREFERENCE "/var/lib/nuxel-radio/mobile-data"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <errno.h>
#include <fcntl.h>
#include <pwd.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <systemd/sd-bus.h>
#include <systemd/sd-event.h>

/* Forward declaration (env-gated MBIM attach-config opt-in). */
static bool mbim_attach_enabled(void);

/* ------------------------------------------------------------------ */
/* constants                                                            */
/* ------------------------------------------------------------------ */
#define BOOT_NODE   "/dev/umts_boot0"
#define FMT_NODE    "/dev/umts_ipc0"
#define RFS_NODE    "/dev/umts_rfs0"
#define MODEM_STATE_SYSFS "/sys/devices/platform/10000.mif_pdata/modem_state"

/* IOCTL_MODEM_STATUS (legacy sipc ioctl, pinned) */
#define IOCTL_MODEM_STATUS 0x6F27
#define STATE_OFFLINE 0
#define STATE_ONLINE  4

/* reopen/backoff bounds */
#define REOPEN_INTERVAL_MS 2000u
#define RX_BUDGET_PER_WAKE 16

#define DEST_NAME "nl.nuxel.Radio1"
#define OBJ_PATH  "/nl/nuxel/Radio1"
#define IFACE_NAME "nl.nuxel.Radio1"

/* ------------------------------------------------------------------ */
/* global daemon state                                                  */
/* ------------------------------------------------------------------ */
struct radiod_endpoint {
    struct nuxel_sipc_dev dev;
    uint8_t  buf[RADIOD_RX_BUF];
    size_t   len;                 /* bytes currently buffered */
    bool     present;
    uint64_t last_reopen_ms;
};

struct radiod_request {
    bool     in_use;
    uint8_t  need_main;
    uint8_t  need_sub;
    uint8_t  need_type;
    uint8_t  msg_seq;             /* sequence we assigned on send */
    uint64_t deadline_ms;
};

struct radiod_ctx {
    struct radiod_endpoint fmt;
    struct radiod_endpoint rfs;
    struct radiod_diag_stats stats;
    struct radiod_obs ring[RADIOD_OBS_RING];
    unsigned ring_head;           /* next write index */
    unsigned ring_count;

    char     cp_state[24];
    int      cp_state_code;
    uint64_t cp_last_change_ms;
    bool     cp_online;

    bool     sim_present;
    /* Stage-06 native data-path: bounded, response-correlated driver. */
    struct data_session_ctx dsc;
    struct fmt_rx_ip ip;
    bool ip_received;
    bool mobile_enabled;
    struct mobile_stop mobile_stop;
    unsigned reconnect_attempts;
    uint64_t reconnect_at;
    struct cellular_link link;
    bool link_attempted, link_down_requested;
    uint64_t link_check_ms;
    struct fmt_rx_pdp_profiles profiles;
    bool profiles_received;
    struct fmt_rx_registration cs_registration;
    bool cs_registration_valid;
    uint8_t service_domain_wire;
    bool service_domain_valid;
    uint64_t status_next_ms;
    unsigned status_query;
    uint8_t sim_lock_type, sim_lock_key;
    bool sim_lock_valid;
    char home_plmn[6];
    char baseband[33];
    bool radio_state_valid, radio_on;
    unsigned oes_requests;
    struct sms_service sms;
    struct call_service calls;
    struct ims_service ims;
    struct ims_pdn ims_pdn;
    struct ims_init ims_init;
    bool ims_pdn_armed; /* opt-in IMS APN PDN drive */
    bool ims_pdn_up;     /* ims APN PDN actually established (carrier/gate) */
    bool ims_apn_present; /* ims APN string present in profile list (diag only) */
    struct iil_pdn iil_pdn;      /* IIL (IpcProtocol41Iil) IMS PDN driver */
    bool iil_pdn_armed;          /* opt-in IIL IMS PDN drive (--arm-data-path) */
    struct iil_auth iil_auth;    /* IIL IMS AKA relay (IsimAuth -> USIM -> ImsAuthResp) */
    struct ims_sdm ims_sdm;      /* modem IMS SDM readback (P-CSCF/domain/mode) */
    bool sip_param_sent;        /* SetSipParam fired once per P-CSCF discovery */
    struct ims_sip_tr sip_tr;   /* native SIP/IMS transport + registration FSM */
    bool sip_tr_open;           /* transport opened (P-CSCF + local IP known) */
    /* Native SIP 401 AKAv1-MD5 -> USIM AKA bridge state. When the SIP FSM
     * enters CHALLENGED, the 401 nonce is base64(RAND||AUTN); radiod decodes
     * it, submits the USIM AKA (SEC 5/9), and passes RES back via
     * ims_sip_tr_auth(). RES/RAND/AUTN are never logged. */
    bool sip_auth_pending;      /* USIM AKA in flight for the SIP 401 challenge */
    uint8_t sip_auth_last_seq;  /* SEC 5/9 request seq to correlate the result */
    uid_t control_uid, bridge_uid;
    sd_bus *data_bus;
    bool     data_path_armed;   /* explicit opt-in (flag / D-Bus) */
    bool     wrote_phase;       /* last phase already emitted a frame */
    bool     rfs_handshake_done;/* RFS boot handshake answered (CP advanced) */
    bool     sim_ready_seen;    /* SEC_PIN_STATUS=READY observed (protocol-backed) */

    struct radiod_request pending[RADIOD_MAX_PENDING];
    uint8_t  next_seq;

    bool     shutting_down;
    bool     write_enabled;       /* authorized-write capability (off by default) */

    sd_bus         *bus;
    sd_event       *loop;
    sd_event_source *fmt_src;
    sd_event_source *rfs_src;
    sd_event_source *tick_src;
    sd_event_source *sig_src[3];
};

static struct radiod_ctx g;
static void begin_data_session(const char *apn);
static int setup_session_bus(void);
static void radiod_sip_param_from_pcscf(const struct iil_pdn *p);
static void radiod_ims_iface_apply(const char *ims_ip, const char *pcscf);
static void radiod_ims_iface_down(void);

/* ------------------------------------------------------------------ */
/* time helpers                                                         */
/* ------------------------------------------------------------------ */
static uint64_t now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)(ts.tv_nsec / 1000000);
}

static uint64_t wall_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)(ts.tv_nsec / 1000000);
}

/* structured diagnostics: JSON line to stderr; never includes payload bytes */
static void diag(const char *event, const char *detail)
{
    fprintf(stderr, "{\"ts\":%llu,\"svc\":\"nuxel-radiod\",\"event\":\"%s\"%s%s}\n",
            (unsigned long long)wall_ms(), event, detail ? "," : "", detail ? detail : "");
}
static void diagf(const char *event, const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    diag(event, buf);
}

/* ------------------------------------------------------------------ */
/* CP state (kernel sysfs + ioctl). NEVER inferred from daemon liveness */
/* ------------------------------------------------------------------ */
static int read_text_file(const char *path, char *out, size_t cap)
{
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -errno;
    ssize_t r = read(fd, out, cap - 1);
    close(fd);
    if (r < 0) return -errno;
    out[r] = '\0';
    /* trim trailing newline(s) */
    while (r > 0 && (out[r-1] == '\n' || out[r-1] == '\r')) out[--r] = '\0';
    return 0;
}

static int ioctl_status(int *out_code)
{
    int fd = open(BOOT_NODE, O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
    if (fd < 0) {
        /* fall back to RDWR (some kernels gate status behind write-open) */
        fd = open(BOOT_NODE, O_RDWR | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
        if (fd < 0) return -errno;
    }
    int st = ioctl(fd, IOCTL_MODEM_STATUS);
    int e = errno;
    close(fd);
    if (st < 0) return -e;
    if (out_code) *out_code = st;
    return 0;
}

static const char *state_name_from_code(int c)
{
    switch (c) {
    case 0: return "OFFLINE";
    case 1: return "BOOTING";
    case 2: return "BYPASS";
    case 3: return "DUMP";
    case 4: return "ONLINE";
    case 5: return "CRASH_RESET";
    case 6: return "OFFLINE";
    case 9: return "CRASH_WATCHDOG";
    default: return "UNKNOWN";
    }
}

static void refresh_cp_state(void)
{
    char s[32] = "";
    int code = -1;
    const char *name = "UNKNOWN";

    /* Primary source: kernel sysfs mirror (cheap, no node open). The ioctl is
     * used only to obtain a numeric code when sysfs is unavailable, to avoid
     * needlessly opening /dev/umts_boot0 (which contends with a boot in progress
     * and clutters the kernel log). */
    if (read_text_file(MODEM_STATE_SYSFS, s, sizeof s) == 0 && s[0]) {
        name = s;
        /* derive a stable numeric mirror from the name for diagnostics */
        if (strcmp(s, "ONLINE") == 0) code = STATE_ONLINE;
        else if (strcmp(s, "OFFLINE") == 0) code = STATE_OFFLINE;
    } else if (ioctl_status(&code) == 0) {
        name = state_name_from_code(code);
    }

    bool online = (strcmp(name, "ONLINE") == 0);
    if (strcmp(g.cp_state, name) != 0 || g.cp_state_code != code) {
        snprintf(g.cp_state, sizeof g.cp_state, "%s", name);
        g.cp_state_code = code;
        g.cp_last_change_ms = wall_ms();
        diagf("cp_state_changed", "\"state\":\"%s\",\"code\":%d", name, code);
    }
    g.cp_online = online;
}

static void refresh_sim_state(void)
{
    /* ds_detect describes board dual-SIM configuration, never card presence.
     * 0x80 maps to LockType 16 / absent in vendor GenerateSimStatus. */
    g.sim_present = g.cp_online && g.sim_lock_valid && g.sim_lock_type != 0x80;
}

/* ------------------------------------------------------------------ */
/* event emission                                                       */
/* ------------------------------------------------------------------ */
static void emit_state_changed(const char *prop, const char *value)
{
    if (!g.bus) return;
    sd_bus_emit_signal(g.bus, OBJ_PATH, IFACE_NAME, "StateChanged",
                       "ss", prop, value);
}
static void emit_cp_reset(void)
{
    if (!g.bus) return;
    sd_bus_emit_signal(g.bus, OBJ_PATH, IFACE_NAME, "CpReset", "");
}

/* ------------------------------------------------------------------ */
/* framing / reassembly / dispatch                                      */
/* ------------------------------------------------------------------ */

/* Return a recovered IpcProtocol41 sub-command name for the telephony
 * families that Stage-06 targets. Returns NULL when the (main,sub) is not in
 * the recovered vocabulary (we do NOT invent a name). */
static const char *fmt_sub_name(uint8_t main, uint8_t sub)
{
    switch (main) {
    case IPC41_MAIN_SEC:
        switch (sub) {
        case IPC41_SEC_PIN_STATUS: return "SEC_PIN_STATUS";
        case IPC41_SEC_PHONE_LOCK: return "SEC_PHONE_LOCK";
        case IPC41_SEC_SIM_ICC_TYPE: return "SEC_SIM_ICC_TYPE";
        case IPC41_SEC_SIM_ICCID: return "SEC_SIM_ICCID";
        case IPC41_SEC_SIM_POWER: return "SEC_SIM_POWER";
        case IPC41_SEC_SIM_ON_OFF: return "SEC_SIM_ON_OFF";
        case IPC41_SEC_SIM_INFO: return "SEC_SIM_INFO";
        case IPC41_SEC_SIMAPPS_INFO: return "SEC_SIMAPPS_INFO";
        case IPC41_SEC_ATR_INFO: return "SEC_ATR_INFO";
        default: break;
        }
        break;
    case IPC41_MAIN_NET:
        switch (sub) {
        case IPC41_NET_SERVING_NETWORK: return "NET_SERVING_NETWORK";
        case IPC41_NET_REGIST: return "NET_REGIST";
        case IPC41_NET_POWERON_ATTACH: return "NET_POWERON_ATTACH";
        case IPC41_NET_PLMN_LIST: return "NET_PLMN_LIST";
        case IPC41_NET_PREF_PLMN: return "NET_PREF_PLMN";
        case IPC41_NET_MODE_SEL: return "NET_MODE_SEL";
        case IPC41_NET_CELL_INFO: return "NET_CELL_INFO";
        default: break;
        }
        break;
    case IPC41_MAIN_GPRS:
        switch (sub) {
        case IPC41_GPRS_DEFINE_PDP_CONTEXT: return "GPRS_DEFINE_PDP_CONTEXT";
        case IPC41_GPRS_PDP_CONTEXT: return "GPRS_PDP_CONTEXT";
        case IPC41_GPRS_PS: return "GPRS_PS";
        case IPC41_GPRS_IP_CONFIGURATION: return "GPRS_IP_CONFIGURATION";
        case IPC41_GPRS_CALL_STATUS: return "GPRS_CALL_STATUS";
        case IPC41_GPRS_PIN_CTRL: return "GPRS_PIN_CTRL";
        case IPC41_GPRS_LTE_ATTACH_APN_INFO: return "GPRS_LTE_ATTACH_APN_INFO";
        case IPC41_GPRS_SET_APN_INFO: return "GPRS_SET_APN_INFO";
        case IPC41_GPRS_MOBILE_DATA_STATUS: return "GPRS_MOBILE_DATA_STATUS";
        case IPC41_GPRS_SET_ALWAYS_ON_PDN: return "GPRS_SET_ALWAYS_ON_PDN";
        case IPC41_GPRS_SYNC_PROFILE_INFO: return "GPRS_SYNC_PROFILE_INFO";
        default: break;
        }
        break;
    case IPC41_MAIN_DISP:
        switch (sub) {
        case IPC41_DISP_ICON_INFO: return "DISP_ICON_INFO";
        case IPC41_DISP_HOMEZONE_INFO: return "DISP_HOMEZONE_INFO";
        case IPC41_DISP_RSSI_INFO: return "DISP_RSSI_INFO";
        case IPC41_DISP_EXT_ROAM_INFO: return "DISP_EXT_ROAM_INFO";
        case IPC41_DISP_USER_INDICATION: return "DISP_USER_INDICATION";
        default: break;
        }
        break;
    case IPC41_MAIN_PWR:
        switch (sub) {
        case IPC41_PWR_PHONE_PWR_UP: return "PWR_PHONE_PWR_UP";
        case IPC41_PWR_PHONE_STATE: return "PWR_PHONE_STATE";
        case IPC41_PWR_ENABLE_MODEM: return "PWR_ENABLE_MODEM";
        default: break;
        }
        break;
    case IPC41_MAIN_SYSTEM:
        if (sub == IPC41_SYSTEM_CP_CHANNEL_INFO) return "SYSTEM_CP_CHANNEL_INFO";
        break;
    default: break;
    }
    return NULL;
}

/* Response-decode decision kinds (see decode_gating_response). */
typedef enum {
    DS_FEEDBACK_IGNORE = 0,
    DS_FEEDBACK_OK     = 1,
    DS_FEEDBACK_FAIL   = 2,
} ds_feedback_kind;

static ds_feedback_kind decode_gating_response(const struct nuxel_sipc_fmt *f);

static const struct nuxel_fmt_observation *find_fmt_obs(uint8_t m, uint8_t s, uint8_t t)
{
    unsigned i;
    for (i = 0; i < NUXEL_NUM_FMT_OBS; i++)
        if (nuxel_fmt_observations[i].main_cmd == m &&
            nuxel_fmt_observations[i].sub_cmd == s &&
            nuxel_fmt_observations[i].cmd_type == t)
            return &nuxel_fmt_observations[i];
    return NULL;
}

static void record_obs(uint8_t ch, const struct nuxel_sipc_fmt *f, bool known)
{
    struct radiod_obs *o = &g.ring[g.ring_head];
    o->ts_ms = wall_ms();
    o->ch_id = ch;
    o->main_cmd = f->main_cmd;
    o->sub_cmd = f->sub_cmd;
    o->cmd_type = f->cmd_type;
    o->msg_seq = f->msg_seq;
    o->ack_seq = f->ack_seq;
    o->payload_len = (uint16_t)f->payload_len;
    o->known = known ? 1 : 0;
    g.ring_head = (g.ring_head + 1) % RADIOD_OBS_RING;
    if (g.ring_count < RADIOD_OBS_RING) g.ring_count++;
    if (!known) g.stats.unknown_cmd++;
}

static void resolve_pending(const struct nuxel_sipc_fmt *f)
{
    unsigned i;
    for (i = 0; i < RADIOD_MAX_PENDING; i++) {
        struct radiod_request *r = &g.pending[i];
        if (!r->in_use) continue;
        /* Correlate on (main,sub,type) only; msg_seq/ack_seq correlation is
         * UNKNOWN for the closed vocab, so we do not trust it. */
        if (r->need_main == f->main_cmd && r->need_sub == f->sub_cmd &&
            r->need_type == f->cmd_type) {
            r->in_use = false;
            diagf("response_matched", "\"main\":%u,\"sub\":%u,\"type\":%u",
                  f->main_cmd, f->sub_cmd, f->cmd_type);
            return;
        }
    }
}

static bool radiod_write_fmt(const struct fmt_tx_frame *f);

static bool sms_write(const struct fmt_tx_frame *f,uint8_t *sequence,void *user)
{
    (void)user;
    *sequence=g.next_seq;
    return g.cp_online && radiod_write_fmt(f);
}

static bool ims_write(const struct fmt_tx_frame *f,uint8_t *sequence,void *user)
{
    (void)user;
    *sequence=g.next_seq;
    return g.cp_online && radiod_write_fmt(f);
}

static bool ims_pdn_write(const struct fmt_tx_frame *f,uint8_t *sequence,void *user)
{
    (void)user;
    *sequence=g.next_seq;
    return g.cp_online && radiod_write_fmt(f);
}

static void ims_state_diag(const char *state,const char *reason,void *user)
{
    (void)user;
    diagf("ims_state","\"state\":\"%s\",\"reason\":\"%s\"",
          state ? state : "", reason ? reason : "");
    emit_state_changed("ImsState", state ? state : "");
}

static int sms_desktop_done(sd_bus_message *m,void *user,sd_bus_error *error)
{
    (void)user;(void)error;
    diag("sms_desktop_notification",sd_bus_message_is_method_error(m,NULL) ? "failed" : "accepted");
    return 0;
}

static void sms_desktop_notify(void)
{
    sd_bus_message *m=NULL;
    int r=sd_bus_message_new_method_call(g.bus,&m,"org.freedesktop.Notifications",
        "/org/freedesktop/Notifications","org.freedesktop.Notifications","Notify");
    if(r>=0)r=sd_bus_message_append(m,"susss","org.nuxel.Messages",0u,"mail-message-new",
        "New SMS","Open Messages to read it.");
    if(r>=0)r=sd_bus_message_open_container(m,'a',"s");
    if(r>=0)r=sd_bus_message_close_container(m);
    if(r>=0)r=sd_bus_message_open_container(m,'a',"{sv}");
    if(r>=0)r=sd_bus_message_close_container(m);
    if(r>=0)r=sd_bus_message_append(m,"i",-1);
    if(r>=0)r=sd_bus_call_async(g.bus,NULL,m,sms_desktop_done,NULL,3000000);
    if(r<0)diag("sms_desktop_notification","unavailable");
    sd_bus_message_unref(m);
}

static void sms_notify(uint32_t id,bool incoming,void *user)
{
    (void)user;
    struct sms_record record;
    if (!sms_store_get(&g.sms.store,id,&record)) return;
    diagf("sms_state","\"id\":%u,\"state\":\"%s\",\"error\":%d",id,record.state,record.error);
    if (g.bus) {
        sd_bus_emit_signal(g.bus,OBJ_PATH,IFACE_NAME,"SmsStateChanged","us",id,record.state);
        if (incoming) {
            sd_bus_emit_signal(g.bus,OBJ_PATH,IFACE_NAME,"SmsReceived","u",id);
            sms_desktop_notify();
        }
    }
}

/* Redacted submission-result metadata. Frame type, payload length,
 * ack_seq, decoded result, modem reference, correlation and resulting state
 * only -- never recipient, body, or PDU bytes. */
static void sms_result_diag(const struct sms_submit_result_diag *d,void *user)
{
    (void)user;
    diagf("sms_submit_result",
        "\"id\":%u,\"type\":%u,\"plen\":%u,\"ack\":%u,\"result\":%u,\"mr\":%u,\"correlated\":%s,\"state\":\"%s\",\"correlation\":\"%s\"",
        d->message_id, d->cmd_type, d->payload_len, d->ack_seq, d->result_code, d->modem_ref,
        d->correlated ? "true" : "false", d->state ? d->state : "", d->reason);
}

static void call_notify(uint8_t id,const char *state,bool incoming,void *user)
{
    (void)user;
    diagf("voice_call_state","\"id\":%u,\"state\":\"%s\"",id,state);
    if(g.bus) {
        sd_bus_emit_signal(g.bus,OBJ_PATH,IFACE_NAME,"CallStateChanged","us",(uint32_t)id,state);
        if(incoming)sd_bus_emit_signal(g.bus,OBJ_PATH,IFACE_NAME,"IncomingCall","u",(uint32_t)id);
    }
}

static void respond_oes_certificate(void)
{
    if (!g.write_enabled || !g.cp_online || g.oes_requests++ >= 3) return;
    struct oes_cert cert;
    int rc = oes_cert_load("/mnt/vendor/efs/DAK/sakeccert0.der", &cert);
    struct fmt_tx_frame reply;
    if (!fmt_tx_oes_confirm(&reply) || !radiod_write_fmt(&reply)) {
        oes_cert_free(&cert); diag("oes_confirm_write_failed", NULL); return;
    }
    if (rc) {
        if (fmt_tx_oes_certificate(&reply, 1, 0, NULL, 0))
            (void)radiod_write_fmt(&reply);
        diagf("oes_certificate_unavailable", "\"error\":%d", rc);
        return;
    }
    size_t sent = 0;
    uint8_t index = 0;
    while (sent < cert.len) {
        size_t n = cert.len - sent;
        if (n > FMT_TX_OES_CERT_CHUNK) n = FMT_TX_OES_CERT_CHUNK;
        if (!fmt_tx_oes_certificate(&reply, 0, index, cert.data+sent, n) ||
            !radiod_write_fmt(&reply)) break;
        sent += n; index++;
    }
    diagf("oes_certificate_transfer", "\"bytes\":%u,\"sent\":%u,\"complete\":%s",
          (unsigned)cert.len, (unsigned)sent, sent == cert.len ? "true" : "false");
    oes_cert_free(&cert);
}

static void dispatch_fmt(uint8_t ch, const struct nuxel_sipc_fmt *f)
{
    const struct nuxel_fmt_observation *ob = find_fmt_obs(f->main_cmd, f->sub_cmd, f->cmd_type);
    record_obs(ch, f, ob != NULL);
    resolve_pending(f);
    sms_service_receive(&g.sms,f);
    call_service_receive(&g.calls,f);
    ims_service_receive(&g.ims,f);
    /* IIL AKA relay: correlate the solicited SEC 5/9 USIM AKA result (type=2)
     * and forward RES/AUTS to the modem via IpcTxImsAuthResp. Secret material
     * (RES/CK/IK) is never logged. */
    if (g.iil_auth.pending && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->ack_seq == g.iil_auth.last_usim_seq &&
        f->main_cmd == IPC41_MAIN_SEC && f->sub_cmd == 9) {
        struct fmt_rx_usim_auth r;
        if (fmt_rx_usim_auth(f->payload, f->payload_len, &r)) {
            (void)iil_auth_usim_result(&g.iil_auth, &r, now_ms());
        }
    }

    /* Native SIP 401 AKA bridge: correlate the solicited SEC 5/9 USIM AKA
     * result to the SIP transport's outstanding challenge and hand RES to
     * ims_sip_tr_auth() so the authenticated REGISTER is sent. RES is never
     * logged; CK/IK are not forwarded here. */
    if (g.sip_auth_pending && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->ack_seq == g.sip_auth_last_seq &&
        f->main_cmd == IPC41_MAIN_SEC && f->sub_cmd == 9) {
        struct fmt_rx_usim_auth r;
        if (fmt_rx_usim_auth(f->payload, f->payload_len, &r) &&
            r.authenticated && r.res && r.res_len >= 4 && r.res_len <= 16) {
            g.sip_auth_pending = false;
            if (ims_sip_tr_auth(&g.sip_tr, r.res, r.res_len))
                diag("iil_sip_tr_auth_res", NULL);
            else
                diag("iil_sip_tr_auth_res_drop", NULL);
        } else {
            /* Auth failure or malformed result: drop the stale transaction so
             * a fresh 401 can drive a new USIM AKA on the next REGISTER. */
            g.sip_auth_pending = false;
            diag("iil_sip_tr_auth_fail", NULL);
        }
    }

    /* --- IIL (IpcProtocol41Iil) receive path ---
     * The stock IMS bearer/auth/registration/SMS events arrive on the IIL
     * endpoint (main=112) with the same main/sub/type offsets as FMT. Decode
     * and feed the IIL PDN/registration/auth/sms state machines. Auth material
     * (RAND/AUTN/RES/CK/IK) and PII are never logged. */
    if (f->main_cmd == IIL_MAIN_IIL) {
        struct iil_rx_event ev = {
            .msg_seq = f->msg_seq, .main_cmd = f->main_cmd, .sub_cmd = f->sub_cmd,
            .cmd_type = f->cmd_type, .payload = f->payload, .payload_len = f->payload_len
        };
        switch (f->sub_cmd) {
        case IIL_SUB_CONNECTED: {
            uint8_t cid = 0; bool attached = false;
            if (iil_rx_connected(&ev, &cid, &attached)) {
                iil_pdn_on_connected(&g.iil_pdn, &ev);
                /* The CP Connected event carries only a notify code (123),
                 * not a CID/IP; never treat it as bearer readiness. */
                diag("iil_connected", NULL);
            }
            break;
        }
        case IIL_SUB_PARAMETERS: {
            struct iil_pdn *p = &g.iil_pdn;
            unsigned before = p->pcscf_count;
            iil_pdn_on_parameters(p, &ev);
            diagf("iil_parameters",
                  "\"ip_ready\":%s,\"pcscf_ready\":%s,\"pcscf_count\":%u",
                  p->ip_ready ? "true" : "false",
                  p->pcscf_ready ? "true" : "false", p->pcscf_count);
            if (p->pcscf_count > before) {
                diag("iil_pcscf_present", NULL);
                /* Newly discovered P-CSCF: configure the modem's SIP stack. */
                if (!g.sip_param_sent) {
                    radiod_sip_param_from_pcscf(p);
                    g.sip_param_sent = true;
                }
            }
            break;
        }
        case IIL_SUB_ISIM_AUTH: {
            uint8_t rnd[16], autn[16];
            if (iil_rx_isim_auth(&ev, rnd, autn) &&
                iil_auth_challenge(&g.iil_auth, rnd, autn, now_ms())) {
                diag("iil_isim_auth_relay", NULL);
            } else {
                diag("iil_isim_auth_drop", NULL);
            }
            memset(rnd, 0, sizeof rnd); memset(autn, 0, sizeof autn);
            break;
        }
        case IIL_SUB_REGISTRATION: {
            int st = iil_rx_registration(&ev, NULL);
            if (st >= 0) {
                bool reg = (st == 1);      /* 1=REGISTERED, 2=REGISTERING */
                diagf("iil_registration", "\"status\":%d,\"registered\":%s",
                      st, reg ? "true" : "false");
                /* Trust an authoritative modem-relayed registration to drive
                 * the IMS service state (bearer-relayed REGISTERED). */
                if (reg) ims_service_native_registered(&g.ims, true);
            }
            break;
        }
        case IIL_SUB_PREFERENCE: {
            uint8_t fmt = 0;
            if (iil_rx_preference(&ev, &fmt))
                diagf("iil_preference", "\"sms_over_ip_fmt\":%u", fmt);
            break;
        }
        default:
            break;
        }
    }
    if ((f->main_cmd == IIL_MAIN_IIL || f->main_cmd == IIL_MAIN_SMS_RP) &&
        f->sub_cmd == IIL_SUB_SMS_INCOMING) {
        struct iil_rx_event ev = {
            .msg_seq = f->msg_seq, .main_cmd = f->main_cmd, .sub_cmd = f->sub_cmd,
            .cmd_type = f->cmd_type, .payload = f->payload, .payload_len = f->payload_len
        };
        const uint8_t *rp = NULL; size_t rp_len = 0;
        if (iil_rx_sms_incoming(&ev, &rp, &rp_len)) {
            /* IIL RP-DATA (3GPP RP PDU). Storage wiring for IMSSMS is a
             * separate inbound task; here we only surface its arrival. */
            diagf("iil_sms_incoming", "\"rp_len\":%u", (unsigned)rp_len);
        }
    }
    /* CP IMS mode changes are not registration notifications. The stock
     * registration/auth challenge source is the separate AP IMS/IIL endpoint.
     * SEC_IMS_AUTH is a solicited UICC result, not an unsolicited challenge. */
    /* Correlate GEN result to the IIL IMS PDN drive. The IIL GPRS builders
     * are acknowledged by the ordinary GEN channel with ack_seq == the shared
     * msg_seq we assigned. Only the active IIL phases await these acks. */
    if (f->main_cmd == IPC41_MAIN_GEN && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->payload_len == 5 && f->ack_seq == g.iil_pdn.last_write_seq) {
        struct fmt_rx_gen gen;
        if (fmt_rx_gen(f->payload, f->payload_len, &gen)) {
            diagf("iil_pdn_result", "\"sub\":%u,\"result\":%u", gen.sub, gen.result);
            iil_pdn_gen_result(&g.iil_pdn, gen.result, f->ack_seq);
        }
    }
    /* Correlate GEN result to the IMS PDN drive (distinct CID). */
    if (f->main_cmd == IPC41_MAIN_GEN && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->payload_len == 5 && f->ack_seq == g.ims_pdn.last_write_seq &&
        f->payload[0] == IPC41_MAIN_GPRS && f->payload[1] == g.ims_pdn.pending_sub &&
        f->payload[2] == FMT_TX_TYPE_NOTIFICATION) {
        struct fmt_rx_gen gen;
        if (fmt_rx_gen(f->payload, f->payload_len, &gen)) {
            diagf("ims_pdn_result","\"sub\":%u,\"result\":%u",gen.sub,gen.result);
            ims_pdn_gen_result(&g.ims_pdn, gen.result, f->ack_seq);
        }
    }
    /* Correlate the modem's direct GetDeviceCapa response (MISC sub=45
     * type=2) to the capability query. This is NOT a GEN ack; the modem
     * answers the request with a 2-byte VoiceDomainPref readback. */
    if (f->main_cmd == IPC41_MAIN_MISC && f->sub_cmd == 45u &&
        f->cmd_type == IPC41_TYPE_RESPONSE && f->ack_seq == g.ims_init.last_write_seq) {
        ims_init_capa_response(&g.ims_init, f->ack_seq);
    }
    /* Correlate a GEN result to the last SDM GET. The modem answers SDM
     * readbacks via the ordinary GEN channel (0x8001 reject here), not a
     * direct value; advance on reject so the surface never retry-storms. */
    if (f->main_cmd == IPC41_MAIN_GEN && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->payload_len == 5 && f->ack_seq == g.ims_sdm.last_write_seq) {
        struct fmt_rx_gen gen;
        if (fmt_rx_gen(f->payload, f->payload_len, &gen)) {
            if (ims_sdm_gen_result(&g.ims_sdm, gen.result, f->ack_seq))
                diagf("ims_sdm_reject", "\"sub\":%u,\"result\":%u", gen.sub, gen.result);
        }
    }
    /* IMS SDM readback capture. Direct type=2 RESPONSE at (main=10) for the
     * SDM sub we queried; capture the modem's authoritative provisioned
     * value (never fabricated). Values are only used to drive downstream
     * provisioning; they are not logged verbatim (P-CSCF/domain redacted). */
    if (f->main_cmd == IPC41_MAIN_MISC && f->cmd_type == IPC41_TYPE_RESPONSE &&
        (f->sub_cmd == 26u || f->sub_cmd == 27u || f->sub_cmd == 28u ||
         f->sub_cmd == 32u || f->sub_cmd == 34u)) {
        if (ims_sdm_receive(&g.ims_sdm, f->sub_cmd, f->ack_seq,
                            f->payload, f->payload_len)) {
            diagf("ims_sdm_readback", "\"sub\":%u,\"complete\":%s",
                  f->sub_cmd, g.ims_sdm.phase == IMS_SDM_DONE ? "true" : "false");
            if (g.ims_sdm.phase == IMS_SDM_DONE) {
                /* Redacted summary: presence flags only, never the values. */
                diagf("ims_sdm_done",
                      "\"pcscf\":%s,\"domain\":%s,\"mode\":%s,\"smsoverip\":%s,\"smsfmt\":%s",
                      g.ims_sdm.pcscf_valid ? "true" : "false",
                      g.ims_sdm.domain_valid ? "true" : "false",
                      g.ims_sdm.mode_valid ? "true" : "false",
                      g.ims_sdm.smsoverip_valid ? "true" : "false",
                      g.ims_sdm.smsfmt_valid ? "true" : "false");
            }
        }
    }
    /* Match both sequence and the outstanding command, including after
     * the 8-bit sequence wraps during status polling. */
    if (f->main_cmd == IPC41_MAIN_GEN && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->payload_len == 5 && f->ack_seq == g.ims_init.last_write_seq) {
        struct fmt_rx_gen gen;
        if (fmt_rx_gen(f->payload,f->payload_len,&gen) && gen.type==3 &&
            ((g.ims_init.phase==IMS_INIT_WAIT_ACK && gen.main==10 && gen.sub==45) ||
             (g.ims_init.phase==IMS_INIT_WAIT_VOLTE_STATE && gen.main==8 && gen.sub==52)))
            ims_init_gen_result(&g.ims_init,gen.result,f->ack_seq);
    }
    /* IMS PDN CID-2 attachment evidence. The IMS context is confirmed by an
     * actual GPRS_CALL_STATUS(cid=2, state active) or GPRS_PDP_CONTEXT list
     * entry (cid=2, state active). This is the missing feed that moves the
     * IMS PDN FSM from VERIFY to ACTIVE. Never fabricates; only mirrors a
     * real modem notification for the distinct IMS CID. */
    if (f->main_cmd == IPC41_MAIN_GPRS && f->sub_cmd == IPC41_GPRS_CALL_STATUS &&
        f->cmd_type == IPC41_TYPE_NOTIFICATION && f->payload_len >= 9 &&
        f->payload[0] == IMS_PDN_CID) {
        bool attached = ds_gprs_call_connected(f->payload[1]);
        ims_pdn_report_cid(&g.ims_pdn, IMS_PDN_CID, attached);
        diagf("ims_pdn_call_status", "\"cid\":%u,\"state\":%u,\"attached\":%s",
              f->payload[0], f->payload[1], attached ? "true" : "false");
    }
    if (f->main_cmd == IPC41_MAIN_GPRS && f->sub_cmd == IPC41_GPRS_PDP_CONTEXT &&
        f->cmd_type == IPC41_TYPE_RESPONSE) {
        uint8_t ims_state = 0;
        if (fmt_rx_pdp_state(f->payload, f->payload_len, IMS_PDN_CID, &ims_state)) {
            bool attached = ds_gprs_call_connected(ims_state);
            ims_pdn_report_cid(&g.ims_pdn, IMS_PDN_CID, attached);
            diagf("ims_pdn_pdp_context", "\"cid\":%u,\"state\":%u,\"attached\":%s",
                  IMS_PDN_CID, ims_state, attached ? "true" : "false");
        }
    }
    if (f->main_cmd == IPC41_MAIN_GPRS &&
        f->sub_cmd == IPC41_GPRS_IP_CONFIGURATION &&
        f->cmd_type == IPC41_TYPE_NOTIFICATION) {
        struct fmt_rx_ip ip;
        if (fmt_rx_ip(f->payload, f->payload_len, &ip) && ip.cid == IMS_PDN_CID) {
            ims_pdn_report_ip(&g.ims_pdn, &ip);
            char ims_ip[64] = {0}, pc[64] = {0};
            if (ip.ipv6_valid) inet_ntop(AF_INET6, ip.ipv6, ims_ip, sizeof ims_ip);
            else if (ip.ipv4_valid) inet_ntop(AF_INET, ip.ipv4, ims_ip, sizeof ims_ip);
            if (ip.pcscf6_count) inet_ntop(AF_INET6, ip.pcscf6[0], pc, sizeof pc);
            else if (ip.pcscf4_count) inet_ntop(AF_INET, ip.pcscf4[0], pc, sizeof pc);
            /* IMS bearer address + P-CSCF are network config, NOT secret. */
            diagf("ims_context", "\"ip_ready\":%s,\"pcscf_count\":%u,"
                  "\"ims_ip\":\"%s\",\"pcscf\":\"%s\"",
                  g.ims_pdn.ip_ready ? "true" : "false",
                  ip.pcscf4_count + ip.pcscf6_count, ims_ip, pc);
            /* Attach the CID-2 IMS bearer to rmnet1 so the native SIP
             * transport can actually source traffic from the IMS IPv6. */
            if (g.write_enabled && ims_ip[0])
                radiod_ims_iface_apply(ims_ip, pc);
        }
    }
    mobile_stop_receive(&g.mobile_stop,f);
    if (f->main_cmd == 13 && f->sub_cmd == 1 && f->cmd_type == 2) {
        struct fmt_rx_pdp_profiles profiles;
        if (fmt_rx_pdp_profiles(f->payload,f->payload_len,&profiles)) {
            g.profiles = profiles; g.profiles_received = true;
            /* Detect the ims APN PDN. A dedicated ims APN profile present in
             * the live profile definitions is evidence of an IMS PDN, NOT a
             * substitute for modem-confirmed IMS registration. */
            g.ims_apn_present = false;
            for (unsigned i = 0; i < profiles.count; i++) {
                const char *a = profiles.profile[i].apn;
                /* KPN 204-08 IMS APN is the well-known "ims" (TS 23.003); accept
                 * both the bare "ims" and any FQDN form for detection. APN-string
                 * presence is NOT proof the IMS PDN bearer is established; it
                 * must never gate registration. ims_pdn_up is driven only by
                 * ims_pdn_active() after real CID-2 attachment. */
                if (!strncmp(a, "ims", 3) && (a[3] == '\0' || a[3] == '.'))
                    g.ims_apn_present = true;
            }
            char apns[FMT_RX_PDP_PROFILES*102] = {0};
            size_t apn_off = 0;
            for (unsigned i = 0; i < profiles.count && apn_off < sizeof(apns)-2; i++) {
                size_t l = strlen(profiles.profile[i].apn);
                if (apn_off) apns[apn_off++] = ',';
                if (l > sizeof(apns)-apn_off-1) l = sizeof(apns)-apn_off-1;
                memcpy(apns+apn_off, profiles.profile[i].apn, l);
                apn_off += l;
            }
            apns[apn_off] = 0;
            diagf("pdp_definitions", "\"count\":%u,\"ims_apn_present\":%s,\"apns\":\"%s\"",
                  profiles.count, g.ims_apn_present ? "true" : "false", apns);
        } else diagf("pdp_definitions_invalid", "\"length\":%u", f->payload_len);
    }
    /* Reply only to the CP's actual startup request. Transfer the existing
     * device certificate unchanged, as OesManager::OnOesDrkCpInfo does. */
    if (f->main_cmd == 38 && f->sub_cmd == 1 && f->cmd_type == 1 && f->payload_len == 4)
        respond_oes_certificate();

    /* Cache the CP's lock indication, including transitions away from unlocked.
     * IpcRxSecPinStatus/ConvertLockType map 0 and 0x82 to no lock. */
    if (f->main_cmd == IPC41_MAIN_SEC && f->sub_cmd == IPC41_SEC_PIN_STATUS &&
        f->payload_len == 2) {
        g.sim_lock_type = f->payload[0]; g.sim_lock_key = f->payload[1];
        g.sim_lock_valid = true;
        g.sim_ready_seen = fmt_rx_sim_ready(f->payload, f->payload_len);
        refresh_sim_state();
        if(!g.sim_ready_seen && g.dsc.phase==DS_ACTIVE) {
            g.data_path_armed=false;g.dsc.ip_configured=false;g.ip_received=false;
            g.dsc.net_regist_valid=false;g.link_down_requested=true;
            g.dsc.phase=DS_IDLE;
            /* A startup notification can arrive after the first bearer.
             * Confirm SIM and registration promptly through the existing
             * read-only query sequence, rather than waiting its idle minute.
             * Do not reinterpret the notification as unlocked/registered. */
            g.status_query=0;g.status_next_ms=now_ms()+1000;
            g.reconnect_at=now_ms()+30000;
        }
        diagf("sim_lock_state", "\"type\":%u,\"key\":%u,\"unlocked\":%s",
              g.sim_lock_type, g.sim_lock_key, g.sim_ready_seen ? "true" : "false");
    }
    if (f->main_cmd == 10 && f->sub_cmd == 2 && f->cmd_type == IPC41_TYPE_RESPONSE) {
        if (fmt_rx_sim_network(f->payload, f->payload_len, g.home_plmn))
            diagf("sim_home_network", "\"plmn\":\"%s\"", g.home_plmn);
        else diag("sim_home_network", "\"plmn\":\"unknown\"");
        /* The existing subscription recognizer explicitly identifies 204-08.
         * Its configured two-digit MNC is not inferred from IMSI length.
         * Never retain the raw IMSI or log the derived private/public identity. */
        if (!strcmp(g.home_plmn,"20408") && f->payload_len>1)
            ims_identity_from_usim(&g.ims.identity,f->payload+1,f->payload_len-1,2);
        else ims_identity_clear(&g.ims.identity);
        diagf("ims_usim_identity", "\"ready\":%s",g.ims.identity.ready ? "true" : "false");
    }
    if (f->main_cmd == 10 && f->sub_cmd == 1 && f->cmd_type == IPC41_TYPE_RESPONSE &&
        fmt_rx_baseband(f->payload, f->payload_len, g.baseband))
        diagf("baseband_version", "\"version\":\"%s\"", g.baseband);
    /* IpcRxPwrState @0x3400e8, payload[0] 2..4 -> ON, 1 -> OFF. */
    if (f->main_cmd == 1 && f->sub_cmd == 7 && f->cmd_type == IPC41_TYPE_NOTIFICATION &&
        f->payload_len >= 1 && f->payload[0] >= 1 && f->payload[0] <= 4) {
        g.radio_state_valid = true; g.radio_on = f->payload[0] >= 2;
        diagf("radio_power_state", "\"on\":%s,\"wire_state\":%u",
              g.radio_on ? "true" : "false", f->payload[0]);
        emit_state_changed("RadioState", g.radio_on ? "on" : "off");
    }

    /* Feed the Stage-06 data-session FSM. We now honour the REAL decoded
     * result of each modem response (GEN result byte, GPRS_CALL_STATUS state,
     * GPRS_PDP_CONTEXT state). A generic GEN echo with non-zero result, or a
     * "not connected" call-state, is treated as a FAILURE and blocks advance.
     * This is the core Stage-06 correction: we no longer advance on a bare ACK. */
    ds_feedback_kind k = decode_gating_response(f);
    if (g.data_path_armed && g.dsc.phase != DS_IDLE) {
        if (k == DS_FEEDBACK_OK) {
            /* Hold PS_ATTACH for a short dwell so the asynchronous PS attach
             * completes before SetPdpContext(ACTIVATE). Bounded: only applies to
             * that phase and only before the dwell elapses. */
            if (g.dsc.phase == DS_PS_ATTACH &&
                g.dsc.phase_entered_ms &&
                now_ms() - g.dsc.phase_entered_ms < 3000u) {
                /* dwell: do not advance yet */
            } else {
                enum ds_phase prev = g.dsc.phase;
                enum ds_phase next = ds_step(&g.dsc, true, now_ms());
                diagf("data_session_ack", "\"phase\":\"%s\",\"next\":\"%s\"",
                      ds_phase_name(prev), ds_phase_name(next));
                if (next != prev) {
                    g.wrote_phase = false;
                    g.dsc.phase_entered_ms = now_ms();
                }
            }
        } else if (k == DS_FEEDBACK_FAIL) {
            enum ds_phase prev = g.dsc.phase;
            diagf("data_session_reject",
                  "\"phase\":\"%s\",\"gen_result\":%u,\"call_state\":%u,\"pdp_state\":%u",
                  ds_phase_name(prev), g.dsc.last_gen_result,
                  g.dsc.last_gprs_call_state, g.dsc.last_gprs_pdp_state);
            enum ds_phase next = ds_feedback(&g.dsc, false, now_ms());
            g.wrote_phase = false;
            g.dsc.phase_entered_ms = now_ms();
            (void)next;
        }
    }
    /* We do not decode telephony semantics (UNKNOWN). We DO surface the
     * existence and classification of every message as a diagnostic. */
    const char *subname = fmt_sub_name(f->main_cmd, f->sub_cmd);
    diagf("fmt_rx", "\"ch\":%u,\"main\":%u,\"sub\":%u,\"type\":%u,\"plen\":%u,\"name\":\"%s\",\"family\":\"%s\",\"seq\":%u,\"ack\":%u",
          ch, f->main_cmd, f->sub_cmd, f->cmd_type, f->payload_len,
          subname ? subname : "UNKNOWN", ipc41_main_name(f->main_cmd),f->msg_seq,f->ack_seq);

    /* SEC_SIMAPPS_INFO: authoritative, identifier-free application inventory.
     * Classify USIM/ISIM/CSIM by 3GPP AID prefix. Never logs the full AID. */
    if (f->main_cmd == IPC41_MAIN_SEC && f->sub_cmd == IPC41_SEC_SIMAPPS_INFO &&
        (f->cmd_type == IPC41_TYPE_RESPONSE || f->cmd_type == IPC41_TYPE_NOTIFICATION)) {
        struct fmt_rx_sim_apps apps;
        if (fmt_rx_sim_apps(f->payload, f->payload_len, &apps))
            diagf("sim_apps", "\"count\":%u,\"usim\":%u,\"isim\":%u,\"csim\":%u",
                  apps.count, apps.usim, apps.isim, apps.csim);
        else
            diag("sim_apps_invalid", NULL);
    }

    /* REDACTED-SAFE payload diagnostics: dump hex ONLY for state-enum
     * messages that carry no subscriber/device identifier (no IMSI/ICCID/
     * IMEI/MSISDN). SEC_PIN_STATUS, SEC_SIM_ICC_TYPE, NET_REGIST,
     * NET_SERVING_NETWORK, GPRS_PIN_CTRL, DISP_* are safe. We explicitly
     * EXCLUDE SEC_SIM_ICCID (sub=12) and IMEI family. */
    if ((f->main_cmd == IPC41_MAIN_SEC &&
         (f->sub_cmd == IPC41_SEC_PIN_STATUS ||
          f->sub_cmd == IPC41_SEC_SIM_ICC_TYPE ||
          f->sub_cmd == IPC41_SEC_SIMAPPS_INFO ||
          f->sub_cmd == IPC41_SEC_SIM_ON_OFF)) ||
        (f->main_cmd == IPC41_MAIN_NET &&
         (f->sub_cmd == IPC41_NET_REGIST ||
          f->sub_cmd == IPC41_NET_SERVING_NETWORK ||
          f->sub_cmd == IPC41_NET_MODE_SEL ||
          f->sub_cmd == IPC41_NET_POWERON_ATTACH)) ||
        (f->main_cmd == IPC41_MAIN_GPRS &&
         (f->sub_cmd == IPC41_GPRS_PIN_CTRL ||
          f->sub_cmd == IPC41_GPRS_PDP_CONTEXT ||
          f->sub_cmd == IPC41_GPRS_IP_CONFIGURATION ||
          f->sub_cmd == IPC41_GPRS_CURRENT_SESSION_DATA_CTR ||
          f->sub_cmd == IPC41_GPRS_CALL_STATUS)) ||
        (f->main_cmd == IPC41_MAIN_GEN) ||
        f->main_cmd == IPC41_MAIN_DISP ||
        (f->main_cmd == IPC41_MAIN_MISC && f->sub_cmd == 82)) {
        char hex[256];
        unsigned k, n = 0;
        for (k = 0; k < f->payload_len && k < 32; k++)
            n += snprintf(hex + n, sizeof hex - n, "%02x", f->payload[k]);
        hex[n] = 0;
        diagf("fmt_payload", "\"main\":%u,\"sub\":%u,\"hex\":\"%s\"",
              f->main_cmd, f->sub_cmd, hex);
    }
}

/*
 * Raw (non-FMT) channels: RFS (245) and RAW misc channels deliver an OPAQUE
 * payload (the kernel strips only the SIPC5 link header). We MUST NOT parse
 * these as SIPC FORMAT messages. Their internal opcode family is UNKNOWN
 * (closed), so we only count them and record redacted metadata (channel,
 * length, first-byte class) with NO payload contents.
 */
/*
 * RFS raw request (recovered contract, SOURCE-BACKED this round; see
 * rfs_respond.h and reports/S5000AP-06-LTE-REAL-LIVE.md). The CP sends:
 *   [u32 total_len][u8 op][u8 seq][u16 reserved][u32 path_len][path+\0]
 * and expects a fixed 14-byte response on the same channel:
 *   [u32 result][u8 op][u8 seq][u16 reserved][u32 detail]
 *
 * We now parse the full request, apply a fail-closed policy (only the
 * boot-stage RFS_UNLINK_FILE("DELETE_ALL_VIS") no-op marker is answered with
 * success), and write the correct AP->CP response so the CP can advance past
 * the NV/RFS init handshake toward SIM attach. We NEVER execute filesystem
 * operations and NEVER log the path or any identifier.
 */
/*
 * EFS-NV serving path (role of the vendor cbd / Nv::ProcessNVRead / Nv::ProcessNvWrite).
 *
 * The CP supplies (offset,length) in the RFS NV request — the AP NEVER invents
 * them (round-40 independent disasm: the AP applies a bounded lseek/read/write
 * into /mnt/vendor/efs/nv_data.bin using the CP's own offset+length). This
 * helper performs exactly that, against the canonical image, with the existing
 * bounded + fail-closed efs_nv backend (no blind seek, no offset fabrication).
 *
 * SAFETY:
 *   - NV_READ  is served from a read-only open of the canonical image, bounded.
 *   - NV_WRITE_ALL is served ONLY when the daemon was started with explicit
 *     write authorization (--write-enable) AND the operator armed NV writes via
 *     NUXEL_NV_WRITE=1. It refuses a write unless that is set (fail-closed),
 *     recomputes the MD5 sidecar only after a full bounded write succeeds, and
 *     never logs payload bytes / item ids.
 */
#define RADIOD_EFS_NV_PATH "/mnt/vendor/efs/nv_data.bin"

static bool nv_write_armed(void)
{
    const char *p = getenv("NUXEL_NV_WRITE");
    return p && (!strcasecmp(p, "1") || !strcasecmp(p, "on") ||
                 !strcasecmp(p, "true") || !strcasecmp(p, "yes"));
}

/* Serve an RFS NV transaction. Returns true when a response was fully built in
 * `out`/`out_cap` (and `*out_len` set); false means "answer fail-closed" and the
 * caller falls back to the error envelope. Never fabricates offset/length. */
static bool serve_rfs_nv(const struct rfs_nv_item *item, uint8_t op,
                         uint8_t *out, size_t out_cap, size_t *out_len)
{
    struct stat st;
    uint8_t *val = NULL;
    int fd = -1;

    if (!item || !item->valid) return false;

    /* READ path: bounded read from the canonical image, then a 15+N read reply. */
    if (op == RFS_OP_NV_READ) {
        if (item->length > EFS_NV_MAX_VALUE) return false;
        fd = open(RADIOD_EFS_NV_PATH, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return false;
        if (fstat(fd, &st) != 0 || st.st_size <= 0) { close(fd); return false; }
        val = malloc(item->length ? item->length : 1u);
        if (!val) { close(fd); return false; }
        enum efs_nv_result r = efs_nv_read_at(fd, item->offset, item->length,
                                              (uint64_t)st.st_size, val);
        close(fd);
        if (r != EFS_NV_OK) { free(val); return false; }
        size_t n = rfs_nv_read_response_build(item->seq, 0 /*OK*/,
                                              item->offset, item->length, val,
                                              out, out_cap);
        free(val);
        if (n == 0) return false;
        *out_len = n;
        return true;
    }

    /* WRITE path: only with explicit write auth + arm, offset/length from the CP,
     * bounded + fsync, MD5 sidecar recomputed after success. */
    if (op == RFS_OP_NV_WRITE_ALL) {
        if (!g.write_enabled || !nv_write_armed()) return false;
        if (item->length > EFS_NV_MAX_VALUE) return false;
        fd = open(RADIOD_EFS_NV_PATH, O_RDWR | O_CLOEXEC);
        if (fd < 0) return false;
        if (fstat(fd, &st) != 0 || st.st_size <= 0) { close(fd); return false; }
        enum efs_nv_result r = efs_nv_write_at(fd, item->offset, item->length,
                                               (uint64_t)st.st_size,
                                               item->data, true);
        close(fd);
        if (r != EFS_NV_OK) return false;
        /* Recompute the MD5 sidecar exactly like Nv::UpdateChecksumFile. */
        enum efs_nv_result m = efs_nv_update_checksum_sidecar(
            RADIOD_EFS_NV_PATH, RADIOD_EFS_NV_PATH ".md5");
        if (m != EFS_NV_OK) {
            /* The write succeeded but the checksum sidecar did not. Report a
             * genuine failure so the CP can retry; do not claim success. */
            return false;
        }
        size_t n = rfs_nv_response_build(item->seq, 0 /*OK*/, item->offset,
                                         item->length, out);
        if (n == 0) return false;
        *out_len = n;
        return true;
    }

    return false;
}

static void dispatch_rfs(uint8_t ch, const uint8_t *data, size_t len)
{
    g.stats.raw_frames++;
    g.stats.raw_bytes += (uint64_t)len;

    /* FULL RFS request parse (recovered contract, see rfs_respond.h). */
    struct rfs_request req;
    enum rfs_request_parse_result pr = rfs_request_parse(data, len, &req);
    if (pr != RFS_REQ_OK) {
        /* Not a valid RFS request: could be opaque bulk or malformed. Count
         * and no-op. We never write a response to an unparseable record. */
        g.stats.raw_rx_unclassified++;
        return;
    }

    g.stats.rfs_ops++;
    if (req.op == RFS_OP_UNLINK_FILE) g.stats.rfs_destructive++;

    /* For NV ops the `param` word is the NV item id (ProcessNVRead reads the
     * u32 at offset 6 as the item id and the u32 at offset 10 as the length).
     * Surface it read-only so the CP's exact NV item IDs become observable. */
    diagf("rfs_rx", "\"ch\":%u,\"op\":%u,\"opname\":\"%s\",\"seq\":%u,"
          "\"special\":%d,\"rlen\":%u,\"item_id\":%u",
          ch, req.op, rfs_op_name(req.op), req.seq,
          req.special_delete_all_vis ? 1 : 0, req.total_len, req.param);

    /* RECOVERED NV-TRANSACTION HANDLING (rfs_nv.h): for NV ops the request
     * body carries [u8 op][u8 seq][u32 reserved][u32 offset][u32 length]
     * [data...] (Nv::ProcessNvWrite @0x1d8550 dereferences offset @+6 and
     * length @+10). The offset/length are ALWAYS supplied by the CP; we never
     * invent them. */
    uint32_t nv_offset = 0, nv_length = 0;
    bool nv_parsed = false;
    struct rfs_nv_item nvi;
    memset(&nvi, 0, sizeof nvi);
    if (req.op == RFS_OP_NV_READ || req.op == RFS_OP_WRITE_FILE ||
        req.op == RFS_OP_NV_WRITE_ALL || req.op == RFS_OP_NV_RESTORE ||
        req.op == RFS_OP_NV_BUFFERING || req.op == RFS_OP_NV_BUFFER_START_END) {
        enum rfs_nv_parse_result npr = rfs_nv_item_parse(data, len, &nvi);
        if (npr == RFS_NV_PARSE_OK) {
            nv_offset = nvi.offset;
            nv_length = nvi.length;
            nv_parsed = true;
        }
    }

    diagf("rfs_nv", "\"ch\":%u,\"op\":%u,\"nv_parsed\":%d,"
          "\"offset\":%u,\"length\":%u",
          ch, req.op, nv_parsed ? 1 : 0, nv_offset, nv_length);

    /* POLICY GATE: default fail-closed. The no-op boot marker is answered with
     * success; NV_READ/NV_WRITE_ALL are served against the canonical nv_data.bin
     * using the CP-supplied (offset,length). A write additionally requires
     * explicit write auth + NUXEL_NV_WRITE arm. Everything else stays refused. */
    int32_t detail = 0;
    int res = rfs_response_policy(&req, &detail);

    /* Response bytes. NV read responses append read-back data (15+length); the
     * vendor clamps length to 0x80000, so allocate up to that bound. */
    uint8_t *nvbuf = NULL;
    size_t nvcap = 0, n = 0;
    bool served = false;

    if (nv_parsed && (req.op == RFS_OP_NV_READ || req.op == RFS_OP_NV_WRITE_ALL)) {
        size_t needed = (size_t)RFS_NV_RESP_LEN;
        if (req.op == RFS_OP_NV_READ) {
            if (nv_length > 0x80000u - RFS_NV_RESP_LEN) { needed = 0; }
            else { needed += (size_t)nv_length; }
        }
        if (needed >= RFS_NV_RESP_LEN && needed <= (RFS_NV_RESP_LEN + 0x80000u)) {
            nvbuf = malloc(needed);
            if (nvbuf) {
                nvcap = needed;
                served = serve_rfs_nv(&nvi, req.op, nvbuf, nvcap, &n);
            }
        }
    }

    /* Fallback envelope when serving was unavailable/unauthorized. */
    uint8_t fallback[RFS_NV_RESP_LEN];
    if (!(served && n > 0)) {
        if (nv_parsed) {
            n = rfs_nv_response_build(req.seq, 1u /*failure*/, 0u, 0u, fallback);
        } else {
            n = rfs_response_build(req.op, req.seq, res, detail, fallback);
        }
    }

    const uint8_t *payload = (served && nvbuf) ? nvbuf : fallback;

    /* Write the response to /dev/umts_rfs0. This is the AP->CP answer the CP
     * is waiting for. Writes are bounded (14/15/15+N bytes). */
    enum nuxel_io_status st = nuxel_dev_write(&g.rfs.dev, payload, n);
    if (st == NUXEL_IO_OK) {
        g.stats.rfs_responses++;
        g.stats.tx_frames++;
        g.rfs_handshake_done = true;
        diagf("rfs_tx", "\"op\":%u,\"res\":%d,\"len\":%zu,\"served\":%d",
              req.op, served ? 0 : res, n, served ? 1 : 0);
    } else {
        g.stats.rfs_resp_errors++;
        diagf("rfs_tx_fail", "\"op\":%u,\"st\":\"%s\"",
              req.op, nuxel_io_status_name(st));
    }
    free(nvbuf);
}

/* ------------------------------------------------------------------ */
/* FMT transmit path (bounded, opt-in, response-correlated)            */
/* ------------------------------------------------------------------ */

/* Write ONE serialized FMT frame to /dev/umts_ipc0. Returns true only when
 * the kernel accepted the full write. Never fabricates success. */
static bool radiod_write_fmt(const struct fmt_tx_frame *f)
{
    if (!g.write_enabled) {
        diag("fmt_tx_refused", "\"reason\":\"write capability disabled\"");
        return false;
    }
    if (!f || f->len < 7 || f->len > FMT_TX_MAX_FRAME) return false;
    /* IpcProtocol41::SetMsgSequence @0x316860 writes byte 2. The vendor
     * GenerateMsgSequence @0x314cc0 cycles 0..254, reserving 255. */
    uint8_t frame[FMT_TX_MAX_FRAME];memcpy(frame,f->buf,f->len);frame[2]=g.next_seq;
    enum nuxel_io_status st = nuxel_dev_write(&g.fmt.dev, frame, f->len);
    if (st == NUXEL_IO_OK) {
        g.stats.tx_frames++;
        diagf("fmt_tx", "\"main\":%u,\"sub\":%u,\"type\":%u,\"len\":%zu,\"seq\":%u",
              f->main_cmd, f->sub_cmd, f->cmd_type, f->len,g.next_seq);
        g.next_seq=(uint8_t)((g.next_seq+1u)%255u);
        return true;
    }
    diagf("fmt_tx_fail", "\"st\":\"%s\"", nuxel_io_status_name(st));
    if (st == NUXEL_IO_PERMISSION || st == NUXEL_IO_DISCONNECTED) {
        g.stats.permissions++;
    }
    return false;
}

/* Write ONE serialized IIL frame (IpcProtocol41Iil) to /dev/umts_ipc0.
 * The IIL header differs from FMT only in bytes 2..3: a 16-bit msg_seq
 * (no ack_seq). main/sub/type sit at the same offsets, so the kernel
 * dispatches on (main,sub) exactly as the stock imsservice does. Writes are
 * bounded and gated by the same write capability. seq is a 16-bit counter. */
static bool radiod_write_iil(const struct iil_frame *f)
{
    if (!g.write_enabled) {
        diag("iil_tx_refused", "\"reason\":\"write capability disabled\"");
        return false;
    }
    if (!f || f->len < 7 || f->len > IIL_TX_MAX_FRAME) return false;
    /* IIL shares the endpoint sequence space with FMT. The vendor uses ONE
     * msg_seq counter (byte 2) across both; IIL's 16-bit msg_seq fits in the
     * low byte for seq<256 and the high byte stays 0. Starting at 1 (never 0,
     * which the CP treats as a non-correlated write). */
    uint8_t frame[IIL_TX_MAX_FRAME];
    memcpy(frame, f->buf, f->len);
    if (g.next_seq == 0) g.next_seq = 1;
    frame[2] = g.next_seq;
    frame[3] = 0;
    enum nuxel_io_status st = nuxel_dev_write(&g.fmt.dev, frame, f->len);
    if (st == NUXEL_IO_OK) {
        g.stats.tx_frames++;
        diagf("iil_tx", "\"main\":%u,\"sub\":%u,\"type\":%u,\"len\":%zu,\"seq\":%u",
              f->main_cmd, f->sub_cmd, f->cmd_type, f->len, g.next_seq);
        g.next_seq = (uint8_t)((g.next_seq + 1u) % 255u);
        if (g.next_seq == 0) g.next_seq = 1;
        return true;
    }
    diagf("iil_tx_fail", "\"st\":\"%s\"", nuxel_io_status_name(st));
    if (st == NUXEL_IO_PERMISSION || st == NUXEL_IO_DISCONNECTED) {
        g.stats.permissions++;
    }
    return false;
}

static bool iil_pdn_write(const struct iil_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    *seq = g.next_seq;   /* radiod_write_iil writes this shared seq */
    return g.cp_online && radiod_write_iil(f);
}

static bool iil_auth_iil_write(const struct iil_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    *seq = g.next_seq;
    return g.cp_online && radiod_write_iil(f);
}
/* The AKA relay reuses the ordinary FMT write path for the USIM request. */
static bool iil_auth_usim_write(const struct fmt_tx_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    *seq = g.next_seq;
    return g.cp_online && radiod_write_fmt(f);
}

/* SDM readback write path: ordinary FMT writes, same shared sequence space. */
static bool ims_sdm_write(const struct fmt_tx_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    *seq = g.next_seq;
    return g.cp_online && radiod_write_fmt(f);
}


/* Fire IpcTxSetSipParam (main=3 CDMA_DATA sub=19) with a discovered P-CSCF
 * and the IMSI-derived private identity. This is the modem-internal IMS
 * stack's SIP configuration; it supplies WHERE to send REGISTER (P-CSCF) and
 * WHAT identity to assert (IMPI). Password is empty (IMS AKA, no SIP digest
 * password). Auth=NONE, proto=IPV6 (KPN 204-08 IMS bearer). Never fabricated. */
static void radiod_sip_param_from_pcscf(const struct iil_pdn *p)
{
    if (!p || !p->pcscf_ready || p->pcscf_count == 0) return;
    if (!g.sim_ready_seen || !g.ims.identity.ready) return;
    char proxy[64] = {0};
    int fam = p->family;
    if (fam == AF_INET) {
        if (p->pcscf_len[0] != 4) return;
        inet_ntop(AF_INET, p->pcscf[0], proxy, sizeof proxy);
    } else {
        if (p->pcscf_len[0] != 16) return;
        inet_ntop(AF_INET6, p->pcscf[0], proxy, sizeof proxy);
    }
    if (!proxy[0]) return;
    struct fmt_tx_frame f;
    if (fmt_tx_set_sip_param(&f, proxy, g.ims.identity.impi, "",
                             FMT_TX_AUTH_NONE, FMT_TX_PROTO_IPV6)) {
        if (g.cp_online && radiod_write_fmt(&f)) {
            diag("iil_sip_param", NULL);  /* P-CSCF is not secret; never log it */
        }
    }
    memset(proxy, 0, sizeof proxy);
}

/* Fire IpcTxSetSipParam from the FMT IMS PDN (ims_pdn) discovered P-CSCF.
 * Mirror of radiod_sip_param_from_pcscf for the Round 07 verified FMT bearer.
 * The modem's internal IMS SIP stack is what actually registers; the AP-side
 * native socket cannot bind the modem-internal IMS bearer IP, so the correct
 * surface is IpcTxSetSipParam (main=3 CDMA_DATA sub=19) with the recovered
 * P-CSCF + IMSI-derived IMPI. Never fabricate; never log the identity. */
static bool radiod_sip_param_from_fmt_pcscf(const struct ims_pdn *p)
{
    if (!p || !p->pcscf_ready || !p->ip.ipv6_valid || p->ip.pcscf6_count == 0) return false;
    if (!g.sim_ready_seen || !g.ims.identity.ready) return false;
    char proxy[64] = {0};
    inet_ntop(AF_INET6, p->ip.pcscf6[0], proxy, sizeof proxy);
    if (!proxy[0]) return false;
    bool sent = false;
    struct fmt_tx_frame f;
    if (fmt_tx_set_sip_param(&f, proxy, g.ims.identity.impi, "",
                             FMT_TX_AUTH_NONE, FMT_TX_PROTO_IPV6)) {
        if (g.cp_online && radiod_write_fmt(&f)) {
            diag("fmt_sip_param", NULL);  /* P-CSCF is not secret; never log it */
            sent = true;
        }
    }
    memset(proxy, 0, sizeof proxy);
    return sent;
}


/* ------------------------------------------------------------------ */
/* IMS bearer data-path: attach CID-2 (rmnet1) to the AP                */
/* ------------------------------------------------------------------ */
/* The CID-2 IMS PDN lives inside the CP; its rmnet vnet (DT rmnet1,
 * SIPC channel 0x0B) is DOWN until the AP opens it. Bringing rmnet1 up and
 * assigning the modem-reported IMS IPv6 + a host route to the discovered
 * P-CSCF makes the IMS P-CSCF reachable from the native SIP transport. This
 * is the DT-defined vnet for PDP channel 0x0B; it does NOT touch rmnet0
 * (the ordinary internet CID-1 bearer). Reversible; idempotent. */
static char g_ims_iface_ip[64];        /* currently-applied IMS IPv6 on rmnet1 */
static char g_ims_iface_pcscf[64];     /* currently-routed P-CSCF */

static int run_ip(char *const argv[])
{
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (!pid) {
        sigset_t mask; sigemptyset(&mask);
        (void)sigprocmask(SIG_SETMASK, &mask, NULL);
        execv("/sbin/ip", argv);
        _exit(127);
    }
    int st = 0;
    while (waitpid(pid, &st, 0) < 0 && errno == EINTR) {}
    return (WIFEXITED(st) && WEXITSTATUS(st) == 0) ? 0 : (WIFEXITED(st) ? WEXITSTATUS(st) : -1);
}

/* Apply the IMS bearer address to rmnet1 and route P-CSCF over it. Called
 * only when a CID-2 GPRS_IP_CONFIGURATION carries an IPv6 + P-CSCF, and only
 * when not already applied (so we don't spam `ip`). Not secret: the IMS IPv6
 * and P-CSCF are network configuration. */
static void radiod_ims_iface_apply(const char *ims_ip, const char *pcscf)
{
    if (!ims_ip || !*ims_ip) return;
    if (!strcmp(ims_ip, g_ims_iface_ip) &&
        (!pcscf || !strcmp(pcscf, g_ims_iface_pcscf))) return;  /* unchanged */
    char addr[80], pcroute[96];
    snprintf(addr, sizeof addr, "%s/64", ims_ip);
    char *up[] = { "ip", "link", "set", "rmnet1", "up", NULL };
    char *aadd[] = { "ip", "-6", "addr", "replace", addr, "dev", "rmnet1", NULL };
    (void)run_ip(up);
    int ra = run_ip(aadd);
    int rp = -1;
    if (pcscf && *pcscf) {
        snprintf(pcroute, sizeof pcroute, "%s/128", pcscf);
        char *padd[] = { "ip", "-6", "route", "replace", pcroute, "dev", "rmnet1", NULL };
        rp = run_ip(padd);
    }
    snprintf(g_ims_iface_ip, sizeof g_ims_iface_ip, "%s", ims_ip);
    snprintf(g_ims_iface_pcscf, sizeof g_ims_iface_pcscf, "%s", pcscf ? pcscf : "");
    diagf("ims_iface_up", "\"addr_rc\":%d,\"route_rc\":%d", ra, rp);
}

/* Tear down the IMS iface binding (on bearer loss). Leaves rmnet0 intact. */
static void radiod_ims_iface_down(void)
{
    if (!g_ims_iface_ip[0]) return;
    char addr[80];
    snprintf(addr, sizeof addr, "%s/64", g_ims_iface_ip);
    char *adel[] = { "ip", "-6", "addr", "del", addr, "dev", "rmnet1", NULL };
    (void)run_ip(adel);
    char *dn[] = { "ip", "link", "set", "rmnet1", "down", NULL };
    (void)run_ip(dn);
    g_ims_iface_ip[0] = 0; g_ims_iface_pcscf[0] = 0;
    diag("ims_iface_down", NULL);
}

/* ------------------------------------------------------------------ */
/* native SIP transport (ims_sip_tr) integration                       */
/* ------------------------------------------------------------------ */
static int sip_tr_fd = -1;               /* UDP socket bound to the IMS bearer */

static bool sip_tr_send_cb(const void *msg, size_t len, void *user)
{
    (void)user;
    if (sip_tr_fd < 0 || !msg || len == 0) return false;
    /* Target is the P-CSCF configured in g.sip_tr.cfg; sendto is captured by
     * the ipsec-3gpp ESP policies installed from CK/IK when negotiated. */
    struct sockaddr_storage peer = {0};
    socklen_t plen = 0;
    if (g.sip_tr.cfg.pcscf[0] && strchr(g.sip_tr.cfg.pcscf, ':') == NULL) {
        struct sockaddr_in *a = (struct sockaddr_in *)&peer;
        a->sin_family = AF_INET;
        a->sin_port = htons(g.sip_tr.cfg.pcscf_port);
        if (inet_pton(AF_INET, g.sip_tr.cfg.pcscf, &a->sin_addr) != 1) return false;
        plen = sizeof *a;
    } else {
        struct sockaddr_in6 *a = (struct sockaddr_in6 *)&peer;
        a->sin6_family = AF_INET6;
        a->sin6_port = htons(g.sip_tr.cfg.pcscf_port);
        if (inet_pton(AF_INET6, g.sip_tr.cfg.pcscf, &a->sin6_addr) != 1) return false;
        plen = sizeof *a;
    }
    /* Privacy-safe outbound field-name mask (header names only; no URIs,
     * identities or auth material). Used only while diagnosing a parser-level
     * CP rejection (e.g. 400 Bad Request) of the REGISTER. */
    if (len > 12 && memcmp(msg, "REGISTER ", 9) == 0) {
        const char *b = (const char *)msg; size_t n = len; char mask[256]; size_t ml = 0;
        static const char *const names[] = {"Via","Max-Forwards","From","To","Call-ID","CSeq",
            "Contact","Require","Proxy-Require","Security-Client","P-Preferred-Identity",
            "P-Access-Network-Info","Supported","Allow","Content-Length"};
        size_t i = 0;
        while (i < n) {
            size_t e = i; while (e < n && b[e] != '\n') e++;
            for (size_t k = 0; k < sizeof names/sizeof names[0]; k++) {
                size_t nl = strlen(names[k]);
                if (e > i + nl && b[i+nl] == ':' && memcmp(b+i, names[k], nl) == 0) {
                    int w = snprintf(mask+ml, sizeof mask-ml, "%s%s", ml?",":"", names[k]);
                    if (w>0 && (size_t)w < sizeof mask-ml) ml += (size_t)w;
                    break;
                }
            }
            i = e + 1;
        }
        diagf("sip_tr_tx_mask", "\"len\":%d,\"fields\":\"%s\"", (int)len, mask);
    }
    ssize_t w = sendto(sip_tr_fd, msg, len, 0, (struct sockaddr *)&peer, plen);
    return w == (ssize_t)len;
}

/* Open (or re-open) the native SIP transport from the discovered IIL P-CSCF
 * and IMS bearer local address. This does NOT start registration; tick() does
 * when bearer + P-CSCF are ready. Bounded, fail-closed; never fabricates. */
static bool sip_tr_open_from_iil(const struct iil_pdn *p)
{
    if (!p || !p->ip_ready || !p->pcscf_ready || p->pcscf_count == 0) return false;
    char pcscf[64] = {0}, local[64] = {0};
    if (p->family == AF_INET) {
        if (p->pcscf_len[0] != 4) return false;
        inet_ntop(AF_INET, p->pcscf[0], pcscf, sizeof pcscf);
        inet_ntop(AF_INET, p->ip, local, sizeof local);
    } else if (p->family == AF_INET6) {
        if (p->pcscf_len[0] != 16) return false;
        inet_ntop(AF_INET6, p->pcscf[0], pcscf, sizeof pcscf);
        inet_ntop(AF_INET6, p->ip, local, sizeof local);
    } else {
        return false;
    }
    if (!pcscf[0] || !local[0]) return false;

    /* Close a previous socket and open a fresh one bound to the IMS local IP. */
    if (sip_tr_fd >= 0) { close(sip_tr_fd); sip_tr_fd = -1; }
    int fam = (p->family == AF_INET) ? AF_INET : AF_INET6;
    sip_tr_fd = socket(fam, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (sip_tr_fd < 0) return false;
    struct sockaddr_storage sa = {0};
    socklen_t slen = 0;
    uint16_t port = 5062;
    if (fam == AF_INET) {
        struct sockaddr_in *a = (struct sockaddr_in *)&sa;
        a->sin_family = AF_INET;
        a->sin_port = htons(port);
        if (inet_pton(AF_INET, local, &a->sin_addr) != 1) goto fail;
        slen = sizeof *a;
    } else {
        struct sockaddr_in6 *a = (struct sockaddr_in6 *)&sa;
        a->sin6_family = AF_INET6;
        a->sin6_port = htons(port);
        if (inet_pton(AF_INET6, local, &a->sin6_addr) != 1) goto fail;
        slen = sizeof *a;
    }
    if (bind(sip_tr_fd, (struct sockaddr *)&sa, slen) != 0) goto fail;

    struct ims_sip_tr_cfg cfg = {
        .impu = NULL, .impi = NULL,
        .pcscf = pcscf, .local_ip = local,
        .port = port, .pcscf_port = 5060,
        /* TS 33.203 7.1 ipsec-3gpp Security-Client offer. The vendor value the CP
         * exposes is alg=hmac-sha-1-96, ealg=null|aes-cbc, prot=esp,
         * mod=trans with explicit SPIs/ports. Use the canonical key=value
         * grammar the P-CSCF parses (alg/ealg/prot/mod/spi/port) rather than
         * the earlier malformed single-token string. */
        .sec_offer = "alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064",
    };
    /* Private/public identity: use the IMSI-derived IMPI when available. */
    char impu_buf[160] = {0}, impi_buf[160] = {0};
    if (g.ims.identity.ready && g.ims.identity.impi[0]) {
        snprintf(impi_buf, sizeof impi_buf, "%s", g.ims.identity.impi);
        /* Prefer the verified MSISDN-derived IMPU (the default public identity
         * a USIM-only subscription registers) over the IMSI-derived temporary
         * IMPU. The private identity (IMPI) is unchanged and remains the IMSI
         * for IMS AKA. If no EF_MSISDN was read, fall back to the IMSI-derived
         * IMPU exactly as before. */
        if (g.ims.identity.msisdn_impu_valid && g.ims.identity.msisdn_impu[0])
            snprintf(impu_buf, sizeof impu_buf, "%s", g.ims.identity.msisdn_impu);
        else if (g.ims.identity.impu[0])
            snprintf(impu_buf, sizeof impu_buf, "%s", g.ims.identity.impu);
        else
            snprintf(impu_buf, sizeof impu_buf, "sip:%s", g.ims.identity.impi);
        cfg.impi = impi_buf;
        cfg.impu = impu_buf;
    }
    if (!cfg.impu || !cfg.impi) {
        /* No identity yet: leave the transport closed; tick re-opens when the
         * USIM identity is ready. */
        close(sip_tr_fd); sip_tr_fd = -1;
        return false;
    }

    struct ims_sip_tr_io io = { .send = sip_tr_send_cb, .recv = NULL };
    if (!ims_sip_tr_open(&g.sip_tr, &cfg, &io, NULL, &g.sip_tr)) { close(sip_tr_fd); sip_tr_fd = -1; return false; }
    g.sip_tr_open = true;
    return true;

fail:
    close(sip_tr_fd); sip_tr_fd = -1;
    return false;
}

/* Open the native SIP transport from the FMT IMS PDN (ims_pdn) IPv6/P-CSCF
 * (the Round 07 verified FMT path). This is the mirror of sip_tr_open_from_iil
 * for the FMT bearer that now reaches ims_pdn_active() with a real CID-2
 * GPRS_IP_CONFIGURATION (2 P-CSCF). The FMT ip is carried in fmt_rx_ip.pcscf6. */
static bool sip_tr_open_from_ims_pdn(const struct ims_pdn *p)
{
    if (!p || !p->ip_ready || !p->pcscf_ready) return false;
    int fam = 0;
    char pcscf[64] = {0}, local[64] = {0};
    if (p->ip.ipv6_valid && p->ip.pcscf6_count > 0) {
        fam = AF_INET6;
        inet_ntop(AF_INET6, p->ip.pcscf6[0], pcscf, sizeof pcscf);
        inet_ntop(AF_INET6, p->ip.ipv6, local, sizeof local);
    } else if (p->ip.ipv4_valid && p->ip.pcscf4_count > 0) {
        fam = AF_INET;
        inet_ntop(AF_INET, p->ip.pcscf4[0], pcscf, sizeof pcscf);
        inet_ntop(AF_INET, p->ip.ipv4, local, sizeof local);
    }
    if (fam == 0 || !pcscf[0] || !local[0]) {
        diagf("fmt_sip_tr_noFam", "fam=%d ipv4=%d v6=%d pcscf4=%u pcscf6=%u",
              fam, p->ip.ipv4_valid, p->ip.ipv6_valid, p->ip.pcscf4_count, p->ip.pcscf6_count);
        return false;
    }

    if (sip_tr_fd >= 0) { close(sip_tr_fd); sip_tr_fd = -1; }
    sip_tr_fd = socket(fam, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (sip_tr_fd < 0) return false;
    uint16_t port = 5062;
    if (fam == AF_INET) {
        struct sockaddr_in sa = {0};
        sa.sin_family = AF_INET;
        sa.sin_port = htons(port);
        if (inet_pton(AF_INET, local, &sa.sin_addr) != 1) goto fail2;
        if (bind(sip_tr_fd, (struct sockaddr *)&sa, sizeof sa) != 0) goto fail2;
    } else {
        struct sockaddr_in6 sa = {0};
        sa.sin6_family = AF_INET6;
        sa.sin6_port = htons(port);
        if (inet_pton(AF_INET6, local, &sa.sin6_addr) != 1) goto fail2;
        if (bind(sip_tr_fd, (struct sockaddr *)&sa, sizeof sa) != 0) goto fail2;
    }

    struct ims_sip_tr_cfg cfg = {
        .impu = NULL, .impi = NULL,
        .pcscf = pcscf, .local_ip = local,
        .port = port, .pcscf_port = 5060,
        /* TS 33.203 7.1 ipsec-3gpp Security-Client offer. The vendor value the CP
         * exposes is alg=hmac-sha-1-96, ealg=null|aes-cbc, prot=esp,
         * mod=trans with explicit SPIs/ports. Use the canonical key=value
         * grammar the P-CSCF parses (alg/ealg/prot/mod/spi/port) rather than
         * the earlier malformed single-token string. */
        .sec_offer = "alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064",
    };
    char impu_buf[160] = {0}, impi_buf[160] = {0};
    if (g.ims.identity.ready && g.ims.identity.impi[0]) {
        snprintf(impi_buf, sizeof impi_buf, "%s", g.ims.identity.impi);
        /* Prefer the verified MSISDN-derived IMPU (the default public identity
         * a USIM-only subscription registers) over the IMSI-derived temporary
         * IMPU. The private identity (IMPI) is unchanged and remains the IMSI
         * for IMS AKA. If no EF_MSISDN was read, fall back to the IMSI-derived
         * IMPU exactly as before. */
        if (g.ims.identity.msisdn_impu_valid && g.ims.identity.msisdn_impu[0])
            snprintf(impu_buf, sizeof impu_buf, "%s", g.ims.identity.msisdn_impu);
        else if (g.ims.identity.impu[0])
            snprintf(impu_buf, sizeof impu_buf, "%s", g.ims.identity.impu);
        else
            snprintf(impu_buf, sizeof impu_buf, "sip:%s", g.ims.identity.impi);
        cfg.impi = impi_buf;
        cfg.impu = impu_buf;
    }
    if (!cfg.impu || !cfg.impi) {
        close(sip_tr_fd); sip_tr_fd = -1;
        return false;
    }
    struct ims_sip_tr_io io = { .send = sip_tr_send_cb, .recv = NULL };
    if (!ims_sip_tr_open(&g.sip_tr, &cfg, &io, NULL, &g.sip_tr)) { close(sip_tr_fd); sip_tr_fd = -1; return false; }
    g.sip_tr_open = true;
    return true;

fail2:
    close(sip_tr_fd); sip_tr_fd = -1;
    return false;
}

/* Close the native SIP transport (bearer loss / stop). */
static void sip_tr_close(void)
{
    if (g.sip_tr_open) { ims_sip_tr_close(&g.sip_tr); g.sip_tr_open = false; }
    if (sip_tr_fd >= 0) { close(sip_tr_fd); sip_tr_fd = -1; }
    /* A bearer loss invalidates any in-flight SIP AKA challenge. */
    g.sip_auth_pending = false;
    g.sip_auth_last_seq = 0;
}

/* Drain any queued SIP response datagram(s) off the IMS bearer socket and
 * feed them to the registration FSM. This is the missing receive path: the
 * FSM previously only SENT REGISTER and never read the network's 401/200
 * replies, so it could never actually register. Non-blocking, bounded. */
/* Privacy-safe summary of a SIP response: status code plus the set of header
 * NAMES present (never values, never PII/identities/URIs). Bounded; used only
 * for root-cause diagnosis of registration rejections. */
static void sip_rx_diag(const uint8_t *buf, size_t n)
{
    if (n < 12 || memcmp(buf, "SIP/2.0 ", 8) != 0 ||
        buf[8] < '1' || buf[8] > '6') {
        diagf("sip_tr_rx", "\"len\":%d,\"not_sip\":true", (int)n);
        return;
    }
    int code = (buf[8]-'0')*100 + (buf[9]-'0')*10 + (buf[10]-'0');
    char mask[192]; mask[0] = 0; size_t ml = 0;
    static const struct { const char *name; const char *tag; } want[] = {
        {"Via", "via"}, {"WWW-Authenticate", "www-auth"},
        {"Proxy-Authenticate", "proxy-auth"}, {"Security-Server", "sec-srv"},
        {"Security-Client", "sec-cli"}, {"Retry-After", "retry"},
        {"Reason", "reason"}, {"Unsupported", "unsupported"},
        {"Warning", "warning"}, {"P-Charging-Vector", "pcv"},
        {"Require", "require"}, {"Server", "server"},
    };
    size_t i = 9;
    while (i < n) {
        size_t e = i;
        while (e < n && buf[e] != '\n') e++;
        size_t llen = e - i;
        if (llen && buf[e-1] == '\r') llen--;
        if (!llen) break;                 /* end of headers */
        for (size_t k = 0; k < sizeof want / sizeof want[0]; k++) {
            size_t nl = strlen(want[k].name);
            if (llen >= nl + 1 && buf[i+nl] == ':' &&
                memcmp(buf+i, want[k].name, nl) == 0) {
                int w = snprintf(mask+ml, sizeof mask - ml, "%s%s",
                                 ml ? "," : "", want[k].tag);
                if (w > 0 && (size_t)w < sizeof mask - ml) ml += (size_t)w;
                break;
            }
        }
        i = e + 1;
    }
    /* Retry-After pre-challenge is the KPN P-CSCF's authoritative "no IMS
     * service for this origin" answer (Round 18: identical 480 in <0.1 s for
     * every standards-compliant REGISTER variant: correct Contact URI,
     * sip.instance, sec-agree+Security-Client, icsi-ref, bare OPTIONS). The
     * modem CP runs no SIP (it only tracks IMS_REG state); stock IMS lives in
     * the Android AP client. Surface the distinction for the FSM/failure. */
    bool retry = strstr(mask, "retry") != NULL;
    diagf("sip_tr_rx", "\"code\":%d,\"headers\":\"%s\",\"p_cscf_no_service\":%s",
          code, mask, (code == 480 && retry) ? "true" : "false");
}

static void sip_tr_recv(void)
{
    if (sip_tr_fd < 0 || !g.sip_tr_open) return;
    uint8_t buf[IMS_SIP_TR_MAX_REPLY + 1];
    unsigned budget = 16;   /* bounded per-wake drain */
    while (budget-- > 0) {
        ssize_t n = recvfrom(sip_tr_fd, buf, sizeof buf, MSG_DONTWAIT, NULL, NULL);
        if (n < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) break;  /* drained */
            if (errno == EINTR) continue;
            break;   /* hard error: drop the socket on next tick */
        }
        if (n == 0) break;
        /* Surface the SIP status code + header NAMES only (never values). */
        sip_rx_diag(buf, (size_t)n);
        /* Feed exactly one datagram; the FSM parse is bounded. Never log body. */
        ims_sip_tr_feed(&g.sip_tr, buf, (size_t)n);
        /* A state change is surfaced below in sip_tr_tick. */
    }
}

/* Bridge a native SIP 401 AKAv1-MD5 challenge to the legitimate USIM AKA.
 * The 401 nonce is base64(RAND||AUTN) (RFC 3310). Decode it, submit the
 * SEC 5/9 USIM 3G AKA, and remember the request seq so the solicited result
 * can be correlated back to ims_sip_tr_auth() in dispatch_fmt. Secret
 * material is stack-scoped and wiped; never logged. */
static void sip_tr_usim_challenge(uint64_t now)
{
    (void)now;
    if (g.sip_auth_pending) return;               /* one outstanding AKA */
    if (g.sip_tr.phase != IMS_SIP_TR_CHALLENGED) return;
    if (g.sip_tr.res_b64[0]) return;              /* RES already stored; awaiting authenticated REGISTER */
    /* t->nonce holds base64(RAND||AUTN), 44 chars + NUL. Decode to 32 bytes. */
    uint8_t raw[32];
    size_t raw_len = 0;
    if (!ims_base64_decode(g.sip_tr.nonce, strlen(g.sip_tr.nonce),
                           raw, sizeof raw, &raw_len) || raw_len != 32) {
        diag("iil_sip_tr_auth_nonce_bad", NULL);
        return;
    }
    uint8_t rnd[16], autn[16];
    memcpy(rnd, raw, 16);
    memcpy(autn, raw + 16, 16);

    struct fmt_tx_frame f;
    if (!fmt_tx_usim_auth(&f, rnd, autn)) {
        memset(rnd, 0, sizeof rnd); memset(autn, 0, sizeof autn);
        memset(raw, 0, sizeof raw);
        return;
    }
    uint8_t seq = g.next_seq;   /* capture BEFORE write (radiod_write_fmt increments) */
    /* Serialize through the same FMT write path the IIL auth relay uses. */
    if (!g.cp_online || !g.write_enabled || !g.fmt.present ||
        !radiod_write_fmt(&f)) {
        diag("iil_sip_tr_usim_tx_refused", NULL);
        g.sip_auth_pending = false;
        g.sip_auth_last_seq = 0;
    } else {
        g.sip_auth_last_seq = seq;
        g.sip_auth_pending = true;
    }
    memset(rnd, 0, sizeof rnd); memset(autn, 0, sizeof autn);
    memset(raw, 0, sizeof raw);
}

/* Tick the native SIP transport: open when P-CSCF+identity are ready, drain
 * replies, start registration, then advance the FSM. Registers only on an
 * authoritative 200. */
static void sip_tr_tick(uint64_t now)
{
    /* The native SIP transport is driven from EITHER the IIL PDN or the FMT
     * IMS PDN, whichever establishes a usable CID-2 bearer with IP + P-CSCF.
     * The FMT path (Round 07 verified) now reaches ims_pdn_active() with a
     * real GPRS_IP_CONFIGURATION (2 P-CSCF); previously only the IIL path was
     * wired here, so a working FMT bearer never opened SIP. */
    /* Round 19 (verified live on libsec-ril.so EFUJ2): the CP does NOT run a
     * SIP registrar client and does NOT initiate IMS AKA autonomously -- it
     * only *relays* AKA if an AP IMS service asks (IIL sub 17) and merely
     * records the AP's SetRegState claim (FMT 22/8). Our unauthenticated,
     * IMSI-derived REGISTERs are answered 480+Retry-After (no 401), so sending
     * them only re-probes the carrier with an IMPU we cannot authenticate.
     * ETHICS GATE: do not transmit a REGISTER whose IMPI we cannot verify by a
     * genuine 401/AKA exchange. NUXEL_IMS_ALLOW_UNAUTH_REGISTER=1 re-enables the
     * probe for an owner-verified IMS provisioning environment. */
    static const char *allow_unauth = NULL;
    if (!allow_unauth) allow_unauth = getenv("NUXEL_IMS_ALLOW_UNAUTH_REGISTER");
    /* The IMS bearer (CID2) + rmnet1 iface/route MUST stay applied so the
     * SIP transport and P-CSCF remain physically available even while REGISTER
     * TX is held (the ethics gate below only suppresses the REGISTER itself,
     * never the bearer). */
    bool bearer = iil_pdn_active(&g.iil_pdn) || ims_pdn_active(&g.ims_pdn);
    bool reg_allowed = allow_unauth && *allow_unauth == '1';
    if (bearer) {
        if (!g.sip_tr_open) {
            if (iil_pdn_active(&g.iil_pdn)) {
                if (sip_tr_open_from_iil(&g.iil_pdn)) diag("iil_sip_tr_open", NULL);
            } else if (sip_tr_open_from_ims_pdn(&g.ims_pdn)) {
                diag("fmt_sip_tr_open", NULL);
            }
        }
        if (g.sip_tr_open && reg_allowed) {
            enum ims_sip_tr_phase before = g.sip_tr.phase;
            sip_tr_recv();   /* read 401/200 replies before advancing the FSM */
            if (before == IMS_SIP_TR_IDLE) {
                if (!ims_sip_tr_start(&g.sip_tr))
                    diag("sip_tr_start_send_fail", NULL);
            }
            /* A 401 sets CHALLENGED; drive the USIM AKA so an authenticated
             * REGISTER can be sent. (Only fires once per challenge.) */
            if (g.sip_tr.phase == IMS_SIP_TR_CHALLENGED &&
                !g.sip_auth_pending)
                sip_tr_usim_challenge(now);
            enum ims_sip_tr_phase after = ims_sip_tr_tick(&g.sip_tr, now, true);
            if (after != before)
                diagf("iil_sip_tr_phase", "\"phase\":\"%s\"",
                      ims_sip_tr_phase_name(after));
            /* Authoritative native SIP 200 OK -> IMS REGISTERED (never from a
             * modem relay/ack). Drives the SMS-transport readiness gate. */
            bool reg = ims_sip_tr_registered(&g.sip_tr);
            if (reg != (g.ims.phase == IMS_REGISTERED))
                ims_service_native_registered(&g.ims, reg);
        }
    } else {
        if (g.sip_tr_open) { sip_tr_close(); diag("sip_tr_close", NULL); }
        /* Bearer loss: release the CID-2 iface binding (rmnet0 untouched). */
        radiod_ims_iface_down();
        /* Bearer loss invalidates any prior native registration. */
        if (g.ims.modem_confirmed_registered)
            ims_service_native_registered(&g.ims, false);
    }
}

/*
 * Decode the REAL modem responses that gate the data-session FSM, and record
 * their results into g.dsc. Returns DS_FEEDBACK_OK / DS_FEEDBACK_FAIL for the
 * *current* phase, or DS_FEEDBACK_IGNORE when the frame is not a gating
 * response for this phase.
 *
 * The three real, protocol-backed sources we now honour (previously ignored):
 *   1. GEN echo (main=128, type=2): payload = [echo_main][echo_sub][echo_type]
 *      [RESULT][0x80]. RESULT==0 means success; non-zero is a CP rejection.
 *   2. GPRS_CALL_STATUS (main=13 sub=16): payload[0]=cid, payload[1]=state.
 *      state in {1,10,11} => connected; else (incl. live-observed 3) => NOT
 *      connected. This is the authoritative bearer-existence flag.
 *   3. GPRS_PDP_CONTEXT (main=13 sub=4 type=2): response to GetPdpContext(query).
 *      payload[0]=entry count; payload[1]=state. state==0 => disconnected.
 */
static ds_feedback_kind decode_gating_response(const struct nuxel_sipc_fmt *f)
{
    uint8_t phase = (uint8_t)g.dsc.phase;

    if (f->main_cmd == 8 && f->sub_cmd == 8 && f->cmd_type == IPC41_TYPE_RESPONSE &&
        f->payload_len == 1 && f->payload[0] >= 1 && f->payload[0] <= 3) {
        g.service_domain_wire = f->payload[0]; g.service_domain_valid = true;
        diagf("service_domain_readback", "\"wire\":%u,\"packet_service_enabled\":%s",
              f->payload[0], f->payload[0] == 2 ? "false" : "true");
        if (phase == DS_VERIFY_SERVICE_DOMAIN)
            return f->payload[0] == 1 ? DS_FEEDBACK_OK : DS_FEEDBACK_FAIL;
        return DS_FEEDBACK_IGNORE;
    }

    if (f->main_cmd == IPC41_MAIN_NET && f->sub_cmd == IPC41_NET_MODE_SEL &&
        f->cmd_type == IPC41_TYPE_RESPONSE && f->payload_len == 1) {
        g.dsc.last_net_mode = f->payload[0]; g.dsc.net_mode_valid = true;
        diagf("network_mode_readback", "\"mask\":%u", f->payload[0]);
        if (phase == DS_VERIFY_NET_MODE) {
            uint8_t wanted = g.dsc.preferred_net == FMT_TX_PREFERRED_NET_LTE_ONLY ? 8 : 11;
            return f->payload[0] == wanted ? DS_FEEDBACK_OK : DS_FEEDBACK_FAIL;
        }
        return DS_FEEDBACK_IGNORE;
    }

    /* ---- MBIM raw-IPC response (main=0x16 sub=0x0c) ----
     * This is the CP's reply to the recovered MbimAdaptor::MakeSetMsLteAttachConfig
     * / IpcTxRawIpc frame. It is an authoritative command acknowledgement for
     * the DS_MBIM_ATTACH_CONFIG phase only. We accept it as the phase's ack
     * (an MBIM message returning means the CP processed the hosted command),
     * but NEVER treat it as bearer proof — the default EPS bearer is still
     * decided by GPRS_CALL_STATUS / GPRS_PDP_CONTEXT downstream. */
    if (f->main_cmd == MBIM_RAW_IPC_MAIN_CMD &&
        f->sub_cmd == MBIM_RAW_IPC_SUB_CMD &&
        phase == DS_MBIM_ATTACH_CONFIG) {
        return DS_FEEDBACK_OK;
    }

    /* GEN is a five-byte payload with a 16-bit LE result. Only the
     * outstanding command's complete origin tuple may advance this phase. */
    if (f->main_cmd == IPC41_MAIN_GEN && f->cmd_type == IPC41_TYPE_RESPONSE) {
        enum ds_gen_status r = ds_gen_response(&g.dsc, f->payload, f->payload_len);
        if (r == DS_GEN_IGNORE) return DS_FEEDBACK_IGNORE;
        diagf("data_session_gen", "\"phase\":\"%s\",\"result\":%u,\"origin\":\"%u/%u/%u\"",
              ds_phase_name(phase), g.dsc.last_gen_result,
              f->payload[0], f->payload[1], f->payload[2]);
        if (r == DS_GEN_REJECTED) return DS_FEEDBACK_FAIL;
        if (r == DS_GEN_OPTIONAL_UNSUPPORTED) {
            diag("mobile_data_toggle_unsupported", "\"result\":32771");
            return DS_FEEDBACK_OK; /* optional facility absent; bearer still required */
        }
        if (phase == DS_SIM_CHECK || phase == DS_DATA_CALL || phase == DS_GET_PDP_LIST ||
            phase == DS_VERIFY_NET_MODE || phase == DS_VERIFY_SERVICE_DOMAIN ||
            phase == DS_IA_STATE_QUERY || phase == DS_PS_DETACHED_VERIFY || phase == DS_PS_REGIST_CHECK ||
            phase == DS_RECOVER_PS_REGIST ||
            phase == DS_NET_REGIST_CHECK || phase == DS_PS_REGIST_VERIFY)
            return DS_FEEDBACK_IGNORE; /* need actual state, not command acceptance */
        if (phase == DS_ENABLE_MOBILE_DATA) g.dsc.mobile_data_on = true;
        if (phase == DS_PS_ATTACH) g.dsc.ps_attach_ack = true;
        return DS_FEEDBACK_OK;
    }

    /* ---- GPRS_CALL_STATUS (main=13 sub=16) ---- */
    /* CP GET replies have two bytes; IpcRxGprsPsState notifications have
     * three (the third is a detach reason). Query after detach acceptance. */
    if (f->main_cmd == 13 && f->sub_cmd == 3 &&
        ((f->cmd_type == IPC41_TYPE_RESPONSE && f->payload_len == 2) ||
         (f->cmd_type == IPC41_TYPE_NOTIFICATION && f->payload_len == 3))) {
        if (f->payload[0] > 1) return DS_FEEDBACK_IGNORE;
        g.dsc.ps_control_valid = true;
        g.dsc.ps_control_state = f->payload[0]; g.dsc.ps_control_suspend = f->payload[1];
        /* GET reads PDNCOMMON_PSINFO and is ignored by the vendor AP receiver.
         * It remained 00 00 with NET PS registered and CID1 active on EFUJ2.
         * Keep it observable; it cannot override actual network registration. */
        diagf("ps_control_state", "\"state\":%u,\"suspend\":%u,\"notification\":%s",
              f->payload[0], f->payload[1], f->cmd_type == IPC41_TYPE_NOTIFICATION ? "true" : "false");
        if (phase == DS_PS_DETACHED_VERIFY && f->cmd_type == IPC41_TYPE_NOTIFICATION && f->payload[0] == 0)
            return DS_FEEDBACK_OK;
        return DS_FEEDBACK_IGNORE;
    }

    if (f->main_cmd == IPC41_MAIN_GPRS && f->sub_cmd == IPC41_GPRS_CALL_STATUS &&
        f->cmd_type == IPC41_TYPE_NOTIFICATION && f->payload_len >= 9 &&
        f->payload[0] == g.dsc.attach_cid) {
        uint8_t state = f->payload[1];
        g.dsc.last_call_cause = f->payload[2];
        diagf("data_call_status", "\"cid\":%u,\"state\":%u,\"cause\":%u",
              f->payload[0], state, f->payload[2]);
        if(g.dsc.phase==DS_ACTIVE && !ds_gprs_call_connected(state)) {
            g.data_path_armed=false;g.dsc.ip_configured=false;g.ip_received=false;
            g.link_down_requested=true;g.reconnect_at=now_ms()+30000;
            emit_state_changed("DataState","disconnected");
        }
        g.dsc.last_gprs_call_state = state;
        g.dsc.gprs_call_state_valid = true;
        if (phase == DS_DATA_CALL) {
            return ds_gprs_call_connected(state) ? DS_FEEDBACK_OK : DS_FEEDBACK_FAIL;
        }
        return DS_FEEDBACK_IGNORE;
    }

    /* ---- GPRS_PDP_CONTEXT list (main=13 sub=4 type=2, GetPdpContext reply) ---- */
    if (f->main_cmd == IPC41_MAIN_GPRS && f->sub_cmd == IPC41_GPRS_PDP_CONTEXT &&
        f->cmd_type == IPC41_TYPE_RESPONSE) {
        uint8_t state;
        if (!fmt_rx_pdp_state(f->payload, f->payload_len, g.dsc.attach_cid, &state))
            return DS_FEEDBACK_IGNORE;
        g.dsc.last_gprs_pdp_state = state;
        g.dsc.gprs_pdp_state_valid = true;
        if (phase == DS_GET_PDP_LIST)
            return ds_gprs_call_connected(state) ? DS_FEEDBACK_OK : DS_FEEDBACK_FAIL;
        return DS_FEEDBACK_IGNORE;
    }

    /* IP notification can precede CALL_STATUS. Keep it across phase changes,
     * but do not call the session ACTIVE until the Linux link is configured. */
    if (f->main_cmd == IPC41_MAIN_GPRS &&
        f->sub_cmd == IPC41_GPRS_IP_CONFIGURATION &&
        f->cmd_type == IPC41_TYPE_NOTIFICATION) {
        struct fmt_rx_ip ip;
        if (fmt_rx_ip(f->payload, f->payload_len, &ip) && ip.cid == g.dsc.attach_cid) {
            if (g.data_path_armed && g.dsc.phase == DS_ACTIVE &&
                memcmp(&ip,&g.ip,sizeof ip)) {
                g.dsc.phase = DS_WAIT_IP; g.dsc.ip_configured = false;
                g.link_attempted = false;
            }
            g.ip = ip; g.ip_received = true;
            diagf("cellular_ip_received", "\"cid\":%u,\"ipv4\":\"%u.%u.%u.%u\",\"ipv6_valid\":%s",
                  ip.cid, ip.ipv4[0], ip.ipv4[1], ip.ipv4[2], ip.ipv4[3],
                  ip.ipv6_valid ? "true" : "false");
            diagf("cellular_ip_parameters", "\"flags\":%u,\"mtu\":%u,\"ipv6_link_local\":%s",
                  ip.flags, ip.mtu, ip.ipv6_valid && ip.ipv6[0] == 0xfe &&
                  (ip.ipv6[1] & 0xc0) == 0x80 ? "true" : "false");
        }
        return DS_FEEDBACK_IGNORE;
    }

    /* ---- NET_REGIST (main=8 sub=5) ---- */
    if (f->main_cmd == IPC41_MAIN_NET && f->sub_cmd == IPC41_NET_REGIST &&
        (f->cmd_type == IPC41_TYPE_RESPONSE || f->cmd_type == IPC41_TYPE_NOTIFICATION)) {
        /* IpcRxNetRegState @0x3399cc maps the CP enum through table
         * 0x14a212. The old identity conversion falsely called raw 1 home.
         * Keep the raw byte alongside its converted state for diagnostics. */
        struct fmt_rx_registration reg;
        if (!fmt_rx_registration(f->payload, f->payload_len, &reg)) return DS_FEEDBACK_IGNORE;
        if (reg.domain == 2) {
            g.cs_registration = reg; g.cs_registration_valid = true;
            diagf("cs_registration", "\"state\":\"%s\",\"raw_state\":%u,\"rat\":\"%s\",\"reject_cause\":%u",
                  fmt_rx_reg_name(reg.state), reg.state_wire, fmt_rx_rat_name(reg.rat_wire), reg.reject_cause);
        }
        if (reg.domain != 3u) return DS_FEEDBACK_IGNORE;
        uint8_t ps_reg = reg.state;
        g.dsc.last_rat_wire = reg.rat_wire;
        g.dsc.last_reg_wire = reg.state_wire;
        g.dsc.last_ps_reg_state = ps_reg;
        g.dsc.net_regist_valid = true;
        g.dsc.ps_state_valid = true; g.dsc.attached = fmt_rx_registered(ps_reg);
        g.dsc.last_reject_cause = reg.reject_cause;
        if(g.dsc.phase==DS_ACTIVE && !fmt_rx_registered(ps_reg)) {
            g.data_path_armed=false;g.dsc.ip_configured=false;g.ip_received=false;
            g.link_down_requested=true;g.reconnect_at=now_ms()+30000;
            emit_state_changed("DataState","no-service");
        }
        const char *psn = fmt_rx_reg_name(ps_reg);
        diagf("net_regist_state",
              "\"ps\":%u,\"ps_name\":\"%s\",\"raw_state\":%u,\"domain_sel\":%u,\"rat_wire\":%u,\"rat\":\"%s\",\"reject_cause\":%u",
              ps_reg, psn, reg.state_wire, reg.domain, reg.rat_wire, fmt_rx_rat_name(reg.rat_wire), reg.reject_cause);

        if (phase == DS_NET_REGIST_CHECK || phase == DS_IA_STATE_QUERY || phase == DS_PS_REGIST_CHECK)
            return DS_FEEDBACK_OK;
        if (phase == DS_PS_DETACHED_VERIFY && !g.dsc.attached) return DS_FEEDBACK_OK;

        /* PS_REGIST_VERIFY: gate the data-call activation on a REAL PS/data
         * attach. We require RegState==1 (registered home) or 5 (roaming).
         * Any other state (0 not-registered, 2 searching, 3 denied, 4 unknown)
         * is FAIL-closed and blocks the PDP activation. */
        if (phase == DS_PS_REGIST_VERIFY || phase == DS_RECOVER_PS_REGIST) {
            if (g.dsc.ps_state_valid && g.dsc.attached && fmt_rx_registered(ps_reg)) {
                diagf("data_session_ps_attached", "\"ps\":%u", ps_reg);
                return DS_FEEDBACK_OK;
            }
            diagf("data_session_ps_attach_failed",
                  "\"ps\":%u,\"ps_name\":\"%s\",\"ps_attached\":%s",
                  ps_reg, psn, g.dsc.attached ? "true" : "false");
            /* Reselection is asynchronous. Keep polling within the bounded
             * deadline; an unregistered indication is not a final result. */
            return ps_reg == 3u ? DS_FEEDBACK_FAIL : DS_FEEDBACK_IGNORE;
        }

        return DS_FEEDBACK_IGNORE;
    }

    /* ---- SIM readiness (SEC_PIN_STATUS) for DS_SIM_CHECK ---- */
    if (phase == DS_SIM_CHECK &&
        f->main_cmd == IPC41_MAIN_SEC &&
        f->sub_cmd == IPC41_SEC_PIN_STATUS &&
        f->cmd_type == IPC41_TYPE_RESPONSE && f->payload_len == 2) {
        return fmt_rx_sim_ready(f->payload, f->payload_len) ? DS_FEEDBACK_OK : DS_FEEDBACK_FAIL;
    }

    return DS_FEEDBACK_IGNORE;
}

/* Build and emit the FMT frame for the current data-session phase. Returns
 * true if a frame was emitted (does NOT imply modem acceptance). */
static bool data_session_emit(void)
{
    struct fmt_tx_frame f;
    memset(&f, 0, sizeof f);
    switch (g.dsc.phase) {
    case DS_SIM_CHECK:
        if (!fmt_tx_get_sim_status(&f)) return false;
        break;
    case DS_NET_REGIST_CHECK:
        /* Read the CP's PS/data registration state before any data-path command.
         * This is the source-backed IpcTxNetGetDataRegState (NET_REGIST sub=5,
         * 9-byte query). The response tells us whether the modem is PS-registered
         * before we attempt a PDP activation that would otherwise be rejected. */
        if (!fmt_tx_get_data_reg_state(&f)) return false;
        break;
    case DS_SET_SERVICE_DOMAIN:
        /* Enable CS+PS service domain (source-backed IpcTxNetSetServiceDomain,
         * main=8 sub=8, payload=[1]=CS_PS). Wire 2 is CS-only. */
        if (!fmt_tx_set_service_domain(&f, FMT_TX_SERVICE_DOMAIN_CS_PS))
            return false;
        break;
    case DS_VERIFY_SERVICE_DOMAIN:
        if (!fmt_tx_get_service_domain(&f)) return false;
        break;
    case DS_SET_PREFERRED_NET:
        /* Set LTE/WCDMA/GSM auto network mode (source-backed
         * IpcTxNetSetPreferredNetType, main=8 sub=10, payload=[0x0b]). */
        if (!fmt_tx_set_preferred_net_type(&f, g.dsc.preferred_net))
            return false;
        break;
    case DS_VERIFY_NET_MODE:
        if (!fmt_tx_get_preferred_net_type(&f)) return false;
        break;
    case DS_ENABLE_MOBILE_DATA:
        /* Enable GPRS mobile data (source-backed IpcTxSetMobileDataSetting,
         * main=13 sub=29, 9 bytes; enable=1, extra=1). This is the explicit
         * mobile-data-authorization toggle the vendor RIL issues before the
         * profile sync/PDP sequence. A feature-gated 0x8003 response is
         * recorded as unsupported, never as already enabled. */
        if (!fmt_tx_mobile_data(&f, true, true))
            return false;
        break;
    case DS_SYNC_PROFILE:
        /* Full data-profile sync incl. RAT (source-backed IpcTxSyncProfileInfo,
         * main=13 sub=37, 326 bytes; RAT = LTE = 14). */
        if (!fmt_tx_sync_profile_info(&f, (const char*)g.dsc.apn,
                                      g.dsc.auth_code, g.dsc.protocol))
            return false;
        break;
    case DS_SET_DATA_PROFILE:
        /* Set the APN/auth/protocol data profile (source-backed SetDataProfile,
         * main=13 sub=27, 203 bytes; auth NONE -> numeric code 0). */
        if (!fmt_tx_set_data_profile(&f, (const char*)g.dsc.apn,
                                     g.dsc.auth_code, g.dsc.protocol))
            return false;
        break;
    case DS_SET_LTE_ATTACH:
        /* Set the LTE attach profile (source-backed SetLteAttachProfile,
         * main=13 sub=20, 201 bytes). payload[1] = attach CID. Corrected
         * GetAttachCid() == 1 for RIL slot 0, 5 for RIL slot 1 (see
         * data_session.h). payload[0]=1 creates the initial profile;
         * 3 instead calls PMPM_AddAlwaysOnProfile (CP 0x40711db2). */
        if (!fmt_tx_set_lte_attach_profile(&f, (const char*)g.dsc.apn,
                                           g.dsc.auth_code,
                                           g.dsc.protocol,
                                           g.dsc.attach_cid, g.dsc.attach_flag))
            return false;
        break;
    case DS_PS_DETACH:
        if (!fmt_tx_ps_attach(&f, false, false, 4)) return false;
        break;
    case DS_PS_DETACHED_VERIFY:
    case DS_IA_STATE_QUERY:
    case DS_PS_REGIST_CHECK:
        if (!fmt_tx_get_data_reg_state(&f)) return false;
        break;
    case DS_RECOVER_PS_ATTACH:
        if (!fmt_tx_ps_attach(&f, true, false, 0)) return false;
        break;
    case DS_RECOVER_PS_REGIST:
        if (!fmt_tx_get_data_reg_state(&f)) return false;
        break;
    case DS_MBIM_ATTACH_CONFIG: {
        /* Recovered MBIM MS LTE Attach Config (CID 0x0A) via IpcTxRawIpc
         * (main=0x16/sub=0x0c/type=0x05) over the RIL FMT channel. This is the
         * source-backed sender from IpcProtocol41::IpcTxRawIpc @0x3180f0 and
         * MbimAdaptor::MakeSetMsLteAttachConfig @0x1c3018 (round-31 recovery).
         *
         * Round-31 live result: a lone MBIM COMMAND frame rendered byte-correct
         * but the CP stayed silent. Root cause recovered this round: the vendor
         * MBIM host performs a full MBIM control session (OPEN -> proprietary
         * CID command -> CLOSE) via the SIPC raw-IPC forward. Sending only the
         * command skips the mandatory OPEN/CLOSE envelope, so the CP never
         * opens the session and never answers.
         *
         * Opt-in only (NUXEL_MBIM_ATTACH=1). The session is driven by
         * g.dsc.mbim_substate: 0=OPEN, 1=COMMAND, 2=STATUS query, 3=CLOSE.
         * Each step wraps the built MBIM message in the recovered raw-IPC FMT
         * frame and emits it once. */
        if (!mbim_attach_enabled()) return false;

        const uint32_t txn = 1u;
        uint8_t mbim[MBIM_TX_MAX_FRAME];
        size_t mbim_len = 0;

        switch (g.dsc.mbim_substate) {
        case 0: /* MBIM OPEN */
            mbim_len = mbim_tx_build_open(mbim, sizeof mbim, txn,
                                          MBIM_MAX_CONTROL_TRANSFER);
            break;
        case 1: { /* MBIM MS LTE Attach Config (SET, CID 0x0A) */
            struct mbim_attach_context mctx[1];
            memset(mctx, 0, sizeof mctx);
            mctx[0].apn = (const char*)g.dsc.apn;
            mctx[0].username = "";
            mctx[0].password = "";
            mctx[0].ip_type = MBIM_CONTEXT_IP_TYPE_IPV4V6;
            mctx[0].auth = MBIM_AUTH_PROTOCOL_NONE;
            mbim_len = mbim_tx_build_lte_attach_config(mbim, sizeof mbim,
                                                       mctx, 1, txn);
            break;
        }
        case 2: /* MBIM MS LTE Attach Status (QUERY, CID 0x0B) */
            mbim_len = mbim_tx_build_query(mbim, sizeof mbim, txn,
                                           MBIM_CID_MS_LTE_ATTACH_STATUS);
            break;
        default: /* MBIM CLOSE (session termination) */
            mbim_len = mbim_tx_build_close(mbim, sizeof mbim, txn);
            break;
        }
        if (mbim_len == 0) return false;

        /* Advance before emit so the next tick issues the following message.
         * CLOSE (substate 3) wraps to 0 for a bounded re-attempt. */
        g.dsc.mbim_substate = (uint8_t)((g.dsc.mbim_substate + 1u) % 4u);

        uint8_t rawipc[MBIM_TX_MAX_FRAME];
        size_t raw_len = mbim_tx_build_raw_ipc_frame(rawipc, sizeof rawipc,
                                                     mbim, mbim_len,
                                                     g.next_seq, 0);
        if (raw_len < 8) return false;

        struct fmt_tx_frame mf;
        memset(&mf, 0, sizeof mf);
        if (raw_len > sizeof mf.buf) return false;
        memcpy(mf.buf, rawipc, raw_len);
        mf.len = raw_len;
        mf.main_cmd = MBIM_RAW_IPC_MAIN_CMD;
        mf.sub_cmd  = MBIM_RAW_IPC_SUB_CMD;
        mf.cmd_type = MBIM_RAW_IPC_CMD_TYPE;
        return radiod_write_fmt(&mf);
    }
    case DS_DEFINE_PDP:
        /* Define the PDP context (source-backed IpcTxDefinePdpContext,
         * main=13 sub=1, 134 bytes) using the corrected attach CID (1 for
         * single-SIM; see GetAttachCid disassembly), NOT the DataProfile id. */
        if (!fmt_tx_define_pdp_context(&f, (const char*)g.dsc.apn,
                                       g.dsc.protocol == FMT_TX_PROTO_IPV4V6 ?
                                       FMT_TX_PROTO_IP : g.dsc.protocol,
                                       g.dsc.attach_cid))
            return false;
        /* CP validator 0x41219fe4 accepts only PDP wire types 2,5,6.
         * The dual-stack attach profile remains separate; DEFINE requests
         * an IPv4 context when the requested family is dual stack. */
        diagf("pdp_definition", "\"cid\":%u,\"requested_protocol\":%u,\"wire_protocol\":%u",
              g.dsc.attach_cid, g.dsc.protocol, f.buf[9]);
        break;
    case DS_ALWAYS_ON_PDN:
        /* Attach the default PDN (source-backed SetAlwaysOnPdn, main=13 sub=34).
         * payload[1] is the int argument that DoAlwaysOnPdn() supplies as 1
         * (ConvertProfileId(DEFAULT)), NOT the attach CID. */
        if (!fmt_tx_set_always_on_pdn(&f, true, DS_ALWAYS_ON_PDN_PROFILE))
            return false;
        break;
    case DS_PS_ATTACH:
        if (!fmt_tx_ps_attach(&f, true, false, 0)) return false;
        break;
    case DS_PS_REGIST_VERIFY:
        /* Re-query the CP's PS/data registration state AFTER the PS attach so
         * we gate the data-call activation on a real attach (RegState 1),
         * never on the generic PS-attach GEN echo alone. */
        if (!fmt_tx_get_data_reg_state(&f)) return false;
        break;
    case DS_DATA_CALL:
        /* Activate the PDP context (source-backed SetPdpContext, main=13 sub=4,
         * 112-byte frame). This is the REAL LTE activation command; the CDMA
         * SetDataCallEstablish (main=3/sub=2) is a legacy CDMA path. */
        if (!fmt_tx_set_pdp_context(&f, (const char*)g.dsc.apn,
                                    g.dsc.auth_code, g.dsc.protocol,
                                    g.dsc.attach_cid, g.dsc.pdp_type_wire))
            return false;
        break;
    case DS_GET_PDP_LIST:
        /* Query the PDP context list (source-backed IpcTxGetPdpContext,
         * main=13 sub=4 type=2, 7-byte query). This fetches the established
         * context (incl. IP config) from the CP. */
        if (!fmt_tx_get_pdp_context(&f)) return false;
        break;
    case DS_WAIT_IP:
    case DS_ACTIVE:
    case DS_REJECTED:
    case DS_FAILED:
    case DS_IDLE:
    default:
        return false;
    }
    if (!radiod_write_fmt(&f)) return false;
    if (g.dsc.phase == DS_PS_DETACH) g.dsc.needs_ps_restore = true;
    ds_expect(&g.dsc, f.main_cmd, f.sub_cmd, f.cmd_type);
    return true;
}

/* Tick-driven data-session driver: emits the current phase frame once, then
 * waits for an authenticated response before advancing. Bounded + opt-in. */
static void data_session_tick(uint64_t now)
{
    static uint64_t bus_retry;
    if(!g.bus && now>=bus_retry) { bus_retry=now+5000; (void)setup_session_bus(); }
    if (cellular_link_poll(&g.link,now)) {
        diagf("cellular_link_complete", "\"operation\":%u,\"result\":%d,\"configured\":%s",
              g.link.operation,g.link.result,g.link.configured ? "true" : "false");
        g.dsc.ip_configured = g.link.configured && g.data_path_armed && g.cp_online;
        g.link_check_ms = now + 30000;
        if (g.link.result && g.dsc.phase == DS_WAIT_IP)
            (void)ds_feedback(&g.dsc,false,now);
        if (g.link.operation == CELL_LINK_CHECK && g.link.result && g.data_path_armed && g.cp_online) {
            g.dsc.phase = DS_WAIT_IP; g.link_attempted = false;
        }
    }
    if (g.link_down_requested && !g.link.pid) {
        if (cellular_link_down(&g.link,now)) g.link_down_requested = false;
        else diag("cellular_link_down_start_failed",NULL);
    }
    mobile_stop_tick(&g.mobile_stop,now);
    if(mobile_stop_busy(&g.mobile_stop) && !g.mobile_stop.deadline)g.mobile_stop.deadline=now+120000;
    if(mobile_stop_busy(&g.mobile_stop) && !g.mobile_stop.pending && now>=g.mobile_stop.deadline) {
        g.mobile_stop.phase=MOBILE_STOP_FAILED;g.mobile_stop.result=-ENETDOWN;
    }
    if(mobile_stop_busy(&g.mobile_stop) && g.write_enabled && g.cp_online && g.sim_ready_seen && !g.link.pid) {
        struct fmt_tx_frame frame;uint8_t sequence;
        if(mobile_stop_frame(&g.mobile_stop,&frame)) {
            if(sms_write(&frame,&sequence,NULL))mobile_stop_sent(&g.mobile_stop,sequence,now);
            else { g.mobile_stop.phase=MOBILE_STOP_FAILED;g.mobile_stop.result=-EIO; }
        }
    }
    /* Reconnect only after actual registration and SIM readiness. Three
     * bounded sessions, spaced 30 seconds apart; never reset/power-cycle CP. */
    if(g.mobile_enabled && !g.data_path_armed && !mobile_stop_busy(&g.mobile_stop) &&
       !g.link_down_requested && !g.link.result && g.mobile_stop.phase!=MOBILE_STOP_FAILED && g.write_enabled && g.cp_online &&
       g.sim_ready_seen && g.dsc.net_regist_valid && fmt_rx_registered(g.dsc.last_ps_reg_state) &&
       g.reconnect_attempts<3 && now>=g.reconnect_at && !g.link.pid) {
        g.reconnect_attempts++;g.reconnect_at=now+30000;
        begin_data_session(g.dsc.apn[0] ? (const char *)g.dsc.apn : "internet");
    }
    if (!g.data_path_armed || g.dsc.phase == DS_IDLE) return;
    if (!g.write_enabled || !g.cp_online || !g.fmt.present) {
        return;   /* cannot safely transmit yet */
    }
    if (g.dsc.phase == DS_ACTIVE && !g.link.pid && now >= g.link_check_ms) {
        if (cellular_link_check(&g.link,now)) g.link_check_ms = now + 30000;
    }
    if (ds_terminal(&g.dsc)) {
        if(g.dsc.phase!=DS_ACTIVE)g.data_path_armed=false;
        return;
    }
    if (g.dsc.phase == DS_WAIT_IP) {
        if (g.dsc.ip_configured) {
            (void)ds_step(&g.dsc,true,now);
            emit_state_changed("DataState","active");
            diag("data_session_active",NULL);
            g.reconnect_attempts=0;
            return;
        }
        if (g.ip_received && !g.link_attempted && !g.link.pid) {
            g.link_attempted = true;
            if (!cellular_link_apply(&g.link,&g.ip,now)) {
                diag("cellular_link_start_failed",NULL);
                (void)ds_feedback(&g.dsc,false,now);
            }
        }
        if (g.link.pid) { g.dsc.step_deadline_ms=now+5000; return; }
    }

    /* Query SIM state first. Sysfs ds_detect describes the board's dual-SIM
     * configuration and cannot establish that a card is present or ready. */
    if (!g.sim_ready_seen) {
        /* SIM startup/loss must not suspend the bounded transaction forever.
         * Background status queries continue while waiting for readiness. */
        if(!g.dsc.step_deadline_ms)g.dsc.step_deadline_ms=now+30000;
        if(ds_step(&g.dsc,false,now)==DS_FAILED) {
            g.data_path_armed=false;g.wrote_phase=false;
            diag("data_session_failed","\"phase\":\"SIM_UNAVAILABLE_TIMEOUT\"");
        }
        return;
    }

    /* MBIM is an opt-in, non-essential attach-config path (round-32 ruled it
     * out as the control-plane transport: vendor GetIntfType==SIPC skips
     * raw-IPC). When it is disabled, DS_SET_LTE_ATTACH advances the FSM into
     * DS_MBIM_ATTACH_CONFIG, but data_session_emit() returns false for that
     * phase with MBIM off. Without this skip the FSM stalls forever and the
     * default EPS bearer can never be driven. Skip directly to ALWAYS_ON_PDN. */
    if (g.dsc.phase == DS_MBIM_ATTACH_CONFIG && !mbim_attach_enabled()) {
        enum ds_phase skip = ds_step(&g.dsc, true, now);
        if (skip != DS_MBIM_ATTACH_CONFIG) {
            g.wrote_phase = false;
            g.dsc.phase_entered_ms = now;
            diagf("data_session_ack", "\"phase\":\"MBIM_ATTACH_CONFIG\",\"next\":\"%s\",\"skipped\":true",
                  ds_phase_name(skip));
        }
        return;
    }

    /* MBIM_ATTACH_CONFIG is a multi-step session (OPEN -> COMMAND -> STATUS
     * query -> CLOSE) driven by g.dsc.mbim_substate. Unlike the other phases,
     * it must emit the NEXT session frame on each tick (with a short dwell)
     * rather than emitting once and waiting for a FMT GEN echo. MBIM responses
     * return as MBIM raw-IPC (not FMT GEN), so the normal ack gate does not
     * drive it; the sub-sequence is self-clocking and bounded.
     *
     * We use g.wrote_phase as the "session started" marker for this phase:
     *  - wrote_phase==false && mbim_substate==0 -> not started; emit OPEN
     *    (handled by the generic emit-once path below).
     *  - wrote_phase==true && mbim_substate!=0 -> mid-session; emit next frame.
     *  - wrote_phase==true && mbim_substate==0 -> CLOSE sent last tick; ack. */
    if (g.dsc.phase == DS_MBIM_ATTACH_CONFIG && g.wrote_phase) {
        if (g.dsc.mbim_substate != 0) {
            /* Still mid-session; emit the next frame on a 80 ms dwell. */
            if (g.dsc.phase_entered_ms && now - g.dsc.phase_entered_ms < 80u)
                return;
            if (data_session_emit()) g.dsc.phase_entered_ms = now;
            return;
        }
        /* CLOSE sent: advance the FSM out of this phase. */
        enum ds_phase n0 = ds_step(&g.dsc, true, now);
        if (n0 != g.dsc.phase) {
            g.wrote_phase = false;
            g.dsc.phase_entered_ms = now;
            diagf("data_session_ack", "\"phase\":\"MBIM_ATTACH_CONFIG\",\"next\":\"%s\"",
                  ds_phase_name(n0));
        }
        return;
    }

    /* Emit the current phase ONCE (no re-transmit storm). */
    if (!g.wrote_phase) {
        if (!g.dsc.phase_entered_ms) g.dsc.phase_entered_ms = now;
        if (data_session_emit()) g.wrote_phase = true;
        if (!g.dsc.step_deadline_ms)
            g.dsc.step_deadline_ms = now + 5000u;
        if (g.wrote_phase) return;
        /* Failed serialization/write still reaches the bounded timeout. */
    }

    /* Wait for ack or timeout. If we are holding in PS_ATTACH past the dwell
     * (the CP only sent a generic GEN echo, no separate PS-attach-done), the
     * dwell guard in dispatch_fmt prevented an ack-based advance; advance here
     * so the bounded attach -> activate sequence still proceeds. */
    if (g.dsc.phase == DS_PS_ATTACH && g.dsc.ps_attach_ack &&
        g.dsc.phase_entered_ms &&
        now - g.dsc.phase_entered_ms >= 3000u) {
        enum ds_phase n2 = ds_step(&g.dsc, true, now);
        if (n2 != DS_PS_ATTACH) {
            g.wrote_phase = false;
            g.dsc.phase_entered_ms = now;
            diagf("data_session_ack", "\"phase\":\"PS_ATTACH\",\"next\":\"%s\"",
                  ds_phase_name(n2));
            return;
        }
    }

    enum ds_phase previous = g.dsc.phase;
    uint8_t previous_attempt = g.dsc.attempt;
    enum ds_phase next = ds_step(&g.dsc, false, now);
    if (next != previous) {
        /* phase actually changed (ack from dispatch_fmt, or terminal timeout). */
        if (next == DS_FAILED) {
            diag("data_session_failed", "\"phase\":\"TIMEOUT\"");
            g.data_path_armed = false;
        }
        g.wrote_phase = false;   /* re-emit after advance/retry */
        return;
    }
    /* Same phase but the deadline lapsed: re-emit (bounded by ds_step's
     * attempt counter; it returns DS_FAILED once attempts are exhausted). */
    if (g.dsc.attempt != previous_attempt) {
        g.wrote_phase = false;   /* re-arm for one bounded retry */
    }
}

static void dispatch_raw(uint8_t ch, const uint8_t *data, size_t len)
{
    if (ch == 0xF5) { dispatch_rfs(ch, data, len); return; }  /* RFS channel */
    g.stats.raw_frames++;
    g.stats.raw_bytes += (uint64_t)len;
    diagf("raw_rx", "\"ch\":%u,\"len\":%u", ch, (unsigned)len);
}

/* Try to consume as many complete FMT messages as the buffer holds. */
static void drain_endpoint(struct radiod_endpoint *ep, uint8_t ch, int is_fmt)
{
    if (!is_fmt) {
        /* Raw endpoint: the kernel delivers one complete skb per read, so we
         * treat each accumulated read as one opaque raw message. We do NOT
         * decode it. We keep a small drain to avoid unbounded growth. */
        if (ep->len > 0) {
            dispatch_raw(ch, ep->buf, ep->len);
            ep->len = 0;
        }
        return;
    }
    size_t off = 0;
    while (off < ep->len) {
        struct nuxel_sipc_fmt f;
        size_t consumed = 0;
        int r = sipc5_parse_fmt(ep->buf + off, ep->len - off, RADIOD_MAX_PAYLOAD, &f, &consumed);
        if (r == SIPC_PARSE_OK) {
            g.stats.rx_frames++;
            dispatch_fmt(ch, &f);
            off += consumed;
            continue;
        }
        if (r == SIPC_PARSE_TRUNCATED) {
            /* need more bytes: keep remainder, compact and return */
            g.stats.parse_truncated++;
            break;
        }
        /* malformed: drop one byte to resynchronise, count error */
        g.stats.parse_errors++;
        diagf("parse_error", "\"why\":\"%s\"", sipc_parse_result_name(r));
        off += 1;
    }
    if (off > 0) {
        memmove(ep->buf, ep->buf + off, ep->len - off);
        ep->len -= off;
    }
}

static void ep_expand_and_drain(struct radiod_endpoint *ep, uint8_t ch, int is_fmt, const uint8_t *data, size_t n)
{
    if (!is_fmt) {
        /* raw: each kernel read is one complete opaque message */
        if (n > sizeof(ep->buf)) n = sizeof(ep->buf);   /* bounded copy */
        dispatch_raw(ch, data, n);
        return;
    }
    if (n > sizeof(ep->buf) - ep->len) {
        /* overflow: drop the whole buffer (bounded, do not grow) */
        g.stats.overflow_drops++;
        diag("rx_overflow", NULL);
        ep->len = 0;
        return;
    }
    memcpy(ep->buf + ep->len, data, n);
    ep->len += n;
    drain_endpoint(ep, ch, is_fmt);
}

/* ------------------------------------------------------------------ */
/* endpoint management + disconnect handling                            */
/* ------------------------------------------------------------------ */
static void ep_close(struct radiod_endpoint *ep)
{
    if (ep->present) nuxel_dev_close(&ep->dev);
    ep->present = false;
    ep->len = 0;
}

static bool ep_open(struct radiod_endpoint *ep, const char *node, uint8_t ch, uint8_t fmt)
{
    int rc = nuxel_dev_open(&ep->dev, node, ch, fmt);
    if (rc == 0) {
        ep->present = true;
        ep->len = 0;
        diagf("ep_opened", "\"node\":\"%s\",\"ch\":%u", node, ch);
        return true;
    }
    diagf("ep_open_failed", "\"node\":\"%s\",\"err\":%d", node, -rc);
    ep->present = false;
    return false;
}

static void handle_disconnect(struct radiod_endpoint *ep, const char *what)
{
    g.stats.disconnects++;
    diagf("ep_disconnected", "\"ep\":\"%s\"", what);
    ep_close(ep);
    emit_state_changed(what, "disconnected");
    /* If the CP itself reset, surface it (state was ONLINE, now not). */
    bool was_online = g.cp_online;
    refresh_cp_state();
    if (was_online && !g.cp_online) {
        diag("cp_reset_observed", NULL);
        emit_cp_reset();
        emit_state_changed("CpState", g.cp_state);
    }
}

static void service_ep(struct radiod_endpoint *ep, uint8_t ch, const char *name, sd_event_source *src)
{
    int is_fmt = (ch >= 235 && ch <= 244);
    if (!ep->present) {
        if (now_ms() - ep->last_reopen_ms < REOPEN_INTERVAL_MS) return;
        ep->last_reopen_ms = now_ms();
        if (!ep_open(ep, name, ch, (uint8_t)(ch == 0xF5 ? 2 : 0))) return;
        if (src) sd_event_source_set_enabled(src, SD_EVENT_ON);
    }
    int budget = RX_BUDGET_PER_WAKE;
    while (budget-- > 0) {
        uint8_t tmp[8192];
        ssize_t n = 0;
        enum nuxel_io_status st = nuxel_dev_read(&ep->dev, tmp, sizeof tmp, &n);
        if (st == NUXEL_IO_OK && n > 0) {
            g.stats.rx_bytes += (uint64_t)n;
            ep_expand_and_drain(ep, ch, is_fmt, tmp, (size_t)n);
            continue;
        }
        if (st == NUXEL_IO_NO_DATA) return;          /* drained */
        if (st == NUXEL_IO_DISCONNECTED) { handle_disconnect(ep, name); return; }
        if (st == NUXEL_IO_PERMISSION) { g.stats.permissions++; return; }
        diagf("read_error", "\"ep\":\"%s\",\"st\":\"%s\"", name, nuxel_io_status_name(st));
        return;
    }
}

static uint64_t g_fmt_partial_since_ms;
static int fmt_handler(sd_event_source *s, int fd, uint32_t revents, void *userdata)
{
    (void)s; (void)fd; (void)revents; (void)userdata;
    if (revents & (EPOLLHUP | EPOLLERR)) handle_disconnect(&g.fmt, FMT_NODE);
    size_t before = g.fmt.len;
    service_ep(&g.fmt, 0xEB, FMT_NODE, g.fmt_src);
    /* If a partial FMT frame is stuck (no progress) for >2 s, drop it to avoid
     * an unbounded stuck buffer / permanent truncated state. */
    if (g.fmt.len > 0 && g.fmt.len == before) {
        if (!g_fmt_partial_since_ms) g_fmt_partial_since_ms = now_ms();
        else if (now_ms() - g_fmt_partial_since_ms > 2000) {
            diagf("fmt_partial_drop", "\"held\":%u", (unsigned)g.fmt.len);
            g.fmt.len = 0;
            g_fmt_partial_since_ms = 0;
        }
    } else {
        g_fmt_partial_since_ms = 0;
    }
    return 0;
}
static int rfs_handler(sd_event_source *s, int fd, uint32_t revents, void *userdata)
{
    (void)s; (void)fd; (void)revents; (void)userdata;
    if (revents & (EPOLLHUP | EPOLLERR)) handle_disconnect(&g.rfs, RFS_NODE);
    service_ep(&g.rfs, 0xF5, RFS_NODE, g.rfs_src);
    return 0;
}

/* Reopen endpoints when CP transitions to ONLINE (they only accept writes then). */
static void maybe_open_endpoints(void)
{
    if (!g.fmt.present && g.cp_online) ep_open(&g.fmt, FMT_NODE, 0xEB, 0);
    if (!g.rfs.present && g.cp_online) ep_open(&g.rfs, RFS_NODE, 0xF5, 2);
    if (g.fmt_src && g.fmt.present) sd_event_source_set_enabled(g.fmt_src, SD_EVENT_ON);
    if (g.rfs_src && g.rfs.present) sd_event_source_set_enabled(g.rfs_src, SD_EVENT_ON);
}

/* SMS is submitted on the CS wire domain (fmt_sms_send domain_wire 0 ==
 * ConvertDomainToIPC(2), i.e. internal DomainSelector::GetDomain=2 CS_ONLY).
 * EFUJ2 vendor DoSendSms (0x2197b0) requires NetRegState::IsRegistered() for
 * the CS path and otherwise reports "CS No Service, SMS send fail" without
 * touching the CP. A PS/LTE-only registration is NOT a CS SMS bearer: the CP
 * rejects a CS-domain submission with raw result 2 (Tp cause 0xFF) and no
 * network submission occurs. Reflect CS registration truthfully instead of
 * OR-ing in PS registration and spawning a doomed submission. */
static bool sms_cs_registered(void)
{
    return g.cs_registration_valid && fmt_rx_registered(g.cs_registration.state);
}

/* tick: CP state polling + pending timeouts + reopen */
static int tick_handler(sd_event_source *s, uint64_t usec, void *userdata)
{
    (void)s; (void)userdata;
    bool prev_online = g.cp_online;
    refresh_cp_state();
    if (prev_online != g.cp_online) {
        emit_state_changed("CpState", g.cp_state);
        if (g.cp_online) maybe_open_endpoints();
        else {
            g.sim_lock_valid = false; g.sim_ready_seen = false;
            g.cs_registration_valid = false;
            g.service_domain_valid = false;
            memset(g.home_plmn, 0, sizeof g.home_plmn);
            g.dsc.net_regist_valid = false; g.dsc.net_mode_valid = false;
            g.ip_received = false; g.dsc.ip_configured = false;
            g.link_down_requested = true;
            g.data_path_armed=false;g.dsc.phase=DS_IDLE;g.reconnect_at=now_ms()+30000;
            g.profiles_received = false;
            g.radio_state_valid = false;
            g.oes_requests = 0;
            g.dsc.ps_state_valid = false; g.dsc.attached = false;
            g.baseband[0] = 0;
        }
    }
    refresh_sim_state();

    /* Stage-06 data-session driver (opt-in, bounded). */
    data_session_tick(now_ms());
    sms_service_tick(&g.sms,now_ms(),g.cp_online,g.sim_ready_seen,
        sms_cs_registered(),
        ims_service_registered(&g.ims),
        g.write_enabled && g.fmt.present);
    /* Configure modem preferences; acknowledgments are not registration. */
    bool ims_online = g.cp_online && g.sim_ready_seen && g.write_enabled && g.fmt.present;
    ims_init_tick(&g.ims_init, now_ms(), ims_online);
    /* Observe the native IMS backend status (fail-closed),
     * gated on BOTH the ims APN PDN and completed device-capability init. */
    ims_service_tick(&g.ims,now_ms(),
        ims_online,
        g.ims_pdn_up && ims_init_done(&g.ims_init));
    /* Opt-in modem-managed IMS/ePDN profile sync. Off unless armed. Runs when
     * the internet data session is ACTIVE/WAIT_IP (quiet period) OR TERMINAL
     * (REJECTED/FAILED: idle, no active GEN correlation), so the IMS profile
     * is armed even when the internet bearer's IP config is absent. The IMS
     * profile only issues SetDataProfile(IMS) and never overlaps the internet
     * bearer's own command sequence. */
    if (!ims_online) {
        ims_pdn_tick(&g.ims_pdn, now_ms(), false);
        g.ims_pdn_up = false;
    }
    /* Only ONE IMS PDN driver may write the GPRS Define/Activate commands at
     * a time. When the recovered IIL path is armed, the FMT path is disabled
     * to avoid competing modem writers on main=13 sub=1/sub=4. */
    if (g.ims_pdn_armed && !g.iil_pdn_armed && ims_online &&
        (g.dsc.phase == DS_ACTIVE || g.dsc.phase == DS_WAIT_IP ||
         ds_terminal(&g.dsc))) {
        static enum ims_pdn_phase ims_pdn_last_diag = (enum ims_pdn_phase)0xff;
        ims_pdn_tick(&g.ims_pdn, now_ms(),
            g.cp_online && g.sim_ready_seen && g.write_enabled && g.fmt.present);
        if (g.ims_pdn.phase != ims_pdn_last_diag) {
            ims_pdn_last_diag = g.ims_pdn.phase;
            diagf("ims_pdn_phase", "\"phase\":\"%s\",\"attempt\":%u,\"cid\":%u",
                  ims_pdn_phase_name(g.ims_pdn.phase), g.ims_pdn.attempt, g.ims_pdn.cid);
        }
        if (ims_pdn_active(&g.ims_pdn) && !g.ims_pdn_up) {
            g.ims_pdn_up = true;
            diag("ims_pdn_active", NULL);
        } else if (!ims_pdn_active(&g.ims_pdn)) {
            g.ims_pdn_up = false;
            g.sip_param_sent = false;  /* re-arm on the next bearer epoch */
        }
        /* Configure the modem's internal IMS SIP stack (IpcTxSetSipParam)
         * with the recovered IPv6 P-CSCF + IMSI-derived IMPI once the bearer
         * is up AND the USIM identity is available. Retried every tick until
         * sent (identity readiness can lag the bearer by a few seconds). */
        if (g.ims_pdn_up && !g.sip_param_sent && g.ims.identity.ready)
            g.sip_param_sent = radiod_sip_param_from_fmt_pcscf(&g.ims_pdn);
    }
    /* IIL IMS APN PDN drive: recovered IpcProtocol41Iil Define/Activate for
     * the isolated CID-2 IMS bearer. Runs only when armed (--arm-data-path).
     * Does NOT overlap the internet bearer command sequence (it is serialized
     * behind the same endpoint write gate). */
    if (!ims_online) {
        iil_pdn_tick(&g.iil_pdn, now_ms(), false);
        g.sip_param_sent = false;   /* re-arm on next P-CSCF discovery */
    }
    /* Modem IMS SDM readback: query the modem's own carrier-provisioned
     * P-CSCF/domain/mode/SMS-over-IP before any IIL provisioner is armed, so
     * the recovered values (never fabricated) can be used downstream. Runs
     * continuously but is a bounded one-pass sequence per online epoch. */
    ims_sdm_tick(&g.ims_sdm, now_ms(), ims_online);
    if (g.iil_pdn_armed && ims_online &&
        (g.dsc.phase == DS_ACTIVE || g.dsc.phase == DS_WAIT_IP ||
         ds_terminal(&g.dsc))) {
        static enum iil_pdn_phase iil_pdn_last_diag = (enum iil_pdn_phase)0xff;
        iil_pdn_tick(&g.iil_pdn, now_ms(),
            g.cp_online && g.sim_ready_seen && g.write_enabled && g.fmt.present);
        if (g.iil_pdn.phase != iil_pdn_last_diag) {
            iil_pdn_last_diag = g.iil_pdn.phase;
            diagf("iil_pdn_phase", "\"phase\":\"%s\",\"attempt\":%u,\"cid\":%u",
                  iil_pdn_phase_name(g.iil_pdn.phase), g.iil_pdn.attempt, g.iil_pdn.cid);
        }
        if (iil_pdn_active(&g.iil_pdn)) {
            diag("iil_pdn_active", NULL);
        }
    }
    /* IIL AKA relay timeout handling (drop stale challenge). */
    iil_auth_tick(&g.iil_auth, now_ms());

    /* Native SIP/IMS transport + registration FSM (opens on IIL P-CSCF+IP). */
    sip_tr_tick(now_ms());

    call_service_tick(&g.calls,now_ms(),g.cp_online,g.write_enabled && g.fmt.present && g.sim_ready_seen);

    /* Read-only status refresh uses the same serialized transport, only while
     * the data transaction is idle/terminal so query replies cannot satisfy a
     * different transaction's registration gate. */
    if (g.write_enabled && g.cp_online && g.fmt.present &&
        (g.dsc.phase == DS_IDLE || ds_terminal(&g.dsc) || !g.sim_ready_seen) &&
        !mobile_stop_busy(&g.mobile_stop) && now_ms() >= g.status_next_ms) {
        struct fmt_tx_frame q;
        bool built = false;
        switch (g.status_query) {
        case 0: built = fmt_tx_get_sim_status(&q); break;
        case 1: built = fmt_tx_get_data_reg_state(&q); break;
        case 2: built = fmt_tx_get_preferred_net_type(&q); break;
        case 3: built = fmt_tx_get_pdp_context(&q); break;
        case 4: built = fmt_tx_get_serving_network(&q); break;
        case 5: built = fmt_tx_get_sim_network(&q); break;
        case 6: built = fmt_tx_get_ps_attach(&q); break;
        case 7: built = fmt_tx_get_baseband_version(&q); break;
        case 8: built = fmt_call_voice_registration(&q); break;
        case 9: built = fmt_tx_get_pdp_definitions(&q); break;
        case 10: built = fmt_tx_get_sim_apps_info(&q); break;
        }
        if (built && radiod_write_fmt(&q)) {
            g.status_query = (g.status_query + 1) % 11;
            g.status_next_ms = now_ms() + (g.status_query ? 1000 : 60000);
        } else g.status_next_ms = now_ms() + 5000;
    }

    uint64_t t = now_ms();
    unsigned i;
    for (i = 0; i < RADIOD_MAX_PENDING; i++) {
        if (g.pending[i].in_use && g.pending[i].deadline_ms && t >= g.pending[i].deadline_ms) {
            g.pending[i].in_use = false;
            g.stats.timeouts++;
            diagf("request_timeout", "\"main\":%u,\"sub\":%u",
                  g.pending[i].need_main, g.pending[i].need_sub);
        }
    }
    sd_event_source_set_time(g.tick_src, usec + 1000000ull);
    sd_event_source_set_enabled(g.tick_src, SD_EVENT_ON);
    return 0;
}

/* ------------------------------------------------------------------ */
/* D-Bus property getters                                              */
/* ------------------------------------------------------------------ */
static int prop_version(sd_bus *b, const char *p, const char *i, const char *prop,
                        sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    return sd_bus_message_append(reply, "u", 1u);
}
static int prop_api_rev(sd_bus *b, const char *p, const char *i, const char *prop,
                        sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    return sd_bus_message_append(reply, "s", "nuxel-radiod-1.0");
}
static int prop_daemon_state(sd_bus *b, const char *p, const char *i, const char *prop,
                             sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    const char *v = g.shutting_down ? "stopping"
                   : ((g.fmt.present || g.rfs.present) ? "running" : "degraded");
    return sd_bus_message_append(reply, "s", v);
}
static int prop_device_present(sd_bus *b, const char *p, const char *i, const char *prop,
                               sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    return sd_bus_message_append(reply, "b", (int)(g.fmt.present || g.rfs.present));
}
static int prop_cp_state(sd_bus *b, const char *p, const char *i, const char *prop,
                         sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    refresh_cp_state();
    return sd_bus_message_append(reply, "s", g.cp_state);
}
static int prop_radio_state(sd_bus *b, const char *p, const char *i, const char *prop,
                            sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    refresh_cp_state();
    const char *v = g.cp_online && g.radio_state_valid ? (g.radio_on ? "on" : "off") : "unknown";
    return sd_bus_message_append(reply, "s", v);
}
static int prop_sim_present(sd_bus *b, const char *p, const char *i, const char *prop,
                            sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    refresh_sim_state();
    return sd_bus_message_append(reply, "b", (int)g.sim_present);
}
static int prop_sim_pin(sd_bus *b, const char *p, const char *i, const char *prop,
                        sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    /* PIN-required is only knowable from an FMT SIM-status message. UNKNOWN. */
    return sd_bus_message_append(reply, "b", 0);
}
static int method_get_sim_state(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    return sd_bus_reply_method_return(m, "s", !g.sim_lock_valid ? "unknown" :
        !g.sim_present ? "absent" : g.sim_ready_seen ? "ready" : "locked-or-unavailable");
}

/* The native session owner and root may control the modem and read private
 * messages. The previous XML's polkit claim was not implemented. Check actual
 * sender credentials on the bus; never trust a caller-supplied UID. */
static int require_control(sd_bus_message *m,sd_bus_error *e)
{
    sd_bus_creds *creds=NULL;uid_t uid=(uid_t)-1;
    int r=sd_bus_query_sender_creds(m,SD_BUS_CREDS_EUID,&creds);
    if (r>=0) r=sd_bus_creds_get_euid(creds,&uid);
    sd_bus_creds_unref(creds);
    if (r<0 || (uid!=0 && uid!=g.control_uid))
        return sd_bus_error_set(e,SD_BUS_ERROR_ACCESS_DENIED,"Only root or the Nuxel session owner may control telephony or read messages");
    return 0;
}

static int require_data_control(sd_bus_message *m, sd_bus_error *e)
{
    sd_bus_creds *creds=NULL; uid_t uid=(uid_t)-1;
    int r=sd_bus_query_sender_creds(m,SD_BUS_CREDS_EUID,&creds);
    if(r>=0)r=sd_bus_creds_get_euid(creds,&uid);
    sd_bus_creds_unref(creds);
    if(r>=0 && uid==g.bridge_uid)return 0;
    return require_control(m,e);
}

static int prop_registered(sd_bus *b, const char *p, const char *i, const char *prop,
                           sd_bus_message *reply, void *u, sd_bus_error *e)
{
    (void)b;(void)p;(void)i;(void)prop;(void)u;(void)e;
    bool registered = g.cp_online && g.dsc.net_regist_valid &&
                      fmt_rx_registered(g.dsc.last_ps_reg_state);
    return sd_bus_message_append(reply, "b", (int)registered);
}

static int method_refresh_status(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;
    if (!g.write_enabled || !g.cp_online)
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "CP unavailable or command transport disabled");
    g.status_query = 0; g.status_next_ms = 0;
    return sd_bus_reply_method_return(m, "b", 1);
}

static int method_get_data_state(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    sd_bus_message *reply = NULL;
    int r = sd_bus_message_new_method_return(m, &reply);
    if (r < 0) return r;
    r = sd_bus_message_open_container(reply, 'a', "{ss}");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "phase", ds_phase_name(g.dsc.phase));
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "apn", (const char *)g.dsc.apn);
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "rat",
        g.dsc.net_regist_valid ? fmt_rx_rat_name(g.dsc.last_rat_wire) : "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "home_plmn", g.home_plmn);
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "baseband", g.baseband);
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "registration",
        g.dsc.net_regist_valid ? fmt_rx_reg_name(g.dsc.last_ps_reg_state) : "UNKNOWN");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "ps_attached",
        g.dsc.ps_state_valid ? (g.dsc.attached ? "true" : "false") : "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "ip_configured", g.dsc.ip_configured ? "true" : "false");
    const char *connection=g.mobile_enabled ? (g.dsc.ip_configured ? "connected" :
        g.data_path_armed ? "connecting" : !g.cp_online || !g.sim_ready_seen ? "unavailable" :
        g.dsc.net_regist_valid && !fmt_rx_registered(g.dsc.last_ps_reg_state) ? "no-service" :
        ds_terminal(&g.dsc) && g.dsc.phase!=DS_ACTIVE ? "failed" : "disconnected") :
        (mobile_stop_busy(&g.mobile_stop) || g.link.pid || g.link_down_requested ? "disconnecting" :
         g.mobile_stop.phase==MOBILE_STOP_FAILED || g.link.result ? "failed" : "disabled");
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","mobile_data_enabled",g.mobile_enabled ? "true" : "false");
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","connection_state",connection);
    char stop_result[24];snprintf(stop_result,sizeof stop_result,"%d",g.mobile_stop.result);
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","disconnect_result",stop_result);
    char link_result[16];
    snprintf(link_result,sizeof link_result,"%d",g.link.result);
    if (r >= 0) r = sd_bus_message_append(reply,"{ss}","link_result",link_result);
    char number[16];
    if(g.dsc.net_regist_valid)snprintf(number,sizeof number,"%u",g.dsc.last_reg_wire);
    else snprintf(number,sizeof number,"unknown");
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","registration_raw",number);
    char address[INET6_ADDRSTRLEN];
    if(g.dsc.ip_configured && g.ip_received && g.ip.ipv4_valid && inet_ntop(AF_INET,g.ip.ipv4,address,sizeof address))
        if(r>=0)r=sd_bus_message_append(reply,"{ss}","ipv4",address);
    if(g.dsc.ip_configured && g.ip_received && g.ip.ipv6_valid && inet_ntop(AF_INET6,g.ip.ipv6,address,sizeof address))
        if(r>=0)r=sd_bus_message_append(reply,"{ss}","ipv6",address);
    if (g.dsc.net_regist_valid) snprintf(number, sizeof number, "%u", g.dsc.last_reject_cause);
    else snprintf(number, sizeof number, "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "ps_reject_cause", number);
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "cs_registration",
        g.cs_registration_valid ? fmt_rx_reg_name(g.cs_registration.state) : "UNKNOWN");
    if (g.cs_registration_valid) snprintf(number, sizeof number, "%u", g.cs_registration.reject_cause);
    else snprintf(number, sizeof number, "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "cs_reject_cause", number);
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "failure_phase", ds_phase_name(g.dsc.failure_phase));
    if (g.dsc.failure_result_valid) snprintf(number, sizeof number, "0x%04x", g.dsc.failure_result);
    else snprintf(number, sizeof number, "unavailable");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "failure_result", number);
    if (g.service_domain_valid) snprintf(number, sizeof number, "%u", g.service_domain_wire);
    else snprintf(number, sizeof number, "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "service_domain_wire", number);
    if (g.dsc.ps_control_valid) snprintf(number, sizeof number, "%u", g.dsc.ps_control_state);
    else snprintf(number, sizeof number, "unknown");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "ps_control_state", number);
    if (r >= 0) r = sd_bus_message_close_container(reply);
    if (r >= 0) r = sd_bus_send(NULL, reply, NULL);
    sd_bus_message_unref(reply);
    return r;
}
static int method_get_ip_info(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u; (void)e;
    sd_bus_message *reply = NULL;
    int r = sd_bus_message_new_method_return(m, &reply);
    if (r < 0) return r;
    r = sd_bus_message_open_container(reply, 'a', "{ss}");
    if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "received", g.ip_received ? "true" : "false");
    if (g.ip_received) {
        const struct { const char *key; int family; const void *bytes; bool valid; } fields[] = {
            {"ipv4", AF_INET, g.ip.ipv4, g.ip.ipv4_valid},
            {"gateway4", AF_INET, g.ip.gateway4, g.ip.ipv4_valid},
            {"dns4_primary", AF_INET, g.ip.dns4[0], g.ip.ipv4_valid},
            {"dns4_secondary", AF_INET, g.ip.dns4[1], g.ip.ipv4_valid},
            {"ipv6", AF_INET6, g.ip.ipv6, g.ip.ipv6_valid},
            {"dns6_primary", AF_INET6, g.ip.dns6[0], g.ip.ipv6_valid},
            {"dns6_secondary", AF_INET6, g.ip.dns6[1], g.ip.ipv6_valid}
        };
        for (size_t i = 0; i < sizeof fields / sizeof fields[0] && r >= 0; i++) {
            char address[INET6_ADDRSTRLEN] = "";
            if (fields[i].valid && !inet_ntop(fields[i].family, fields[i].bytes, address, sizeof address))
                return sd_bus_message_unref(reply), -errno;
            r = sd_bus_message_append(reply, "{ss}", fields[i].key, address);
        }
        char value[16];
        snprintf(value, sizeof value, "%u", g.ip.cid);
        if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "cid", value);
        snprintf(value, sizeof value, "%u", g.ip.flags);
        if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "flags", value);
        snprintf(value, sizeof value, "%u", g.ip.mtu);
        if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "mtu", value);
        snprintf(value, sizeof value, "%u", g.ip.prefix4);
        if (r >= 0) r = sd_bus_message_append(reply, "{ss}", "prefix4", value);
    }
    if (r >= 0) r = sd_bus_message_close_container(reply);
    if (r >= 0) r = sd_bus_send(NULL, reply, NULL);
    sd_bus_message_unref(reply);
    return r;
}

static int method_get_pdp_profiles(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;
    if (!g.profiles_received)
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"No valid CP PDP definition response received");
    sd_bus_message *reply = NULL;
    int r = sd_bus_message_new_method_return(m,&reply);
    if (r >= 0) r = sd_bus_message_open_container(reply,'a',"(yysyy)");
    for (unsigned i = 0; i < g.profiles.count && r >= 0; i++) {
        const struct fmt_rx_pdp_profile *p = &g.profiles.profile[i];
        r = sd_bus_message_append(reply,"(yysyy)",p->cid,p->protocol_wire,p->apn,
                                  p->data_compression,p->header_compression);
    }
    if (r >= 0) r = sd_bus_message_close_container(reply);
    if (r >= 0) r = sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);
    return r;
}

static int method_get_ims_status(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u; (void)e;
    const char *keys[]={"state","reason","usim_identity_ready","profile_phase",
        "cid_attached","ip_ready","pcscf_ready","context_ready","init_phase",
        "auth_pending","registered","sms_transport"};
    const char *vals[]={ims_phase_name(g.ims.phase),
        g.ims.last_reason ? g.ims.last_reason : "not-started",
        g.ims.identity.ready ? "true" : "false",ims_pdn_phase_name(g.ims_pdn.phase),
        g.ims_pdn.attached ? "true" : "false",g.ims_pdn.ip_ready ? "true" : "false",
        g.ims_pdn.pcscf_ready ? "true" : "false",ims_pdn_active(&g.ims_pdn) ? "true" : "false",
        ims_init_phase_name(g.ims_init.phase),g.ims.auth_pending ? "true" : "false",
        ims_service_registered(&g.ims) ? "true" : "false","unavailable"};
    sd_bus_message *reply=NULL;
    int r=sd_bus_message_new_method_return(m,&reply);
    if (r>=0) r=sd_bus_message_open_container(reply,'a',"{ss}");
    for (unsigned i=0;i<sizeof keys/sizeof keys[0] && r>=0;i++)
        r=sd_bus_message_append(reply,"{ss}",keys[i],vals[i]);
    if (r>=0) r=sd_bus_message_close_container(reply);
    if (r>=0) r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);
    return r;
}

static int method_get_capabilities(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    sd_bus_message *reply = NULL;
    if (sd_bus_message_new_method_return(m, &reply) < 0) return -1;
    sd_bus_message_open_container(reply, 'a', "{ss}");
    const char *lte = (g.dsc.phase == DS_ACTIVE) ? "active" :
                      (g.data_path_armed ? "pending" : "unsupported");
    const char *ims = ims_service_registered(&g.ims) ? "registered" :
                       (g.ims.phase == IMS_WAIT_BACKEND ? "backend-missing" :
                        g.ims.phase == IMS_FAILED ? "failed" :
                        (g.ims_pdn_up ? "attempting" : "unsupported"));
    const char *keys[] = {"lte_data","sms","voice","ims","volte"};
    const char *vals[] = {lte, g.sms.store.db ? (ims_service_registered(&g.ims) ? "ready" : "cs-only") : "unavailable", "call-control-only", ims, ims_service_registered(&g.ims) ? "false" : "false"};
    for (unsigned i = 0; i < 5; i++) {
        sd_bus_message_append(reply, "{ss}", keys[i], vals[i]);
    }
    sd_bus_message_close_container(reply);
    int r = sd_bus_send(NULL, reply, NULL);
    sd_bus_message_unref(reply);
    return r;
}
static int method_set_radio(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    int access=require_control(m,e);if (access<0) return access;
    int en = 0;
    if (sd_bus_message_read(m, "b", &en) < 0)
        return sd_bus_error_set(e, SD_BUS_ERROR_INVALID_ARGS, "bad arg");
    if (!g.write_enabled || !g.cp_online)
        return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED, "radio transport unavailable");
    if (g.data_path_armed && !ds_terminal(&g.dsc))
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "data transaction in progress");
    struct fmt_tx_frame f;
    if (!fmt_tx_radio_power(&f, en != 0) || !radiod_write_fmt(&f))
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "radio command write failed");
    g.radio_state_valid = false;
    diagf("radio_power_requested", "\"on\":%s", en ? "true" : "false");
    g.status_query = 0; g.status_next_ms = 0;
    return sd_bus_reply_method_return(m, "");
}
static int method_select_auto(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;
    int access=require_control(m,e);if (access<0) return access;
    if (!g.write_enabled || !g.cp_online)
        return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED, "radio transport unavailable");
    if (g.data_path_armed && !ds_terminal(&g.dsc))
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "data transaction in progress");
    struct fmt_tx_frame f;
    if (!fmt_tx_net_selection_auto(&f) || !radiod_write_fmt(&f))
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "network selection command write failed");
    diag("network_selection_auto_requested", NULL);
    g.status_query = 0; g.status_next_ms = 0;
    return sd_bus_reply_method_return(m, "");
}
static int method_get_signal(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    /* No FMT signal source known -> unavailable, never fabricated. */
    return sd_bus_reply_method_return(m, "iiib", 0, 0, 0, 0);
}
static int method_get_operators(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    sd_bus_message *reply = NULL;
    if (sd_bus_message_new_method_return(m, &reply) < 0) return -1;
    sd_bus_message_open_container(reply, 'a', "(ss)");
    sd_bus_message_close_container(reply);
    int r = sd_bus_send(NULL, reply, NULL);
    sd_bus_message_unref(reply);
    return r;
}
static int method_packet_stats(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    return sd_bus_reply_method_return(m, "ttb", (uint64_t)0, (uint64_t)0, 0);
}
/* Map NUXEL_PROTO env string -> fmt_tx_data_protocol numeric value.
 * Accepted: ip|ipv4 -> 2 (IPv4-only), ipv6 -> 3, ipv4v6|ipv6v4|dual -> 4.
 * Default -> IPv4, which this CP accepts for the initial profile. */
static uint8_t env_protocol(void)
{
    const char *p = getenv("NUXEL_PROTO");
    if (!p || !*p || !strcasecmp(p, "default")) return FMT_TX_PROTO_IP;
    if (!strcasecmp(p, "ip") || !strcasecmp(p, "ipv4")) return FMT_TX_PROTO_IP;
    if (!strcasecmp(p, "ipv6")) return FMT_TX_PROTO_IPV6;
    if (!strcasecmp(p, "ipv4v6") || !strcasecmp(p, "ipv6v4") ||
        !strcasecmp(p, "dual"))
        return FMT_TX_PROTO_IPV4V6;
    return FMT_TX_PROTO_IP;
}

/* Map NUXEL_ATTACH_FLAG env string -> SetLteAttachProfile payload[0] flag.
 * 1 creates profile zero. 3 selects PMPM_AddAlwaysOnProfile, not initial APN.
 * Unknown -> 1. */
static uint8_t env_attach_flag(void)
{
    const char *p = getenv("NUXEL_ATTACH_FLAG");
    if (!p || !*p) return 1u;
    long v = strtol(p, NULL, 10);
    if (v == 1 || v == 3) return (uint8_t)v;
    return 1u;
}

static uint8_t env_preferred_net(void)
{
    const char *p = getenv("NUXEL_NETWORK_MODE");
    return p && !strcmp(p, "lte") ? FMT_TX_PREFERRED_NET_LTE_ONLY : FMT_TX_PREFERRED_NET_LTE_AUTO;
}

/* Map NUXEL_ATTACH_CID env string -> attach/context CID.
 * Accepted: 1 (default, single-SIM), 5 (DSDS/second-slot), 2..15 raw.
 * Unknown -> 1 (DS_ATTACH_CID). */
static uint8_t env_attach_cid(void)
{
    const char *p = getenv("NUXEL_ATTACH_CID");
    if (!p || !*p) return DS_ATTACH_CID;
    long v = strtol(p, NULL, 10);
    if (v >= 1 && v <= 15) return (uint8_t)v;
    return DS_ATTACH_CID;
}

/* Map configuration to DataAuth; no-auth is 0 in ALL serializers. */
static uint8_t env_auth(void)
{
    const char *p = getenv("NUXEL_AUTH");
    if (p && !strcasecmp(p, "pap")) return FMT_TX_AUTH_PAP;
    if (p && !strcasecmp(p, "chap")) return FMT_TX_AUTH_CHAP;
    return FMT_TX_AUTH_NONE;
}

/* Map NUXEL_PDP_TYPE env string -> SetPdpContext payload[0] wire-byte selector.
 * full=1 (default; APN + flags path), lte=4, legacy=3, 2..8 raw. Unknown -> 1. */
static uint8_t env_pdp_type(void)
{
    const char *p = getenv("NUXEL_PDP_TYPE");
    if (!p || !*p) return FMT_TX_PDP_TYPE_DEFAULT;
    if (!strcasecmp(p, "full") || !strcasecmp(p, "1")) return FMT_TX_PDP_TYPE_FULL;
    if (!strcasecmp(p, "lte")  || !strcasecmp(p, "eutran") || !strcasecmp(p, "4"))
        return FMT_TX_PDP_TYPE_LTE;
    if (!strcasecmp(p, "legacy") || !strcasecmp(p, "3")) return FMT_TX_PDP_TYPE_LEGACY;
    long v = strtol(p, NULL, 10);
    if (v >= 1 && v <= 8) return (uint8_t)v;
    return FMT_TX_PDP_TYPE_DEFAULT;
}

/* Opt-in gate for the recovered MBIM MS LTE Attach Config (CID 0x0A) path.
 * OFF by default: the default FMT GPRS path is unchanged until the MBIM
 * attach-config transport is live-validated on hardware. */
static bool mbim_attach_enabled(void)
{
    const char *p = getenv("NUXEL_MBIM_ATTACH");
    return p && (!strcasecmp(p, "1") || !strcasecmp(p, "on") ||
                 !strcasecmp(p, "true") || !strcasecmp(p, "yes"));
}

static void begin_data_session(const char *apn)
{
    char saved_apn[101];snprintf(saved_apn,sizeof saved_apn,"%s",apn);
    ds_reset(&g.dsc, saved_apn, 1);
    g.link_attempted = false;
    memset(&g.ip, 0, sizeof g.ip); g.ip_received = false;
    g.dsc.protocol = env_protocol();
    g.dsc.preferred_net = env_preferred_net();
    g.dsc.attach_flag = env_attach_flag();
    g.dsc.auth_code = env_auth();
    g.dsc.pdp_type_wire = env_pdp_type();
    g.dsc.attach_cid = env_attach_cid();
    g.dsc.reattach_for_apn = getenv("NUXEL_REATTACH_IA") &&
        !strcmp(getenv("NUXEL_REATTACH_IA"), "1");
    g.data_path_armed = true;
    g.wrote_phase = false;
    g.dsc.step_deadline_ms = 0;
    diagf("data_session_start", "\"apn\":\"%s\",\"profile\":%u,\"protocol\":%u,\"pdp_type\":%u",
          saved_apn, 1u, g.dsc.protocol, g.dsc.pdp_type_wire);
}

static int method_start_data_session(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    int access=require_data_control(m,e);if (access<0) return access;
    const char *apn = NULL;
    uint32_t profile = 1;
    int r = sd_bus_message_read(m, "s", &apn);
    if (r < 0) apn = "internet";
    /* Reserve a future uint32 profile argument; tolerate missing arg. */
    (void)sd_bus_message_read(m, "u", &profile);

    if (!g.write_enabled) {
        return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED,
            "data-path TX disabled (start radiod with --write-enable)");
    }
    if (!g.cp_online) {
        return sd_bus_error_set(e, SD_BUS_ERROR_FAILED, "CP offline");
    }
    if (!apn || !*apn || strlen(apn) > 100 || profile != 1 ||
        strspn(apn, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-") != strlen(apn))
        return sd_bus_error_set(e, SD_BUS_ERROR_INVALID_ARGS, "invalid APN or unsupported profile (use 1)");
    if(mobile_stop_busy(&g.mobile_stop) || g.link_down_requested || g.link.pid)
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Mobile data operation in progress");
    if(g.data_path_armed && (g.dsc.phase==DS_ACTIVE || !ds_terminal(&g.dsc))) {
        if(strcmp(apn,(const char *)g.dsc.apn))return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Stop data before changing APN");
        return sd_bus_reply_method_return(m,"b",1);
    }
    if(mobile_preference_save(MOBILE_PREFERENCE,true)<0)
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Could not persist mobile data preference");
    g.mobile_enabled=true;g.mobile_stop.phase=MOBILE_STOP_IDLE;
    g.reconnect_attempts=0;g.reconnect_at=now_ms()+30000;
    begin_data_session(apn);
    emit_state_changed("MobileDataEnabled","true");
    return sd_bus_reply_method_return(m, "b", 1);
}

static int method_stop_data_session(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    int access=require_data_control(m,e);if (access<0) return access;
    if(!g.write_enabled)return sd_bus_error_set(e,SD_BUS_ERROR_ACCESS_DENIED,"Data transport disabled");
    if(mobile_stop_busy(&g.mobile_stop) || (!g.mobile_enabled && g.mobile_stop.phase==MOBILE_STOP_DONE &&
       !g.link.pid && !g.link_down_requested && !g.link.result))return sd_bus_reply_method_return(m,"b",1);
    if(g.data_path_armed && !ds_terminal(&g.dsc))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Connecting; wait for this bounded operation to finish");
    if(mobile_preference_save(MOBILE_PREFERENCE,false)<0)
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Could not persist mobile data preference");
    g.mobile_enabled=false;g.data_path_armed=false;g.wrote_phase=false;
    g.dsc.ip_configured=false;g.ip_received=false;g.link_down_requested=true;
    mobile_stop_begin(&g.mobile_stop);
    emit_state_changed("MobileDataEnabled","false");
    diag("data_session_stop_requested",NULL);
    return sd_bus_reply_method_return(m, "b", 1);
}

static int method_no_bearer(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)m; (void)u;
    return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED,
                            "bearer control not implemented (vocab UNKNOWN)");
}

static int method_send_sms(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if (r<0) return r;
    if (!g.write_enabled || !g.sms.store.db || g.sms.blocked)
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"SMS transport disabled, storage unavailable, or unresolved submission");
    const char *to,*text;
    if (sd_bus_message_read(m,"ss",&to,&text)<0)
        return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Recipient and UTF-8 text required");
    struct sms_encoded encoded;enum sms_codec_result result=sms_encode(to,text,0,0,&encoded);
    if (result!=SMS_CODEC_OK) return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,sms_codec_name(result));
    uint32_t id;
    if (!sms_store_queue(&g.sms.store,to,text,&id))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Could not durably queue SMS or reserve message references");
    sms_notify(id,false,NULL);
    return sd_bus_reply_method_return(m,"u",id);
}

static int method_resolve_sms(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    uint32_t id;const char *outcome;
    if (sd_bus_message_read(m,"us",&id,&outcome)<0)
        return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Message ID and outcome ('failed', 'delivered' or 'superseded') required");
    if (strcmp(outcome,"failed") && strcmp(outcome,"delivered") && strcmp(outcome,"superseded"))
        return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Outcome must be 'failed', 'delivered' or 'superseded'");
    if (!sms_service_resolve(&g.sms,id,outcome))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Message is not in an unresolved state or storage is unavailable");
    return sd_bus_reply_method_return(m,"b",1);
}

static int method_list_sms(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    if (!g.sms.store.db) return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"SMS storage unavailable");
    uint32_t ids[256];size_t n=sms_store_list(&g.sms.store,ids,256);sd_bus_message *reply=NULL;
    r=sd_bus_message_new_method_return(m,&reply);
    if (r>=0) r=sd_bus_message_append_array(reply,'u',ids,n*sizeof ids[0]);
    if (r>=0) r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);return r;
}

static int method_get_sms(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    uint32_t id;struct sms_record record;
    if (sd_bus_message_read(m,"u",&id)<0) return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Message ID required");
    if (!sms_store_get(&g.sms.store,id,&record)) return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Message unavailable");
    sd_bus_message *reply=NULL;r=sd_bus_message_new_method_return(m,&reply);
    if(r>=0)r=sd_bus_message_open_container(reply,'a',"{ss}");
    const char *keys[]={"direction","peer","text","state","timestamp"};
    const char *vals[]={record.direction,record.peer,record.text,record.state,record.timestamp};
    for(size_t i=0;i<5 && r>=0;i++)r=sd_bus_message_append(reply,"{ss}",keys[i],vals[i]);
    char value[32];snprintf(value,sizeof value,"%u",record.parts);
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","parts",value);
    snprintf(value,sizeof value,"%d",record.error);
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","error",value);
    if(r>=0)r=sd_bus_message_close_container(reply);
    if(r>=0)r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);return r;
}

static int method_get_sms_status(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;(void)e;sd_bus_message *reply=NULL;int r=sd_bus_message_new_method_return(m,&reply);
    if(r>=0)r=sd_bus_message_open_container(reply,'a',"{ss}");
    const char *keys[]={"storage","device_ready","smsc","pending","blocked","domain","delivery_verified","ready","registration"};
    const char *vals[]={g.sms.store.db ? "available" : "unavailable",
        g.sms.ready_rejected ? "rejected" : g.sms.ready_ack ? "accepted" : g.sms.ready_sent ? "sent" : "unknown",
        g.sms.smsc_len ? "received" : "unknown",g.sms.active ? "true" : "false",
        g.sms.blocked ? "true" : "false","CS",
        sms_store_any_delivered(&g.sms.store) ? "true" : "false",
        g.write_enabled && g.cp_online && g.sim_ready_seen && g.sms.store.db && g.sms.ready_ack &&
        g.sms.smsc_len && !g.sms.active && !g.sms.blocked &&
        sms_cs_registered() ? "true" : "false",
        sms_cs_registered() ? "registered" : "cs-denied"};
    for(size_t i=0;i<9 && r>=0;i++)r=sd_bus_message_append(reply,"{ss}",keys[i],vals[i]);
    if(r>=0)r=sd_bus_message_close_container(reply);
    if(r>=0)r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);return r;
}

static int method_dial(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    const char *number;
    if(sd_bus_message_read(m,"s",&number)<0)return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Phone number required");
    if(!strcmp(number,"112") || !strcmp(number,"911"))
        return sd_bus_error_set(e,SD_BUS_ERROR_NOT_SUPPORTED,"Emergency-call procedure is not implemented");
    struct fmt_tx_frame check;
    if(!fmt_call_dial(&check,number))return sd_bus_error_set(e,SD_BUS_ERROR_INVALID_ARGS,"Invalid phone number");
    if(!g.write_enabled || !g.cp_online || !g.sim_ready_seen || !call_service_dial(&g.calls,number,now_ms()))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Call transport unavailable, calls unknown/active, or previous setup unresolved");
    return sd_bus_reply_method_return(m,"b",1);
}
static int method_answer_call(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    if(!g.write_enabled || !g.cp_online || !call_service_answer(&g.calls,now_ms()))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"No confirmed incoming call or command transport unavailable");
    return sd_bus_reply_method_return(m,"b",1);
}
static int method_hangup_call(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    if(!g.write_enabled || !g.cp_online || !call_service_hangup(&g.calls,now_ms()))
        return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"Call release write failed");
    return sd_bus_reply_method_return(m,"b",1);
}
static int method_get_calls(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;int r=require_control(m,e);if(r<0)return r;
    if(!g.calls.list_valid)return sd_bus_error_set(e,SD_BUS_ERROR_FAILED,"CP call list unavailable or unsupported");
    sd_bus_message *reply=NULL;r=sd_bus_message_new_method_return(m,&reply);
    if(r>=0)r=sd_bus_message_open_container(reply,'a',"(ussb)");
    for(size_t i=0;i<g.calls.list.count && r>=0;i++) {
        const struct fmt_call *c=&g.calls.list.calls[i];
        r=sd_bus_message_append(reply,"(ussb)",(uint32_t)c->id,fmt_call_state_name(c->state),c->number,c->direction==2);
    }
    if(r>=0)r=sd_bus_message_close_container(reply);
    if(r>=0)r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);return r;
}
static int method_get_voice_status(sd_bus_message *m,void *u,sd_bus_error *e)
{
    (void)u;(void)e;sd_bus_message *reply=NULL;int r=sd_bus_message_new_method_return(m,&reply);
    if(r>=0)r=sd_bus_message_open_container(reply,'a',"{ss}");
    const char *keys[]={"registration","call_list","pending","audio_route","ims"};
    const char *vals[]={g.cs_registration_valid ? fmt_rx_reg_name(g.cs_registration.state) : "UNKNOWN",
        g.calls.list_valid ? "received" : "unknown",g.calls.pending || g.calls.dial_waiting ? "true" : "false","unconfigured","unimplemented"};
    for(size_t i=0;i<5 && r>=0;i++)r=sd_bus_message_append(reply,"{ss}",keys[i],vals[i]);
    char value[32];
    if(g.cs_registration_valid)snprintf(value,sizeof value,"%u",g.cs_registration.reject_cause);else snprintf(value,sizeof value,"unknown");
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","registration_cause",value);
    snprintf(value,sizeof value,"%d",g.calls.result);
    if(r>=0)r=sd_bus_message_append(reply,"{ss}","command_result",value);
    if(g.calls.status_valid) {
        snprintf(value,sizeof value,"%u",g.calls.status.state);
        if(r>=0)r=sd_bus_message_append(reply,"{ss}","status_wire",value);
        snprintf(value,sizeof value,"%u/%u",g.calls.status.cause_class,g.calls.status.cause);
        if(r>=0)r=sd_bus_message_append(reply,"{ss}","cause_wire",value);
    }
    if(r>=0)r=sd_bus_message_close_container(reply);
    if(r>=0)r=sd_bus_send(NULL,reply,NULL);
    sd_bus_message_unref(reply);return r;
}

/* GetDiagnostics: redacted, aggregate counters ONLY. No payload/identifiers. */
static int method_get_diagnostics(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u; (void)e;
    sd_bus_message *reply = NULL;
    int r = sd_bus_message_new_method_return(m, &reply);
    if (r < 0) return r;
    r = sd_bus_message_open_container(reply, 'a', "{st}");
    if (r < 0) goto out;
    struct { const char *k; uint64_t v; } kv[] = {
        {"RxFrames",       g.stats.rx_frames},
        {"RxBytes",        g.stats.rx_bytes},
        {"TxFrames",       g.stats.tx_frames},
        {"ParseTruncated", g.stats.parse_truncated},
        {"ParseErrors",    g.stats.parse_errors},
        {"OverflowDrops",  g.stats.overflow_drops},
        {"UnknownCmd",     g.stats.unknown_cmd},
        {"RawFrames",      g.stats.raw_frames},
        {"RawBytes",       g.stats.raw_bytes},
        {"RfsOps",         g.stats.rfs_ops},
        {"RfsDestructive", g.stats.rfs_destructive},
        {"RawUnclassified",g.stats.raw_rx_unclassified},
        {"RfsResponses",   g.stats.rfs_responses},
        {"RfsRespErrors",  g.stats.rfs_resp_errors},
        {"Disconnects",    g.stats.disconnects},
        {"Reconnects",     g.stats.reconnects},
        {"Timeouts",       g.stats.timeouts},
        {"Permissions",    g.stats.permissions},
        {"SmsReceived",    g.sms.received},
        {"SmsDecodeErrors",g.sms.decode_errors},
        {"SmsStoreErrors", g.sms.store_errors},
        {"SmsAckErrors",   g.sms.ack_errors},
        {"SmsUnmatched",   g.sms.unmatched},
        {"CallParseErrors",g.calls.parse_errors},
        {"CallUnmatched",  g.calls.unmatched},
    };
    for (unsigned i = 0; i < sizeof(kv)/sizeof(kv[0]); i++) {
        r = sd_bus_message_append(reply, "{st}", kv[i].k, kv[i].v);
        if (r < 0) goto out;
    }
    r = sd_bus_message_close_container(reply);
    if (r < 0) goto out;
    r = sd_bus_send(NULL, reply, NULL);
out:
    sd_bus_message_unref(reply);
    return r;
}

static const sd_bus_vtable radiod_vtable[] = {
    SD_BUS_VTABLE_START(0),
    SD_BUS_PROPERTY("Version", "u", prop_version, 0, SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("ApiRevision", "s", prop_api_rev, 0, SD_BUS_VTABLE_PROPERTY_CONST),
    SD_BUS_PROPERTY("DaemonState", "s", prop_daemon_state, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_PROPERTY("DevicePresent", "b", prop_device_present, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_PROPERTY("CpState", "s", prop_cp_state, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_PROPERTY("RadioState", "s", prop_radio_state, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_METHOD("SetRadioEnabled", "b", "", method_set_radio, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("SelectNetworkAutomatic", "", "", method_select_auto, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_PROPERTY("SimPresent", "b", prop_sim_present, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_PROPERTY("SimPinRequired", "b", prop_sim_pin, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_METHOD("GetSimState", "", "s", method_get_sim_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_PROPERTY("Registered", "b", prop_registered, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_METHOD("RefreshStatus", "", "b", method_refresh_status, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetDataSessionState", "", "a{ss}", method_get_data_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetIpInfo", "", "a{ss}", method_get_ip_info, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetPdpProfiles", "", "a(yysyy)", method_get_pdp_profiles, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("SendSms", "ss", "u", method_send_sms, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("ResolveSms", "us", "b", method_resolve_sms, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("ListSms", "", "au", method_list_sms, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetSms", "u", "a{ss}", method_get_sms, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetSmsStatus", "", "a{ss}", method_get_sms_status, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("Dial", "s", "b", method_dial, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("AnswerCall", "", "b", method_answer_call, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("HangupCall", "", "b", method_hangup_call, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetCalls", "", "a(ussb)", method_get_calls, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetVoiceStatus", "", "a{ss}", method_get_voice_status, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetSignalInfo", "", "iiib", method_get_signal, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetAvailableOperators", "", "a(ss)", method_get_operators, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetPacketStats", "", "ttb", method_packet_stats, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("CreateBearer", "s", "u", method_no_bearer, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("DeleteBearer", "u", "", method_no_bearer, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("StartDataSession", "su", "b", method_start_data_session, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("StopDataSession", "", "b", method_stop_data_session, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetImsStatus", "", "a{ss}", method_get_ims_status, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetCapabilities", "", "a{ss}", method_get_capabilities, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetDiagnostics", "", "a{st}", method_get_diagnostics, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_SIGNAL("StateChanged", "ss", 0),
    SD_BUS_SIGNAL("CpReset", "", 0),
    SD_BUS_SIGNAL("SmsReceived", "u", 0),
    SD_BUS_SIGNAL("SmsStateChanged", "us", 0),
    SD_BUS_SIGNAL("IncomingCall", "u", 0),
    SD_BUS_SIGNAL("CallStateChanged", "us", 0),
    SD_BUS_VTABLE_END
};

/* ------------------------------------------------------------------ */
/* lifecycle                                                            */
/* ------------------------------------------------------------------ */
static int on_signal(sd_event_source *s, const struct signalfd_siginfo *si, void *u)
{
    (void)s;(void)si;(void)u;
    g.shutting_down = true;
    if (g.loop) sd_event_exit(g.loop, 0);
    return 0;
}

static const sd_bus_vtable mobile_vtable[] = {
    SD_BUS_VTABLE_START(0),
    SD_BUS_METHOD("GetSimState", "", "s", method_get_sim_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetDataSessionState", "", "a{ss}", method_get_data_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("StartDataSession", "su", "b", method_start_data_session, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("StopDataSession", "", "b", method_stop_data_session, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_VTABLE_END
};

static int setup_dbus(void)
{
    int system_result=sd_bus_open_system(&g.data_bus);
    if(system_result>=0)system_result=sd_bus_add_object_vtable(g.data_bus,NULL,OBJ_PATH,IFACE_NAME,mobile_vtable,NULL);
    if(system_result>=0)system_result=sd_bus_request_name(g.data_bus,DEST_NAME,0);
    if(system_result>=0)system_result=sd_bus_attach_event(g.data_bus,g.loop,SD_EVENT_PRIORITY_NORMAL);
    if(system_result<0)return system_result;

    return setup_session_bus();
}

static int setup_session_bus(void)
{
    /* Nuxel services live on the Wayland session bus (same convention as
     * nuxel-soundd/portal/bridge). Fall back to the system bus for portability. */
    const char *addr = getenv("NUXEL_DBUS_ADDRESS");
    if (!addr || !addr[0]) addr = "unix:path=/run/nuxel-wayland/bus";
    int r = sd_bus_new(&g.bus);
    if (r >= 0) r = sd_bus_set_address(g.bus, addr);
    if (r >= 0) r = sd_bus_set_bus_client(g.bus, 1);
    if (r >= 0) r = sd_bus_start(g.bus);
    if (r < 0) {
        /* fallback: system bus */
        sd_bus_unref(g.bus);
        g.bus = NULL;
        /* Mobile policy is available independently of graphical login. */
        diag("session_bus_unavailable",NULL);
        return 0;
    }
    if (r < 0) { diagf("dbus_connect_failed", "\"err\":%d", r); return r; }
    r = sd_bus_add_object_vtable(g.bus, NULL, OBJ_PATH, IFACE_NAME, radiod_vtable, NULL);
    if (r < 0) { diagf("dbus_vtable_failed", "\"err\":%d", r); return r; }
    r = sd_bus_request_name(g.bus, DEST_NAME, 0);
    if (r < 0) { diagf("dbus_name_failed", "\"err\":%d", r); return r; }
    sd_bus_attach_event(g.bus, g.loop, SD_EVENT_PRIORITY_NORMAL);
    diagf("dbus_ready", "\"bus_name\":\"%s\"", DEST_NAME);
    return 0;
}

static int setup_event(void)
{
    int r = sd_event_default(&g.loop);
    if (r < 0) return r;

    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGTERM);
    sigaddset(&mask, SIGINT);
    sigprocmask(SIG_BLOCK, &mask, NULL);
    sd_event_add_signal(g.loop, &g.sig_src[0], SIGTERM, on_signal, NULL);
    sd_event_add_signal(g.loop, &g.sig_src[1], SIGINT, on_signal, NULL);
    return 0;
}

int main(int argc, char **argv)
{
    memset(&g, 0, sizeof g);
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--write-enable") == 0) {
            g.write_enabled = true;
        } else if (strcmp(argv[i], "--arm-data-path") == 0) {
            g.write_enabled = true;
            g.data_path_armed = true;
            ds_reset(&g.dsc, getenv("NUXEL_APN") ? getenv("NUXEL_APN") : "internet", 1);
            g.dsc.protocol = env_protocol();
            g.dsc.preferred_net = env_preferred_net();
            g.dsc.attach_flag = env_attach_flag();
            g.dsc.auth_code = env_auth();
            g.dsc.pdp_type_wire = env_pdp_type();
            g.dsc.attach_cid = env_attach_cid();
        } else if (strcmp(argv[i], "--help") == 0) {
            fprintf(stderr, "usage: nuxel-radiod [--write-enable] [--arm-data-path]\n");
            return 0;
        }
    }
    g.mobile_enabled=g.data_path_armed;
    if(mobile_preference_load(MOBILE_PREFERENCE,&g.mobile_enabled)<0)
        diag("mobile_preference_invalid_disabled",NULL);
    if(g.mobile_enabled && g.write_enabled && !g.data_path_armed)
        begin_data_session(getenv("NUXEL_APN") ? getenv("NUXEL_APN") : "internet");
    if(!g.mobile_enabled) {
        g.data_path_armed=false;g.dsc.phase=DS_IDLE;
        if(g.write_enabled)mobile_stop_begin(&g.mobile_stop);
    }
    g.link_down_requested=g.write_enabled; /* reconcile a previous helper journal */
    g.fmt.dev.fd = -1;
    g.rfs.dev.fd = -1;
    g.cp_state_code = -1;
    snprintf(g.cp_state, sizeof g.cp_state, "UNKNOWN");
    struct passwd *owner=getpwnam("nuxel");g.control_uid=owner ? owner->pw_uid : 0;
    owner=getpwnam("nuxel-bridge");g.bridge_uid=owner ? owner->pw_uid : 0;
    const char *sms_path=getenv("NUXEL_SMS_DATABASE");
    if (!sms_path || !*sms_path) sms_path="/var/lib/nuxel-radio/sms.sqlite3";
    if (!sms_service_open(&g.sms,sms_path,sms_write,sms_notify,NULL)) diag("sms_storage_unavailable",NULL);
    else sms_service_set_result_diag(&g.sms,sms_result_diag);
    call_service_init(&g.calls,sms_write,call_notify,NULL);
    ims_service_open(&g.ims,ims_write,ims_state_diag,NULL);
    ims_pdn_open(&g.ims_pdn,ims_pdn_write,NULL);
    iil_pdn_open(&g.iil_pdn,iil_pdn_write,NULL);
    /* IMS DataProfile (type 2) sync via the FMT GPRS SET_DATA_PROFILE path
     * before the IIL Define/Activate. This is the missing provisioning step
     * that seeds the modem's IMS APN profile. Shared sequence space. */
    iil_pdn_set_fmt_write(&g.iil_pdn, ims_pdn_write, NULL);
    iil_auth_open(&g.iil_auth,iil_auth_iil_write,iil_auth_usim_write,NULL);
    ims_init_open(&g.ims_init,ims_write,NULL);
    ims_sdm_open(&g.ims_sdm,ims_sdm_write,NULL);
    g.ims_pdn_armed = false;
    {
        const char *imens = getenv("NUXEL_IMS_PDN");
        g.ims_pdn_armed = imens && (!strcasecmp(imens,"1") || !strcasecmp(imens,"on") ||
                                    !strcasecmp(imens,"true") || !strcasecmp(imens,"yes"));
        diagf("ims_pdn_config", "\"armed\":%s", g.ims_pdn_armed ? "true" : "false");
    }
    /* IIL (IpcProtocol41Iil) IMS PDN drive: usable only with --write-enable.
     * Independently opted-in so the FMT path stays available for rollback. */
    g.iil_pdn_armed = false;
    {
        const char *iil = getenv("NUXEL_IIL_PDN");
        if (iil && (!strcasecmp(iil,"1") || !strcasecmp(iil,"on") ||
                    !strcasecmp(iil,"true") || !strcasecmp(iil,"yes"))) {
            g.iil_pdn_armed = g.write_enabled;
        }
        diagf("iil_pdn_config", "\"armed\":%s", g.iil_pdn_armed ? "true" : "false");
    }

    if (setup_event() < 0) { diag("event_setup_failed", NULL); return 1; }

    refresh_cp_state();
    refresh_sim_state();
    diagf("startup", "\"cp\":\"%s\",\"sim\":%d", g.cp_state, (int)g.sim_present);

    if (g.cp_online) maybe_open_endpoints();

    if (g.fmt.present) {
        sd_event_add_io(g.loop, &g.fmt_src, g.fmt.dev.fd, EPOLLIN, fmt_handler, NULL);
    }
    if (g.rfs.present) {
        sd_event_add_io(g.loop, &g.rfs_src, g.rfs.dev.fd, EPOLLIN, rfs_handler, NULL);
    }

    sd_event_add_time(g.loop, &g.tick_src, CLOCK_MONOTONIC, 0, 0, tick_handler, NULL);
    sd_event_source_set_enabled(g.tick_src, SD_EVENT_ON);

    if (setup_dbus() < 0) {
        /* D-Bus is part of the contract; degrade but keep running?  No: fail. */
        diag("fatal_no_dbus", NULL);
        return 1;
    }

    diag("running", NULL);
    int r = sd_event_loop(g.loop);
    diag("shutdown", NULL);
    sms_service_close(&g.sms);
    ims_service_close(&g.ims);
    ims_pdn_close(&g.ims_pdn);
    ims_init_close(&g.ims_init);
    iil_pdn_close(&g.iil_pdn);
    iil_auth_close(&g.iil_auth);
    sip_tr_close();
    ep_close(&g.fmt);
    ep_close(&g.rfs);
    (void)r;
    return 0;
}
