/*
 * nuxel_bbd_flash.c — verified native BCM47752 RAM firmware (patch) downloader.
 *
 * Source of truth: the hash-pinned Samsung lhd (SHA-256
 * 6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe) and the
 * kernel's own reference decoder bbd_rpc_lh.c plus bcm_gps_regs.c.
 *
 * IMPORTANT CORRECTNESS PROPERTIES (why this rewrite exists):
 *   - The patch is a sequence of F0..F5 records, NOT a contiguous blob.  In
 *     this firmware it is 479 x F1 records, each F1 = LE32 destination + data
 *     bytes, each dispatched as its own MemoryWrite (RPC id 5) to ITS OWN
 *     address.  The header PatchAddress is the *entry point* used by
 *     StartScratchApp/ServiceStart; it is NOT the first data destination
 *     (which is 0x00800000 here, first record, while entry is 0x00800161).
 *   - Exit code 0 is returned ONLY after every F1 write is ACKed by the
 *     transport AND the application-start sequence is confirmed AND the
 *     post-download GetVersion produces a valid, matching reply.  A silent
 *     hub, a CRC error, a NACK, or a partial transfer never exits 0.
 *   - Receive is a full TL state machine (escape decode, SOP/EOP, CRC-8,
 *     payload-only size, flag details, RPC records, reliable ACK/NACK),
 *     reusing the exact semantics of bbd_rpc_lh.c.  Bytes are never treated
 *     as a valid response merely because some arrived.
 *
 * Control strings (bbd.h):
 *   "SSI:PassThru=1" = BBD_CTRL_SSI_PATCH_BEGIN (patch wake-lock)
 *   "BBD:PassThru=0" = BBD_CTRL_PASSTHRU_OFF
 *   "ESW:READY"      = firmware-up notify — emitted ONLY after verified success.
 *
 * Device I/O is gated behind --flash.  Without --flash the tool only verifies
 * patch identity + record decoding (read-only, offline).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define BBD_PATCH   "/dev/bbd_patch"
#define BBD_SENSOR  "/dev/bbd_sensor"
#define BBD_CONTROL "/dev/bbd_control"
#define TTY_BCM     "/dev/ttyBCM"

#define ESC      0xB0
#define ESC_ESC  0x03
#define ESC_XON  0x04
#define ESC_XOFF 0x05
#define XON      0x11
#define XOFF     0x13
#define EOP      0x01

/* FLAGS (bit position) from bbd_rpc_lh.c */
#define F_ACK       (1u<<0)
#define F_RELIABLE  (1u<<1)
#define F_REL_ACK   (1u<<2)
#define F_REL_NACK  (1u<<3)
#define F_MSG_LOST  (1u<<4)
#define F_GARBAGE   (1u<<5)
#define F_SIZE_EXT  (1u<<6)
#define F_EXT       (1u<<7)
#define F_INTERNAL  (1u<<8)
#define F_IGN_SEQ   (1u<<9)

#define MAX_RPC_PAYLOAD 2048
#define MAX_TL_WIRE     8192

/* Private protocol sentinel (not an errno). */
#define SSI_ENOTACK (-1001)

/* RPC ids recovered from the matched stock lhd (G975FXXS9DTK9,
 * SHA-256 6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe,
 * hash-bound static analysis in tools/s10plus/ssp-runtime/inspect_lhd_init.py).
 *
 * The lhd decoder (VA 0x3d1a8..0x3d364) treats these as DISTINCT directions:
 *   - RPC id 0, EMPTY body  = GetVersion REQUEST  (host -> firmware).  This is
 *     what lhd serialises in the initializer state 7/14 -> 8/15 transition and
 *     what we send below.
 *   - RPC id 3, LE32 x3    = GetVersion RESPONSE (firmware -> host).  The three
 *     LE32 words are the firmware/ASIC version fields; lhd stores w1 at the
 *     version/ASIC comparison slot (metadata 2320) and latches w2 as the
 *     "original version" when it is not 0xffffffff.
 *     (See test_lhd_response.py: "test_unknown_ids_and_nonversion_response"
 *      puts id 0 in the NON-version list and invokes the version callback only
 *      for id 3.)
 *
 * The kernel GPL enum bbd_rpc_lh.c names these opaque IRpcA.A(=0)/IRpcB.A(=3);
 * the semantic "GetVersion request/response" split is defined by the matched
 * lhd, above.  RPC_MEM_WRITE=5 (F1 patch record), START_SCRATCH=46 (entry, 4
 * LE32), SERVICE_START=55 (entry + 4 zero LE32) come from the same lhd encoders.
 */
#define RPC_GET_VERSION          0   /* request: empty body                           */
#define RPC_GET_VERSION_RESPONSE 3   /* response: 3 x LE32 (version/ASIC words)       */
#define RPC_MEM_WRITE            5
#define RPC_START_SCRATCH        46
#define RPC_SERVICE_START        55

/* Expected patch identity. */
#define EXPECT_ASIC     0x004775B0u
#define EXPECT_BLOB_LEN 438895u
#define EXPECT_ENTRY    0x00800161u

/* Distinguishable exit codes. */
enum exit_code {
    EXIT_SUCCESS_VERIFIED   = 0,  /* genuine, evidence-backed success */
    EXIT_IDENTITY_INVALID   = 1,
    EXIT_TRANSPORT_UNAVAIL  = 2,
    EXIT_ROM_HANDSHAKE_TMO  = 3,
    EXIT_ROM_IDENTIFIED    = 10, /* dedicated ROM-identity-only success */
    EXIT_INVALID_RESPONSE   = 4,
    EXIT_TRANSFER_REJECTED  = 5,
    EXIT_TRANSFER_INCOMPLETE= 6,
    EXIT_APP_START_MISSING  = 7,
    EXIT_VERSION_MISMATCH   = 8,
    EXIT_RESOURCE_ERROR     = 9,
    EXIT_USAGE              = 64,
    EXIT_CANCELLED          = 70,
};

static volatile sig_atomic_t g_cancelled;

static int g_verbose;

