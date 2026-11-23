/*
 * nuxel-s5000ap-uapi-check — OFFLINE ABI verification fixture.
 *
 * Compiles for both the host (LP64) and a 32-bit target to catch pointer-width
 * and struct-layout drift, and static-asserts every ioctl numeric value and
 * struct size/offset against the pinned kernel ABI. It performs NO ioctl and
 * touches NO device: it is pure compile-time + size/offset printing.
 *
 * Build (see BUILD_RECEIPT):
 *   aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -o nuxel-s5000ap-uapi-check s5000ap_uapi.h nuxel-s5000ap-uapi-check.c
 *   gcc -m32 ...                                    (ILP32 layout diff)
 *   gcc ...                                         (host LP64)
 */
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>
#include "s5000ap_uapi.h"

/* ---- compile-time ioctl value pins ---------------------------------- */
_Static_assert(IOCTL_MODEM_ON          == 0x6F19, "ioctl 0x19");
_Static_assert(IOCTL_MODEM_OFF         == 0x6F20, "ioctl 0x20");
_Static_assert(IOCTL_MODEM_RESET       == 0x6F21, "ioctl 0x21");
_Static_assert(IOCTL_MODEM_BOOT_ON     == 0x6F22, "ioctl 0x22");
_Static_assert(IOCTL_MODEM_BOOT_OFF    == 0x6F23, "ioctl 0x23");
_Static_assert(IOCTL_MODEM_BOOT_DONE   == 0x6F24, "ioctl 0x24");
_Static_assert(IOCTL_MODEM_STATUS      == 0x6F27, "ioctl 0x27");
_Static_assert(IOCTL_MODEM_DL_START    == 0x6F28, "ioctl 0x28");
_Static_assert(IOCTL_MODEM_FW_UPDATE   == 0x6F29, "ioctl 0x29");
_Static_assert(IOCTL_MODEM_FORCE_CRASH_EXIT == 0x6F34, "ioctl 0x34");
_Static_assert(IOCTL_MODEM_CP_UPLOAD   == 0x6F35, "ioctl 0x35");
_Static_assert(IOCTL_MODEM_XMIT_BOOT   == 0x6F40, "ioctl 0x40");
_Static_assert(IOCTL_MODEM_GET_SHMEM_INFO == 0x6F41, "ioctl 0x41");
_Static_assert(IOCTL_MODEM_GET_SHMEM_SRINFO == 0x6F45, "ioctl 0x45");
_Static_assert(IOCTL_MODEM_SET_SHMEM_SRINFO == 0x6F46, "ioctl 0x46");
_Static_assert(IOCTL_MODEM_GET_CP_BOOTLOG   == 0x6F47, "ioctl 0x47");
_Static_assert(IOCTL_MODEM_CLR_CP_BOOTLOG   == 0x6F48, "ioctl 0x48");
_Static_assert(IOCTL_SECURITY_REQ      == 0x6F53, "ioctl 0x53");
_Static_assert(IOCTL_MODEM_CRASH_REASON== 0x6F55, "ioctl 0x55");
_Static_assert(IOCTL_MODEM_AIRPLANE_MODE==0x6F56, "ioctl 0x56");

/* ---- boot-state enum pins ------------------------------------------- */
_Static_assert(STATE_OFFLINE==0 && STATE_CRASH_RESET==1 && STATE_CRASH_EXIT==2
    && STATE_BOOTING==3 && STATE_ONLINE==4 && STATE_NV_REBUILDING==5
    && STATE_LOADER_DONE==6 && STATE_SIM_ATTACH==7 && STATE_SIM_DETACH==8
    && STATE_CRASH_WATCHDOG==9, "modem_state order");

_Static_assert(CP_BOOT_MODE_NORMAL==0 && CP_BOOT_MODE_DUMP==1
    && CP_BOOT_RE_INIT==2 && CP_BOOT_REQ_CP_RAM_LOGGING==5
    && CP_BOOT_MODE_MANUAL==7, "cp_boot_mode values");

/* ---- struct layout pins (LP64 / AArch64) ----------------------------- */
_Static_assert(sizeof(struct modem_firmware) == 28, "modem_firmware size 28 (packed, no tail padding)");
_Static_assert(sizeof(struct modem_sec_req) == 16, "modem_sec_req size 16");
_Static_assert(offsetof(struct modem_firmware, binary) == 0,  "mf.binary@0");
_Static_assert(offsetof(struct modem_firmware, size)   == 8,  "mf.size@8");
_Static_assert(offsetof(struct modem_firmware, m_offset)==12, "mf.m_offset@12");
_Static_assert(offsetof(struct modem_firmware, b_offset)==16, "mf.b_offset@16");
_Static_assert(offsetof(struct modem_firmware, mode)   ==20,  "mf.mode@20");
_Static_assert(offsetof(struct modem_firmware, len)    ==24,  "mf.len@24");

int main(void)
{
    /* Emit a deterministic JSON fact-matrix for CI comparison. */
    printf("{\n");
    printf("  \"abi_source_commit\": \"f7194c1d15eded1c2a1a4dc63825b26103435cc0\",\n");
    printf("  \"sizeof_ptr\": %zu,\n", sizeof(void *));
    printf("  \"sizeof_long\": %zu,\n", sizeof(long));
    printf("  \"sizeof_long_long\": %zu,\n", sizeof(long long));
    printf("  \"sizeof_u32\": %zu,\n", sizeof(u32));
    printf("  \"sizeof_modem_firmware\": %zu,\n", sizeof(struct modem_firmware));
    printf("  \"modem_firmware_offsets\": {\"binary\":%zu,\"size\":%zu,\"m_offset\":%zu,\"b_offset\":%zu,\"mode\":%zu,\"len\":%zu},\n",
        offsetof(struct modem_firmware, binary),
        offsetof(struct modem_firmware, size),
        offsetof(struct modem_firmware, m_offset),
        offsetof(struct modem_firmware, b_offset),
        offsetof(struct modem_firmware, mode),
        offsetof(struct modem_firmware, len));
    printf("  \"sizeof_modem_sec_req\": %zu,\n", sizeof(struct modem_sec_req));
    printf("  \"sizeof_sipc5_link_header\": %zu,\n", sizeof(struct sipc5_link_header));
    printf("  \"ioctl_0x27_status\": \"0x6F27\",\n");
    printf("  \"ioctl_0x40_xmit_boot\": \"0x6F40\",\n");
    printf("  \"ioctl_0x53_security\": \"0x6F53\",\n");
    printf("  \"state_online\": %d,\n", (int)STATE_ONLINE);
    printf("  \"state_crash_watchdog\": %d\n", (int)STATE_CRASH_WATCHDOG);
    printf("}\n");
    return 0;
}
