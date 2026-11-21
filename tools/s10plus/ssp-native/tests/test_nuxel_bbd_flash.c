/* Host-only offline test for nuxel_bbd_flash framing and patch identity.
 * No BBD/SPI device is opened here. Verifies the RPC/TL encoding matches the
 * kernel bbd_rpc_lh.c reference decoder (size field = payload only). */
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

int main(void)
{
    uint8_t wire[8192]; size_t wn;
    uint8_t rpc[8]; size_t rn;

    /* 1. GetVersion: RPC 0 empty, reliable, seq=1. */
    rn = rpc_record(rpc, 0x00, NULL, 0);
    assert(rn == 2 && rpc[0] == 0x00 && rpc[1] == 0x00);
    wn = tl_build(wire, 1, F_RELIABLE, rpc, rn, 1);
    assert(wn == 11);
    assert(wire[0] == 0xB0 && wire[1] == 0x00);
    assert(wire[2] == 0x01);
    assert(wire[3] == 0x02); /* size = payload-only = 2 */
    assert(wire[4] == 0x02); /* RELIABLE */
    assert(wire[5] == 0x01);
    assert(wire[6] == 0x00 && wire[7] == 0x00);
    assert(wire[8] == ref_crc(wire + 2, 6));
    assert(wire[9] == 0xB0 && wire[10] == 0x01);

    /* 2. MemoryWrite RPC 5: LE32 dest + LE16 count + bytes. */
    {
        uint8_t data[3] = {'a','b','c'};
        uint8_t body[9];
        uint8_t r5[16]; size_t r5n;
        body[0]=0x61; body[1]=0x01; body[2]=0x80; body[3]=0x00; /* 0x00800161 LE */
        body[4]=0x03; body[5]=0x00;
        memcpy(body+6, data, 3);
        r5n = rpc_record(r5, 0x05, body, 9);
        assert(r5[0] == 0x05 && r5[1] == 0x09);
        assert(memcmp(r5+2, body, 9) == 0);
        (void)r5n;
    }

    /* 3. StartScratchApp RPC 46 body = LE32 entry. */
    {
        uint8_t body[4]={0x61,0x01,0x80,0x00};
        uint8_t r[8]; size_t n = rpc_record(r, 46, body, 4);
        assert(r[0] == 46 && r[1] == 4);
        assert(memcmp(r+2, body, 4) == 0); (void)n;
    }

    /* 4. ServiceStart RPC 55 body = LE32 entry + 4x LE32 zero. */
    {
        uint8_t body[20]={0}; body[0]=0x61; body[1]=0x01; body[2]=0x80; body[3]=0x00;
        uint8_t r[32]; size_t n = rpc_record(r, 55, body, 20);
        assert(r[0] == 55 && r[1] == 20);
        assert(memcmp(r+2, body, 20) == 0); (void)n;
    }

    /* 5. Patch parse. */
    {
        const char good[] = "<AsicVersion=0x004775B0>\n<BlobLength=438895>\n"
                            "<PatchAddress=0x00800161>\n<Crc=0x000000C1>\n"
                            "<Blob=010203>\n";
        uint8_t *blob = NULL; size_t blen = 0;
        assert(parse_hex_hdr((const uint8_t*)good, strlen(good), "AsicVersion") == 0x004775b0u);
        assert(parse_hex_hdr((const uint8_t*)good, strlen(good), "BlobLength") == 438895u);
        assert(parse_hex_hdr((const uint8_t*)good, strlen(good), "PatchAddress") == 0x00800161u);
        blob = patch_blob((const uint8_t*)good, strlen(good), &blen);
        assert(blob && blen == 3 && blob[0]==0x01 && blob[2]==0x03);
        free(blob);
    }

    puts("PASS nuxel_bbd_flash framing + patch identity (offline)");
    return 0;
}
