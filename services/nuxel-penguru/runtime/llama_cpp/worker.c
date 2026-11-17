/* PenGuru llama.cpp worker — unprivileged, no network, line-JSON events.
 *
 * Reads exactly one JSON job on stdin (a deliberately small parser: the job
 * shape is produced by our own control plane), loads one verified GGUF file
 * and streams: loading -> loaded -> token* -> done -> unloaded.  On failure it
 * emits an error event and exits non-zero.
 *
 * Built against the pinned llama.cpp headers; no ABI guessing.
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <dirent.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/prctl.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <sys/syscall.h>
#include <stddef.h>
#include "llama.h"

static volatile sig_atomic_t g_cancel = 0;

static void on_signal(int sig) { (void)sig; g_cancel = 1; }

static void emit(const char *event, const char *fmt, ...) {
  printf("{\"schema_version\":1,\"event\":\"%s\"", event);
  if (fmt && *fmt) {
    va_list ap;
    va_start(ap, fmt);
    char buf[8192];
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    printf(",%s", buf);
  }
  printf("}\n");
  fflush(stdout);
}

static void json_escape(const char *in, char *out, size_t outn) {
  size_t o = 0;
  for (const unsigned char *p = (const unsigned char *)in; *p && o + 8 < outn; p++) {
    switch (*p) {
      case '"': out[o++] = '\\'; out[o++] = '"'; break;
      case '\\': out[o++] = '\\'; out[o++] = '\\'; break;
      case '\n': out[o++] = '\\'; out[o++] = 'n'; break;
      case '\r': out[o++] = '\\'; out[o++] = 'r'; break;
      case '\t': out[o++] = '\\'; out[o++] = 't'; break;
      default:
        if (*p < 0x20) { o += (size_t)snprintf(out + o, outn - o, "\\u%04x", *p); }
        else out[o++] = (char)*p;
    }
  }
  out[o] = 0;
}

/* Find "key": "value" in a flat JSON document; returns 1 on success. */
static int jget(const char *doc, const char *key, char *out, size_t outn) {
  char pat[128];
  snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char *p = strstr(doc, pat);
  if (!p) return 0;
  p += strlen(pat);
  while (*p && (*p == ' ' || *p == '\t' || *p == ':')) p++;
  if (*p != '"') return 0;
  p++;
  size_t o = 0;
  while (*p && *p != '"' && o + 1 < outn) {
    if (*p == '\\' && p[1]) {
      p++;
      switch (*p) {
        case 'n': out[o++] = '\n'; break;
        case 't': out[o++] = '\t'; break;
        case 'r': out[o++] = '\r'; break;
        default: out[o++] = *p;
      }
    } else out[o++] = *p;
    p++;
  }
  out[o] = 0;
  return 1;
}

static long jgeti(const char *doc, const char *key, long dflt) {
  char pat[128];
  snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char *p = strstr(doc, pat);
  if (!p) return dflt;
  p += strlen(pat);
  while (*p && (*p == ' ' || *p == '\t' || *p == ':')) p++;
  if (!*p) return dflt;
  return strtol(p, NULL, 10);
}

