/* Offline C regression harness for the phone host's indicator reader.
 *
 * The build script generates a translation unit containing the exact sensor
 * block from tools/s10plus/a45/nuxel-pwa-host.c, then compiles it with this
 * harness.  A synthetic sysfs/proc/run tree proves all eight combinations and
 * the false-positive cases without a device.
 */
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "indicator_snippet.inc"

static int failures;

static void check(int cond, const char *label) {
  printf("%s %s\n", cond ? "PASS" : "FAIL", label);
  if (!cond) failures++;
}

static void mkdir_p(const char *path) {
  char tmp[1024];
  snprintf(tmp, sizeof tmp, "%s", path);
  for (char *p = tmp + 1; *p; p++) {
    if (*p == '/') { *p = 0; mkdir(tmp, 0755); *p = '/'; }
  }
  mkdir(tmp, 0755);
}

static void write_file(const char *root, const char *rel, const char *value) {
  char path[1024], dir[1024];
  snprintf(path, sizeof path, "%s/%s", root, rel);
  snprintf(dir, sizeof dir, "%s", path);
  char *slash = strrchr(dir, '/');
  if (slash) { *slash = 0; mkdir_p(dir); }
  FILE *f = fopen(path, "wb");
  if (!f) return;
  fputs(value, f);
  fclose(f);
}

static void link_file(const char *root, const char *rel, const char *target) {
  char path[1024], dir[1024];
  snprintf(path, sizeof path, "%s/%s", root, rel);
  snprintf(dir, sizeof dir, "%s", path);
  char *slash = strrchr(dir, '/');
  if (slash) { *slash = 0; mkdir_p(dir); }
  unlink(path);
  symlink(target, path);
}

