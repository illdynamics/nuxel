/* Nuxel's loopback-only system metrics endpoint.
 *
 * It is socket activated and does no periodic work: a Home request reads the
 * kernel counters once, and the service exits after 30 seconds without another
 * request.  This keeps the meter off the wakeup path while Home is hidden.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#define GPU_UTIL_PATH "/sys/devices/platform/18500000.mali/utilization"
#define GPU_CLOCK_PATH "/sys/devices/platform/18500000.mali/clock"
#define GPU_BUSY_PATH "/sys/kernel/gpu/gpu_busy"
#define GPU_MEMORY_PATH "/sys/kernel/gpu/gpu_memory"
#define IDLE_TIMEOUT_MS 30000
#define CPU_SAMPLE_NS 150000000L

struct cpu_sample { unsigned long long total, idle; int valid; };
static struct cpu_sample previous;

/* Returns false until two monotonic samples exist. This makes cumulative CPU
 * time impossible to accidentally present as a percentage. */
static int cpu_percent(const struct cpu_sample *before, const struct cpu_sample *after, double *percent) {
  if (!before->valid || !after->valid || after->total <= before->total || after->idle < before->idle) return 0;
  unsigned long long total_delta = after->total - before->total;
  unsigned long long idle_delta = after->idle - before->idle;
  if (!total_delta || idle_delta > total_delta) return 0;
  *percent = 100.0 * (double)(total_delta - idle_delta) / (double)total_delta;
  return 1;
}

/* Write the whole buffer.  The old code cast write(2) to void, which is a hard
 * -Werror=unused-result failure on Fedora (the release gate compiles this file
 * with -Wall -Wextra -Werror).  A short write simply ends the response: the
 * collector must never spin or claim a complete body it did not send. */
static void write_all(int fd, const char *buf, size_t len) {
  while (len > 0) {
    ssize_t n = write(fd, buf, len);
    if (n <= 0) return;
    buf += (size_t)n;
    len -= (size_t)n;
  }
}

static long long timestamp_ms(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_REALTIME, &ts) != 0) return 0;
  return (long long)ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL;
}

static int read_cpu(struct cpu_sample *out) {
  FILE *f = fopen("/proc/stat", "r");
  unsigned long long v[10] = {0};
  int found;
  if (!f) return 0;
  found = fscanf(f, "cpu  %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
                 &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9]);
  fclose(f);
  if (found < 4) return 0;
  out->total = 0;
  for (int i = 0; i < found; i++) out->total += v[i];
  out->idle = v[3] + (found > 4 ? v[4] : 0); /* idle + iowait */
  out->valid = out->total >= out->idle;
  return out->valid;
}

static int read_memory(double *percent, unsigned long long *used_kib,
                       unsigned long long *total_kib) {
  FILE *f = fopen("/proc/meminfo", "r");
  char key[64]; unsigned long long value, total = 0, available = 0;
  if (!f) return 0;
  while (fscanf(f, "%63[^:]: %llu kB\n", key, &value) == 2) {
    if (!strcmp(key, "MemTotal")) total = value;
    else if (!strcmp(key, "MemAvailable")) available = value;
  }
  fclose(f);
  if (!total || available > total) return 0;
  *percent = 100.0 * (double)(total - available) / (double)total;
  *used_kib = total - available;
  *total_kib = total;
  return 1;
}

/* CPUfreq reports kHz.  The S10+ is heterogeneous, so this is the arithmetic
 * mean of the online cores that actually report a current frequency.  It is a
 * representative effective clock, never a rated maximum or a fabricated load
 * estimate. */
static int read_cpu_frequency(double *mhz) {
  unsigned long long sum = 0, value;
  int count = 0;
  char path[128];
  for (int cpu = 0; cpu < 32; cpu++) {
    FILE *f;
    snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    f = fopen(path, "r");
    if (!f) continue;
    if (fscanf(f, "%llu", &value) == 1 && value > 0) { sum += value; count++; }
    fclose(f);
  }
  if (!count) return 0;
  *mhz = (double)sum / (double)count / 1000.0;
  return 1;
}

static int read_gpu_percent_file(const char *path, double *percent) {
  FILE *f = fopen(path, "r");
  double value;
  if (!f) return 0;
  int ok = fscanf(f, "%lf", &value) == 1;
  fclose(f);
  if (!ok || value < 0.0 || value > 100.0) return 0;
  *percent = value;
  return 1;
}

static int read_gpu(double *percent) {
  /* Prefer the Mali utilization node; the generic gpu_busy node is the
   * fallback on kernels that expose the same percentage under /sys/kernel. */
  return read_gpu_percent_file(GPU_UTIL_PATH, percent) ||
         read_gpu_percent_file(GPU_BUSY_PATH, percent);
}

/* The vendor Mali node reports its active clock in kHz (observed on the
 * beyond2lte kernel).  Zero is meaningful while the GPU is idle. */