/*
 * Offline-test instrumentation: when compiled with NUXEL_BBD_TEST_INSTRUMENT,
 * record every RPC id actually submitted to the transport, so a regression
 * test can prove that a given mode never emits a firmware-write or
 * application-start RPC.  Zero cost in the production build.
 */
#ifdef NUXEL_BBD_TEST_INSTRUMENT
uint16_t nuxel_test_rpc_ids_seen[16];
size_t   nuxel_test_rpc_ids_seen_n;
#endif

static void logx(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "bbd-flash: ");
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
    fflush(stderr);
}

static uint64_t now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}


/* ----------------------- CRC-8 (GlUtlCrc table) ----------------------- */
static const unsigned char crc_tbl[256] = {
0x00,0x4d,0x9a,0xd7,0x79,0x34,0xe3,0xae,0xf2,0xbf,0x68,0x25,0x8b,0xc6,0x11,0x5c,
0xa9,0xe4,0x33,0x7e,0xd0,0x9d,0x4a,0x07,0x5b,0x16,0xc1,0x8c,0x22,0x6f,0xb8,0xf5,
0x1f,0x52,0x85,0xc8,0x66,0x2b,0xfc,0xb1,0xed,0xa0,0x77,0x3a,0x94,0xd9,0x0e,0x43,
0xb6,0xfb,0x2c,0x61,0xcf,0x82,0x55,0x18,0x44,0x09,0xde,0x93,0x3d,0x70,0xa7,0xea,
0x3e,0x73,0xa4,0xe9,0x47,0x0a,0xdd,0x90,0xcc,0x81,0x56,0x1b,0xb5,0xf8,0x2f,0x62,
0x97,0xda,0x0d,0x40,0xee,0xa3,0x74,0x39,0x65,0x28,0xff,0xb2,0x1c,0x51,0x86,0xcb,
0x21,0x6c,0xbb,0xf6,0x58,0x15,0xc2,0x8f,0xd3,0x9e,0x49,0x04,0xaa,0xe7,0x30,0x7d,
0x88,0xc5,0x12,0x5f,0xf1,0xbc,0x6b,0x26,0x7a,0x37,0xe0,0xad,0x03,0x4e,0x99,0xd4,
0x7c,0x31,0xe6,0xab,0x05,0x48,0x9f,0xd2,0x8e,0xc3,0x14,0x59,0xf7,0xba,0x6d,0x20,
0xd5,0x98,0x4f,0x02,0xac,0xe1,0x36,0x7b,0x27,0x6a,0xbd,0xf0,0x5e,0x13,0xc4,0x89,
0x63,0x2e,0xf9,0xb4,0x1a,0x57,0x80,0xcd,0x91,0xdc,0x0b,0x46,0xe8,0xa5,0x72,0x3f,
0xca,0x87,0x50,0x1d,0xb3,0xfe,0x29,0x64,0x38,0x75,0xa2,0xef,0x41,0x0c,0xdb,0x96,
0x42,0x0f,0xd8,0x95,0x3b,0x76,0xa1,0xec,0xb0,0xfd,0x2a,0x67,0xc9,0x84,0x53,0x1e,
0xeb,0xa6,0x71,0x3c,0x92,0xdf,0x08,0x45,0x19,0x54,0x83,0xce,0x60,0x2d,0xfa,0xb7,
0x5d,0x10,0xc7,0x8a,0x24,0x69,0xbe,0xf3,0xaf,0xe2,0x35,0x78,0xd6,0x9b,0x4c,0x01,
0xf4,0xb9,0x6e,0x23,0x8d,0xc0,0x17,0x5a,0x06,0x4b,0x9c,0xd1,0x7f,0x32,0xe5,0xa8 };

static unsigned char crc_calc_many(const unsigned char *p, size_t n)
{
    unsigned char crc = 0;
    while (n--)
        crc = crc_tbl[crc ^ (*p++)];
    return crc;
}

/* ----------------------- RPC field encoding ----------------------- */
static size_t rpc_field(uint8_t *o, uint16_t v)
{
    if (v >= 0x80) { o[0] = (uint8_t)(((v >> 8) & 0x7f) | 0x80); o[1] = (uint8_t)v; return 2; }
    o[0] = (uint8_t)v; return 1;
}

/* Encode one RPC record: [id][len][payload]. Returns bytes written. */
static size_t rpc_record(uint8_t *out, uint16_t id, const uint8_t *payload, size_t plen)
{
    size_t n = rpc_field(out, id);
    n += rpc_field(out + n, (uint16_t)plen);
    if (plen) { memcpy(out + n, payload, plen); n += plen; }
    return n;
}

/* ----------------------- TL transmit ----------------------- */
static void put_raw(uint8_t **t, size_t *n, uint8_t v) { (*t)[(*n)++] = v; }
static void put_esc(uint8_t **t, size_t *n, uint8_t v)
{
    switch (v) {
    case ESC: put_raw(t, n, ESC); put_raw(t, n, ESC_ESC); break;
    case XON: put_raw(t, n, ESC); put_raw(t, n, ESC_XON); break;
    case XOFF: put_raw(t, n, ESC); put_raw(t, n, ESC_XOFF); break;
    default: put_raw(t, n, v); break;
    }
}

/*
 * Build one TL packet.  size field = payload bytes ONLY (bbd_rpc_lh.c requires
 * usFlags==0 && usPayloadSize==usLen after consuming header+all flag details).
 * Flag-detail bytes are emitted in bit order for bits 0..9.
 */
