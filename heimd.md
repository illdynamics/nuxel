wicked@dextronux:/x/nuxel$ lsusb                                                                                           
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub                                                             
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub                                                             
Bus 002 Device 004: ID 04e8:685d Samsung Electronics Co., Ltd GT-I9100 Phone [Galaxy S II] (Download mode)                 
Bus 003 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub                                                             
Bus 003 Device 002: ID 8087:0032 Intel Corp. AX210 Bluetooth                                                               
Bus 003 Device 003: ID 1532:0276 Razer USA, Ltd Razer Blade                                                                
Bus 003 Device 004: ID 13d3:5279 IMC Networks Integrated RGB Camera                                                        Bus 004 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub                                                             
wicked@dextronux:/x/nuxel$ adb devices                                                                                     
List of devices attached                                                                                                   
                                                                                                                           
wicked@dextronux:/x/nuxel$ heimdall version                                                                                
v2.2.2                                                                                                                     
wicked@dextronux:/x/nuxel$ heimdall detect                                                                                 
Device detected                                                                                                            
wicked@dextronux:/x/nuxel$ heimdall print-pit                                                                              
Heimdall v2.2.2                                                                                                            
                                                                                                                           
Copyright (c) 2010-2017 Benjamin Dobell, Glass Echidna https://glassechidna.com.au                                         
Copyright (c) 2021-2024 Henrik Grimler                                                                                     
This software is provided free of charge. Copying and redistribution is encouraged.                                        
                                                                                                                           
Initialising connection...                                                                                                 
Detecting device...                                                                                                        
libusb: error [get_usbfs_fd] libusb couldn't open USB device /dev/bus/usb/002/004, errno=13                                libusb: error [get_usbfs_fd] libusb requires write access to USB device nodes                                              
ERROR: Failed to access device. libusb error: -3                                                                           
wicked@dextronux:/x/nuxel$ sudo heimdall print-pit                                                                         
[sudo] password for wicked:                                                                                                
Heimdall v2.2.2                                                                                                            
[sudo] password for wicked:                                                                               13:40 [132/71210]
Heimdall v2.2.2                                                                                                            
                                                                                                                           
Copyright (c) 2010-2017 Benjamin Dobell, Glass Echidna https://glassechidna.com.au                                         
Copyright (c) 2021-2024 Henrik Grimler                                                                                     
This software is provided free of charge. Copying and redistribution is encouraged.                                        
                                                                                                                           
Initialising connection...                                                                                                 
Detecting device...                                                                                                        
Claiming interface...                                                                                                      
Initialising protocol...                                                                                                   
ERROR: Protocol initialisation failed!                                                                                                                                                                                                                
Releasing device interface...                                                                                              
                                                                                                                           
