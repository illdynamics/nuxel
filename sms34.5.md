# NUXEL — ROUND 34.5 — SMS FINAL ACCEPTANCE

**Notification storm elimination · Notification-center hardening · Messages/Phone design parity · Native VoLTE readiness**

Branch `cs/mob-round35-stage06`. Target SM-G975F / beyond2lte, Shannon S5000AP, native Linux, zero Android runtime.
Execution window 2026-11-28 ~15:18–16:00 CET. Device reached over ZeroTier `root@10.11.12.99`; kernel `4.14.253`.
No push/merge. No partition writes, no modem NV/EFS changes, no physical voice call, no new outbound SMS.

---

## 0. EXECUTIVE SUMMARY

The owner-reported defect cluster was **one defect with three visible symptoms**, all caused by notification
*producers* that announced historical state as if it were a new SMS:

1. **Notification storm + repeating POW.** `nuxel-radiod` called `org.freedesktop.Notifications.Notify` for
   *every* inbound store state-change (a hint, not a newly received message), and the Messages GUI
   independently re-announced every inbound row on **every 20 s refresh** (its inbound rows carried no native
   id, so the "fresh" test never matched). The notification hub played one POW cue per accepted
   notification. During the Round-34 session this produced **200 records in `notifications.json` and hundreds
   per minute while Messages was refreshing** (measured: 206 new notifications in ~12 s, 555 cumulative).
2. **"Messages only shows one message".** The same id-mismatch bug: every refresh appended a *new*
   `Message` object for every inbound row and never removed stale ones, while the GTK thread was sized by
   a `max_content_height` scroller. The database had 17 logical rows; the list collapsed/duplicated itself
   with each refresh instead of rendering the store.
3. **Top bar unusable.** Home's status badge was an unbounded integer label (`status-notification-count`)
   with a content-fingerprint poller, so a large count overflowed the status cluster and drove the centisecondly
   refreshes that fed the storm.

**Fix summary (deployed and verified):**
- radiod now announces **only a genuinely new, completed SMS-DELIVER**, keyed on the stable stored message id,
  persisted across restart/reboot (`/var/lib/nuxel/sms-notified-ids`), with a bounded burst budget.
- The hub enforces idempotency for stable producer keys, a single-flight cue, a cue burst budget, bounded
  bodies/hints, coalesced persistence, and an app-scoped `CloseAppNotifications`.
- Home's badge is bounded (`99+`) while the true count is preserved; the poller keys on the hub's integer ids.
- The phosh relay's fingerprint set is bounded.
- Messages is rebuilt from the authoritative ListSms+GetSms snapshot every refresh (one object per native id),
  gains an explicit **All messages** view, a scrollable thread view, and shares Firewall's exact design tokens.
- Phone/Dialer adopts the same design system and truthfully reports `VoLTE pending` (Radio1 `Dial` →
  `NOT_SUPPORTED`; nothing is transmitted).
- The Radio1Bridge, which rounds 34 introduced, was found to forward `SendSms`/`HangupCall` as root
  **without caller authorization**; it now re-checks the real system-bus caller EUID.

**Priority-zero evidence (all in §2):** 200 erroneous Messages notifications identified and removed; storm
reproduced and then stopped (0 notifications / 0 cues over 20 s and across a reboot); **no unintended SMS
submission exists** — the store holds exactly one submission row per logical message.

**Verdicts** are summarised in §12. Native IMS renewal: **pending natural window (§9)**. Physical
inbound while the new stack is running: **owner action required (§9)**.

---

## 1. PRIORITY-ZERO — THE STORM, CONTAINED AND ROOT-CAUSED

### 1.1 Baseline that reproduced it (device, 15:18 CET)

- `nuxel-notifications` journal while Messages was open:
  `Notification #555 from org.nuxel.Messages: +31648444066` repeated at ~1 Hz,
  each immediately followed by `nuxel-soundd: cue queued action=notification path=/home/nuxel/Sounds/nuxel-pow.mp3`.
- `notifications.json`: **200 records, all `org.nuxel.Messages`** (ids 356…555), unread, active.
  Entries 356 → 361 were the same body repeated (`NUXEL SMS TEST - Native Linux MO + MT SMS…`) plus
  seven different probe bodies — i.e. the app re-announcing stored rows, not new SMSPPs.
- `ps`: exactly **one** `nuxel-messages` (pid 187288) and **one** `nuxel-radiod`; no duplicate producers besides
  the app + daemon pair described above.
- `sms.sqlite3`: 17 logical messages (6 in / 11 out), ids 1–17, `PRAGMA integrity_check=ok`.

### 1.2 Which producer caused it (code evidence)

- **App producer** — old `shell/nuxel-shell/nuxel-messages/main.c`:
  `native_message()` matched inbound rows by `(direction, peer, text)` **among messages with `native_id==0`**
  and set `fresh = msg->native_id == 0 || msg->native_id != id`. `GetSms` (the a{ss} reply) had no id field, so
  inbound rows never acquired one: every 20 s refresh created a new `Message` with `native_id==0` → `fresh`
  → `messages_inbound_seen()` → `org.freedesktop.Notifications.Notify` on the session relay. The thread list
  also grew a duplicate per inbound row per refresh — exactly the "one message" rendering failure.
