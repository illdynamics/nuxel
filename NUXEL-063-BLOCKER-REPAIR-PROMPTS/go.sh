#!/usr/bin/env bash
# Run the 31 repair prompts one at a time using the local csft executor.
# This simple runner DOES NOT create branches, commits, PRs, or version bumps.
set -euo pipefail
PROMPTS="${1:-./prompts}"
ORDER="${2:-./EXECUTION-ORDER.tsv}"
[ -d "$PROMPTS" ] || { echo "Missing prompt folder: $PROMPTS" >&2; exit 1; }
[ -f "$ORDER" ] || { echo "Missing execution-order manifest: $ORDER" >&2; exit 1; }
# Run from the prompts directory, as requested. zsh -ic resolves a csft alias/function.
cd "$PROMPTS"
command -v zsh >/dev/null || { echo 'zsh required (macOS default)' >&2; exit 1; }
while IFS=$'\t' read -r seq issue priority prereqs filename title; do
  [ "$seq" = execution_order ] && continue
  [ -n "$filename" ] || continue
  [ -f "./$filename" ] || { echo "Missing $filename" >&2; exit 1; }
  printf '\n[Nuxel] %s/31 %s — %s\n' "$seq" "$issue" "$title"
  zsh -ic 'csft "$(cat "./$1")"' _ "$filename" || {
    echo "STOP: csft failed on $filename. Remaining prompts NOT run." >&2; exit 1;
  }
done < "$ORDER"

