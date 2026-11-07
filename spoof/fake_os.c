#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

// ---- Spoof uname ----
int uname(struct utsname *buf) {
  int (*real_uname)(struct utsname*) = dlsym(RTLD_NEXT, "uname");
  int ret = real_uname(buf);
  strcpy(buf->sysname, "Windows_NT");
  strcpy(buf->release, "10.0.22621");
  strcpy(buf->version, "#1 SMP Wonked 2025");
  strcpy(buf->machine, "x86_64");
  return ret;
}

// ---- Spoof /etc/os-release ----
FILE* fopen(const char* pathname, const char* mode) {
  static FILE* (*real_fopen)(const char*, const char*) = NULL;
  if (!real_fopen)
    real_fopen = dlsym(RTLD_NEXT, "fopen");

  if (strstr(pathname, "/etc/os-release")) {
    return real_fopen("/srv/fake-os-release", mode);
  }

  return real_fopen(pathname, mode);
}

// ---- Spoof open() too, just in case ----
int open(const char *pathname, int flags, ...) {
  static int (*real_open)(const char*, int, ...) = NULL;
  if (!real_open)
    real_open = dlsym(RTLD_NEXT, "open");

  if (strstr(pathname, "/etc/os-release")) {
    return real_open("/srv/fake-os-release", flags);
  }

  return real_open(pathname, flags);
}
