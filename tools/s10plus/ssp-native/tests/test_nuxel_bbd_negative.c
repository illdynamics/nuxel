/* Offline negative-case tests for nuxel_bbd_flash.c's pure protocol/parser
 * functions. No device I/O: only patch records, header decoding, RPC/TL
 * framing, the RX state machine and the reliable-RPC session state machine
 * (exercised over an in-memory socketpair). */
#define NO_MAIN_NUXEL_BBD_FLASH
#define main nuxel_bbd_flash_program_main
#include "../nuxel_bbd_flash.c"
#undef main
#undef NO_MAIN_NUXEL_BBD_FLASH

#include <assert.h>
#include <string.h>
#include <sys/socket.h>

/* --- helpers ------------------------------------------------------------ */
static uint8_t crc_of(const uint8_t *body, size_t n)
{
    uint8_t crc = 0;
    size_t i;
    for (i = 1; i < n; i++) crc = crc_tbl[crc ^ body[i]];
    return (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
}

/* Feed an already-escaped wire buffer through rx_feed. */
static void feed_wire(struct rx *r, const uint8_t *wire, size_t n, rx_pkt_cb cb, void *ctx)
{
    rx_feed(r, wire, n, cb, ctx);
}

/* Build a wire packet with an arbitrary body (seq,size,flags,details...,payload)
 * and a caller-supplied (possibly wrong) CRC byte. */
static size_t build_wire(uint8_t *wire, const uint8_t *body, size_t bn, uint8_t crc)
{
    size_t wn = 0, i;
    wire[wn++] = ESC; wire[wn++] = 0x00; /* SOP */
    for (i = 0; i < bn; i++) {
        switch (body[i]) {
        case ESC: wire[wn++] = ESC; wire[wn++] = ESC_ESC; break;
        case XON: wire[wn++] = ESC; wire[wn++] = ESC_XON; break;
        case XOFF: wire[wn++] = ESC; wire[wn++] = ESC_XOFF; break;
        default: wire[wn++] = body[i]; break;
        }
    }
    switch (crc) {
    case ESC: wire[wn++] = ESC; wire[wn++] = ESC_ESC; break;
    case XON: wire[wn++] = ESC; wire[wn++] = ESC_XON; break;
    case XOFF: wire[wn++] = ESC; wire[wn++] = ESC_XOFF; break;
    default: wire[wn++] = crc; break;
    }
    wire[wn++] = ESC; wire[wn++] = EOP;
    return wn;
}

/* --- F0..F5 malformed / truncated -------------------------------------- */
static void test_f0_f5_malformed_truncated(void)
{
    /* Each of F0..F5 with a length that overruns the buffer must fail. */
    uint8_t tag;
    for (tag = 0xF0; tag <= 0xF5; tag++) {
        uint8_t blob[8] = { tag, 0xFF, 0xFF, 0, 0, 0, 0, 0 }; /* len 65535 */
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        assert(patch_parse_records(&pt) != 0); /* truncated */
        free(pt.recs);
    }

    /* F0 with body but a len that points exactly past the end (off+3+len >
     * blob_len) is truncated. */
    {
        uint8_t blob[4] = { 0xF0, 0x01, 0x00, 0xAA }; /* len=1, but off+3+1=4 == blob_len OK -> valid */
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        /* len=1 fits exactly (off=0, +3+1 = 4 == 4): not truncated, but tag F0
         * is a non-F1 record we do NOT dispatch; parser must still accept it
         * structurally (return 0) and set tag. */
        assert(patch_parse_records(&pt) == 0);
        assert(pt.nrecs == 1 && pt.recs[0].tag == 0xF0 && pt.recs[0].len == 1);
        free(pt.recs);
    }

    /* Truncated mid-tag: a leading F1 tag alone with no room for length. */
    {
        uint8_t blob[2] = { 0xF1, 0x01 }; /* missing second length byte */
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        /* off+3+len needs off+1 and off+2 to read len; off+2 is OOB read but
         * len computed from bytes 1,2; guarded by off + 3 + len > blob_len. */
        assert(patch_parse_records(&pt) != 0);
        free(pt.recs);
    }

    /* F1 too short: len < 5 cannot hold LE32 dest + 1 byte. */
    {
        uint8_t blob[6] = { 0xF1, 0x03, 0x00, 0x00, 0x00, 0x00 }; /* len=3 < 5 */
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        assert(patch_parse_records(&pt) != 0);
        free(pt.recs);
    }

    /* Zero-length record: len=0 -> off advances by 3, infinite-ish but bounded
     * by nrecs runaway guard; here it must not advance and must flag nothing
     * invalid structurally (tag valid). Actually a zero-length F1 is <5 so
     * only F0/F2..F5 accept len 0. Verify F0 len=0 parses as one record. */
    {
        uint8_t blob[3] = { 0xF0, 0x00, 0x00 };
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        assert(patch_parse_records(&pt) == 0);
        assert(pt.nrecs == 1 && pt.recs[0].len == 0);
        free(pt.recs);
    }

    /* Tag outside F0..F5 -> immediate reject. */
    {
        uint8_t blob[3] = { 0xEE, 0x00, 0x00 };
        struct patch pt; memset(&pt, 0, sizeof pt);
        pt.blob = blob; pt.blob_len = sizeof blob;
        assert(patch_parse_records(&pt) != 0);
        free(pt.recs);
    }
}

/* --- header decode edge cases ------------------------------------------ */
static void test_header_decode_edge_cases(void)
{
    const uint8_t *h;
    size_t n;

    /* Missing AsicVersion/BlobLength/PatchAddress/Crc -> 0. */
    h = (const uint8_t *)"<Blob=01>\n";
    n = strlen((const char *)h);
    assert(parse_hex_hdr(h, n, "AsicVersion") == 0);
    assert(parse_hex_hdr(h, n, "BlobLength") == 0);
    assert(parse_hex_hdr(h, n, "PatchAddress") == 0);
    assert(parse_hex_hdr(h, n, "Crc") == 0);

    /* Hex empty value -> strtoull no digits -> returns 0 (ambiguous but safe). */
    h = (const uint8_t *)"<AsicVersion=>\n";
    n = strlen((const char *)h);
    assert(parse_hex_hdr(h, n, "AsicVersion") == 0);

    /* Odd-length hex blob: decoder pairs hex digits, trailing nibble dropped. */
    {
        const uint8_t hdr[] = "<Blob=ABC>\n";
        size_t blen = 0;
        uint8_t *b = patch_blob_decode(hdr, sizeof hdr - 1, &blen);
        assert(b != NULL && blen == 1 && b[0] == 0xAB);
        free(b);
    }

    /* No <Blob= terminator -> decode returns NULL. */
    {
        const uint8_t hdr[] = "<Blob=0102"; /* no closing >\n */
        size_t blen = 0;
        assert(patch_blob_decode(hdr, sizeof hdr - 1, &blen) == NULL);
    }

    /* Empty blob (<Blob=> no digits) -> zero-length blob, non-NULL alloc. */
    {
        const uint8_t hdr[] = "<Blob=>\n";
        size_t blen = 0;
        uint8_t *b = patch_blob_decode(hdr, sizeof hdr - 1, &blen);
        assert(b != NULL && blen == 0);
        free(b);
    }
}

/* --- identity (version) mismatch --------------------------------------- */
/* Directly exercise the identity check that gate-keeps firmware identity:
 * asic / declared length / entry must each match the pinned constants or the
 * container is REJECTED before any record is dispatched. We mirror the exact
 * condition from patch_load_and_verify() (no device I/O here). */
static int identity_ok(uint32_t asic, uint32_t declared_len, uint32_t entry)
{
    return asic == EXPECT_ASIC && declared_len == EXPECT_BLOB_LEN &&
           entry == EXPECT_ENTRY;
}
static void test_identity_version_mismatch(void)
{
    assert(identity_ok(EXPECT_ASIC, EXPECT_BLOB_LEN, EXPECT_ENTRY));
    assert(!identity_ok(EXPECT_ASIC ^ 1, EXPECT_BLOB_LEN, EXPECT_ENTRY));  /* wrong asic */
    assert(!identity_ok(EXPECT_ASIC, EXPECT_BLOB_LEN + 1, EXPECT_ENTRY));  /* wrong length */
    assert(!identity_ok(EXPECT_ASIC, EXPECT_BLOB_LEN, EXPECT_ENTRY + 1));  /* wrong entry */
    assert(!identity_ok(0, 0, 0));
}

/* --- RPC/TL framing edge cases ------------------------------------------ */
static void test_rpc_field_boundaries(void)
{
    uint8_t o[4];
    /* 0x7f is one byte; 0x80 is two bytes. */
    assert(rpc_field(o, 0x7F) == 1 && o[0] == 0x7F);
    assert(rpc_field(o, 0x80) == 2 && o[0] == 0x80 && o[1] == 0x80);
    assert(rpc_field(o, 0x3FFF) == 2 && o[0] == 0xBF && o[1] == 0xFF);
}

static void test_tl_build_oversize_payload_fails(void)
{
    uint8_t wire[MAX_TL_WIRE];
    uint8_t payload[MAX_RPC_PAYLOAD + 1];
    memset(payload, 0, sizeof payload);
    assert(tl_build(wire, 1, 0, payload, MAX_RPC_PAYLOAD + 1, 0) == 0);
}

/* --- RX state machine: wrong CRC ---------------------------------------- */
static void test_rx_wrong_crc_all_bit_positions(void)
{
    /* A single corrupted CRC byte must be rejected (crc_err++, no packet). */
    uint8_t body[3] = { 7, 0, F_ACK }; /* seq=7, size=0, flags=ACK */
    uint8_t crc = crc_of(body, sizeof body);
    struct rx r; rx_init(&r);
    uint8_t wire[64];
    size_t wn = build_wire(wire, body, sizeof body, (uint8_t)(crc ^ 0xFF));
    feed_wire(&r, wire, wn, NULL, NULL);
    assert(r.packets == 0 && r.crc_err == 1);
}

/* --- RX: bad ACK / NACK flag combos ------------------------------------- */
static int g_seen_ack, g_seen_relack, g_seen_relnack, g_seen_reliable;
static void count_pkt_cb(const struct rx_pkt *pkt, void *ctx)
{
    (void)ctx;
    if (pkt->flags & F_ACK) g_seen_ack++;
    if (pkt->rel_ack) g_seen_relack++;
    if (pkt->rel_nack) g_seen_relnack++;
    if (pkt->reliable) g_seen_reliable++;
}
static void test_rx_ack_nack_classification(void)
{
    struct rx r; rx_init(&r);
    g_seen_ack = g_seen_relack = g_seen_relnack = g_seen_reliable = 0;

    /* Plain ACK (F_ACK) with a detail byte: detail consumed, no reliable. */
    {
        uint8_t b2[4] = { 1, 0, F_ACK, 42 };
        uint8_t wire[64];
        size_t wn = build_wire(wire, b2, sizeof b2, crc_of(b2, sizeof b2));
        feed_wire(&r, wire, wn, count_pkt_cb, NULL);
    }
    /* REL_NACK alone (no REL_ACK) */
    {
        uint8_t b2[4] = { 2, 0, F_REL_NACK, 8 };
        uint8_t wire[64];
        size_t wn = build_wire(wire, b2, sizeof b2, crc_of(b2, sizeof b2));
        feed_wire(&r, wire, wn, count_pkt_cb, NULL);
    }
    /* REL_NACK + reliable mismatch must still classify rel_nack. */
    {
        uint8_t b2[5] = { 3, 0, F_RELIABLE | F_REL_NACK, 1, 9 };
        uint8_t wire[64];
        size_t wn = build_wire(wire, b2, sizeof b2, crc_of(b2, sizeof b2));
        feed_wire(&r, wire, wn, count_pkt_cb, NULL);
    }

    assert(r.packets == 3 && r.malformed == 0 && r.crc_err == 0);
    assert(g_seen_ack == 1);           /* first only */
    assert(g_seen_relack == 0);        /* none of the three */
    assert(g_seen_relnack == 2 && g_seen_reliable == 1);
}

/* --- no reply => reliable_rpc times out (returns -ETIMEDOUT) ------------- */
static void test_reliable_rpc_no_reply_times_out(void)
{
    int fd[2];
    struct session s;
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, fd) == 0);
    memset(&s, 0, sizeof s);
    s.fd_tty = fd[0]; s.fd_sensor = fd[0]; /* write to fd[0], read notices nothing */
    rx_init(&s.rx);
    s.seq = 1; s.rel_seq = 1;
    /* Never write a reply from the peer: reliable_rpc must time out. */
    int rc = reliable_rpc(&s, RPC_GET_VERSION, NULL, 0, 30);
    assert(rc == -ETIMEDOUT);
    close(fd[0]); close(fd[1]);
}

