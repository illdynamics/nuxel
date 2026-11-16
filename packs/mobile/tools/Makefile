CC ?= cc
CFLAGS ?= -O2 -g
WARNINGS = -Wall -Wextra -Werror -Wformat=2 -Wshadow -Wconversion -Wstrict-prototypes

.PHONY: all clean test
all: s5000ap-status

s5000ap-status: s5000ap-status.c s5000ap_uapi.h
	$(CC) $(CFLAGS) $(WARNINGS) -std=c11 -o $@ s5000ap-status.c

test: s5000ap-status
	./s5000ap-status --decode 0 | grep -F 'OFFLINE'
	./s5000ap-status --decode 4 --json | grep -F '"ONLINE"'
	./s5000ap-status --decode 9 | grep -F 'CRASH_WATCHDOG'
	! ./s5000ap-status --decode 99 >/dev/null 2>&1

clean:
	rm -f s5000ap-status