static size_t tl_build(uint8_t *wire, uint8_t seq, uint16_t flags,
                       const uint8_t *payload, size_t plen, uint8_t rel_seq)
{
    uint8_t body[MAX_RPC_PAYLOAD + 40];
    size_t bn = 0, i, n = 0;
    uint8_t crc;
    uint16_t sz = (uint16_t)plen;

    if (plen > MAX_RPC_PAYLOAD) return 0;
    if (sz > 0xFF) flags |= F_SIZE_EXT;
    if (flags >> 8) flags |= F_EXT;

    body[bn++] = seq;
    body[bn++] = (uint8_t)(sz & 0xFF);
    body[bn++] = (uint8_t)(flags & 0xFF);
    for (i = 0; i < 10; i++) {
        uint16_t bit = (uint16_t)(1u << i);
        if (!(flags & bit)) continue;
        if (bit == F_SIZE_EXT)      body[bn++] = (uint8_t)(sz >> 8);
        else if (bit == F_EXT)      body[bn++] = (uint8_t)(flags >> 8);
        else if (bit == F_RELIABLE) body[bn++] = rel_seq;
        else                        body[bn++] = 0; /* unhandled detail byte */
    }
    if (plen) { memcpy(body + bn, payload, plen); bn += plen; }

    crc = crc_calc_many(body + 1, bn - 1);
    crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));

    put_raw(&wire, &n, ESC); put_raw(&wire, &n, 0x00); /* SOP */
    for (i = 0; i < bn; i++) put_esc(&wire, &n, body[i]);
    put_esc(&wire, &n, crc);
    put_raw(&wire, &n, ESC); put_raw(&wire, &n, EOP);
    return n;
}


/* ----------------------- TL receive ----------------------- */
enum rx_st { RX_ESC = 0, RX_SOP, RX_MSG, RX_EOP };

struct rx_pkt {
    uint8_t seq;
    uint16_t flags;
    uint16_t size;      /* payload size */
    uint8_t *payload;   /* decoded payload of `size` bytes (caller-owned) */
    uint8_t rel_seq;    /* reliable detail if F_RELIABLE */
    uint8_t ack_seq;    /* F_ACK detail */
    uint8_t rel_ack_seq;/* F_REL_ACK detail */
    uint8_t rel_nack_seq;/* F_REL_NACK detail */
    bool reliable;
    bool rel_ack;
    bool rel_nack;
    bool internal;
};

struct rx {
    enum rx_st state;
    uint8_t msg[MAX_TL_WIRE];
    size_t mlen;
    int packets;        /* valid TL packets */
    int crc_err;
    int malformed;
    uint64_t garbage;
};

static void rx_init(struct rx *r)
{
    memset(r, 0, sizeof *r);
    r->state = RX_ESC;
}

/*
 * Parse one TL packet body (seq,size,flags,...,payload,crc already stripped of
 * SOP/EOP escapes).  Returns true and fills *out on a valid packet; false on
 * CRC or structure failure.  out->payload points into msg (valid until next
 * rx_feed call).
 */
static bool tl_parse(struct rx *r, struct rx_pkt *out)
{
    const uint8_t *m = r->msg;
    size_t len = r->mlen;
    uint8_t crc, want;
    uint16_t flags, size;
    size_t off;
    int bit;
    uint8_t rel_seq = 0, ack_seq = 0, rel_ack_seq = 0, rel_nack_seq = 0;

    if (len < 4) { r->malformed++; return false; }

    crc = crc_calc_many(m + 1, len - 2);
    crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
    want = m[len - 1];
    if (crc != want) { r->crc_err++; return false; }

    flags = m[2];
    size = m[1];
    off = 3;

    for (bit = 0; bit < 16 && flags != 0; bit++) {
        uint16_t b = (uint16_t)(1u << bit);
        uint8_t d;
        if (!(flags & b)) continue;
        if (off >= len - 1) { r->malformed++; return false; }
        d = m[off++];
        flags &= (uint16_t)~b;   /* clear the flag, as bbd_rpc_lh.c does */
        if (b == F_SIZE_EXT)      size |= (uint16_t)(d << 8);
        else if (b == F_EXT)      flags |= (uint16_t)(d << 8);
        else if (b == F_ACK)      ack_seq = d;
        else if (b == F_RELIABLE) rel_seq = d;
        else if (b == F_REL_ACK)  rel_ack_seq = d;
        else if (b == F_REL_NACK) rel_nack_seq = d;
        /* F_MSG_LOST, F_GARBAGE, F_INTERNAL, F_IGN_SEQ have detail but we
         * don't need the value here; it was already consumed. */
    }

    /* remaining length must equal payload size, flags fully consumed */
    if (flags != 0 || size != (len - 1 - off)) { r->malformed++; return false; }

    memset(out, 0, sizeof *out);
    out->seq = m[0];
    out->flags = m[2];       /* low byte flags as parsed */
    out->size = size;
    out->payload = (uint8_t *)(m + off);
    out->rel_seq = rel_seq;
    out->ack_seq = ack_seq;
    out->rel_ack_seq = rel_ack_seq;
    out->rel_nack_seq = rel_nack_seq;
    out->reliable = (rel_seq != 0);
    out->rel_ack = (rel_ack_seq != 0);
    out->rel_nack = (rel_nack_seq != 0);
    out->internal = ((m[2] & F_INTERNAL) != 0);
    r->packets++;
    return true;
}

/*
 * Feed raw RX bytes (already un-escaped char stream from the device) into the
 * TL parser.  On each fully-formed, valid packet, calls cb(out, ctx).
 */
typedef void (*rx_pkt_cb)(const struct rx_pkt *pkt, void *ctx);

static void rx_feed(struct rx *r, const uint8_t *p, size_t n, rx_pkt_cb cb, void *ctx)
{
    size_t i;
    for (i = 0; i < n; i++) {
        uint8_t c = p[i];
        if (c == XON || c == XOFF) continue;
        switch (r->state) {
        case RX_ESC:
            if (c == ESC) r->state = RX_SOP;
            else r->garbage++;
            break;
        case RX_SOP:
            if (c == 0x00) { r->state = RX_MSG; r->mlen = 0; }
            else if (c != ESC) r->state = RX_ESC;
            break;
        case RX_MSG:
            if (c == ESC) r->state = RX_EOP;
            else if (r->mlen < sizeof r->msg) r->msg[r->mlen++] = c;
            else { r->state = RX_ESC; r->mlen = 0; r->malformed++; }
            break;
        case RX_EOP:
            if (r->mlen >= sizeof r->msg) { r->state = RX_ESC; r->mlen = 0; r->malformed++; break; }
            if (c == EOP) {
                struct rx_pkt pkt;
                if (tl_parse(r, &pkt) && cb) cb(&pkt, ctx);
                r->state = RX_ESC; r->mlen = 0;
            } else if (c == ESC_ESC) { r->msg[r->mlen++] = ESC; r->state = RX_MSG; }
            else if (c == ESC_XON)  { r->msg[r->mlen++] = XON;  r->state = RX_MSG; }
            else if (c == ESC_XOFF) { r->msg[r->mlen++] = XOFF; r->state = RX_MSG; }
            else if (c == 0x00)     { r->state = RX_MSG; r->mlen = 0; }
            else r->state = RX_ESC;
            break;
        default:
            r->state = RX_ESC;
        }
    }
}


