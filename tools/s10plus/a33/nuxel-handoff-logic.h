/* nuxel-handoff-logic.h — the PURE decision logic of the A33 boot-animation
 * ownership handoff (briq-02a).
 *
 * WHY THIS FILE EXISTS
 *   The A32 bridge decided the handoff inline in main(): "launcher ready ->
 *   wait for NUXEL_ANIM_MIN_LOOPS marker -> request stop".  That logic is the
 *   thing that actually goes wrong on the glass (the second half of the MP4
 *   being replaced by the launcher's static wallpaper), so it must be testable
 *   WITHOUT a framebuffer, WITHOUT Wayland and WITHOUT the handset.
 *
 *   Everything in this header is side-effect free: no file I/O, no ioctl, no
 *   static state.  Three consumers share it and therefore cannot drift apart:
 *     1. tools/s10plus/a33/nuxel-wl-fb.c      (the real bridge)
 *     2. tools/s10plus/a33/tests/test-handoff-logic.c (compiled on any host)
 *     3. tools/s10plus/a33/nuxel-anim-handoff.py (the replayable timing
 *        harness re-implements the same table and the test compares the two
 *        implementations case by case against tests/handoff-cases.json)
 *
 * CONTRACT (measured inputs, from the live handset A21/A22/A32 logs)
 *   * The boot animation is the ORIGINAL MP4: 1080x1920, 192 frames at 24 fps
 *     = one 8000 ms play-through (verify with
 *     `ffprobe -show_entries stream=nb_frames,r_frame_rate`).
 *   * The animation player loops forever and only ever stops when its stop FILE
 *     appears (nuxel-anim-player.c: `file_exists_at(A_STOPFILE) -> STOP=1`), so
 *     "the animation finished" can never be inferred from the process exiting.
 *     It is inferred from the player's own loop counter markers
 *     (NUXEL_ANIM_LOOP / NUXEL_ANIM_HEARTBEAT_LOOPS) reaching the configured
 *     number of COMPLETE cycles, or from an explicit terminal marker.
 *   * The launcher's readiness is a graphical fact
 *     (/run/nuxel-launcher-ready committed by nuxel-pwa-host), never a timer.
 *   * Ownership is exclusive: exactly one process may write /dev/fb0 at a time.
 *     This process may only take ownership after BOTH (a) the launcher is ready
 *     and (b) it has PROOF that no animation painter is alive.
 */
#ifndef NUXEL_HANDOFF_LOGIC_H
#define NUXEL_HANDOFF_LOGIC_H

#include <stdio.h>
#include <string.h>

/* Schema of the ownership receipt written to /run/nuxel-anim-handoff and of
 * the audit lines appended to /var/lib/nuxel/anim-handoff.log. */
#define NUXEL_HANDOFF_SCHEMA_VERSION 1

/* The authored animation, measured from the shipping asset (not assumed):
 *   ffprobe pwa/nuxel-home/assets/nuxel-boot-animation.mp4
 *   -> width=1080 height=1920 r_frame_rate=24/1 nb_frames=192 duration=8.0 */
#define NUXEL_MP4_FRAMES_DEFAULT 192
#define NUXEL_MP4_FPS_DEFAULT     24
#define NUXEL_ANIM_CYCLE_MS(frames, fps) (((frames) * 1000) / (fps))

/* Minimum number of COMPLETE play-throughs that must be on the glass before the
 * panel may change owner.  A21/A22 (the accepted A32 baseline) is the
 * 0-skipped-frames behaviour; the floor is therefore a whole cycle. */
#define NUXEL_ANIM_MIN_CYCLES_DEFAULT 1

/* Bounded wait for that floor before the bridge gives up ON WAITING and either
 * keeps the animation as the owner (launcher not ready) or refuses to race a
 * painter that will not stop.  2 cycles + slack. */
#define NUXEL_ANIM_MAX_WAIT_S_DEFAULT 24