wicked@dextronux:/x/nuxel$ export HD="docker exec nuxel-heimdall2 heimdall"                                                
wicked@dextronux:/x/nuxel$ export NUXEL_INIT=openrc bash images/mkrootfs.sh                                                
bash: export: `images/mkrootfs.sh': not a valid identifier                                                                 
wicked@dextronux:/x/nuxel$ export NUXEL_INIT="openrc bash images/mkrootfs.sh"                                              
wicked@dextronux:/x/nuxel$ sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo    
wicked@dextronux:/x/nuxel$ sudo flatpak install --system org.gnome.Platform//46                                            
Looking for matches…                                                                                                       
                                                                                                                           
Info: runtime org.gnome.Platform branch 46 is end-of-life, with reason:                                                    
   The GNOME 46 runtime is no longer supported as of April 17, 2025. Please ask your application developer to migrate to a 
supported platform.                                                                                                        
                                                                                                                           
Info: runtime org.freedesktop.Platform.VAAPI.Intel branch 23.08 is end-of-life, with reason:                               
   org.freedesktop.Platform 23.08 is no longer receiving fixes and security updates. Please update to a supported runtime v
ersion.                                                                                                                                                                                                                                               
Info: runtime org.freedesktop.Platform.GL.default branch 23.08-extra is end-of-life, with reason:                          
   org.freedesktop.Platform 23.08 is no longer receiving fixes and security updates. Please update to a supported runtime v
ersion.                                                                                                                    
ersion.                                                                                                    13:41 [99/71210]
                                                                                                                           
Info: runtime org.freedesktop.Platform.GL.default branch 23.08 is end-of-life, with reason:                                
   org.freedesktop.Platform 23.08 is no longer receiving fixes and security updates. Please update to a supported runtime v
ersion.                                                                                                                    
                                                                                                                           
                                                                                                                           
        ID                                                Branch             Op        Remote        Download              
 1. [✓] org.freedesktop.Platform.GL.default               23.08              i         flathub       169,3 MB / 170,0 MB   
 2. [✓] org.freedesktop.Platform.GL.default               23.08-extra        i         flathub        23,7 MB / 170,0 MB   
 3. [✓] org.freedesktop.Platform.GL.nvidia-580-142        1.4                u         flathub         3,7 kB / 331,3 MB   
 4. [✓] org.freedesktop.Platform.VAAPI.Intel              23.08              i         flathub        13,4 MB / 13,6 MB     5. [✓] org.freedesktop.Platform.openh264                 2.4.1              i         flathub       920,7 kB / 976,5 kB   
 6. [✓] org.gnome.Platform.Locale                         46                 i         flathub       804,1 kB / 386,7 MB   
 7. [✓] org.gnome.Platform                                46                 i         flathub       298,2 MB / 367,4 MB   
                                                                                                                           
Changes complete.                                                                                                          
wicked@dextronux:/x/nuxel$ export S=/x/nuxel/build/out/rootfs                                                              
wicked@dextronux:/x/nuxel$ S=/x/nuxel/build/out/rootfs                                                                     
mkdir -p "$S/etc/nuxel/device/s10plus" "$S/etc/udev/rules.d"                                                               
cp -a configs/s10plus/.                       "$S/etc/nuxel/device/s10plus/"                                               
cp -a device/s10plus/90-nuxel-beyond2lte.rules "$S/etc/udev/rules.d/"                                                      
cp -a device/s10plus/nuxel-beyond2lte.conf    "$S/etc/nuxel/"                                                              
# Kernel modules (only if present):                                                                                        
[ -d kernel/s10plus/.build/out/lib/modules ] && \                                                                          
  { mkdir -p "$S/lib/modules"; cp -a kernel/s10plus/.build/out/lib/modules/. "$S/lib/modules/"; }                          
# Vendor firmware blobs (WiFi/BT/panel — only if you have pulled them, §8.3):                                              
[ -d firmware/s10plus/blobs ] && \                                                                                         
  NUXEL_DEVICE=s10plus bash firmware/s10plus/install-firmware.sh \                                                         
      --install --force-pending --rootfs-staging "$S" || true                                                              [nuxel] Device key:       s10plus                                                                                          
[nuxel] Device directory: s10plus                                                                                          
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B0_murata.hcd — blob not present (optional or forced pending)             
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B0_semco.hcd — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B1_murata.hcd — blob not present (optional or forced pending)           
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B0_semco.hcd — blob not present (optional or forced pendin13:42 [66/71210]
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B1_murata.hcd — blob not present (optional or forced pending)             
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B1_semco.hcd — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/bcm4375B1_semco_sem.hcd — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_clm.blob — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_mfg.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_mon.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_sta.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_1rh_es11_b0 — blob not present (optional or forced pending)            
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_1rh_es12_b0 — blob not present (optional or forced pending)            
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_1rh_es13_b0 — blob not present (optional or forced pending)            
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_1rh_es43_b1 — blob not present (optional or forced pending)            [nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_CS01_semco_b1 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_ES00_semco_b0 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_ES01_semco_b0 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_ES02_semco_b0 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_ES03_semco_b0 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_sta.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_mfg.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_mon.bin_b1 — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/bcmdhd_clm.blob — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/nvram.txt_CS01_semco_b1 — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/APBargeIn_AUDIO_SLSI.bin — blob not present (optional or forced pending)         
[nuxel-fw][warn] SKIP     vendor/firmware/APBiBF_AUDIO_SLSI.bin — blob not present (optional or forced pending)            
[nuxel-fw][warn] SKIP     vendor/firmware/APDV_AUDIO_SLSI.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/APSV_AUDIO_SLSI.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/APTV_AUDIO_SLSI.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/AP_AUDIO_SLSI.bin — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/SoundBoosterParam.bin — blob not present (optional or forced pending)            
[nuxel-fw][warn] SKIP     vendor/firmware/bidirmic.bin — blob not present (optional or forced pending)                     [nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-bot-dsp1-spk-prot-calib.bin — blob not present (optional or forced pendin
g)                                                                                                                         
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-bot-dsp1-spk-prot.bin — blob not present (optional or forced pending)    
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-bot-dsp1-spk-prot.wmfw — blob not present (optional or forced pending)   
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-rcv-dsp1-spk-prot-calib.bin — blob not present (optional or forced pendin
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-bot-dsp1-spk-prot.wmfw — blob not present (optional or fo13:42 [33/71210]
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-rcv-dsp1-spk-prot-calib.bin — blob not present (optional or forced pendin
g)                                                                                                                         
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-rcv-dsp1-spk-prot.bin — blob not present (optional or forced pending)    
[nuxel-fw][warn] SKIP     vendor/firmware/cs35l40-rcv-dsp1-spk-prot.wmfw — blob not present (optional or forced pending)   
[nuxel-fw][warn] SKIP     vendor/firmware/cs47l93-dsp1-trace.wmfw — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/dax_param.bin — blob not present (optional or forced pending)                    
[nuxel-fw][warn] SKIP     vendor/firmware/default_configuration.hfd.cfg.json — blob not present (optional or forced pending
)                                                                                                                          
[nuxel-fw][warn] SKIP     vendor/firmware/dual_cal_wide_swide.bin — blob not present (optional or forced pending)          
[nuxel-fw][warn] SKIP     vendor/firmware/dual_cal_wide_tele.bin — blob not present (optional or forced pending)           
[nuxel-fw][warn] SKIP     vendor/firmware/nfc/sec_s3nrn82_firmware.bin — blob not present (optional or forced pending)     [nuxel-fw][warn] SKIP     vendor/firmware/mfc_fw.bin — blob not present (optional or forced pending)                       
[nuxel-fw][warn] SKIP     vendor/firmware/dnn.bin — blob not present (optional or forced pending)                          
[nuxel-fw][warn] SKIP     vendor/firmware/dual_cal_front_subfront.bin — blob not present (optional or forced pending)      
[nuxel-fw][warn] SKIP     vendor/firmware/fimc_is_fw_mcu.bin — blob not present (optional or forced pending)               
[nuxel-fw][warn] SKIP     vendor/firmware/fimc_is_lib.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/fimc_is_rta.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/fmsb.bin — blob not present (optional or forced pending)                         
[nuxel-fw][warn] SKIP     vendor/firmware/rxse.bin — blob not present (optional or forced pending)                         
[nuxel-fw][warn] SKIP     vendor/firmware/setfile_2l4.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/setfile_3j1.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/setfile_3m3.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/setfile_3p9.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/setfile_4ha.bin — blob not present (optional or forced pending)                  
[nuxel-fw][warn] SKIP     vendor/firmware/txse1.bin — blob not present (optional or forced pending)                        
[nuxel-fw][warn] SKIP     vendor/firmware/txse2.bin — blob not present (optional or forced pending)                        
[nuxel-fw][warn] SKIP     vendor/firmware/txse3.bin — blob not present (optional or forced pending)                        
[nuxel-fw][warn] SKIP     vendor/firmware/vts.bin — blob not present (optional or forced pending)                          
[nuxel-fw][warn] SKIP     vendor/firmware/calliope2.dt — blob not present (optional or forced pending)                     [nuxel-fw][warn] SKIP     vendor/firmware/calliope_dram.bin — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/calliope_dram_2.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/calliope_sram.bin — blob not present (optional or forced pending)                
[nuxel-fw][warn] SKIP     vendor/firmware/calliope_sram_2.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/NPU.bin — blob not present (optional or forced pending)                          
[nuxel-fw][warn] SKIP     vendor/firmware/calliope_sram_2.bin — blob not present (optional or forced pending13:42 [0/71210]
[nuxel-fw][warn] SKIP     vendor/firmware/NPU.bin — blob not present (optional or forced pending)                          
[nuxel-fw][warn] SKIP     vendor/firmware/WithLightFixNoBN.SDNNmodel — blob not present (optional or forced pending)       
[nuxel-fw][warn] SKIP     vendor/firmware/epx.bin — blob not present (optional or forced pending)                          
[nuxel-fw][warn] SKIP     vendor/firmware/iva30_rt-makalu.bin — blob not present (optional or forced pending)              
[nuxel-fw][warn] SKIP     vendor/firmware/pp_cfg.json — blob not present (optional or forced pending)                      
[nuxel-fw][warn] SKIP     vendor/firmware/tracker_cfg.json — blob not present (optional or forced pending)                 
[nuxel-fw][warn] SKIP     vendor/firmware/usbin.bin — blob not present (optional or forced pending)                        
[nuxel-fw][warn] SKIP     vendor/firmware/usbout.bin — blob not present (optional or forced pending)                       
[nuxel-fw][warn] SKIP     vendor/firmware/score/camera1/score_br_dmb.bin — blob not present (optional or forced pending)   
[nuxel-fw][warn] SKIP     vendor/firmware/score/camera1/score_br_pmw.bin — blob not present (optional or forced pending)   
[nuxel-fw][warn] SKIP     vendor/firmware/score/camera1/score_ts_dmb.bin — blob not present (optional or forced pending)   [nuxel-fw][warn] SKIP     vendor/firmware/score/camera1/score_ts_pmw.bin — blob not present (optional or forced pending)   
[nuxel-fw][warn] SKIP     vendor/firmware/score/camera2/score_dummy — blob not present (optional or forced pending)        
[nuxel-fw][warn] SKIP     vendor/firmware/score/camera3/score_dummy — blob not present (optional or forced pending)        
[nuxel-fw][warn] SKIP     vendor/firmware/score/develop1/score_br_dmb.bin — blob not present (optional or forced pending)  
[nuxel-fw][warn] SKIP     vendor/firmware/score/develop1/score_br_pmw.bin — blob not present (optional or forced pending)  
[nuxel-fw][warn] SKIP     vendor/firmware/score/develop1/score_ts_dmb.bin — blob not present (optional or forced pending)  
[nuxel-fw][warn] SKIP     vendor/firmware/score/develop1/score_ts_pmw.bin — blob not present (optional or forced pending)  
[nuxel-fw] Install complete (staging: /x/nuxel/build/out/rootfs).                                                          
wicked@dextronux:/x/nuxel$ cd /x/nuxel                                                                                     
SIZE_M=2048    # must be <= the USERDATA partition size; content + slack                                                   
fakeroot sh -c '                                                                                                           
  chown -R 0:0 /x/nuxel/build/out/rootfs                                                                                   
  exec mke2fs -q -t ext4 -L nuxel-beyond2lte -d /x/nuxel/build/out/rootfs \                                                
       /x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs.img '"${SIZE_M}"'M'                                              
e2fsck -fy build/out/s10plus/nuxel-beyond2lte-rootfs.img >/dev/null 2>&1 || true                                           
ls -la build/out/s10plus/nuxel-beyond2lte-rootfs.img                                                                       
-rw-r--r--. 1 wicked wicked 2147483648 14 okt 13:43 build/out/s10plus/nuxel-beyond2lte-rootfs.img                          
wicked@dextronux:/x/nuxel$ mkdir -p /tmp/rfs && sudo mount -o loop,ro build/out/s10plus/nuxel-beyond2lte-rootfs.img /tmp/rfs                                                                                                                          
ls /tmp/rfs            # expect sbin/ or init or bin/sh to exist                                                           
sudo umount /tmp/rfs                                                                                                       
etc  lost+found                                                                                                            
wicked@dextronux:/x/nuxel$                                                                                                 

the heimdall command seems to fail even though the print pit does work?

wicked@dextronux:/x/nuxel$ sudo heimdall flash --BOOT ./build/out/s10plus/nuxel-beyond2lte-boot.img --USER13:51 [655/73261]
s10plus/nuxel-beyond2lte-rootfs.img
Heimdall v2.2.2

Copyright (c) 2010-2017 Benjamin Dobell, Glass Echidna https://glassechidna.com.au
Copyright (c) 2021-2024 Henrik Grimler
This software is provided free of charge. Copying and redistribution is encouraged.

Initialising connection...
Detecting device...
ERROR: Failed to detect compatible download-mode device.
wicked@dextronux:/x/nuxel$ sudo heimdall print-pit --no-reboot
Heimdall v2.2.2

Copyright (c) 2010-2017 Benjamin Dobell, Glass Echidna https://glassechidna.com.au
Copyright (c) 2021-2024 Henrik Grimler
This software is provided free of charge. Copying and redistribution is encouraged.

Initialising connection...
Detecting device...
Claiming interface...
Initialising protocol...
Protocol initialisation successful.

Beginning session...

Some devices may take up to 2 minutes to respond.
Please be patient!

Session begun.

Downloading device's PIT file...
PIT file download successful.

--- PIT Header ---

