/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_iil_rx.h"
#include <sys/socket.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_parse(void)
{
    /* A 7-byte IIL header + 2-byte payload, main=112 sub=10 type=3. */
    uint8_t buf[16] = { 0x09,0x00, 0x34,0x12, 112,10,3, 2,1 };
    struct iil_rx_event e; size_t cons = 0;
    int r = iil_rx_parse(buf, 9, &e, &cons);
    assert(r == 9 && cons == 9);
    assert(e.msg_seq == 0x1234);
    assert(e.main_cmd == 112 && e.sub_cmd == 10 && e.cmd_type == 3);
    assert(e.payload_len == 2 && e.payload[0] == 2 && e.payload[1] == 1);

    /* truncation -> 0, need more */
    r = iil_rx_parse(buf, 4, &e, &cons);
    assert(r == 0);

    /* corrupt length -> negative */
    buf[0] = 0; buf[1] = 0x20;  /* 8192 > max */
    r = iil_rx_parse(buf, 9, &e, &cons);
    assert(r < 0);
    buf[0] = 9; buf[1] = 0;
}

static void test_connected(void)
{
    uint8_t buf[16] = { 9,0,0,0,112,10,3, 2,1 };
    struct iil_rx_event e; iil_rx_parse(buf, 9, &e, NULL);
    uint8_t cid = 0; bool attached = false;
    assert(iil_rx_connected(&e, &cid, &attached));
    assert(cid == 2 && attached);
}

static void test_isim_auth(void)
{
    uint8_t buf[40] = { 39,0,0,0,112,9,2 };
    for (int i = 0; i < 32; i++) buf[7+i] = (uint8_t)i;
    struct iil_rx_event e; iil_rx_parse(buf, 39, &e, NULL);
    uint8_t r[16], a[16];
    assert(iil_rx_isim_auth(&e, r, a));
    for (int i = 0; i < 16; i++) assert(r[i] == i && a[i] == i+16);
}

static void test_registration(void)
{
    uint8_t buf[8] = { 8,0,0,0,112,4,3, 1 };
    struct iil_rx_event e; iil_rx_parse(buf, 8, &e, NULL);
    bool reg = false;
    assert(iil_rx_registration(&e, &reg) && reg);
}

static void test_parameters(void)
{
    /* family=AF_INET6(10), prefix=64, ip=16 bytes, count=1, alen=16, pcscf */
    uint8_t buf[64];
    memset(buf, 0, sizeof buf);
    buf[0] = 7 + 18 + 1 + 1 + 16;
    buf[1] = 0;
    buf[4] = 112; buf[5] = 8; buf[6] = 3;
    buf[7] = 10; buf[8] = 64;
    memset(buf+9, 0xfd, 16);
    buf[25] = 1; buf[26] = 16;
    memset(buf+27, 0xaa, 16);
    size_t total = 7 + 18 + 1 + 1 + 16;
    struct iil_rx_event e; iil_rx_parse(buf, total, &e, NULL);
    int fam = 0; uint8_t ip[16]; uint8_t prefix = 0;
    uint8_t pcscf[4][16]; uint8_t plen[4]; unsigned n = 0;
    assert(iil_rx_parameters(&e, &fam, ip, &prefix, pcscf, plen, 4, &n));
    assert(fam == AF_INET6 && prefix == 64);
    assert(n == 1 && plen[0] == 16 && pcscf[0][0] == 0xaa);
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
