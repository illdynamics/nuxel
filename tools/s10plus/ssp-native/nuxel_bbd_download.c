/*
 * nuxel_bbd_download — native sensor-hub firmware downloader for Nuxel.
 *
 * Offline framing diagnostics and explicitly gated version-query observations.
 * The matched stock lhd now runs in hardware-denied isolation. This utility
 * is NOT a verified firmware downloader. Transport ACKs are not RPC completion.
 * See reports/SSP-PROTOCOL-CONTRACT-2026-11-17.md for evidence and open gaps.
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

#define BBD_SENSOR  "/dev/bbd_sensor"
#define BBD_PATCH   "/dev/bbd_patch"
#define TTY_BCM     "/dev/ttyBCM"
#define PATCH_READ_LIMIT (2u << 20)

#define ESC 0xB0
#define ESC_ESC 0x03
#define ESC_XON 0x04
#define ESC_XOFF 0x05
#define XON 0x11
#define XOFF 0x13
#define EOP 0x01

#define F_ACK       (1u<<0)
#define F_RELIABLE  (1u<<1)
#define F_REL_ACK   (1u<<2)
#define F_REL_NACK  (1u<<3)
#define F_SIZE_EXT  (1u<<6)
#define F_EXT       (1u<<7)
#define F_INTERNAL  (1u<<8)
#define F_IGN_SEQ   (1u<<9)

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

static int g_verbose;
static void logx(const char *fmt, ...)
{
	va_list ap; va_start(ap, fmt);
	fprintf(stderr, "bbd-dl: "); vfprintf(stderr, fmt, ap); fputc('\n', stderr);
	va_end(ap); fflush(stderr);
}
static uint64_t now_ms(void)
{
	struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec*1000u + (uint64_t)ts.tv_nsec/1000000u;
}

/* Used only to fingerprint decoded content.  The vendor text field named
 * "Crc" is not documented as IEEE CRC-32 and must not be treated as one. */
static uint32_t crc32_ieee(const uint8_t *p, size_t n)
{
	uint32_t crc = 0xffffffffu;
	while (n--) {
		unsigned int bit;
		crc ^= *p++;
		for (bit = 0; bit < 8; bit++)
			crc = (crc >> 1) ^ (0xedb88320u & -(int32_t)(crc & 1));
	}
	return ~crc;
}
/* ---------- TL transmit ---------- */
struct tx { uint8_t b[1<<17]; size_t n; };
static void put_raw(struct tx *t, uint8_t v) { t->b[t->n++] = v; }
static void put_esc(struct tx *t, uint8_t v)
{
	switch (v) {
	case ESC:  put_raw(t, ESC); put_raw(t, ESC_ESC); break;
	case XON:  put_raw(t, ESC); put_raw(t, ESC_XON); break;
	case XOFF: put_raw(t, ESC); put_raw(t, ESC_XOFF); break;
	default:   put_raw(t, v); break;
	}
}

/*
 * Build a TL packet.  Layout (from lhd TransportLayer::BuildAndSendPacket and
 * the kernel's reference decoder):
 *   seqId | size | flags | [details in bit order] | payload | crc
 * `size` counts only payload bytes (bbd_rpc_lh.c:472).
 */