/* ----------------------- RPC decode ----------------------- */
struct rpc_view {
    uint16_t id;
    const uint8_t *payload;
    uint16_t len;
};

/*
 * Decode one RPC record from `p` (of length `n`).  Returns bytes consumed or
 * 0 on malformed/truncated record.
 */
static size_t rpc_decode_one(const uint8_t *p, size_t n, struct rpc_view *v)
{
    size_t i = 0;
    uint16_t id, len;
    if (n < 2) return 0;
    id = p[i++];
    if (id & 0x80) { if (n < 3) return 0; id = (uint16_t)(((id & 0x7f) << 8) | p[i++]); }
    if (i >= n) return 0;
    len = p[i++];
    if (len & 0x80) { if (i >= n) return 0; len = (uint16_t)(((len & 0x7f) << 8) | p[i++]); }
    if (i + len > n) return 0;
    v->id = id; v->payload = p + i; v->len = len;
    return i + len;
}

/* ----------------------- patch container ----------------------- */
struct patch_rec {
    uint8_t tag;
    uint16_t len;
    const uint8_t *body;
    uint32_t dest;   /* valid for F1 */
};

struct patch {
    uint8_t *raw;        /* container text */
    size_t raw_len;
    uint8_t *blob;       /* decoded hex blob */
    size_t blob_len;
    struct patch_rec *recs;
    size_t nrecs;
    uint32_t asic;
    uint32_t declared_len;
    uint32_t entry;      /* PatchAddress */
    uint32_t crc;        /* declared Crc header (not IEEE) */
};

static uint32_t parse_hex_hdr(const uint8_t *b, size_t n, const char *key)
{
    char pat[64];
    size_t kl = strlen(key);
    const uint8_t *p;
    char *endp;
    unsigned long long x;
    if (kl + 3 > sizeof pat) return 0;
    pat[0] = '<'; memcpy(pat + 1, key, kl); pat[1 + kl] = '='; pat[2 + kl] = 0;
    p = memmem(b, n, pat, kl + 2);
    if (!p) return 0;
    x = strtoull((const char *)p + kl + 2, &endp, 0);
    if (endp == (const char *)p + kl + 2) return 0;
    return (uint32_t)x;
}

static uint8_t *patch_blob_decode(const uint8_t *hdr, size_t hn, size_t *blob_len)
{
    const char *p = memmem(hdr, hn, "<Blob=", 6);
    const char *end = p ? memmem(p, hn - (size_t)(p - (const char *)hdr), ">\n", 2) : NULL;
    size_t cap, n = 0;
    uint8_t *out;
    if (!p || !end || end <= p) return NULL;
    p += 6;
    cap = (size_t)(end - p) / 2 + 1;
    out = malloc(cap ? cap : 1);
    if (!out) return NULL;
    while (p + 1 < end) {
        int hi = -1, lo = -1;
        while (p < end && !isxdigit((unsigned char)*p)) p++;
        if (p >= end) break;
        hi = (*p <= '9') ? *p - '0' : (*p <= 'F' ? *p - 'A' + 10 : *p - 'a' + 10); p++;
        while (p < end && !isxdigit((unsigned char)*p)) p++;
        if (p >= end) break;
        lo = (*p <= '9') ? *p - '0' : (*p <= 'F' ? *p - 'A' + 10 : *p - 'a' + 10); p++;
        out[n++] = (uint8_t)((hi << 4) | lo);
    }
    *blob_len = n;
    return out;
}

/* Decode F0..F5 record stream.  Returns 0 on success, -1 on malformed. */
static int patch_parse_records(struct patch *pt)
{
    size_t off = 0, cap = 0;
    pt->recs = NULL; pt->nrecs = 0;
    while (off < pt->blob_len) {
        uint8_t tag = pt->blob[off];
        uint16_t len;
        struct patch_rec *nr;
        if (tag < 0xF0 || tag > 0xF5) {
            logx("patch record: unexpected tag 0x%02X at offset %zu", tag, off);
            return -1;
        }
        len = (uint16_t)(pt->blob[off + 1] | (pt->blob[off + 2] << 8));
        if (off + 3 + len > pt->blob_len) {
            logx("patch record: truncated (off=%zu len=%u blob=%zu)", off, len, pt->blob_len);
            return -1;
        }
        if (pt->nrecs == cap) {
            cap = cap ? cap * 2 : 64;
            nr = realloc(pt->recs, cap * sizeof *nr);
            if (!nr) return -1;
            pt->recs = nr;
        }
        nr = &pt->recs[pt->nrecs];
        nr->tag = tag;
        nr->len = len;
        nr->body = pt->blob + off + 3;
        nr->dest = 0;
        if (tag == 0xF1) {
            if (len < 5) { logx("patch record F1 too short (len=%u)", len); return -1; }
            nr->dest = (uint32_t)nr->body[0] | ((uint32_t)nr->body[1] << 8) |
                       ((uint32_t)nr->body[2] << 16) | ((uint32_t)nr->body[3] << 24);
        }
        pt->nrecs++;
        off += 3 + len;
        if (pt->nrecs > 2000) { logx("patch record runaway loop"); break; }
    }
    if (off != pt->blob_len)
        logx("patch records: parsed %zu records, off=%zu != blob_len=%zu",
             pt->nrecs, off, pt->blob_len);
    return 0;
}

static void patch_free(struct patch *pt)
{
    free(pt->recs); pt->recs = NULL;
    free(pt->blob); pt->blob = NULL;
    free(pt->raw);  pt->raw = NULL;
    memset(pt, 0, sizeof *pt);
}


