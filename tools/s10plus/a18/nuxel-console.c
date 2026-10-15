/* nuxel-console — live diagnostic channel for the Nuxel S10+ bring-up.
 *
 * PROBLEM (Phase 3 of the mission): the only way to read a Nuxel boot today is
 * to let it fail, get the phone back into TWRP by hand and read /proc/last_kmsg.
 *
 * SOLUTION: the Samsung Exynos 9820 kernel registers a USB device controller
 * ("10c00000.dwc3", measured live) and has CONFIG_USB_CONFIGFS=y +
 * CONFIG_USB_CONFIGFS_ACM=y.  So a CDC-ACM gadget can be created from Linux
 * userspace.  This program
 *
 *   1. binds an ACM gadget to the UDC via configfs,
 *   2. pumps the kernel ring buffer (/dev/kmsg) to /dev/ttyGS0, and
 *   3. gives the operator an INTERACTIVE ROOT SHELL on the Fedora rootfs.
 *
 * It runs from the initramfs, so it needs no rootfs modification at all.  The
 * shell gets the real Fedora root by chroot()ing through a dirfd opened before
 * switch_root: chroot() affects only this process, so PID1's switch_root is
 * unaffected and the shell survives it.
 *
 * On the MacBook the channel appears as /dev/tty.usbmodem* :
 *     screen /dev/tty.usbmodemXXXX 115200
 *
 * Usage: nuxel-console <newroot> [--no-shell|--no-pump|--no-report]
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <dirent.h>
#include <signal.h>
#include <sys/ioctl.h>

extern char **environ;

#define GADGET "/sys/kernel/config/usb_gadget/nuxel"
#define TTY    "/dev/ttyGS0"

static int kmsg = -1;

static void klog(const char *fmt, ...) {
        char buf[512];
        va_list ap; va_start(ap, fmt);
        int n = vsnprintf(buf, sizeof buf, fmt, ap);
        va_end(ap);
        if (n < 0) return;
        if (n > (int)sizeof buf - 1) n = (int)sizeof buf - 1;
        if (kmsg >= 0) (void)!write(kmsg, buf, (size_t)n);
        (void)!write(2, buf, (size_t)n);
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
        for (char *q = tmp + 1; *q; q++) {
                if (*q == '/') { *q = 0; (void)mkdir(tmp, 0755); *q = '/'; }
        }
        return mkdir(tmp, 0755);
}

/* Pick the first UDC the kernel exposes. */
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

static void pump_kmsg(int ttyfd_in) {
        /* fresh, non-blocking reader of the kernel ring buffer */
        int fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        int tfd = ttyfd_in;
        if (fd < 0) return;
        if (tfd < 0) {
                tfd = open(TTY, O_WRONLY | O_NONBLOCK | O_CLOEXEC);
                if (tfd < 0) { close(fd); return; }
        }
        static char buf[4096];
        char line[4600];
        (void)!write(tfd, "\r\nNUXEL live kernel log attached (ttyGS0)\r\n", 41);
        for (;;) {
                struct pollfd pfd = { .fd = fd, .events = POLLIN };
                ssize_t r;
                if (poll(&pfd, 1, 1000) <= 0) continue;
                r = read(fd, buf, sizeof buf - 1);
                if (r <= 0) continue;
                buf[r] = 0;
                /* /dev/kmsg gives "prio,seq,usec,flags;message" per line */
                int n = snprintf(line, sizeof line, "%s", buf);
                if (n > 0) (void)!write(tfd, line, (size_t)n);
        }
}

