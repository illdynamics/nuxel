CC ?= cc
CFLAGS ?= -O2 -g
WARN = -Wall -Wextra -Werror -std=c11
OUT ?= build

.PHONY: all check clean

all: $(OUT)/nuxel_bbd_download $(OUT)/nuxel_bbd_host $(OUT)/nuxel_bbd_flash

$(OUT):
	mkdir -p $@

$(OUT)/nuxel_bbd_download: nuxel_bbd_download.c | $(OUT)
	$(CC) $(CFLAGS) $(WARN) -o $@ $<

$(OUT)/nuxel_bbd_host: nuxel_bbd_host.c | $(OUT)
	$(CC) $(CFLAGS) $(WARN) -o $@ $<

$(OUT)/nuxel_bbd_flash: nuxel_bbd_flash.c | $(OUT)
	$(CC) $(CFLAGS) $(WARN) -o $@ $<

$(OUT)/test_nuxel_bbd_download: tests/test_nuxel_bbd_download.c nuxel_bbd_download.c | $(OUT)
	$(CC) $(CFLAGS) $(WARN) -I. -o $@ $<

$(OUT)/test_nuxel_bbd_flash: tests/test_nuxel_bbd_flash.c nuxel_bbd_flash.c | $(OUT)
	$(CC) $(CFLAGS) $(WARN) -I. -o $@ $<

check: $(OUT)/test_nuxel_bbd_download $(OUT)/test_nuxel_bbd_flash $(OUT)/nuxel_bbd_download
	$(OUT)/test_nuxel_bbd_download
	$(OUT)/test_nuxel_bbd_flash
	python3 -S tests/test_verify_embedded_patch.py
	python3 -S ../ssp-runtime/check_protocol_replay.py --decoder $(OUT)/nuxel_bbd_download --summary

clean:
	rm -rf $(OUT)
