/*
 * nuxel_bbd_host — native host side of the Samsung BBD/SSP transport for the
 * Galaxy S10+ (beyond2lte, BCM47752 sensor hub) on Nuxel.
 *
 * Android runs the vendor daemon "lhd" for this job.  lhd cannot run under
 * glibc (Bionic, HAL, Android services), so this tool implements the pieces
 * the bring-up needs, taken from the kernel's own reference decoder
 * (drivers/sensorhub/brcm/bbdpl/bbd_rpc_lh.c) and the on-device lhd.conf:
 *
 *  - TL  : transport layer (escape 0xB0 / SOP 0x00 / EOP 0x01, seqId,
 *          flags, CRC-8, reliable packet / ack / nack).
 *  - RPC : IRpcSensorRequest data (RPC 34) carries raw SSP packets,
 *          IRpcSensorResponse data (RPC 35) delivers MCU->AP packets.
 *  - LHD : the BBD "hello" request the hub answers once its application
 *          patch is uploaded (used as a liveness probe; never fabricated).
 *
 * It never invents sensor samples: every byte printed came from the hub or
 * from the kernel.
 *
 * Usage:
 *   nuxel_bbd_host --selftest
 *   nuxel_bbd_host --probe [--ms N]       probe hub liveness (no writes)
 *   nuxel_bbd_host --send-hex HEX ...     send one RPC chunk
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define BBD_SENSOR   "/dev/bbd_sensor"
#define BBD_PATCH    "/dev/bbd_patch"
#define BBD_CONTROL  "/dev/bbd_control"
#define TTY_BCM      "/dev/ttyBCM"

#define RPC_SENSOR_REQUEST   34
#define RPC_SENSOR_RESPONSE  35

#define ESC      0xB0
#define ESC_ESC  0x03
#define ESC_XON  0x04
#define ESC_XOFF 0x05
#define XON      0x11
#define XOFF     0x13
#define EOP      0x01

#define FLAG_PACKET_ACK       (1u << 0)
#define FLAG_RELIABLE_PACKET  (1u << 1)
#define FLAG_RELIABLE_ACK     (1u << 2)
#define FLAG_RELIABLE_NACK    (1u << 3)
#define FLAG_SIZE_EXTENDED    (1u << 6)
#define FLAG_EXTENDED         (1u << 7)
#define FLAG_INTERNAL_PACKET  (1u << 8)
#define FLAG_IGNORE_SEQID     (1u << 9)

static const unsigned char crc_table[256] = {
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

static int g_verbose;

static void logx(const char *fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	fprintf(stderr, "bbd-host: ");
	vfprintf(stderr, fmt, ap);
	fprintf(stderr, "\n");
	va_end(ap);
	fflush(stderr);
}

static uint64_t now_ms(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

/* ---------------- TL encode ---------------- */
struct txbuf {
	uint8_t b[70000];
	size_t n;
};

static void put_raw(struct txbuf *t, uint8_t v) { t->b[t->n++] = v; }

static void put_esc(struct txbuf *t, uint8_t v)
{
	switch (v) {
	case ESC:  put_raw(t, ESC); put_raw(t, ESC_ESC);  break;
	case XON:  put_raw(t, ESC); put_raw(t, ESC_XON);  break;
	case XOFF: put_raw(t, ESC); put_raw(t, ESC_XOFF); break;
	default:   put_raw(t, v); break;
	}
}

/*
 * One TL packet carrying a single RPC chunk or an ack.  Layout (reference
 * implementation, verified by the CRC rule at bbd_rpc_lh.c:371):
 *   seqId | size | flags | [flag details] | payload | crc
 * CRC covers bytes [1 .. len-2) with a nibble swap, which trivially includes
 * the flag details, matching "compute CRC after parsing details".
 */