static void shell_child(const char *newroot, int ttyfd_in) {
        /* chroot() through a dirfd: this process only, PID1 is untouched. */
        if (chdir(newroot) != 0) { klog("nuxel-console: chdir %s: %s\n", newroot, strerror(errno)); _exit(1); }
        if (chroot(".") != 0) { klog("nuxel-console: chroot: %s\n", strerror(errno)); _exit(1); }
        if (chdir("/") != 0) _exit(1);

        int fd = ttyfd_in;
        if (fd < 0) fd = open(TTY, O_RDWR | O_CLOEXEC);
        if (fd < 0) { klog("nuxel-console: open %s in new root: %s\n", TTY, strerror(errno)); _exit(1); }

        (void)setsid();
        (void)ioctl(fd, 0x540E /* TIOCSCTTY */, 0);
        dup2(fd, 0); dup2(fd, 1); dup2(fd, 2);
        if (fd > 2) close(fd);

        setenv("TERM", "vt100", 1);
        setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
        setenv("HOME", "/root", 1);
        setenv("PS1", "nuxel-s10+ # ", 1);

        (void)!write(1, "\r\n\r\n=========================== NUXEL S10+ LIVE SHELL ===========================\r\n"
                        " You are root inside the Fedora/Nuxel rootfs, over USB (ttyGS0).\r\n"
                        " Kernel ring buffer is being streamed to this port above the prompt.\r\n"
                        " Type 'exit' to drop the channel (the boot is unaffected).\r\n"
                        "===========================================================================\r\n\r\n", 0);

        char *av[] = { (char *)"sh", (char *)"-i", NULL };
        execve("/bin/sh", av, environ);
        av[0] = (char *)"bash";
        execve("/usr/bin/bash", av, environ);
        execve("/bin/bash", av, environ);
        (void)!write(1, "nuxel-console: no /bin/sh in the new root\r\n", 43);
        _exit(127);
}


/* ---------------------------------------------------------------------------
 * Persistent boot report (A18).
 *
 * The live USB channel is the good path, but it depends on the gadget binding
 * and on the operator being at the Mac.  This child makes the *systemd verdict*
 * survive regardless: it chroots into the real Fedora root and, once systemd is
 * up, runs the state queries that answer "did A17's fix work?" and appends them
 * to a file inside the rootfs.  That file is readable from TWRP with a single
 * mount (or by the debug pack), with no dependency on USB, on journald, or on
 * any service having succeeded.
 *
 * It is a forked child, so it cannot delay or fail the boot.
 */
static const char *REPORT_SCRIPT =
    "mkdir -p /var/log 2>/dev/null\n"
    "R=/var/log/nuxel-bootreport.txt\n"
    "{\n"
    "  echo \"=== nuxel boot report ===\"\n"
    "  echo \"cmdline: $(cat /proc/cmdline 2>/dev/null)\"\n"
    "  echo \"kernel:  $(cat /proc/version 2>/dev/null)\"\n"
    "  echo \"start:   uptime=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)s\"\n"
    "} >>$R 2>&1\n"
    "i=0\n"
    "while [ $i -lt 30 ]; do\n"
    "  i=$((i+1))\n"
    "  sleep 5\n"
    "  if [ -d /run/systemd/system ]; then\n"
    "    {\n"
    "      echo \"--- t=$((i*5))s uptime=$(cut -d' ' -f1 /proc/uptime 2>/dev/null)s\"\n"
    "      echo \"is-system-running: $(systemctl is-system-running 2>&1)\"\n"
    "      echo \"--- failed units ---\"\n"
    "      systemctl --failed --no-pager 2>&1 | head -40\n"
    "      echo \"--- running services ---\"\n"
    "      systemctl list-units --type=service --state=running --no-pager 2>&1 | head -30\n"
    "      echo \"--- recent warnings ---\"\n"
    "      journalctl -b -p warning --no-pager 2>&1 | tail -60\n"
    "      echo \"--- spawn failures seen this boot ---\"\n"
    "      journalctl -b --no-pager 2>&1 | grep -c 'Failed to spawn executor' 2>/dev/null\n"
    "      echo \"--- cgroup ---\"\n"
    "      echo \"controllers: $(cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null)\"\n"
    "      echo \"self: $(cat /proc/self/cgroup 2>/dev/null)\"\n"
    "      echo \"--- state files ---\"\n"
    "      cat /var/lib/nuxel/boot-stage /var/lib/nuxel/animation 2>/dev/null\n"
    "    } >>$R 2>&1\n"
    "    break\n"
    "  fi\n"
    "done\n"
    "echo \"=== live shell still available on ttyGS0 (if the gadget bound) ===\" >>$R 2>&1\n"
    "if [ -x /opt/nuxel/nuxel-hwprobe ]; then /opt/nuxel/nuxel-hwprobe >>$R 2>&1; fi\n"
    "echo \"=== end report ===\" >>$R 2>&1\n";

static void report_child(const char *newroot) {
        if (chdir(newroot) != 0 || chroot(".") != 0 || chdir("/") != 0) _exit(1);
        (void)setsid();
        int devnull = open("/dev/null", O_RDWR | O_CLOEXEC);
        if (devnull >= 0) { dup2(devnull, 0); }
        setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
        char *av[] = { (char *)"sh", (char *)"-c", (char *)REPORT_SCRIPT, NULL };
        execve("/bin/sh", av, environ);
        execve("/usr/bin/bash", av, environ);
        _exit(127);
}

