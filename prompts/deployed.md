Done. Here's the summary.                                                                                                                             
                                                                                                                                                      
## SSH connection                                                                                                                                     
Connected to the Nuxel device:                                                                                                                        
- `root@192.168.178.167`                                                                                                                              
- key: `~/.ssh/wicked_wqn_id_rsa`                                                                                                                     
- Your IP string was truncated at `192.168.178`; live discovery showed `192.168.178.167` is the active nuxel host.                                    
                                                                                                                                                      
## 1. iptables + firewall (wired, NOT enabled)                                                                                                        
- Installed `iptables-legacy` 1.8.11 and its deps on the device.                                                                                      
- Deployed the Python `nuxel-firewall` backend/CLI:                                                                                                   
  - package → `/usr/local/lib/python3.14/site-packages/nuxel_firewall`                                                                                
  - CLI → `/usr/local/bin/nuxel-firewall`                                                                                                             
  - policy → `/etc/nuxel/firewall/policy.json`                                                                                                        
- Fixed a real bug in `services/nuxel-firewall/nuxel_firewall/remote.py` (`ssh_ports` local variable shadowing the function) that made `dry-run` crash
.
- Verified on device:
  - `nuxel-firewall backend-probe` → selects `iptables`
  - `nuxel-firewall self-test` → OK
  - `nuxel-firewall dry-run` → `backend: iptables`, `ok: true`
  - `nuxel-firewall status` → `enabled: false`
- Left it **disabled**:
  - `iptables-legacy -S` still shows `-P INPUT/FORWARD/OUTPUT ACCEPT`
  - no Nuxel chains or rules were applied.

## 2. Zoomed-in desktop before lockscreen on wake
Root cause: `nuxel-wl-fb` force-committed the first post-wake frame (the stale desktop) and unblanked before the launcher had re-asserted the lockscre
en. The launcher lock watcher also only polled every 5s.

Fixes:
- `tools/s10plus/a67/nuxel-wl-fb.c`
  - publishes wake/on state immediately,
  - no longer force-commits a stale full frame while a wake is pending,
  - waits for a real changed frame (the lockscreen) before unblanking,
  - does a full-frame blit of that real first frame,
  - unblanks DECON before writing `bl_power=0` (also fixes `bl_power` staying at 4),
  - holds the fallback longer.
- `pwa/nuxel-home/js/app.js`
  - adaptive wl-fb state polling: 500 ms while panel off, 5 s while on.

      Deployed:
- rebuilt AArch64 on-device and installed to `/usr/lib/nuxel/nuxel-wl-fb`
- deployed the updated `app.js` and reloaded the launcher
- tested via the control FIFO: wake now presents the lockscreen frame directly; no stale desktop flash; `bl_power` returns to 0.

Backups on device:
- `/usr/lib/nuxel/nuxel-wl-fb.prev-pwakefix3-20261107T200338Z`
- `/usr/share/nuxel/pwa/nuxel-home/js/app.js.prev-pwakefix-20261107T195947Z`
(plus earlier `nuxel-wl-fb.prev-pwakefix*` variants)

## 3. Icon between battery and Wi-Fi
That's the **sound mode icon** (speaker).

Current state is `normal`. It indicates:
- `normal` → speaker
- `vibrate` → vibrate bars
- `silent` → slashed speaker

The other in-between candidates (location, Bluetooth, NFC, USB, remote desktop) are currently hidden/off, so the visible one is the sound-mode indicator.
tokens used
24,197,579
[codeseeq] stopping owned bridge process (pid=33955)


---

## 2026-11-07 23:2x — timer/alarm shake, Doom restore, chords, Tangram, speed

**Timer/alarm**
- Lockscreen alarm and timer penguins now shake heavily (whole 12–16 px cell plus artwork, 0.18 s loop) the moment `alarm_ringing` / `timer_ringing` becomes true.
- `nuxel-pwa-host` watches `/run/nuxel/clockd.state` and dispatches `nuxel:clock-state-changed`; the 2 s poll is only a safety net. GIO events are coalesced to one refresh.
- Reduced-motion no longer downgrades the ringing alarm to a silent pulse.

**Nuxel Doom**
- Root cause of "gone": the payload, WASM engine and Freedoom WADs were still on disk, but `org.nuxel.Doom` was absent from the launcher `apps[]` (it survived only as a NuxTore catalogue entry). Registry v16 restores it in the canonical registry, the native-shell registry and the static launcher baseline.
- Sound defaults remain ON (`sound: true`) and the engine config now writes `sfx_volume 15` / `music_volume 8`. The SDL/Emscripten `AudioContext` is explicitly resumed after `callMain()` and on the next trusted gesture, fixing the silent-first-game case where the context was created after the PLAY click.