static int read_gpu_frequency(double *mhz) {
  FILE *f = fopen(GPU_CLOCK_PATH, "r");
  unsigned long long khz;
  if (!f) return 0;
  int ok = fscanf(f, "%llu", &khz) == 1;
  fclose(f);
  if (!ok) return 0;
  *mhz = (double)khz / 1000.0;
  return 1;
}

/* The Mali driver accounts every GPU allocation in this table.  On the S10+
 * GPU memory is shared with system RAM (there is no dedicated VRAM), so the
 * usable budget is MemTotal.  A readable header with no rows is a valid zero,
 * not an unavailable source. */
static int read_gpu_memory(unsigned long long *used_kib) {
  FILE *f = fopen(GPU_MEMORY_PATH, "r");
  char line[256];
  unsigned long long tgid, pid, bytes, total_bytes = 0;
  int saw_header = 0;
  if (!f) return 0;
  while (fgets(line, sizeof(line), f)) {
    if (strstr(line, "mem_used")) { saw_header = 1; continue; }
    if (sscanf(line, "%llu %llu %llu", &tgid, &pid, &bytes) == 3) {
      total_bytes += bytes;
      saw_header = 1;
    }
  }
  fclose(f);
  if (!saw_header) return 0;
  *used_kib = total_bytes / 1024ULL;
  return 1;
}

static void make_json(char *out, size_t cap) {
  struct cpu_sample now = {0};
  double cpu = 0, memory = 0, gpu = 0, cpu_mhz = 0, gpu_mhz = 0;
  unsigned long long memory_used_kib = 0, memory_total_kib = 0;
  unsigned long long gpu_memory_used_kib = 0;
  char cpu_json[32], memory_json[32], gpu_json[32], cpu_mhz_json[32], gpu_mhz_json[32];
  char gpu_memory_json[32], gpu_memory_total_json[32];
  const char *cpu_status = "unavailable";
  const char *mem_status = "unavailable";
  const char *gpu_status = "unavailable";
  const char *cpu_frequency_status = "unavailable";
  const char *gpu_frequency_status = "unavailable";
  const char *gpu_memory_status = "unavailable_shared_memory";
  if (read_cpu(&now)) {
    if (cpu_percent(&previous, &now, &cpu)) {
      cpu_status = "ok";
    } else {
      /* A freshly socket-activated collector has no previous sample.  Take a
       * short in-request delta so the very first Home poll reports real CPU
       * activity instead of "initializing" (and never freezes at null if the
       * service is respawned between polls). */
      struct cpu_sample before = now, after = {0};
      struct timespec window = { .tv_sec = 0, .tv_nsec = CPU_SAMPLE_NS };
      nanosleep(&window, NULL);
      if (read_cpu(&after) && cpu_percent(&before, &after, &cpu)) {
        cpu_status = "ok";
        now = after;
      } else {
        cpu_status = "initializing";
      }
    }
    previous = now;
  }
  if (read_memory(&memory, &memory_used_kib, &memory_total_kib)) mem_status = "ok";
  if (read_gpu(&gpu)) gpu_status = "ok";
  if (read_cpu_frequency(&cpu_mhz)) cpu_frequency_status = "ok";
  if (read_gpu_frequency(&gpu_mhz)) gpu_frequency_status = "ok";
  if (read_gpu_memory(&gpu_memory_used_kib)) {
    gpu_memory_status = !strcmp(mem_status, "ok") ? "ok" : "unavailable_shared_memory";
  }
  if (!strcmp(cpu_status, "ok")) snprintf(cpu_json, sizeof(cpu_json), "%.1f", cpu); else strcpy(cpu_json, "null");
  if (!strcmp(mem_status, "ok")) snprintf(memory_json, sizeof(memory_json), "%.1f", memory); else strcpy(memory_json, "null");
  if (!strcmp(gpu_status, "ok")) snprintf(gpu_json, sizeof(gpu_json), "%.1f", gpu); else strcpy(gpu_json, "null");
  if (!strcmp(cpu_frequency_status, "ok")) snprintf(cpu_mhz_json, sizeof(cpu_mhz_json), "%.0f", cpu_mhz); else strcpy(cpu_mhz_json, "null");
  if (!strcmp(gpu_frequency_status, "ok")) snprintf(gpu_mhz_json, sizeof(gpu_mhz_json), "%.0f", gpu_mhz); else strcpy(gpu_mhz_json, "null");
  if (!strcmp(gpu_memory_status, "ok")) snprintf(gpu_memory_json, sizeof(gpu_memory_json), "%llu", gpu_memory_used_kib); else strcpy(gpu_memory_json, "null");
  if (!strcmp(gpu_memory_status, "ok")) snprintf(gpu_memory_total_json, sizeof(gpu_memory_total_json), "%llu", memory_total_kib); else strcpy(gpu_memory_total_json, "null");
  snprintf(out, cap,
    "{\"cpu_percent\":%s,\"cpu_status\":\"%s\",\"cpu_frequency_mhz\":%s,\"cpu_frequency_status\":\"%s\",\"memory_percent\":%s,\"memory_status\":\"%s\",\"memory_used_kib\":%llu,\"memory_total_kib\":%llu,\"gpu_percent\":%s,\"gpu_status\":\"%s\",\"gpu_frequency_mhz\":%s,\"gpu_frequency_status\":\"%s\",\"gpu_memory_kib\":%s,\"gpu_memory_total_kib\":%s,\"gpu_memory_status\":\"%s\",\"timestamp_ms\":%lld}",
    cpu_json, cpu_status, cpu_mhz_json, cpu_frequency_status, memory_json, mem_status,
    memory_used_kib, memory_total_kib, gpu_json, gpu_status, gpu_mhz_json,
    gpu_frequency_status, gpu_memory_json, gpu_memory_total_json,
    gpu_memory_status, timestamp_ms());
}

