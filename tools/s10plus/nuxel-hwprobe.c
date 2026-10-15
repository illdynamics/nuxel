/* nuxel-hwprobe — one command that answers "what hardware can Nuxel actually use?"
 *
 * Written for the S10+ bring-up: run it from the A17 live USB shell (or from
 * init.sh) and it reports, in the kernel log and on stdout, everything the later
 * phases depend on:
 *   identity + boot mode, framebuffer geometry, DRM presence,
 *   the full input inventory with capability bitmaps (is there a touchscreen?),
 *   cgroup v2 state, PID 1 / systemd state, power-supply state.
 *
 * It deliberately prints ABSENCE as loudly as presence: "no /dev/dri" and
 * "no sec_touchscreen" are results, not errors.
 *
 * Freestanding-ish: only libc, no external tools, safe to run anywhere.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

static int kmsg = -1;

static void out(const char *fmt, ...) {
        char b[1024];
        va_list ap; va_start(ap, fmt);
        int n = vsnprintf(b, sizeof b, fmt, ap);
        va_end(ap);
        if (n <= 0) return;
        if (n > (int)sizeof b - 1) n = (int)sizeof b - 1;
        (void)!write(1, b, (size_t)n);
        if (kmsg >= 0) (void)!write(kmsg, b, (size_t)n);
}

static char *slurp(const char *path) {
        static char buf[4096];
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        if (fd < 0) return NULL;
        ssize_t n = read(fd, buf, sizeof buf - 1);
        close(fd);
        if (n < 0) return NULL;
        buf[n] = 0;
        for (ssize_t i = 0; i < n; i++) if (buf[i] == '\n') buf[i] = ' ';
        return buf;
}

static void sect(const char *name) { out("NUXEL-HWPROBE == %s ==\n", name); }

static void probe_identity(void) {
        struct utsname u;
        sect("identity");
        if (uname(&u) == 0)
                out("NUXEL-HWPROBE kernel=%s %s %s\n", u.release, u.version, u.machine);
        char *c = slurp("/proc/cmdline");
        out("NUXEL-HWPROBE cmdline=%s\n", c ? c : "<unreadable>");
        char *m = slurp("/sys/firmware/devicetree/base/model");
        if (!m) m = slurp("/proc/device-tree/model");
        out("NUXEL-HWPROBE dt-model=%s\n", m ? m : "<none>");
        char *p1 = slurp("/proc/1/comm");
        out("NUXEL-HWPROBE pid1=%s\n", p1 ? p1 : "<unknown>");
        struct stat st;
        out("NUXEL-HWPROBE systemd-running=%s\n",
            (stat("/run/systemd/system", &st) == 0) ? "yes" : "no");
}

static void probe_display(void) {
        sect("display");
        int found = 0;
        for (int i = 0; i < 4; i++) {
                char p[32]; snprintf(p, sizeof p, "/dev/fb%d", i);
                int fd = open(p, O_RDWR | O_CLOEXEC);
                if (fd < 0) continue;
                found = 1;
                struct fb_var_screeninfo vi; struct fb_fix_screeninfo fi;
                memset(&vi, 0, sizeof vi); memset(&fi, 0, sizeof fi);
                int rv = ioctl(fd, FBIOGET_VSCREENINFO, &vi);
                int rf = ioctl(fd, FBIOGET_FSCREENINFO, &fi);
                out("NUXEL-HWPROBE fb %s vscrc=%d fscrc=%d xres=%u yres=%u "
                    "vxres=%u vyres=%u bpp=%u stride=%u\n", p, rv, rf,
                    vi.xres, vi.yres, vi.xres_virtual, vi.yres_virtual,
                    vi.bits_per_pixel, fi.line_length);
                out("NUXEL-HWPROBE fb %s id=%s smem_len=%u\n", p, fi.id, fi.smem_len);
                close(fd);
        }
        if (!found) out("NUXEL-HWPROBE fb NONE (no /dev/fb*)\n");
        for (int i = 0; i < 4; i++) {
                char p[48]; snprintf(p, sizeof p, "/dev/dri/card%d", i);
                if (access(p, R_OK) == 0) out("NUXEL-HWPROBE drm %s present\n", p);
        }
        if (access("/dev/dri/card0", R_OK) != 0)
                out("NUXEL-HWPROBE drm ABSENT (no /dev/dri/card*) -> wlroots/Phoc cannot start\n");
        char *bl = slurp("/sys/class/backlight/panel/brightness");
        out("NUXEL-HWPROBE backlight=%s\n", bl ? bl : "<none>");
        char *md = slurp("/sys/class/lcd/panel/lcd_type");
        if (md) out("NUXEL-HWPROBE lcd_type=%s\n", md);
}

static const char *evname(unsigned t) {
        switch (t) {
        case EV_SYN: return "SYN"; case EV_KEY: return "KEY"; case EV_REL: return "REL";
        case EV_ABS: return "ABS"; case EV_MSC: return "MSC"; case EV_SW: return "SW";
        case EV_LED: return "LED"; case EV_SND: return "SND"; case EV_REP: return "REP";
        case EV_FF: return "FF"; case EV_PWR: return "PWR"; default: return "?";
        }
}

static void probe_input(void) {
        sect("input");
        DIR *d = opendir("/dev/input");
        if (!d) { out("NUXEL-HWPROBE input /dev/input unreadable (%s)\n", strerror(errno)); return; }
        struct dirent *e;
        int touch = 0, nev = 0;
        while ((e = readdir(d))) {
                if (strncmp(e->d_name, "event", 5) != 0) continue;
                char p[300]; snprintf(p, sizeof p, "/dev/input/%s", e->d_name);
                int fd = open(p, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
                if (fd < 0) { out("NUXEL-HWPROBE input %s open failed %s\n", p, strerror(errno)); continue; }
                nev++;
                char name[256] = "<unnamed>";
                (void)ioctl(fd, EVIOCGNAME(sizeof name - 1), name);
                unsigned long evb = 0; unsigned long absb[(ABS_MAX / 8) + 1];
                memset(absb, 0, sizeof absb);
                (void)ioctl(fd, EVIOCGBIT(0, sizeof evb), &evb);
                char caps[128] = ""; size_t cl = 0;
                for (unsigned t = 0; t < 32; t++)
                        if (evb & (1UL << t) && cl < sizeof caps - 8)
                                cl += (size_t)snprintf(caps + cl, sizeof caps - cl, "%s ", evname(t));
                out("NUXEL-HWPROBE input %s name='%s' caps=%s\n", p, name, caps);
                if (ioctl(fd, EVIOCGBIT(EV_ABS, sizeof absb), absb) >= 0) {
                        struct input_absinfo ai;
                        if (absb[ABS_MT_POSITION_X / 8] & (1UL << (ABS_MT_POSITION_X % 8))) {
                                if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_X), &ai) == 0)
                                        out("NUXEL-HWPROBE input %s ABS_MT_POSITION_X min=%d max=%d\n",
                                            p, ai.minimum, ai.maximum);
                                if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_Y), &ai) == 0)
                                        out("NUXEL-HWPROBE input %s ABS_MT_POSITION_Y min=%d max=%d\n",
                                            p, ai.minimum, ai.maximum);
                                if (strstr(name, "sec_touchscreen")) touch = 1;
                        }
                }
                close(fd);
        }
        closedir(d);
        out("NUXEL-HWPROBE input events=%d\n", nev);
        if (touch)
                out("NUXEL-HWPROBE TOUCHSCREEN=PRESENT (sec_touchscreen with multitouch ABS)\n");
        else
                out("NUXEL-HWPROBE TOUCHSCREEN=ABSENT -> check for "
                    "'sec_ts_init: Do not load driver due to : lpm 1' (charger-mode boot)\n");
}

static void probe_cgroup(void) {
        sect("cgroup");
        char *ctl = slurp("/sys/fs/cgroup/cgroup.controllers");
        out("NUXEL-HWPROBE cgroup2.controllers=%s\n", ctl ? ctl : "<absent: cgroup2 not mounted here>");
        char *sub = slurp("/sys/fs/cgroup/cgroup.subtree_control");
        out("NUXEL-HWPROBE cgroup2.subtree_control=%s\n", sub ? sub : "<n/a>");
        char *sc = slurp("/proc/self/cgroup");
        out("NUXEL-HWPROBE self.cgroup=%s\n", sc ? sc : "<none>");
}

static void probe_power(void) {
        sect("power");
        DIR *d = opendir("/sys/class/power_supply");
        if (!d) return;
        struct dirent *e;
        while ((e = readdir(d))) {
                if (e->d_name[0] == '.') continue;
                char p[300];
                snprintf(p, sizeof p, "/sys/class/power_supply/%s/status", e->d_name);
                char *s = slurp(p);
                snprintf(p, sizeof p, "/sys/class/power_supply/%s/capacity", e->d_name);
                char *c = slurp(p);
                snprintf(p, sizeof p, "/sys/class/power_supply/%s/online", e->d_name);
                char *o = slurp(p);
                out("NUXEL-HWPROBE power %s status=%s capacity=%s online=%s\n",
                    e->d_name, s ? s : "-", c ? c : "-", o ? o : "-");
        }
        closedir(d);
}

int main(int argc, char **argv) {
        kmsg = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
        out("\nNUXEL-HWPROBE begin (pid=%d)\n", (int)getpid());
        probe_identity();
        probe_display();
        probe_input();
        probe_cgroup();
        probe_power();
        out("NUXEL-HWPROBE end\n");
        if (kmsg >= 0) close(kmsg);
        (void)argc; (void)argv;
        return 0;
}
