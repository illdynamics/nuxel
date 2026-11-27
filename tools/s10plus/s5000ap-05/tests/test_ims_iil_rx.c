/* SPDX-License-Identifier: GPL-2.0-only
 * Unit tests for the IIL receive parser + decoders. Sub numbers and layouts
 * are the AUTHORITATIVE vendor map recovered from libsec-ril.so
 * (IpcRxIil dispatch @0x356c18, vtable @0x3a9a60). See round17.md. */
#include "ims_iil_rx.h"
#include <sys/socket.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_parse(void)
{
    /* 7-byte IIL header + 2-byte payload, main=112 sub=22(Connected) type=3. */
    uint8_t buf[16] = { 0x09,0x00, 0x34,0x12, 112,22,3, 2,1 };
    struct iil_rx_event e; size_t cons = 0;
    int r = iil_rx_parse(buf, 9, &e, &cons);
    assert(r == 9 && cons == 9);
    assert(e.msg_seq == 0x1234);
    assert(e.main_cmd == 112 && e.sub_cmd == 22 && e.cmd_type == 3);
    assert(e.payload_len == 2 && e.payload[0] == 2 && e.payload[1] == 1);

    r = iil_rx_parse(buf, 4, &e, &cons);  /* truncation */
    assert(r == 0);

    buf[0] = 0; buf[1] = 0x20;            /* corrupt length > max */
    r = iil_rx_parse(buf, 9, &e, &cons);
    assert(r < 0);
}

static void test_connected(void)
{
    /* sub 22 = IpcRxIilConnected; carries only a notify code, no cid/ip. */
    uint8_t buf[8] = { 8,0,0,0,112,22,3, 123 };
    struct iil_rx_event e; iil_rx_parse(buf, 8, &e, NULL);
    uint8_t cid = 99; bool attached = false;
    assert(iil_rx_connected(&e, &cid, &attached));
    assert(cid == 0 && attached);        /* never fabricates a CID */
    /* sub 10 is UNHANDLED by the CP -> decoder must reject it. */
    buf[5] = 10; iil_rx_parse(buf, 8, &e, NULL);
    assert(!iil_rx_connected(&e, &cid, &attached));
}

static void test_isim_auth(void)
{
    /* sub 17; RAND@payload[1..16], AUTN@payload[17..32] (buf+8 / buf+0x18). */
    uint8_t buf[40] = { 40,0,0,0,112,17,2 };
    buf[7] = 0x7f;                        /* leading type/flag byte */
    for (int i = 0; i < 16; i++) buf[8+i] = (uint8_t)i;
    for (int i = 0; i < 16; i++) buf[24+i] = (uint8_t)(0x80+i);
    struct iil_rx_event e; iil_rx_parse(buf, 40, &e, NULL);
    uint8_t r[16], a[16];
    assert(iil_rx_isim_auth(&e, r, a));
    for (int i = 0; i < 16; i++) assert(r[i] == i && a[i] == 0x80+i);
}

static void test_registration(void)
{
    /* sub 7; payload[0]=ImsRegStatus. 1=REGISTERED. */
    uint8_t buf[16]; memset(buf,0,sizeof buf);
    buf[0]=16; buf[4]=112; buf[5]=7; buf[6]=3; buf[7]=1; buf[8]=2;
    struct iil_rx_event e; iil_rx_parse(buf, 16, &e, NULL);
    int st = iil_rx_registration(&e, NULL);
    assert(st == 1);
}

static void test_parameters(void)
{
    /* sub 4. Vendor handler is a stub, but the bounded decoder still accepts
     * a well-formed payload: family=AF_INET6(10), prefix=64, ip=16, 1 pcscf. */
    uint8_t buf[64];
    memset(buf, 0, sizeof buf);
    size_t total = 7 + 18 + 1 + 1 + 16;
    buf[0] = (uint8_t)total; buf[1] = 0;
    buf[4] = 112; buf[5] = 4; buf[6] = 3;
    buf[7] = 10; buf[8] = 64;
    memset(buf+9, 0xfd, 16);
    buf[25] = 1; buf[26] = 16;
    memset(buf+27, 0xaa, 16);
    struct iil_rx_event e; iil_rx_parse(buf, total, &e, NULL);
    int fam = 0; uint8_t ip[16]; uint8_t prefix = 0;
    uint8_t pcscf[4][16]; uint8_t plen[4]; unsigned n = 0;
    assert(iil_rx_parameters(&e, &fam, ip, &prefix, pcscf, plen, 4, &n));
    assert(fam == AF_INET6 && prefix == 64);
    assert(n == 1 && plen[0] == 16 && pcscf[0][0] == 0xaa);
    /* sub 8 is UNHANDLED -> decoder must reject. */
    buf[5] = 8; iil_rx_parse(buf, total, &e, NULL);
    assert(!iil_rx_parameters(&e, &fam, ip, &prefix, pcscf, plen, 4, &n));
}

int main(void)
{
    test_parse();
    test_connected();
    test_isim_auth();
    test_registration();
    test_parameters();
    puts("IMS IIL RX: PASS");
    return 0;
}