static void respond(int fd) {
  char request[1024], json[1024], header[1536], date[64];
  ssize_t n = read(fd, request, sizeof(request) - 1);
  if (n <= 0) return;
  request[n] = '\0';
  /* Cache-busting query parameters are part of the contract: WebKit cached a
   * previous 200 even with no-store and kept presenting frozen counters while
   * the on-demand service had already exited.  Accept GET /metrics?t=... and
   * answer the CORS preflight explicitly. */
  if (strncmp(request, "OPTIONS /metrics", 16) == 0) {
    const char *preflight =
      "HTTP/1.1 204 No Content\r\n"
      "Access-Control-Allow-Origin: http://127.0.0.1:8000\r\n"
      "Access-Control-Allow-Methods: GET, OPTIONS\r\n"
      "Access-Control-Allow-Headers: Cache-Control, Pragma\r\n"
      "Access-Control-Max-Age: 600\r\n"
      "Content-Length: 0\r\nConnection: close\r\n\r\n";
    write_all(fd, preflight, strlen(preflight));
    return;
  }
  if (strncmp(request, "GET /metrics", 12) != 0 ||
      (request[12] != ' ' && request[12] != '?')) {
    const char *not_found = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
    write_all(fd, not_found, strlen(not_found)); return;
  }
  make_json(json, sizeof(json));
  time_t now = time(NULL);
  struct tm tmv;
  gmtime_r(&now, &tmv);
  strftime(date, sizeof(date), "%a, %d %b %Y %H:%M:%S GMT", &tmv);
  snprintf(header, sizeof(header),
    "HTTP/1.1 200 OK\r\nDate: %s\r\nContent-Type: application/json\r\nContent-Length: %zu\r\n"
    "Cache-Control: no-store, no-cache, must-revalidate\r\nPragma: no-cache\r\nExpires: 0\r\n"
    "Access-Control-Allow-Origin: http://127.0.0.1:8000\r\nVary: Origin\r\nConnection: close\r\n\r\n%s",
    date, strlen(json), json);
  write_all(fd, header, strlen(header));
}

static int self_test(void) {
  double mem, gpu;
  struct cpu_sample sample;
  struct cpu_sample a = { .total = 100, .idle = 60, .valid = 1 };
  struct cpu_sample b = { .total = 200, .idle = 110, .valid = 1 };
  double cpu = 0;
  if (!cpu_percent(&a, &b, &cpu) || cpu != 50.0) return 10;
  b.total = a.total; if (cpu_percent(&a, &b, &cpu)) return 11;
  if (!read_cpu(&sample) || sample.total == 0) return 1;
  unsigned long long used_kib, total_kib;
  if (!read_memory(&mem, &used_kib, &total_kib) || mem < 0 || mem > 100 || used_kib > total_kib) return 2;
  /* GPU availability is hardware-specific; absence is an expected success path. */
  if (read_gpu(&gpu) && (gpu < 0 || gpu > 100)) return 3;
  return 0;
}

int main(int argc, char **argv) {
  if (argc == 2 && !strcmp(argv[1], "--self-test")) return self_test();
  if (argc == 2 && !strcmp(argv[1], "--json")) {
    char snapshot[1024];
    make_json(snapshot, sizeof(snapshot));
    puts(snapshot);
    return 0;
  }
  const char *pid = getenv("LISTEN_PID");
  const char *fds = getenv("LISTEN_FDS");
  if (!pid || !fds || (pid_t)strtol(pid, NULL, 10) != getpid() || strtol(fds, NULL, 10) < 1) return 64;
  for (;;) {
    struct pollfd p = { .fd = 3, .events = POLLIN };
    int ready = poll(&p, 1, IDLE_TIMEOUT_MS);
    if (ready == 0) return 0;
    if (ready < 0) { if (errno == EINTR) continue; return 1; }
    int client = accept(3, NULL, NULL);
    if (client < 0) continue;
    respond(client);
    close(client);
  }
}
