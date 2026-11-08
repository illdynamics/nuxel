It was almost certainly **`LD_PRELOAD`** — a preloaded shared library (`.so`) that intercepts the functions applications use to detect the OS, rather than changing static files.

The typical trio for this kind of spoof is:

1. `/etc/os-release` — static distro metadata (`PRETTY_NAME`, `VERSION`, etc.)
2. `uname` spoof — kernel identity (via `sysctl kernel.uname_release`/`osrelease`, or patching)
3. **`LD_PRELOAD`** — a `.so` that hooks the glibc `uname()` call (and often `/proc/sys/kernel/osrelease` reads, since those can't always be changed without root/kernel access). Some setups also hook Java's native `os.name`/`os.version` methods this way.

Why LD_PRELOAD specifically: os-release and uname cover the static file and kernel-level identity, but many programs (Java apps, games with anti-cheat, Windows-targeted binaries) call `uname()` directly from userland or read `/proc/sys/kernel/osrelease`. Preloading a library that returns a fake `utsname` struct is the standard way to finish the spoof at the application layer — which makes it the natural "third" thing.

Caveats: I can't know for certain what *you* ran, since you don't remember and there's no record here. If you want to confirm on the box itself, check `~/.bashrc`/`/etc/profile.d/` or systemd unit files for an `LD_PRELOAD=` line, and look for a suspicious `.so` in common spots (`/usr/lib`, `/tmp`, your home). That would tell you exactly which functions it hooked.