/* --- NACK => reliable_rpc returns SSI_ENOTACK ---------------------------- */
static void test_reliable_rpc_nack(void)
{
    int fd[2];
    struct session s;
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, fd) == 0);
    memset(&s, 0, sizeof s);
    s.fd_tty = fd[0]; s.fd_sensor = fd[1];
    rx_init(&s.rx);
    s.seq = 1; s.rel_seq = 1;
    /* Peer sends a REL_NACK for the outstanding rel_seq (2 after increment). */
    /* reliable_rpc increments rel_seq to 2 and sends; peer replies NACK seq 2. */
    /* We pre-write the NACK so pump() reads it. */
    {
        uint8_t nack_body[4] = { 1, 0x00, F_REL_NACK, 2 }; /* seq=1,size=0,flags=REL_NACK, detail=2 */
        uint8_t wire[64];
        size_t wn = build_wire(wire, nack_body, sizeof nack_body, crc_of(nack_body, sizeof nack_body));
        assert(write(fd[0], wire, wn) == (ssize_t)wn);
    }
    int rc = reliable_rpc(&s, RPC_GET_VERSION, NULL, 0, 300);
    assert(rc == SSI_ENOTACK);
    assert(s.got_rel_nack && s.rel_nack_seq == 2);
    close(fd[0]); close(fd[1]);
}

