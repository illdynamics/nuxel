# Host cross-build only; no deployment or hardware access.
CROSS ?= aarch64-linux-gnu-
CC = $(CROSS)gcc
READELF = $(CROSS)readelf
OUT ?= build
WARN = -Wall -Wextra -Werror

.PHONY: all check
all: $(OUT)/isolation-probe $(OUT)/libssp-log-stderr.so

$(OUT):
	mkdir -p $@

$(OUT)/isolation-probe: isolation_probe.c | $(OUT)
	$(CC) -static -O2 $(WARN) -o $@ $<
	! $(READELF) -l $@ | grep -q INTERP

$(OUT)/libssp-log-stderr.so: android_log_stderr.c | $(OUT)
	$(CC) -shared -fPIC -nostdlib -fno-stack-protector -O2 $(WARN) \
		-Wl,-soname,libssp-log-stderr.so -o $@ $<
	! $(READELF) -d $@ | grep -q NEEDED

check:
	python3 -S -m unittest -v test_isolation.py
