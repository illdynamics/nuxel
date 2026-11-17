/* SIMULATED host-only tests: no BBD or SPI device is opened here. */
#define main nuxel_bbd_download_program_main
#include "../nuxel_bbd_download.c"
#undef main

#include <assert.h>
#include <sys/socket.h>

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

/* Manually specified decoded bodies follow the kernel receive contract;
 * this helper deliberately does not use the production TL encoder. */
static void feed_body(struct rx *rx, const uint8_t *body, size_t n)
{
	struct tx wire = {0}; uint8_t crc = 0;
	put_raw(&wire, ESC); put_raw(&wire, 0);
	for (size_t i = 0; i < n; i++) {
		put_esc(&wire, body[i]);
		if (i) crc = crc_tbl[crc ^ body[i]];
	}
	put_esc(&wire, (uint8_t)((crc << 4) | (crc >> 4)));
	put_raw(&wire, ESC); put_raw(&wire, EOP);
	rx_feed(rx, wire.b, wire.n);
}

static void test_source_contract(void)
{
	struct rx rx = {0};
	/* Packet ACK and reliable ACK have separate sequence details. */
	const uint8_t ack[] = {7, 0, F_ACK | F_REL_ACK, 42, 9};
	feed_body(&rx, ack, sizeof ack);
	assert(rx.packets == 1 && rx.nevents == 0);
	assert(rx.flags == (F_ACK | F_REL_ACK));
	assert(rx.details[0] == 42 && rx.details[2] == 9);
	const uint8_t nack[] = {8, 0, F_REL_NACK, 8};
	feed_body(&rx, nack, sizeof nack);
	assert(rx.packets == 2 && rx.details[3] == 8);
	/* Size excludes details; missing detail, unknown flag and surplus data fail. */
	const uint8_t bad[][6] = {
		{9, 1, F_ACK, 42}, {9, 0, F_ACK},
		{9, 0, F_EXT, 4, 0}, {9, 0, 0, 0},
		{9, 3, 0, 1, 2, 0}, /* truncated RPC */
	};
	const size_t sizes[] = {4, 3, 5, 4, 6};
	for (size_t i = 0; i < sizeof sizes / sizeof sizes[0]; i++)
		feed_body(&rx, bad[i], sizes[i]);
	assert(rx.packets == 2 && rx.malformed == 5 && rx.nevents == 0);
	const uint8_t internal[] = {10, 1, F_EXT, 1, 0, 0xff};
	feed_body(&rx, internal, sizeof internal);
	assert(rx.packets == 3 && rx.nevents == 0); /* internal data is not RPC */
}

static void test_extended_and_restart(void)
{
	struct tx tx = {0}; struct rx rx = {0};
	uint8_t payload[260] = {0}; /* 130 empty RPC records */
	uint8_t detail = 4;
	tl_packet(&tx, 0, F_RELIABLE, &detail, 1, payload, sizeof payload);
	rx_feed(&rx, tx.b, tx.n);
	assert(rx.packets == 1 && rx.rpc_seen[0] == 130);
	assert(rx.details[1] == 4 && (rx.flags & F_SIZE_EXT));
	const uint8_t unfinished[] = {ESC, 0, 99, 20, 0};
	rx_feed(&rx, unfinished, sizeof unfinished);
	rx_feed(&rx, tx.b, tx.n);
	assert(rx.packets == 2); /* new SOP discards partial old message */
	rx.state = 3; rx.mlen = sizeof(rx.msg);
	const uint8_t escaped = ESC_ESC;
	rx_feed(&rx, &escaped, 1);
	assert(rx.state == 0 && rx.malformed == 1);
}

static void test_unrelated_packet_cannot_complete_transaction(void)
{
	/* None of these establish operation completion, including an ACK whose
	 * packet sequence matches. No RPC-response matcher is established. */
	const uint8_t bodies[][5] = {
		{91, 2, 0, 0x21, 0}, /* unrelated RPC */
		{91, 0, F_ACK, 0}, /* matching packet ACK */
		{91, 0, F_ACK, 99}, /* stale packet ACK */
		{91, 0, F_REL_ACK, 0},
		{91, 0, F_REL_NACK, 0},
	};
	const size_t sizes[] = {5, 4, 4, 4, 4};
	for (size_t i = 0; i < sizeof sizes / sizeof sizes[0]; i++) {
		int fd[2]; assert(socketpair(AF_UNIX, SOCK_STREAM, 0, fd) == 0);
		struct chan c = {0}; struct rpcmsg request = {0}; struct tx wire = {0};
		uint8_t crc = 0;
		put_raw(&wire, ESC); put_raw(&wire, 0);
		for (size_t j = 0; j < sizes[i]; j++) {
			put_esc(&wire, bodies[i][j]);
			if (j) crc = crc_tbl[crc ^ bodies[i][j]];
		}
		put_esc(&wire, (uint8_t)((crc << 4) | (crc >> 4)));
		put_raw(&wire, ESC); put_raw(&wire, EOP);
		c.tf = fd[0]; c.sf = -1;
		assert(write(fd[1], wire.b, wire.n) == (ssize_t)wire.n);
		rpc_add(&request, 0, NULL, 0);
		assert(transact(&c, &request, 20, "SIMULATED non-completion") == 0);
		assert(c.rx.packets == 1);
		close(fd[0]); close(fd[1]);
	}
}

int main(void)
{
	test_tl_round_trip_and_fragmentation();
	test_crc_failure_is_rejected();
	test_patch_validation();
	test_source_contract();
	test_extended_and_restart();
	test_unrelated_packet_cannot_complete_transaction();
	puts("PASS SIMULATED nuxel_bbd_download framing, CRC, and patch validation");
	return 0;
}