struct nuxel_handoff_decision {
  int request_stop;        /* may the bridge write the animation stop request? */
  int take_ownership;      /* may the bridge write /dev/fb0 scanout memory?    */
  const char *reason;      /* stable, greppable reason string (evidence)      */
  const char *owner;       /* "anim" while the animation owns the panel       */
};

/* ---- decision 1: is the animation allowed to be asked to stop? ------------ */
static inline struct nuxel_handoff_decision
nuxel_handoff_request_stop(int launcher_ready, int painter_alive,
                           int loops_seen, int min_cycles, int terminal_marker) {
  struct nuxel_handoff_decision d = { 0, 0, "waiting", "anim" };
  if (!launcher_ready) { d.reason = "launcher_not_ready"; return d; }
  if (!painter_alive)  { d.reason = "no_painter";         return d; }
  if (terminal_marker) { d.request_stop = 1; d.reason = "anim_terminal_marker";   return d; }
  if (loops_seen >= min_cycles) { d.request_stop = 1; d.reason = "anim_min_cycle_reached"; return d; }
  d.reason = "anim_min_cycle_pending";
  return d;
}

/* ---- decision 2: is this process allowed to become the framebuffer owner? -- */
static inline struct nuxel_handoff_decision
nuxel_handoff_take_ownership(int launcher_ready, int painter_alive,
                             int stop_requested, int stop_confirmed) {
  struct nuxel_handoff_decision d = { 0, 0, "waiting", "anim" };
  if (!launcher_ready) { d.reason = "launcher_not_ready"; return d; }
  if (stop_requested && !stop_confirmed) { d.reason = "animation_stop_unconfirmed"; return d; }
  if (painter_alive) { d.reason = stop_requested ? "animation_stop_refused" : "animation_still_painting"; return d; }
  d.take_ownership = 1;
  d.owner = "ui";
  d.reason = stop_requested ? "animation_stop_confirmed" : "no_painter";
  return d;
}

/* ---- decision 3: must the animation be handed the panel back? ------------- */
/* True whenever the launcher never became graphically ready: the animation (or
 * the first-light fallback) resumes as the sole owner instead of the panel
 * being left blank or showing a silently static frame. */
static inline int
nuxel_handoff_resume_animation(int launcher_ready, int bridge_wrote_scanout) {
  return (!launcher_ready && !bridge_wrote_scanout) ? 1 : 0;
}

/* ---- decision 4b: the bounded-wait fail-safe ----------------------------- */
/* The bridge may not wait forever for a floor that a stuck animation will never
 * reach (a stalled player would leave the glass on the animation for the whole
 * session).  After the bounded wait it therefore MAY take over anyway, and the
 * receipt records the DEGRADED evidence - loops_seen vs the floor, or the fact
 * that the player's own markers were unreadable.  This path is never reported as
 * a completed cycle: `terminal` stays 0 in the receipt. */
static inline struct nuxel_handoff_decision
nuxel_handoff_degraded_stop(int launcher_ready, int painter_alive, int loops_seen,
                            int min_cycles, int terminal_marker, int bounded_wait_expired) {
  struct nuxel_handoff_decision d = { 0, 0, "not_applicable", "anim" };
  if (!launcher_ready || !painter_alive || !bounded_wait_expired) return d;
  if (terminal_marker) return d;
  if (loops_seen >= min_cycles) return d;
  d.request_stop = 1;
  d.reason = (loops_seen < 0) ? "anim_clock_unavailable" : "anim_min_cycle_timeout";
  return d;
}

