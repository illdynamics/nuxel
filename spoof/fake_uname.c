#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/utsname.h>
#include <string.h>  // 🧠 Include for strcpy()

int uname(struct utsname *buf) {
  int (*real_uname)(struct utsname*) = dlsym(RTLD_NEXT, "uname");
  int ret = real_uname(buf);

  // Now spoof dat OS ID like a proper cyberninja
  strcpy(buf->sysname, "Windows_NT");
  strcpy(buf->release, "10.0.22621");
  strcpy(buf->version, "#1 SMP Windows Wonked 2025");
  strcpy(buf->machine, "x86_64");

  return ret;
}
