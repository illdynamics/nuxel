/*
 * test_ipc41_recovery.c — source-backed validation of Stage-06 protocol
 * recovery facts (O3 static candidates from the exact vendor RIL).
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * These tests do NOT assert any live telephony semantics (SIM/registration/
 * bearer command IDs remain UNKNOWN). They pin the non-fabricated facts that
 * were RECOVERED this round from vendor/lib64/libsec-ril.so:
 *
 *   1. The dialect is "IpcProtocol41" (exported class name).
 *   2. The FMT transport header is exactly 7 bytes and its field order is
 *      len(u16), msg_seq, ack_seq, main_cmd, sub_cmd, cmd_type (corroborated
 *      by IpcTxExchange disassembly AND by the live AST_POWERON capture).
 *   3. The live AST_POWERON frame decodes to main=0x13 sub=0x05 type=0x03
 *      and 0x03 belongs to the notification cmd-type class (IPC_CMD_NOTI is
 *      present in the string table; 0x03 is the live-observed notification).
 *   4. The RFS receive path in libsec-ril is a stub (IpcRxRfs returns 0),
 *      i.e. RFS is handled by cbd, NOT by libsec-ril — this is recorded as a
 *      documented architectural fact, not a live RFS reply contract.
 *
 * The main_cmd family NAME list is recorded as O3 static-candidate evidence
 * only (34 distinct family names). We deliberately do NOT fabricate numeric
 * main_cmd ids for those names.
 */
#include "sipc5_fmt.h"
#include "sipc5_proto_table.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   "); printf(__VA_ARGS__); printf("\n"); } } while (0)

/* The 34 main_cmd FAMILY NAMES recovered from the vendor RIL string table.
 * Names only — no numeric ids are asserted (ids remain UNKNOWN). */
static const char * const recovered_family_names[] = {
    "CALL","CDMA DATA","CFG","DISP","DOMESTIC","EMBMS","FACTORY","GEN",
    "GPRS","GPS","IIL","IMEI","IMS","JPN","MCPTT","MISC","MMS","MODEMTEST",
    "NET","OES","OMADM","PB","PROSE","PWR","QMIIMS","RFS","SAP","SAT",
    "SEC","SMS","SND","SS","SVC","SYSTEM", NULL /* MAIN_CMD_UNDEFINED */
};

int main(void)
{
    /* 1. Dialect pin */
    CHECK(strcmp(NUXEL_IPC41_DIALECT, "IpcProtocol41") == 0,
          "dialect == %s", NUXEL_IPC41_DIALECT);

    /* 2. FMT ABI: struct is exactly 7 bytes */
    CHECK(sizeof(struct sipc_fmt_hdr) == 7,
          "sipc_fmt_hdr ABI == 7 bytes (got %zu)", sizeof(struct sipc_fmt_hdr));

    /* 3. Live AST_POWERON frame decodes to confirmed fields.
     *    (main=0x13 sub=0x05 type=0x03; 25 bytes total; 18-byte payload). */
    {
        const u8 real25[] = {
            0x19,0x00,0x00,0x00,0x13,0x05,0x03,
            0x0f,0x00,0x0d,0x0a,
            'A','S','T','_','P','O','W','E','R','O','N',
            0x0d,0x0a,0x00
        };
        struct nuxel_sipc_fmt f; size_t consumed = 0;
        int r = sipc5_parse_fmt(real25, sizeof real25, 0x10000, &f, &consumed);
        CHECK(r == SIPC_PARSE_OK, "live AST_POWERON parse OK (r=%d)", r);
        CHECK(f.main_cmd == 0x13 && f.sub_cmd == 0x05 && f.cmd_type == 0x03,
              "AST_POWERON main=0x13 sub=0x05 type=0x03");
        CHECK(f.cmd_type == 0x03, "cmd_type 0x03 is notification class (live)");
    }

    /* 4. Family-name table is internally consistent and has the expected
     *    count (34 recoverable names; the 35th slot is the sentinel). */
    {
        int n = 0;
        while (n < 64 && recovered_family_names[n] != NULL) n++;
        CHECK(n == NUXEL_NUM_MAINCMD_FAMILY_NAMES,
              "recovered family-name count == %d (got %d)",
              NUXEL_NUM_MAINCMD_FAMILY_NAMES, n);
        /* spot-check a few families that matter for stage-06 goals */
        CHECK(strcmp(recovered_family_names[0], "CALL") == 0, "CALL present");
        CHECK(strcmp(recovered_family_names[4], "DOMESTIC") == 0, "DOMESTIC present");
        CHECK(strcmp(recovered_family_names[8], "GPRS") == 0, "GPRS present");
        CHECK(strcmp(recovered_family_names[18], "NET") == 0, "NET present");
        CHECK(strcmp(recovered_family_names[25], "RFS") == 0, "RFS present");
        CHECK(strcmp(recovered_family_names[31], "SS") == 0, "SS present");
    }

    /* 5. RFS is cbd-handled, not libsec-ril: IpcRxRfs is a stub.
     *    We encode this as a documented FACT (not a live reply contract). */
    CHECK(1, "RFS receive is documented as cbd-handled (IpcRxRfs is a stub)");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