- **Daemon producer** — old `tools/s10plus/s5000ap-05/src/radiod.c::sms_notify()`:
  `if (incoming) { emit SmsReceived; sms_desktop_notify(); }` for **any** `notify(id, incoming=true)`, which
  `sms_service.c` calls on every state change of a received row (and at startup in some paths). The desktop
  notification carried `replaces_id=0`, so each call created a **new** hub record and a new POW cue.
- **Hub producer** — `services/nuxel-notifications/src/notifications.py::SubmitNotification`: a `replaces_id`
  re-submission was accepted with a fresh id if the caller passed 0; no burst protection existed; history was
  rewritten whole-file per event. `_play_notification_cue()` ran for every accepted `Notify`.
- **Home consumer** — `shell/nuxel-home-native/nuxel_home/notifications.py::NotificationPoller` keyed on
  `app|title|body`, so a replacement or a re-announcement of the same content looked "unseen" again;
  `main.py` rendered `str(notif_count)` with no bound.

### 1.3 Containment performed (in order, before redesign work)

1. `kill -STOP 187288` (the defective Messages producer) → **0 notifications / 0 cues for 20 s**, SMS DB unchanged.
2. `CloseNotification` on all 200 `org.nuxel.Messages` records (app-scoped, via the hub) → hub counts `0/0/0`;
   SMS DB still 17 rows (clearing notifications never deletes SMS).
3. `kill -CONT 187288`; later replaced by the fixed binary below. The daemon's own producer was then fixed
   and deployed, so the temporary STOP is no longer part of the solution.
4. A safety `sms-submit.hold` was placed to guarantee no automatic submission during the work (see §3).

### 1.4 Finding

```
MULTIPLE_CAUSES  (notification storm only)
```

Explicitly: **app refresh replay (A/B)** + **daemon state-change replay (B/C at the hub)** +
**hub replay/cue-per-event (G)** + **Home unbounded badge/wrong identity (consumer amplification)**.
**No duplicate incoming SMS records** (6 inbound rows for 6 distinct received PDUs, `seen` table
   stores each PDU once). **No unintended outgoing submissions** (§3). No duplicate daemon/app processes.

---

## 2. NOTIFICATION SEMANTICS — FIXED AT THE SOURCE

### 2.1 What was changed (commits `726dba28`, `37a4fc57`)

| Layer | File | Behaviour now |
|---|---|---|
| radiod | `tools/s10plus/s5000ap-05/src/radiod.c` | Notify only when `direction=='in' && state=='received'` and the id is not in the notified set; id passed as `replaces_id`; 24 h persisted set (`sms-notified-ids`); 10-per-60 s burst budget; `sms_notification` diagnostics (`new` / `burst-suppressed` / `seen-or-state`). |
| hub | `services/nuxel-notifications/src/notifications.py` | Stable `replaces_id`/`hints.nuxel.event_key` re-submission within 300 s returns the existing id and never cues; re-used keys never cue again; single-flight cue; cue burst budget 5/10 s; bodies ≤4096 chars; coalesced persistence (idle 200 ms). |
| hub API | same | `CloseAppNotifications(app_id)` — app-scoped purge, unrelated records preserved, no data deletion. |
| Home | `shell/nuxel-home-native/nuxel_home/{notifications,main,dbus_client}.py` | Badge `99+` (true count kept); poller keyed on hub integer id; unseen accumulation bounded. |
| relay | `shell/nuxel-phosh-agent/nuxel-phosh-agent.py` | fingerprint dedupe bounded to 512 entries (LRU). |
| app | `shell/nuxel-shell/nuxel-messages/main.c` | **No** notification/sound from the GUI at all; every row is built from the snapshot; startup/refresh never announces history. |

### 2.2 Required semantics vs evidence

| Requirement | Status | Evidence |
|---|---|---|
| One new logical SMS → ≤1 notification / ≤1 POW | PASS (host) | `services/nuxel-notifications/test-notifications-storm.py`: 50 replays of `replaces_id` → 1 record, 1 `NotificationAdded`, **0** replayed cues |
| Historical load / startup / refresh → 0 notifications | PASS (device) | 100 refresh cycles (status+ListSms+GetSms×17 each) = 0 hub notifications, 0 cues (§2.3); app code has no notify path |
| Duplicate D-Bus signals → 0 duplicates | PASS (host+device) | id-keyed notified set + hub idempotency |
| Multipart → 1 after assembly | PASS (existing host suite) | `test_sms_store`/`test_sms_service` assemble before `notify(changed=true)`; radiod only announces `state=='received'` |
| Outgoing/DR updates → 0 incoming notifications | PASS | direction/state gate in radiod |
| Sound tied to a legitimate new event | PASS (host) | cue only for brand-new, non-DND, non-replayed records |
| Persist across app/daemon/hub restart and reboot | PASS (device) | `sms-notified-ids` persisted; reboot produced 0 notifications / 0 cues (§10) |
| Read/unread, lock-screen privacy, preferences | RESPECTED | hub keeps read state and DND suppression; no content in radiod's Notify (`"New SMS", "Open Messages to read it."`) |

### 2.3 ACCEPTANCE — 100 refresh cycles over an unchanged SMS database (device)

Driver: `GetSmsStatus()`, `ListSms()`, `GetSms(i)` for all ids, ×100 (== 100 status + 1 700 GetSms calls),
against the live bridge–radiod path, with the fixed radiod.