/* ---- decision 5: may the minimum-cycle floor be waived for THIS boot? ----- */
/* The operator's durable verbose-boot setting
 * (/etc/nuxel/boot/verbose-boot.json -> nuxel-verbose-boot.service ->
 * /run/nuxel/anim-skip.request) deliberately trades the boot animation for the
 * earliest possible on-glass boot log.  A deliberate user choice is NOT a fault,
 * so the receipt records it honestly:
 *   * it WAIVES the floor and therefore NEVER reports a completed cycle
 *     (terminal stays 0, reason = verbose_boot_requested);
 *   * it still requires the launcher to be graphically ready - a waived floor
 *     must never leave a blank panel;
 *   * it never fires when the floor was reached anyway (then the ordinary
 *     terminal condition is the reason, not the setting).
 * The request is a FILE, never a timer, so it is observable in the audit trail. */
#define NUXEL_HANDOFF_REASON_VERBOSE_SKIP "verbose_boot_requested"

static inline struct nuxel_handoff_decision
nuxel_handoff_verbose_skip(int launcher_ready, int painter_alive, int skip_requested,
                           int loops_seen, int min_cycles, int terminal_marker) {
  struct nuxel_handoff_decision d = { 0, 0, "floor_pending", "anim" };
  if (!launcher_ready) { d.reason = "launcher_not_ready"; return d; }
  if (!painter_alive)  { d.reason = "no_painter";         return d; }
  if (terminal_marker || loops_seen >= min_cycles) { d.reason = "floor_already_met"; return d; }
  if (!skip_requested) { d.reason = "floor_pending";      return d; }
  d.request_stop = 1;
  d.reason = NUXEL_HANDOFF_REASON_VERBOSE_SKIP;
  return d;
}

/* ---- decision 4: did the animation reach a real terminal condition? ------- */
/* A terminal condition is either the player's own terminal marker or the
 * configured number of COMPLETE loops.  It is deliberately NOT "some frames
 * were seen": a half-played cycle is exactly the A31 defect. */
static inline int
nuxel_handoff_anim_terminal(int loops_seen, int min_cycles, int terminal_marker) {
  if (terminal_marker) return 1;
  return loops_seen >= min_cycles ? 1 : 0;
}

/* ---- the shared case table (also in tests/handoff-cases.json) -------------
 * Every case is evaluated by BOTH implementations; the automated test compares
 * the two tables, so a change to the C logic that the Python model does not
 * mirror fails the suite (and vice versa).  Return value = number of failures. */
struct nuxel_handoff_case {
  const char *name;
  int launcher_ready, painter_alive, loops_seen, min_cycles, terminal_marker;
  int stop_requested, stop_confirmed, bounded_wait_expired;
  int skip_requested;      /* /run/nuxel/anim-skip.request present (verbose boot) */
};

static const struct nuxel_handoff_case NUXEL_HANDOFF_CASES[] = {
  /* name,                                    lr pa loops mc tm sr sc exp sk */
  { "launcher_not_ready_keeps_animation",     0, 1,  3, 1, 0, 0, 0, 0 , 0 },
  { "ready_but_half_cycle_pending",           1, 1,  0, 1, 0, 0, 0, 0 , 0 },
  { "ready_and_one_full_cycle_done",          1, 1,  1, 1, 0, 0, 0, 0 , 0 },
  { "ready_and_two_cycles_done",              1, 1,  2, 2, 0, 0, 0, 0 , 0 },
  { "ready_one_cycle_of_two_pending",         1, 1,  1, 2, 0, 0, 0, 0 , 0 },
  { "player_terminal_marker_wins",            1, 1,  0, 1, 1, 0, 0, 0 , 0 },
  { "no_painter_at_all",                      1, 0,  0, 1, 0, 0, 0, 0 , 0 },
  { "zero_min_cycles_is_explicit",            1, 1,  0, 0, 0, 0, 0, 0 , 0 },
  { "stop_requested_but_unconfirmed",         1, 0,  1, 1, 0, 1, 0, 0 , 0 },
  { "stop_confirmed_take_ownership",          1, 0,  1, 1, 0, 1, 1, 0 , 0 },
  { "painter_resurrected_refuse",             1, 1,  1, 1, 0, 1, 1, 0 , 0 },
  { "launcher_not_ready_after_stop",          0, 0,  1, 1, 0, 1, 1, 0 , 0 },
  { "bounded_wait_expired_no_clock",          1, 1, -1, 1, 0, 0, 0, 1 , 0 },
  { "bounded_wait_expired_stalled",           1, 1,  0, 1, 0, 0, 0, 1 , 0 },
  { "bounded_wait_expired_floor_reached",     1, 1,  1, 1, 0, 0, 0, 1 , 0 },
  { "bounded_wait_not_expired_no_stop",       1, 1,  0, 1, 0, 0, 0, 0 , 0 },
  { "bounded_wait_expired_no_painter",        1, 0,  0, 1, 0, 0, 0, 1 , 0 },
  /* the verbose-boot override (briq-02b): the floor is waived on request */
  { "verbose_skip_before_floor",              1, 1,  0, 1, 0, 0, 0, 0, 1 },
  { "verbose_skip_launcher_not_ready",        0, 1,  0, 1, 0, 0, 0, 0, 1 },
  { "verbose_skip_no_painter",                1, 0,  0, 1, 0, 0, 0, 0, 1 },
  { "verbose_skip_floor_already_met",         1, 1,  1, 1, 0, 0, 0, 0, 1 },
  { "verbose_skip_bounded_wait_expired",      1, 1,  0, 1, 0, 0, 0, 1, 1 },
};

