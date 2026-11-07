/* nuxel-soundctl — minimal latency client for nuxel-soundd.
 *
 * The Python client cost ~100 ms just to start on the S10+, which pushed the
 * volume cue past the 100 ms target.  This client only formats one JSON line,
 * connects to the private Unix socket and returns immediately; it never starts
 * a decoder, player or audio server.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

static const char *sock_path(void) {
  const char *p = getenv("NUXEL_SOUNDD_SOCKET");
  return (p && *p) ? p : "/run/nuxel/soundd.sock";
}

static int send_request(const char *json, char *reply, size_t rn) {
  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  if (fd < 0) return -1;
  struct sockaddr_un sa;
  memset(&sa, 0, sizeof sa);
  sa.sun_family = AF_UNIX;
  snprintf(sa.sun_path, sizeof sa.sun_path, "%s", sock_path());
  if (connect(fd, (struct sockaddr *)&sa, sizeof sa) < 0) { close(fd); return -1; }
  size_t n = strlen(json);
  if (write(fd, json, n) != (ssize_t)n) { close(fd); return -1; }
  if (write(fd, "\n", 1) != 1) { close(fd); return -1; }
  size_t off = 0;
  while (off + 1 < rn) {
    ssize_t r = read(fd, reply + off, rn - 1 - off);
    if (r <= 0) break;
    off += (size_t)r;
    reply[off] = 0;
    if (memchr(reply, '\n', off)) break;
  }
  close(fd);
  reply[rn - 1] = 0;
  return 0;
}

static void json_escape(const char *in, char *out, size_t n) {
  size_t j = 0;
  for (; in && *in && j + 2 < n; in++) {
    unsigned char c = (unsigned char)*in;
    if (c == '"' || c == '\\') { out[j++] = '\\'; out[j++] = (char)c; }
    else if (c >= 0x20 && c < 0x7f) out[j++] = (char)c;
  }
  out[j] = 0;
}

int main(int argc, char **argv) {
  int i = 1, quiet = 0;
  if (i < argc && !strcmp(argv[i], "--json")) { quiet = 1; i++; }
  if (i >= argc) i = argc;
  const char *cmd = (i < argc) ? argv[i++] : "state";
  char action[64] = "other", token[160] = "", path[512] = "";
  int loop = 0;
  for (; i < argc; i++) {
    if (!strcmp(argv[i], "--loop")) loop = 1;
    else if (!strcmp(argv[i], "--token") && i + 1 < argc) snprintf(token, sizeof token, "%s", argv[++i]);
    else if (!strcmp(argv[i], "--action") && i + 1 < argc) snprintf(action, sizeof action, "%s", argv[++i]);
    else if (!strcmp(argv[i], "--path") && i + 1 < argc) snprintf(path, sizeof path, "%s", argv[++i]);
    else if (!strcmp(cmd, "play") || !strcmp(cmd, "preview")) snprintf(action, sizeof action, "%s", argv[i]);
    else if (!strcmp(cmd, "stop")) { /* bare token is accepted */ snprintf(token, sizeof token, "%s", argv[i]); }
    else if (!strcmp(cmd, "assign")) snprintf(path, sizeof path, "%s", argv[i]);
  }
  char esc_action[128], esc_token[320], esc_path[1100], req[2048];
  json_escape(action, esc_action, sizeof esc_action);
  json_escape(token, esc_token, sizeof esc_token);
  json_escape(path, esc_path, sizeof esc_path);
  if (!strcmp(cmd, "play") || !strcmp(cmd, "preview")) {
    if (path[0]) {
      snprintf(req, sizeof req,
        "{\"cmd\":\"%s\",\"action\":\"%s\",\"token\":\"%s\",\"loop\":%s,\"path\":\"%s\"}",
        cmd, esc_action, esc_token, loop ? "true" : "false", esc_path);
    } else {
      snprintf(req, sizeof req,
        "{\"cmd\":\"%s\",\"action\":\"%s\",\"token\":\"%s\",\"loop\":%s}",
        cmd, esc_action, esc_token, loop ? "true" : "false");
    }
  } else if (!strcmp(cmd, "stop")) {
    snprintf(req, sizeof req, "{\"cmd\":\"stop\",\"token\":\"%s\",\"action\":\"%s\"}",
             esc_token, esc_action);
  } else {
    snprintf(req, sizeof req, "{\"cmd\":\"state\"}");
  }
  char reply[65536];
  if (send_request(req, reply, sizeof reply) != 0) {
    fprintf(stderr, "nuxel-soundctl: soundd unavailable: %s\n", strerror(errno));
    return 2;
  }
  int ok = strstr(reply, "\"success\": true") != NULL || strstr(reply, "\"success\":true") != NULL;
  (void)quiet;
  fputs(reply, stdout);
  if (!reply[0] || reply[strlen(reply) - 1] != '\n') fputc('\n', stdout);
  return ok ? 0 : 1;
}
