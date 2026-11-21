/* Offline tests for nuxel_bbd_flash: TL framing, RPC encode, F1 record
 * decoding, patch identity, and (implicitly) the receive state machine.
 * No device I/O. */
#define NO_MAIN_NUXEL_BBD_FLASH
#define main nuxel_bbd_flash_program_main
#include "../nuxel_bbd_flash.c"
#undef main
#undef NO_MAIN_NUXEL_BBD_FLASH

#include <assert.h>
#include <string.h>

static uint8_t ref_crc(const uint8_t *body, size_t n)
{
    uint8_t crc = 0; size_t i;
    for (i = 1; i < n; i++) crc = crc_tbl[crc ^ body[i]];
    return (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
}

/* Build a GetVersion reliable packet and verify wire layout. */
static void test_tl_getversion(void)
{
    uint8_t wire[MAX_TL_WIRE]; size_t wn;
    uint8_t rpc[8]; size_t rn;
    rn = rpc_record(rpc, RPC_GET_VERSION, NULL, 0);
    assert(rn == 2 && rpc[0] == 0x00 && rpc[1] == 0x00);
    wn = tl_build(wire, 1, F_RELIABLE, rpc, rn, 1);
    assert(wn == 11);
    assert(wire[0] == 0xB0 && wire[1] == 0x00); /* SOP */
    assert(wire[2] == 0x01);          /* seq */
    assert(wire[3] == 0x02);          /* size = payload only = 2 */
    assert(wire[4] == 0x02);          /* F_RELIABLE */
    assert(wire[5] == 0x01);          /* rel_seq */
    assert(wire[6] == 0x00 && wire[7] == 0x00); /* RPC 0, len 0 */
    assert(wire[8] == ref_crc(wire + 2, 6));
    assert(wire[9] == 0xB0 && wire[10] == 0x01); /* EOP */
}

/* MemoryWrite RPC 5: LE32 dest + LE16 count + bytes. */
static void test_rpc_memwrite(void)
{
    uint8_t data[3] = {'a','b','c'};
    uint8_t body[9], r5[16];
    body[0]=0x00; body[1]=0x00; body[2]=0x80; body[3]=0x00; /* 0x00800000 LE */
    body[4]=0x03; body[5]=0x00;
    memcpy(body+6, data, 3);
    rpc_record(r5, RPC_MEM_WRITE, body, 9);
    assert(r5[0] == 0x05 && r5[1] == 0x09);
    assert(memcmp(r5+2, body, 9) == 0);
}

/* StartScratchApp RPC 46: LE32 entry; ServiceStart RPC 55: entry + 4x zero. */
static void test_rpc_start(void)
{
    uint8_t body46[4]={0x61,0x01,0x80,0x00};
    uint8_t r[32];
    rpc_record(r, RPC_START_SCRATCH, body46, 4);
    assert(r[0] == 46 && r[1] == 4 && memcmp(r+2, body46, 4)==0);

    uint8_t body55[20]={0}; body55[0]=0x61; body55[1]=0x01; body55[2]=0x80; body55[3]=0x00;
    rpc_record(r, RPC_SERVICE_START, body55, 20);
    assert(r[0] == 55 && r[1] == 20 && memcmp(r+2, body55, 20)==0);
}

/* Patch record stream: F1 tag, LE16 len, LE32 dest, data. */
static void test_patch_records(void)
{
    /* Build a tiny 2-record patch blob and hand it to the parser. */
    uint8_t blob[3 + 1 + 2 + 4 + 3 + 1 + 2 + 4 + 2];
    size_t off = 0;
    blob[off++] = 0xF1;
    blob[off++] = (4+3) & 0xFF; blob[off++] = (4+3) >> 8; /* len=7 */
    blob[off++]=0x00; blob[off++]=0x01; blob[off++]=0x80; blob[off++]=0x00; /* 0x00800100 LE */
    blob[off++]='x'; blob[off++]='y'; blob[off++]='z';
    blob[off++] = 0xF1;
    blob[off++] = (4+2) & 0xFF; blob[off++] = (4+2) >> 8; /* len=6 */
    blob[off++]=0x90; blob[off++]=0x03; blob[off++]=0x80; blob[off++]=0x00; /* 0x00800390 LE */
    blob[off++]='p'; blob[off++]='q';

    struct patch pt;
    memset(&pt, 0, sizeof pt);
    pt.blob = blob; pt.blob_len = off;
    assert(patch_parse_records(&pt) == 0);
    assert(pt.nrecs == 2);
    assert(pt.recs[0].tag == 0xF1 && pt.recs[0].dest == 0x00800100u);
    assert(pt.recs[0].len == 7);
    assert(pt.recs[1].tag == 0xF1 && pt.recs[1].dest == 0x00800390u);
    assert(pt.recs[1].len == 6);
    /* free the recs array only (blob is stack) */
    free(pt.recs);

    /* Malformed: tag out of range. */
    uint8_t bad[4] = { 0xEE, 0x04, 0x00, 0x00 };
    struct patch p2; memset(&p2, 0, sizeof p2);
    p2.blob = bad; p2.blob_len = sizeof bad;
    assert(patch_parse_records(&p2) != 0);
    free(p2.recs);

    /* Truncated F1. */
    uint8_t trunc[6] = { 0xF1, 0xFF, 0xFF, 0x00 }; /* len 65535 > avail */
    struct patch p3; memset(&p3, 0, sizeof p3);
    p3.blob = trunc; p3.blob_len = sizeof trunc;
    assert(patch_parse_records(&p3) != 0);
    free(p3.recs);
}

/* Receive state machine: feed a valid GetVersion reply TL packet and confirm
 * the RPC callback classifies it. */
static int g_cb_version;
static void cb_version(const struct rx_pkt *pkt, void *ctx)
{
    (void)ctx;
    if (pkt->reliable) g_cb_version++;
}

static void test_rx_decode(void)
{
    /* Construct a GetVersion reply: RPC 0 with a 4-byte version body,
     * reliable ACK flags set. */
    struct rx rr; rx_init(&rr);
    /* body: seq=1, size=6 (RPC: id 0, len 4, payload), flags=RELIABLE|RELIABLE_ACK */
    uint8_t body[3 + 1 + 1 + 6 + 1]; /* seq,size,flags, rel_seq, rel_ack_seq, [6], crc */
    size_t bn = 0;
    uint8_t rpc[6]; /* RPC id=0, len=4, 4 payload bytes */
    rpc[0]=0x00; rpc[1]=0x04; rpc[2]=0x12; rpc[3]=0x34; rpc[4]=0x56; rpc[5]=0x78;
    body[bn++]=1;         /* seq */
    body[bn++]=6;         /* size = payload only = 6 */
    body[bn++]=F_RELIABLE | F_REL_ACK;
    body[bn++]=1;         /* rel_seq */
    body[bn++]=1;         /* rel_ack_seq */
    memcpy(body+bn, rpc, 6); bn += 6;
    uint8_t crc = ref_crc(body, bn);
    body[bn++] = crc;

    /* Now escape into wire (local flat encoder; put_raw/put_esc are pointer
     * walkers not suitable for a fixed array here). */
    uint8_t wire[MAX_TL_WIRE]; size_t wn=0;
    wire[wn++]=ESC; wire[wn++]=0x00;
    for (size_t i=0;i<bn;i++) {
        switch (body[i]) {
        case ESC: wire[wn++]=ESC; wire[wn++]=ESC_ESC; break;
        case XON: wire[wn++]=ESC; wire[wn++]=ESC_XON; break;
        case XOFF: wire[wn++]=ESC; wire[wn++]=ESC_XOFF; break;
        default: wire[wn++]=body[i]; break;
        }
    }
    wire[wn++]=ESC; wire[wn++]=EOP;

    g_cb_version = 0;
    rx_feed(&rr, wire, wn, cb_version, NULL);
    assert(rr.packets == 1);
    assert(rr.crc_err == 0);
    assert(rr.malformed == 0);
    assert(g_cb_version == 1);
}

int main(void)
{
    test_tl_getversion();
    test_rpc_memwrite();
    test_rpc_start();
    test_patch_records();
    test_rx_decode();
    puts("PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)");
    return 0;
}