#define NUXEL_HANDOFF_CASE_COUNT \
  ((int)(sizeof NUXEL_HANDOFF_CASES / sizeof NUXEL_HANDOFF_CASES[0]))

/* Machine-readable evaluation of one case - the exact line format the Python
 * harness parses:
 *   HANDOFF_CASE <name> request_stop=<0|1> request_reason=<str> take=<0|1> take_reason=<str>
 */
static inline void
nuxel_handoff_case_line(FILE *out, const struct nuxel_handoff_case *c) {
  struct nuxel_handoff_decision rs = nuxel_handoff_request_stop(
      c->launcher_ready, c->painter_alive, c->loops_seen, c->min_cycles, c->terminal_marker);
  struct nuxel_handoff_decision tk = nuxel_handoff_take_ownership(
      c->launcher_ready, c->painter_alive, c->stop_requested, c->stop_confirmed);
  struct nuxel_handoff_decision dg = nuxel_handoff_degraded_stop(
      c->launcher_ready, c->painter_alive, c->loops_seen, c->min_cycles,
      c->terminal_marker, c->bounded_wait_expired);
  struct nuxel_handoff_decision vs = nuxel_handoff_verbose_skip(
      c->launcher_ready, c->painter_alive, c->skip_requested, c->loops_seen,
      c->min_cycles, c->terminal_marker);
  fprintf(out, "HANDOFF_CASE %s request_stop=%d request_reason=%s take=%d take_reason=%s "
               "degraded_stop=%d degraded_reason=%s verbose_skip=%d verbose_skip_reason=%s\n",
          c->name, rs.request_stop, rs.reason, tk.take_ownership, tk.reason,
          dg.request_stop, dg.reason, vs.request_stop, vs.reason);
}

/* Offline self-test: prints the case table and the invariants that keep the
 * panel from ever having two writers.  Returns the number of failures. */