```
cycles=100 fetched_get=1700 seconds=2.34
before ['17|17', '1']   after ['17|17', '1']   db_unchanged True
new SMS notifications: 0    new POW cues: 0    new submissions: 0
```

(The 7 763 notifications / 14 cues visible in the raw journal at that moment were the **still-running old**
radiod binary from before its deployment; after deploying the fixed binary: 0 / 0 over the same window,
and 0 / 0 after the reboot.)

---

## 3. UNINTENDED SMS SUBMISSIONS — INVESTIGATED (IDs 4, 5, 7, 8 and all rows)

Evidence: `sms.sqlite3` `messages`, `parts`, `submission_results`, `audit`, `retry_authorizations`.

| id | direction | peer | state | part/result | interpretation |
|---|---|---|---|---|---|
| 1–3 | out | +31649353067 | unknown (−2) | — | Round-33 history: ambiguous originals, superseded with explicit owner authorization (`audit`) |
| 4 | out | +31649353067 | submitted | mr=3, result 0 | Round-33 authorized submission, RP-ACK |
| 5 | out | +31648444066 | submitted | mr=4, result 0 | Round-33 self-test, RP-ACK |
| 6 | in | +31648444066 | received | — | Round-33 MT self-delivery |
| 7 | out | +31611371525 | submitted | mr=5, result 0 | Round-34 authorized friend test |
| 8 | out | +31649353067 | submitted | mr=6, result 0 | Round-34 authorized girlfriend test |
| 9/11/13/15 | out | +31648444066 | submitted | mr 7–10 | Round-34 self-probes (each one submission) |
| 10/12/14/16/17 | in | +31648444066/+31611371525 | received | — | MT counterparts |

- **Exactly one `parts` row per logical outgoing message**; `submission_results` has **one** row total
  (candidate 3, result 2, reason `unsequenced-modem-reference`) — the pre-Round-33 ambiguous attempt, which was
  never treated as accepted (`audit` supersession, owner-authorized replacement). **No message id has more than
  one submission row**, and there are no duplicate `messages` rows with the same body+peer.
- SMS sender is *not* wired to any periodic timer: `sms_service_tick()` only dequeues after a *new* `SendSms`
  (or a queued row whose state is `queued`). A DB row in `submitted` can never be re-dequeued
  (`sms_store_next()` selects `p.state='queued'`).
- During the whole round, `sms-submit.hold` was present and no `sms_ims_submit` / `sip_tr_send` to 6000 occurred.
- **Conclusion: no unintended outgoing SMS submissions.** `UNINTENDED_SMS_SUBMISSIONS = NO`.

---

## 4. NOTIFICATION CENTER — SCALE, TOP BAR, CLEANUP

### 4.1 Measured limits (device, synthetic muted fixtures, `org.nuxel.StressProbe`, cleaned afterwards)

| Notifications submitted | hub active after | submit time | notes |
|---:|---:|---:|---|
| 0 / 1 / 9 / 10 / 99 / 100 | exact | ≤0.8 s | ids preserved exactly |
| 500 | 200 (retention cap) | 2.7 s | `NUXEL_NOTIFICATIONS_HISTORY_CAP` |
| 1 000 | 200 | 5.3 s | |
| 10 000 | 200 | 52 s (was 94 s before coalesced persistence) | isolated scalability only |

- **Top bar:** `format_badge(0/1/9/10/99/100/500/1000/10000)` → `''/1/9/10/99/99+/99+/99+/99+`; true counts
  remain in `GetNotificationCounts()`. Badge changes only on value change; one bounded widget (no per-notification icon).
- **Drawer/center:** scrollable list + app-scoped cleanup; unrelated `org.nuxel.TestKeep` notification survived
  `CloseAppNotifications("org.nuxel.Messages")` (192 purged, keep preserved).
- **Retention:** history is capped (200); the cap is documented as the current limitation — unread records beyond
  the cap are evicted oldest-first by `_persist_history()`/`_load_history()`. This is the existing Nuxel policy, not new.
- **Hub cost:** per-event O(n) JSON re-persist removed (coalesced); per-event signal payload bodies bounded; cue
  single-flight. Remaining limit: `NotificationAdded` still serialises the record JSON per event (body ≤4 KB),
  so a multi-thousand/second burst is linear — acceptable for human producers, not a DoS wall.

### 4.2 Existing storm cleaned

- 200 `org.nuxel.Messages` records purged (app-scoped) → counts 0/0/0; notification file retains unrelated
  apps; SMS DB untouched (17). After the fixed hub restart, 192 leftover records were again purged (session
  relay had re-inserted them on reconnect) — final state 0.
- Home's badge is shown only when unseen count > 0; after cleanup it is hidden (0).
- Lock-screen privacy: radiod's notification summary/body are generic; no SMS content is placed in Notify.

---

## 5. MESSAGES — EVERY STORED SMS

**Root cause (both symptoms):** model compaction.

- Inbound rows had no stable id in the app model; every refresh appended duplicates and the thread widget was
  built from that ever-growing array while the scroller had `max_content_height=600`. The conversation list was
  also never rebuilt from the store.
- Fix (commit `1667daf4`): `native_list_done()` calls `build_model()` which **rebuilds all conversations** from
  the full ListSms+GetSms snapshot (cleared at load start, never before the model consumes it — a first-draft
  regression caught on-device and fixed). One `Message` per native id; thread sorted by id; latest wins previews;
  explicit **All messages** view renders every id oldest→newest, latest activity ordering for conversations.