static void tl_build_packet(struct txbuf *t, uint8_t seq, uint16_t flags,
			    uint8_t ack_detail, uint8_t nack_detail,
			    const uint8_t *payload, size_t plen,
			    bool reliable, uint8_t rel_seq)
{
	uint8_t body[65500];
	size_t bn = 0;
	uint16_t f = flags;
	uint8_t hdr[40];
	size_t hn = 0;
	uint8_t crc = 0;
	size_t i;

	/* details travel inside the "payload size" (reference decoder: the
	 * size must equal everything after the flags field). */
	uint16_t dlen = plen;
	if (reliable) f |= FLAG_RELIABLE_PACKET;
	if (f & FLAG_PACKET_ACK) dlen += 1;
	if (f & FLAG_RELIABLE_PACKET) dlen += 1;
	if (f & FLAG_RELIABLE_NACK) dlen += 1;
	if (dlen > 0xFF) f |= FLAG_SIZE_EXTENDED;
	if (f & ~0xFFu) f |= FLAG_EXTENDED;
	if (f & FLAG_SIZE_EXTENDED) dlen += 1;
	if (f & FLAG_EXTENDED) dlen += 1;

	hdr[hn++] = seq;
	hdr[hn++] = (uint8_t)(dlen & 0xFF);
	hdr[hn++] = (uint8_t)(f & 0xFF);
	if (f & FLAG_PACKET_ACK)  hdr[hn++] = ack_detail;
	if (f & FLAG_RELIABLE_PACKET) hdr[hn++] = rel_seq;
	if (f & FLAG_RELIABLE_NACK)   hdr[hn++] = nack_detail;
	if (f & FLAG_SIZE_EXTENDED)   hdr[hn++] = (uint8_t)(dlen >> 8);
	if (f & FLAG_EXTENDED)        hdr[hn++] = (uint8_t)(f >> 8);

	memcpy(body + bn, hdr, hn); bn += hn;
	if (payload && plen) { memcpy(body + bn, payload, plen); bn += plen; }

	crc = 0;
	for (i = 1; i < bn; i++) crc = crc_table[crc ^ body[i]];
	crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));

	put_raw(t, ESC);
	put_raw(t, 0x00);          /* SOP is not escaped in the bitstream */
	for (i = 0; i < bn; i++) put_esc(t, body[i]);
	put_esc(t, crc);
	put_raw(t, ESC);
	put_raw(t, EOP);
}

/* rpc chunk: [id][len16 LE][payload] */
static size_t rpc_wrap(uint8_t *out, uint8_t id, const uint8_t *p, size_t n)
{
	out[0] = id;
	out[1] = (uint8_t)(n & 0xFF);
	out[2] = (uint8_t)(n >> 8);
	if (n) memcpy(out + 3, p, n);
	return n + 3;
}

/* ---------------- TL decode ---------------- */
enum { WAIT_ESC = 0, WAIT_SOP, IN_MSG, WAIT_EOP };

struct rxstate {
	int state;
	uint8_t msg[70000];
	size_t mlen;
	uint8_t esc[70000];
	size_t esclen;
	uint8_t last_seq;
	int packets;
	int crc_errors;
	int rpc_seen[64];
	uint64_t garbage;
};

static void hexdump(const char *tag, const uint8_t *p, size_t n)
{
	size_t i;
	if (!g_verbose && !getenv("BBD_DEBUG")) return;
	fprintf(stderr, "  %s (%zu):", tag, n);
	for (i = 0; i < n && i < 96; i++) fprintf(stderr, " %02x", p[i]);
	if (n > 96) fprintf(stderr, " ...");
	fprintf(stderr, "\n");
}

