/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_OES_CERT_H
#define NUXEL_OES_CERT_H
#include <stddef.h>
#include <stdint.h>
struct oes_cert { uint8_t *data; size_t len; };
/* Read an existing regular DER certificate, never repair/create/modify it.
 * 255 chunks is the maximum representable by the vendor's u8 chunk index. */
int oes_cert_load(const char *path, struct oes_cert *out);
void oes_cert_free(struct oes_cert *cert);
#endif