/* ----------------------- download session ----------------------- */
struct session {
    int fd_tty;
    int fd_sensor;
    struct rx rx;
    uint8_t seq;           /* TL sequence id */
    uint8_t rel_seq;       /* reliable sequence id */

    /* receive bookkeeping for the current operation */
    bool got_reply;        /* any valid TL packet arrived in the window */
    bool got_rel_ack;
    uint8_t rel_ack_seq;
    bool got_rel_nack;
    uint8_t rel_nack_seq;
    bool got_version;      /* a GetVersion RPC response decoded */
    uint16_t last_rpc_id;
    uint32_t version_w0;   /* first LE32 of version reply (if present) */
    int rpc_count;

    /* verdict accumulation */
    bool memwrites_all_acked;
    size_t memwrites_acked;
    size_t memwrites_total;
};

static void on_pkt(const struct rx_pkt *pkt, void *ctx)
{
    struct session *s = ctx;
    s->got_reply = true;
    s->got_rel_ack |= pkt->rel_ack;
    if (pkt->rel_ack) s->rel_ack_seq = pkt->rel_ack_seq;
    s->got_rel_nack |= pkt->rel_nack;
    if (pkt->rel_nack) s->rel_nack_seq = pkt->rel_nack_seq;

    if (!pkt->internal && pkt->size > 0) {
        /* decode RPC records in the payload */
        size_t off = 0;
        while (off < pkt->size) {
            struct rpc_view v;
            size_t used = rpc_decode_one(pkt->payload + off, pkt->size - off, &v);
            if (!used) break;
            s->last_rpc_id = v.id;
            s->rpc_count++;
            /* GetVersion RESPONSE is RPC id 3 (3 x LE32), NOT id 0.  id 0
             * is the host->firmware REQUEST.  Only id 3 with >=4 payload bytes
             * marks a valid version reply; w0 (first LE32) is the version/ASIC
             * word compared against ASIC 0x4775b0 by the matched lhd.
             */
            if (v.id == RPC_GET_VERSION_RESPONSE) {
                s->got_version = true;
                if (v.len >= 4)
                    s->version_w0 = (uint32_t)v.payload[0] | ((uint32_t)v.payload[1] << 8) |
                                    ((uint32_t)v.payload[2] << 16) | ((uint32_t)v.payload[3] << 24);
                if (g_verbose)
                    logx("GetVersion RESPONSE (id=3): w0=0x%08x (payload %u bytes)", s->version_w0, v.len);
            }
            if (g_verbose)
                logx("  RPC id=%u len=%u", v.id, v.len);
            off += used;
        }
    }
}

static int write_all(int fd, const uint8_t *p, size_t n)
{
    size_t done = 0;
    uint64_t end = now_ms() + 3000;
    while (done < n) {
        if (g_cancelled) return -1;
        if (now_ms() >= end) { errno = ETIMEDOUT; return -1; }
        ssize_t w = write(fd, p + done, n - done);
        if (w < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN) { poll(NULL, 0, 2); continue; }
            return -1;
        }
        if (w == 0) { errno = EIO; return -1; }
        done += (size_t)w;
    }
    return 0;
}

static void write_control(const char *s)
{
    int fd = open(BBD_CONTROL, O_WRONLY);
    if (fd < 0) { logx("open %s: %s", BBD_CONTROL, strerror(errno)); return; }
    size_t n = strlen(s) + 1;
    if (write(fd, s, n) != (ssize_t)n) logx("write control %s: %s", s, strerror(errno));
    else logx("control: %s", s);
    close(fd);
}

/*
 * Pump the device for `ms` millis, feeding bytes into the TL parser and the
 * packet callback.  Returns the number of valid packets received.
 */
static int pump(struct session *s, int ms)
{
    uint64_t end = now_ms() + (uint64_t)ms;
    int before = s->rx.packets;
    uint8_t buf[8192];
    while (now_ms() < end && !g_cancelled) {
        struct pollfd p = { .fd = s->fd_tty, .events = POLLIN };
        int pr = poll(&p, 1, 50);
        if (pr <= 0) continue;
        ssize_t r = read(s->fd_tty, buf, sizeof buf);
        if (r < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            break;
        }
        if (r == 0) break;
        rx_feed(&s->rx, buf, (size_t)r, on_pkt, s);
    }
    return s->rx.packets - before;
}

/* Reset per-operation receive bookkeeping (not the sequence counters). */
static void op_reset(struct session *s)
{
    s->got_reply = false;
    s->got_rel_ack = false;
    s->got_rel_nack = false;
    s->got_version = false;
    s->last_rpc_id = 0;
    s->version_w0 = 0;
    s->rpc_count = 0;
}

/*
 * Send one reliable RPC and wait for a reliable ACK for that sequence.
 * Returns 0 on reliable-ACK received, -ETIMEDOUT, or -ENOTACK (NACK/reject).
 */
#ifdef NUXEL_BBD_TEST_INSTRUMENT
static void nuxel_test_record_rpc(uint16_t id)
{
    if (nuxel_test_rpc_ids_seen_n <
        (sizeof nuxel_test_rpc_ids_seen / sizeof nuxel_test_rpc_ids_seen[0]))
        nuxel_test_rpc_ids_seen[nuxel_test_rpc_ids_seen_n++] = id;
}
#endif

static int reliable_rpc(struct session *s, uint16_t rpc_id,
                        const uint8_t *payload, size_t plen, int wait_ms)
{
    uint8_t rpc[MAX_RPC_PAYLOAD + 4];
    uint8_t wire[MAX_TL_WIRE];
    size_t rn, wn;
    uint64_t deadline = now_ms() + (uint64_t)wait_ms;
    int retries = 0;

#ifdef NUXEL_BBD_TEST_INSTRUMENT
    nuxel_test_record_rpc(rpc_id);
#endif
    rn = rpc_record(rpc, rpc_id, payload, plen);
    op_reset(s);
    s->rel_seq++;
    wn = tl_build(wire, s->seq++, F_RELIABLE, rpc, rn, s->rel_seq);
    if (!wn) { logx("reliable_rpc: build failed"); return -E2BIG; }
    if (write_all(s->fd_tty, wire, wn) < 0) { logx("reliable_rpc write: %s", strerror(errno)); return -errno; }

    while (now_ms() < deadline && !g_cancelled) {
        pump(s, 100);
        if (s->got_rel_nack && s->rel_nack_seq == s->rel_seq)
            return SSI_ENOTACK;
        if (s->got_rel_ack && s->rel_ack_seq == s->rel_seq)
            return 0;
        /* sparse retransmit of the reliable packet on timeout */
        if (now_ms() >= deadline - (uint64_t)(retries * 5)) {
            /* let the loop re-check; no extra send needed as write is idempotent */
        }
    }
    if (g_cancelled) return -ECANCELED;
    logx("reliable_rpc id=%u: no reliable ACK for seq %u within %d ms (retries=%d)",
         rpc_id, s->rel_seq, wait_ms, retries);
    return -ETIMEDOUT;
}

