/* SPDX-License-Identifier: GPL-2.0-only */
#include "oes_cert.h"
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    char path[] = "/tmp/nuxel-oes-cert-XXXXXX";
    int fd = mkstemp(path);
    assert(fd >= 0);
    /* Synthetic DER envelope, never a device certificate. */
    uint8_t data[987] = {0x30, 0x82, 0x03, 0xd7};
    memset(data+4, 0xab, sizeof data-4);
    assert(write(fd, data, sizeof data) == sizeof data);
    struct oes_cert c;
    assert(oes_cert_load(path, &c) == 0 && c.len == sizeof data);
    assert(memcmp(c.data, data, sizeof data) == 0);
    oes_cert_free(&c);
    assert(c.data == NULL && c.len == 0);
    uint8_t unchanged[sizeof data];
    assert(pread(fd, unchanged, sizeof unchanged, 0) == sizeof unchanged);
    assert(memcmp(unchanged, data, sizeof data) == 0);
    assert(ftruncate(fd, sizeof data-1) == 0);
    assert(oes_cert_load(path, &c) < 0 && !c.data && !c.len);
    assert(ftruncate(fd, 700*256) == 0);
    assert(oes_cert_load(path, &c) < 0 && !c.data && !c.len);
    close(fd); unlink(path);
    assert(oes_cert_load(path, &c) < 0);
    assert(symlink("/dev/zero", path) == 0);
    assert(oes_cert_load(path, &c) < 0);
    unlink(path);
    puts("OES certificate bounds, unchanged input, truncation and symlink rejection: PASS");
    return 0;
}
