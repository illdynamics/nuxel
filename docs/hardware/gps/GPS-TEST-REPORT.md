# Nuxel S10+ GNSS — Test Report

Clear separation of **MOCKED**, **HOST**, and **LIVE-HARDWARE** results. No
coordinate is fabricated anywhere. A physical GNSS fix has **not** been obtained
(blocked on the proprietary position decoder — see `GPS-BLOCKERS.md`); this is
stated plainly, not hidden.

## 1. Host unit tests (pure logic, no hardware)

| Suite | Result | Notes |
|---|---|---|
| `services/nuxel-gnss/tests/test_nuxel_bbd_tl.py` | **8 passed** | BBD TL framing/CRC/RPC; validates the exact `sample1` byte vector from the GPL `bbd_rpc_lh.c` |
| `services/nuxel-gnss/tests/test_nuxel_control_firmware.py` | **5 passed** | patch parser + BCM4773 identity + real captured firmware decodes to exactly 438895 bytes |
| `tests/a72/test_maps_location_integration.py` | passed (31 total in a72 pair) | Maps/bridge/tile/provider contract agreement |
| `tests/a72/test_location_provider.py` | passed | FakeGeoClue drives the real provider state machine (MOCK) |
| `tests/pwnage42000/test_gnss_provider.py` | passed (23 total in 42000+64000) | GNSS provider power/lease/inventory gating (no hardware) |
| `tests/pwnage64000/test_gnss_completion.py` | passed | completion classifier honesty |
| `tests/pwnage42000/test_geolocation_shim.js` (node) | **18 passed** | source-labelling, timestamp preservation, watch lifecycle (MOCK) |
| `tests/a72/test_maps_core.mjs` (node) | **17 passed** | provider states, staleness, coordinate rejection (MOCK) |

**Host total: 8 + 5 + 31 + 23 = 67 Python + 18 + 17 = 35 Node.**

## 2. Live-device tests (real hardware, bounded, no flash)

### 2.1 Firmware provenance read (read-only)

```
/dev/bbd_patch -> 897113 bytes
<AsicVersion=0x004775B0>  (BCM4773)
<Name=bcm_sensorhub_a1>
<BlobLength=438895>
sha256(file)=0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72
sha256(blob)=56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d
```
**Result: PASS** — firmware present, correct chip, internally consistent.

### 2.2 Bounded LHD hardware session (power + transport + control + cleanup)

Run via `nuxel_lhd.py --session --json --handshake-timeout 8 --observe 3`:

| Check | Result |
|---|---|
| BBD nodes present | PASS |
| GPS power 0→1, readback+verified | PASS |
| FW loaded from `/dev/bbd_patch` (BCM4773, SHA verified) | PASS |
| `/dev/ttyBCM` open (chip wake/IRQ enable) | PASS |
| `SSI:PassThru=1` + `ESW:READY` control write | PASS |
| HW revision (ap_type=2, hw_rev=1) | PASS |
| BBD handshake to `GPS: true` | **NOT REACHED** (SSP/MCU not initialized by proprietary lhd) |
| Position decode | **UNAVAILABLE** (proprietary RPC map) |
| GPS power restored to 0 (cleanup) | PASS |
| `GPSD:CORE_OFF` issued + fds closed | PASS |

Kernel log during session shows SSP reporting the true state: `get_chipid -
MCU is not working`, `ssp_down == true`, `GPS: false` — i.e. the sensor hub
is down because the proprietary `lhd`/`gpsd` initialization RPCs were not
performed. **No unsafe power state; no wedge; no reboot.**

### 2.3 Maps / location provider live state

```
bridge LocationGetStatus -> state=disabled, gnss.blocker=<firmware (stale msg)>,
                            network fallback available via GeoClue (labelled network)
```
The blocker string is stale (it still claims "missing firmware"); see §5.

## 3. What is proven and what is not

| Claim | Proven? | Evidence |
|---|---|---|
| FW present + correct chip + hash | **YES** | §2.1 |
| Power sequencing safe + verified | **YES** | §2.2 rail 0→1→0 |
| BBD transport open + wake | **YES** | §2.2 `/dev/ttyBCM` open |
| BBD TL framing (RX/TX) correct | **YES** | §1 8 unit tests incl. kernel vector |
| Control-string ABI | **YES** | §2.2 writes succeed |
| Receiver-originated fresh GNSS fix | **NO** | blocked on B1 (proprietary lhd/gpsd) |
| Maps displays real GNSS fix | **NO** | blocked (no fix to display) |
| Maps mock/network path correct | **YES** | §1 Maps suites pass |

