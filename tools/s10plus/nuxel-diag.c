/* nuxel-diag — S10+ (beyond2lte) hardware diagnostic for the Nuxel bring-up.
 *
 * Built static (glibc) for aarch64 so it can run from the initramfs *before*
 * switch_root, with no dependency on the old root remaining mounted after
 * switch_root (toybox's switch_root wipes it).
 *
 * Subcommands
 *   spawn        syscall / process-spawn availability probe; full /proc/cmdline
 *   fb           framebuffer (fbdev) probe + Nuxel first-light pattern
 *   fedora-exec  chroot /newroot and run Fedora's /bin/sh (proof a Fedora
 *                child process executes on this kernel), writing through an
 *                inherited /dev/kmsg fd
 *   sentinel N   background supervisor: keeps the softdog fed through a held
 *                fd, logs a heartbeat + process census every 10 s for N
 *                seconds.  It NEVER reboots: the ram console keeps the log
 *                across a reboot, so evidence survives without a self-reset.
 *
 * Every result is written to /dev/kmsg (the only console-independent channel
 * measured to work on this handset: /dev/console is ENODEV) under the
 * "nuxel-diag:" prefix.
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/fb.h>
#include <signal.h>
#include <spawn.h>
#include <sched.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

static int g_kmsg = -1;

static void klog(const char *fmt, ...) {
        char buf[1024];
        int n;
        va_list ap;
        va_start(ap, fmt);
        n = vsnprintf(buf, sizeof buf - 2, fmt, ap);
        va_end(ap);
        if (n < 0) return;
        if (n > (int)sizeof buf - 3) n = sizeof buf - 3;
        buf[n++] = '\n';
        buf[n] = 0;
        if (g_kmsg >= 0) { ssize_t w = write(g_kmsg, buf, n); (void)w; }
        fputs(buf, stderr);
}

static void kmsg_open(void) {
        g_kmsg = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
        if (g_kmsg < 0) g_kmsg = open("/dev/console", O_WRONLY | O_CLOEXEC);
}

/* keep a /dev/kmsg fd at 9 for children that run after /dev is moved */
static void kmsg_handoff_fd(void) {
        int f = open("/dev/kmsg", O_WRONLY); /* NOT cloexec: meant to be inherited */
        if (f >= 0) { if (f != 9) { dup2(f, 9); close(f); } }
        else klog("nuxel-diag: could not open /dev/kmsg for fd 9 (errno=%d)", errno);
}

static const char *en(int e) { return strerror(e); }

static int readfile(const char *p, char *b, size_t n) {
        int fd = open(p, O_RDONLY);
        ssize_t r;
        if (fd < 0) return -errno;
        r = read(fd, b, n - 1);
        close(fd);
        if (r < 0) return -errno;
        b[r] = 0;
        return (int)r;
}

static void log_cmdline(void) {
        char b[2048];
        int r = readfile("/proc/cmdline", b, sizeof b);
        if (r < 0) { klog("cmdline: unreadable errno=%d (%s)", -r, en(-r)); return; }
        size_t len = strlen(b);
        while (len && (b[len-1] == '\n' || b[len-1] == '\r')) b[--len] = 0;
        klog("cmdline_len=%zu", len);
        for (size_t off = 0; off < len; off += 200) {
                char chunk[201];
                size_t take = len - off > 200 ? 200 : len - off;
                memcpy(chunk, b + off, take);
                chunk[take] = 0;
                klog("cmdline[%03zu]=%s", off, chunk);
        }
        klog("cmdline token 'ro'=%s 'rw'=%s",
             strstr(b, " ro ") || strstr(b, " ro") == b ? "yes" : "no",
             strstr(b, " rw ") ? "yes" : "no");
}

