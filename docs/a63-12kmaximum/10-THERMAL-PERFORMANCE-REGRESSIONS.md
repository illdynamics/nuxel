# Thermal and performance regressions

At diagnosis time the phone had about 6.5 GiB available memory, root filesystem 64% used, and a one-second CPU sample of about 1% busy. Load average was high but did not correspond to CPU saturation. There was no memory/storage exhaustion explaining the lockscreen symptom.

The web server was converted from an orphan process plus failed unit to an active, unprivileged `nuxel-web.service`; HTTP returned 200 afterward. Touch absence in charger mode remains the dominant usability blocker. Thermal soak and post-boot interactive latency still need physical measurement.
