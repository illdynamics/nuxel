# Owner acceptance

From Home, perform this sequence without using Power to force a repaint:

1. Open and close Settings.
2. Open Calendar and return Home.
3. Pull down and dismiss Quick Settings.
4. Open Terminal, type `Ab 1!`, Backspace once, press Enter, then close it.
5. Open another app and return Home.

Pass means every action is visible immediately and later taps still work. If it
fails, preserve `/run/nuxel-home.state`, button logs, and framebuffer state from
that exact interaction. This sequence is currently `NEEDS_OWNER_TEST`.
