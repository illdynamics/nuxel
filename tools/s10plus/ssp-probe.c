/*
 * ssp-probe — native Linux bring-up/diagnostic client for the Samsung
 * Broadcom BBD/SSP sensor-hub transport on the Galaxy S10+ (beyond2lte).
 *
 * There is NO Android dependency here.  It speaks the in-kernel ABI the SSD
 * vendor tools use:
 *
 *   /dev/bbd_sensor   binary stream: sensor packets the kernel wants sent to
 *                     the MCU (u16 LE length + payload) come out of a read();
 *                     payloads received from the MCU are written back in.
 *   /dev/bbd_patch    signed sensor-hub patch image, read() to EOF.  The
 *                     kernel serves it; this tool hashes it and records it.
 *   /dev/bbd_control  text control channel ("ESW:READY", "ESW:NOTREADY",
 *                     "BBD:DEBUG=1", "SSP:DEBUG=1", "SSI:PassThru=1", ...).
 *
 * Commands:
 *   --info                       print ABI/version facts and exit
 *   --dump-patch FILE            read /dev/bbd_patch to FILE, print sha256
 *   --bringup [--prefix DIR] [--duration MS] [--control STR]...
 *                                open bbd_sensor, read kernel->MCU frames, log
 *                                them (hex), answer nothing by default, and
 *                                optionally push control strings in order.
 *   --listen MS                  read-only: just log frames for MS ms
 *
 * Exit codes: 0 ok, 1 device/ABI error, 2 usage.  Never writes any partition.
 *
 * Build (Fedora aarch64): gcc -O2 -Wall -o ssp-probe ssp-probe.c
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
#define BBD_CONTROL "/dev/bbd_control"
#define MAX_FRAME   1024

static uint64_t now_ms(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}

/* Minimal SHA-256 (no OpenSSL/libcrypto dependency on the phone). */
struct sha256 { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; };
static const uint32_t K[64] = {
	0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
	0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
	0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
	0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
	0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
	0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
	0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
	0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2 };