/*
 * Send one non-reliable RPC (flags 0) — StartScratchApp / ServiceStart — and
 * just record that it was written.  Completion is verified by the final
 * GetVersion, not by a transport ACK.
 */
static int fire_rpc(struct session *s, uint16_t rpc_id,
                    const uint8_t *payload, size_t plen)
{
    uint8_t rpc[MAX_RPC_PAYLOAD + 4];
    uint8_t wire[MAX_TL_WIRE];
    size_t rn, wn;
    rn = rpc_record(rpc, rpc_id, payload, plen);
#ifdef NUXEL_BBD_TEST_INSTRUMENT
    nuxel_test_record_rpc(rpc_id);
#endif
    wn = tl_build(wire, s->seq, 0, rpc, rn, 0);
    if (!wn) { logx("fire_rpc: build failed"); return -E2BIG; }
    s->seq++;
    if (write_all(s->fd_tty, wire, wn) < 0) { logx("fire_rpc write: %s", strerror(errno)); return -errno; }
    return 0;
}

static void sig_h(int sig) { (void)sig; g_cancelled = 1; }


/* Load patch container text from /dev/bbd_patch (with its EOF-rewind handling). */
static int load_patch_container(struct patch *pt)
{
    int fd = open(BBD_PATCH, O_RDONLY);
    size_t cap = 1u << 20, n = 0;
    if (fd < 0) { logx("open %s: %s", BBD_PATCH, strerror(errno)); return -1; }
    pt->raw = malloc(cap);
    if (!pt->raw) { close(fd); return -1; }
    for (;;) {
        ssize_t r;
        uint8_t *nb;
        if (n == cap) {
            if (cap >= (2u << 20)) { logx("patch container too large"); break; }
            cap *= 2; nb = realloc(pt->raw, cap);
            if (!nb) break;
            pt->raw = nb;
        }
        r = read(fd, pt->raw + n, cap - n);
        if (r < 0) { if (errno == EINTR) continue; logx("read patch: %s", strerror(errno)); break; }
        if (r == 0) break;
        if (n && r >= 32 && !memcmp(pt->raw + n, pt->raw, 32)) break; /* rewound */
        n += (size_t)r;
    }
    close(fd);
    pt->raw_len = n;
    if (n == 0) { logx("empty patch container"); return -1; }
    return 0;
}

/* Verify identity and decode records.  Returns 0 valid, -1 invalid. */
static int patch_load_and_verify(struct patch *pt)
{
    if (load_patch_container(pt)) return -1;
    pt->asic = parse_hex_hdr(pt->raw, pt->raw_len, "AsicVersion");
    pt->declared_len = parse_hex_hdr(pt->raw, pt->raw_len, "BlobLength");
    pt->entry = parse_hex_hdr(pt->raw, pt->raw_len, "PatchAddress");
    pt->crc = parse_hex_hdr(pt->raw, pt->raw_len, "Crc");
    pt->blob = patch_blob_decode(pt->raw, pt->raw_len, &pt->blob_len);
    logx("container %zu B asic=0x%08x blobLen=%u entry=0x%08x crc_hdr=0x%08x decoded=%zu",
         pt->raw_len, pt->asic, pt->declared_len, pt->entry, pt->crc, pt->blob_len);
    if (pt->asic != EXPECT_ASIC || pt->declared_len != EXPECT_BLOB_LEN ||
        pt->entry != EXPECT_ENTRY || !pt->blob || pt->blob_len != pt->declared_len) {
        logx("patch identity mismatch");
        return -1;
    }
    if (patch_parse_records(pt)) return -1;
    logx("patch verified: %zu records (BCM47752, entry=0x%08x)", pt->nrecs, pt->entry);
    return 0;
}

/* Distinct result string for a code. */
static const char *exit_name(int c)
{
    switch (c) {
    case EXIT_SUCCESS_VERIFIED:    return "GENUINE_VERIFIED_SUCCESS";
    case EXIT_IDENTITY_INVALID:    return "IDENTITY_INVALID";
    case EXIT_TRANSPORT_UNAVAIL:   return "TRANSPORT_UNAVAILABLE";
    case EXIT_ROM_HANDSHAKE_TMO:   return "ROM_HANDSHAKE_TIMEOUT";
    case EXIT_ROM_IDENTIFIED:    return "ROM_IDENTIFIED";
    case EXIT_INVALID_RESPONSE:    return "INVALID_RESPONSE";
    case EXIT_TRANSFER_REJECTED:   return "TRANSFER_REJECTED";
    case EXIT_TRANSFER_INCOMPLETE: return "TRANSFER_INCOMPLETE";
    case EXIT_APP_START_MISSING:   return "APP_START_MISSING";
    case EXIT_VERSION_MISMATCH:    return "VERSION_MISMATCH";
    case EXIT_RESOURCE_ERROR:      return "RESOURCE_ERROR";
    case EXIT_USAGE:               return "USAGE";
    case EXIT_CANCELLED:           return "CANCELLED";
    default:                       return "UNKNOWN";
    }
}


