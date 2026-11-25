/*
 * test_rfs_policy.c — unit tests for rfs_policy.c in a real temp tree.
 * SPDX-License-Identifier: GPL-2.0-only
 * Build: gcc -I../src -o test_rfs_policy test_rfs_policy.c ../src/rfs_policy.c
 */
#include "rfs_policy.h"
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

static int failures = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { failures++; printf("FAIL %d: ", __LINE__); \
        printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %d: ", __LINE__); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

static char ROOT[512], SUB[512];

static void mk(const char *p) { mkdir(p, 0755); }
static void wr(const char *p, const char *s) {
    int fd = open(p, O_CREAT|O_WRONLY|O_TRUNC, 0644);
    if (fd >= 0) { write(fd, s, strlen(s)); close(fd); }
}
static void join_path(char *dst, size_t n, const char *a, const char *b) {
    size_t an = strlen(a), bn = strlen(b);
    if (an >= n || bn >= n - an - 1) {
        fputs("test path exceeds buffer\n", stderr);
        exit(2);
    }
    memcpy(dst, a, an);
    dst[an] = '/';
    memcpy(dst + an + 1, b, bn + 1);
}

int main(void)
{
    char tmpl[] = "/tmp/nuxel-rfs-XXXXXX";
    char *t = mkdtemp(tmpl);
    if (!t) { printf("mkdtemp failed\n"); return 2; }
    strcpy(ROOT, t);
    join_path(SUB, sizeof SUB, ROOT, "sub");

    char p[600];
    mk(SUB);
    join_path(p, sizeof p, ROOT, "safe.bin");   wr(p, "ok");
    join_path(p, sizeof p, ROOT, "secret.bin"); wr(p, "secret");
    join_path(p, sizeof p, SUB, "inner.bin");   wr(p, "inner");

    struct rfs_access acc;

    rfs_policy_set_root(ROOT);
    rfs_policy_allow("safe.bin", false);
    rfs_policy_allow("sub", false);

    CHECK(rfs_policy_validate("safe.bin", 0, false, &acc) == RFS_ALLOW_READ,
          "allow safe.bin read");
    CHECK(rfs_policy_validate("sub/inner.bin", 0, false, &acc) == RFS_ALLOW_READ,
          "allow sub/inner.bin read (dir entry)");

        /* create hardlink + efs fixtures AFTER positive allow tests */
    { char a[600], b[600];
      join_path(a,sizeof a,ROOT,"safe.bin"); join_path(b,sizeof b,ROOT,"hard.bin"); link(a,b);
      join_path(a,sizeof a,ROOT,"efs"); mk(a);
      join_path(a,sizeof a,ROOT,"efs/nv.bin"); wr(a,"x"); }
        /* symlinks created here too */
    join_path(p, sizeof p, ROOT, "link_esc"); symlink("/etc", p);
    join_path(p, sizeof p, ROOT, "link_bin"); symlink("/bin", p);
    CHECK(rfs_policy_validate("secret.bin", 0, false, &acc) == RFS_DENY,
          "DENY non-allowlisted file");
    CHECK(acc.deny_reason == RFS_DENY_NOT_ALLOWLISTED, "reason NOT_ALLOWLISTED");

    CHECK(rfs_policy_validate("../etc/passwd", 0, false, &acc) == RFS_DENY,
          "DENY dotdot traversal");
    CHECK(acc.deny_reason == RFS_DENY_TRAVERSAL_DOTDOT, "reason DOTDOT");

    CHECK(rfs_policy_validate("/etc/passwd", 0, false, &acc) == RFS_DENY,
          "DENY absolute path");
    CHECK(acc.deny_reason == RFS_DENY_ABSOLUTE, "reason ABSOLUTE");

    CHECK(rfs_policy_validate("safe.bin\\..\\..\\etc", 0, false, &acc) == RFS_DENY,
          "DENY backslash");

    CHECK(rfs_policy_validate("link_esc/passwd", 0, false, &acc) == RFS_DENY,
          "DENY symlink escape");
    CHECK(acc.deny_reason == RFS_DENY_SYMLINK || acc.deny_reason == RFS_DENY_ROOT_ESCAPE,
          "reason SYMLINK-or-ROOT_ESCAPE (got %s)", rfs_deny_reason_name(acc.deny_reason));

    CHECK(rfs_policy_validate("hard.bin", 0, false, &acc) == RFS_DENY,
          "DENY hardlink");
    CHECK(acc.deny_reason == RFS_DENY_HARDLINK, "reason HARDLINK");

    rfs_policy_allow("efs", false);
    CHECK(rfs_policy_validate("efs/nv.bin", 0, false, &acc) == RFS_DENY,
          "DENY protected /efs prefix");
    CHECK(acc.deny_reason == RFS_DENY_PROTECTED_PREFIX, "reason PROTECTED_PREFIX");

    CHECK(rfs_policy_validate("safe.bin", 1, true, &acc) == RFS_DENY,
          "DENY write to read-only-allowlisted file");

    CHECK(rfs_policy_validate("", 0, false, &acc) == RFS_DENY, "DENY empty path");

    rfs_policy_set_root(NULL);
    CHECK(rfs_policy_validate("safe.bin", 0, false, &acc) == RFS_DENY,
          "DENY when root not installed");

    rfs_policy_set_root(ROOT);
    rfs_policy_clear_allowlist();
    rfs_policy_allow("sub", true);
    CHECK(rfs_policy_validate("sub/inner.bin", 1, true, &acc) == RFS_ALLOW_WRITE,
          "ALLOW write to write-allowlisted subtree");

    /* A short relative name under a long valid root must not be authorized
     * with a truncated absolute output path. */
    char long_dirs[3][1024];
    char component[201];memset(component,'x',200);component[200]=0;
    join_path(long_dirs[0],sizeof long_dirs[0],ROOT,component);assert(mkdir(long_dirs[0],0700)==0);
    join_path(long_dirs[1],sizeof long_dirs[1],long_dirs[0],component);assert(mkdir(long_dirs[1],0700)==0);
    join_path(long_dirs[2],sizeof long_dirs[2],long_dirs[1],component);assert(mkdir(long_dirs[2],0700)==0);
    char long_file[1200];join_path(long_file,sizeof long_file,long_dirs[2],"safe.bin");
    FILE *long_stream=fopen(long_file,"w");assert(long_stream);fclose(long_stream);
    rfs_policy_set_root(long_dirs[2]);rfs_policy_clear_allowlist();rfs_policy_allow("safe.bin",false);
    CHECK(rfs_policy_validate("safe.bin",0,false,&acc)==RFS_DENY,"DENY truncated absolute result");
    CHECK(acc.deny_reason==RFS_DENY_NAMING,"long result reports naming error");
    unlink(long_file);for(int i=2;i>=0;i--)rmdir(long_dirs[i]);

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS",
           failures);

    /* cleanup */
    join_path(p,sizeof p,ROOT,"hard.bin"); unlink(p);
    join_path(p,sizeof p,ROOT,"link_esc"); unlink(p);
    join_path(p,sizeof p,ROOT,"link_bin"); unlink(p);
    join_path(p,sizeof p,ROOT,"safe.bin"); unlink(p);
    join_path(p,sizeof p,ROOT,"secret.bin"); unlink(p);
    join_path(p,sizeof p,SUB,"inner.bin"); unlink(p);
    join_path(p,sizeof p,ROOT,"efs/nv.bin"); unlink(p);
    join_path(p,sizeof p,ROOT,"efs"); rmdir(p);
    rmdir(SUB); rmdir(ROOT);
    return failures ? 1 : 0;
}