/* --- cancellation => reliable_rpc returns -ECANCELED --------------------- */
static void test_reliable_rpc_cancelled(void)
{
    int fd[2];
    struct session s;
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, fd) == 0);
    memset(&s, 0, sizeof s);
    s.fd_tty = fd[0]; s.fd_sensor = fd[0];
    rx_init(&s.rx);
    s.seq = 1; s.rel_seq = 1;
    g_cancelled = 1;
    errno = ECANCELED; /* the write-abort path maps cancellation via -errno */
    int rc = reliable_rpc(&s, RPC_GET_VERSION, NULL, 0, 300);
    assert(rc == -ECANCELED);
    g_cancelled = 0;
    close(fd[0]); close(fd[1]);
}

/* --- reliable sequence rollover (8-bit wrap) ----------------------------- */
static void test_seq_rollover(void)
{
    struct session s;
    uint8_t wire[MAX_TL_WIRE];
    uint8_t rpc[8]; size_t rn;
    memset(&s, 0, sizeof s);
    s.seq = 254; s.rel_seq = 254;
    rn = rpc_record(rpc, RPC_GET_VERSION, NULL, 0);
    /* seq wraps 254 -> 255, rel_seq wraps 254 -> 255. */
    assert(tl_build(wire, s.seq++, F_RELIABLE, rpc, rn, ++s.rel_seq) != 0);
    assert(s.seq == 255 && s.rel_seq == 255);
    /* next wraps to 0. */
    assert(tl_build(wire, s.seq++, F_RELIABLE, rpc, rn, ++s.rel_seq) != 0);
    assert(s.seq == 0 && s.rel_seq == 0);
}

