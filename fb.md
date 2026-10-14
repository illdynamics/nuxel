wicked@dextronux:/x/nuxel$ fastboot devices
no permissions; see [http://developer.android.com/tools/device.html]     Motorola Fastboot Interface
wicked@dextronux:/x/nuxel$ /tmp/fb devices
ZY326RGXCM       Motorola Fastboot Interface
wicked@dextronux:/x/nuxel$ /tmp/fb getvar product
product: ocean
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ /tmp/fb getvar securestate
securestate: flashing_unlocked
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ /tmp/fb getvar serialno
serialno: ZY326RGXCM
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ /tmp/fb getvar current-slot
current-slot: a
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ /tmp/fb getvar running-slot
running-slot: _a
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ /tmp/fb getvar max-download-size
max-download-size: 536870912
Finished. Total time: 0.000s
wicked@dextronux:/x/nuxel$ export FB=/tmp/fb
wicked@dextronux:/x/nuxel$ FBTIMEOUT=120 $FB flash dtbo build/out/g7power/stock/firmware/extracted/dtbo.img
(bootloader) is-logical:dtbo_a: not found
(bootloader) is-logical:dtbo_a: not found
Sending 'dtbo_a' (1760 KB)                         OKAY [  0.094s]
Writing 'dtbo_a'                                   OKAY [  0.039s]
Finished. Total time: 0.475s
wicked@dextronux:/x/nuxel$ BOOT=build/out/g7power/lk2nd-nuxel-final-combined.img FBTIMEOUT=300 $FB flash boot_a "$BOOT"
fastboot: error: cannot determine image filename for 'boot_a'
wicked@dextronux:/x/nuxel$ 

