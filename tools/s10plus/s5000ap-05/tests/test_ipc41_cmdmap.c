/*
 * test_ipc41_cmdmap.c — validate the recovered IpcProtocol41 command map.
 * SPDX-License-Identifier: GPL-2.0-only
 * Pure freestanding assertions on the numeric main/sub IDs and family
 * names recovered from the exact vendor RIL (see ipc41_cmdmap.h).
 */
#include <stdio.h>
#include <string.h>
#include "ipc41_cmdmap.h"

static int fails = 0;
static void chk(int cond, const char *msg)
{
    if (!cond) { fails++; printf("FAIL: %s\n", msg); }
}

int main(void)
{
    chk(IPC41_MAIN_PWR == 1, "main PWR == 1");
    chk(IPC41_MAIN_CALL == 2, "main CALL == 2");
    chk(IPC41_MAIN_SMS == 4, "main SMS == 4");
    chk(IPC41_MAIN_SEC == 5, "main SEC == 5");
    chk(IPC41_MAIN_PB == 6, "main PB == 6");
    chk(IPC41_MAIN_DISP == 7, "main DISP == 7");
    chk(IPC41_MAIN_NET == 8, "main NET == 8");
    chk(IPC41_MAIN_GPRS == 13, "main GPRS == 13");
    chk(IPC41_MAIN_SAT == 14, "main SAT == 14");
    chk(IPC41_MAIN_FACTORY == 19, "main FACTORY == 19");
    chk(IPC41_MAIN_SYSTEM == 39, "main SYSTEM == 39");
    chk(strcmp(ipc41_main_name(7), "DISP") == 0, "main_name(7)==DISP");
    chk(strcmp(ipc41_main_name(8), "NET") == 0, "main_name(8)==NET");
    chk(strcmp(ipc41_main_name(13), "GPRS") == 0, "main_name(13)==GPRS");
    chk(strcmp(ipc41_main_name(5), "SEC") == 0, "main_name(5)==SEC");

    chk(IPC41_SEC_PIN_STATUS == 1, "SEC_PIN_STATUS == 1");
    chk(IPC41_NET_POWERON_ATTACH == 9, "NET_POWERON_ATTACH == 9");
    chk(IPC41_NET_SERVING_NETWORK == 3, "NET_SERVING_NETWORK == 3");
    chk(IPC41_GPRS_DEFINE_PDP_CONTEXT == 1, "GPRS_DEFINE_PDP_CONTEXT == 1");
    chk(IPC41_DISP_RSSI_INFO == 6, "DISP_RSSI_INFO == 6");
    chk(IPC41_DISP_HOMEZONE_INFO == 2, "DISP_HOMEZONE_INFO == 2");
    chk(IPC41_PWR_PHONE_PWR_UP == 1, "PWR_PHONE_PWR_UP == 1");

    if (fails == 0) { printf("RESULT=PASS (ipc41_cmdmap)\n"); return 0; }
    printf("RESULT=FAIL %d\n", fails);
    return 1;
}