static void reset_tree(const char *root) {
  char cmd[1200];
  snprintf(cmd, sizeof cmd, "find '%s' -mindepth 1 -delete", root);
  if (system(cmd) != 0) { /* best effort */ }
  char p[1024];
  snprintf(p, sizeof p, "%s/power_supply", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/udc", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/tty", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/usb_gadget", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/proc", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/android_usb", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/typec", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/debugfs", root); mkdir(p, 0755);
  snprintf(p, sizeof p, "%s/run/nuxel", root); mkdir_p(p);
}

static void battery(const char *root, const char *status) {
  write_file(root, "power_supply/battery/type", "Battery\n");
  write_file(root, "power_supply/battery/capacity", "71\n");
  write_file(root, "power_supply/battery/status", status);
}

static void usb_power(const char *root, const char *online) {
  write_file(root, "power_supply/usb/type", "USB\n");
  write_file(root, "power_supply/usb/online", online);
}

static void gadget(const char *root, const char *state) {
  write_file(root, "usb_gadget/nuxel/UDC", "10c00000.dwc3\n");
  if (state) write_file(root, "udc/10c00000.dwc3/state", state);
}


static void typec_role(const char *root, const char *role) {
  /* role == NULL clears the Type-C class (absent); otherwise writes
     typec/port0/data_role (brackets mark the resolved role). */
  if (!role) { write_file(root, "typec/.absent", ""); return; }
  write_file(root, "typec/port0/data_role", role);
}

static void dwc3_link(const char *root, const char *state) {
  /* state == NULL clears debugfs; otherwise writes the dwc3 link_state. */
  if (!state) { write_file(root, "debugfs/.absent", ""); return; }
  write_file(root, "debugfs/10c00000.dwc3/link_state", state);
}

static void unbound_gadget(const char *root) {
  write_file(root, "usb_gadget/nuxel/UDC", "\n");
  write_file(root, "udc/10c00000.dwc3/state", "not attached\n");
}

static void console_proc(const char *root, int pid, int tty, const char *cmd) {
  char rel[128];
  snprintf(rel, sizeof rel, "proc/%d/cmdline", pid);
  write_file(root, rel, cmd);
  snprintf(rel, sizeof rel, "proc/%d/fd", pid);
  char p[1024]; snprintf(p, sizeof p, "%s/%s", root, rel); mkdir_p(p);
  if (tty) {
    snprintf(rel, sizeof rel, "proc/%d/fd/0", pid);
    link_file(root, rel, "/dev/ttyGS0");
  }
}

static void tty_registered(const char *root, int present) {
  write_file(root, "tty/ttyGS0/dev", present ? "254:0\n" : "");
}

static void set_roots(const char *root) {
  char buf[8][1024];
  static const char *vars[6] = {
    "NUXEL_SYS_POWER_SUPPLY", "NUXEL_SYS_UDC", "NUXEL_SYS_TTY",
    "NUXEL_CONFIGFS_GADGET", "NUXEL_PROC", "NUXEL_RUN"
  };
  static const char *sub[6] = {
    "power_supply", "udc", "tty", "usb_gadget", "proc", "run"
  };
  for (int i = 0; i < 6; i++) {
    snprintf(buf[i], sizeof buf[i], "%s/%s", root, sub[i]);
    setenv(vars[i], buf[i], 1);
  }
  /* The test hook names the android_usb DIRECTORY; the detector appends /state,
     matching the live sysfs layout. */
  snprintf(buf[0], sizeof buf[0], "%s/android_usb", root);
  setenv("NUXEL_ANDROID_USB_STATE", buf[0], 1);
  /* A73 physical detach signals. */
  snprintf(buf[6], sizeof buf[6], "%s/typec", root);
  setenv("NUXEL_SYS_TYPEC", buf[6], 1);
  snprintf(buf[7], sizeof buf[7], "%s/debugfs", root);
  setenv("NUXEL_DEBUGFS", buf[7], 1);
}

static void state(int *power, int *charging, int *pc, int *live) {
  ind_power(power, charging);
  *pc = ind_pc_connected();
  *live = ind_live_console();
}

int main(void) {
  char tmpl[] = "/tmp/nuxel-ind-c-XXXXXX";
  char *root = mkdtemp(tmpl);
  if (!root) return 2;
  set_roots(root);

  int p, c, pc, lv;

  reset_tree(root);
  state(&p, &c, &pc, &lv);
  check(!p && !c && !pc && !lv, "empty tree: all indicators off");

  reset_tree(root); battery(root, "Discharging\n"); usb_power(root, "1\n");
  state(&p, &c, &pc, &lv);
  check(p && !c && !pc && !lv, "charging-only cable: power on, no false PC, no console");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "actively charging: charge animation only");

  reset_tree(root); battery(root, "Full\n"); usb_power(root, "1\n");
  state(&p, &c, &pc, &lv);
  check(p && !c && !pc && !lv, "battery Full: external power, not active charging");

  reset_tree(root); battery(root, "Not charging\n"); usb_power(root, "1\n");
  state(&p, &c, &pc, &lv);
  check(p && !c && !pc && !lv, "battery Not charging: external power, no charge animation");

  reset_tree(root); battery(root, "Discharging\n");
  write_file(root, "power_supply/otg/type", "OTG\n");
  write_file(root, "power_supply/otg/online", "1\n");
  state(&p, &c, &pc, &lv);
  check(!p && !c && !pc && !lv, "OTG/host mode does NOT light the charging indicator");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "configured\n"); tty_registered(root, 1);
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "configured UDC + tty, no console process: PC only");

  /* Vendor android_usb state may be stale; without exact UDC configuration it
     is diagnostic only and must fail closed. */
  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  write_file(root, "android_usb/state", "CONFIGURED\n");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "stale android USB CONFIGURED: no UDC proof, no PC");
  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  write_file(root, "android_usb/state", "DISCONNECTED\n");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "android USB DISCONNECTED: no PC");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "addressed\n"); tty_registered(root, 1);
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "addressed UDC is pre-enumeration: no PC");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "configured\n"); tty_registered(root, 1);
  console_proc(root, 4242, 1, "/opt/nuxel/nuxel-console\0/newroot\0");
  state(&p, &c, &pc, &lv);
  check(p && c && pc && lv, "configured UDC + running console process: all three");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "configured\n"); tty_registered(root, 1);
  console_proc(root, 4343, 1, "/bin/sh\0");
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "root shell alone does NOT light live console");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "configured\n"); tty_registered(root, 1);
  console_proc(root, 4444, 0, "/opt/nuxel/nuxel-console\0/newroot\0");
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "console process without tty fd does NOT light live console");

  /* A live USB console cannot outlive the data link (A71): a surviving daemon
     and tty fd must not keep the console icon lit after detach. */
  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "not attached\n"); tty_registered(root, 1);
  console_proc(root, 4545, 1, "/opt/nuxel/nuxel-console\0/newroot\0");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "not-attached UDC: console cannot stay active without a data link");

  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  unbound_gadget(root); tty_registered(root, 1);
  console_proc(root, 4646, 1, "/opt/nuxel/nuxel-console\0/newroot\0");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "console process without a bound gadget is inactive");

  /* A73 PHYSICAL DETACH VETO: a stale "configured" UDC must not survive an
     independent physical down signal. */
  reset_tree(root); battery(root, "Charging\n"); usb_power(root, "1\n");
  gadget(root, "configured\n"); tty_registered(root, 1);
  typec_role(root, "host [device]\n"); dwc3_link(root, "On\n");
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "configured UDC + typec device role + dwc3 On: PC on");

  typec_role(root, "host device\n");  /* no bracket: role not resolved to device */
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "typec no-device-role vetoes a stale configured UDC");

  typec_role(root, "host [device]\n"); dwc3_link(root, "Off\n");
  state(&p, &c, &pc, &lv);
  check(p && c && !pc && !lv, "dwc3 link_state Off vetoes a stale configured UDC");

  dwc3_link(root, "On\n");
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "physical signals restored: PC on again");

  typec_role(root, NULL); dwc3_link(root, NULL);
  state(&p, &c, &pc, &lv);
  check(p && c && pc && !lv, "absent physical signals leave UDC proof authoritative");

  for (int power = 0; power < 2; power++) {
    for (int wantpc = 0; wantpc < 2; wantpc++) {
      for (int wantlive = 0; wantlive < 2; wantlive++) {
        reset_tree(root);
        battery(root, power ? "Charging\n" : "Discharging\n");
        usb_power(root, power ? "1\n" : "0\n");
        if (wantlive) {
          gadget(root, wantpc ? "configured\n" : "not attached\n");
          tty_registered(root, 1);
          console_proc(root, 5000, 1, "/opt/nuxel/nuxel-console\0/newroot\0");
        } else if (wantpc) {
          gadget(root, "configured\n");
          tty_registered(root, 1);
        } else {
          unbound_gadget(root);
        }
        state(&p, &c, &pc, &lv);
        char label[180];
        int want_live = wantlive && wantpc;
        snprintf(label, sizeof label,
                 "combination power=%d pc=%d live=%d -> (%d,%d,%d,%d)",
                 power, wantpc, wantlive, p, c, pc, lv);
        check(p == power && c == power && pc == wantpc && lv == want_live, label);
      }
    }
  }

  reset_tree(root); gadget(root, "configured\n"); tty_registered(root, 1);
  write_file(root, "run/nuxel/live-console-session", "pid=999999\n");
  check(!ind_live_console(), "stale lease pid does NOT light live console");

  reset_tree(root); gadget(root, "configured\n"); tty_registered(root, 1);
  console_proc(root, 4747, 0, "/opt/nuxel/nuxel-console\0/newroot\0");
  write_file(root, "run/nuxel/live-console-session", "pid=4747\n");
  check(ind_live_console(), "validated live lease lights the console");

  reset_tree(root); gadget(root, "configured\n"); tty_registered(root, 1);
  console_proc(root, 4747, 0, "/opt/nuxel/nuxel-console\0/newroot\0");
  write_file(root, "proc/4747/stat",
             "4747 (nuxel-console) S 1 4747 4747 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 777 0 0\n");
  write_file(root, "run/nuxel/live-console-session",
             "pid=4747\nstate=serving\nstart_ticks=777\n");
  check(ind_live_console(), "start_ticks-bound serving lease lights the console");
  write_file(root, "run/nuxel/live-console-session",
             "pid=4747\nstate=serving\nstart_ticks=778\n");
  check(!ind_live_console(), "reused PID with the wrong start_ticks is rejected");
  write_file(root, "run/nuxel/live-console-session",
             "pid=4747\nstate=stopped\n");
  check(!ind_live_console(), "a non-serving lease state does not light the console");

  /* Exercise the exact JSON envelope the host sends to the JS UI. */
  reset_tree(root);
  battery(root, "Charging\n");
  usb_power(root, "1\n");
  gadget(root, "configured\n");
  tty_registered(root, 1);
  console_proc(root, 5001, 1, "/opt/nuxel/nuxel-console\0/newroot\0");
  char json[1024];
  indicators_json(json, sizeof json);
  check(strstr(json, "\"external_power\":1") && strstr(json, "\"charging\":1") &&
        strstr(json, "\"pc_connected\":1") && strstr(json, "\"active\":1"),
        "JSON envelope carries all three active states");

  char cmd[1200];
  snprintf(cmd, sizeof cmd, "find '%s' -mindepth 1 -delete", root);
  if (system(cmd) != 0) { /* best effort */ }
  rmdir(root);
  printf("\n%s\n", failures ? "FAILURES" : "ALL PASS");
  return failures;
}