static void tl_packet(struct tx *t, uint8_t seq, uint16_t flags,
		      const uint8_t *details, size_t ndet,
		      const uint8_t *payload, size_t plen)
{
	uint8_t body[1<<16];
	size_t bn = 0, i, di = 0;
	uint16_t size = (uint16_t)plen;
	t->n = 0;
	if (plen > 2048) { t->n = 0; return; }
	uint8_t crc = 0;

	if (size > 0xFF) flags |= F_SIZE_EXT;
	if (flags & ~0xFFu) flags |= F_EXT;

	body[bn++] = seq;
	body[bn++] = (uint8_t)(size & 0xFF);
	body[bn++] = (uint8_t)(flags & 0xFF);
	/* Caller supplies details for non-extension flags, in bit order. */
	for (i = 0; i < 10; i++) {
		uint16_t bit = (uint16_t)(1u << i);
		if (!(flags & bit)) continue;
		if (bit == F_SIZE_EXT) body[bn++] = (uint8_t)(size >> 8);
		else if (bit == F_EXT) body[bn++] = (uint8_t)(flags >> 8);
		else {
			if (di >= ndet) { t->n = 0; return; }
			body[bn++] = details[di++];
		}
	}
	if (di != ndet || flags & ~0x3ffu || plen > sizeof(body) - bn) { t->n = 0; return; }
	if (plen) { memcpy(body + bn, payload, plen); bn += plen; }

	for (i = 1; i < bn; i++) crc = crc_tbl[crc ^ body[i]];
	crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));

	put_raw(t, ESC); put_raw(t, 0x00);
	for (i = 0; i < bn; i++) put_esc(t, body[i]);
	put_esc(t, crc);
	put_raw(t, ESC); put_raw(t, EOP);
}

/* RPC field encoding: 7-bit continuation with high bit marking an extra byte */
static size_t rpc_u16(uint8_t *o, uint16_t v)
{
	if (v >= 0x80) { o[0] = (uint8_t)((v >> 8) | 0x80); o[1] = (uint8_t)v; return 2; }
	o[0] = (uint8_t)v; return 1;
}
struct rpcmsg { uint8_t b[1<<16]; size_t n; };
/* add one RPC: id (u16-encoded), then payload already encoded */
static void rpc_add(struct rpcmsg *m, uint16_t id, const uint8_t *payload, size_t plen)
{
	size_t n;
	n = rpc_u16(m->b + m->n, id); m->n += n;
	n = rpc_u16(m->b + m->n, (uint16_t)plen); m->n += n;
	if (plen) { memcpy(m->b + m->n, payload, plen); m->n += plen; }
}

/* ---------- TL receive ---------- */
struct rx {
	int state; uint8_t msg[1<<17]; size_t mlen;
	uint8_t last_seq; int packets; int crc_err; int malformed;
	uint16_t flags; uint8_t details[10];
	uint8_t rpc[64][256]; uint16_t rpclen[64]; int nrpc; int rpc_seen[64];
	uint16_t last_rpcid[256]; int nevents;
};
static bool rpc_valid(const uint8_t *p, size_t n)
{
	size_t i = 0;
	while (i < n) {
		uint16_t len;
		if (p[i++] & 0x80) { if (i == n) return false; i++; }
		if (i == n) return false;
		len = p[i++];
		if (len & 0x80) {
			if (i == n) return false;
			len = (uint16_t)(((len & 0x7f) << 8) | p[i++]);
		}
		if (len > n - i) return false;
		i += len;
	}
	return true;
}