**Buttons / chords**
- A Power press that arms a Power+Volume chord can no longer also dispatch `power_short` (`screen-toggle`).
- Volume-first chords emit `volume-restore`, which silently puts the mixer back to its pre-press value; Power+VolDn no longer changes volume before the screenshot, and Power+VolUp no longer changes volume before the sound-mode cycle.
- The FSM replay fixture `tools/s10plus/a34/tests/chord-no-side-effects.trace` proves `volume-up → volume-restore → sound-mode-cycle` with no `screen-toggle`.

**Sound indicator**
- The 26 px speaker cell is replaced by a 12 px square: green filled = normal, yellow stripes = vibrate, red outline + slash = silent.
- `nuxel-pwa-host` relays the button manager's `sound-mode <mode>` FIFO line to the launcher immediately (`nuxel:sound-mode`), so the icon changes on the same chord instead of waiting for the 15 s provider poll.

**Tangram / removed apps**
- Removed Flatpak `re.sonny.Tangram` and its per-user data.
- Reinstalled the other recently removed app found in Flatpak history: `com.sindresorhus.Caprine` 2.61.0.

**Performance**
- Launcher registry/Flatpak watch slowed from 5 s to 30 s; the bridge caches `flatpak list` for 20 s and invalidates on install/update/uninstall.
- Home clock widget no longer repaints every second (HH:MM only, minute-aligned), removing the largest continuous WebKit/phoc/wl-fb composite cost at idle.
- Clock-state GIO events are coalesced. Steady-state WebKit measured ~1.9 % of one core and the compositor thread ~0.7 %. The `load average ≈ 12` is dominated by permanent kernel D-state threads (`tz_worker_thread`, `scsi_srpmb_work`, `ree_time`, `tz_iwsock`), not runnable userspace work.

---

## 2026-11-07 23:35 — audio/volume/boot cue/Ferdium mic repair

**Root cause**
- `nuxel-audio-session.sh` started WirePlumber immediately after the `pipewire-0` socket inode appeared. WirePlumber raced PipeWire startup, exited with `Failed to connect to PipeWire`, and was never restarted.
- Without WirePlumber there is no default-node metadata: `pactl set-default-sink` returned `Failure: Not supported`; `nuxel-audio-route.sh` stayed `state=deferred`; `nuxel-soundd` refused every cue (`audio route pending`); the button manager’s `wpctl get-volume` readback failed and fell back to the 0..1 ALSA fader (the exact 0%/100% volume symptom); and PipeWire published the speaker monitor as the default capture source instead of the WDMA1 microphone.

**Fixes**
- `services/nuxel-s10/bin/nuxel-audio-session.sh`: wait for the real PipeWire core object (`pw-cli info 0`), start/supervise WirePlumber with restart-on-exit, and terminate it with the unit.
- `services/nuxel-s10/bin/nuxel-audio-route.sh`: retry `pactl set-default-sink` for up to 10 s while WirePlumber publishes default-node metadata.
- `services/nuxel-s10/systemd/nuxel-audio-route.service`: order the route after `nuxel-audio-session.service`.
- `tools/s10plus/a33/nuxel-sound-cue.py` + `services/nuxel-session/systemd/nuxel-boot-sound.service`: boot fallback now uses the supplied `nuxel-boot-audio.mp3` (soundd already assigned `boot` to that file); volume feedback still uses `nuxel-pow.mp3`.
- Regression assertions added in `tests/pwnage89000/test_boot_readiness.py`; boot fallback test updated.

**Live verification after reboot**
- `nuxel-audio-session.service` active, WirePlumber running, default sink `alsa_output.hw_0_1`, default source `alsa_input.hw_0_13`.
- `nuxel-audio-route.state`: `state=applied`, `calliope=MUB0`, `dsp1=2/2`, `rate=48000`.
- `nuxel-mic-route.state`: `state=applied`, `pcm=hw:0,13`.
- `nuxel-boot-sound.service`: queued `action=boot path=/home/nuxel/Sounds/nuxel-boot-audio.mp3`.
- Volume keys/settings now take 5% absolute steps (verified 50→55→60→65→50), not 0↔100.
- Ferdium Flatpak sandbox: `pactl get-default-source` = `alsa_input.hw_0_13`; a 1 kHz 48 kHz speaker tone recorded with `parecord` inside the Ferdium sandbox came back at 1 kHz with 4.000 s duration and no clipping (peak ≈ 4.2k/32.7k).
- Device host files touched: `/usr/lib/nuxel/nuxel-audio-session.sh`, `/usr/lib/nuxel/nuxel-audio-route.sh`, `/etc/systemd/system/nuxel-audio-route.service`, `/etc/systemd/system/nuxel-boot-sound.service`, `/usr/libexec/nuxel/nuxel-sound-cue`.
- Backup: `/var/backups/nuxel/audio-wireplumber-20261107T223131Z`.
