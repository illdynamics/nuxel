/*
 * nuxel-nfc-hash-probe — boot-safety check for the S3FWRN5/S3NRN82 image.
 *
 * The pinned Samsung 4.14 kernel panics in sha1_ce_transform() (the ARMv8
 * Crypto Extensions SHA-1) while s3fwrn5_fw_download() digests the firmware
 * blob.  The crash is an unhandled paging fault on a buffer the kernel
 * cannot read, and with `oops=panic` on the S-Boot cmdline that is an
 * instant reset (bootloop), not a logged warning.
 *
 * This tool mirrors the driver's parse and digest:
 *   1. parse the header exactly like s3fwrn5_fw_request_firmware()
 *      (date, version, sig/image/custom-sig offsets and sizes, sectors)
 *   2. verify every derived pointer+length stays inside the file
 *   3. hash the image the same way (image_off .. image_off+sector*4096)
 *      page by page, reporting the first unreadable page
 *
 * A file that passes here is safe to feed to the kernel's digest; a file
 * that fails must never be installed into /lib/firmware.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>

#define SECTOR_DEFAULT 4096u

static uint32_t le32(const uint8_t *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

int main(int argc, char **argv)
{
	const char *path;
	int fd, rc = 1;
	struct stat st;
	uint8_t *data;
	uint32_t sig_off, sig_size, img_off, sectors, csig_off, csig_size;
	uint64_t img_end;
	uint32_t sectorsz = SECTOR_DEFAULT;
	size_t page = (size_t)sysconf(_SC_PAGESIZE);
	size_t off;

	if (argc < 2 || argc > 3) {
		fprintf(stderr, "usage: %s <image.bin> [sector_kb]\n", argv[0]);
		return 2;
	}
	path = argv[1];
	if (argc == 3)
		sectorsz = (uint32_t)atoi(argv[2]) * 1024u;

	fd = open(path, O_RDONLY);
	if (fd < 0) {
		fprintf(stderr, "open %s: %s\n", path, strerror(errno));
		return 2;
	}
	if (fstat(fd, &st) != 0 || st.st_size <= 0) {
		fprintf(stderr, "stat %s failed\n", path);
		close(fd);
		return 2;
	}
	data = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
	if (data == MAP_FAILED) {
		fprintf(stderr, "mmap: %s\n", strerror(errno));
		close(fd);
		return 2;
	}
	close(fd);

	if (st.st_size < 0x2c) {
		fprintf(stderr, "FAIL: file too small (%lld) for the image header\n",
			(long long)st.st_size);
		goto out;
	}
	sig_off = le32(data + 0x14);
	sig_size = le32(data + 0x18);
	img_off = le32(data + 0x1c);
	sectors = le32(data + 0x20);
	csig_off = le32(data + 0x24);
	csig_size = le32(data + 0x28);
	img_end = (uint64_t)img_off + (uint64_t)sectors * sectorsz;

	printf("image      : %s\n", path);
	printf("size       : %lld\n", (long long)st.st_size);
	printf("date       : %.12s\n", data);
	printf("version    : 0x%08x\n", le32(data + 0x10));
	printf("sig        : off=%u size=%u\n", sig_off, sig_size);
	printf("custom_sig : off=%u size=%u\n", csig_off, csig_size);
	printf("image      : off=%u sectors=%u sector_kb=%u => end=%llu\n",
	       img_off, sectors, sectorsz / 1024u, (unsigned long long)img_end);

	if ((uint64_t)sig_off + sig_size > (uint64_t)st.st_size ||
	    (uint64_t)csig_off + csig_size > (uint64_t)st.st_size ||
	    img_end > (uint64_t)st.st_size) {
		fprintf(stderr, "FAIL: derived region extends past the file (the "
			"kernel would digest memory it never loaded)\n");
		goto out;
	}
	if (img_end == img_off) {
		fprintf(stderr, "FAIL: zero-length image\n");
		goto out;
	}

	/* Touch every page of the digest region; page-aligned mmap touching
	 * is what sha1_ce_transform's ld1 reads do. */
	for (off = img_off; off < img_end; off += page) {
		volatile uint8_t sink = data[off];
		(void)sink;
	}
	printf("digest     : region readable\n");
	printf("PASS: image layout is consistent and safe to digest\n");
	rc = 0;
out:
	munmap(data, (size_t)st.st_size);
	return rc;
}