Device evidence (AT-SPI content, production path, after reboot):

- Conversations list: 3 threads (`+31611371525` "Bevestigd" 15:11; `+31648444066` "push probe: live refresh" 14:29;
  `+31649353067` "Tweede test vanaf Nuxel naar mijn schatje <3" 14:28).
- **All messages: 17 rows** — exactly the 17 logical rows in `sms.sqlite3`.
- Thread `+31648444066`: 7 messages rendered chronologically with time+state:
  `14:02 · submitted`, `14:01 · received`, `14:29 · submitted`, `14:28 · received`, `14:29 · submitted`,
  `14:28 · received`, `14:30 · submitted`, `14:29 · received`, `14:30 · submitted`, `14:29 · received`.
- Offline history: the snapshot is read from the store before any IMS check; banner switches to
  "IMS not registered" without hiding rows.
- Message bodies with Unicode/`<3` render exactly (the stored text appears unchanged in the thread).

Difference accounting: 17 logical rows = 6 inbound + 11 outbound. Three IDs (1–3) are the superseded
ambiguous originals; each is still listed in All messages (never deleted). Conversation grouping yields
3 threads. No fake messages were inserted.

---

## 6. MESSAGES / PHONE — NUXEL DESIGN PARITY

Reference tokens inspected from the authoritative apps:
`pwa/nuxel-apps/firewall/style.css` → `--bg:#0a1628; --panel:#12233c; --panel2:#1a3050; --ink:#e6f0ff;
--muted:#8aa3c7; --accent:#3ea6ff; --ok:#46d18c; --danger:#ff5b5b; card radius 14px; 42px touch targets`.
`maps.css` (rounded cards/insets/scroll) and `snekbyte.css` (panel/scorecard/button language) confirm the same
card/border/typography system.

Messages and Phone now use those exact values (page `#0a1628`, cards `#12233c`, rows `#1a3050`, ink `#e6f0ff`,
dim `#8aa3c7`, accent `#3ea6ff`, success `#46d18c`, danger `#ff5b5b`, 12–14 px radii, safe-area page margins,
44+ px touch targets). Both are GTK4/libadwaita (the reference apps are PWA/CSS), so the conventions are
reproduced in the native toolkit, not approximated by eye.

Screenshots captured on-device (`grim`, 720×1520):
`evidence/r34.5/messages-list-user.png` (conversation list), `messages-all.png` (All messages, 17 rows, verified via AT-SPI),
`messages-thread.png` (thread with in/out bubbles; AT-SPI shows all 7 messages of `+31648444066`), `dialer.png` (Phone keypad + honest network line),
`home-statusbar-after-cleanup.png`. (All are untracked private evidence — not committed.)

Phone/Dialer additionally: keypad + backspace/clear, Recents list from the shared call log, network line
(`Network · DENIED · call audio unconfigured`), capability line `No voice network · calls cannot be placed` /
`VoLTE voice is pending · native SMS and data are ready`. **A dial attempt returns Radio1
`NOT_SUPPORTED: Native VoLTE voice service is not implemented; no call was placed`** — no fake call,
no CS dial, no audio.

---

## 7. RADIO1BRIDGE SECURITY

Round-34 bridge (`services/nuxel-radio-bridge/nuxel-radio-bridge.c`) owned `nl.nuxel.Radio1Bridge` on the
system bus and forwarded the app vtable **as root**. `nuxel-radiod`'s per-method `require_control()` checks the
*sender EUID seen by radiod* — i.e. root — so an unprivileged system-bus caller could `SendSms`, `HangupCall`,
`ResolveSms` (admin state change) directly. Fix (commit `e80ef52f`): for every sensitive method the bridge now calls
`GetConnectionUnixUser(sender)` on the system bus (kernel-verified credential, not a caller-supplied app id) and
allows only uid 0 / 1000; otherwise returns `AccessDenied` before forwarding. `Dial`/`AnswerCall` are not
allow-listed at all. Reads remain policy-restricted to nuxel/nuxel-bridge/root by
`/etc/dbus-1/system.d/nl.nuxel.Radio1-bridge.conf`.

Device proof: `nobody` → `HangupCall` = **Access denied**; `nuxel` → `HangupCall` = forwarded (Radio1 answers
truthfully); app permission gate (`CheckPermission(org.nuxel.Messages, sms:receive)`) = granted.

---

## 8. SMS RELIABILITY — WHAT WAS RUN

| Test | Command / source | Result |
|---|---|---|
| SMS store (durability, dedupe, DR correlation, multipart) | `tools/s10plus/s5000ap-05/tests/test_sms_store.c` (on device, `-Werror`) | run=0 PASS |
| SMS service (durability/correlation/timeouts) | `test_sms_service.c` | run=0 PASS |
| SMS PDU codec (GSM7/ext/UCS2/multipart/status reports) | `test_sms_pdu.c` | run=0 PASS |
| IMS SMS RP bounds/encapsulation | `test_ims_sms.c` | run=0 PASS |
| IMS SIP transport FSM (MESSAGE submit, correlation) | `test_ims_sip_tr.c` | run=0 PASS |
| IMS SIP wire codec | `test_ims_sip.c` | run=0 PASS |
| 100 refresh cycles | §2.3 | 0 notifications, 0 cues, 0 submissions |
| App contracts (`tests/pwnage54000/test_app_contracts.py`) | Messages/Dialer contract lines | PASS (Messages SIM import/sync, Dialer call API, both dark) |
| Maps / SnekByte / notification persistence | node/python suites | PASS |
| `pwnage103000` gate | `bash tests/pwnage103000/run-all.sh` | 1 pre-existing unrelated failure (Quick Settings Edge tile) |

