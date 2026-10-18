# CI workflow audit

The Release workflow resolves one canonical tag, captures one source SHA, and
checks out that SHA for both build and publication. It preserves S10+ and G7
Power. S10+ builds the known A25 BOOT construction plus the current Fedora 43
rootfs, then runs A34/A33 interaction tests and fail-closed artifact checks.
