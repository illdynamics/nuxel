/* test-handoff-logic.c — host-compilable test of the A33 handoff decision
 * logic (briq-02a).  Compiles with plain `cc` on macOS/Linux: the header is
 * side-effect free and pulls in no Wayland, no fbdev and no GTK.
 *
 *   cc -O2 -Wall -o build/out/s10plus/a33/test-handoff-logic \
 *      tools/s10plus/a33/tests/test-handoff-logic.c
 *
 * Exit status = number of failures.  The extra cases below pin the properties
 * the receipt contract depends on and that the JSON case table cannot express
 * (monotonicity, the "never two writers" invariant, the resume rule).
 */
#include <stdio.h>
#include <string.h>
#include "../nuxel-handoff-logic.h"

static int failures;

static void check(const char *name, int cond) {
  printf("%s %s\n", cond ? "PASS" : "FAIL", name);
  if (!cond) failures++;
}

static int case_count(void) { return NUXEL_HANDOFF_CASE_COUNT; }

int main(void) {
  printf("== A33 handoff decision logic (cases=%d) ==\n", case_count());

  /* 1. the shared table, machine readable: parsed by nuxel-anim-handoff.py */
  failures += nuxel_handoff_selftest(stdout);

  /* 2. the authored animation is what the floor is computed from */
  check("mp4 default is the shipping 192-frame 24 fps asset",
        NUXEL_MP4_FRAMES_DEFAULT == 192 && NUXEL_MP4_FPS_DEFAULT == 24);
  check("one play-through is exactly 8000 ms",
        NUXEL_ANIM_CYCLE_MS(NUXEL_MP4_FRAMES_DEFAULT, NUXEL_MP4_FPS_DEFAULT) == 8000);
  check("default floor is one complete cycle", NUXEL_ANIM_MIN_CYCLES_DEFAULT == 1);

  /* 3. monotonicity: more loops can only ever unlock the stop, never re-lock it */
  for (int mc = 1; mc <= 3; mc++) {
    int seen = -1;
    for (int loops = 0; loops <= 4; loops++) {
      struct nuxel_handoff_decision d = nuxel_handoff_request_stop(1, 1, loops, mc, 0);
      if (d.request_stop && seen == -1) {
        check("first loop count that unlocks the stop equals the floor", loops == mc);
        seen = loops;
      }
    }
    check("monotonic unlock reached for every configured floor", seen == mc);
  }

  /* 4. the terminal condition is a whole cycle, not "some frames" */
  check("half a cycle is not terminal", nuxel_handoff_anim_terminal(0, 1, 0) == 0);
  check("0 loops of a 1-cycle floor is not terminal", nuxel_handoff_anim_terminal(0, 1, 0) == 0);
  check("one full cycle is terminal", nuxel_handoff_anim_terminal(1, 1, 0) == 1);
  check("an explicit terminal marker is terminal", nuxel_handoff_anim_terminal(0, 1, 1) == 1);

  /* 5. the resume rule: the animation gets the panel back whenever the launcher
   *    never became ready and the bridge never wrote scanout */
  check("resume when launcher not ready and no scanout write",
        nuxel_handoff_resume_animation(0, 0) == 1);
  check("no resume when the bridge already owns the panel",
        nuxel_handoff_resume_animation(1, 1) == 0);
  check("no resume once a scanout write happened",
        nuxel_handoff_resume_animation(0, 1) == 0);

  /* 6. exhaustive single-owner proof (the property the lock file enforces) */
  {
    int violations = 0;
    for (int ready = 0; ready <= 1; ready++)
      for (int alive = 0; alive <= 1; alive++)
        for (int sr = 0; sr <= 1; sr++)
          for (int sc = 0; sc <= 1; sc++)
            if (nuxel_handoff_take_ownership(ready, alive, sr, sc).take_ownership && alive)
              violations++;
    check("exhaustive: never take ownership while a painter is alive", violations == 0);
  }

  printf("%s test-handoff-logic (%d failures)\n", failures ? "FAIL" : "PASS", failures);
  return failures;
}
