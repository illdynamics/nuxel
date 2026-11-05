/* nuxel-touch-inject — bounded virtual touchscreen for PWNAGE-80000 acceptance.
 *
 * This is an engineering test aid, not part of the desktop.  It creates one
 * temporary uinput multitouch device, emits a tap or a single-finger drag, then
 * destroys the device.  It never opens the real touchscreen and never writes a
 * device node other than /dev/uinput.
 *
 * usage: nuxel-touch-inject tap X Y
 *        nuxel-touch-inject swipe X1 Y1 X2 Y2 [STEPS]
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int fd = -1;

static void die(const char *what) {
  fprintf(stderr, "nuxel-touch-inject: %s: %s\n", what, strerror(errno));
  exit(2);
}

static void emit(int type, int code, int value) {
  struct input_event ev;
  memset(&ev, 0, sizeof ev);
  ev.type = type; ev.code = code; ev.value = value;
  if (write(fd, &ev, sizeof ev) != (ssize_t)sizeof ev) die("write");
}

static void syn(void) { emit(EV_SYN, SYN_REPORT, 0); }

static void setup(int max_x, int max_y) {
  fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
  if (fd < 0) die("open /dev/uinput");
  ioctl(fd, UI_SET_EVBIT, EV_SYN);
  ioctl(fd, UI_SET_EVBIT, EV_KEY);
  ioctl(fd, UI_SET_EVBIT, EV_ABS);
  ioctl(fd, UI_SET_KEYBIT, BTN_TOUCH);
  ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT);
  ioctl(fd, UI_SET_ABSBIT, ABS_X);
  ioctl(fd, UI_SET_ABSBIT, ABS_Y);
  ioctl(fd, UI_SET_ABSBIT, ABS_MT_SLOT);
  ioctl(fd, UI_SET_ABSBIT, ABS_MT_TRACKING_ID);
  ioctl(fd, UI_SET_ABSBIT, ABS_MT_POSITION_X);
  ioctl(fd, UI_SET_ABSBIT, ABS_MT_POSITION_Y);
  ioctl(fd, UI_SET_ABSBIT, ABS_MT_TOUCH_MAJOR);

  struct uinput_user_dev dev;
  memset(&dev, 0, sizeof dev);
  snprintf(dev.name, sizeof dev.name, "nuxel-pwnage80000-inject");
  dev.id.bustype = BUS_VIRTUAL;
  dev.id.vendor = 0x4e58;
  dev.id.product = 0x8000;
  dev.id.version = 1;
  dev.absmin[ABS_X] = 0; dev.absmax[ABS_X] = max_x;
  dev.absmin[ABS_Y] = 0; dev.absmax[ABS_Y] = max_y;
  dev.absmin[ABS_MT_POSITION_X] = 0; dev.absmax[ABS_MT_POSITION_X] = max_x;
  dev.absmin[ABS_MT_POSITION_Y] = 0; dev.absmax[ABS_MT_POSITION_Y] = max_y;
  dev.absmin[ABS_MT_TOUCH_MAJOR] = 0; dev.absmax[ABS_MT_TOUCH_MAJOR] = 255;
  if (write(fd, &dev, sizeof dev) != (ssize_t)sizeof dev) die("write uinput_user_dev");
  if (ioctl(fd, UI_DEV_CREATE) < 0) die("UI_DEV_CREATE");
  usleep(250000);
}

static void down(int x, int y) {
  emit(EV_ABS, ABS_MT_SLOT, 0);
  emit(EV_ABS, ABS_MT_TRACKING_ID, 0x8000);
  emit(EV_ABS, ABS_MT_TOUCH_MAJOR, 12);
  emit(EV_ABS, ABS_MT_POSITION_X, x);
  emit(EV_ABS, ABS_MT_POSITION_Y, y);
  emit(EV_ABS, ABS_X, x);
  emit(EV_ABS, ABS_Y, y);
  emit(EV_KEY, BTN_TOUCH, 1);
  syn();
}

static void move(int x, int y) {
  emit(EV_ABS, ABS_MT_POSITION_X, x);
  emit(EV_ABS, ABS_MT_POSITION_Y, y);
  emit(EV_ABS, ABS_X, x);
  emit(EV_ABS, ABS_Y, y);
  syn();
}

static void up(void) {
  emit(EV_ABS, ABS_MT_SLOT, 0);
  emit(EV_ABS, ABS_MT_TRACKING_ID, -1);
  emit(EV_KEY, BTN_TOUCH, 0);
  syn();
  usleep(120000);
}

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: %s tap X Y | swipe X1 Y1 X2 Y2 [STEPS] [MS] | hold SECS\n", argv[0]);
    return 2;
  }
  int max_x = 1520, max_y = 1520;
  const char *mx = getenv("NUXEL_INJECT_MAX_X");
  const char *my = getenv("NUXEL_INJECT_MAX_Y");
  if (mx && atoi(mx) > 0) max_x = atoi(mx);
  if (my && atoi(my) > 0) max_y = atoi(my);
  setup(max_x, max_y);
  if (!strcmp(argv[1], "hold")) {
    unsigned secs = (unsigned)atoi(argv[2]);
    if (secs < 1) secs = 3;
    sleep(secs);
  } else if (!strcmp(argv[1], "tap")) {
    int x = atoi(argv[2]), y = atoi(argv[3]);
    down(x, y); usleep(90000); up();
  } else if (!strcmp(argv[1], "swipe") && argc >= 6) {
    int x1 = atoi(argv[2]), y1 = atoi(argv[3]);
    int x2 = atoi(argv[4]), y2 = atoi(argv[5]);
    int steps = argc >= 7 ? atoi(argv[6]) : 16;
    int ms = argc >= 8 ? atoi(argv[7]) : 260;
    if (steps < 2) steps = 2;
    down(x1, y1);
    for (int i = 1; i <= steps; i++) {
      move(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps);
      usleep((useconds_t)((ms * 1000) / steps));
    }
    up();
  } else {
    fprintf(stderr, "unknown command\n"); return 2;
  }
  ioctl(fd, UI_DEV_DESTROY);
  close(fd);
  return 0;
}
