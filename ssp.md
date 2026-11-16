connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99

please fix the top bar icon location. I have to go to settings and out of settinsg again before the icons are aligned properly, with the last 2 blocks of the 10 blocks blocked from dispalying icons as there is the camera. when we just boot up the last 2 blocks are still being used and the top bar icon blockers dont work until I open settings and close it again.

and remove "take screenshot" from the power menu when we hold power button please.

then continue the Nuxel Galaxy S10+ BCM47752 SSP sensor-hub recovery.

All 9 tests in `NUXEL_SSP_RECOVERY_V2/test_recovery_v2.py` have passed successfully.

Read and execute the complete engineering mission in:

`NUXEL_SSP_RECOVERY_V2/02_AGENT_CONTINUE_SSP_UNTIL_VERIFIED.md`

Work from the existing repository, preserving previous commits and changes.

Your primary objective is to restore **genuine, physically changing accelerometer and gyroscope readings** from the BCM47752 sensor hub.

Prioritize recovering the matching Android/Bionic runtime and testing the existing Samsung `lhd` implementation. Reuse the available Samsung firmware, driver and vendor components before writing replacements.

Perform all safe research, implementation, builds, simulations and diagnostics independently. Do not stop at a report if further safe engineering work is possible.

Before any firmware transmission, GPIO reset, power sequencing or flashing, establish the protocol and a recovery plan and request my explicit approval.

Once sensor streaming works, integrate and verify automatic rotation.

Provide actual hardware evidence for success, with reproducible test results. If an indispensable external dependency remains, document exactly what is missing and how to obtain it.

all files and ressources you need are located in ./NUXEL_SSP_RECOVERY_V2

if you need to reflash anything thats impossible without TWRP access, you are allowed to reboot into recovery and reflash the phone. if you reflash and it ends up in TWRP again that means I did that and it bootlooped/hung/crashed. then you re-investigate, fix and reflash again until we boot into nuxel again then it was successful.
