#!/bin/sh
export PATH=/sbin:/bin
mount -t proc none /proc 2>/dev/null; mount -t sysfs none /sys 2>/dev/null
mount -t devtmpfs none /dev 2>/dev/null
if [ -x /bin/toybox ]; then ln -sf toybox /bin/sh; ln -sf toybox /bin/sleep 2>/dev/null; fi
echo "<6>nuxel-idle: PID1 alive at $(date 2>/dev/null); idling forever (watchdog test)" > /dev/kmsg 2>/dev/null
echo "nuxel-idle: alive" > /dev/console 2>/dev/null
while true; do sleep 3600; done