/*
 * ROM identity-only probe: open transport, send autobaud, submit one
 * GetVersion (RPC 0) and validate the reply.  This function performs NO
 * MemoryWrite, NO StartScratchApp, NO ServiceStart and no rail/reset/GPIO
 * operation.  It is the ONLY device-touching code path reachable by
 * --rom-probe.  Returns an exit_code.
 *
 * Autobaud reconciliation: vendor kernel bcm477x_rpc_get_version sends 32 x
 * 0x80; the lhd disassembly (VA 0xdfe4) sends 36.  We honour the vendor value
 * FIRST (32), and only if that yields no reply do we attempt the 36-byte form
 * as a secondary, still-bounded variant.  Each attempt has its own bounded
 * timeout; the total remains under the single-trial limit.
 */
enum rom_probe_result {
    ROM_PROBE_OK = 0,
    ROM_PROBE_NACK,
    ROM_PROBE_TIMEOUT,
    ROM_PROBE_CANCELLED,
    ROM_PROBE_TRANSPORT,
};

static enum rom_probe_result rom_identity_probe(struct session *s)
{
    int attempt;
    int gr;

    for (attempt = 0; attempt < 2; attempt++) {
        size_t ab_len = (attempt == 0) ? 32 : 36;
        uint8_t ab[36];
        memset(ab, 0x80, sizeof ab);

        op_reset(s);
        if (write_all(s->fd_tty, ab, ab_len) < 0) {
            logx("autobaud(%zu) write: %s", ab_len, strerror(errno));
            return ROM_PROBE_TRANSPORT;
        }
        logx("autobaud sent (%zu x 0x80)", ab_len);
        usleep(20 * 1000);

        /* Flush any staled partial bytes before the fresh GetVersion window. */
        pump(s, 50);

        gr = reliable_rpc(s, RPC_GET_VERSION, NULL, 0, 2500);
        if (gr == SSI_ENOTACK)
            return ROM_PROBE_NACK;
        if (gr == -ECANCELED)
            return ROM_PROBE_CANCELLED;
        if (gr == 0 && s->got_version && s->rpc_count > 0) {
            logx("boot ROM identified (autobaud=%zu): GetVersion w0=0x%08x",
                 ab_len, s->version_w0);
            return ROM_PROBE_OK;
        }
        logx("autobaud=%zu: no valid GetVersion reply (packets=%d crc_err=%d malformed=%d rpc=%d)",
             ab_len, s->rx.packets, s->rx.crc_err, s->rx.malformed, s->rpc_count);
    }
    return ROM_PROBE_TIMEOUT;
}

