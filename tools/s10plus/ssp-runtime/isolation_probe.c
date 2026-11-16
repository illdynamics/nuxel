/* Target-side test of the same namespace used for the vendor daemon.
 * This never writes to a device. Compile with aarch64-linux-gnu-gcc -static. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    const char *denied[] = {
        "/dev/ttyBCM", "/dev/bbd_sensor", "/dev/bbd_control", "/dev/bbd_patch",
        "/dev/sda", "/sys/class/sec/sensorhub/mcu_power",
        "/sys/class/sec/gps/GPS_PWR_EN/value", "/efs", "/etc/shadow",
        "/proc/1/root/etc/shadow"
    };
    unsigned int i;
    int failed = 0;
    for (i = 0; i < sizeof denied / sizeof denied[0]; i++) {
        int fd = open(denied[i], O_RDONLY | O_NONBLOCK);
        printf("%s %s errno=%d\n", fd < 0 ? "DENIED" : "EXPOSED", denied[i], errno);
        if (fd >= 0) { failed = 1; close(fd); }
    }
    int fd = open("/vendor/bin/hw/lhd", O_WRONLY);
    printf("runtime_readonly=%d uid=%ld gid=%ld\n", fd < 0, (long)getuid(), (long)getgid());
    if (fd >= 0) { failed = 1; close(fd); }
    FILE *f = fopen("/proc/self/status", "r");
    char line[256];
    int no_privs = 0, no_caps = 0;
    if (f) {
        while (fgets(line, sizeof line, f)) {
            if (!strncmp(line, "NoNewPrivs:", 11)) {
                fputs(line, stdout);
                no_privs = strstr(line, "1") != NULL;
            }
            if (!strncmp(line, "CapEff:", 7)) {
                fputs(line, stdout);
                no_caps = strstr(line, "0000000000000000") != NULL;
            }
        }
        fclose(f);
    }
    if (!no_privs || !no_caps || getuid() != 65534) failed = 1;
    printf("isolation=%s (NO HARDWARE ACCESS)\n", failed ? "FAIL" : "PASS");
    return failed;
}
