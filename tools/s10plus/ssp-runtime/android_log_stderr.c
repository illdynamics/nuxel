/* Diagnostic-only Android log sink; no HAL, property, GPIO or RPC stubs.
 * Build as a freestanding AArch64 shared object. The Android loader resolves
 * vsnprintf/write against the staged Bionic libc, never against host glibc. */
#include <stdarg.h>
#include <stddef.h>
extern int vsnprintf(char *, size_t, const char *, va_list);
extern long write(int, const void *, unsigned long);

int __android_log_vprint(int priority, const char *tag, const char *fmt, va_list args)
{
    char text[2048];
    int n;
    (void)priority;
    (void)tag;
    n = vsnprintf(text, sizeof text, fmt, args);
    if (n < 0) return n;
    if ((size_t)n >= sizeof text) n = sizeof text - 1;
    (void)write(2, text, (unsigned long)n);
    (void)write(2, "\n", 1);
    return n;
}

int __android_log_print(int priority, const char *tag, const char *fmt, ...)
{
    int n;
    va_list args;
    va_start(args, fmt);
    n = __android_log_vprint(priority, tag, fmt, args);
    va_end(args);
    return n;
}

int __android_log_write(int priority, const char *tag, const char *text)
{
    return __android_log_print(priority, tag, "%s", text);
}
