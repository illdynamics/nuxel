connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99

then please fix the USB networking, I still have the wrong IP I see in settings it still says 10.15.19.1 make our IP-address and USB net subnet configurable and set it now to 10.100.10.1/24 for the Nuxel phone and we have 10.100.10.2 on the macbook now. please make sure the USB tethering works and enable the usb networking at all.

then test the usb tethering by pinging from my macbook over the right interface via usb tethering. do not disable my macbooks wifi. you are allowed to control my macbook though.

and in power menu remove the option to take a screenshot.

for the quick settings, change some texts:
change "Bluetooth" to "BT"
change "Zerotier" to "ZT"
change "Fingerprint" to "Finger"
change "Camera" to "Cam"
change "Microphone" to "Mic"
change "Paranoid" to "Para"
also remove the "USB Net" quick setting, and move GPS to the top row.
then on second row all the way on the right add "PenGuru" placeholder toggle (for penguru squad LLM network subssystem later)

please make the quick ssettings buttons even less high in height so we have even more space for notifications.

and fix the Hotspot functionality so we are able to use the hostapd daemon and set up our hotspot properly.

and make sure all changes are implemented to our live phone, as well as previous changes from last turn, and nothing else broke again please.

when finished, reboot the phone.