static void log_paths(void) {
        static const char *p[] = {
                "/proc/device-tree", "/proc/device-tree/model",
                "/sys/firmware/devicetree", "/sys/firmware/devicetree/base",
                "/sys/firmware/devicetree/base/model",
                "/dev/fb0", "/dev/graphics/fb0", "/dev/dri", "/dev/watchdog",
                "/sys/class/graphics", "/sys/class/block", "/sys/fs/cgroup",
                "/newroot", "/newroot/usr/lib/os-release", "/newroot/etc/os-release",
                "/newroot/sbin/init", "/newroot/bin/sh",
        };
        char b[256];
        for (size_t i = 0; i < sizeof p / sizeof *p; i++) {
                struct stat st;
                int r = stat(p[i], &st);
                if (r < 0) { klog("path %-42s MISSING errno=%d", p[i], errno); continue; }
                klog("path %-42s %s size=%lld", p[i],
                     S_ISDIR(st.st_mode) ? "dir" : S_ISCHR(st.st_mode) ? "chr" :
                     S_ISBLK(st.st_mode) ? "blk" : S_ISLNK(st.st_mode) ? "lnk" :
                     S_ISREG(st.st_mode) ? "reg" : "other", (long long)st.st_size);
        }
        int r = readfile("/sys/firmware/devicetree/base/model", b, sizeof b);
        if (r > 0) klog("dt model: %s", b);
        r = readfile("/newroot/usr/lib/os-release", b, sizeof b);
        if (r > 0) {
                char *nl = strchr(b, '\n'); if (nl) *nl = 0;
                klog("rootfs /usr/lib/os-release: %s", b);
        } else klog("rootfs /usr/lib/os-release: unreadable errno=%d", -r);
}

/* ---------- syscall + spawn probes ---------------------------------------- */

static void report_spawn(const char *what, int rc) {
        /* posix_spawn-family returns the errno itself; *at/syscall return -1 */
        if (rc == 0) klog("PROBE %-28s rc=0 OK", what);
        else klog("PROBE %-28s rc=%d errno=%d (%s)", what, rc, rc, en(rc));
}