static void rx_rpc_payload(struct rx *r, const uint8_t *p, size_t n)
{
	size_t i = 0;
	while (i < n) {
		uint16_t id, len;
		if (i >= n) break;
		id = p[i++];
		if (id & 0x80) { if (i >= n) break; id = (uint16_t)(((id & 0x7f) << 8) | p[i++]); }
		if (i >= n) break;
		len = p[i++];
		if (len & 0x80) { if (i >= n) break; len = (uint16_t)(((len & 0x7f) << 8) | p[i++]); }
		if (i + len > n) { logx("rpc overflow id=%u len=%u", id, len); return; }
		if (id < 64) r->rpc_seen[id]++;
		if (r->nevents < 256) {
			r->last_rpcid[r->nevents] = id;
			r->nevents++;
		}
		if (g_verbose) {
			size_t k;
			fprintf(stderr, "  rpc id=0x%02x len=%u:", id, len);
			for (k = 0; k < len && k < 32; k++) fprintf(stderr, " %02x", p[i + k]);
			fprintf(stderr, "\n");
		}
		i += len;
	}
}
static void rx_finish(struct rx *r)
{
	size_t i, off;
	uint8_t crc = 0, want;
	uint16_t flags, size;
	uint8_t details[10] = {0};
	int bit;

	if (r->mlen < 4) { r->malformed++; return; }
	for (i = 1; i < r->mlen - 1; i++) crc = crc_tbl[crc ^ r->msg[i]];
	crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
	want = r->msg[r->mlen - 1];
	if (crc != want) { r->crc_err++; printf("  TL CRC error %02x!=%02x\n", crc, want); return; }
	flags = r->msg[2];
	size = r->msg[1];
	off = 3;
	for (bit = 0; bit < 16; bit++) {
		uint16_t b = (uint16_t)(1u << bit);
		uint8_t d;
		if (!(flags & b)) continue;
		if (bit >= 10 || off >= r->mlen - 1) { r->malformed++; return; }
		d = r->msg[off++];
		details[bit] = d;
		if (b == F_SIZE_EXT) size |= (uint16_t)(d << 8);
		else if (b == F_EXT) flags |= (uint16_t)(d << 8);
	}
	if (size > 2048 || size != r->mlen - 1 - off) { r->malformed++; return; }
	if (!(flags & F_INTERNAL) && !rpc_valid(r->msg + off, size)) {
		r->malformed++; return;
	}
	memcpy(r->details, details, sizeof(details));
	r->flags = flags;
	r->packets++; r->last_seq = r->msg[0];
	printf("  TL seq=%u flags=0x%03x size=%u%s\n", r->msg[0], flags, size,
	       (flags & F_RELIABLE) ? " REL" : "");
	if (!(flags & F_INTERNAL)) rx_rpc_payload(r, r->msg + off, size);
}
static void rx_feed(struct rx *r, const uint8_t *p, size_t n)
{
	size_t i;
	for (i = 0; i < n; i++) {
		uint8_t c = p[i];
		if (c == XON || c == XOFF) continue;
		switch (r->state) {
		case 0:
			if (c == ESC) r->state = 1;
			break;
		case 1:
			if (c == 0x00) { r->state = 2; r->mlen = 0; }
			else if (c != ESC) r->state = 0;
			break;
		case 2:
			if (c == ESC) r->state = 3;
			else if (r->mlen < sizeof(r->msg)) r->msg[r->mlen++] = c;
			else { r->state = 0; r->mlen = 0; r->malformed++; }
			break;
		case 3:
			if (r->mlen >= sizeof(r->msg)) { r->state = 0; r->mlen = 0; r->malformed++; break; }
			if (c == EOP) { r->state = 0; rx_finish(r); r->mlen = 0; }
			else if (c == ESC_ESC) { r->msg[r->mlen++] = ESC; r->state = 2; }
			else if (c == ESC_XON) { r->msg[r->mlen++] = XON; r->state = 2; }
			else if (c == ESC_XOFF) { r->msg[r->mlen++] = XOFF; r->state = 2; }
			else if (c == 0x00) { r->state = 2; r->mlen = 0; }
			else r->state = 0;
			break;
		}
	}
}

/* ---------- channel ---------- */
struct chan {
	int tf;       /* ttyBCM */
	int sf;       /* bbd_sensor: kernel->peer frames, peer->kernel replies */
	struct rx rx;
	uint8_t seq;
	int kernel_frames;
	uint8_t kbuf[4096];
	size_t klen;
};

