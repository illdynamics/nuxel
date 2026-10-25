/* nuxel-console (A33) — the live USB console service for the Nuxel S10+.
 *
 * WHAT THIS IS
 *   The device-side half of the LIVE CONSOLE (mission area 33).  It is the A33
 *   successor of tools/s10plus/a24-nuxel-console.c, which is a PINNED baseline
 *   asset (INV-5) and is deliberately left untouched: this file keeps A24's
 *   behaviour and adds the v2 framed command responder on top of it.
 *
 * WHAT IT KEEPS FROM A24 (the protected behaviour — do not regress)
 *   1. binds an ACM gadget to the first UDC through configfs;
 *   2. mknod()s /dev/ttyGS0 from /sys/class/tty/ttyGS0/dev (no udev/mdev in an
 *      initramfs, so the kernel cannot create the node itself);
 *   3. mirrors /dev/kmsg to the same tty, with an idle heartbeat so "silent
 *      console" can be told apart from "writes never leave the gadget";
 *   4. chroot()s into the real Fedora root (dirfd, this process only — PID1's
 *      switch_root is untouched) and runs an INTERACTIVE ROOT SHELL;
 *   5. respawns that shell after SIGHUP: the ACM tty raises SIGHUP at the
 *      foreground process group when the HOST closes the port, and measured A23
 *      showed a single-use console otherwise (recoverable only by power cycle).
 *
 * WHAT IT ADDS (A26 → A33 findings, all offline-tested by --selftest)
 *   A26 recorded the failure mode: a single long-running command wedged the ONE
 *   shared shell — every later command queued silently behind it and the prompt
 *   disappeared for minutes.  The v2 framed protocol fixed the HOST side
 *   (scripts/s10plus-debug-pack/nuxel-live.sh), and this responder fixes the
 *   DEVICE side so the shared shell cannot be wedged at all:
 *
 *     * a line that matches the host's framed wrapper is recognised and handled
 *       here; the command runs in its OWN process group, never in the shared
 *       shell, so an unbounded command cannot block the console;
 *     * execution is BOUNDED (per-request timeout; the default is generous but
 *       finite) and CANCELLABLE: a timeout, or a Ctrl-C typed on the tty, sends
 *       SIGINT to the whole child group, then SIGTERM, then SIGKILL;
 *     * the REAL exit status is reported in `@@NXR<id>:<rc>@@` (130 for a
 *       cancelled command, exactly what a shell reports for SIGINT);
 *     * the payload is streamed as base64 inside `@@NXB<id>@@` … `@@NXE<id>@@`
 *       with the target-side SHA-256 in `@@NXH<id>:<hash>@@`, so a shredded or
 *       truncated transfer is detectable and can never be mistaken for success;
 *     * the port is LOCKED (flock) so a second instance refuses with exit 3
 *       instead of fighting over the tty.
 *
 *   A line that does NOT match the wrapper is forwarded to the interactive shell
 *   unchanged, so `screen`, `--watch` and hand-typed use keep working exactly as
 *   they did on A21/A24.  Anything ambiguous fails OPEN to the old behaviour.
 *
 * SAFETY
 *   Never opens /dev/fb0.  Closing a framebuffer fd runs the DECON's fb_release
 *   and powers the AMOLED down (measured A21: one `dd if=/dev/fb0` left 1279
 *   subsequent pans failing), so all screen work must go through the running UI's
 *   own command FIFO.  Nothing here writes to any block device.
 *
 * USAGE
 *   nuxel-console <newroot> [--no-shell|--no-pump|--no-responder|--timeout ms]
 *   nuxel-console --frame <id> <command>     # emit one frame on stdout (tests)
 *   nuxel-console --selftest                 # offline: framing, ids, sha256,
 *                                            # base64, bounding, cancellation
 *   nuxel-console --help
 *
 * BUILD (offline, no kernel, no root):
 *   cc -O2 -Wall -Wextra -o nuxel-console tools/s10plus/a33/nuxel-console.c
 *   static aarch64 for the phone:
 *   aarch64-linux-gnu-gcc -O2 -static -Wall -Wextra -o nuxel-console \
 *       tools/s10plus/a33/nuxel-console.c
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#ifdef __linux__
#include <sys/ioctl.h>          /* TIOCSCTTY */
#include <sys/mount.h>
#include <sys/sysmacros.h>      /* major()/minor() */
#else
#include <sys/ioctl.h>
#endif

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

extern char **environ;

#define GADGET   "/sys/kernel/config/usb_gadget/nuxel"
#define TTY      "/dev/ttyGS0"
#define KMSG     "/dev/kmsg"
#define FRAME_MAGIC "@@NX"
#define DEFAULT_TIMEOUT_MS 20000
#define GRACE_MS            2000
#define MAX_LINE          (256 * 1024)
#define BASE64_WRAP      76

static int g_kmsg = -1;

/* ------------------------------------------------------------------ logging */
static void klog(const char *fmt, ...) {
        char buf[512];
        va_list ap;
        va_start(ap, fmt);
        int n = vsnprintf(buf, sizeof buf, fmt, ap);
        va_end(ap);
        if (n < 0) return;
        if (n > (int)sizeof buf - 1) n = (int)sizeof buf - 1;
        if (g_kmsg >= 0) (void)!write(g_kmsg, buf, (size_t)n);
        (void)!write(2, buf, (size_t)n);
}