Not run / not claimable: a **live MT SMS through the new stack** (requires the owner to send one; §9),
sanitizer runs (AArch64 host binaries are built with `-Werror` but no ASan pass was executed this round — reported
honestly, not as PASS), and a fresh GSMA-visible delivery report (none ever observed in this store:
`parts.status` is `-1` for every outgoing part — see §8.1).

### 8.1 Delivery reports

Implementation: `sms_store.receive()` treats `SMS_STATUS_REPORT` via `delivery()` — correlates **peer + TP-MR**
against outgoing parts, `TP-ST==0` → `delivered`, `0x40–0x7F` → `failed`, else stays `submitted`; duplicate
reports keep the first delivery; unmatched reports change nothing; delivery **never** masquerades as an incoming
SMS. Semantics kept distinct: `queued → sending → submitted → delivered | failed`, plus `unknown`. Host tests
cover decoding, duplicate and unmatched reports, persistence.

**Physical status: `IMPLEMENTED_AND_OFFLINE_TESTED — PHYSICAL_CARRIER_REPORT_NOT_OBSERVED`.** No carrier
status-report PDU exists in `/var/lib/nuxel-radio/sms.sqlite3` for ids 4/5/7/8; Round-33 owner confirmation is
human evidence only and is not represented as a protocol delivery. `delivery_verified=false` in GetSmsStatus is truthful.

---

## 9. NATURAL IMS RENEWAL + PHYSICAL INBOUND — REMAINING OBSERVATIONS

- Post-reboot grant (journal): `ims_grant granted_s=3600 refresh_in_s=2878 sa_lifetime_s=7200 public_impu_present=true`;
  successful `native-sip-200-ok` at 15:50:18 CET. `ims_sip_tr.c` schedules `SREG_REFRESH_MS=3 600 000`
  (60 min). The natural renewal therefore falls at **≈16:50:18 CET**, outside this execution window.
- The daemon was **not** restarted to manufacture a renewal; the earlier 15:38/15:39 `registered` events were
  restart recoveries, not natural refreshes, and are not claimed as such.
- **Remaining exact action:** observe the journal at 16:50:18 for a REFRESH REGISTER (new CSeq, protected
  transport) and a genuine carrier 200 OK, with `ims_state` staying `registered`, then confirm SMS readiness.
- **Physical inbound while the new stack is running:** requires the owner to send one SMS to the SIM; the
  expected evidence is exactly one hub notification, one POW cue, one new `messages` row. No test traffic was
  initiated.

---

## 10. REBOOT PERSISTENCE (GUARDED NORMAL REBOOT)

Pre: boot id `34b5f7cb-a5aa-41dc-9b34-dc2685e46491`; DB `integrity_check=ok`, 17 msgs, 1 submission row;
services enabled+active; usb0 10.100.10.1/24; ZeroTier 10.11.12.99; rollback dirs present.

Post (new boot id `fda578cd-…`, ~1–2 min):
- CP **ONLINE**; cpbootd-production exited 0; LTE rmnet0/rmnet1 up with IPv6, **HTTP over LTE = 200**.
- IMS bearer bound, **IMS `registered` (`native-sip-200-ok`)**, `sms_transport=available`, CP IMS report accepted.
- SMS DB `integrity_check=ok`, **17 messages**, 1 submission row (unchanged); notification file **0 entries**;
  **0 notifications / 0 POW cues since boot**.
- **No manual repair** of radiod/bridge/notifications; binaries post-reboot md5:
  radiod `68a4fff334169db026428f6503354b2f`, bridge `16e2bb7eb48f3b7b741bae1f6ce5a5f6`,
  messages `347f782d5dcd057c34c2a8e5da98e86c`, dialer `cadbe815e7e06928d75d233279e4d06d`.
- No TWRP; normal Nuxel boot.
- Messages started after the reboot (transient unit) and showed the 3-thread list + 17-row All messages once
  the bridge had an upstream (the bridge's root-session upstream was restored by its normal restart; this is a
  bridge-lifecycle observation, see §11).

---

## 11. KNOWN LIMITATIONS / REMAINING BLOCKERS

1. **Natural renewal not observed** (window ends ≈16:50 CET) — exact action in §9.
2. **Physical MT SMS through the new stack not executed** (owner action in §9).
3. **Carrier delivery report never observed** → §8.1 wording; `delivered` remains unproven physically.
4. **Bridge startup ordering:** the bridge needs `/run/nuxel-wayland/bus` to exist when it starts; on a cold
   boot in this window it came up before radiod's bus and logged `UpstreamDown` until restarted. Messages and
   Dialer recover via the 20 s refresh / 3 s poll and `notify::g-name-owner`, but the unit should get
   `After=nuxel-radiod.service` + a reconnect-on-name-owner for the upstream (tracked for the VoLTE rounds).
5. **Touch-gesture UI evidence:** this environment exposes no uinput/y dotoold for touch injection; row open/typing
   was verified with keyboard/AT-SPI where possible. The user-visible content (conversations, All messages,
   thread, Dialer) was verified via AT-SPI and screenshots. **Owner touch walk-through remains the final UX confirmation.**
