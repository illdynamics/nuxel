/*
 * nuxel-mt.h — the S10+ touchscreen (MT protocol B) frame parser.
 *
 * WHY THIS IS A SEPARATE, TESTABLE UNIT
 *   The sec_ts driver reports a new contact as
 *
 *       ABS_MT_SLOT 0
 *       ABS_MT_TRACKING_ID <id>
 *       ABS_MT_POSITION_X <x>        (often in the same frame)
 *       ABS_MT_POSITION_Y <y>
 *       SYN_REPORT
 *
 *   Emitting a "down" event at ABS_MT_TRACKING_ID therefore uses the PREVIOUS
 *   frame's coordinates.  On the first touch of a session those are 0,0, which
 *   made every tap look like a swipe from the top-left edge (the observed
 *   spurious `action=back`) and made a real swipe-up-from-the-bottom
 *   indistinguishable from a gesture that started at 0,0 (so `home` never
 *   fired).  The contact is only complete at SYN_REPORT, so this parser emits
 *   DOWN/MOVE/UP there, after ABS_MT_POSITION_X/Y have been applied.
 *
 *   The parser is dependency-free apart from <linux/input.h>, so the offline
 *   test compiles the SAME code the daemon runs (tests/test-touch-mt.c).
 */
#ifndef NUXEL_MT_H
#define NUXEL_MT_H

#include <linux/input.h>
#include <stdint.h>
#include <string.h>

enum {
  NUXEL_MT_PHASE_NONE = 0,
  NUXEL_MT_PHASE_DOWN = 1,
  NUXEL_MT_PHASE_MOVE = 2,
  NUXEL_MT_PHASE_UP = 3,
  NUXEL_MT_PHASE_CANCEL = 4
};

typedef struct {
  int slot;             /* current ABS_MT_SLOT                      */
  int tracking;         /* current slot-0 tracking id, -1 = lifted  */
  int active;           /* a slot-0 contact is being tracked        */
  int down_pending;     /* tracking id seen, coords not complete    */
  int32_t x, y;         /* last known slot-0 coordinates            */
  int32_t axis_max_x, axis_max_y;
} nuxel_mt_state;

typedef struct {
  int phase;            /* NUXEL_MT_PHASE_*                         */
  int32_t x, y;
  int32_t axis_max_x, axis_max_y;
} nuxel_mt_event;

static inline void nuxel_mt_init(nuxel_mt_state *m,
                                 int32_t axis_max_x, int32_t axis_max_y) {
  memset(m, 0, sizeof *m);
  m->slot = 0;
  m->tracking = -1;
  m->axis_max_x = axis_max_x > 0 ? axis_max_x : 1;
  m->axis_max_y = axis_max_y > 0 ? axis_max_y : 1;
}

/*
 * Feed one raw evdev event.  Returns 1 and fills *out when the event completes
 * a frame that the gesture state machine must see, otherwise 0.
 *
 * Only slot 0 is tracked: the manager owns single-finger screen gestures and
 * pretending to interpret pinch would be dishonest.  Other slots are ignored,
 * but an ABS_MT_SLOT switch back to 0 still works because coordinates and the
 * tracking id are kept per the currently selected slot's last report.
 */
static inline int nuxel_mt_feed(nuxel_mt_state *m,
                                const struct input_event *ev,
                                nuxel_mt_event *out) {
  out->phase = NUXEL_MT_PHASE_NONE;

  if (ev->type == EV_ABS) {
    switch (ev->code) {
      case ABS_MT_SLOT:
        m->slot = ev->value;
        break;
      case ABS_MT_TRACKING_ID:
        if (m->slot != 0) break;
        if (ev->value >= 0) {
          if (!m->active && m->tracking < 0) m->down_pending = 1;
          m->tracking = ev->value;
        } else {
          m->tracking = -1;
        }
        break;
      case ABS_MT_POSITION_X:
        if (m->slot == 0) m->x = ev->value;
        break;
      case ABS_MT_POSITION_Y:
        if (m->slot == 0) m->y = ev->value;
        break;
      default:
        break;
    }
    return 0;
  }

  if (ev->type != EV_SYN) return 0;

  if (ev->code == SYN_DROPPED) {
    /* The kernel dropped events.  Never leave a gesture half-open: report a
     * cancel if a contact was being tracked, then resynchronise. */
    if (m->active) {
      out->phase = NUXEL_MT_PHASE_CANCEL;
      out->x = m->x; out->y = m->y;
      out->axis_max_x = m->axis_max_x; out->axis_max_y = m->axis_max_y;
    }
    m->active = 0;
    m->down_pending = 0;
    m->tracking = -1;
    return out->phase != NUXEL_MT_PHASE_NONE;
  }

  if (ev->code != SYN_REPORT || m->slot != 0) return 0;

  if (m->down_pending) {
    /* Coordinates are complete now; this is the first honest DOWN. */
    m->down_pending = 0;
    m->active = 1;
    out->phase = NUXEL_MT_PHASE_DOWN;
  } else if (m->active && m->tracking >= 0) {
    out->phase = NUXEL_MT_PHASE_MOVE;
  } else if (m->active && m->tracking < 0) {
    m->active = 0;
    out->phase = NUXEL_MT_PHASE_UP;
  } else {
    return 0;
  }

  out->x = m->x;
  out->y = m->y;
  out->axis_max_x = m->axis_max_x;
  out->axis_max_y = m->axis_max_y;
  return 1;
}

#endif /* NUXEL_MT_H */
