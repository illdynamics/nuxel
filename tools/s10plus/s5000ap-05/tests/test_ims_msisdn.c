/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_msisdn.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
static void chk(int cond, const char *what)
{
    if (cond) return;
    failures++;
    fprintf(stderr, "FAIL: %s\n", what);
}

int main(void)
{
    char out[64];
    /* Valid EF_MSISDN: 11 digits "31612345678" -> len=11, TON/NPI=0x91.
     * BCD low-nibble-first (TS 31.102 4.4.2.3):
     *   (3,1)=0x13 (6,1)=0x61 (2,3)=0x32 (4,5)=0x54 (6,7)=0x76 (8,F)=0xf8 */
    const uint8_t ef[] = { 11, 0x91, 0x13, 0x16, 0x32, 0x54, 0x76, 0xf8 };
    chk(ims_msisdn_decode(ef, sizeof ef, out, sizeof out), "valid decode");
    chk(strcmp(out, "31612345678") == 0, "expected digits");
    if (strcmp(out,"31612345678")) printf("got=%s\n", out);

    /* MSISDN-based IMPU: +31612345678 @ ims.mnc008.mcc204.3gppnetwork.org */
    chk(ims_msisdn_impu("31612345678", "ims.mnc008.mcc204.3gppnetwork.org",
                        out, sizeof out), "impu build");
    chk(strcmp(out, "sip:+31612345678@ims.mnc008.mcc204.3gppnetwork.org") == 0,
        "impu content");
    if (strcmp(out,"sip:+31612345678@ims.mnc008.mcc204.3gppnetwork.org"))
        printf("impu=%s\n", out);

    /* Reject non-0x91 TON/NPI (domestic/unknown). */
    const uint8_t domestic[] = { 11, 0x81, 0x13,0x16,0x32,0x54,0x76,0xf8 };
    chk(!ims_msisdn_decode(domestic, sizeof domestic, out, sizeof out),
        "reject non-international TON/NPI");

    /* Reject a high nibble that is not a valid digit in the middle. */
    const uint8_t bad_nib[] = { 2, 0x91, 0x1a };
    chk(!ims_msisdn_decode(bad_nib, sizeof bad_nib, out, sizeof out),
        "reject invalid nibble");

    /* Reject zero digits / truncation. */
    const uint8_t zero[] = { 0, 0x91, 0x00 };
    chk(!ims_msisdn_decode(zero, sizeof zero, out, sizeof out), "reject zero digits");
    chk(!ims_msisdn_decode(ef, 1, out, sizeof out), "reject truncated EF");

    /* Protected runtime subscriber-config parsing (synthetic, never real). */
    char conf[64];
    chk(ims_msisdn_parse_conf("MSISDN=31600000000", conf, sizeof conf),
        "conf valid parse");
    chk(strcmp(conf, "31600000000") == 0, "conf expected value");
    chk(!ims_msisdn_parse_conf("MSISDN=", conf, sizeof conf), "conf empty");
    chk(!ims_msisdn_parse_conf("MSISDN=+316", conf, sizeof conf), "conf plus rejected");
    chk(!ims_msisdn_parse_conf("MSISDN=31a45", conf, sizeof conf), "conf non-digit");
    chk(!ims_msisdn_parse_conf("MSISDN=1234567890123456", conf, sizeof conf), "conf too long");
    chk(!ims_msisdn_parse_conf("MSISDN =3164", conf, sizeof conf), "conf wrong key");
    chk(!ims_msisdn_parse_conf("3100", conf, sizeof conf), "conf missing key");
    chk(!ims_msisdn_parse_conf(NULL, conf, sizeof conf), "conf null line");

    /* IMPU rejects an empty / non-digit / too-long input. */
    chk(!ims_msisdn_impu("", "d", out, sizeof out), "impu empty");
    chk(!ims_msisdn_impu("12a45", "d", out, sizeof out), "impu non-digit");
    chk(!ims_msisdn_impu("1234567890123456", "d", out, sizeof out), "impu too long");

    if (failures) { fprintf(stderr, "test_ims_msisdn: %d failures\n", failures); return 1; }
    puts("test_ims_msisdn OK");
    return 0;
}
