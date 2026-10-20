#!/usr/bin/env python3
"""Evidence-based Nuxel Exynos S10+ bootloop triage, never a generic 'fixed' claim."""
import argparse
import collections
import json
import pathlib
import re
import sys

# A hit is a clue requiring review, not proof of the underlying root cause.
PATTERNS = [
    ("kernel_panic", "urgent", r"Kernel panic|not syncing|Attempted to kill init|Unable to handle kernel paging request|Synchronous External Abort"),
    ("kernel_watchdog", "urgent", r"watchdog.*(?:bite|expired|reset)|soft lockup|hard LOCKUP|RCU.*stall"),
    ("root_mount", "urgent", r"VFS: Unable to mount root fs|unknown-block\(|Cannot open root device|mount:.*(?:can't find|failed)|/newroot.*failed"),
    ("missing_init", "urgent", r"No working init found|Failed to execute /init|Failed to execute /sbin/init|Requested init .* failed|exec /sbin/init.*not found"),
    ("filesystem", "high", r"EXT4-fs.*(?:error|corrupt)|I/O error|Buffer I/O error|invalid superblock|journal has aborted"),
    ("device_tree", "high", r"OF:.*(?:failed|error)|fdt.*(?:invalid|corrupt)|dtb.*(?:invalid|failed)|reserved memory.*(?:failed|error)"),
    ("ufs", "high", r"ufshcd.*(?:fatal|failed|error)|ufs.*(?:timeout|failed|abort)|scsi.*timed out"),
    ("display", "medium", r"drm.*(?:failed|error)|panel.*(?:failed|error)|decon.*(?:failed|error)|dsi.*(?:failed|error)|framebuffer.*(?:failed|error)"),
    ("init_services", "medium", r"systemd\[1\].*(?:failed|emergency)|Failed to start.*(?:greetd|phosh|phoc)|greetd.*(?:error|failed)|phosh.*(?:crash|failed)|phoc.*(?:crash|failed)"),
    ("selinux", "medium", r"avc: *denied|SELinux:.*(?:denied|error)"),
]
IGNORE_NAMES = {"SESSION.txt", "CAPTURE-STATUS.tsv", "TRIAGE.md", "TRIAGE.json"}

def applicable_files(root):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in IGNORE_NAMES or p.name.endswith(".stderr"):
            continue
        if p.suffix.lower() not in (".txt", ".log", ".dmesg", ".pstore", ""):
            continue
        if any(part in {"boot-image", "rootfs-image"} for part in p.relative_to(root).parts):
            continue
        if p.stat().st_size > 128 * 1024 * 1024:
            continue
        yield p

def triage(root):
    matches = []
    file_count = 0
    previous_boot_count = 0
    for path in applicable_files(root):
        file_count += 1
        rel = str(path.relative_to(root))
        # Only an actual stored pstore artifact or successful last_kmsg capture
        # is evidence of a previous boot. Listing files and placeholder notices
        # must NEVER turn a missing previous-boot log into a positive result.
        pstore_payload = rel.startswith("pstore/") and path.name not in (
            "listing.txt", "NO-PSTORE-FILES.txt")
        last_kmsg_payload = rel.endswith("/last_kmsg.txt")
        source = "previous_boot" if (pstore_payload or last_kmsg_payload) else "current_recovery_or_host"
        if source == "previous_boot" and path.stat().st_size > 0: previous_boot_count += 1
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for number, line in enumerate(fh, 1):
                for category, priority, regex in PATTERNS:
                    if re.search(regex, line, flags=re.IGNORECASE):
                        if len(matches) < 250:
                            matches.append({"file": rel, "line": number, "category": category,
                                            "priority": priority, "source": source, "excerpt": line.strip()[:260]})
                        break
    result = {
        "status": "EVIDENCE_CAPTURED_NEEDS_REVIEW" if previous_boot_count else "NO_PREVIOUS_BOOT_LOGS_AVAILABLE",
        "files_scanned": file_count,
        "previous_boot_candidate_files": previous_boot_count,
        "matches": matches,
        "note": "Regex hits are hypotheses, not confirmed root causes. Current recovery logs do not describe the earlier Nuxel kernel.",
    }
    counts = collections.Counter((x["category"], x["source"]) for x in matches)
    lines = ["# Nuxel S10+ bootloop triage", "", "**Result:** " + result["status"], "",
             "Collected log files scanned: " + str(file_count), "",
             "A kernel panic cannot be ruled out by an empty pstore directory. The phone may reboot before pstore is initialized, or firmware may clear it.", "",
             "## Evidence categories", ""]
    if not matches:
        lines += ["No matching signatures found. This is **not** a clean-boot verdict.", ""]
    else:
        for (category, source), count in counts.most_common():
            lines.append(f"- {category} ({source}): {count} occurrence(s)")
        lines += ["", "## Samples (review context in raw logs)", ""]
        for item in matches[:80]:
            lines.append(f"- `{item['file']}:{item['line']}` [{item['source']}; {item['category']}] {item['excerpt']}")
    lines += ["", "## Decision tree", "",
        "1. **Previous-boot pstore/last_kmsg contains panic or mount failure:** examine precise kernel stack, error code and failing path; inspect BOOT initramfs and Fedora rootfs together.",
        "2. **Recovery logs exist but previous-boot logs do not:** don't attribute recovery dmesg to Nuxel. Investigate UART/earlycon and kernel pstore support as a *separate, reviewed firmware/kernel modification*.",
        "3. **BOOT/DTB fails before kernel logging:** consider S-Boot handoff, DTB/DTBO overlay application, cmdline, vbmeta/recovery launch semantics.",
        "4. **Kernel starts but display stays black:** assess kernel log for DECON/DSI/panel failures. Phosh cannot fix absent DRM/KMS.",
        "5. **systemd starts but UI absent:** check greetd/Phosh/Phoc services, permissions, seatd/logind, input and display nodes after bringing up a debug console.",
        "", "No device writes, resets, repartitioning or flashing were performed by this triage tool.", ""]
    (root / "TRIAGE.json").write_text(json.dumps(result, indent=2) + "\n")
    (root / "TRIAGE.md").write_text("\n".join(lines))
    print(f"Status: {result['status']}; {file_count} files; {len(matches)} signature hit(s)")
    print("Triage report:", root / "TRIAGE.md")
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture_dir", type=pathlib.Path)
    args = ap.parse_args()
    if not args.capture_dir.is_dir():
        ap.error("Capture directory does not exist")
    triage(args.capture_dir)
    return 0

if __name__ == "__main__":
    sys.exit(main())