#define ROR(x,n) (((x)>>(n))|((x)<<(32-(n))))
static void sha_block(struct sha256 *s, const uint8_t *p)
{
	uint32_t w[64], a,b,c,d,e,f,g,h,t1,t2; int i;
	for (i=0;i<16;i++) w[i]=(uint32_t)p[4*i]<<24|(uint32_t)p[4*i+1]<<16|(uint32_t)p[4*i+2]<<8|p[4*i+3];
	for (;i<64;i++){uint32_t s0=ROR(w[i-15],7)^ROR(w[i-15],18)^(w[i-15]>>3);
		uint32_t s1=ROR(w[i-2],17)^ROR(w[i-2],19)^(w[i-2]>>10); w[i]=w[i-16]+s0+w[i-7]+s1;}
	a=s->h[0];b=s->h[1];c=s->h[2];d=s->h[3];e=s->h[4];f=s->h[5];g=s->h[6];h=s->h[7];
	for(i=0;i<64;i++){t1=h+(ROR(e,6)^ROR(e,11)^ROR(e,25))+((e&f)^(~e&g))+K[i]+w[i];
		t2=(ROR(a,2)^ROR(a,13)^ROR(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
	s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
static void sha_init(struct sha256 *s)
{
	static const uint32_t iv[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
		0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
	memcpy(s->h,iv,sizeof iv); s->len=0; s->n=0;
}
static void sha_upd(struct sha256 *s, const uint8_t *p, size_t n)
{
	s->len += n;
	while (n) { size_t c = 64 - s->n; if (c > n) c = n; memcpy(s->buf+s->n,p,c); s->n+=c; p+=c; n-=c;
		if (s->n==64){ sha_block(s,s->buf); s->n=0; } }
}
static void sha_hex(struct sha256 *s, char out[65])
{
	uint64_t bits = s->len*8; uint8_t pad=0x80; int i;
	sha_upd(s,&pad,1);
	while (s->n!=56){ uint8_t z=0; sha_upd(s,&z,1); }
	for(i=7;i>=0;i--){ uint8_t b=(uint8_t)(bits>>(8*i)); sha_upd(s,&b,1); }
	for(i=0;i<8;i++) sprintf(out+8*i,"%08x",s->h[i]);
}

static int write_control(const char *str)
{
	int fd = open(BBD_CONTROL, O_WRONLY);
	ssize_t n;
	if (fd < 0) { fprintf(stderr,"open %s: %s\n",BBD_CONTROL,strerror(errno)); return -1; }
	/* The kernel uses strstr() on the buffer, so an unterminated string works;
	 * NUL-terminating matches what lhd does. */
	n = write(fd, str, strlen(str) + 1);
	if (n < 0) fprintf(stderr,"write %s: %s\n",BBD_CONTROL,strerror(errno));
	close(fd);
	return n < 0 ? -1 : 0;
}

static int cmd_dump_patch(const char *out)
{
	uint8_t buf[65536]; struct sha256 sh; char hex[65];
	int fd = open(BBD_PATCH, O_RDONLY); ssize_t n; uint64_t total = 0;
	FILE *f;
	if (fd < 0) { fprintf(stderr,"open %s: %s\n",BBD_PATCH,strerror(errno)); return 1; }
	f = out ? fopen(out,"wb") : NULL;
	if (out && !f) { fprintf(stderr,"open %s: %s\n",out,strerror(errno)); close(fd); return 1; }
	sha_init(&sh);
	while ((n = read(fd, buf, sizeof buf)) > 0) {
		sha_upd(&sh, buf, (size_t)n);
		if (f) fwrite(buf,1,(size_t)n,f);
		total += (uint64_t)n;
	}
	close(fd); if (f) fclose(f);
	sha_hex(&sh, hex);
	printf("bbd_patch bytes=%llu sha256=%s\n",(unsigned long long)total,hex);
	return total > 0 ? 0 : 1;
}

struct frame { uint16_t len; uint8_t data[MAX_FRAME]; };

static void hexdump(const char *tag, uint64_t t, const uint8_t *p, size_t n)
{
	size_t i; printf("%s t=%llums len=%zu:", tag, (unsigned long long)t, n);
	for (i = 0; i < n && i < 64; i++) printf(" %02x", p[i]);
	if (n > 64) printf(" ...");
	printf("\n"); fflush(stdout);
}

static int cmd_listen(int ms, int ctl_count, char **ctl, int follow_patch)
{
	uint8_t buf[MAX_FRAME*4]; int fd, i; uint64_t end; uint64_t t0 = now_ms();
	bool sent_ready = false;

	fd = open(BBD_SENSOR, O_RDWR);
	if (fd < 0) { fprintf(stderr,"open %s: %s\n",BBD_SENSOR,strerror(errno)); return 1; }
	if (follow_patch) cmd_dump_patch(NULL);
	end = t0 + (uint64_t)ms;
	printf("listening on %s for %d ms (t0=%llu)\n", BBD_SENSOR, ms, (unsigned long long)t0);
	system("printf 'ESW:READY' > /dev/bbd_control");
	sent_ready = true;
	(void)sent_ready;
	for (i = 0; i < ctl_count; i++) {
		printf("control: %s\n", ctl[i]);
		write_control(ctl[i]);
	}
	while (now_ms() < end) {
		struct pollfd p = { .fd = fd, .events = POLLIN };
		int pr = poll(&p, 1, 100);
		if (pr > 0 && (p.revents & POLLIN)) {
			ssize_t n = read(fd, buf, sizeof buf);
			if (n > 0) hexdump("K2M", now_ms() - t0, buf, (size_t)n);
		}
		/* Report live sensor state every second regardless of traffic. */
		if (((now_ms() - t0) % 1000) < 100) {
			char line[128]; FILE *f = fopen("/sys/class/sensors/accelerometer_sensor/raw_data","r");
			if (f) { if (fgets(line,sizeof line,f)) { printf("accel %s", line); fflush(stdout);} fclose(f);} 
		}
	}
	close(fd);
	return 0;
}

int main(int argc, char **argv)
{
	int i;
	if (argc < 2) {
		printf("usage: %s --info | --dump-patch FILE | --listen MS [--control STR]... | --bringup [--duration MS] [--control STR]...\n", argv[0]);
		return 2;
	}
	for (i = 1; i < argc; i++) {
		if (!strcmp(argv[i],"--info")) {
			printf("ssp-probe ABI=ssp_msg-packed cmd:u8 len:u16 options:u16 data:u32\n");
			printf("control=%s sensor=%s patch=%s\n",BBD_CONTROL,BBD_SENSOR,BBD_PATCH);
			return 0;
		}
		if (!strcmp(argv[i],"--dump-patch") && i+1 < argc) return cmd_dump_patch(argv[++i]);
		if ((!strcmp(argv[i],"--listen") || !strcmp(argv[i],"--bringup")) && i+1 < argc) {
			int ms = atoi(argv[++i]); char *ctl[16]; int nctl = 0; int follow = 1;
			while (i+1 < argc) {
				if (!strcmp(argv[i+1],"--control") && i+2 < argc) { ctl[nctl++] = argv[i+2]; i += 2; }
				else if (!strcmp(argv[i+1],"--no-patch")) { follow = 0; i++; }
				else break;
			}
			return cmd_listen(ms, nctl, ctl, follow);
		}
	}
	fprintf(stderr,"unknown arguments\n");
	return 2;
}
