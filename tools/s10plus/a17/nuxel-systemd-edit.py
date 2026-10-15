#!/usr/bin/env python3
"""Nuxel/S10+ systemd 258.11 source edits so Fedora can start services on a
Linux 4.14 Exynos 9820 kernel (Samsung Galaxy S10+, beyond2lte).

Runs inside rpmbuild %prep with cwd = BUILD/systemd-258.11.

Edit 1 - src/basic/process-util.c :: posix_spawn_wrapper()
  glibc's pidfd_spawn() returns ENOSYS unconditionally when the kernel has no
  waitid(P_PIDFD) (Linux 5.4+).  258.11 retried pidfd_spawn() after clearing
  POSIX_SPAWN_SETCGROUP instead of falling back to plain posix_spawn(), so the
  spawn itself failed.  This is upstream's own later fix.

Edit 2 - src/basic/pidref.c :: pidref_set_pid()
  pidfd_open() was added in Linux 5.3, so on 4.14 the call always fails with
  ENOSYS and pidref_set_pid() returned -ENOSYS.  posix_spawn_wrapper()'s
  (now working) posix_spawn() fallback therefore *did* start sd-executor but
  still returned -ENOSYS to PID1, which logged
  "Failed to spawn executor: Function not implemented", failed the unit and
  orphaned the running executor.

  PROVEN on hardware + reproduced offline: candidate A16 logs, and a
  podman/fedora:43 harness that emulates a pidfd-less kernel against the
  shipped libsystemd-shared, both show
      posix_spawn_wrapper failed, rc=-38 ENOSYS, while the child still ran.
  A PidRef without a pidfd is an explicitly supported state (see pidref.h) and
  every consumer degrades to PID-only operation, so ENOSYS must degrade too.
"""
import sys

FAILED = []

def edit(path, old, new, label):
    s = open(path).read()
    if new in s:
        print("ALREADY APPLIED: %s" % label)
        return
    if old not in s:
        print("FATAL: anchor not found for %s in %s" % (label, path))
        FAILED.append(label)
        return
    if s.count(old) != 1:
        print("FATAL: anchor for %s is not unique (%d) in %s" % (label, s.count(old), path))
        FAILED.append(label)
        return
    open(path, "w").write(s.replace(old, new, 1))
    print("APPLIED: %s" % label)


# ---------------------------------------------------------------- edit 1 ------
PU = "src/basic/process-util.c"
PU_OLD = """        if (r != 0)
                return -r;

        r = pidref_set_pidfd_consume(ret_pidref, TAKE_FD(pidfd));
        if (r < 0)
                return r;

        return FLAGS_SET(flags, POSIX_SPAWN_SETCGROUP);
#else
"""
PU_NEW = """        if (r == 0) {
                r = pidref_set_pidfd_consume(ret_pidref, TAKE_FD(pidfd));
                if (r < 0)
                        return r;

                return FLAGS_SET(flags, POSIX_SPAWN_SETCGROUP);
        }

        if (!ERRNO_IS_NOT_SUPPORTED(r))
                return -r;

        /* pidfd_spawn() is unavailable (libc or kernel missing) -- fall back to plain
         * posix_spawn().  NUXEL/S10+: pidfd_spawn() needs waitid(P_PIDFD) (Linux 5.4),
         * independently of clone3(); glibc returns ENOSYS with no fallback there, which
         * made every systemd service spawn fail with "Failed to spawn executor:
         * Function not implemented" on the Samsung 4.14.253 kernel.  posix_spawn() is
         * clone3()-with-clone()-fallback and works here; the caller then attaches the
         * child to its cgroup itself (return 0 below). */
        pid_t pid;

        r = posix_spawn(&pid, path, NULL, &attr, argv, envp);
        if (r != 0)
                return -r;

        r = pidref_set_pid(ret_pidref, pid);
        if (r < 0)
                return r;

        return 0; /* No CLONE_INTO_CGROUP was used, the caller must move the child */
#else
"""

# ---------------------------------------------------------------- edit 2 ------
PR = "src/basic/pidref.c"
PR_OLD = """        fd = pidfd_open(pid, 0);
        if (fd < 0) {
                /* Graceful fallback in case the kernel is out of fds */
                if (!ERRNO_IS_RESOURCE(errno))
                        return log_debug_errno(errno, "Failed to open pidfd for pid " PID_FMT ": %m", pid);

                fd = -EBADF;
        }
"""
PR_NEW = """        fd = pidfd_open(pid, 0);
        if (fd < 0) {
                /* Graceful fallback in case the kernel is out of fds -- or has no pidfd support
                 * at all.  NUXEL/S10+ (Linux 4.14.253, Samsung Exynos 9820): pidfd_open() was
                 * added in Linux 5.3, so here it always fails with ENOSYS.  A PidRef without a
                 * pidfd is an explicitly supported state (see pidref.h) and every consumer
                 * degrades to PID-only operation, so this must degrade too.  Returning -ENOSYS
                 * made posix_spawn_wrapper() report a spawn failure for a process it had in
                 * fact already started successfully. */
                if (!ERRNO_IS_RESOURCE(errno) && !ERRNO_IS_NOT_SUPPORTED(errno))
                        return log_debug_errno(errno, "Failed to open pidfd for pid " PID_FMT ": %m", pid);

                fd = -EBADF;
        }
"""

# pidref_set_pidfd_impl(): same class of failure for pidfds handed to us.
PR2_OLD = """int pidref_set_pidfd_impl(PidRef *pidref, int fd, pid_t pid) {"""
print("# systemd source edits")
edit(PU, PU_OLD, PU_NEW, "process-util.c: posix_spawn() fallback")
edit(PR, PR_OLD, PR_NEW, "pidref.c: pidref_set_pid() degrades without pidfd_open()")

if FAILED:
    print("FAILED EDITS: %s" % ", ".join(FAILED))
    sys.exit(1)
print("ALL EDITS OK")