static double now_s(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

int main(void) {
  static char job[131072];
  size_t n = fread(job, 1, sizeof(job) - 1, stdin);
  job[n] = 0;
  char op[32] = "", pkg[512] = "", model[128] = "", prompt[65536] = "";
  jget(job, "op", op, sizeof op);
  jget(job, "package_dir", pkg, sizeof pkg);
  jget(job, "model", model, sizeof model);
  jget(job, "prompt", prompt, sizeof prompt);
  long threads = jgeti(job, "threads", 4);
  long n_ctx = jgeti(job, "context", 4096);
  long max_tokens = jgeti(job, "max_tokens", 128);
  if (threads < 1 || threads > 16) threads = 4;
  if (n_ctx < 256) n_ctx = 4096;
  if (n_ctx > 32768) n_ctx = 32768;
  if (max_tokens < 1) max_tokens = 1;
  if (max_tokens > 2048) max_tokens = 2048;
  if (!op[0] || !pkg[0]) { emit("error", "\"code\":\"invalid_job\""); return 2; }
  if (!prompt[0]) snprintf(prompt, sizeof prompt, "Hello!");

  /* The package dir must contain exactly one .gguf file. */
  char gguf[1024] = "";
  int count = 0;
  DIR *dir = opendir(pkg);
  struct dirent *entry;
  while (dir && (entry = readdir(dir))) {
    size_t len = strlen(entry->d_name);
    if (len > 5 && !strcmp(entry->d_name + len - 5, ".gguf")) {
      snprintf(gguf, sizeof gguf, "%s/%s", pkg, entry->d_name);
      count++;
    }
  }
  if (dir) closedir(dir);
  int lockfd = open("/var/lib/nuxel-penguru/worker.lock", O_CREAT|O_RDWR, 0600);
  if (lockfd < 0 || flock(lockfd, LOCK_EX|LOCK_NB)) {
    emit("error", "\"code\":\"worker_busy\""); return 2;
  }
  struct sock_filter filter[] = {
    BPF_STMT(BPF_LD|BPF_W|BPF_ABS, offsetof(struct seccomp_data, nr)),
    BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K, __NR_socket, 0, 1),
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ERRNO | EPERM),
    BPF_STMT(BPF_RET|BPF_K, SECCOMP_RET_ALLOW)
  };
  struct sock_fprog program = {4, filter};
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) ||
      prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program)) {
    emit("error", "\"code\":\"network_isolation_unavailable\""); return 2;
  }
  if (count != 1) { emit("error", "\"code\":\"invalid_package\",\"detail\":\"expected one gguf\""); return 2; }

  signal(SIGTERM, on_signal);
  signal(SIGINT, on_signal);
  double t0 = now_s();
  emit("loading", "\"file\":\"%.*s\"", 256, gguf);
  llama_backend_init();

  struct llama_model_params mp = llama_model_default_params();
  mp.n_gpu_layers = 0;          /* CPU baseline only */
  struct llama_model *m = llama_model_load_from_file(gguf, mp);
  if (!m) { emit("error", "\"code\":\"load_failed\""); return 3; }
  const struct llama_vocab *vocab = llama_model_get_vocab(m);
  char archbuf[64] = "unknown";
  if (llama_model_meta_val_str(m, "general.architecture", archbuf,
                               sizeof archbuf) < 0)
    snprintf(archbuf, sizeof archbuf, "unknown");
  long load_ms = (long)((now_s() - t0) * 1000.0);
  emit("loaded", "\"engine\":\"llama.cpp\",\"architecture\":\"%.*s\","
       "\"n_params\":%llu,\"n_vocab\":%d,\"load_ms\":%ld,\"threads\":%ld,"
       "\"context\":%ld,\"model\":\"%.*s\",\"llama_version\":\"%.*s\"",
       60, archbuf, (unsigned long long)llama_model_n_params(m),
       llama_vocab_n_tokens(vocab), load_ms, threads, n_ctx, 120, model,
       40, llama_version());

  if (strcmp(op, "load_test") == 0) {
    llama_model_free(m);
    emit("done", "\"op\":\"load_test\",\"result\":\"pass\",\"load_ms\":%ld,"
         "\"architecture\":\"%.*s\"", load_ms, 60, archbuf);
    llama_backend_free();
    return 0;
  }

  struct llama_context_params cp = llama_context_default_params();
  cp.n_ctx = (uint32_t)n_ctx;
  cp.n_batch = 256;
  cp.n_ubatch = 256;
  cp.n_threads = (int32_t)threads;
  cp.n_threads_batch = (int32_t)threads;
  struct llama_context *ctx = llama_init_from_model(m, cp);
  if (!ctx) { llama_model_free(m); emit("error", "\"code\":\"context_failed\""); return 3; }

  const char *tmpl = llama_model_chat_template(m, NULL);
  if (!tmpl) { emit("error", "\"code\":\"missing_chat_template\""); return 4; }
  char formatted[131072];
  struct llama_chat_message msg = {"user", prompt};
  int np = llama_chat_apply_template(tmpl, &msg, 1, true, formatted, sizeof formatted);
  if (np < 0 || np >= (int)sizeof formatted) {
    emit("error", "\"code\":\"unsupported_chat_template\""); return 4;
  }
  int32_t *toks = malloc(sizeof(int32_t) * (size_t)(n_ctx + 8));
  int nt = llama_tokenize(vocab, formatted, np, toks, (int32_t)n_ctx, true, true);
  if (nt <= 0) { free(toks); llama_free(ctx); llama_model_free(m);
                 emit("error", "\"code\":\"tokenize_failed\""); return 4; }

  llama_batch batch = llama_batch_init(256, 0, 1);
  int pos = 0, rc = 0;
  for (int off = 0; off < nt && !g_cancel; off += 256) {
    int count = nt - off < 256 ? nt - off : 256;
    batch.n_tokens = count;
    for (int i = 0; i < count; i++) {
      batch.token[i] = toks[off + i];
      batch.pos[i] = pos + i;
      batch.n_seq_id[i] = 1;
      batch.seq_id[i][0] = 0;
      batch.logits[i] = (off + i == nt - 1) ? 1 : 0;
    }
    rc = llama_decode(ctx, batch);
    if (rc != 0) break;
    pos += count;
  }
  llama_batch_free(batch);
  free(toks);
  if (g_cancel) { emit("cancelled", "\"reason\":\"signal\""); }
  else if (rc == -2) { emit("oom", "\"code\":\"decode_oom\""); }
  else if (rc != 0) { emit("error", "\"code\":\"decode_failed\",\"rc\":%d", rc); }

  int gen = 0;
  char output[65537];
  size_t olen = 0;
  output[0] = 0;
  double t_first = 0, t_gen = now_s();
  if (!g_cancel && rc == 0) {
    llama_sampler_chain_params sp = llama_sampler_chain_default_params();
    struct llama_sampler *chain = llama_sampler_chain_init(sp);
    llama_sampler_chain_add(chain, llama_sampler_init_greedy());
    for (int step = 0; step < max_tokens && pos < n_ctx && !g_cancel; step++) {
      llama_token tok = llama_sampler_sample(chain, ctx, -1);
      llama_sampler_accept(chain, tok);
      if (llama_vocab_is_eog(vocab, tok)) break;
      char piece[257];
      int pl = llama_token_to_piece(vocab, tok, piece, sizeof piece - 1, 0, true);
      if (pl > 0 && pl < (int)sizeof piece) {
        char esc[1024];
        piece[pl] = 0;
        json_escape(piece, esc, sizeof esc);
        emit("token", "\"text\":\"%s\"", esc);
        size_t k = (size_t)pl;
        if (olen + k < sizeof(output) - 1) { memcpy(output + olen, piece, k); olen += k; output[olen] = 0; }
        if (t_first == 0) t_first = now_s() - t_gen;
        gen++;
      }
      if (llama_vocab_is_eog(vocab, tok)) break;
      batch = llama_batch_init(1, 0, 1);
      batch.n_tokens = 1;
      batch.token[0] = tok;
      batch.pos[0] = pos;
      batch.n_seq_id[0] = 1;
      batch.seq_id[0][0] = 0;
      batch.logits[0] = 1;
      rc = llama_decode(ctx, batch);
      llama_batch_free(batch);
      if (rc != 0) break;
      pos++;
    }
    llama_sampler_free(chain);
    double elapsed = now_s() - t_gen;
    if (elapsed <= 0) elapsed = 1e-6;
    if (g_cancel) {
      emit("cancelled", "\"reason\":\"signal\",\"generated_tokens\":%d", gen);
    } else if (rc == -2) {
      emit("oom", "\"code\":\"decode_oom\"");
    } else if (rc != 0) {
      emit("error", "\"code\":\"decode_failed\",\"rc\":%d", rc);
    } else {
      emit("done", "\"op\":\"%.*s\",\"result\":\"ok\",\"prompt_tokens\":%d,"
           "\"generated_tokens\":%d,\"decode_tokens_per_second\":%.3f,"
           "\"time_to_first_token_ms\":%ld,\"output\":\"%.*s\"",
           24, op, nt, gen, (double)gen / elapsed, (long)(t_first * 1000.0),
           65536, output);
    }
  }
  llama_free(ctx);
  llama_model_free(m);
  llama_backend_free();
  emit("unloaded", "\"reason\":\"job_complete\"");
  return 0;
}
