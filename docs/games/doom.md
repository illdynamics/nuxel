# Nuxel Doom

![Nuxel Doom icon](../../pwa/nuxel-apps/doom/icons/icon-192.png)

**Application ID:** `org.nuxel.Doom`  
**Version:** `1.0.0` (shipped with Nuxel `v0.7.6-beta`)  
**Type:** offline-first PWA, installable from NuXtore  
**Content:** original Nuxel game — no DOOM WAD, no commercial sprite or sound
asset is bundled.

Nuxel Doom is a touch-first arcade shooter built for the Nuxel phone. It is not
a desktop DOOM window squeezed onto a phone: the game renders into a 320×180
raycasting framebuffer, scales with nearest-neighbour sampling, and owns a
multitouch HUD designed for two thumbs.

## What ships

- Three original sectors: **Docking Bay**, **Foundry** and **Hellgate**.
- Enemies, doors, pickups, health/armor/ammo, three weapons and sector exits.
- Left-thumb movement joystick with diagonal movement and run threshold.
- Right-side aim surface with configurable sensitivity and optional inverted Y.
- Simultaneous **FIRE**, **USE**, **WPN +/−**, **RUN** and **MENU** buttons.
- Pause/resume, restart, return to campaign and exit.
- Optional audio and Nuxel host haptics.
- Offline settings and progress in local storage.
- Left-handed control layout.
- Fullscreen/immersive mode that hides the top bar and triple buttons.

The game stays playable offline after installation. It never needs a network
connection, an account, a keyboard or a terminal.

## Install from NuXtore

1. Open **NuXtore** from Nuxel Home.
2. Open the **Available** tab.
3. Select **Nuxel Doom**.
4. Press **Install**. NuXtore verifies the signed bundle and every staged file
   digest, then registers `org.nuxel.Doom` with the canonical app registry.
5. Return Home. The Nuxel Doom icon is now in the launcher and app drawer.

The install is a launcher registration against the payload already shipped in
the read-only image. It does not fetch anything from the internet.

## Remove from NuXtore

1. Open **NuXtore** → **Installed**.
2. Select **Nuxel Doom** → **Remove**.

Remove unregisters the launcher entry and preserves the user's settings and
progress. The read-only application payload remains part of the OS image so it
can be installed again without a network download.

## Play

1. Open **Nuxel Doom**.
2. Choose a sector, or press **PLAY DOOM** for sector 1.
3. Move with the left joystick; aim by dragging the right side.
4. Tap **FIRE** and **USE** with the right thumb while moving. Multitouch is
   tracked per pointer, so walking, aiming and firing can happen together.
5. The app requests landscape while playing and restores the previous
   orientation when you pause/exit or the app loses the foreground.

## Fullscreen chrome

While playing, the top bar and the Back/Home/Recents strip are hidden.

- **Swipe up from the bottom edge** to reveal Back/Home/Recents.
  - Back pauses the game while the controls are visible.
  - Home returns to Nuxel Home without killing the game session.
  - Recents opens the app switcher.
- **Pull down from the top edge** to reveal the status bar.
- Both strips hide again automatically after a few seconds.

The same bottom-edge gesture works in other PWA apps. Nuxel Home and the
lockscreen deliberately keep their normal chrome.

## Configuration

The **TOUCH & AUDIO** screen stores:

| Setting | Effect |
|---|---|
| Sound | Weapon, door, pickup, pain and end-of-sector cues |
| Haptics | Nuxel host vibration on fire/use/menu where available |
| Invert look | Reverses vertical aim direction |
| Left handed | Mirrors the joystick, aim surface and action cluster |
| Look sensitivity | Right-side aim multiplier |

There are no text inputs anywhere in the Doom shell. The system keyboard is
explicitly dismissed when the game starts, regains focus, resumes or exits.

## Classic engine

The **CLASSIC ENGINE** button tries to launch an installed Crispy Doom through
the Nuxel Bridge. That path is optional and is not required for Nuxel Doom.
If the classic engine is not installed, the button reports that honestly and
the original Nuxel game remains fully playable.

## Related documentation

- [Touch controls](doom-touch-controls.md)
- [Troubleshooting](doom-troubleshooting.md)
- [v0.7.6-beta release notes](../releases/v0.7.6-beta.md)
- [Original Crispy Doom launcher notes](../doom-touch-launcher.md)
