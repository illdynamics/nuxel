# nuxel-radio-bridge — host or aarch64 build of the system-bus Radio1 forwarder.
# The binary has no runtime dependency beyond glib/gio.
CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra -Werror -std=gnu11
PKGS    := gio-2.0 glib-2.0
GIO_CFLAGS := $(shell pkg-config --cflags $(PKGS))
GIO_LIBS   := $(shell pkg-config --libs $(PKGS))

nuxel-radio-bridge: nuxel-radio-bridge.c
	$(CC) $(CFLAGS) $(GIO_CFLAGS) -o $@ $< $(GIO_LIBS)

install: nuxel-radio-bridge
	install -D -m 0755 nuxel-radio-bridge $(DESTDIR)/usr/libexec/nuxel/nuxel-radio-bridge
	install -D -m 0644 systemd/nuxel-radio-bridge.service $(DESTDIR)/etc/systemd/system/nuxel-radio-bridge.service
	install -D -m 0644 dbus/nl.nuxel.Radio1-bridge.conf $(DESTDIR)/etc/dbus-1/system.d/nl.nuxel.Radio1-bridge.conf

uninstall:
	rm -f $(DESTDIR)/usr/libexec/nuxel/nuxel-radio-bridge \
	      $(DESTDIR)/etc/systemd/system/nuxel-radio-bridge.service \
	      $(DESTDIR)/etc/dbus-1/system.d/nl.nuxel.Radio1-bridge.conf

clean:
	rm -f nuxel-radio-bridge

.PHONY: install uninstall clean
