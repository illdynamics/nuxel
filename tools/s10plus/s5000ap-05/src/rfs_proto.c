/* rfs_proto.c — pure RFS raw-request parser/classifier. GPL-2.0-only. */
#include "rfs_proto.h"
#include "sipc5_proto_table.h"
#include <string.h>

/* Destructive op-classes for this hardware, LIVE-observed + policy:
 *   0x0b = DELETE_ALL_VIS (delete-all NV/EFS artifact). */
static bool is_destructive_op(uint8_t op_class)
{
    return op_class == 0x0b;
}

int rfs_proto_parse(const uint8_t *data, size_t len, struct rfs_proto_msg *out)
{
    if (!data || !out) return RFS_PROTO_SHORT;
    memset(out, 0, sizeof(*out));
    if (len < RFS_PROTO_HDR_MIN) return RFS_PROTO_SHORT;

    out->len      = (uint32_t)data[0] | ((uint32_t)data[1] << 8) |
                    ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
    out->op_class = data[4];
    out->flags    = data[5];
    out->path_len = (uint16_t)data[6] | ((uint16_t)data[7] << 8);

    /* Extract a bounded printable opcode starting at offset 10. We cap at
     * RFS_PROTO_OP_MAX-1 and never read past the buffer. */
    bool printable = true;
    size_t k = 0;
    size_t want = out->path_len ? out->path_len : (RFS_PROTO_OP_MAX - 1);
    if (want > RFS_PROTO_OP_MAX - 1) want = RFS_PROTO_OP_MAX - 1;
    for (size_t i = RFS_PROTO_HDR_MIN; i < len && k < want; i++) {
        unsigned char c = data[i];
        if (c == 0) break;
        if (c < 0x20 || c > 0x7e) { printable = false; out->opcode[k++] = '?'; continue; }
        out->opcode[k++] = (char)c;
    }
    out->opcode[k] = '\0';
    out->opcode_valid = printable && k > 0;

    /* A real RFS request carries a printable ASCII opcode. A blob whose opcode
     * is not printable / empty is NOT RFS-header-shaped (e.g. opaque bulk),
     * so reject it as RFS rather than misclassifying it. */
    if (!out->opcode_valid)
        return RFS_PROTO_LEN_MISMATCH;

    /* Additional sanity: a plausible request must not declare a length far
     * beyond what could be carried; reject pathological values as non-RFS. */
    if (out->len > (1u << 20) || out->path_len > (1u << 12))
        return RFS_PROTO_LEN_MISMATCH;

    out->destructive = is_destructive_op(out->op_class);
    out->known = false;
    for (unsigned i = 0; i < NUXEL_NUM_RFS_OBS; i++) {
        if (nuxel_rfs_observations[i].op_class == out->op_class) {
            out->known = true;
            out->destructive = true; /* all observed ops are destructive */
            break;
        }
    }
    return RFS_PROTO_OK;
}
