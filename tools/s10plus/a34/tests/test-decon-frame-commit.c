/* Offline A35 regression: Samsung DECON must PAN after each framebuffer blit.
 * Mock ioctl; NEVER touches /dev/fb0, backlight sysfs, or the phone. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <linux/fb.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/ioctl.h>

static int mock_calls;
static unsigned long mock_request;
static int mock_result;
static int mock_expected_fd = 143;
static int mock_ioctl(int fd, unsigned long request, ...);
#define ioctl mock_ioctl
#define main nuxel_wl_fb_main_for_testing
#include "tools/s10plus/a34/nuxel-wl-fb.c"
#undef main
#undef ioctl

static int mock_ioctl(int fd, unsigned long request, ...) {
  assert(fd == mock_expected_fd);
  mock_calls++;
  mock_request = request;
  va_list args;
  va_start(args, request);
  if (request == FBIOPAN_DISPLAY) {
    struct fb_var_screeninfo *v = va_arg(args, struct fb_var_screeninfo *);
    assert(v->activate == FB_ACTIVATE_NOW);
    assert(v->xoffset == 0 && v->yoffset == 0);
  } else if (request == FBIOBLANK) {
    int mode = va_arg(args, int);
    assert(mode == FB_BLANK_POWERDOWN);
  } else {
    assert(!"unplanned display ioctl in per-frame commit test");
  }
  va_end(args);
  if (mock_result) { errno = EIO; return -1; }
  return 0;
}

int main(void) {
  fb.fd = mock_expected_fd;
  fb.var.activate = FB_ACTIVATE_TEST;
  fb.var.yoffset = 3040;
  mock_calls = mock_result = 0;
  assert(panel_commit_frame("test-first-frame") == 0);
  assert(mock_request == FBIOPAN_DISPLAY);
  assert(mock_calls == 1 && decon_pan_ok == 1 && decon_pan_failed == 0);
  assert(fb.var.yoffset == 0);
  assert(panel_commit_frame("test-next-frame") == 0);
  assert(mock_calls == 2 && decon_pan_ok == 2);
  mock_result = 1;
  assert(panel_commit_frame("test-failure") == -1);
  assert(decon_pan_failed == 1 && decon_pan_fail_streak == 1);
  mock_result = 0;
  assert(panel_commit_frame("test-recovery") == 0);
  assert(decon_pan_fail_streak == 0);
  assert(panel_blank_powerdown("test-off") == 0);
  assert(mock_request == FBIOBLANK);
  printf("PASS DECON PAN per frame + failure bookkeeping + POWERDOWN blank\n");
  return 0;
}
