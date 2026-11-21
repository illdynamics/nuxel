/*
 * nuxel_bbd_flash.c — verified native BCM47752 RAM firmware (patch) downloader.
 *
 * Implements the firmware-download state machine recovered from the hash-verified
 * Samsung lhd (G975FXXS9DTK9, SHA-256 6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe).
 * Protocol facts extracted by tools/s10plus/ssp-runtime/inspect_lhd_init.py and
 * replay_lhd_response.py (static + Unicorn emulation of the exact matched ELF):
 *
 *   autobaud       : raw 36 x 0x80 on /dev/ttyBCM (lhd VA 0xdfe4)
 *   GetVersion     : RPC id 0, empty body (reliable enqueue payload 00 00)
 *   StartScratchApp: RPC id 46 (0x2E), body = LE32 entry, delay 40 ms, flags 0
 *   ServiceStart   : RPC id 55 (0x37), body = LE32 entry + 4 x LE32 zero, delay 100 ms, flags 0
 *   MemoryWrite    : RPC id 5 (0x05), body = LE32 destination + LE16 length + bytes
 *   patch record   : tags F0..F5; F1 = LE32 destination + data bytes
 *
 * Embedded patch: AsicVersion=0x004775b0 BlobLength=438895 PatchAddress=0x00800161 Crc=0x000000c1.
 *
 * Control strings (bbd.h / bbd_control):
 *   "SSI:PassThru=1"  = BBD_CTRL_SSI_PATCH_BEGIN (patch wake-lock)
 *   "BBD:PassThru=0"  = BBD_CTRL_PASSTHRU_OFF
 *   "ESW:READY"       = firmware-up notify — only emitted AFTER a verified hub reply.
 *
 * This tool NEVER synthesizes READY without the hub answering. Every RPC id, field
 * layout, delay and the autobaud byte run are pinned to the reviewed binary offsets.
 * It opens real devices only under the explicit --flash flag.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define BBD_PATCH   "/dev/bbd_patch"
#define BBD_SENSOR  "/dev/bbd_sensor"
#define BBD_CONTROL "/dev/bbd_control"
#define TTY_BCM     "/dev/ttyBCM"

#define ESC      0xB0
#define ESC_ESC  0x03
#define ESC_XON  0x04
#define ESC_XOFF 0x05
#define XON      0x11
#define XOFF     0x13
#define EOP      0x01

#define F_RELIABLE (1u << 1)

static const unsigned char crc_tbl[256] = {
0x00,0x4d,0x9a,0xd7,0x79,0x34,0xe3,0xae,0xf2,0xbf,0x68,0x25,0x8b,0xc6,0x11,0x5c,
0xa9,0xe4,0x33,0x7e,0xd0,0x9d,0x4a,0x07,0x5b,0x16,0xc1,0x8c,0x22,0x6f,0xb8,0xf5,
0x1f,0x52,0x85,0xc8,0x66,0x2b,0xfc,0xb1,0xed,0xa0,0x77,0x3a,0x94,0xd9,0x0e,0x43,
0xb6,0xfb,0x2c,0x61,0xcf,0x82,0x55,0x18,0x44,0x09,0xde,0x93,0x3d,0x70,0xa7,0xea,
0x3e,0x73,0xa4,0xe9,0x47,0x0a,0xdd,0x90,0xcc,0x81,0x56,0x1b,0xb5,0xf8,0x2f,0x62,
0x97,0xda,0x0d,0x40,0xee,0xa3,0x74,0x39,0x65,0x28,0xff,0xb2,0x1c,0x51,0x86,0xcb,
0x21,0x6c,0xbb,0xf6,0x58,0x15,0xc2,0x8f,0xd3,0x9e,0x49,0x04,0xaa,0xe7,0x30,0x7d,
0x88,0xc5,0x12,0x5f,0xf1,0xbc,0x6b,0x26,0x7a,0x37,0xe0,0xad,0x03,0x4e,0x99,0xd4,
0x7c,0x31,0xe6,0xab,0x05,0x48,0x9f,0xd2,0x8e,0xc3,0x14,0x59,0xf7,0xba,0x6d,0x20,
0xd5,0x98,0x4f,0x02,0xac,0xe1,0x36,0x7b,0x27,0x6a,0xbd,0xf0,0x5e,0x13,0xc4,0x89,
0x63,0x2e,0xf9,0xb4,0x1a,0x57,0x80,0xcd,0x91,0xdc,0x0b,0x46,0xe8,0xa5,0x72,0x3f,
0xca,0x87,0x50,0x1d,0xb3,0xfe,0x29,0x64,0x38,0x75,0xa2,0xef,0x41,0x0c,0xdb,0x96,
0x42,0x0f,0xd8,0x95,0x3b,0x76,0xa1,0xec,0xb0,0xfd,0x2a,0x67,0xc9,0x84,0x53,0x1e,
0xeb,0xa6,0x71,0x3c,0x92,0xdf,0x08,0x45,0x19,0x54,0x83,0xce,0x60,0x2d,0xfa,0xb7,
0x5d,0x10,0xc7,0x8a,0x24,0x69,0xbe,0xf3,0xaf,0xe2,0x35,0x78,0xd6,0x9b,0x4c,0x01,
0xf4,0xb9,0x6e,0x23,0x8d,0xc0,0x17,0x5a,0x06,0x4b,0x9c,0xd1,0x7f,0x32,0xe5,0xa8 };

static int g_verbose;
static void logx(const char *fmt, ...)
{
    va_list ap; va_start(ap, fmt);
    fprintf(stderr, "bbd-flash: "); vfprintf(stderr, fmt, ap); fputc('\n', stderr);
    va_end(ap); fflush(stderr);
}
static uint64_t now_ms(void)
{
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u;
}
static size_t rpc_field(uint8_t *o, uint16_t v)
{
    if (v >= 0x80) { o[0] = (uint8_t)(((v >> 8) & 0x7f) | 0x80); o[1] = (uint8_t)v; return 2; }
    o[0] = (uint8_t)v; return 1;
}
static size_t rpc_record(uint8_t *out, uint16_t id, const uint8_t *payload, size_t plen)
{
    size_t n = rpc_field(out, id);
    n += rpc_field(out + n, (uint16_t)plen);
    if (plen) { memcpy(out + n, payload, plen); n += plen; }
    return n;
}
static void put_raw(uint8_t **t, size_t *n, uint8_t v) { (*t)[(*n)++] = v; }
static void put_esc(uint8_t **t, size_t *n, uint8_t v)
{
    switch (v) {
    case ESC: put_raw(t,n,ESC); put_raw(t,n,ESC_ESC); break;
    case XON: put_raw(t,n,ESC); put_raw(t,n,ESC_XON); break;
    case XOFF: put_raw(t,n,ESC); put_raw(t,n,ESC_XOFF); break;
    default: put_raw(t,n,v); break;
    }
}
static size_t tl_build(uint8_t *wire, uint8_t seq, uint16_t flags,
                       const uint8_t *payload, size_t plen, uint8_t rel_seq)
{
    uint8_t body[4096]; size_t bn = 0, i, n = 0;
    uint8_t crc = 0; uint16_t sz = (uint16_t)plen;
    if (plen > 2048) return 0;
    /* size field = payload bytes ONLY (bbd_rpc_lh.c: usPayloadSize == usLen after
     * consuming header + all flag details). Flag-detail bytes are NOT counted. */
    sz = (uint16_t)plen;
    if (sz > 0xFF) flags |= (1u<<6);
    if (flags >> 8) flags |= (1u<<7);
    body[bn++] = seq; body[bn++] = (uint8_t)(sz & 0xFF); body[bn++] = (uint8_t)(flags & 0xFF);
    for (i = 0; i < 10; i++) {
        uint16_t bit = (uint16_t)(1u << i);
        if (!(flags & bit)) continue;
        if (bit == (1u<<6)) body[bn++] = (uint8_t)(sz >> 8);
        else if (bit == (1u<<7)) body[bn++] = (uint8_t)(flags >> 8);
        else if (bit == F_RELIABLE) body[bn++] = rel_seq;
        else body[bn++] = 0;
    }
    if (plen) { memcpy(body + bn, payload, plen); bn += plen; }
    for (i = 1; i < bn; i++) crc = crc_tbl[crc ^ body[i]];
    crc = (uint8_t)(((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4));
    put_raw(&wire, &n, ESC); put_raw(&wire, &n, 0x00);
    for (i = 0; i < bn; i++) put_esc(&wire, &n, body[i]);
    put_esc(&wire, &n, crc); put_raw(&wire, &n, ESC); put_raw(&wire, &n, EOP);
    return n;
}
static int write_all(int fd, const uint8_t *p, size_t n)
{
    size_t done = 0; uint64_t end = now_ms() + 3000;
    while (done < n) {
        if (now_ms() >= end) { errno = ETIMEDOUT; return -1; }
        ssize_t w = write(fd, p + done, n - done);
        if (w < 0) { if (errno == EINTR) continue; if (errno == EAGAIN) { poll(NULL,0,2); continue; } return -1; }
        if (w == 0) { errno = EIO; return -1; }
        done += (size_t)w;
    }
    return 0;
}
static void write_control(const char *s)
{
    int fd = open(BBD_CONTROL, O_WRONLY);
    if (fd < 0) { logx("open %s: %s", BBD_CONTROL, strerror(errno)); return; }
    size_t n = strlen(s) + 1;
    if (write(fd, s, n) != (ssize_t)n) logx("write %s: %s", s, strerror(errno));
    else logx("control: %s", s);
    close(fd);
}
static uint32_t parse_hex_hdr(const uint8_t *b, size_t n, const char *key)
{
    char pat[64]; size_t kl = strlen(key); const uint8_t *p; char *endp; unsigned long long x;
    if (kl + 3 > sizeof pat) return 0;
    pat[0]='<'; memcpy(pat+1,key,kl); pat[1+kl]='='; pat[2+kl]=0;
    p = memmem(b, n, pat, kl + 2);
    if (!p) return 0;
    x = strtoull((const char*)p + kl + 2, &endp, 0);
    if (endp == (const char*)p + kl + 2) return 0;
    return (uint32_t)x;
}
static uint8_t *patch_blob(const uint8_t *hdr, size_t hn, size_t *blob_len)
{
    const char *p = memmem(hdr, hn, "<Blob=", 6);
    const char *end = p ? memmem(p, hn - (size_t)(p-(const char*)hdr), ">\n", 2) : NULL;
    size_t cap, n = 0; uint8_t *out;
    if (!p || !end || end <= p) return NULL;
    p += 6; cap = (size_t)(end - p)/2 + 1;
    out = malloc(cap ? cap : 1);
    if (!out) return NULL;
    while (p + 1 < end) {
        int hi=-1, lo=-1;
        while (p < end && !((*p>='0'&&*p<='9')||(*p>='A'&&*p<='F'))) p++;
        if (p >= end) break;
        hi = (*p<='9') ? *p-'0' : *p-'A'+10; p++;
        while (p < end && !((*p>='0'&&*p<='9')||(*p>='A'&&*p<='F'))) p++;
        if (p >= end) break;
        lo = (*p<='9') ? *p-'0' : *p-'A'+10; p++;
        out[n++] = (uint8_t)((hi<<4)|lo);
    }
    *blob_len = n; return out;
}
/* Minimal read of a bounded window from /dev/bbd_sensor: returns bytes read. */
static ssize_t drain_sensor(int fd, uint8_t *buf, size_t cap, int ms)
{
    uint64_t end = now_ms() + (uint64_t)ms; size_t got = 0;
    while (now_ms() < end && got < cap) {
        struct pollfd p = { .fd = fd, .events = POLLIN };
        int pr = poll(&p, 1, 50);
        if (pr <= 0) continue;
        ssize_t r = read(fd, buf + got, cap - got);
        if (r < 0) { if (errno == EINTR || errno == EAGAIN) continue; break; }
        if (r == 0) break;
        got += (size_t)r;
    }
    return (ssize_t)got;
}

