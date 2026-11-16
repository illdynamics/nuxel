/* SIMULATED host-only tests: no BBD or SPI device is opened here. */
#define main nuxel_bbd_download_program_main
#include "../nuxel_bbd_download.c"
#undef main

#include <assert.h>

static void test_tl_round_trip_and_fragmentation(void)
{
	struct tx tx = {0};
	struct rx rx = {0};
	const uint8_t rpc[] = { 0x01, 0x03, 0xb0, 0x11, 0x13 };

	tl_packet(&tx, 255, 0, NULL, 0, rpc, sizeof(rpc));
	/* Feed one byte at a time to exercise the fractured-stream state machine. */
	for (size_t i = 0; i < tx.n; i++)
		rx_feed(&rx, tx.b + i, 1);
	assert(rx.packets == 1);
	assert(rx.crc_err == 0);
	assert(rx.last_seq == 255);
	assert(rx.rpc_seen[1] == 1);
}

static void test_crc_failure_is_rejected(void)
{
	struct tx tx = {0};
	struct rx rx = {0};
	const uint8_t rpc[] = { 0x00, 0x00 };

	tl_packet(&tx, 0, 0, NULL, 0, rpc, sizeof(rpc));
	assert(tx.n > 3);
	tx.b[tx.n - 3] ^= 0x01; /* CRC byte before ESC,EOP */
	rx_feed(&rx, tx.b, tx.n);
	assert(rx.packets == 0);
	assert(rx.crc_err == 1);
}

static void test_patch_validation(void)
{
	char good[256], bad[256];
	uint8_t *blob = NULL;
	size_t blen = 0;
	uint32_t addr = 0;
	const uint8_t bytes[] = { 0x01, 0x02 };
	uint32_t crc = crc32_ieee(bytes, sizeof(bytes));

	snprintf(good, sizeof(good),
		 "<AsicVersion=0x004775B0>\n<BlobLength=2>\n<PatchAddress=0x00800161>\n<Crc=0x%08x>\n<Blob=0102>\n",
		 crc);
	assert(validate_patch((const uint8_t *)good, strlen(good), &blob, &blen, &addr) == 0);
	assert(blen == 2 && addr == 0x00800161 && !memcmp(blob, bytes, 2));
	free(blob);
	snprintf(bad, sizeof(bad),
		 "<AsicVersion=0x004775B0>\n<BlobLength=3>\n<PatchAddress=0x00800161>\n<Crc=0x%08x>\n<Blob=0102>\n",
		 crc);
	assert(validate_patch((const uint8_t *)bad, strlen(bad), &blob, &blen, &addr) != 0);
}

int main(void)
{
	test_tl_round_trip_and_fragmentation();
	test_crc_failure_is_rejected();
	test_patch_validation();
	puts("PASS SIMULATED nuxel_bbd_download framing, CRC, and patch validation");
	return 0;
}
