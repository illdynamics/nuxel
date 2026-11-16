#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -d "$1/payload" ]]; then
  echo "Usage: verify-extracted.sh EXTRACTED_OUTPUT_DIR" >&2
  exit 64
fi
OUT=$(cd "$1" && pwd -P)
REPORT="$OUT/elf-report.txt"
: > "$REPORT"

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUT" && find payload -type f -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
fi

{
  echo "Nuxel S10+ GNSS extracted file verification"
  echo "output=$OUT"
  echo ""
  echo "This report establishes file hashes and ELF metadata only. It does not establish firmware/device compatibility."
  echo ""
} >> "$REPORT"

file_count=0
elf_count=0
while IFS= read -r -d '' f; do
  file_count=$((file_count+1))
  {
    echo "===== ${f#"$OUT"/} ====="
    if command -v file >/dev/null 2>&1; then file "$f"; fi
    if command -v readelf >/dev/null 2>&1 && readelf -h "$f" >/dev/null 2>&1; then
      elf_count=$((elf_count+1))
      echo "-- ELF header --"
      readelf -h "$f" | grep -E 'Class:|Data:|OS/ABI:|ABI Version:|Type:|Machine:' || true
      echo "-- Program interpreter --"
      readelf -l "$f" 2>/dev/null | grep -E 'Requesting program interpreter' || echo "(none / static / not shown)"
      echo "-- DT_NEEDED / SONAME / RPATH --"
      readelf -d "$f" 2>/dev/null | grep -E 'NEEDED|SONAME|RPATH|RUNPATH' || true
    fi
    echo ""
  } >> "$REPORT"
done < <(find "$OUT/payload" -type f -print0 | sort -z)

{
  echo "files=$file_count"
  echo "elf_files=$elf_count"
  echo ""
  echo "Compatibility reminders:"
  echo "- AArch64 ELF is not automatically Linux/glibc compatible; Android Bionic and HIDL/Binder dependencies matter."
  echo "- Never flash or load any file solely because this verifier recognized it."
  echo "- Verify source model SM-G975F, exact stock build, patch hash, hardware revision, and loader ABI."
} >> "$REPORT"

cat "$REPORT"
