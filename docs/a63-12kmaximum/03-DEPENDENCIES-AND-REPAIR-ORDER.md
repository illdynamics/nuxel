# A63 dependency and repair order

1. Preserve rollback data and verify the framed USB console.
2. Establish boot mode and input-device existence before debugging lockscreen JavaScript.
3. Restore a normal boot before any physical touch assertion.
4. Keep Home's static server healthy, then validate battery and launcher assets.
5. Inventory the owner-provided SnekByte archive before merging game source.
6. Validate launcher lifecycle, SnekByte controls, browser, camera escape and rotation on glass.
7. Validate NetworkManager reconnect and core UI after owner-authorized cold boots.

Owners: the vendor kernel owns charger-mode `sec_ts`; NetworkManager owns Wi-Fi; `nuxel-pwa-host` owns direct battery reads; Home owns launcher IDs/lifecycle; phoc/libinput own display/touch transforms; the Exynos media graph owns camera frame availability.
