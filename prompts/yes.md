|---|---|
| Touch | **Samsung S6SY761** (`sec_ts`), I2C 0x48, firmware `y771`/`y771_d`, FOD *(was "Samsung/Synaptics, verify")* |    
| Panel | **Samsung S6E3HA9** (`s6e3ha9_beyond2`), 3040×1440 |
| Audio | **CS47L93** + **2× CS35L40** amps *(was "CS35L41" — that was wrong)* |
| WiFi/BT | **BCM4375** confirmed (`samsung,brcm-wlan` node + teardown) |
| NFC | **Samsung sec-nfc** (S3FWRN5-family) @ 0x27 + embedded SE |

## What I changed

Updated all four files — `g7power-requirements.md`, `nuxel-g7power.md`, `s10plus-requirements.md`, `nuxel-s10plus.md`:     

1. **Hardware profile tables** — filled in real IDs + sources instead of "verify on device".
2. **Driver matrices** — fixed WiFi driver (wcn36xx, not ath10k), touch driver, audio amp model.
3. **Kernel defconfig guidance** — `CONFIG_WCN36XX` + `CONFIG_QCOM_WCNSS_PIL` + `CONFIG_TOUCHSCREEN_ILI2117`.
4. **"Verified facts" in both agent prompts** — touch/panel/audio/NFC/sensor IDs now stated as known.
5. **Phase 0 / open-questions sections** — marked the now-resolved items, and shrank the "unknowns" to what's genuinely left.

## What's *still* genuinely unknown (and still needs the physical device)

- **Camera sensors** (both) and **sensor-hub part numbers** (S10+).
- **Exact firmware blob filenames** under `/vendor/firmware` (chip is known, filename isn't).
- **Modem interface** and **bootloader revision** (for picking matching stock-recovery firmware).
- G7 Power exact **LCM/DDIC name** (only in the stock vendor tree; mainline uses a lk2nd-handoff framebuffer).

One honest caveat I left in: the G7 Power touch controller is now *identified*, but the postmarketOS wiki still has user notes saying the generic image boots with "no touchscreen" on some units — so it's "known + DTS node present, but still verify on your specific unit before trusting it."

Want me to also fold these IDs into the shared `docs/driver-status.md` / `docs/hardware-bringup-prep.md` files so there's one canonical component table, or add a short "hardware IDs" reference doc with the source URLs cited?