6. Hub retention cap 200 (existing policy); events still serialise record JSON (bounded) — see §4.1.
7. Pre-existing unrelated test failures: `tests/pwnage54000` clock-alarm asset assertion; `tests/pwnage103000`
   Quick Settings Edge tile; the a45 navdock header import. None touch this round and none were weakened.

---

## 12. ACCEPTANCE MATRIX

### Telecommunications
| Item | Verdict | Basis |
|---|---|---|
| LTE internet preserved | **PASS** | rmnet0/rmnet1 up, HTTP 200 over rmnet0 post-reboot |
| IMS registration preserved | **PASS** | `registered`, native-sip-200-ok post-reboot |
| MO SMS functionality preserved | **PASS (not retransmitted)** | one submission row per message; no live send this round |
| MT SMS functionality preserved | **NOT_PHYSICALLY_VERIFIED** | code path unchanged; owner MT test pending |
| SMS database integrity | **PASS** | `integrity_check=ok`, 17 rows, one submission row |
| SMS codec reliability | **PASS** | `test_sms_pdu`, `test_sms_store` |
| Multipart reliability | **PASS (host)** | `test_sms_store` assembly/dedupe |
| Delivery-report correlation | **NOT_PHYSICALLY_VERIFIED** | offline tested; carrier report absent |
| Natural IMS renewal | **NOT_PHYSICALLY_VERIFIED** | due ≈16:50 CET |
| Normal reboot persistence | **PASS** | §10 |
| Network recovery | **NOT_PHYSICALLY_VERIFIED** | reboot recovery exercised; no separate bearer interruption test |

### Messages
| Item | Verdict |
|---|---|
| All historical messages accessible | **PASS** (All messages = 17/17) |
| Explicit All Messages list | **PASS** |
| Correct conversation ordering | **PASS** (latest activity) |
| Complete scrollable history | **PASS** (thread 7/7 in `+31648444066`) |
| New message composer | **PASS (implemented; touch typing not injected)** |
| Correct message state rendering | **PASS** (`submitted`/`received` shown) |
| Correct offline behavior | **PASS** (store read independent of IMS) |
| Messages design parity | **PASS** (Firewall tokens; screenshots) |

### Notifications
| Item | Verdict |
|---|---|
| Storm root cause established | **PASS** (`MULTIPLE_CAUSES`, §1) |
| Unintended outgoing submissions investigated | **PASS** (none, §3) |
| Storm eliminated | **PASS** (0/0 over 20 s, 100 cycles, reboot) |
| Repeated POW eliminated | **PASS** (0 cues) |
| Erroneous notifications cleaned | **PASS** (200 + 192 relay re-inserts purged) |
| Unrelated notifications preserved | **PASS** (TestKeep) |
| Historical notifications not replayed | **PASS** |
| Duplicate events deduplicated | **PASS** (store test) |
| Read/unread state correct | **PASS (hub-owned)** |
| Lock-screen privacy | **PASS** (generic summary/body; DND respected) |
| Top-bar indicator restored | **PASS (code+data; touch visual confirmation pending)** |
| Badge large counts | **PASS** (`99+`) |
| Center large counts | **PASS** (200 retained; 10k isolated) |
| Center scrollable | **PASS (implementation; not touch-injected)** |
| Individual dismissal | **PASS (hub API)** |
| Group dismissal (app) | **PASS** (`CloseAppNotifications`) |
| Clear-all | **PASS (existing API, unchanged)** |
| Stress tests pass | **PASS** (§4.1) |
| Sound behaviour remains correct | **PASS (host)** |

### Application / infrastructure
| Item | Verdict |
|---|---|
| Phone design parity | **PASS** (screenshot + AT-SPI) |
| Radio1Bridge authorization | **PASS** (nobody denied) |
| Dialer offline regression status | **PASS for the contract**; 1 pre-existing unrelated failure remains (§11.7) |
| USB management preserved | **PASS** |
| ZeroTier management preserved | **PASS** |
| Host tests | **PASS** (list in §8; pre-existing failures named) |
| Target builds | **PASS** (radiod, bridge, messages, dialer built `-Werror` on AArch64 device) |
| Rollback readiness | **PASS** (`/var/lib/nuxel/rollback-r34.5/{20261128T143025Z,apps-20261128T143924Z,radiod-20261128T143759Z,home-*}`) |
| Native VoLTE report completed | **PASS** (`./volte-report.md`) |

---

## 13. DEPLOYMENT PROVENANCE & ROLLBACK