static void probe_spawn(void) {
        char *argv[] = { "/bin/sh", "-c", "exit 0", NULL };

        /* 1. clone3 availability (args=NULL,size=0 => ENOSYS on <5.3, EINVAL on >=5.3) */
        errno = 0;
        long r = syscall(435 /*clone3*/, NULL, (size_t)0);
        klog("PROBE clone3(NULL,0)                 rc=%ld errno=%d (%s)", r, errno, en(errno));

        /* 2. waitid(P_PIDFD) -- exactly what glibc's pidfd_spawn() gates on */
        errno = 0;
        r = syscall(__NR_waitid, 3 /*P_PIDFD*/, (id_t)INT_MAX, NULL, 5 /*WEXITED|WNOHANG*/, NULL);
        klog("PROBE waitid(P_PIDFD,INT_MAX)        rc=%ld errno=%d (%s) -> pidfd support %s",
             r, errno, en(errno), (errno == EBADF) ? "YES" : "NO");

        /* 3. pidfd_open */
#ifdef __NR_pidfd_open
        errno = 0;
        r = syscall(__NR_pidfd_open, getpid(), 0);
        klog("PROBE pidfd_open(self)               rc=%ld errno=%d (%s)", r, errno, en(errno));
        if (r >= 0) close((int)r);
#else
        klog("PROBE pidfd_open                     not declared by this libc");
#endif

        /* 4. memfd_create (systemd serializes the executor state through it) */
#ifdef __NR_memfd_create
        errno = 0;
        r = syscall(__NR_memfd_create, "nuxel-probe", 1 /*MFD_CLOEXEC*/);
        klog("PROBE memfd_create                   rc=%ld errno=%d (%s)", r, errno, en(errno));
        if (r >= 0) close((int)r);
#endif

        /* 5. close_range (systemd closes fds before exec) */
#ifdef __NR_close_range
        errno = 0;
        r = syscall(__NR_close_range, 1000u, 1100u, 0u);
        klog("PROBE close_range(1000,1100,0)       rc=%ld errno=%d (%s)", r, errno, en(errno));
#endif

        /* 6. glibc pidfd_spawn -- the exact call systemd 258 uses */
#if defined(__GLIBC__) && (__GLIBC__ > 2 || (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 39))
        {
                int pfd = -1;
                int rc = pidfd_spawn(&pfd, "/bin/sh", NULL, NULL, argv, environ);
                klog("PROBE pidfd_spawn(/bin/sh)           rc=%d (%s)%s", rc, en(rc),
                     rc == 0 ? " -- spawned, reaping" : "");
                if (rc == 0) { int st = 0; waitpid(pfd, &st, 0); close(pfd); }
        }
#else
        klog("PROBE pidfd_spawn                    not declared by this libc");
#endif

        /* 7. plain posix_spawn -- the fallback path the patch selects */
        {
                pid_t pid = -1;
                int rc = posix_spawn(&pid, "/bin/sh", NULL, NULL, argv, environ);
                if (rc == 0) {
                        int st = 0;
                        waitpid(pid, &st, 0);
                        klog("PROBE posix_spawn(plain,/bin/sh)     rc=0 pid=%d exit=%d OK", pid,
                             WIFEXITED(st) ? WEXITSTATUS(st) : -1);
                } else report_spawn("posix_spawn(plain,/bin/sh)", rc);
        }

        /* 8. posix_spawn with POSIX_SPAWN_SETCGROUP (clone3/CLONE_INTO_CGROUP path) */
#ifdef POSIX_SPAWN_SETCGROUP
        {
                posix_spawnattr_t a;
                pid_t pid = -1;
                int rc;
                int cfd = open("/sys/fs/cgroup", O_PATH | O_DIRECTORY | O_CLOEXEC);
                if (cfd < 0) klog("PROBE posix_spawn(SETCGROUP)         skipped: no /sys/fs/cgroup (errno=%d)", errno);
                else {
                        rc = posix_spawnattr_init(&a);
                        if (rc == 0) {
                                rc = posix_spawnattr_setcgroup_np(&a, cfd);
                                if (rc == 0) {
                                        rc = posix_spawnattr_setflags(&a, POSIX_SPAWN_SETCGROUP);
                                        if (rc == 0) {
                                                rc = posix_spawn(&pid, "/bin/sh", NULL, &a, argv, environ);
                                                if (rc == 0) {
                                                        int st = 0;
                                                        waitpid(pid, &st, 0);
                                                        klog("PROBE posix_spawn(SETCGROUP)         rc=0 pid=%d exit=%d OK", pid,
                                                             WIFEXITED(st) ? WEXITSTATUS(st) : -1);
                                                } else report_spawn("posix_spawn(SETCGROUP)", rc);
                                        } else report_spawn("spawnattr_setflags(SETCGROUP)", rc);
                                } else klog("PROBE posix_spawnattr_setcgroup_np   rc=%d (%s)", rc, en(rc));
                        }
                        close(cfd);
                }
        }
#endif

        /* 9. fork() + execve() -- the classic path, must work everywhere */
        {
                pid_t pid = fork();
                if (pid == 0) { execl("/bin/sh", "sh", "-c", "exit 0", (char *)NULL); _exit(127); }
                if (pid < 0) klog("PROBE fork+execve                    fork errno=%d (%s)", errno, en(errno));
                else {
                        int st = 0;
                        waitpid(pid, &st, 0);
                        klog("PROBE fork+execve(/bin/sh)           rc=0 pid=%d exit=%d OK", pid,
                             WIFEXITED(st) ? WEXITSTATUS(st) : -1);
                }
        }
}

/* ---------- framebuffer first light --------------------------------------- */

static int find_fb(const char **via) {
        static const char *c[] = { "/dev/fb0", "/dev/graphics/fb0" };
        for (size_t i = 0; i < sizeof c / sizeof *c; i++) {
                struct stat st;
                if (stat(c[i], &st) == 0 && S_ISCHR(st.st_mode)) { *via = c[i]; return 0; }
        }
        *via = NULL;
        return -1;
}

