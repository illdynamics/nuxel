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
#include <sys/wait.h>
#include <sys/ioctl.h>
#include <sys/sysmacros.h>

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
        const char hb0[] = "\r\nNUXEL live kernel log attached (ttyGS0) -- type 'help'? just type.\r\n";
        (void)!write(tfd, hb0, sizeof hb0 - 1);
        int idle = 0;
        for (;;) {
                struct pollfd pfd = { .fd = fd, .events = POLLIN };
                ssize_t r;
                if (poll(&pfd, 1, 1000) <= 0) {
                        /* A19: a heartbeat every 10 s proves the direction
                         * device->host works even when the console is idle, so a
                         * silent console is instantly distinguishable from a
                         * console whose writes never leave the gadget. */
                        if (++idle >= 10) {
                                idle = 0;
                                const char hb[] = "\r\nNUXEL-CONSOLE heartbeat (device->host OK)\r\n";
                                (void)!write(tfd, hb, sizeof hb - 1);
                        }
                        continue;
                }
                idle = 0;
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

        /* Open our own handle first (belt and braces, and it proves the node is
         * visible from inside the chroot); fall back to the inherited fd. */
        int fd = open(TTY, O_RDWR);
        if (fd < 0) {
                klog("nuxel-console: shell could not open %s inside the new root "
                     "(%s); using the inherited fd\n", TTY, strerror(errno));
                fd = ttyfd_in;
        }
        if (fd < 0) { klog("nuxel-console: shell has no tty at all\n"); _exit(1); }
        klog("nuxel-console: shell tty fd=%d (own_open=%d)\n", fd, ttyfd_in);

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

        /* A24: the ACM tty raises SIGHUP to the foreground process group when the
         * HOST closes the port (unplug, or any program closing the fd).  A23
         * measured the consequence: the shell died permanently and the only way
         * back was a manual power cycle -- the live channel must never be
         * single-use.  An IGNORED signal disposition survives execve (a handler
         * does not), so the shell is re-exec'd through a one-line sh that ignores
         * SIGHUP first.  The supervisor in main() respawns it even if it dies. */
        char *av[] = { (char *)"sh", (char *)"-c",
                       (char *)"trap '' HUP; exec /bin/sh -i", NULL };
        execve("/bin/sh", av, environ);
        char *av2[] = { (char *)"bash", (char *)"-i", NULL };
        execve("/usr/bin/bash", av2, environ);
        execve("/bin/bash", av2, environ);
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
/* ---------------------------------------------------------------------------
 * /dev/ttyGS0 does not exist until userspace makes it.
 *
 * Measured in the A18 ram console: the ACM gadget bound successfully and macOS
 * enumerated "Nuxel S10+ Live Console", yet nuxel-console could not open the
 * serial function and gave up with
 *     nuxel-console: /dev/ttyGS0 did not appear (No such file or directory)
 *
 * Cause, from the kernel source this device runs (Samsung 4.14.253):
 *   f_acm.c: acm_alloc_instance() -> gserial_alloc_line()
 *   u_serial.c:1496: tty_port_register_device(...);
 *     (its own comment there reads: "... and sysfs class devices, so mdev/udev
 *      make /dev/ttyGS*")
 * The kernel registers the tty in sysfs and expects userspace (Android ueventd
 * there, mdev/udev here) to create the node.  A Nuxel initramfs runs neither, so
 * the node never exists -- the driver is fine.
 *
 * Fix: read the major:minor the kernel published at /sys/class/tty/ttyGS0/dev and
 * mknod it ourselves.  Poll for the sysfs entry first, because it only appears
 * when the function instance is created (i.e. when functions/acm.usb0 is mkdir'd).
 */
static int ensure_tty_node(void) {
        static const char sysdev[] = "/sys/class/tty/ttyGS0/dev";
        char buf[64];
        int i, fd;
        struct stat st;

        for (i = 0; i < 60; i++) {                 /* up to ~30 s */
                if (stat(TTY, &st) == 0 && S_ISCHR(st.st_mode)) {
                        klog("nuxel-console: %s exists (maj:min %u:%u)\n", TTY,
                             (unsigned)major(st.st_rdev), (unsigned)minor(st.st_rdev));
                        return 0;
                }
                fd = open(sysdev, O_RDONLY | O_CLOEXEC);
                if (fd >= 0) {
                        ssize_t n = read(fd, buf, sizeof buf - 1);
                        close(fd);
                        if (n > 0) {
                                unsigned maj = 0, min = 0;
                                buf[n] = 0;
                                if (sscanf(buf, "%u:%u", &maj, &min) == 2) {
                                        if (mknod(TTY, S_IFCHR | 0666,
                                                  makedev((int)maj, (int)min)) == 0 || errno == EEXIST) {
                                                klog("nuxel-console: created %s from %s (%u:%u)"
                                                     " - the kernel only registers the tty in sysfs,"
                                                     " userspace must mknod it\n", TTY, sysdev, maj, min);
                                                return 0;
                                        }
                                        klog("nuxel-console: mknod %s c %u %u failed: %s\n",
                                             TTY, maj, min, strerror(errno));
                                } else {
                                        klog("nuxel-console: unparsable %s = '%s'\n", sysdev, buf);
                                }
                        }
                }
                if (i % 5 == 0)
                        klog("nuxel-console: waiting for %s / %s (%d s)\n", TTY, sysdev, i);
                usleep(500000);
        }
        klog("nuxel-console: %s never became available (no sysfs tty registration)\n", TTY);
        return -1;
}

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

        /* A25: the post-handoff supervisor is started HERE, not by /init.
         * A24 measured why: /init's detached subshell survives switch_root (the
         * code pages stay mapped) but every command it then runs -- `sleep 1` in its
         * wait loop, and later `date`/`systemctl` -- resolves against a root that
         * switch_root has already emptied, so it dies before writing anything and
         * /var/lib/nuxel/bootreport.txt never appears.  This process, by contrast,
         * chroots deliberately into the new root (exactly like the reporter and the
         * live shell, both of which are proven to work) and then runs the script
         * with the Fedora shell. */
        if (want_report) {
                pid_t p = fork();
                if (p == 0) {
                        if (chdir(newroot) == 0 && chroot(".") == 0 && chdir("/") == 0) {
                                setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
                                sleep(12);
                                char *av[] = { (char *)"sh", (char *)"/usr/lib/nuxel/nuxel-postboot.sh",
                                               (char *)"20", NULL };
                                execve("/bin/sh", av, environ);
                                execve("/usr/bin/bash", av, environ);
                        }
                        _exit(127);
                }
                klog("nuxel-console: post-handoff supervisor pid=%d -> /usr/lib/nuxel/nuxel-postboot.sh\n", (int)p);
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

        /* A19: make sure the device node exists, then open it.  See
         * ensure_tty_node() for why the kernel does not create it. */
        if (ensure_tty_node() != 0)
                return 1;
        int ttyfd = open(TTY, O_RDWR | O_NONBLOCK);
        if (ttyfd < 0) {
                klog("nuxel-console: open %s failed: %s\n", TTY, strerror(errno));
                return 1;
        }
        { int cf = fcntl(ttyfd, F_GETFD); if (cf >= 0) (void)fcntl(ttyfd, F_SETFD, cf & ~FD_CLOEXEC); }

        /* keep a blocking-ish duplicate policy: O_NONBLOCK off for the shell tty */
        int fl = fcntl(ttyfd, F_GETFL); if (fl >= 0) (void)fcntl(ttyfd, F_SETFL, fl & ~O_NONBLOCK);
        klog("nuxel-console: %s ready - live channel UP\n", TTY);

        if (want_pump) {
                pid_t p = fork();
                if (p == 0) { pump_kmsg(-1); _exit(0); }
        }
        if (want_shell) {
                pid_t p = fork();
                if (p == 0) {
                        /* A24 shell supervisor: the channel is re-armed after ANY
                         * exit (host disconnect, 'exit', a crash in the shell).
                         * Without this a single disconnect ended live debugging for
                         * the rest of the boot. */
                        for (int attempt = 1; attempt <= 100000; attempt++) {
                                pid_t c = fork();
                                if (c == 0) shell_child(newroot, ttyfd);
                                if (c < 0) { sleep(2); continue; }
                                int st = 0;
                                (void)waitpid(c, &st, 0);
                                if (attempt <= 3 || attempt % 20 == 0)
                                        klog("nuxel-console: shell #%d exited (status %d); respawning\n",
                                             attempt, st);
                                sleep(1);
                        }
                        _exit(0);
                }
                klog("nuxel-console: live shell supervisor pid=%d on %s\n", (int)p, TTY);
        }
        return 0;
}