static void rx_rpc(struct rxstate *r, uint8_t *p, size_t n)
{
	while (n > 0) {
		uint16_t id, len;
		size_t need;
		if (n < 3) { r->garbage++; return; }
		id = p[0];
		if (id & 0x80) { /* two-byte id */
			if (n < 4) { r->garbage++; return; }
			id = (uint16_t)(((id & 0x7f) << 8) | p[1]);
			len = p[2];
			if (len & 0x80) { if (n < 5) { r->garbage++; return; }
				len = (uint16_t)(((len & 0x7f) << 8) | p[3]); p += 1; n -= 1; }
			need = 2 + 3 + len;
		} else {
			len = p[1];
			if (len & 0x80) { if (n < 4) { r->garbage++; return; }
				len = (uint16_t)(((len & 0x7f) << 8) | p[2]); p += 1; n -= 1; }
			need = 3 + len;
		}
		if (need > n) { r->garbage++; return; }
		if (id < 64) r->rpc_seen[id]++;
		if (id == RPC_SENSOR_RESPONSE) {
			/* [u16 size][ssp packet] */
			if (len >= 2) {
				uint16_t sz = (uint16_t)(p[1] | (p[2] << 8));
				logx("MCU->AP SSP packet len=%u %s", sz, "");
				hexdump("pkt", p + 3, sz <= len - 2 ? sz : len - 2);
				/* Hand the exact ssp packet to the kernel. */
				if (sz > 0) {
					int fd = open(BBD_SENSOR, O_WRONLY | O_NONBLOCK);
					if (fd >= 0) {
						ssize_t w = write(fd, p + 3, sz);
						if (w < 0) logx("kernel write failed: %s", strerror(errno));
						close(fd);
					}
				}
			}
		} else if (id == RPC_SENSOR_REQUEST) {
			/* The kernel asks us to carry an SSP packet to the hub. */
			if (g_verbose) { logx("RPC request len=%u", len); hexdump("req", p + 1, len); }
		} else {
			logx("RPC id=%u len=%u", id, len);
			hexdump("rpc", p + 1, len);
		}
		p += need;
		n -= need;
	}
}

static void rx_finish(struct rxstate *r)
{
	size_t i, off;
	uint8_t crc = 0, want;
	uint16_t flags, psz;
	int bit;

	if (r->mlen < 4) { r->garbage++; return; }
	for (i = 1; i < r->mlen - 1; i++) crc = crc_table[crc ^ r->msg[i]];
	crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
	want = r->msg[r->mlen - 1];
	if (crc != want) {
		r->crc_errors++;
		fprintf(stderr, "  TL CRC error (got %02x want %02x)\n", crc, want);
		if (g_verbose || getenv("BBD_DEBUG")) hexdump("crcfail", r->msg, r->mlen);
		return;
	}
	flags = r->msg[2];
	psz = r->msg[1];
	off = 3;
	for (bit = 0; bit < 16; bit++) {
		uint16_t b = (uint16_t)(1u << bit);
		uint8_t d;
		if (!(flags & b)) continue;
		if (off >= r->mlen - 1) break;
		d = r->msg[off++];
		if (b == FLAG_SIZE_EXTENDED) psz |= (uint16_t)(d << 8);
		else if (b == FLAG_EXTENDED) flags |= (uint16_t)(d << 8);
	}
	r->packets++;
	r->last_seq = r->msg[0];
	fprintf(stderr, "  TL packet seq=%u flags=0x%03x payload=%u%s\n",
		r->msg[0], flags, psz,
		(flags & FLAG_RELIABLE_PACKET) ? " RELIABLE" : "");
	if (off + psz <= r->mlen - 1) {
		if (g_verbose) hexdump("raw", r->msg, r->mlen);
		rx_rpc(r, r->msg + off, psz);
	} else {
		r->garbage++;
	}
}

static void rx_byte(struct rxstate *r, uint8_t c)
{
	if (c == XON || c == XOFF) return;
	if (r->esclen < sizeof(r->esc)) r->esc[r->esclen++] = c;

	switch (r->state) {
	case WAIT_ESC:
		if (c == ESC) { r->state = WAIT_SOP; r->garbage += (r->esclen > 1) ? r->esclen - 1 : 0; r->esclen = 1; }
		break;
	case WAIT_SOP:
		if (c == 0x00) { r->state = IN_MSG; r->mlen = 0; }
		else if (c != ESC) r->state = WAIT_ESC;
		else { r->garbage += 2; r->esclen = 1; }
		break;
	case IN_MSG:
		if (c == ESC) r->state = WAIT_EOP;
		else if (r->mlen < sizeof(r->msg)) r->msg[r->mlen++] = c;
		else r->state = WAIT_ESC;
		break;
	case WAIT_EOP: {
		bool done = false;
		if (c == EOP) { done = true; r->state = WAIT_ESC; }
		else if (c == ESC_ESC)  { r->msg[r->mlen++] = ESC;  r->state = IN_MSG; }
		else if (c == ESC_XON)  { r->msg[r->mlen++] = XON;  r->state = IN_MSG; }
		else if (c == ESC_XOFF) { r->msg[r->mlen++] = XOFF; r->state = IN_MSG; }
		else if (c == 0x00)     { r->state = WAIT_SOP; r->mlen = 0; }
		else                     r->state = WAIT_ESC;
		r->esclen = 0;
		if (done) { rx_finish(r); r->mlen = 0; }
		break;
	}
	default:
		r->state = WAIT_ESC;
	}
}

