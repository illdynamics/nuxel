/* SPDX-License-Identifier: GPL-2.0-only */
#include "oes_cert.h"
#include "fmt_tx.h"
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

void oes_cert_free(struct oes_cert *cert)
{
    if (!cert) return;
    free(cert->data); cert->data = NULL; cert->len = 0;
}

int oes_cert_load(const char *path, struct oes_cert *out)
{
    if (!path || !out) return -EINVAL;
    memset(out, 0, sizeof *out);
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0) return -errno;
    struct stat st;
    int rc = -EINVAL;
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_size < 2 ||
        st.st_size > (off_t)(255u * FMT_TX_OES_CERT_CHUNK)) goto done;
    out->len = (size_t)st.st_size;
    out->data = malloc(out->len);
    if (!out->data) { rc = -ENOMEM; goto done; }
    for (size_t got = 0; got < out->len;) {
        ssize_t n = read(fd, out->data + got, out->len - got);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { rc = -EIO; goto done; }
        got += (size_t)n;
    }
    /* A certificate is an ASN.1 DER SEQUENCE. Verify its outer length only;
     * the CP validates the original certificate's signature and identity. */
    if (out->data[0] != 0x30) goto done;
    size_t header = 2, size = out->data[1];
    if (size & 0x80) {
        size_t bytes = size & 0x7f;
        if (!bytes || bytes > 3 || 2+bytes > out->len) goto done;
        size = 0; header += bytes;
        for (size_t i=0; i<bytes; i++) size = (size << 8) | out->data[2+i];
    }
    if (header + size != out->len) goto done;
    rc = 0;
done:
    close(fd);
    if (rc) oes_cert_free(out);
    return rc;
}
