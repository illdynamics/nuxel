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
#include "transport.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <systemd/sd-bus.h>
#include <systemd/sd-event.h>

/* ------------------------------------------------------------------ */
/* constants                                                            */
/* ------------------------------------------------------------------ */
#define BOOT_NODE   "/dev/umts_boot0"
#define FMT_NODE    "/dev/umts_ipc0"
#define RFS_NODE    "/dev/umts_rfs0"
#define MODEM_STATE_SYSFS "/sys/devices/platform/10000.mif_pdata/modem_state"
#define SIM_DETECT_SYSFS  "/sys/devices/platform/10000.mif_pdata/sim/ds_detect"

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
            (unsigned long long)wall_ms(), event,
            detail ? ",\"detail\":\"" : "", detail ? detail : "");
    fputc('\n', stderr);
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
    char s[8] = "";
    if (read_text_file(SIM_DETECT_SYSFS, s, sizeof s) == 0)
        g.sim_present = (s[0] == '1');
    else
        g.sim_present = false;
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

static void dispatch_fmt(uint8_t ch, const struct nuxel_sipc_fmt *f)
{
    const struct nuxel_fmt_observation *ob = find_fmt_obs(f->main_cmd, f->sub_cmd, f->cmd_type);
    record_obs(ch, f, ob != NULL);
    resolve_pending(f);
    /* We do not decode telephony semantics (UNKNOWN). We DO surface the
     * existence and classification of every message as a diagnostic. */
    diagf("fmt_rx", "\"ch\":%u,\"main\":%u,\"sub\":%u,\"type\":%u,\"plen\":%u,\"known\":%d",
          ch, f->main_cmd, f->sub_cmd, f->cmd_type, f->payload_len, ob != NULL);
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

    diagf("rfs_rx", "\"ch\":%u,\"op\":%u,\"opname\":\"%s\",\"seq\":%u,"
          "\"special\":%d,\"rlen\":%u",
          ch, req.op, rfs_op_name(req.op), req.seq,
          req.special_delete_all_vis ? 1 : 0, req.total_len);

    /* POLICY GATE: build a fail-closed response. Only the no-op boot marker
     * (DELETE_ALL_VIS) is answered with success. We never mention the path in
     * logs (only the op name + special flag), never execute filesystem I/O. */
    int32_t detail = 0;
    int res = rfs_response_policy(&req, &detail);
    uint8_t resp[RFS_RESP_LEN];
    size_t n = rfs_response_build(req.op, req.seq, res, detail, resp);

    /* Write the response to /dev/umts_rfs0. This is the AP->CP answer the CP
     * is waiting for. Writes are bounded (14 bytes) and only performed here. */
    enum nuxel_io_status st = nuxel_dev_write(&g.rfs.dev, resp, n);
    if (st == NUXEL_IO_OK) {
        g.stats.rfs_responses++;
        g.stats.tx_frames++;
        diagf("rfs_tx", "\"op\":%u,\"res\":%d,\"len\":%zu",
              req.op, res, n);
    } else {
        g.stats.rfs_resp_errors++;
        diagf("rfs_tx_fail", "\"op\":%u,\"st\":\"%s\"",
              req.op, nuxel_io_status_name(st));
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

/* tick: CP state polling + pending timeouts + reopen */
static int tick_handler(sd_event_source *s, uint64_t usec, void *userdata)
{
    (void)s; (void)userdata;
    bool prev_online = g.cp_online;
    refresh_cp_state();
    if (prev_online != g.cp_online) {
        emit_state_changed("CpState", g.cp_state);
        if (g.cp_online) maybe_open_endpoints();
    }
    refresh_sim_state();

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
    /* We know only CP ONLINE. Actual "radio on" requires an FMT source we do
     * not have, so report "on" only if online, honoring the truth contract. */
    const char *v = g.cp_online ? "on" : "off";
    if (!g.cp_online && strcmp(g.cp_state, "UNKNOWN") == 0) v = "unknown";
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
    return sd_bus_reply_method_return(m, "s", "__NOT_SUPPORTED__");
}
static int method_get_capabilities(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    sd_bus_message *reply = NULL;
    if (sd_bus_message_new_method_return(m, &reply) < 0) return -1;
    sd_bus_message_open_container(reply, 'a', "{ss}");
    const char *keys[] = {"lte_data","sms","voice","ims","volte"};
    for (unsigned i = 0; i < 5; i++) {
        sd_bus_message_append(reply, "{ss}", keys[i], "unknown");
    }
    sd_bus_message_close_container(reply);
    int r = sd_bus_send(NULL, reply, NULL);
    sd_bus_message_unref(reply);
    return r;
}
static int method_set_radio(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)u;(void)e;
    int en = 0;
    if (sd_bus_message_read(m, "b", &en) < 0)
        return sd_bus_error_set(e, SD_BUS_ERROR_INVALID_ARGS, "bad arg");
    /* No authorized radio-power vocabulary is known; refuse rather than guess. */
    return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED,
                            "radio power control not implemented (vocab UNKNOWN)");
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
static int method_no_bearer(sd_bus_message *m, void *u, sd_bus_error *e)
{
    (void)m; (void)u;
    return sd_bus_error_set(e, SD_BUS_ERROR_ACCESS_DENIED,
                            "bearer control not implemented (vocab UNKNOWN)");
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
    SD_BUS_PROPERTY("SimPresent", "b", prop_sim_present, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_PROPERTY("SimPinRequired", "b", prop_sim_pin, 0, SD_BUS_VTABLE_PROPERTY_EMITS_CHANGE),
    SD_BUS_METHOD("GetSimState", "", "s", method_get_sim_state, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_PROPERTY("Registered", "b", NULL, 0, 0),
    SD_BUS_METHOD("GetSignalInfo", "", "iiib", method_get_signal, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetAvailableOperators", "", "a(ss)", method_get_operators, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetPacketStats", "", "ttb", method_packet_stats, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("CreateBearer", "s", "u", method_no_bearer, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("DeleteBearer", "u", "", method_no_bearer, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetCapabilities", "", "a{ss}", method_get_capabilities, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_METHOD("GetDiagnostics", "", "a{st}", method_get_diagnostics, SD_BUS_VTABLE_UNPRIVILEGED),
    SD_BUS_SIGNAL("StateChanged", "ss", 0),
    SD_BUS_SIGNAL("CpReset", "", 0),
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

static int setup_dbus(void)
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
        r = sd_bus_default_system(&g.bus);
    }
    if (r < 0) { diagf("dbus_connect_failed", "\"err\":%d", r); return r; }
    r = sd_bus_add_object_vtable(g.bus, NULL, OBJ_PATH, IFACE_NAME, radiod_vtable, NULL);
    if (r < 0) { diagf("dbus_vtable_failed", "\"err\":%d", r); return r; }
    r = sd_bus_request_name(g.bus, DEST_NAME, 0);
    if (r < 0) { diagf("dbus_name_failed", "\"err\":%d", r); return r; }
    sd_bus_attach_event(g.bus, g.loop, SD_EVENT_PRIORITY_NORMAL);
    diag("dbus_ready", DEST_NAME);
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
    (void)argc; (void)argv;
    memset(&g, 0, sizeof g);
    g.fmt.dev.fd = -1;
    g.rfs.dev.fd = -1;
    g.cp_state_code = -1;
    snprintf(g.cp_state, sizeof g.cp_state, "UNKNOWN");

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
    ep_close(&g.fmt);
    ep_close(&g.rfs);
    (void)r;
    return 0;
}
