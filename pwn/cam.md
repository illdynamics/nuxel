ok you can  connect to Nuxel with SSH key ~wicked/.ssh/wicked_wqn_id_rsa to connect to root@10.11.12.99 for a root oncole on the live nuxel device. it is also connected over USB in case we need to flash anything. if anything needs to be flashed through TWRP, you can reboot the phone to recovery mode and flash it via adb. if you then reboot and we end up in TWRP again that means the flash failed or it bootlooped/hung/crashed. so you know that and we can keep running autonomously. if that happens you re-investigate, fix and reflash and reboot until it boots in Nuxel then it was successful.

but we prefer no flashing via TWRP if not needed anymore. but if we have to to get the camera working fully, do it.

so you will now read this prompt and execute it very carefully, accurately and you will not stop until it works, dont mind the time it takes or tokens: ./pwn/ULTIMATE_CAMERA_AGENT_PROMPT.md

also read the 2 other documents so you know the state we are in and the verified public references:
- ./pwn/COMPONENT_STATE_AND_CAMERA_AUDIT.md
- ./pwn/VERIFIED_PUBLIC_REFERENCES.md

and make sure when it works, you deploy it to the live phone as well, check out the ./scripts folder for deplying to live phone.

then also make sure you test it on the phone itself by opening the camera application and making a picture and a video with it and let them be saved in the gallery. and then we can play them back and view them. include sound as well in the video as the microphone already works as well.

Test both the rear and front cameras and create videos and pictures with both. and make sure flashlight/video light works as well. upgrade the camera app to include those configurations and functionalities so we have a full camera app. then also next to our own camera app, also install another camera app via the official fedora repos a native gtk one. then also install a flatpak one and make sure all 3 camera apps work properly.