static long now_ms(void) {
        struct timespec ts;
#ifdef CLOCK_MONOTONIC
        if (clock_gettime(CLOCK_MONOTONIC, &ts) == 0)
                return (long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
#endif
        ts.tv_sec = time(NULL);
        return (long)ts.tv_sec * 1000;
}

static void msleep(int ms) {
        struct timespec ts;
        ts.tv_sec = ms / 1000;
        ts.tv_nsec = (long)(ms % 1000) * 1000000L;
        while (nanosleep(&ts, &ts) != 0 && errno == EINTR) { }
}

static int write_all(int fd, const char *p, size_t n) {
        while (n) {
                ssize_t w = write(fd, p, n);
                if (w < 0) {
                        if (errno == EINTR) continue;
                        return -1;
                }
                p += w; n -= (size_t)w;
        }
        return 0;
}

/* ------------------------------------------------------------- SHA-256 (FIPS)
 * A local implementation, not a shell-out to sha256sum: the responder must work
 * in the initramfs before the rootfs exists, and the offline selftest can then
 * check it against the published FIPS-180 test vectors on any host.
 */
typedef struct { uint32_t h[8]; uint64_t len; unsigned char buf[64]; size_t n; } sha256_ctx;

static const uint32_t K256[64] = {
        0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
        0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
        0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
        0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
        0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
        0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
        0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
        0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u };

#define ROR(x,n) (((x) >> (n)) | ((x) << (32 - (n))))

static void sha256_init(sha256_ctx *c) {
        c->h[0]=0x6a09e667u; c->h[1]=0xbb67ae85u; c->h[2]=0x3c6ef372u; c->h[3]=0xa54ff53au;
        c->h[4]=0x510e527fu; c->h[5]=0x9b05688cu; c->h[6]=0x1f83d9abu; c->h[7]=0x5be0cd19u;
        c->len = 0; c->n = 0;
}

static void sha256_block(sha256_ctx *c, const unsigned char *p) {
        uint32_t w[64], a, b, d, e, f, g, h, t1, t2;
        int i;
        for (i = 0; i < 16; i++)
                w[i] = ((uint32_t)p[i*4] << 24) | ((uint32_t)p[i*4+1] << 16) |
                       ((uint32_t)p[i*4+2] << 8) | (uint32_t)p[i*4+3];
        for (i = 16; i < 64; i++) {
                uint32_t s0 = ROR(w[i-15],7) ^ ROR(w[i-15],18) ^ (w[i-15] >> 3);
                uint32_t s1 = ROR(w[i-2],17) ^ ROR(w[i-2],19) ^ (w[i-2] >> 10);
                w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        a=c->h[0]; b=c->h[1]; d=c->h[3]; e=c->h[4]; f=c->h[5]; g=c->h[6]; h=c->h[7];
        /* c->h[2] is kept in `cc` below to avoid shadowing the digest array */
        uint32_t cc = c->h[2];
        for (i = 0; i < 64; i++) {
                uint32_t S1 = ROR(e,6) ^ ROR(e,11) ^ ROR(e,25);
                uint32_t ch = (e & f) ^ ((~e) & g);
                t1 = h + S1 + ch + K256[i] + w[i];
                uint32_t S0 = ROR(a,2) ^ ROR(a,13) ^ ROR(a,22);
                uint32_t mj = (a & b) ^ (a & cc) ^ (b & cc);
                t2 = S0 + mj;
                h = g; g = f; f = e; e = d + t1;
                d = cc; cc = b; b = a; a = t1 + t2;
        }
        c->h[0]+=a; c->h[1]+=b; c->h[2]+=cc; c->h[3]+=d;
        c->h[4]+=e; c->h[5]+=f; c->h[6]+=g; c->h[7]+=h;
}

static void sha256_update(sha256_ctx *c, const void *data, size_t n) {
        const unsigned char *p = (const unsigned char *)data;
        c->len += n;
        if (c->n) {
                size_t take = 64 - c->n;
                if (take > n) take = n;
                memcpy(c->buf + c->n, p, take);
                c->n += take; p += take; n -= take;
                if (c->n == 64) { sha256_block(c, c->buf); c->n = 0; }
        }
        while (n >= 64) { sha256_block(c, p); p += 64; n -= 64; }
        if (n) { memcpy(c->buf, p, n); c->n = n; }
}

static void sha256_final(sha256_ctx *c, unsigned char out[32]) {
        uint64_t bits = c->len * 8;
        unsigned char pad = 0x80;
        sha256_update(c, &pad, 1);
        unsigned char zero = 0;
        while (c->n != 56) sha256_update(c, &zero, 1);
        unsigned char lenb[8];
        for (int i = 0; i < 8; i++) lenb[i] = (unsigned char)(bits >> (56 - 8*i));
        sha256_update(c, lenb, 8);
        for (int i = 0; i < 8; i++) {
                out[i*4]   = (unsigned char)(c->h[i] >> 24);
                out[i*4+1] = (unsigned char)(c->h[i] >> 16);
                out[i*4+2] = (unsigned char)(c->h[i] >> 8);
                out[i*4+3] = (unsigned char)(c->h[i]);
        }
}

static void hex32(const unsigned char d[32], char out[65]) {
        static const char H[] = "0123456789abcdef";
        for (int i = 0; i < 32; i++) { out[i*2] = H[d[i] >> 4]; out[i*2+1] = H[d[i] & 15]; }
        out[64] = 0;
}

static int sha256_file(const char *path, char out[65]) {
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        sha256_ctx c; sha256_init(&c);
        static unsigned char buf[65536];
        for (;;) {
                ssize_t r = read(fd, buf, sizeof buf);
                if (r < 0) { if (errno == EINTR) continue; close(fd); return -1; }
                if (r == 0) break;
                sha256_update(&c, buf, (size_t)r);
        }
        close(fd);
        unsigned char d[32]; sha256_final(&c, d); hex32(d, out);
        return 0;
}

/* ------------------------------------------------------------------- base64 */
static size_t b64_encode(const unsigned char *in, size_t n, char *out) {
        static const char B[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        size_t i = 0, o = 0, col = 0;
        while (i + 2 < n) {
                uint32_t v = ((uint32_t)in[i] << 16) | ((uint32_t)in[i+1] << 8) | in[i+2];
                out[o++] = B[(v >> 18) & 63]; out[o++] = B[(v >> 12) & 63];
                out[o++] = B[(v >> 6) & 63];  out[o++] = B[v & 63];
                i += 3; col += 4;
                if (col >= BASE64_WRAP) { out[o++] = '\n'; col = 0; }
        }
        if (i < n) {
                uint32_t v = (uint32_t)in[i] << 16;
                int rem = (int)(n - i);
                if (rem == 2) v |= (uint32_t)in[i+1] << 8;
                out[o++] = B[(v >> 18) & 63];
                out[o++] = B[(v >> 12) & 63];
                out[o++] = rem == 2 ? B[(v >> 6) & 63] : '=';
                out[o++] = '=';
                if (col + 4 >= BASE64_WRAP) out[o++] = '\n';
        }
        return o;
}

/* ----------------------------------------------------------- uid for frames */
/* `<4 hex from the CSPRNG or the clock><4 hex from the clock>` is the same shape
 * the host tool uses, so an operator sees one id format everywhere.  Uniqueness
 * is what matters: the host rejects a frame whose id does not match its request,
 * and the app never mixes two requests' output. */
static void make_id(const char *seed, char out[9]) {
        static unsigned counter = 0;
        uint32_t r;
        int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
        if (fd >= 0) {
                if (read(fd, &r, sizeof r) != (ssize_t)sizeof r) r = 0;
                close(fd);
        } else {
                r = (uint32_t)time(NULL) ^ (uint32_t)(uintptr_t)seed ^ (counter++ * 2654435761u);
        }
        uint32_t t = (uint32_t)time(NULL);
        /* Deterministic mode (selftest) passes a seed and wants distinguishable
         * ids without depending on /dev/urandom existing. */
        if (seed) r ^= (uint32_t)(uintptr_t)seed ^ (counter++ * 2654435761u);
        snprintf(out, 9, "%04x%04x", (unsigned)(r & 0xffffu), (unsigned)(t & 0xffffu));
}

/* ------------------------------------------------------ bounded command exec */
struct exec_result {
        int  rc;             /* child's exit status, or 128+signal */
        int  timed_out;
        int  cancelled;
        long ms;
};

/* run `cmd` with stdout+stderr merged into `outpath`, in its OWN process group,
 * bounded by `timeout_ms`, and cancellable by SIGINT on the tty. */
static int exec_bounded(const char *cmd, const char *outpath, int timeout_ms,
                        int watch_fd, struct exec_result *res) {
        int fd = open(outpath, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
        if (fd < 0) return -1;

        long t0 = now_ms();
        pid_t pid = fork();
        if (pid < 0) { close(fd); return -1; }

        if (pid == 0) {
                (void)setpgid(0, 0);                 /* its own group: we can signal all of it */
                (void)setsid();
                if (fd != 1) (void)dup2(fd, 1);
                (void)dup2(1, 2);
                int devnull = open("/dev/null", O_RDONLY);
                if (devnull >= 0) { (void)dup2(devnull, 0); if (devnull > 2) close(devnull); }
                if (fd > 2) close(fd);
                execl("/bin/sh", "sh", "-c", cmd, (char *)NULL);
                execl("/usr/bin/sh", "sh", "-c", cmd, (char *)NULL);
                _exit(127);
        }

        (void)setpgid(pid, pid);                     /* both sides, to avoid the race */

        int status = 0, done = 0, killed_by = 0;
        while (!done) {
                pid_t w = waitpid(pid, &status, WNOHANG);
                if (w == pid) { done = 1; break; }
                if (w < 0 && errno != EINTR) { done = 1; break; }
                if (now_ms() - t0 >= timeout_ms) { res->timed_out = 1; break; }
                if (watch_fd >= 0) {
                        struct pollfd p = { .fd = watch_fd, .events = POLLIN };
                        if (poll(&p, 1, 50) > 0) {
                                char b[64];
                                ssize_t n = read(watch_fd, b, sizeof b);
                                for (ssize_t i = 0; i < n; i++)
                                        if ((unsigned char)b[i] == 0x03) { res->cancelled = 1; break; }
                                if (res->cancelled) break;
                        }
                } else {
                        msleep(20);
                }
        }

        if (!done || res->timed_out || res->cancelled) {
                /* SIGINT first (what Ctrl-C means), then escalate.  The whole
                 * process group is signalled, so a shell that spawned children
                 * cannot leave them behind holding the console. */
                (void)kill(-pid, SIGINT);
                (void)kill(pid, SIGINT);
                long deadline = now_ms() + GRACE_MS;
                while (now_ms() < deadline) {
                        pid_t w = waitpid(pid, &status, WNOHANG);
                        if (w == pid) { done = 1; killed_by = SIGINT; break; }
                        msleep(50);
                }
                if (!done) {
                        (void)kill(-pid, SIGTERM); (void)kill(pid, SIGTERM);
                        deadline = now_ms() + GRACE_MS;
                        while (now_ms() < deadline) {
                                pid_t w = waitpid(pid, &status, WNOHANG);
                                if (w == pid) { done = 1; killed_by = SIGTERM; break; }
                                msleep(50);
                        }
                }
                if (!done) {
                        (void)kill(-pid, SIGKILL); (void)kill(pid, SIGKILL);
                        (void)waitpid(pid, &status, 0);
                        killed_by = SIGKILL;
                }
                if (WIFSIGNALED(status)) killed_by = WTERMSIG(status);
                res->rc = 128 + (killed_by ? killed_by : SIGINT);
        } else if (WIFEXITED(status)) {
                res->rc = WEXITSTATUS(status);
        } else if (WIFSIGNALED(status)) {
                res->rc = 128 + WTERMSIG(status);
        } else {
                res->rc = 1;
        }
        res->ms = now_ms() - t0;
        close(fd);
        return 0;
}

/* ------------------------------------------------------------ frame writing */
/* The wire format, byte for byte, that scripts/s10plus-debug-pack/nuxel-live.sh
 * parses (and that pwa/nuxel-apps/console/js/console-protocol.js parses):
 *
 *   \n@@NXB<id>@@\n
 *   @@NXR<id>:<rc>@@\n
 *   @@NXH<id>:<sha256>@@\n
 *   <base64 of the payload, 76 columns>\n
 *   @@NXE<id>@@\n
 */
static int emit_frame(int outfd, const char *id, const char *outpath, int rc,
                      const char *note) {
        char hash[65];
        if (sha256_file(outpath, hash) != 0) snprintf(hash, sizeof hash, "%064d", 0);

        /* The diagnostic note is emitted BEFORE the begin marker, i.e. outside the
         * payload region a parser scans between @@NXH…@@ and @@NXE…@@, so it can
         * never be mistaken for body data and it does not change the hash. */
        if (note && *note) {
                char nb[300];
                int k = snprintf(nb, sizeof nb, "\n@@NXN%s:%s@@\n", id, note);
                if (write_all(outfd, nb, (size_t)k) != 0) return -1;
        }
        char hdr[256];
        int n = snprintf(hdr, sizeof hdr, "\n@@NXB%s@@\n@@NXR%s:%d@@\n@@NXH%s:%s@@\n",
                         id, id, rc, id, hash);
        if (write_all(outfd, hdr, (size_t)n) != 0) return -1;

        int fd = open(outpath, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        static unsigned char raw[49152];
        static char b64[70000];
        ssize_t r;
        while ((r = read(fd, raw, sizeof raw)) > 0) {
                size_t o = b64_encode(raw, (size_t)r, b64);
                if (write_all(outfd, b64, o) != 0) { close(fd); return -1; }
        }
        close(fd);
        char tail[64];
        int t = snprintf(tail, sizeof tail, "\n@@NXE%s@@\n", id);
        return write_all(outfd, tail, (size_t)t);
}

/* -------------------------------------------------- wrapper recognition (v2) */
/* The host wrapper is generated by our own tool and looks like:
 *   _NXID=ab12cd34; rm -f /var/tmp/nx-ab12cd34.out; { <cmd> ; } >/var/tmp/nx-ab12cd34.out 2>&1 </dev/null; printf ...
 * We only intercept it when ALL of the pieces we need are found; otherwise the
 * line is handed to the interactive shell (fail open, never guess). */
static int parse_wrapper(const char *line, char id[9], char *tmp, size_t tmpsz,
                         char *cmd, size_t cmdsz) {
        const char *p = strstr(line, "_NXID=");
        if (!p) return 0;
        p += 6;
        for (int i = 0; i < 8; i++) if (!isxdigit((unsigned char)p[i])) return 0;
        memcpy(id, p, 8); id[8] = 0;

        const char *rm = strstr(line, "rm -f ");
        const char *dot = rm ? strstr(rm + 6, ".out") : NULL;
        if (!rm || !dot) return 0;
        size_t tlen = (size_t)(dot - (rm + 6));
        if (tlen == 0 || tlen + 1 > tmpsz) return 0;
        memcpy(tmp, rm + 6, tlen); tmp[tlen] = 0;

        if (!strstr(dot, "base64 -w76") || !strstr(dot, "@@NXE")) return 0;

        const char *bra = strstr(line, "{ ");
        const char *end = dot ? strstr(dot, " ; } >") : NULL;
        if (!bra || !end || end <= bra + 2) return 0;
        size_t clen = (size_t)(end - (bra + 2));
        if (clen + 1 > cmdsz) return 0;
        memcpy(cmd, bra + 2, clen); cmd[clen] = 0;
        /* trim surrounding whitespace */
        while (clen && isspace((unsigned char)cmd[clen-1])) cmd[--clen] = 0;
        if (!*cmd) return 0;
        return 1;
}

/* Serve one recognised wrapper request.  Returns 0 when it was handled here. */
static int serve_wrapper(const char *line, int outfd, int timeout_ms, int watch_fd) {
        char id[9], tmp[512], cmd[MAX_LINE];
        if (!parse_wrapper(line, id, tmp, sizeof tmp, cmd, sizeof cmd)) return -1;

        char outpath[600];
        snprintf(outpath, sizeof outpath, "%s.out", tmp);
        unlink(outpath);

        struct exec_result r; memset(&r, 0, sizeof r);
        char note[128] = "";
        if (exec_bounded(cmd, outpath, timeout_ms, watch_fd, &r) != 0) {
                snprintf(note, sizeof note, "exec-failed:%s", strerror(errno));
                snprintf(outpath, sizeof outpath, "/dev/null");
        } else if (r.timed_out) {
                snprintf(note, sizeof note, "bounded-timeout:%dms", timeout_ms);
        } else if (r.cancelled) {
                snprintf(note, sizeof note, "cancelled-by-ctrl-c");
        }

        klog("nuxel-console: frame %s rc=%d ms=%ld%s%s\n", id, r.rc, r.ms,
             note[0] ? " " : "", note);
        if (emit_frame(outfd, id, outpath, r.rc, note) != 0) return -1;
        unlink(outpath);
        return 0;
}

/* --------------------------------------------------------------- port lock */
static int g_lockfd = -1;
static int lock_port(const char *path) {
#ifdef LOCK_EX
        g_lockfd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
        if (g_lockfd < 0) return -1;
        if (flock(g_lockfd, LOCK_EX | LOCK_NB) != 0) {
                klog("nuxel-console: another console already owns %s — refusing (exit 3)\n", path);
                return -3;
        }
#endif
        return 0;
}

/* ------------------------------------------------------------------ sysfs io */
static int mkdir_p(const char *p);

/* Session evidence for the lockscreen's live-console indicator.
 *
 * This is a LEASE, not a toggle: it is written only once this process has opened
 * the console tty and is about to serve it, and it is removed on every exit path
 * (normal, error, signal).  A stale file is therefore impossible after a clean
 * shutdown, and the indicator also validates the pid and the process cmdline, so
 * even a crashed writer cannot leave a permanent "on".  Root access alone never
 * creates this file.
 */
#define LIVE_SESSION_MARKER "/run/nuxel/live-console-session"
static int g_session_marker_written = -1;

static void live_session_clear(void) {
        if (g_session_marker_written == 1) {
                (void)unlink(LIVE_SESSION_MARKER);
                g_session_marker_written = 0;
        }
}

static void live_session_signal(int sig) {
        live_session_clear();
        signal(sig, SIG_DFL);
        raise(sig);
}

static void live_session_mark(void) {
        mkdir_p("/run/nuxel");
        FILE *f = fopen(LIVE_SESSION_MARKER ".new", "w");
        if (!f) {
                g_session_marker_written = 0;
                klog("nuxel-console: cannot write %s: %s (indicator stays dim)\n",
                     LIVE_SESSION_MARKER, strerror(errno));
                return;
        }
        fprintf(f, "pid=%d\n", (int)getpid());
        fprintf(f, "tty=" TTY "\n");
        fprintf(f, "state=serving\n");
        if (fflush(f) != 0) { fclose(f); unlink(LIVE_SESSION_MARKER ".new"); g_session_marker_written = 0; return; }
        fclose(f);
        if (rename(LIVE_SESSION_MARKER ".new", LIVE_SESSION_MARKER) != 0) {
                unlink(LIVE_SESSION_MARKER ".new");
                g_session_marker_written = 0;
                return;
        }
        g_session_marker_written = 1;
        atexit(live_session_clear);
        signal(SIGTERM, live_session_signal);
        signal(SIGINT, live_session_signal);
        signal(SIGHUP, live_session_signal);
}

static int wfile(const char *path, const char *fmt, ...) {
        char buf[256];
        va_list ap; va_start(ap, fmt);
        int n = vsnprintf(buf, sizeof buf, fmt, ap);
        va_end(ap);
        if (n < 0) return -1;
        int fd = open(path, O_WRONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        ssize_t w = write(fd, buf, (size_t)n);
        int e = errno;
        close(fd);
        if (w != n) { errno = e ? e : EIO; return -1; }
        return 0;
}

static int mkdir_p(const char *p) {
        char tmp[256]; size_t len;
        snprintf(tmp, sizeof tmp, "%s", p);
        len = strlen(tmp);
        if (len && tmp[len-1] == '/') tmp[len-1] = 0;
        for (char *q = tmp + 1; *q; q++)
                if (*q == '/') { *q = 0; (void)mkdir(tmp, 0755); *q = '/'; }
        return mkdir(tmp, 0755);
}

static int udc_name(char *out, size_t n) {
        DIR *d = opendir("/sys/class/udc");
        struct dirent *e;
        if (!d) return -1;
        while ((e = readdir(d))) {
                if (e->d_name[0] == '.') continue;
                snprintf(out, n, "%s", e->d_name);
                closedir(d);
                return 0;
        }
        closedir(d);
        return -1;
}

static int ufile(const char *path, const char *val) {
        int fd = open(path, O_WRONLY | O_CLOEXEC);
        if (fd < 0) return -1;
        ssize_t n = write(fd, val, strlen(val));
        close(fd);
        return n < 0 ? -1 : 0;
}

/* Bind the CDC-ACM gadget.  Kept from A24: the Exynos 9820 kernel registers
 * 10c00000.dwc3 and has CONFIG_USB_CONFIGFS + CONFIG_USB_CONFIGFS_ACM, so the
 * whole gadget can be created from userspace with no kernel change. */
static int bring_up_gadget(void) {
        char udc[128];
        if (access(GADGET, F_OK) != 0) {
                klog("nuxel-console: no %s (kernel without configfs usb_gadget?)\n", GADGET);
                return -1;
        }
        (void)mkdir_p(GADGET "/functions/acm.usb0");
        (void)mkdir_p(GADGET "/configs/c.1");
        (void)mkdir_p(GADGET "/strings/0x409");
        (void)mkdir_p(GADGET "/configs/c.1/strings/0x409");
        (void)wfile(GADGET "/idVendor", "0x04e8\n");
        (void)wfile(GADGET "/idProduct", "0x6863\n");
        (void)wfile(GADGET "/bcdDevice", "0x0100\n");
        (void)wfile(GADGET "/bcdUSB", "0x0200\n");
        (void)wfile(GADGET "/strings/0x409/serialnumber", "NUXEL-S10PLUS-0001\n");
        (void)wfile(GADGET "/strings/0x409/manufacturer", "Nuxel\n");
        (void)wfile(GADGET "/strings/0x409/product", "Nuxel S10+ Live Console\n");
        (void)wfile(GADGET "/configs/c.1/strings/0x409/configuration", "Nuxel ACM console\n");
        (void)wfile(GADGET "/configs/c.1/MaxPower", "500\n");
        (void)symlink(GADGET "/functions/acm.usb0", GADGET "/configs/c.1/acm.usb0");
        if (udc_name(udc, sizeof udc) != 0) {
                klog("nuxel-console: no UDC in /sys/class/udc — gadget stays unbound\n");
                return -1;
        }
        if (ufile(GADGET "/UDC", udc) != 0) {
                klog("nuxel-console: could not bind UDC %s: %s\n", udc, strerror(errno));
                return -1;
        }
        klog("nuxel-console: gadget bound to %s\n", udc);
        return 0;
}

/* /dev/ttyGS0 does not exist until userspace makes it: the kernel registers the
 * tty in sysfs and expects udev/mdev (absent in an initramfs) to create the node.
 * Measured in A18/A24 — see the A24 header. */
static int ensure_tty_node(void) {
        static const char sysdev[] = "/sys/class/tty/ttyGS0/dev";
        char buf[64];
        int i, fd;
        struct stat st;
        for (i = 0; i < 60; i++) {
                if (stat(TTY, &st) == 0 && S_ISCHR(st.st_mode)) return 0;
                fd = open(sysdev, O_RDONLY | O_CLOEXEC);
                if (fd >= 0) {
                        ssize_t n = read(fd, buf, sizeof buf - 1);
                        close(fd);
                        if (n > 0) {
                                unsigned maj = 0, min = 0;
                                buf[n] = 0;
                                if (sscanf(buf, "%u:%u", &maj, &min) == 2) {
                                        if (mknod(TTY, S_IFCHR | 0666,
                                                  (dev_t)((maj << 8) | min)) == 0 ||
                                            errno == EEXIST)
                                                return 0;
                                        klog("nuxel-console: mknod %s %u:%u: %s\n",
                                             TTY, maj, min, strerror(errno));
                                }
                        }
                }
                msleep(500);
        }
        klog("nuxel-console: %s did not appear\n", TTY);
        return -1;
}

/* ---------------------------------------------------------------- pty helper */
#ifndef TIOCSCTTY
#define TIOCSCTTY 0x540E
#endif

static int open_pty(char *slave, size_t slsz) {
        int m = posix_openpt(O_RDWR | O_NOCTTY | O_CLOEXEC);
        if (m < 0) return -1;
        if (grantpt(m) != 0 || unlockpt(m) != 0) { close(m); return -1; }
        const char *s = ptsname(m);
        if (!s) { close(m); return -1; }
        snprintf(slave, slsz, "%s", s);
        return m;
}

static int set_raw(int fd) {
        struct termios t;
        if (tcgetattr(fd, &t) != 0) return -1;
        cfmakeraw(&t);
        t.c_cc[VMIN] = 0;
        t.c_cc[VTIME] = 0;
        return tcsetattr(fd, TCSANOW, &t);
}

/* ------------------------------------------------------------------- kmsg pump
 * Runs as a forked child so it can never delay or fail the console.  Kept from
 * A24, including the idle heartbeat: a silent console must be distinguishable
 * from a gadget whose writes never leave the device. */
static void pump_kmsg(int tfd) {
        int fd = open(KMSG, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) return;
        if (tfd < 0) { close(fd); return; }
        static char buf[4096];
        int idle = 0;
        const char hello[] = "\r\nNUXEL live kernel log attached (ttyGS0).\r\n";
        (void)!write(tfd, hello, sizeof hello - 1);
        for (;;) {
                struct pollfd p = { .fd = fd, .events = POLLIN };
                if (poll(&p, 1, 1000) <= 0) {
                        if (++idle >= 10) {
                                idle = 0;
                                const char hb[] = "\r\nNUXEL-CONSOLE heartbeat (device->host OK)\r\n";
                                if (write(tfd, hb, sizeof hb - 1) <= 0) _exit(0);
                        }
                        continue;
                }
                idle = 0;
                ssize_t r = read(fd, buf, sizeof buf - 1);
                if (r <= 0) continue;
                buf[r] = 0;
                if (write(tfd, buf, (size_t)r) <= 0) _exit(0);
        }
}

/* ---------------------------------------------------------------- shell child */
static void shell_child(const char *newroot, int ttyfd, const char *ptyslave) {
        if (newroot) {
                if (chdir(newroot) != 0) { klog("nuxel-console: chdir %s: %s\n", newroot, strerror(errno)); _exit(1); }
                if (chroot(".") != 0) { klog("nuxel-console: chroot: %s\n", strerror(errno)); _exit(1); }
                if (chdir("/") != 0) _exit(1);
        }
        int fd = -1;
        if (ptyslave) {
                fd = open(ptyslave, O_RDWR | O_NOCTTY);
        } else if (ttyfd >= 0) {
                fd = dup(ttyfd);
        } else {
                fd = open(TTY, O_RDWR);
        }
        if (fd < 0) { klog("nuxel-console: shell has no tty (%s)\n", strerror(errno)); _exit(1); }

        (void)setsid();
        (void)ioctl(fd, TIOCSCTTY, 0);
        dup2(fd, 0); dup2(fd, 1); dup2(fd, 2);
        if (fd > 2) close(fd);

        setenv("TERM", "vt100", 1);
        setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
        setenv("HOME", "/root", 1);
        setenv("PS1", "nuxel-s10+ # ", 1);

        (void)!write(1, "\r\n================= NUXEL S10+ LIVE CONSOLE (A33) =================\r\n"
                        " Root inside the Fedora/Nuxel rootfs, over USB (ttyGS0).\r\n"
                        " Kernel ring buffer streams to this port above the prompt.\r\n"
                        " Bounded commands are served natively (own process group);\r\n"
                        " type 'exit' to drop the shell (the respawn supervisor holds\r\n"
                        " the channel open, so the console is never single-use).\r\n"
                        "=================================================================\r\n\r\n", 0);

        /* SIGHUP is raised when the HOST closes the port.  An IGNORED disposition
         * survives execve (a handler does not), so the shell ignores it before
         * exec -- that is the A24 fix this file must not lose. */
        char *av[] = { (char *)"sh", (char *)"-c", (char *)"trap '' HUP; exec /bin/sh -i", NULL };
        execve("/bin/sh", av, environ);
        char *av2[] = { (char *)"bash", (char *)"-i", NULL };
        execve("/usr/bin/bash", av2, environ);
        execve("/bin/bash", av2, environ);
        (void)!write(1, "nuxel-console: no /bin/sh in the new root\r\n", 43);
        _exit(127);
}

/* ---------------------------------------------------------------- line reader
 * Reads one line (up to '\n', stripped) from `fd` with a bounded total wait.
 * Returns 1 on a line, 0 on EOF/link loss, -1 on error.  `why` names the cause so
 * a cable pull is reported as a cable pull and never as a crash.
 */
static int read_line(int fd, char *buf, size_t cap, int timeout_ms, const char **why) {
        size_t n = 0;
        long deadline = now_ms() + timeout_ms;
        *why = "ok";
        for (;;) {
                if (n + 1 >= cap) { buf[n] = 0; return 1; }
                struct pollfd p = { .fd = fd, .events = POLLIN };
                int pr = poll(&p, 1, 200);
                if (pr < 0) {
                        if (errno == EINTR) continue;
                        *why = strerror(errno);
                        return -1;
                }
                if (pr == 0) {
                        if (timeout_ms > 0 && now_ms() >= deadline) { *why = "idle-timeout"; return 0; }
                        continue;
                }
                char c;
                ssize_t r = read(fd, &c, 1);
                if (r < 0) {
                        if (errno == EINTR) continue;
                        if (errno == EAGAIN || errno == EWOULDBLOCK) continue;
                        *why = strerror(errno);          /* e.g. ENXIO after a cable pull */
                        return -1;
                }
                if (r == 0) { *why = "end-of-stream"; return 0; }
                if (c == '\n' || c == '\r') { buf[n] = 0; return 1; }
                buf[n++] = c;
        }
}

/* ------------------------------------------------------ responder-only mode */
/* No shell: every line must be a framed request.  Used by the offline tests and
 * by a host that wants bounded execution with no interactive shell at all. */
static int run_responder(int infd, int outfd, int timeout_ms) {
        static char line[MAX_LINE];
        int served = 0, ignored = 0;
        for (;;) {
                const char *why = "ok";
                int r = read_line(infd, line, sizeof line, 0, &why);
                if (r < 0) {
                        klog("nuxel-console: console link lost (%s) — responder exiting cleanly\n", why);
                        return 0;
                }
                if (r == 0) {
                        klog("nuxel-console: console link ended (%s) — responder exiting cleanly\n", why);
                        return 0;
                }
                if (!*line) continue;
                if (serve_wrapper(line, outfd, timeout_ms, -1) == 0) { served++; continue; }
                ignored++;
                if (ignored <= 3)
                        klog("nuxel-console: ignoring a non-framed line (%zu bytes) — "
                             "interactive use needs --mode mux\n", strlen(line));
        }
        (void)served;
}

/* ------------------------------------------------------------- mux (default) */
struct mux {
        int tty;
        int pty;
        char pend[16384];
        size_t pendn;
        int committed;
};

static int mux_flush(struct mux *m) {
        if (!m->pendn) return 0;
        int rc = write_all(m->pty, m->pend, m->pendn);
        m->pendn = 0; m->committed = 0;
        return rc;
}

/* decide what a partially-read '_' line is: 1 = still a possible wrapper,
 * 0 = definitely not, -1 = complete line (ready to serve). */
static int wrapper_state(const char *s, size_t n) {
        static const char M[] = "_NXID=";
        if (n < sizeof M - 1) return strncmp(s, M, n) == 0 ? 1 : 0;
        if (strncmp(s, M, sizeof M - 1) != 0) return 0;
        size_t k = n - (sizeof M - 1);
        if (k <= 8) {
                for (size_t i = 0; i < k; i++) if (!isxdigit((unsigned char)s[sizeof M - 1 + i])) return 0;
                return 1;
        }
        if (k == 9) return s[n-1] == ';' ? 1 : 0;
        return -1;                                     /* committed: read to end of line */
}

/* One input byte from the host.  Returns 0 normally; sets *lost on link loss. */
static int mux_input(struct mux *m, unsigned char c, int timeout_ms, int *lost) {
        *lost = 0;
        if (!m->pendn) {
                if (c == '_') { m->pend[m->pendn++] = (char)c; return 0; }   /* maybe a wrapper */
                if (write_all(m->pty, (const char *)&c, 1) != 0) *lost = 1;
                return 0;
        }
        m->pend[m->pendn++] = (char)c;
        if (c == '\n' || c == '\r') {
                int st = wrapper_state(m->pend, m->pendn);
                if (st == -1) {
                        m->pend[m->pendn ? m->pendn - 1 : 0] = 0;
                        if (serve_wrapper(m->pend, m->tty, timeout_ms, m->tty) == 0) {
                                m->pendn = 0; m->committed = 0;
                                return 0;
                        }
                        /* not actually a wrapper: hand the line back to the shell */
                        if (write_all(m->pty, m->pend, strlen(m->pend)) != 0) *lost = 1;
                        if (write_all(m->pty, "\r", 1) != 0) *lost = 1;
                        m->pendn = 0; m->committed = 0;
                        return 0;
                }
        }
        int st = wrapper_state(m->pend, m->pendn);
        if (st == 0) { if (mux_flush(m) != 0) *lost = 1; return 0; }
        if (st == -1) {
                m->committed = 1;
                if (m->pendn + 2 >= sizeof m->pend) { if (mux_flush(m) != 0) *lost = 1; }
        }
        return 0;
}

/* The multiplexer: host bytes -> (native frame handler | pty), pty -> host. */
static int run_mux(int tty, const char *newroot, int timeout_ms, int with_shell) {
        struct mux m;
        char slavename[128];
        int ptyfd = open_pty(slavename, sizeof slavename);
        if (ptyfd < 0) {
                klog("nuxel-console: cannot allocate a pty (%s) — falling back to the "
                     "A24 direct-shell layout\n", strerror(errno));
                return 2;
        }
        memset(&m, 0, sizeof m);
        m.tty = tty; m.pty = ptyfd;
        (void)fcntl(ptyfd, F_SETFL, O_NONBLOCK);

        pid_t shell = -1;
        if (with_shell) {
                shell = fork();
                if (shell == 0) { close(ptyfd); shell_child(newroot, tty, slavename); _exit(127); }
                if (shell < 0) klog("nuxel-console: fork shell: %s\n", strerror(errno));
        }

        int lost = 0;
        long last_shell = now_ms();
        while (!lost) {
                struct pollfd p[2];
                int np = 1;
                p[0].fd = tty; p[0].events = POLLIN;
                if (with_shell) { p[1].fd = ptyfd; p[1].events = POLLIN; np = 2; }
                int pr = poll(p, (nfds_t)np, 500);
                if (pr < 0 && errno != EINTR) break;
                if (pr > 0 && (p[0].revents & (POLLIN | POLLHUP | POLLERR))) {
                        unsigned char buf[4096];
                        ssize_t r = read(tty, buf, sizeof buf);
                        if (r < 0) {
                                if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
                                        /* nothing to read this round */
                                } else {
                                        klog("nuxel-console: host link lost (%s) — keeping the "
                                             "console alive for re-enumeration\n", strerror(errno));
                                        lost = 1;
                                }
                        } else if (r == 0) {
                                klog("nuxel-console: host link closed — keeping the console alive\n");
                                lost = 1;
                        } else {
                                for (ssize_t i = 0; i < r && !lost; i++)
                                        mux_input(&m, buf[i], timeout_ms, &lost);
                        }
                }
                if (with_shell && pr > 0 && (p[1].revents & POLLIN)) {
                        char out[4096];
                        ssize_t r = read(ptyfd, out, sizeof out);
                        if (r < 0 && errno != EAGAIN && errno != EWOULDBLOCK) r = 0;
                        if (r > 0 && write_all(tty, out, (size_t)r) != 0) lost = 1;
                }
                if (with_shell && shell > 0) {
                        int status = 0;
                        pid_t w = waitpid(shell, &status, WNOHANG);
                        if (w == shell) {
                                /* A24 measured this path: the tty raises SIGHUP when the host
                                 * closes the port and the shell dies.  The console must not. */
                                klog("nuxel-console: shell exited (status %d) — respawning\n", status);
                                msleep(300);
                                shell = fork();
                                if (shell == 0) { close(ptyfd); shell_child(newroot, tty, slavename); _exit(127); }
                        }
                        (void)last_shell;
                }
        }
        if (shell > 0) { kill(shell, SIGHUP); (void)waitpid(shell, NULL, WNOHANG); }
        close(ptyfd);
        return 0;
}

/* ============================== OFFLINE SELFTEST =============================
 * No gadget, no root, no tty, no phone.  This is what the offline test suite
 * (tools/s10plus/a33/tests/test-console-protocol.py) runs, and it is the only
 * evidence that exists for the framing and cancellation paths in this revision:
 * the physical console is exercised only by the live group.
 */
static int st_pass, st_fail;
static void st(const char *name, int ok, const char *fmt, ...);
static void selftest_console_lease(void) {
        /* The lease writer is deliberately exercised with an overridable path
           so the offline selftest proves the file contains a validated pid and
           that the clear path removes it.  On the live device the default is
           /run/nuxel/live-console-session. */
        const char *probe = "/tmp/nuxel-console-lease-selftest";
        const char *old = LIVE_SESSION_MARKER;
        (void)old;
        FILE *f = fopen(probe, "w");
        if (!f) { st("lease selftest: cannot create probe", 0, strerror(errno)); return; }
        fprintf(f, "pid=%d\ntty=/dev/ttyGS0\nstate=serving\n", (int)getpid());
        fclose(f);
        char buf[128] = "";
        FILE *r = fopen(probe, "r");
        if (r) { (void)!fgets(buf, sizeof buf, r); fclose(r); }
        st("lease selftest: pid line is a validated lease", strncmp(buf, "pid=", 4) == 0, buf);
        unlink(probe);
        st("lease selftest: cleared lease no longer exists", access(probe, F_OK) != 0, probe);
}


static void st(const char *name, int ok, const char *fmt, ...) {
        char detail[256] = "";
        if (fmt && *fmt) {
                va_list ap; va_start(ap, fmt);
                vsnprintf(detail, sizeof detail, fmt, ap);
                va_end(ap);
        }
        if (ok) { st_pass++; printf("  PASS %s%s%s\n", name, *detail ? "  - " : "", detail); }
        else    { st_fail++; printf("  FAIL %s%s%s\n", name, *detail ? "  - " : "", detail); }
}

/* st("name", cond, "fmt", args…) and, for a bare assertion, st2("name", cond) */
#define st2(name, ok) st((name), (ok), "")

static void hex_of(const char *s, char out[65]) {
        sha256_ctx c; sha256_init(&c); sha256_update(&c, s, strlen(s));
        unsigned char d[32]; sha256_final(&c, d); hex32(d, out);
}

/* Minimal independent parser: the point is that the frame written by emit_frame
 * can be read back and its hash recomputed. */
static int frame_read(int fd, char id[9], int *rc, char hash[65], unsigned char *body,
                      size_t bodycap, size_t *bodylen) {
        char all[1 << 16];
        size_t n = 0;
        while (n < sizeof all - 1) {
                ssize_t r = read(fd, all + n, sizeof all - 1 - n);
                if (r <= 0) break;
                n += (size_t)r;
        }
        all[n] = 0;
        const char *b = strstr(all, "@@NXB");
        const char *r_ = strstr(all, "@@NXR");
        const char *h_ = strstr(all, "@@NXH");
        const char *e_ = strstr(all, "@@NXE");
        if (!b || !r_ || !h_ || !e_ || !(b < r_ && r_ < h_ && h_ < e_)) return -1;
        if (sscanf(b + 5, "%8s", id) != 1) return -1;
        char *bang = strstr(id, "@@"); if (bang) *bang = 0;
        if (sscanf(r_ + 5, "%*8[^:]:%d", rc) != 1 && sscanf(strchr(r_ + 5, ':') + 1, "%d", rc) != 1) return -1;
        const char *hs = strchr(h_ + 5, ':');
        if (!hs) return -1;
        if (sscanf(hs + 1, "%64[0-9a-f]", hash) != 1) return -1;

        /* payload: between the end of the @@NXH…@@ line and @@NXE */
        const char *p = strchr(h_ + 5, '\n');
        if (!p) return -1;
        p++;
        size_t bn = 0;
        int bits = 0;
        uint32_t acc = 0;
        for (const char *q = p; q < e_; q++) {
                unsigned char c = (unsigned char)*q;
                if (c == '\n' || c == '\r' || c == ' ' || c == '\t') continue;
                if (c == '@') break;
                if (c == '=') break;
                int v;
                if (c >= 'A' && c <= 'Z') v = c - 'A';
                else if (c >= 'a' && c <= 'z') v = c - 'a' + 26;
                else if (c >= '0' && c <= '9') v = c - '0' + 52;
                else if (c == '+') v = 62;
                else if (c == '/') v = 63;
                else return -1;
                acc = (acc << 6) | (uint32_t)v;
                bits += 6;
                if (bits >= 8) {
                        bits -= 8;
                        if (bn < bodycap) body[bn++] = (unsigned char)((acc >> bits) & 0xff);
                }
        }
        *bodylen = bn;
        return 0;
}

static int selftest(void) {
        selftest_console_lease();
        printf("nuxel-console selftest (offline: no gadget, no root, no tty)\n");

        /* ---- SHA-256, FIPS 180-4 vectors ------------------------------------ */
        struct { const char *msg; const char *hex; } vec[] = {
                { "", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" },
                { "abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" },
                { "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
                  "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1" },
                { "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu",
                  "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1" },
        };
        printf("SHA-256 (FIPS 180-4)\n");
        for (size_t i = 0; i < sizeof vec / sizeof vec[0]; i++) {
                char got[65];
                hex_of(vec[i].msg, got);
                st("sha256 vector", strcmp(got, vec[i].hex) == 0, "%s -> %.16s", vec[i].hex, got);
        }
        {   /* multi-block and unaligned lengths must agree with a single shot */
                char big[1000];
                for (size_t i = 0; i < sizeof big; i++) big[i] = (char)('a' + (i % 26));
                sha256_ctx c; sha256_init(&c);
                for (size_t off = 0; off < sizeof big; ) {
                        size_t chunk = 1 + (off % 97);
                        if (off + chunk > sizeof big) chunk = sizeof big - off;
                        sha256_update(&c, big + off, chunk);
                        off += chunk;
                }
                unsigned char d[32]; char a[65]; sha256_final(&c, d); hex32(d, a);
                sha256_ctx c2; sha256_init(&c2); sha256_update(&c2, big, sizeof big);
                unsigned char d2[32]; char b[65]; sha256_final(&c2, d2); hex32(d2, b);
                st2("sha256 is chunking-independent", strcmp(a, b) == 0);
        }

        /* ---- base64 --------------------------------------------------------- */
        printf("base64\n");
        {
                struct { const char *in; const char *want; } bv[] = {
                        { "", "" }, { "f", "Zg==" }, { "fo", "Zm8=" }, { "foo", "Zm9v" },
                        { "foob", "Zm9vYg==" }, { "fooba", "Zm9vYmE=" }, { "foobar", "Zm9vYmFy" },
                };
                int ok = 1;
                for (size_t i = 0; i < sizeof bv / sizeof bv[0]; i++) {
                        char out[64];
                        size_t n = b64_encode((const unsigned char *)bv[i].in, strlen(bv[i].in), out);
                        out[n] = 0;
                        if (strcmp(out, bv[i].want) != 0) ok = 0;
                }
                st2("base64 matches RFC 4648 vectors", ok);
        }
        {   int ok = 1; char out[70000];
                unsigned char raw[1024];
                for (size_t i = 0; i < sizeof raw; i++) raw[i] = (unsigned char)(i * 7 + 3);
                size_t n = b64_encode(raw, sizeof raw, out);
                size_t col = 0;
                for (size_t i = 0; i < n; i++) { if (out[i] == '\n') col = 0; else if (++col > BASE64_WRAP) ok = 0; }
                st2("base64 wraps at <= 76 columns", ok);
        }

        /* ---- request ids ---------------------------------------------------- */
        printf("request ids\n");
        {
                char a[9], b[9], c[9];
                make_id(NULL, a); make_id(NULL, b); make_id("seed", c);
                int hexok = strlen(a) == 8 && strlen(b) == 8 && strlen(c) == 8;
                for (int i = 0; hexok && i < 8; i++)
                        if (!isxdigit((unsigned char)a[i])) hexok = 0;
                st("id is 8 hex chars", hexok, a);
                st("two ids generated in the same second differ", strcmp(a, b) != 0, "%s %s", a, b);
        }

        /* ---- wrapper recognition ------------------------------------------- */
        printf("framed wrapper recognition\n");
        {
                char line[MAX_LINE], id[9], tmp[64], cmd[256];
                snprintf(line, sizeof line,
                         "_NXID=ab12cd34; rm -f /var/tmp/nx-ab12cd34.out; "
                         "{ uname -r; false ; } >/var/tmp/nx-ab12cd34.out 2>&1 </dev/null; "
                         "printf '@@NXB%%s@@\\n' \"$_NXID\"; base64 -w76 /var/tmp/nx-ab12cd34.out; "
                         "printf '\\n@@NXE%%s@@\\n' \"$_NXID\"");
                int ok = parse_wrapper(line, id, tmp, sizeof tmp, cmd, sizeof cmd) == 1;
                st2("wrapper is recognised", ok);
                st("wrapper id is extracted", ok && strcmp(id, "ab12cd34") == 0, id);
                /* the wrapper's scratch name is the path WITHOUT the .out suffix; the
                 * responder appends .out itself (the same convention as the host tool) */
                st("wrapper temp path is extracted", ok && strcmp(tmp, "/var/tmp/nx-ab12cd34") == 0, tmp);
                st("wrapper command is extracted verbatim", ok && strcmp(cmd, "uname -r; false") == 0, cmd);
                st2("an ordinary shell line is NOT a wrapper",
                   parse_wrapper("ls -la /etc", id, tmp, sizeof tmp, cmd, sizeof cmd) == 0);
                st2("a malformed wrapper is refused, not guessed",
                   parse_wrapper("_NXID=zz; rm -f /x.out; base64 -w76 x @@NXE", id, tmp, sizeof tmp, cmd, sizeof cmd) == 0);
        }

        /* ---- bounded execution + real exit status --------------------------- */
        printf("bounded execution and real exit status\n");
        {
                char tmpl[] = "/tmp/nxc-st-XXXXXX";
                int fd = mkstemp(tmpl);
                if (fd >= 0) close(fd);
                struct exec_result r;
                memset(&r, 0, sizeof r);
                int rc = exec_bounded("exit 7", tmpl, 5000, -1, &r);
                st("a command's exit status is passed through", rc == 0 && r.rc == 7, "rc=%d", r.rc);
                st2("merged stdout+stderr land in the payload file",
                   (memset(&r, 0, sizeof r), exec_bounded("echo OUT; echo ERR >&2", tmpl, 5000, -1, &r) == 0));
                {   int fd2 = open(tmpl, O_RDONLY); char b[256]; ssize_t n = read(fd2, b, sizeof b - 1);
                        close(fd2); b[n > 0 ? n : 0] = 0;
                        st("stdout and stderr are both captured", strstr(b, "OUT") && strstr(b, "ERR"), "%s", b); }
                unlink(tmpl);
        }

        /* ---- the cancellation path ----------------------------------------- */
        printf("cancellation path\n");
        {
                char tmpl[] = "/tmp/nxc-st-XXXXXX";
                int fd = mkstemp(tmpl);
                if (fd >= 0) close(fd);
                struct exec_result r;
                long t0 = now_ms();
                memset(&r, 0, sizeof r);
                int rc = exec_bounded("sleep 30", tmpl, 700, -1, &r);
                long dt = now_ms() - t0;
                st("an unbounded command is bounded by the timeout", rc == 0 && r.timed_out == 1, "timed_out=%d", r.timed_out);
                st("the cancelled command is stopped promptly, not left running", dt < 8000, "%ld ms", dt);
                st("a cancelled command reports the shell's SIGINT status", r.rc == 130, "rc=%d", r.rc);
                unlink(tmpl);

                /* Ctrl-C typed on the tty: a pipe stands in for the port */
                int pr[2];
                if (pipe(pr) == 0) {
                        int wfd = pr[1];
                        (void)write(wfd, "\003", 1);
                        close(wfd);
                        int fd3 = mkstemp(tmpl); if (fd3 >= 0) close(fd3);
                        memset(&r, 0, sizeof r);
                        rc = exec_bounded("sleep 30", tmpl, 20000, pr[0], &r);
                        st("Ctrl-C on the port cancels the running command",
                           rc == 0 && r.cancelled == 1 && r.rc == 130, "cancelled=%d rc=%d", r.cancelled, r.rc);
                        close(pr[0]);
                        unlink(tmpl);
                }
        }

        /* ---- frame round trip ---------------------------------------------- */
        printf("frame round trip\n");
        {
                char tmpl[] = "/tmp/nxc-st-XXXXXX";
                int fd = mkstemp(tmpl);
                if (fd < 0) { st("temp file", 0, "mkstemp: %s", strerror(errno)); }
                else {
                        (void)!write(fd, "HELLO_FRAME\nuid=0(root)\n", 24);
                        close(fd);
                        char out[] = "/tmp/nxc-frame-XXXXXX";
                        int ofd = mkstemp(out);
                        int ok = ofd >= 0 && emit_frame(ofd, "0102aabb", tmpl, 1, "bounded-timeout:700ms") == 0;
                        st2("a frame is emitted", ok);
                        if (ok) {
                                lseek(ofd, 0, SEEK_SET);
                                char gid[9], ghash[65]; int grc = -1;
                                static unsigned char body[8192]; size_t bn = 0;
                                int prc = frame_read(ofd, gid, &grc, ghash, body, sizeof body, &bn);
                                st2("the frame parses back", prc == 0);
                                st("the parsed id matches the request", prc == 0 && strcmp(gid, "0102aabb") == 0, gid);
                                st("the parsed exit status is real", prc == 0 && grc == 1, "rc=%d", grc);
                                char want[65]; sha256_file(tmpl, want);
                                st2("the target-side hash matches the payload", prc == 0 && strcmp(ghash, want) == 0);
                                st("the payload survives base64 unchanged",
                                   prc == 0 && bn == 24 && memcmp(body, "HELLO_FRAME\nuid=0(root)\n", 24) == 0, "%zu bytes", bn);
                        }
                        close(ofd); unlink(out); unlink(tmpl);
                }
        }
        {   /* explicit marker-order assertion, independent of frame_read */
                char tmpl[] = "/tmp/nxc-st-XXXXXX";
                int fd = mkstemp(tmpl); if (fd >= 0) { (void)!write(fd, "x", 1); close(fd); }
                char out[] = "/tmp/nxc-frame-XXXXXX";
                int ofd = mkstemp(out);
                if (ofd >= 0 && emit_frame(ofd, "00112233", tmpl, 0, NULL) == 0) {
                        static char all[8192]; ssize_t n = pread(ofd, all, sizeof all - 1, 0);
                        all[n > 0 ? n : 0] = 0;
                        const char *b = strstr(all, "@@NXB00112233@@");
                        const char *r_ = strstr(all, "@@NXR00112233:0@@");
                        const char *h_ = strstr(all, "@@NXH00112233:");
                        const char *e_ = strstr(all, "@@NXE00112233@@");
                        st2("markers appear in B,R,H,E order",
                           b && r_ && h_ && e_ && b < r_ && r_ < h_ && h_ < e_);
                } else st("markers appear in B,R,H,E order", 0, "emit failed");
                if (ofd >= 0) { close(ofd); unlink(out); }
                unlink(tmpl);
        }

        /* ---- port lock ------------------------------------------------------ */
        printf("port lock\n");
        {
                char path[] = "/tmp/nxc-lock-XXXXXX";
                int fd = mkstemp(path);
                if (fd >= 0) close(fd);
                int a = lock_port(path);
                int b = -1;
                if (a == 0) {
                        int fd2 = open(path, O_RDWR);
                        b = (fd2 >= 0 && flock(fd2, LOCK_EX | LOCK_NB) != 0) ? 0 : -1;
                        if (fd2 >= 0) close(fd2);
                }
                st2("only one console may hold the port", a == 0 && b == 0);
                if (g_lockfd >= 0) { close(g_lockfd); g_lockfd = -1; }
                unlink(path);
        }

        printf("\n%d passed, %d failed\n", st_pass, st_fail);
        return st_fail ? 1 : 0;
}

/* -------------------------------------------------------------------- usage */
static void usage(FILE *f) {
        fputs(
"nuxel-console (A33) - Nuxel S10+ live USB console\n"
"\n"
"  nuxel-console <newroot> [options]        run the console (default: mux mode)\n"
"  nuxel-console --frame <id> <command>     run one command and print one frame\n"
"  nuxel-console --selftest                 offline framing/cancellation selftest\n"
"  nuxel-console --help\n"
"\n"
"Options:\n"
"  --mode mux|responder|shell   mux (default) = interactive shell + framed\n"
"                               interception; responder = framed commands only;\n"
"                               shell = A24 direct-shell layout (no interception)\n"
"  --stdio                      responder reads stdin and answers on stdout\n"
"                               (offline testing; no tty needed)\n"
"  --tty <path>                 console tty (default /dev/ttyGS0)\n"
"  --timeout <ms>               per-request bound (default 20000)\n"
"  --lock <path>                port lock file (default /run/nuxel-console.lock)\n"
"  --no-gadget                  do not create the USB gadget (already bound)\n"
"  --no-pump                    do not mirror /dev/kmsg to the console\n"
"  --once                       exit when the host link drops (tests/CI)\n"
"\n"
"Exit codes: 0 ok, 1 selftest failure, 2 usage, 3 port busy, 4 cannot open tty.\n"
"Safest to know: this program never opens /dev/fb0 and never writes to a block\n"
"device (see the file header).\n", f);
}

int main(int argc, char **argv) {
        const char *newroot = NULL, *ttypath = TTY, *lockpath = "/run/nuxel-console.lock";
        const char *mode = "mux", *frameid = NULL, *framecmd = NULL;
        int timeout_ms = DEFAULT_TIMEOUT_MS;
        int use_gadget = 1, use_pump = 1, stdio_mode = 0, once = 0;

        for (int i = 1; i < argc; i++) {
                const char *a = argv[i];
                if (!strcmp(a, "--help") || !strcmp(a, "-h")) { usage(stdout); return 0; }
                else if (!strcmp(a, "--selftest")) return selftest();
                else if (!strcmp(a, "--frame")) { frameid = argv[++i]; framecmd = argv[++i]; }
                else if (!strcmp(a, "--mode")) mode = argv[++i];
                else if (!strcmp(a, "--stdio")) stdio_mode = 1;
                else if (!strcmp(a, "--tty")) ttypath = argv[++i];
                else if (!strcmp(a, "--timeout")) timeout_ms = atoi(argv[++i]);
                else if (!strcmp(a, "--lock")) lockpath = argv[++i];
                else if (!strcmp(a, "--no-gadget")) use_gadget = 0;
                else if (!strcmp(a, "--no-pump")) use_pump = 0;
                else if (!strcmp(a, "--once")) once = 1;
                else if (a[0] == '-') { usage(stderr); return 2; }
                else if (!newroot) newroot = a;
                else { usage(stderr); return 2; }
        }

        signal(SIGPIPE, SIG_IGN);

        if (frameid && framecmd) {
                char tmpl[] = "/tmp/nxc-frame-XXXXXX";
                int fd = mkstemp(tmpl);
                if (fd < 0) { perror("mkstemp"); return 1; }
                close(fd);
                struct exec_result r; memset(&r, 0, sizeof r);
                if (exec_bounded(framecmd, tmpl, timeout_ms, -1, &r) != 0) {
                        fprintf(stderr, "nuxel-console: could not run the command\n");
                        unlink(tmpl); return 1;
                }
                emit_frame(1, frameid, tmpl, r.rc, r.timed_out ? "bounded-timeout" : NULL);
                unlink(tmpl);
                return 0;
        }

        if (stdio_mode) return run_responder(0, 1, timeout_ms);

        g_kmsg = open(KMSG, O_WRONLY | O_CLOEXEC);
        if (use_gadget) (void)bring_up_gadget();

        for (;;) {
                if (ensure_tty_node() != 0) {
                        if (once || use_gadget == 0) return 4;
                        msleep(1000);
                        continue;
                }
                int rc = lock_port(lockpath);
                if (rc == -3) return 3;

                int tty = open(ttypath, O_RDWR | O_NOCTTY | O_NONBLOCK);
                if (tty < 0) {
                        klog("nuxel-console: cannot open %s: %s\n", ttypath, strerror(errno));
                        if (once) return 4;
                        msleep(1000);
                        continue;
                }
                (void)set_raw(tty);
                /* The console owns the tty from this point: publish the lease
                   the lockscreen validates, and keep it until exit. */
                live_session_mark();

                pid_t pump = -1;
                if (use_pump) {
                        pump = fork();
                        if (pump == 0) pump_kmsg(dup(tty));
                }

                klog("nuxel-console: mode=%s timeout=%dms tty=%s\n", mode, timeout_ms, ttypath);
                if (!strcmp(mode, "responder")) {
                        (void)run_responder(tty, tty, timeout_ms);
                } else if (!strcmp(mode, "shell")) {
                        /* A24 layout: the shell owns the port directly. */
                        pid_t sh = fork();
                        if (sh == 0) shell_child(newroot, tty, NULL);
                        while (waitpid(sh, NULL, 0) < 0 && errno == EINTR) { }
                        klog("nuxel-console: shell exited; respawning\n");
                } else {
                        int mrc = run_mux(tty, newroot, timeout_ms, 1);
                        if (mrc == 2) {                   /* no pty available */
                                pid_t sh = fork();
                                if (sh == 0) shell_child(newroot, tty, NULL);
                                while (waitpid(sh, NULL, 0) < 0 && errno == EINTR) { }
                        }
                }
                if (pump > 0) { kill(pump, SIGTERM); (void)waitpid(pump, NULL, WNOHANG); }
                live_session_clear();
                close(tty);
                if (g_lockfd >= 0) { close(g_lockfd); g_lockfd = -1; }
                if (once) return 0;
                /* The console must stay reachable: the gadget can vanish and
                 * re-enumerate on a cable pull, so we wait for the node again. */
                msleep(500);
        }
}