## 4. Real-world outdoor acceptance (pending B1)

Only after B1: cold-start ≤300 s, warm-start ≤60 s, accuracy ≤50 m, source=GNSS,
timestamp+accuracy present, marker cross-checked against an independent
reference, marker updates after physical movement, disable/restart transitions
correct. Exact coordinates are never committed.

## 5. Required follow-up (reflash-independent)

- Update `services/nuxel-bridge/src/gnss_inventory.py` blocker text to reflect
  the corrected finding (firmware is kernel-embedded; the blocker is the
  proprietary userspace). (Cosmetic but the handoff specifically flagged the
  `READY_FOR_SKY`/blocker string weakness.)

## 6. 2026-11-12 session — permission gate fixed, receiver silence measured

### 6.1 "Capability not granted" was a store/permission bug, now fixed

| Symptom | Root cause | Fix (deployed) |
|---|---|---|
| Enabling Location said `Capability not granted` | `nuxel-permd` was **disabled** at boot (`inactive (dead)`), so `_permd` check/grant failed closed for every app | permD unit now works (`/usr/bin/nuxel-permd.py` was missing) and is **enabled**; bridge seeds absent first-party grants |
| Bridge logged `Grant store refresh failed: Permission denied org.nuxel.Maps.json` | stale `root:root 0600` grant file unreadable by the unprivileged bridge | writers publish `0640 root:nuxel-bridge`; bridge start repairs group-read; deploy no longer overwrites the live store |
| Settings grant of one location switch erased the other | permD `decide()` ignored a standalone delegate record | standalone `location:read` / `location:manage` record resolves as `delegate-grant`; 2 new unit tests |
| Every app call answered "provider unavailable" | `bridge.js` POSTed `/ping` (host serves GET) and cached the failed init as mock mode | GET `/ping`, only successful init cached, `whenReady()` |
| Weather "Use my current location" reported a permission error | treated permD's `{success:true, stdout:"allowed: …"}` as *not granted* | shared allow/deny predicate; uses `location/acquire` with a bounded wait |
| Maps locate after a provider hiccup served a stale fix | `begin_acquisition` reused a lease even when the provider had disconnected | lease is reused only while the provider is ready |

### 6.2 Live acceptance (real app pages, real buttons, on the handset)

Driven through headless Chrome DevTools on `127.0.0.1:8000` (the phone's own web
root), clicking the production buttons:

| App | Action | Result |
|---|---|---|
| Maps | `#use-my-location` | `state=fixed`, fix `network_wifi` ±25000 m, marker drawn at canvas centre (144 blue px), label *"Fresh approximate network location"* |
| Weather | `#use-location` | `Loaded Current location.` with live Open-Meteo values (e.g. `4.9°`, humidity, wind) |
| Settings → Permissions | Maps / Weather | **Location** and **Location control** switches present, both *Allowed* |
| Settings toggle | Location off → on | permD `check` flips `allowed` → `denied (explicit-deny)` → `allowed` |
| Settings toggle | Location control off | `location:manage` denied **while `location:read` stays allowed** |
| Home Quick Settings | Location tile | off → `Location off`, on → `Location searching` (real policy) |

Both orderings (Maps→Weather, Weather→Maps) passed; three consecutive full
runs ended `ACCEPTANCE PASS` after the acquisition-lease fixes (a lease is only
reused while the provider is ready **and** the remembered fix is current; a
fresh acquisition starts only once per stale episode, and status reads never
start one). The Home Quick Setting flips the real global policy; after
re-enabling, the retained position is reported as *stale* until an app asks for
a new acquisition (which produced a fresh fix in <3 s).

### 6.3 Satellite GNSS still not available (honest)

The fix above is the provider (Wi-Fi/IP) position, `gnss=false`. The BCM4773
receiver produced **zero bytes** in a 3 s receive window with the transport open
and the rail on, and the sensor hub stays `NG,NG,NG` (`chip ID retry`, `fail to
initialize mcu`). Satellite GPS cannot be claimed until that is resolved — see
`GPS-BLOCKERS.md` B0/B1.