static inline int nuxel_handoff_selftest(FILE *out) {
  int fail = 0;
  for (int i = 0; i < NUXEL_HANDOFF_CASE_COUNT; i++)
    nuxel_handoff_case_line(out, &NUXEL_HANDOFF_CASES[i]);

  /* Invariant 1: the bridge NEVER takes ownership while a painter is alive. */
  for (int ready = 0; ready <= 1; ready++)
    for (int alive = 0; alive <= 1; alive++)
      for (int sr = 0; sr <= 1; sr++)
        for (int sc = 0; sc <= 1; sc++) {
          struct nuxel_handoff_decision d = nuxel_handoff_take_ownership(ready, alive, sr, sc);
          if (alive && d.take_ownership) {
            fprintf(out, "FAIL invariant single_owner ready=%d alive=%d sr=%d sc=%d\n", ready, alive, sr, sc);
            fail++;
          }
          if (!ready && d.take_ownership) {
            fprintf(out, "FAIL invariant never_take_before_launcher_ready ready=%d alive=%d\n", ready, alive);
            fail++;
          }
        }
  /* Invariant 2: the stop is never requested before the launcher is ready. */
  for (int alive = 0; alive <= 1; alive++)
    for (int loops = 0; loops <= 3; loops++)
      for (int mc = 0; mc <= 3; mc++) {
        struct nuxel_handoff_decision d = nuxel_handoff_request_stop(0, alive, loops, mc, 0);
        if (d.request_stop) { fprintf(out, "FAIL invariant no_stop_before_ready alive=%d\n", alive); fail++; }
      }
  /* Invariant 3: a sub-cycle animation is never stopped (the A31 defect). */
  for (int mc = 1; mc <= 3; mc++)
    for (int loops = 0; loops < mc; loops++) {
      struct nuxel_handoff_decision d = nuxel_handoff_request_stop(1, 1, loops, mc, 0);
      if (d.request_stop) { fprintf(out, "FAIL invariant min_cycle_floor loops=%d mc=%d\n", loops, mc); fail++; }
    }
  /* Invariant 5: the degraded (fail-safe) stop never fires early, never fires
   * once the floor is met, and never overrides an explicit terminal marker. */
  for (int exp = 0; exp <= 1; exp++)
    for (int loops = -1; loops <= 3; loops++)
      for (int mc = 0; mc <= 3; mc++)
        for (int tm = 0; tm <= 1; tm++) {
          struct nuxel_handoff_decision d = nuxel_handoff_degraded_stop(1, 1, loops, mc, tm, exp);
          if (d.request_stop && (!exp || loops >= mc || tm)) {
            fprintf(out, "FAIL invariant degraded_stop_bounded exp=%d loops=%d mc=%d tm=%d\n", exp, loops, mc, tm);
            fail++;
          }
        }
  /* Invariant 6: the verbose-boot skip never fires before the launcher is ready,
   * never fires when the floor was already met, and never fires without the
   * request file - a waiver is a recorded user choice, not an accident. */
  for (int ready = 0; ready <= 1; ready++)
    for (int alive = 0; alive <= 1; alive++)
      for (int skip = 0; skip <= 1; skip++)
        for (int loops = -1; loops <= 3; loops++)
          for (int mc = 0; mc <= 3; mc++)
            for (int tm = 0; tm <= 1; tm++) {
              struct nuxel_handoff_decision d =
                  nuxel_handoff_verbose_skip(ready, alive, skip, loops, mc, tm);
              if (d.request_stop && (!ready || !alive || !skip || tm || loops >= mc)) {
                fprintf(out, "FAIL invariant verbose_skip_guarded ready=%d alive=%d skip=%d "
                             "loops=%d mc=%d tm=%d\n", ready, alive, skip, loops, mc, tm);
                fail++;
              }
              if (d.request_stop && strcmp(d.reason, NUXEL_HANDOFF_REASON_VERBOSE_SKIP) != 0) {
                fprintf(out, "FAIL invariant verbose_skip_reason reason=%s\n", d.reason);
                fail++;
              }
            }
  /* Invariant 4: a refused stop hands the panel back to the animation. */
  for (int ready = 0; ready <= 1; ready++)
    if (nuxel_handoff_resume_animation(ready, 0) != (ready ? 0 : 1)) {
      fprintf(out, "FAIL invariant resume_on_not_ready ready=%d\n", ready);
      fail++;
    }
  fprintf(out, "%s handoff_logic invariants cases=%d\n", fail ? "FAIL" : "PASS", NUXEL_HANDOFF_CASE_COUNT);
  return fail;
}

#endif /* NUXEL_HANDOFF_LOGIC_H */
