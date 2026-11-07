#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <netdb.h>
#include <errno.h>
#include <stdlib.h>
#include <fcntl.h>
#include <stdarg.h>
#include <sys/types.h>
#include <sys/stat.h>

// Spoof uname
int uname(struct utsname *buf) {
    int (*original_uname)(struct utsname *buf);
    original_uname = dlsym(RTLD_NEXT, "uname");
    int result = original_uname(buf);

    strcpy(buf->sysname, "Windows_NT");
    strcpy(buf->nodename, "dextronux");
    strcpy(buf->release, "10.0.22621");
    strcpy(buf->version, "#1 SMP Wonked 2025");
    strcpy(buf->machine, "x86_64");

    return result;
}

// Spoof gethostname
int gethostname(char *name, size_t len) {
    strncpy(name, "dextronux", len);
    return 0;
}

// Spoof getaddrinfo
int getaddrinfo(const char *node, const char *service,
                const struct addrinfo *hints,
                struct addrinfo **res) {
    int (*original_getaddrinfo)(const char *, const char *,
                                const struct addrinfo *,
                                struct addrinfo **);
    original_getaddrinfo = dlsym(RTLD_NEXT, "getaddrinfo");
    if (strcmp(node, "dextronux") == 0) {
        node = "127.0.0.1";
    }
    return original_getaddrinfo(node, service, hints, res);
}

// Spoof /proc/version
FILE *fopen(const char *pathname, const char *mode) {
    static FILE* (*real_fopen)(const char *, const char *) = NULL;
    if (!real_fopen) real_fopen = dlsym(RTLD_NEXT, "fopen");

    if (strcmp(pathname, "/proc/version") == 0) {
        FILE *tmp = tmpfile();
        if (!tmp) return NULL;
        fprintf(tmp, "Microsoft Windows [Version 10.0.22621.2428]\n");
        rewind(tmp);
        return tmp;
    }
    return real_fopen(pathname, mode);
}

// Optional: Spoof stat access to /etc/os-release
int open(const char *pathname, int flags, ...) {
    static int (*real_open)(const char *, int, ...) = NULL;
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");

    if (strcmp(pathname, "/etc/os-release") == 0) {
        char tmpfile_path[] = "/tmp/winosXXXXXX";
        int fd = mkstemp(tmpfile_path);
        if (fd < 0) return -1;
        const char *fake =
            "NAME=\"Windows 11\"\n"
            "VERSION=\"22H2\"\n"
            "ID=windows\n"
            "ID_LIKE=winnt\n"
            "PRETTY_NAME=\"Windows 11 Wonk Edition\"\n"
            "VERSION_ID=\"22H2\"\n";
        write(fd, fake, strlen(fake));
        lseek(fd, 0, SEEK_SET);
        return fd;
    }

    va_list args;
    va_start(args, flags);
    int fd = real_open(pathname, flags, args);
    va_end(args);
    return fd;
}