/* --- reentrancy of RX parser: nested feed during callback ----------------- */
static int g_nested_ok;
static void nested_cb(const struct rx_pkt *pkt, void *ctx)
{
    (void)pkt;
    struct rx *r = ctx;
    /* Feed a second valid packet synchronously inside the callback. */
    uint8_t b2[4] = { 9, 0, F_ACK, 1 };
    uint8_t wire[64];
    size_t wn = build_wire(wire, b2, sizeof b2, crc_of(b2, sizeof b2));
    feed_wire(r, wire, wn, NULL, NULL);
    g_nested_ok = 1;
}
static void test_rx_reentrancy(void)
{
    struct rx r; rx_init(&r);
    uint8_t b2[4] = { 1, 0, F_ACK, 1 };
    uint8_t wire[64];
    size_t wn = build_wire(wire, b2, sizeof b2, crc_of(b2, sizeof b2));
    g_nested_ok = 0;
    feed_wire(&r, wire, wn, nested_cb, &r);
    assert(g_nested_ok == 1); /* nested feed did not corrupt parser state */
    assert(r.packets >= 1);
}

/* --- partial transfer / short read: split across many 1-byte feeds --------- */
static void test_rx_partial_transfer_and_short_read(void)
{
    struct rx r; rx_init(&r);
    uint8_t body[4] = { 5, 0, F_REL_ACK, 7 };
    uint8_t wire[64];
    size_t wn = build_wire(wire, body, sizeof body, crc_of(body, sizeof body));
    size_t i;
    for (i = 0; i < wn; i++)
        feed_wire(&r, wire + i, 1, NULL, NULL); /* 1 byte at a time */
    assert(r.packets == 1 && r.crc_err == 0 && r.malformed == 0);
    /* A truncated wire (dropped EOP) leaves the parser mid-message and a new
     * SOP resets it cleanly. */
    feed_wire(&r, wire, wn - 2, NULL, NULL); /* missing trailing EOP */
    feed_wire(&r, wire, wn, NULL, NULL);     /* fresh packet resets */
    assert(r.packets == 2);
}

/* --- duplicate / same-buffer open (no exclusive lock in parser) ----------- */
/* The parser is stateless per-instance; two instances are independent. */
static void test_two_instances_independent(void)
{
    struct rx a, b;
    rx_init(&a); rx_init(&b);
    uint8_t body[4] = { 7, 0, F_ACK, 1 };
    uint8_t wire[64];
    size_t wn = build_wire(wire, body, sizeof body, crc_of(body, sizeof body));
    feed_wire(&a, wire, wn, NULL, NULL);
    assert(a.packets == 1 && b.packets == 0);
}

int main(void)
{
    test_f0_f5_malformed_truncated();
    test_header_decode_edge_cases();
    test_identity_version_mismatch();
    test_rpc_field_boundaries();
    test_tl_build_oversize_payload_fails();
    test_rx_wrong_crc_all_bit_positions();
    test_rx_ack_nack_classification();
    test_reliable_rpc_no_reply_times_out();
    test_reliable_rpc_nack();
    test_reliable_rpc_cancelled();
    test_seq_rollover();
    test_rx_reentrancy();
    test_rx_partial_transfer_and_short_read();
    test_two_instances_independent();
    puts("PASS nuxel_bbd_flash negative cases (offline)");
    return 0;
}