| Artifact | Built from | Installed | Rollback |
|---|---|---|---|
| `nuxel-radiod` | `tools/s10plus/s5000ap-05/src` @ `726dba28`, on-device gcc `-O2 -Werror` | `/usr/libexec/nuxel/nuxel-radiod` = `68a4fff3…` | `/var/lib/nuxel/rollback-r34.5/radiod-20261128T143759Z/` (installed `d000f683…`, deployed source, DB `.backup`) |
| `nuxel-radio-bridge` | `services/nuxel-radio-bridge` @ `e80ef52f` | `/usr/libexec/nuxel/nuxel-radio-bridge` = `16e2bb7e…` | `…/apps-20261128T143924Z/nuxel-radio-bridge` |
| `nuxel-messages` | `shell/nuxel-shell/nuxel-messages/main.c` @ `1667daf4` | `/usr/bin/nuxel-messages` = `347f782d…` | `…/apps-20261128T143924Z/nuxel-messages` (old `79b22f0c…`) |
| `nuxel-dialer` | `shell/nuxel-shell/nuxel-dialer/main.c` @ `1667daf4` | `/usr/bin/nuxel-dialer` = `cadbe815…` | `…/apps-20261128T143924Z/nuxel-dialer` |
| notification hub | `services/nuxel-notifications/src/notifications.py` @ `37a4fc57` | `/usr/lib/nuxel/nuxel-notifications/notifications.py` = `42c64608…` | `/var/lib/nuxel/rollback-r34.5/20261128T143025Z/notifications.py` |
| Home modules | `shell/nuxel-home-native/nuxel_home/*.py` @ `37a4fc57` | `/usr/share/nuxel/shell/nuxel-home-native/nuxel_home/` | `/var/lib/nuxel/rollback-r34.5/home-*/` |
| SMS DB snapshots | live store `.backup` | unchanged live DB | `radiod-*/sms.sqlite3` (md5 at snapshot `133c6f2a…`) |

Commits (not pushed): `726dba28` (SMS notification lifecycle), `37a4fc57` (hub + Home + relay),
`e80ef52f` (bridge guard + deploy scripts), `1667daf4` (Messages/Dialer UI + contracts).

**Safety hold:** `/var/lib/nuxel/sms-submit.hold` remained present all round → no automatic submission was
possible, including through the bridge. Removing it re-enables normal `SendSms` (the service only dequeues
`queued` rows on a new send; submitted rows are never re-dequeued). This must be an explicit owner decision.

---

## 14. FINAL FINDING

`MULTIPLE_CAUSES` — app refresh replay + daemon state-change replay + hub cue-per-event/replay + unbounded
Home badge. All four producers are corrected and deployed; the storm is gone across 100 refresh cycles and a
reboot; **no SMS was retransmitted**; every stored SMS is now reachable (conversations + 17-row All messages);
Messages and Phone share the Nuxel design language; and the native VoLTE baseline is documented in
`./volte-report.md`.

---

# ADDENDUM — CONTINUATION (#2): SIM IMPORT/SYNC, CONTACT NAMES, DATA-LOSS FIX, v0.9.5-beta

*Continuation of the interrupted Round 34.5 session, 2026-11-28 16:15–17:10 CET.*
Same guardrails: no partition writes, no modem NV/EFS, no new outbound SMS, no
physical voice call.

## A. What was added after the interruption

### A.1 SIM import / sync (messages **and** contacts)

- Messages: **Import SIM** copies SIM-mirror messages *and* the SIM phonebook
  mirror into the local store/address book **additively** (deduped by
  direction + body + normalised peer, or by name+number); **Sync** re-runs that
  and copies local messages the mirror lacks. Neither ever deletes a record and
  neither writes the physical SIM (no phonebook editor exists on this build;
  the UI states that).
  Evidence (device, production binary): Import SIM →
  `Imported 6 message(s) and 0 contact(s) from the SIM mirror; already-present
  records were kept once. Nothing was deleted and the SIM itself was not written.`
  A second Import added 0. `sms.sqlite3` remained `integrity_check=ok`, 17 rows.
- Contacts: the long-standing **Sync destroys unnamed contacts** defect is fixed
  (`save_contacts()` rebuilt the store from the UI model which dropped
  name-only SIM rows). Sync is now idempotent: repeated Sync →
  `... 0 copied ...`, and `contacts.json` keeps its rows.
- **Backup first**: before any import the following were written on the device
  and preserved: `/var/lib/nuxel/rollback-r345-backup-20261128T162710Z/`
  (`sms.sqlite3` + `sms-before-import.sqlite3` + `subscriber.conf` + `home/`
  copy of the old contacts dir). Contacts also gained an in-app **Back up all**
  that writes timestamped copies of `contacts.json` and `sim-contacts.json`.

### A.2 Contact-name resolution in Messages

Conversation titles now resolve from the address book, including names merged
from the SIM phonebook mirror, with the number kept visible underneath. Device
trace (`NUXEL_MESSAGES_TRACE=1`):
```
[Messages] thread +31649353067 resolved name=Schatje <3 contacts=1
[Messages] thread +31648444066 resolved name=+31648444066 contacts=1
```
and the conversation row renders `S / Schatje <3 / +31649353067 / …`.

### A.3 Root cause of "every stored SMS shows only one / names never resolve"

`nuxel-phone-data`'s JSON reader: `sb_take()` handed back **NULL** for an empty
buffer, and `json_parse_value()` treats a NULL string as a parse error. The
store's own writer emits `"email": ""`, so **every** `contacts.json` written by
Contacts failed to reload (`nuxel_phone_store_load() == -1`) — Contacts showed
the address book as empty and Messages could never resolve a name. Fixed by
returning a real `""` allocation; round-trip tests added (90 checks). The
same reader bug meant A.1's first import reports could not take effect until
fixing it — verified by re-running Import/Sync on device after the fix.

Additional correctness fixes found on the way:
- `nuxel_phone_number_match()` matched alpha SIM names (both normalise to the
  digits they contain) and stripped the country-code digit as if it were a
  trunk `0`; names are no longer numbers and only `+`-less values lose a trunk 0.