int main(int argc, char **argv) {
        const char *newroot = argc > 1 ? argv[1] : "/newroot";
        int want_shell = 1, want_pump = 1, want_report = 1;
        for (int i = 2; i < argc; i++) {
                if (!strcmp(argv[i], "--no-shell"))  want_shell = 0;
                if (!strcmp(argv[i], "--no-pump"))   want_pump  = 0;
                if (!strcmp(argv[i], "--no-report")) want_report = 0;
        }
        kmsg = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);

        klog("nuxel-console: starting (newroot=%s)\n", newroot);

        /* Start the persistent reporter FIRST: it must survive a failed gadget
         * bind, a missing UDC and a broken tty.  It only needs the new root. */
        if (want_report) {
                pid_t p = fork();
                if (p == 0) report_child(newroot);
                klog("nuxel-console: rootfs boot reporter pid=%d -> /var/log/nuxel-bootreport.txt\n", (int)p);
        }

        if (mount("none", "/sys/kernel/config", "configfs", 0, NULL) < 0 && errno != EBUSY)
                klog("nuxel-console: configfs mount: %s (continuing)\n", strerror(errno));

        char udc[128];
        if (udc_name(udc, sizeof udc) != 0) {
                klog("nuxel-console: NO UDC in /sys/class/udc - live channel unavailable\n");
                return 1;
        }
        klog("nuxel-console: UDC=%s\n", udc);

        if (mkdir_p(GADGET) != 0 && errno != EEXIST)
                klog("nuxel-console: mkdir %s: %s\n", GADGET, strerror(errno));

        wfile(GADGET "/idVendor",  "0x18d1");   /* Google */
        wfile(GADGET "/idProduct", "0x4ee7");   /* Nexus/Pixel-style debug gadget */
        wfile(GADGET "/bcdDevice", "0x0100");
        wfile(GADGET "/bcdUSB",    "0x0200");

        mkdir_p(GADGET "/strings/0x409");
        wfile(GADGET "/strings/0x409/serialnumber", "NUXEL-S10PLUS-0001");
        wfile(GADGET "/strings/0x409/manufacturer", "Nuxel");
        wfile(GADGET "/strings/0x409/product",      "Nuxel S10+ Live Console");

        mkdir_p(GADGET "/configs/c.1");
        mkdir_p(GADGET "/configs/c.1/strings/0x409");
        wfile(GADGET "/configs/c.1/strings/0x409/configuration", "Nuxel serial console");
        wfile(GADGET "/configs/c.1/MaxPower", "250");

        mkdir_p(GADGET "/functions/acm.usb0");
        if (symlink(GADGET "/functions/acm.usb0", GADGET "/configs/c.1/acm.usb0") != 0 && errno != EEXIST)
                klog("nuxel-console: symlink acm function: %s\n", strerror(errno));

        if (wfile(GADGET "/UDC", "%s", udc) != 0) {
                klog("nuxel-console: BIND FAILED (%s) - controller not in device mode?\n", strerror(errno));
                return 1;
        }
        klog("nuxel-console: ACM gadget BOUND to %s; waiting for %s\n", udc, TTY);

        int ttyfd = -1;
        for (int i = 0; i < 60; i++) {          /* up to ~6 s */
                ttyfd = open(TTY, O_RDWR | O_NONBLOCK | O_CLOEXEC);
                if (ttyfd >= 0) break;
                usleep(100000);
        }
        if (ttyfd < 0) {
                klog("nuxel-console: %s did not appear (%s)\n", TTY, strerror(errno));
                return 1;
        }
        /* keep a blocking-ish duplicate policy: O_NONBLOCK off for the shell tty */
        int fl = fcntl(ttyfd, F_GETFL); if (fl >= 0) (void)fcntl(ttyfd, F_SETFL, fl & ~O_NONBLOCK);
        klog("nuxel-console: %s ready - live channel UP\n", TTY);

        if (want_pump) {
                pid_t p = fork();
                if (p == 0) { pump_kmsg(-1); _exit(0); }
        }
        if (want_shell) {
                pid_t p = fork();
                if (p == 0) shell_child(newroot, ttyfd);
                klog("nuxel-console: live shell pid=%d on %s\n", (int)p, TTY);
        }
        return 0;
}
