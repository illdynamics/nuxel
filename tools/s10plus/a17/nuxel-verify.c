/* nuxel-verify — freestanding aarch64 content/ELF verifier for the Nuxel initramfs.
 *
 * A marker file must never be the proof that a deployment happened (mission
 * rule).  This tool gives /init a real, self-contained check that needs no
 * coreutils: it hashes with its own SHA-256 and inspects ELF headers itself.
 *
 *   nuxel-verify sha256 <file> [<expected-hex>]   -> prints SHA256 <hex> <file>;
 *                                                    exit 0 iff expected matches
 *   nuxel-verify elf <file> <e_machine-decimal>   -> exit 0 iff ELF64 of that machine
 *   nuxel-verify present <file> <expected-bytes>  -> exit 0 iff regular file of that size
 *
 * Exit codes: 0 ok, 1 mismatch/not satisfied, 2 usage/io error.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* ---------------------------------------------------------------- sha256 --- */
typedef struct { uint32_t h[8]; uint64_t len; unsigned char buf[64]; size_t n; } sha256_t;

static const uint32_t K[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2 };

#define ROR(x,n) (((x) >> (n)) | ((x) << (32-(n))))
static void sha256_block(sha256_t *s, const unsigned char *p) {
        uint32_t w[64], a, b, c, d, e, f, g, h; int i;
        for (i = 0; i < 16; i++)
                w[i] = (uint32_t)p[i*4]<<24 | (uint32_t)p[i*4+1]<<16 | (uint32_t)p[i*4+2]<<8 | p[i*4+3];
        for (; i < 64; i++) {
                uint32_t s0 = ROR(w[i-15],7) ^ ROR(w[i-15],18) ^ (w[i-15] >> 3);
                uint32_t s1 = ROR(w[i-2],17) ^ ROR(w[i-2],19) ^ (w[i-2] >> 10);
                w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        a=s->h[0]; b=s->h[1]; c=s->h[2]; d=s->h[3]; e=s->h[4]; f=s->h[5]; g=s->h[6]; h=s->h[7];
        for (i = 0; i < 64; i++) {
                uint32_t S1 = ROR(e,6) ^ ROR(e,11) ^ ROR(e,25);
                uint32_t ch = (e & f) ^ (~e & g);
                uint32_t t1 = h + S1 + ch + K[i] + w[i];
                uint32_t S0 = ROR(a,2) ^ ROR(a,13) ^ ROR(a,22);
                uint32_t mj = (a & b) ^ (a & c) ^ (b & c);
                uint32_t t2 = S0 + mj;
                h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
        }
        s->h[0]+=a; s->h[1]+=b; s->h[2]+=c; s->h[3]+=d;
        s->h[4]+=e; s->h[5]+=f; s->h[6]+=g; s->h[7]+=h;
}
static void sha256_init(sha256_t *s) {
        static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
                                       0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
        memcpy(s->h, iv, sizeof iv); s->len = 0; s->n = 0;
}
static void sha256_add(sha256_t *s, const void *data, size_t len) {
        const unsigned char *p = data;
        s->len += len;
        while (len) {
                size_t c = 64 - s->n; if (c > len) c = len;
                memcpy(s->buf + s->n, p, c); s->n += c; p += c; len -= c;
                if (s->n == 64) { sha256_block(s, s->buf); s->n = 0; }
        }
}
static void sha256_final(sha256_t *s, unsigned char out[32]) {
        uint64_t bits = s->len * 8; unsigned char pad = 0x80; int i;
        sha256_add(s, &pad, 1);
        unsigned char z = 0;
        while (s->n != 56) sha256_add(s, &z, 1);
        unsigned char lb[8];
        for (i = 0; i < 8; i++) lb[i] = (unsigned char)(bits >> (56 - i*8));
        sha256_add(s, lb, 8);
        for (i = 0; i < 8; i++) {
                out[i*4]   = (unsigned char)(s->h[i] >> 24);
                out[i*4+1] = (unsigned char)(s->h[i] >> 16);
                out[i*4+2] = (unsigned char)(s->h[i] >> 8);
                out[i*4+3] = (unsigned char)(s->h[i]);
        }
}

static int hash_file(const char *path, unsigned char out[32], uint64_t *size) {
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        sha256_t s; sha256_init(&s);
        static unsigned char buf[65536];
        ssize_t r; uint64_t total = 0;
        while ((r = read(fd, buf, sizeof buf)) > 0) { sha256_add(&s, buf, (size_t)r); total += (uint64_t)r; }
        close(fd);
        if (r < 0) return -1;
        sha256_final(&s, out);
        if (size) *size = total;
        return 0;
}

static int eq_hex(const unsigned char *d, const char *hex) {
        char b[65]; int i;
        if (strlen(hex) != 64) return 0;
        for (i = 0; i < 32; i++) snprintf(b + i*2, 3, "%02x", d[i]);
        b[64] = 0;
        for (i = 0; i < 64; i++) {
                char c = hex[i];
                if (c >= 'A' && c <= 'F') c = (char)(c - 'A' + 'a');
                if (b[i] != c) return 0;
        }
        return 1;
}

/* ------------------------------------------------------------------- elf --- */
static int elf_machine(const char *path, unsigned *machine, unsigned *is64) {
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        unsigned char eh[64];
        ssize_t n = read(fd, eh, sizeof eh);
        close(fd);
        if (n < 20) return -1;
        if (eh[0] != 0x7f || eh[1] != 'E' || eh[2] != 'L' || eh[3] != 'F') return -2;
        *is64 = (eh[4] == 2);
        *machine = (unsigned)eh[18] | ((unsigned)eh[19] << 8);
        return 0;
}

int main(int argc, char **argv) {
        if (argc < 3) {
                fprintf(stderr, "usage: nuxel-verify sha256 <file> [hex] | elf <file> <machine> | present <file> <bytes>\n");
                return 2;
        }
        const char *cmd = argv[1], *path = argv[2];

        if (strcmp(cmd, "sha256") == 0) {
                unsigned char d[32]; uint64_t sz = 0; char hex[65]; int i;
                if (hash_file(path, d, &sz) < 0) {
                        printf("NUXEL-VERIFY sha256 io-error %s\n", strerror(errno));
                        return 2;
                }
                for (i = 0; i < 32; i++) snprintf(hex + i*2, 3, "%02x", d[i]);
                hex[64] = 0;
                printf("NUXEL-VERIFY sha256 %s %s size=%llu\n", hex, path, (unsigned long long)sz);
                if (argc >= 4) return eq_hex(d, argv[3]) ? 0 : 1;
                return 0;
        }
        if (strcmp(cmd, "elf") == 0) {
                unsigned m = 0, is64 = 0; int r;
                if (argc < 4) { fprintf(stderr, "elf needs <machine>\n"); return 2; }
                r = elf_machine(path, &m, &is64);
                if (r == -1) { printf("NUXEL-VERIFY elf io-error %s\n", strerror(errno)); return 2; }
                if (r == -2) { printf("NUXEL-VERIFY elf not-elf %s\n", path); return 1; }
                printf("NUXEL-VERIFY elf %s machine=%u (%s) class=%s\n",
                       path, m, m == 183 ? "aarch64" : "other", is64 ? "ELF64" : "ELF32");
                if (m != (unsigned)strtoul(argv[3], NULL, 10)) return 1;
                return 0;
        }
        if (strcmp(cmd, "present") == 0) {
                struct stat st;
                if (argc < 4) { fprintf(stderr, "present needs <bytes>\n"); return 2; }
                if (stat(path, &st) != 0) { printf("NUXEL-VERIFY present absent %s\n", path); return 1; }
                printf("NUXEL-VERIFY present %s size=%lld\n", path, (long long)st.st_size);
                return ((unsigned long long)st.st_size == strtoull(argv[3], NULL, 10)) ? 0 : 1;
        }
        fprintf(stderr, "unknown command %s\n", cmd);
        return 2;
}