/* Probe the hub: write a TL hello request on ttyBCM and listen for any TL
 * packet.  Nothing is invented: a silent hub yields packets=0. */
static int probe(int ms)
{
	struct rxstate r;
	struct txbuf t = {0};
	struct txbuf empty = {0};
	int tf, i;
	uint64_t end;
	uint8_t hello[64] = {0};
	size_t hn = 0;

	(void)empty;
	memset(&r, 0, sizeof r);
	r.state = WAIT_ESC;
	tf = open(TTY_BCM, O_RDWR | O_NONBLOCK);
	if (tf < 0) { logx("open %s: %s", TTY_BCM, strerror(errno)); return 1; }

	/* LHD-style hello: an empty reliable packet with IGNORE_SEQID. */
	tl_build_packet(&t, 0, FLAG_IGNORE_SEQID, 0, 0, hello, hn, false, 0);
	if (write(tf, t.b, t.n) < 0) logx("write hello: %s", strerror(errno));
	else logx("hello sent (%zu bytes)", t.n);

	end = now_ms() + (uint64_t)ms;
	while (now_ms() < end) {
		struct pollfd p = { .fd = tf, .events = POLLIN };
		int pr = poll(&p, 1, 50);
		if (pr > 0 && (p.revents & POLLIN)) {
			uint8_t buf[4096];
			ssize_t n = read(tf, buf, sizeof buf);
			if (n > 0) { if (g_verbose) hexdump("spi-rx", buf, (size_t)n);
				for (i = 0; i < n; i++) rx_byte(&r, buf[i]); }
		}
	}
	close(tf);
	printf("probe: packets=%d crc_errors=%d garbage=%llu rpc_response=%d\n",
	       r.packets, r.crc_errors, (unsigned long long)r.garbage,
	       r.rpc_seen[RPC_SENSOR_RESPONSE]);
	return r.packets > 0 ? 0 : 1;
}

int main(int argc, char **argv)
{
	int i;
	if (argc < 2) {
		fprintf(stderr, "usage: %s --selftest | --probe [--ms N] [--verbose] | --send-hex HEX\n", argv[0]);
		return 2;
	}
	for (i = 1; i < argc; i++)
		if (!strcmp(argv[i], "--verbose")) g_verbose = 1;

	if (!strcmp(argv[1], "--selftest")) {
		struct txbuf t = {0};
		struct rxstate r;
		uint8_t chunk[300];
		size_t cn;
		memset(&r, 0, sizeof r);
		r.state = WAIT_ESC;
		cn = rpc_wrap(chunk, RPC_SENSOR_REQUEST, (const uint8_t *)"hello", 5);
		tl_build_packet(&t, 1, 0, 0, 0, chunk, cn, false, 0);
		if (g_verbose) hexdump("tl", t.b, t.n);
		for (i = 0; i < (int)t.n; i++) rx_byte(&r, t.b[i]);
		/* Feed the packet back and verify CRC + RPC id 34 was seen. */
		printf("selftest: encoded %zu bytes, decoded packets=%d crc_errors=%d rpc34=%d\n",
		       t.n, r.packets, r.crc_errors, r.rpc_seen[RPC_SENSOR_REQUEST]);
		return (r.packets == 1 && r.crc_errors == 0) ? 0 : 1;
	}
	if (!strcmp(argv[1], "--probe")) {
		int ms = 1500;
		for (i = 2; i < argc; i++) {
			if (!strcmp(argv[i], "--ms") && i + 1 < argc) ms = atoi(argv[++i]);
		}
		return probe(ms);
	}
	return 2;
}
