#define _POSIX_C_SOURCE 200809L
#include "s5000ap_uapi.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static const char *state_name(int state)
{
    static const char *const names[] = {
        "OFFLINE", "CRASH_RESET", "CRASH_EXIT", "BOOTING", "ONLINE",
        "NV_REBUILDING", "LOADER_DONE", "SIM_ATTACH", "SIM_DETACH",
        "CRASH_WATCHDOG"
    };
    if (state < 0 || (size_t)state >= sizeof(names) / sizeof(names[0]))
        return NULL;
    return names[state];
}

static int parse_nonnegative_int(const char *s, int *out)
{
    char *end = NULL;
    long value;
    errno = 0;
    value = strtol(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || value < 0 || value > 1000000)
        return -1;
    *out = (int)value;
    return 0;
}

static void print_state(int state, int json)
{
    const char *name = state_name(state);
    if (json) {
        if (name)
            printf("{\"state_id\":%d,\"state\":\"%s\",\"source\":\"read-only MODEM_STATUS ioctl\"}\n",
                   state, name);
        else
            printf("{\"state_id\":%d,\"state\":\"UNKNOWN\",\"source\":\"read-only MODEM_STATUS ioctl\"}\n",
                   state);
    } else if (name) {
        printf("S5000AP state: %s (%d) [read-only]\n", name, state);
    } else {
        printf("S5000AP state: UNKNOWN (%d) [read-only]\n", state);
    }
}

int main(int argc, char **argv)
{
    const char *device = "/dev/umts_boot0";
    int json = 0;
    int decode = -1;
    int i;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--json") == 0) {
            json = 1;
        } else if (strcmp(argv[i], "--device") == 0 && i + 1 < argc) {
            device = argv[++i];
        } else if (strcmp(argv[i], "--decode") == 0 && i + 1 < argc) {
            if (parse_nonnegative_int(argv[++i], &decode) != 0) {
                fprintf(stderr, "invalid state id\n");
                return 64;
            }
        } else if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [--device PATH] [--json] [--decode STATE_ID]\n", argv[0]);
            printf("Default device: /dev/umts_boot0. Only MODEM_STATUS is issued.\n");
            return 0;
        } else {
            fprintf(stderr, "unknown or incomplete option: %s\n", argv[i]);
            return 64;
        }
    }

    if (decode >= 0) {
        print_state(decode, json);
        return state_name(decode) ? 0 : 2;
    }

    {
        int fd = open(device, O_RDONLY | O_CLOEXEC | O_NOCTTY);
        int result;
        if (fd < 0) {
            fprintf(stderr, "cannot open %s read-only: %s\n", device, strerror(errno));
            return 1;
        }
        result = ioctl(fd, NUXEL_IOCTL_MODEM_STATUS);
        if (result < 0) {
            int saved_errno = errno;
            (void)close(fd);
            fprintf(stderr, "MODEM_STATUS ioctl failed on %s: %s\n", device,
                    strerror(saved_errno));
            return 1;
        }
        (void)close(fd);
        print_state(result, json);
        return state_name(result) ? 0 : 2;
    }
}