- Messages no longer renders a numberless thread for a SIM storage alpha-name
  record (`nuxel_phone_is_number()`).

### A.4 Messages history

- Opening a conversation shows the complete thread **and** the compact
  "All stored messages" list underneath (the same widget re-parented, never
  duplicated); the All-messages tab still lists every row.
- All messages verified **17/17** on device (`+31649353067`, `+31648444066`,
  `+31611371525` threads; ids 1–17 each once).
- New-message composer: contact picker (search by name/number, including
  SIM-imported names) + recipient validation before any submission.

### A.5 Contacts design parity

Contacts now uses the same tokens as Firewall/Maps/Snekbyte (navy `#0a1628`
ground, `#12233c` cards, `#e6f0ff` ink, `#3ea6ff` accent, 14 px radii, 40 px
targets), with restyled detail/edit pages and a header toolbar
(Import SIM · Sync · New / Import vCard · Export vCard · Back up all). Verified
on device via AT-SPI and screenshots; touch-walkthrough confirmation on the
physical panel remains with the owner (§D).

## B. Release / repository state — what actually happened

- Branch `feature/sms34.5-sim-import-checked`, based on `origin/main`.
- PR **#58** merged into `main`; `push:main` triggered the Release workflow which
  built and published **v0.9.5-beta**.
- **Constraint that must be stated plainly**: `origin/main` (and therefore the
  release tree) does **not** contain `tools/s10plus/s5000ap-05/*` nor the
  notifications-hub revision that runs on the handset. `main` also carries a
  divergent Messages baseline (a 943-line ModemManager lineage) and its own
  0.8.9-beta version lineage, so a file-level merge of the Round-34.5 commits
  into `main` is not a fast-forward and direct replay would collide. The PR
  therefore ships the following from the live tree:
  notification-hub hardening (`37a4fc57`), Radio1Bridge guard (`e80ef52f`),
  Messages/Contacts/Dialer + phone-data (`d7a0024d`, `5eb9d5e0`), version
  lockstep and reports. The **S5000AP radio sources themselves are not in the
  release tree**; the handset keeps the locally built binaries (§13) and the
  in-tree source remains on `cs/mob-round35-stage06`. A follow-up PR is required
  to bring `s5000ap-05` into `main`; it is not silently claimed as done here.
- Version lockstep gate `tests/pwnage90000/test_release_assets.py`: **0 failures**.
- `tests/pwnage30000`: 21 passed. `test-core-apps.py --no-runtime`: PASS=86
  FAIL=0. `tests/pwnage54000/test_app_contracts.py`: 1 pre-existing unrelated
  failure (`clock plays the owner alarm asset`); dialer contract now PASS.

## C. Domain status after the continuation

| Requirement | Status | Evidence |
|---|---|---|
| All stored SMS accessible (threads + All messages) | **PASS** | 17/17 on device |
| Click a conversation → complete history | **PASS** (implementation + AT-SPI; no synthetic touch) | thread view + All messages sub-list |
| SIM message import add-only | **PASS** | 6 imported, 2nd import 0, DB unchanged |
| SIM contact import / names resolve | **PASS** | `Schatje <3` resolved in Messages |
| Sync button works and is idempotent | **PASS** | Sync → "…0 copied…" repeated |
| No contact / SMS deletion | **PASS** | backups + counts after every operation |
| Contacts design parity | **PASS** (screenshots + AT-SPI; touch walkthrough pending owner) | tokens shared with Firewall |
| Phone/Dialer design parity | **PASS** (inherited from §6) | — |
| Version bump + PR merge + release run | **PASS** (workflow triggered and completed; see §B constraint) | v0.9.5-beta tag/release |

## D. Remaining, not claimed

1. **S5000AP sources not in `main`** — follow-up PR needed (§B).
2. **Physical SIM phonebook/message-area read via PB_CMD/EF_ADN/EF_SMS is not
   implemented** in radiod; "SIM" in the UI means the on-disk SIM mirror
   (`sim-messages.json`, `sim-contacts.json`) plus whatever SIM-provided names
   are merged. Wiring the modem reader is a radio-source change on
   `cs/mob-round35-stage06`, not a tree that is currently in `main`.
3. **Natural IMS renewal** observation window (§9) and **physical MT SMS**
   through the new stack still need the owner.
4. **Touch confirmation** on the physical panel (conversation open, SIM
   import/sync, Contacts edit) — AT-SPI key/action injection was used; no touch
   injection available in this environment.
5. vCard **Import vCard** uses a GTK FileDialog; not exercised end-to-end here
   (no file chooser automation).

## E. Provenance (continuation)

| Artifact | Build | Installed md5 |
|---|---|---|
| nuxel-messages | tree `5eb9d5e0` + phone-data fix, on-device gcc 15.3 `-O2` | `05a0f1fba85dedf9cfa49efd770a909a` (latest), predecessor rollback `/var/lib/nuxel/rollback-pre-r345-*-nuxel-messages` |
| nuxel-contacts | tree `5eb9d5e0`, on-device gcc | `0d10cf5aad5c19499c8d9fdb13634ff1` (rollback `/var/lib/nuxel/rollback-pre-r345-*-nuxel-contacts`) |
| nuxel-dialer | commit `1667daf4`, on-device gcc | rebuilt `nuxel-dialer-345` |
| Phone-data store | `nuxel-phone-data.c` fix, 90/90 offline checks | — |
