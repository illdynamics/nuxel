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
#define IDLE_TIMEOUT_MS 30000

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

static int read_gpu(double *percent) {
  FILE *f = fopen(GPU_UTIL_PATH, "r");
  double value;
  if (!f) return 0;
  int ok = fscanf(f, "%lf", &value) == 1;
  fclose(f);
  if (!ok || value < 0.0 || value > 100.0) return 0;
  *percent = value;
  return 1;
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

static void make_json(char *out, size_t cap) {
  struct cpu_sample now = {0};
  double cpu = 0, memory = 0, gpu = 0, cpu_mhz = 0, gpu_mhz = 0;
  unsigned long long memory_used_kib = 0, memory_total_kib = 0;
  char cpu_json[32], memory_json[32], gpu_json[32], cpu_mhz_json[32], gpu_mhz_json[32];
  const char *cpu_status = "unavailable";
  const char *mem_status = "unavailable";
  const char *gpu_status = "unavailable";
  const char *cpu_frequency_status = "unavailable";
  const char *gpu_frequency_status = "unavailable";
  if (read_cpu(&now)) {
    if (cpu_percent(&previous, &now, &cpu)) cpu_status = "ok";
    else if (!previous.valid) cpu_status = "initializing";
    previous = now;
  }
  if (read_memory(&memory, &memory_used_kib, &memory_total_kib)) mem_status = "ok";
  if (read_gpu(&gpu)) gpu_status = "ok";
  if (read_cpu_frequency(&cpu_mhz)) cpu_frequency_status = "ok";
  if (read_gpu_frequency(&gpu_mhz)) gpu_frequency_status = "ok";
  if (!strcmp(cpu_status, "ok")) snprintf(cpu_json, sizeof(cpu_json), "%.1f", cpu); else strcpy(cpu_json, "null");
  if (!strcmp(mem_status, "ok")) snprintf(memory_json, sizeof(memory_json), "%.1f", memory); else strcpy(memory_json, "null");
  if (!strcmp(gpu_status, "ok")) snprintf(gpu_json, sizeof(gpu_json), "%.1f", gpu); else strcpy(gpu_json, "null");
  if (!strcmp(cpu_frequency_status, "ok")) snprintf(cpu_mhz_json, sizeof(cpu_mhz_json), "%.0f", cpu_mhz); else strcpy(cpu_mhz_json, "null");
  if (!strcmp(gpu_frequency_status, "ok")) snprintf(gpu_mhz_json, sizeof(gpu_mhz_json), "%.0f", gpu_mhz); else strcpy(gpu_mhz_json, "null");
  snprintf(out, cap,
    "{\"cpu_percent\":%s,\"cpu_status\":\"%s\",\"cpu_frequency_mhz\":%s,\"cpu_frequency_status\":\"%s\",\"memory_percent\":%s,\"memory_status\":\"%s\",\"memory_used_kib\":%llu,\"memory_total_kib\":%llu,\"gpu_percent\":%s,\"gpu_status\":\"%s\",\"gpu_frequency_mhz\":%s,\"gpu_frequency_status\":\"%s\",\"gpu_memory_kib\":null,\"gpu_memory_status\":\"unavailable_shared_memory\",\"timestamp_ms\":%lld}",
    cpu_json, cpu_status, cpu_mhz_json, cpu_frequency_status, memory_json, mem_status,
    memory_used_kib, memory_total_kib, gpu_json, gpu_status, gpu_mhz_json,
    gpu_frequency_status, timestamp_ms());
}

static void respond(int fd) {
  char request[1024], json[512], header[768];
  ssize_t n = read(fd, request, sizeof(request) - 1);
  if (n <= 0) return;
  request[n] = '\0';
  if (strncmp(request, "GET /metrics ", 13) != 0) {
    const char *not_found = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n";
    (void)write(fd, not_found, strlen(not_found)); return;
  }
  make_json(json, sizeof(json));
  snprintf(header, sizeof(header),
    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: %zu\r\nCache-Control: no-store\r\nAccess-Control-Allow-Origin: http://127.0.0.1:8000\r\nConnection: close\r\n\r\n%s",
    strlen(json), json);
  (void)write(fd, header, strlen(header));
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
