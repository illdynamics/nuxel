# Lock, navigation and keyboard tests

The running Home reached its lockscreen and auto-hid verbose boot. It could not be unlocked because this boot has no touchscreen input device. Root cause precedes Home: `androidboot.mode=charger` caused the vendor kernel not to instantiate `sec_ts`.

No userspace restart can create the missing device. Owner recovery: disconnect USB/power, power on normally, wait for the lockscreen, then reconnect USB. Afterward test unlock, Home, short/long Back, Recents, keyboard show/type/hide, lock/wake, and escape from both camera apps. Until observed, these gates are not PASS.