static void fb_log_sysfs(void) {
        DIR *d = opendir("/sys/class/graphics");
        struct dirent *de;
        char b[256];
        if (!d) { klog("fb: /sys/class/graphics unreadable errno=%d", errno); return; }
        while ((de = readdir(d))) {
                if (de->d_name[0] == '.') continue;
                if (!strncmp(de->d_name, "fb", 2)) {
                        char p[256]; int r;
                        snprintf(p, sizeof p, "/sys/class/graphics/%s/name", de->d_name);
                        r = readfile(p, b, sizeof b);
                        klog("fb: sysfs %s name=%s", de->d_name, r > 0 ? b : "<unreadable>");
                        snprintf(p, sizeof p, "/sys/class/graphics/%s/virtual_size", de->d_name);
                        r = readfile(p, b, sizeof b);
                        if (r > 0) klog("fb: sysfs %s virtual_size=%s", de->d_name, b);
                        snprintf(p, sizeof p, "/sys/class/graphics/%s/stride", de->d_name);
                        r = readfile(p, b, sizeof b);
                        if (r > 0) klog("fb: sysfs %s stride=%s", de->d_name, b);
                        snprintf(p, sizeof p, "/sys/class/graphics/%s/bits_per_pixel", de->d_name);
                        r = readfile(p, b, sizeof b);
                        if (r > 0) klog("fb: sysfs %s bpp=%s", de->d_name, b);
                } else
                        klog("fb: sysfs node %s", de->d_name);
        }
        closedir(d);
}

static unsigned int pack_px(unsigned bpp, unsigned char r, unsigned char g, unsigned char b) {
        switch (bpp) {
        case 16: return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
        case 24: return ((unsigned)r << 16) | ((unsigned)g << 8) | b;
        case 32: return ((unsigned)r << 16) | ((unsigned)g << 8) | b;
        default: return 0;
        }
}

static void put_px(unsigned char *base, unsigned bpp, unsigned x, unsigned y, unsigned stride,
                   unsigned char r, unsigned char g, unsigned char b) {
        unsigned px = pack_px(bpp, r, g, b);
        unsigned char *p = base + (size_t)y * stride + (size_t)x * ((bpp == 16) ? 2 : (bpp == 24 ? 3 : 4));
        if (bpp == 16) { *(unsigned short *)p = (unsigned short)px; }
        else if (bpp == 24) { p[0] = px & 0xff; p[1] = (px >> 8) & 0xff; p[2] = (px >> 16) & 0xff; }
        else { *(unsigned int *)p = px; }
}

/* Paint a distinctive Nuxel pattern: red / navy / green / white vertical bands
 * with a black bar, plus a white border.  Anything visible on the AMOLED proves
 * an fbdev scanout path; the band order identifies the bpp/geometry mapping. */