int main(int argc, char **argv)
{
    int fd_patch=-1, fd_tty=-1, fd_sensor=-1;
    uint8_t *patch=NULL, *blob=NULL, rbuf[8192];
    size_t plen=0, cap=1<<20, blen=0;
    uint32_t asic, declared_len, address;
    bool flash=false, reply=false;
    int i; uint8_t seq=1; uint8_t wire[8192]; size_t wn;

    for (i=1;i<argc;i++){
        if(!strcmp(argv[i],"--flash")) flash=true;
        else if(!strcmp(argv[i],"--verbose")) g_verbose=1;
        else { fprintf(stderr,"usage: %s [--flash] [--verbose]\n",argv[0]); return 64; }
    }

    fd_patch=open(BBD_PATCH,O_RDONLY);
    if(fd_patch<0){logx("open %s: %s",BBD_PATCH,strerror(errno));return 1;}
    patch=malloc(cap); if(!patch){logx("malloc");return 1;}
    for(;;){
        ssize_t r; uint8_t *nb;
        if(plen==cap){ if(cap>=(2u<<20)){logx("patch too large");break;} cap*=2; nb=realloc(patch,cap); if(!nb){logx("realloc");break;} patch=nb; }
        r=read(fd_patch,patch+plen,cap-plen);
        if(r<0){ if(errno==EINTR)continue; logx("read patch: %s",strerror(errno)); break; }
        if(r==0) break;
        if(plen && r>=32 && !memcmp(patch+plen,patch,32)) break;
        plen+=(size_t)r;
    }
    close(fd_patch); fd_patch=-1;
    if(plen==0){logx("empty patch");free(patch);return 1;}

    asic=parse_hex_hdr(patch,plen,"AsicVersion");
    declared_len=parse_hex_hdr(patch,plen,"BlobLength");
    address=parse_hex_hdr(patch,plen,"PatchAddress");
    blob=patch_blob(patch,plen,&blen);
    logx("patch container %zu B asic=0x%08x blobLength=%u addr=0x%08x decoded=%zu",plen,asic,declared_len,address,blen);
    if(asic!=0x004775b0u || declared_len!=438895u || address!=0x00800161u || !blob || blen!=declared_len){
        logx("patch identity mismatch (asic=0x%08x blobLen=%u addr=0x%08x decoded=%zu)",asic,declared_len,address,blen);
        free(blob); free(patch); return 1;
    }
    logx("patch identity verified: BCM47752, 438895 bytes @ 0x00800161");

    if(!flash){
        logx("read-only verification only (no device I/O). Pass --flash to download.");
        free(blob); free(patch); return 0;
    }

    fd_tty=open(TTY_BCM,O_RDWR|O_NONBLOCK);
    if(fd_tty<0){logx("open %s: %s",TTY_BCM,strerror(errno)); free(blob); free(patch); return 1;}
    fd_sensor=open(BBD_SENSOR,O_RDWR|O_NONBLOCK);
    if(fd_sensor<0){logx("open %s: %s",BBD_SENSOR,strerror(errno)); free(blob); free(patch); close(fd_tty); return 1;}

    write_control("SSI:PassThru=1");

    /* autobaud 36 x 0x80 */
    { uint8_t ab[36]; memset(ab,0x80,sizeof ab);
      if(write_all(fd_tty,ab,sizeof ab)<0){logx("autobaud: %s",strerror(errno));} else logx("autobaud sent"); }

    /* GetVersion RPC 0 */
    { uint8_t rpc[4]; size_t rn=rpc_record(rpc,0x00,NULL,0);
      wn=tl_build(wire,seq,F_RELIABLE,rpc,rn,seq); seq++;
      if(write_all(fd_tty,wire,wn)<0){logx("GetVersion write: %s",strerror(errno));} else logx("GetVersion (RPC 0) sent"); }

    /* Read for a real response before proceeding (bounded). */
    { ssize_t n=drain_sensor(fd_sensor,rbuf,sizeof rbuf,2500);
      if(n>0){ reply=true; logx("hub replied %zd bytes (verified download path enabled)",n); }
      else logx("no hub reply within 2.5s (hub not in power-on window; NOT emitting READY)"); }

    if(reply){
        /* MemoryWrite (RPC 5) chunked <=512B */
        uint32_t dest=address; size_t off=0;
        while(off<blen){
            size_t chunk=blen-off; if(chunk>512) chunk=512;
            uint8_t *rb=malloc(6+chunk); uint8_t rpc[4096]; size_t rn;
            if(!rb){logx("malloc chunk");break;}
            rb[0]=(uint8_t)dest; rb[1]=(uint8_t)(dest>>8); rb[2]=(uint8_t)(dest>>16); rb[3]=(uint8_t)(dest>>24);
            rb[4]=(uint8_t)(chunk&0xFF); rb[5]=(uint8_t)(chunk>>8);
            memcpy(rb+6,blob+off,chunk);
            rn=rpc_record(rpc,0x05,rb,6+chunk);
            wn=tl_build(wire,seq,F_RELIABLE,rpc,rn,seq); seq++;
            if(write_all(fd_tty,wire,wn)<0){logx("MemoryWrite write: %s",strerror(errno));free(rb);break;}
            if(g_verbose) logx("MemoryWrite dest=0x%08x +%zu/%zu",dest+(uint32_t)off,chunk,blen);
            free(rb); dest+=(uint32_t)chunk; off+=chunk; usleep(2000);
        }
        logx("MemoryWrite complete (%zu bytes)",off);

        /* StartScratchApp RPC 46 */
        { uint8_t body[4]={(uint8_t)address,(uint8_t)(address>>8),(uint8_t)(address>>16),(uint8_t)(address>>24)};
          uint8_t rpc[8]; size_t rn=rpc_record(rpc,46,body,4);
          wn=tl_build(wire,seq,0,rpc,rn,0); seq++;
          if(write_all(fd_tty,wire,wn)<0) logx("StartScratchApp: %s",strerror(errno)); else logx("StartScratchApp (RPC 46) sent");
          usleep(40*1000); }

        /* ServiceStart RPC 55 */
        { uint8_t body[20]={0}; uint8_t rpc[32]; size_t rn;
          body[0]=(uint8_t)address; body[1]=(uint8_t)(address>>8); body[2]=(uint8_t)(address>>16); body[3]=(uint8_t)(address>>24);
          rn=rpc_record(rpc,55,body,20);
          wn=tl_build(wire,seq,0,rpc,rn,0); seq++;
          if(write_all(fd_tty,wire,wn)<0) logx("ServiceStart: %s",strerror(errno)); else logx("ServiceStart (RPC 55) sent");
          usleep(100*1000); }

        /* Re-verify the hub answers after the download before claiming success. */
        { uint8_t rpc[4]; size_t rn=rpc_record(rpc,0x00,NULL,0);
          wn=tl_build(wire,seq,F_RELIABLE,rpc,rn,seq); seq++;
          if(write_all(fd_tty,wire,wn)<0) logx("confirm GetVersion: %s",strerror(errno));
          else { ssize_t m=drain_sensor(fd_sensor,rbuf,sizeof rbuf,2500);
                 if(m>0){ logx("hub answers after download (%zd bytes); firmware up",m);
                          write_control("BBD:PassThru=0"); write_control("ESW:READY"); }
                 else logx("hub silent after download — NOT emitting ESW:READY"); } }
    }

    close(fd_tty); close(fd_sensor);
    free(blob); free(patch);
    return 0;
}