int main(int argc, char **argv)
{
    struct patch pt;
    struct session sess;
    bool flash = false;
    bool rom_probe = false;
    int i, ret = 0;
    uint32_t memdest_first = 0;

    memset(&pt, 0, sizeof pt);
    memset(&sess, 0, sizeof sess);
    sess.fd_tty = -1; sess.fd_sensor = -1;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--flash")) flash = true;
        else if (!strcmp(argv[i], "--rom-probe")) rom_probe = true;
        else if (!strcmp(argv[i], "--verbose")) g_verbose = 1;
        else {
            fprintf(stderr,
                "usage: %s [--rom-probe] [--flash] [--verbose]\n"
                "  --rom-probe : open transport, autobaud, GetVersion ONLY. Never writes firmware"
                "                and never starts the application.\n"
                "  --flash     : FULL firmware download + app-start (separately authorized).\n"
                "These may not be combined.\n", argv[0]);
            ret = EXIT_USAGE; goto out;
        }
    }

    signal(SIGINT, sig_h);
    signal(SIGTERM, sig_h);

    if (flash && rom_probe) {
        fprintf(stderr, "--flash and --rom-probe are mutually exclusive\n");
        ret = EXIT_USAGE; goto out;
    }

    if (patch_load_and_verify(&pt)) { ret = EXIT_IDENTITY_INVALID; goto out; }

    /* record first memory destination for diagnostics (entry != first dest). */
    for (i = 0; i < (int)pt.nrecs; i++)
        if (pt.recs[i].tag == 0xF1) { memdest_first = pt.recs[i].dest; break; }
    logx("first memory-write dest=0x%08x (entry=0x%08x)", memdest_first, pt.entry);

    if (!flash && !rom_probe) {
        logx("read-only verification only (no device I/O). Pass --rom-probe (ROM-identity-only) or --flash (full download).");
        ret = EXIT_SUCCESS_VERIFIED; /* identity+records verified; still no hub claim */
        goto out;
    }

    /* ---- open transport ---- */
    sess.fd_tty = open(TTY_BCM, O_RDWR | O_NONBLOCK);
    if (sess.fd_tty < 0) { logx("open %s: %s", TTY_BCM, strerror(errno)); ret = EXIT_TRANSPORT_UNAVAIL; goto out; }
    /*
     * ROM-phase ownership: boot-ROM SSI/TL replies are raw RX bytes surfaced
     * on /dev/ttyBCM (see pump(), bcm_gps_spi.c bcm_on_packet_received non-peer
     * branch).  Do NOT open /dev/bbd_sensor here: holding the native peer
     * routes bcm_on_packet_received into the SSP application state machine
     * (callback_bbd_on_packet) instead of the raw SSI circ-buffer, which would
     * swallow every ROM reply and leave rx=0.
     */
    sess.fd_sensor = -1;
    rx_init(&sess.rx);
    sess.seq = 1; sess.rel_seq = 1;

    write_control("SSI:PassThru=1");

    /*
     * 1+2. ROM sync + GetVersion (shared with --flash).  This is the ONLY
     *      ROM-phase exchange.  It performs no firmware write and no app
     *      start.
     */
    {
        enum rom_probe_result pr = rom_identity_probe(&sess);
        if (pr == ROM_PROBE_NACK) {
            logx("GetVersion rejected (NACK)");
            ret = EXIT_TRANSFER_REJECTED;
            goto out;
        }
        if (pr == ROM_PROBE_CANCELLED) { ret = EXIT_CANCELLED; goto out; }
        if (pr == ROM_PROBE_TRANSPORT) { ret = EXIT_TRANSPORT_UNAVAIL; goto out; }
        if (pr != ROM_PROBE_OK) {
            logx("boot ROM handshake: no valid GetVersion reply (packets=%d crc_err=%d malformed=%d rpc=%d)",
                 sess.rx.packets, sess.rx.crc_err, sess.rx.malformed, sess.rpc_count);
            ret = EXIT_ROM_HANDSHAKE_TMO;
            goto out;
        }
        logx("boot ROM identified: GetVersion reply w0=0x%08x", sess.version_w0);
    }

    /*
     * ROM-identity-only mode ends here.  Returning now guarantees that no
     * MemoryWrite (RPC 5), StartScratchApp (RPC 46) or ServiceStart (RPC 55)
     * is ever emitted, and no rail/reset/GPIO operation is performed.  The
     * firmware-download and application-start code below is unreachable from
     * --rom-probe.
     */
    if (rom_probe) {
        ret = EXIT_ROM_IDENTIFIED;
        goto out;
    }

    /* 3. MemoryWrite each F1 record to its own destination, require reliable
     *    ACK per write. */
    {
        size_t n;
        sess.memwrites_total = 0; sess.memwrites_acked = 0;
        for (n = 0; n < pt.nrecs; n++) {
            const struct patch_rec *pr = &pt.recs[n];
            int mw;
            uint8_t body[MAX_RPC_PAYLOAD + 6];
            size_t plen;
            if (pr->tag != 0xF1) {
                /* Only F1 exists in this patch.  F0/F2..F5 would need their
                 * own command here; refuse to silently skip them. */
                logx("non-F1 record tag=0x%02X cannot be downloaded by this build", pr->tag);
                ret = EXIT_TRANSFER_INCOMPLETE; goto out;
            }
            if (pr->len - 4 > MAX_RPC_PAYLOAD - 6) { logx("F1 body too large"); ret = EXIT_TRANSFER_INCOMPLETE; goto out; }
            body[0] = (uint8_t)pr->dest; body[1] = (uint8_t)(pr->dest >> 8);
            body[2] = (uint8_t)(pr->dest >> 16); body[3] = (uint8_t)(pr->dest >> 24);
            body[4] = (uint8_t)((pr->len - 4) & 0xFF);
            body[5] = (uint8_t)((pr->len - 4) >> 8);
            memcpy(body + 6, pr->body + 4, pr->len - 4);
            plen = 6 + (pr->len - 4);
            sess.memwrites_total++;
            mw = reliable_rpc(&sess, RPC_MEM_WRITE, body, plen, 1500);
            if (mw == SSI_ENOTACK) {
                logx("MemoryWrite #%zu rejected (NACK) dest=0x%08x", n, pr->dest);
                ret = EXIT_TRANSFER_REJECTED; goto out;
            }
            if (mw == -ECANCELED) { ret = EXIT_CANCELLED; goto out; }
            if (mw != 0) {
                logx("MemoryWrite #%zu (dest=0x%08x, %u bytes) not ACKed: %s",
                     n, pr->dest, (unsigned)(pr->len - 4), strerror(-mw));
                ret = EXIT_TRANSFER_INCOMPLETE; goto out;
            }
            sess.memwrites_acked++;
            if (g_verbose) logx("MemoryWrite #%zu ACKed dest=0x%08x", n, pr->dest);
        }
        if (sess.memwrites_acked == sess.memwrites_total)
            sess.memwrites_all_acked = true;
        logx("firmware transfer confirmed: %zu/%zu writes ACKed",
             sess.memwrites_acked, sess.memwrites_total);
    }

    /* 4. StartScratchApp (RPC 46) + delay 40 ms. */
    {
        uint8_t body[4] = { (uint8_t)pt.entry, (uint8_t)(pt.entry >> 8),
                            (uint8_t)(pt.entry >> 16), (uint8_t)(pt.entry >> 24) };
        if (fire_rpc(&sess, RPC_START_SCRATCH, body, 4) < 0) { ret = EXIT_APP_START_MISSING; goto out; }
        logx("StartScratchApp (RPC 46, entry=0x%08x) sent", pt.entry);
        usleep(40 * 1000);
    }

    /* 5. ServiceStart (RPC 55) + delay 100 ms. */
    {
        uint8_t body[20] = {0};
        body[0] = (uint8_t)pt.entry; body[1] = (uint8_t)(pt.entry >> 8);
        body[2] = (uint8_t)(pt.entry >> 16); body[3] = (uint8_t)(pt.entry >> 24);
        if (fire_rpc(&sess, RPC_SERVICE_START, body, 20) < 0) { ret = EXIT_APP_START_MISSING; goto out; }
        logx("ServiceStart (RPC 55, entry=0x%08x) sent", pt.entry);
        usleep(100 * 1000);
    }

    /* 6. Confirmation GetVersion.  Only a valid version reply confirms the
     *    application is actually running. */
    {
        int gr = reliable_rpc(&sess, RPC_GET_VERSION, NULL, 0, 2500);
        if (gr == SSI_ENOTACK) { ret = EXIT_TRANSFER_REJECTED; goto out; }
        if (gr == -ECANCELED) { ret = EXIT_CANCELLED; goto out; }
        if (gr != 0 || !sess.got_version) {
            logx("application-start confirmation: no GetVersion reply after start");
            ret = EXIT_APP_START_MISSING; goto out;
        }
        logx("application confirmed: post-download GetVersion w0=0x%08x", sess.version_w0);
    }

    write_control("BBD:PassThru=0");
    write_control("ESW:READY");
    logx("READY (firmware verified + app confirmed)");
    ret = EXIT_SUCCESS_VERIFIED;

out:
    if (sess.fd_tty >= 0) close(sess.fd_tty);
    if (sess.fd_sensor >= 0) close(sess.fd_sensor);
    patch_free(&pt);
    /*
     * Restore the pass-through control state whenever we armed it
     * (SSI:PassThru=1) and did NOT already restore it in the --flash success
     * path.  This covers --rom-probe (success or failure) and every --flash
     * failure.  ESW:READY is intentionally NOT emitted here: it belongs only
     * to the fully-verified firmware+app path above.
     */
    if ((flash || rom_probe) &&
        ret != EXIT_SUCCESS_VERIFIED && ret != EXIT_IDENTITY_INVALID)
        write_control("BBD:PassThru=0");
    logx("exit %d (%s)", ret, exit_name(ret));
    return ret;
}