static int fb_first_light(void) {
        const char *via = NULL;
        struct fb_var_screeninfo vi;
        struct fb_fix_screeninfo fi;
        unsigned char *map;
        size_t maplen;
        int fd;

        if (find_fb(&via) < 0) { klog("FB_RESULT no_framebuffer_node (/dev/fb0, /dev/graphics/fb0 absent)"); return 1; }
        fd = open(via, O_RDWR);
        if (fd < 0) { klog("FB_RESULT open(%s) failed errno=%d (%s)", via, errno, en(errno)); return 1; }
        memset(&vi, 0, sizeof vi);
        memset(&fi, 0, sizeof fi);
        if (ioctl(fd, FBIOGET_VSCREENINFO, &vi) < 0) klog("fb: FBIOGET_VSCREENINFO errno=%d (%s)", errno, en(errno));
        else klog("fb: %s vsc xres=%u yres=%u xres_virtual=%u yres_virtual=%u bpp=%u line_length=%u rotate=%u",
                  via, vi.xres, vi.yres, vi.xres_virtual, vi.yres_virtual, vi.bits_per_pixel, vi.line_length, vi.rotate);
        if (ioctl(fd, FBIOGET_FSCREENINFO, &fi) < 0) klog("fb: FBIOGET_FSCREENINFO errno=%d (%s)", errno, en(errno));
        else klog("fb: %s fsc id=%s smem_len=%u line_length=%u type=%u visual=%u",
                  via, fi.id, fi.smem_len, fi.line_length, fi.type, fi.visual);
        if (ioctl(fd, FBIOBLANK, 0 /*FB_BLANK_UNBLANK*/) < 0) klog("fb: FBIOBLANK(0) errno=%d (%s)", errno, en(errno));
        else klog("fb: FBIOBLANK(0) ok (panel unblanked)");

        unsigned bpp = vi.bits_per_pixel ? vi.bits_per_pixel : 32;
        unsigned stride = fi.line_length ? fi.line_length : (vi.xres_virtual * bpp / 8);
        unsigned w = vi.xres ? vi.xres : 1440, h = vi.yres ? vi.yres : 3040;
        maplen = (size_t)stride * (vi.yres_virtual ? vi.yres_virtual : h);
        map = mmap(NULL, maplen, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (map == MAP_FAILED) {
                klog("fb: mmap(%zu) failed errno=%d (%s) -- falling back to write()", maplen, errno, en(errno));
                unsigned px = pack_px(16, 0x0a, 0x16, 0x28);
                unsigned char line[8192];
                size_t i, written = 0;
                for (i = 0; i + 4 <= sizeof line; i += 4) { memcpy(line + i, &px, 2); memcpy(line + i + 2, &px, 2); }
                for (i = 0; i < (size_t)w * h * 2 / 4; i++) { ssize_t wr = write(fd, line, sizeof line); if (wr <= 0) break; written += wr; }
                klog("FB_RESULT pattern_write bytes=%zu (write path)", written);
                close(fd);
                return written ? 0 : 1;
        }
        /* bands: 0-14% red, 14-40% navy, 40-66% green, 66-92% white, 92-100% black */
        for (unsigned y = 0; y < h; y++) {
                unsigned char r, g, b;
                unsigned pct = (unsigned)((unsigned long)y * 100 / h);
                if (pct < 14) { r = 0xc0; g = 0x10; b = 0x10; }
                else if (pct < 40) { r = 0x0a; g = 0x16; b = 0x28; }
                else if (pct < 66) { r = 0x10; g = 0xc0; b = 0x30; }
                else if (pct < 92) { r = 0xe8; g = 0xe8; b = 0xe8; }
                else { r = 0x00; g = 0x00; b = 0x00; }
                for (unsigned x = 0; x < w; x++) put_px(map, bpp, x, y, stride, r, g, b);
        }
        msync(map, maplen, MS_SYNC);
        munmap(map, maplen);
        close(fd);
        klog("FB_RESULT painted %ux%u bpp=%u stride=%u bytes=%zu -> bands RED/NAVY/GREEN/WHITE/BLACK",
             w, h, bpp, stride, maplen);
        klog("FB_RESULT FIRSTLIGHT_EXECUTED");
        return 0;
}

/* ---------- Fedora child process proof ------------------------------------ */

static int fedora_exec(void) {
        char *argv[] = { "/bin/sh", "-c",
                "printf 'nuxel-child: FEDORA_CHILD_EXECUTED pid=%d comm=sh\\n' $$ >&9; "
                "id -u > /nuxel-exec-proof.txt 2>&1; "
                "uname -m >> /nuxel-exec-proof.txt 2>&1; "
                "printf 'nuxel-child: fedora /bin/sh + coreutils ran\\n' >&9; exit 7", NULL };
        pid_t pid;
        int st = 0;
        kmsg_handoff_fd();

        if (chroot("/newroot") < 0) { klog("FEDORA_EXEC chroot(/newroot) failed errno=%d (%s)", errno, en(errno)); return 1; }
        if (chdir("/") < 0) { klog("FEDORA_EXEC chdir(/) failed errno=%d (%s)", errno, en(errno)); return 1; }
        pid = fork();
        if (pid < 0) { klog("FEDORA_EXEC fork failed errno=%d (%s)", errno, en(errno)); return 1; }
        if (pid == 0) {
                execve("/bin/sh", argv, environ);
                int e = errno;
                char m[256];
                int n = snprintf(m, sizeof m, "<3>nuxel-diag: FEDORA_EXEC execve(/bin/sh) failed errno=%d (%s)\n", e, en(e));
                if (write(9, m, n) < 0) write(2, m, n);
                _exit(127);
        }
        if (waitpid(pid, &st, 0) < 0) { klog("FEDORA_EXEC waitpid failed errno=%d", errno); return 1; }
        if (WIFEXITED(st) && WEXITSTATUS(st) == 7) {
                klog("FEDORA_EXEC_RESULT OK: Fedora /bin/sh ran inside /newroot (exit 7 as instructed)");
                return 0;
        }
        klog("FEDORA_EXEC_RESULT exit=%d signal=%d (7 expected)", WIFEXITED(st) ? WEXITSTATUS(st) : -1,
             WIFSIGNALED(st) ? WTERMSIG(st) : 0);
        return 1;
}

/* ---------- sentinel: feed the softdog + census, never reboot -------------- */

static void census(int procfd, int commfd, int seconds) {
        char b[64];
        ssize_t r;
        static char names[24][32];

        if (lseek(commfd, 0, SEEK_SET) >= 0) {
                r = read(commfd, b, sizeof b - 1);
                if (r > 0) { b[r] = 0; char *nl = strchr(b, '\n'); if (nl) *nl = 0; }
                else strcpy(b, "?");
        } else strcpy(b, "?");
        klog("census t=%ds pid1_comm=%s", seconds, b);

        int dfd = dup(procfd);
        if (dfd < 0) { klog("census: dup(/proc) failed errno=%d", errno); return; }
        DIR *d = fdopendir(dfd);
        if (!d) { close(dfd); klog("census: fdopendir failed errno=%d", errno); return; }
        int n = 0, shown = 0;
        char line[512]; size_t off = 0;
        line[0] = 0;
        struct dirent *de;
        while ((de = readdir(d))) {
                if (!isdigit((unsigned char)de->d_name[0])) continue;
                n++;
                if (shown < 12) {
                        char p[64]; int fd2; ssize_t rr;
                        snprintf(p, sizeof p, "%s/comm", de->d_name);
                        fd2 = openat(procfd, p, O_RDONLY | O_CLOEXEC);
                        if (fd2 >= 0) {
                                rr = read(fd2, names[shown], sizeof names[shown] - 1);
                                close(fd2);
                                if (rr > 0) {
                                        names[shown][rr] = 0;
                                        char *nl = strchr(names[shown], '\n'); if (nl) *nl = 0;
                                        off += (size_t)snprintf(line + off, sizeof line - off, "%s:%s ",
                                                               de->d_name, names[shown]);
                                        shown++;
                                }
                        }
                }
        }
        closedir(d);
        klog("census t=%ds processes=%d sample=[%s]", seconds, n, line);
}

static int sentinel(int seconds) {
        int wfd = open("/dev/watchdog", O_WRONLY | O_CLOEXEC);
        int procfd = open("/proc", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
        int commfd = open("/proc/1/comm", O_RDONLY | O_CLOEXEC);
        klog("sentinel: start seconds=%d watchdog_fd=%d proc_fd=%d comm_fd=%d", seconds, wfd, procfd, commfd);
        for (int t = 0; t <= seconds; t += 2) {
                if (wfd >= 0) {
                        ssize_t w = write(wfd, "x", 1);
                        if (w < 0 && t) { klog("sentinel: softdog feed failed errno=%d (%s) -- stopping feed", errno, en(errno)); close(wfd); wfd = -1; }
                }
                if (t % 10 == 0) census(procfd, commfd, t);
                sleep(2);
        }
        klog("sentinel: done after %ds (no reboot performed; evidence stays in the ram console)", seconds);
        return 0;
}

static void usage(void) {
        fprintf(stderr, "usage: nuxel-diag spawn|fb|fedora-exec|sentinel N|all\n");
}

int main(int argc, char **argv) {
        kmsg_open();
        setvbuf(stdout, NULL, _IONBF, 0);
        setvbuf(stderr, NULL, _IONBF, 0);
        if (argc < 2) { usage(); return 2; }
        klog("nuxel-diag: start cmd=%s pid=%d", argv[1], (int)getpid());

        if (!strcmp(argv[1], "spawn")) {
                log_cmdline(); log_paths(); probe_spawn();
        } else if (!strcmp(argv[1], "fb")) {
                fb_log_sysfs(); return fb_first_light();
        } else if (!strcmp(argv[1], "fb-sysfs")) {
                fb_log_sysfs();
        } else if (!strcmp(argv[1], "fedora-exec")) {
                return fedora_exec();
        } else if (!strcmp(argv[1], "sentinel")) {
                return sentinel(argc > 2 ? atoi(argv[2]) : 300);
        } else if (!strcmp(argv[1], "all")) {
                log_cmdline(); log_paths(); probe_spawn(); fb_log_sysfs(); fb_first_light();
        } else { usage(); return 2; }
        klog("nuxel-diag: done cmd=%s", argv[1]);
        return 0;
}