static int write_all(int fd, const uint8_t *p, size_t n)
{
	size_t done = 0;
	uint64_t end = now_ms() + 1000; /* host safety limit, not vendor timeout */
	while (done < n) {
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

/* Read whatever the hub has sent within `ms`, keeping kernel frames drained. */
static void pump(struct chan *c, int ms, int stop_on_reply)
{
	uint64_t end = now_ms() + (uint64_t)ms;
	int before = c->rx.packets;
	while (now_ms() < end) {
		struct pollfd p[2];
		int n = 0, i;
		int idx_tty = -1, idx_sen = -1;
		if (c->tf >= 0) { p[n].fd = c->tf; p[n].events = POLLIN; idx_tty = n++; }
		if (c->sf >= 0) { p[n].fd = c->sf; p[n].events = POLLIN; idx_sen = n++; }
		if (!n) return;
		if (poll(p, n, 50) <= 0) continue;
		for (i = 0; i < n; i++) {
			if (!(p[i].revents & POLLIN)) continue;
			if (i == idx_tty) {
				uint8_t buf[8192];
				ssize_t r = read(c->tf, buf, sizeof buf);
				if (r > 0) {
					if (g_verbose) {
						ssize_t k; fprintf(stderr, "  spi-rx(%zd):", r);
						for (k = 0; k < r && k < 48; k++) fprintf(stderr, " %02x", buf[k]);
						fprintf(stderr, "\n");
					}
					rx_feed(&c->rx, buf, (size_t)r);
				}
			} else if (i == idx_sen) {
				ssize_t r = read(c->sf, c->kbuf + c->klen, sizeof(c->kbuf) - c->klen);
				if (r > 0) {
					c->klen += (size_t)r;
					while (c->klen >= 2) {
						uint16_t sz = (uint16_t)(c->kbuf[0] | (c->kbuf[1] << 8));
						if (c->klen < (size_t)sz + 2) break;
						c->kernel_frames++;
						if (g_verbose) {
							size_t k; fprintf(stderr, "  K->M(%u):", sz);
							for (k = 2; k < (size_t)sz + 2 && k < 40; k++) fprintf(stderr, " %02x", c->kbuf[k]);
							fprintf(stderr, "\n");
						}
						memmove(c->kbuf, c->kbuf + sz + 2, c->klen - sz - 2);
						c->klen -= sz + 2;
					}
				}
			}
		}
		if (stop_on_reply && c->rx.packets > before) return;
	}
}

static int chan_open(struct chan *c)
{
	c->tf = open(TTY_BCM, O_RDWR | O_NONBLOCK);
	if (c->tf < 0) { logx("open %s: %s", TTY_BCM, strerror(errno)); return -1; }
	c->sf = open(BBD_SENSOR, O_RDWR | O_NONBLOCK);
	if (c->sf < 0) { logx("open %s: %s", BBD_SENSOR, strerror(errno)); return -1; }
	return 0;
}
static void chan_close(struct chan *c)
{
	if (c->tf >= 0) close(c->tf);
	if (c->sf >= 0) close(c->sf);
	c->tf = c->sf = -1;
}

/* Observe traffic for a bounded window. No verified RPC completion matcher exists. */
static int transact(struct chan *c, const struct rpcmsg *m, int wait_ms, const char *what)
{
	struct tx t = {0};
	tl_packet(&t, c->seq++, 0, NULL, 0, m->b, m->n);
	logx("-> %s (%zu rpc bytes, %zu TL bytes)", what, m->n, t.n);
	if (write_all(c->tf, t.b, t.n) < 0) { logx("write: %s", strerror(errno)); return -1; }
	/* keep the kernel side moving while the hub answers */
	pump(c, wait_ms, 0);
	logx("%s: completion UNVERIFIED (transport activity is not an RPC ACK)", what);
	return 0;
}

/* ---------- actions ---------- */
static int rpc_get_version(struct chan *c)
{
	struct rpcmsg m = {0};
	uint8_t none[1] = {0};
	rpc_add(&m, 0x00, none, 0);
	return transact(c, &m, 1500, "GetVersion");
}
static int rpc_get_version_ext(struct chan *c)
{
	struct rpcmsg m = {0};
	uint8_t none[1] = {0};
	rpc_add(&m, 0x3a, none, 0);
	return transact(c, &m, 1500, "GetVersionExt");
}
static int load_patch_path(const char *path, uint8_t **out, size_t *len)
{
	int fd = open(path, O_RDONLY);
	uint8_t *b; size_t cap = 1 << 20, n = 0; ssize_t r;
	if (fd < 0) { logx("open %s: %s", path, strerror(errno)); return -1; }
	b = malloc(cap);
	if (!b) { close(fd); logx("malloc patch buffer"); return -1; }
	for (;;) {
		uint8_t *nb;
		if (n == cap) {
			if (cap >= PATCH_READ_LIMIT) { logx("patch exceeds %u-byte safety limit", PATCH_READ_LIMIT); free(b); close(fd); return -1; }
			cap *= 2;
			nb = realloc(b, cap);
			if (!nb) { free(b); close(fd); logx("realloc patch buffer"); return -1; }
			b = nb;
		}
		r = read(fd, b + n, cap - n);
		if (r < 0) { if (errno == EINTR) continue; free(b); close(fd); logx("read %s: %s", path, strerror(errno)); return -1; }
		if (r == 0) break;
		/* bbd_patch_read() rewinds at EOF.  Its next read begins with the
		 * original prefix; do not append it indefinitely. */
		if (n && r >= 32 && !memcmp(b + n, b, 32)) break;
		n += (size_t)r;
	}
	close(fd);
	*out = b; *len = n;
	return 0;
}

static int load_patch(uint8_t **out, size_t *len)
{
	return load_patch_path(BBD_PATCH, out, len);
}

static int parse_hex_hdr(const uint8_t *b, size_t n, const char *key, uint32_t *val, unsigned long *ulong)
{
	char pat[64], *p;
	size_t kl = strlen(key);
	if (kl + 3 > sizeof pat) return -1;
	pat[0] = '<'; memcpy(pat + 1, key, kl); pat[1 + kl] = '='; pat[2 + kl] = 0;
	p = memmem(b, n, pat, kl + 2);
	if (!p) return -1;
	{
		const char *v = p + kl + 2;
		char *endp;
		unsigned long long x = strtoull(v, &endp, 0);
		if (endp == v) return -1;
		if (val) *val = (uint32_t)x;
		if (ulong) *ulong = (unsigned long)x;
	}
	return 0;
}

/* Decode the <Blob=...> hex section into binary. */
static uint8_t *patch_blob(const uint8_t *hdr, size_t hn, size_t *blob_len)
{
	const char *p = memmem(hdr, hn, "<Blob=", 6);
	const char *end = p ? memmem(p, hn - (size_t)(p - (const char *)hdr), ">\n", 2) : NULL;
	size_t cap, n = 0;
	uint8_t *out;
	if (!p || !end || end <= p) return NULL;
	p += 6;
	cap = (size_t)(end - p) / 2 + 1;
	out = malloc(cap);
	while (p + 1 < end) {
		int hi = -1, lo = -1;
		while (p < end && !((*p >= '0' && *p <= '9') || (*p >= 'A' && *p <= 'F'))) p++;
		if (p >= end) break;
		hi = (*p <= '9') ? *p - '0' : *p - 'A' + 10; p++;
		while (p < end && !((*p >= '0' && *p <= '9') || (*p >= 'A' && *p <= 'F'))) p++;
		if (p >= end) break;
		lo = (*p <= '9') ? *p - '0' : *p - 'A' + 10; p++;
		out[n++] = (uint8_t)((hi << 4) | lo);
	}
	*blob_len = n;
	return out;
}

static int validate_patch(const uint8_t *patch, size_t plen, uint8_t **blob_out,
			  size_t *blen_out, uint32_t *address_out)
{
	uint8_t *blob;
	size_t blen = 0;
	uint32_t asic = 0, declared_len = 0, address = 0;
	unsigned long declared_crc = 0;

	if (parse_hex_hdr(patch, plen, "AsicVersion", &asic, NULL) ||
	    parse_hex_hdr(patch, plen, "BlobLength", &declared_len, NULL) ||
	    parse_hex_hdr(patch, plen, "PatchAddress", &address, NULL) ||
	    parse_hex_hdr(patch, plen, "Crc", NULL, &declared_crc)) {
		logx("patch header missing a mandatory field");
		return -1;
	}
	blob = patch_blob(patch, plen, &blen);
	if (!blob || !blen || blen != declared_len) {
		logx("patch blob length invalid (declared=%u decoded=%zu)", declared_len, blen);
		free(blob);
		return -1;
	}
	printf("patch: input=%zu B asic=0x%08x blobLength=%u patchAddr=0x%08x headerCrc=0x%08lx contentCrc32=0x%08x\n",
	       plen, asic, declared_len, address, declared_crc, crc32_ieee(blob, blen));
	*blob_out = blob;
	*blen_out = blen;
	*address_out = address;
	return 0;
}

int main(int argc, char **argv)
{
	struct chan c;
	uint8_t *patch = NULL, *blob = NULL;
	size_t plen = 0, blen = 0;
	uint32_t patchaddr = 0;
	const char *mode = NULL;
	const char *verify_path = NULL;
	bool live = false;
	int i;
	int replied = 0;

	if (argc == 2 && !strcmp(argv[1], "--replay-stdin")) {
		struct rx replay = {0};
		uint8_t buf[4096]; size_t n;
		while ((n = fread(buf, 1, sizeof(buf), stdin)) != 0) rx_feed(&replay, buf, n);
		printf("OFFLINE REPLAY: packets=%d crc_err=%d malformed=%d incomplete=%d; hardware_verified=false\n",
		       replay.packets, replay.crc_err, replay.malformed, replay.state != 0);
		return ferror(stdin) || replay.crc_err || replay.malformed || replay.state ? 2 : 0;
	}

	for (i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--verbose")) g_verbose = 1;
		else if (!strcmp(argv[i], "--live")) live = true;
		else if (!strcmp(argv[i], "--download")) mode = "download";
		else if (!strcmp(argv[i], "--query")) mode = "query";
		else if (!strcmp(argv[i], "--verify-patch") && i + 1 < argc) verify_path = argv[++i];
		else { fprintf(stderr, "usage: %s --replay-stdin | --verify-patch PATH | --live --query [--verbose]\\n", argv[0]); return 64; }
	}
	if ((!verify_path && !mode) || (verify_path && mode) || (mode && !live)) {
		fprintf(stderr, "refusing device I/O: use --verify-patch PATH, or explicitly --live --query\\n");
		return 64;
	}
	if (mode && !strcmp(mode, "download")) {
		fprintf(stderr, "refusing unvalidated firmware download: no source-verified command/ACK state machine is available\\n");
		return 64;
	}
	memset(&c, 0, sizeof c); c.tf = c.sf = -1; c.rx.state = 0;
	c.seq = 1;

	if (verify_path ? load_patch_path(verify_path, &patch, &plen) : load_patch(&patch, &plen)) return 1;
	if (validate_patch(patch, plen, &blob, &blen, &patchaddr)) { free(patch); return 1; }
	if (verify_path) { free(blob); free(patch); return 0; }

	if (chan_open(&c) < 0) return 1;
	/* The kernel queues its own frames; drain them so they do not confuse us. */
	pump(&c, 250, 0);
	printf("kernel peer attached; drained %d kernel frames\n", c.kernel_frames);

	if (strcmp(mode, "query") == 0) {
		replied = rpc_get_version(&c);
		if (replied <= 0) replied = rpc_get_version_ext(&c);
		printf("RESULT query: %s (packets=%d crc_err=%d)\n",
		       "COMPLETION UNVERIFIED", c.rx.packets, c.rx.crc_err);
		printf("  rpc seen: 0x00=%d 0x01=%d 0x02=%d 0x1f=%d 0x3b=%d\n",
		       c.rx.rpc_seen[0], c.rx.rpc_seen[1], c.rx.rpc_seen[2],
		       c.rx.rpc_seen[0x1f], c.rx.rpc_seen[0x3b]);
		chan_close(&c);
		free(blob); free(patch);
		return 2; /* No verified operation response contract. */
	}

	chan_close(&c);
	return 2;
}
