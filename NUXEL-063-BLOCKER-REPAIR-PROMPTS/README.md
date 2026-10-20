# Nuxel — 31 `csft` blocker loop + 88-task Git/PR orchestrator

**Purpose:** Run the 31 previously authored repair prompts sequentially, OR prepare 88 separate cumulative pull requests by executing all 31 blocker prompts and the 57 existing component-branch prompts through `csft`.

**The two modes are alternatives, not steps to run consecutively.** The simple mode performs no Git bookkeeping and will not version-bump. The 88-PR mode does. No agent, PR or phone task was run against your actual remote/device to create this kit.

## Requirements

- macOS, Python 3, Git and GitHub CLI (`brew install gh`), authenticated `gh auth login`.
- A **clean** checkout of the real Nuxel Git repository containing `VERSION` and `CHANGELOG.md` and an accessible `origin/main`.
- `csft` accessible through your interactive `zsh` shell, and the 57 original remote `nuxel/*` prompt branches already created/pushed.
- Live USB connection from MacBook to Galaxy S10+, with a **real** repeatable USB-console reachability check supplied as `NUXEL_PHONE_CHECK`. This check alone does not verify speaker/Wi-Fi hardware.
- GitHub repository must allow **merge commits** (not squash-only or rebase-only). Its actions, branch policies and release permissions still need independent validation.

## A. Exactly the requested quick one-liner (31 prompts only)

Run **in the folder containing all 31 numbered Markdown prompts**:

```zsh
for p in ./*.md; do csft "$(cat "$p")" || break; done
```

This iterates files in lexical order (01–31) and stops when `csft` fails. A failed/blocked repair is not automatically counted as a working hardware component. This is **NOT** the 31-task execution-order manifest order and does **NOT** make branches/PRs. For the recommended supplied execution order, run:

```zsh
cd ~/Projects/NUXEL-88-PR-ORCHESTRATOR
bash scripts/run-31-simple.sh "$PWD/blocker-prompts/prompts"
```

That script loads `data/blockers.tsv`, executes `zsh -ic 'csft "$(cat "./$1")"'` once per file, and stops on error. It intentionally runs in the prompt directory as requested; if the agent requires a Git workspace to edit, use Mode B.

## B. The Git-aware 88-task queue (recommended for individually reviewed PRs)

**Never run Mode A first if you intend to run Mode B:** you'd implement the 31 repairs twice.

```zsh
cd ~/Projects
unzip ~/Downloads/NUXEL-88-PR-ORCHESTRATOR.zip
cd NUXEL-88-PR-ORCHESTRATOR

python3 scripts/run-88-pr-queue.py --repo ~/Projects/nuxel --dry-run

gh auth status
git -C ~/Projects/nuxel status --short

# Example ONLY; replace with your proven USB console command:
export NUXEL_PHONE_CHECK='YOUR_PROVEN_S10PLUS_USB_SHELL_CHECK'

# Pilot one task and inspect resulting PR:
python3 scripts/run-88-pr-queue.py --repo ~/Projects/nuxel --limit 1

# Prepare the remaining tasks/PRs. This may take hours or days:
python3 scripts/run-88-pr-queue.py --repo ~/Projects/nuxel
```

Default shell is `zsh`. If `csft` is a Bash function or executable instead, pass `--agent-shell bash`. Each invocation is effectively `csft "$(cat ./<branch-specific-prompt>.md)"`, with the current directory set to the dedicated Nuxel Git worktree. One `csft` session finishes before the next begins.

**81? No: precisely 88 tasks = 31 + 57.** The actual queue consists of repair branches `repair/063-...` plus the existing 57 `nuxel/` branches. The first repair task from supplied `EXECUTION-ORDER.tsv` is B04 (icon/cache), then B28 (fresh image parity). The prompt-only branch phase begins with P06, then P08/P09/P11 and R06–R58.

### Versions

The runner reads `VERSION` from **origin/main**. If the current main is `v0.6.3-beta`, the planned 88 task versions are `v0.6.4-beta` through `v0.6.91-beta`. Each PR updates `VERSION`, `CHANGELOG.md` and task-related docs; agents must update any other authoritative version metadata and image-build paths. Historical version citations stay historical.

### PR review and release — critical

Each PR targets `main` but **contains its preceding PR's commit history**. You **must merge PRs in queue order, with “Create a merge commit”**. This maintains clean incremental Git diffs and avoids the previous commit being reintroduced in later PRs. The script refuses to run if the repository disallows merge commits. A squash merge breaks this scheme. No force-pushes or direct `main` pushes are performed.

- DO NOT merge any PR while the queue is still preparing more PRs: a moving `origin/main` causes the runner to stop for reconciliation.
- Each queued release tag is only a **future** tag. The actual GitHub workflow creates/publishes the matching beta release **after the corresponding PR is merged and release/build gates pass**.
- The S10+ image built from a PR's source must contain all merged implementation and device manifests; the script does not manufacture or verify a GitHub image remotely on its own.
- `docs/repair-evidence/<ID>.md` is required for each task and must separate SOURCE, DEPLOYMENT and physical hardware results. Unverified/blocked hardware PRs are created as **drafts**, not as falsely verified releases.
- Device-side deployment via the user's agent should use rollback-safe userspace updates, not flashing. Versioned image parity remains a separate CI/hardware verification obligation.

### Failure and resume

The script stores state under `.nuxel-pr-state` outside the Nuxel repo; it never automatically erases or force-resets work. It stops on conflicts, dirty worktree, missing phone, failure of `csft`, missing evidence, unexpected branch changes, version drift, Git failures and protected merge policy. Fix the problem at the reported checkpoint, then rerun. If Git push succeeds but GitHub PR creation fails, **manual reconciliation is necessary** before resuming; never run a fresh queue over a half-published commit without inspecting it.

`--dry-run` is completely read-only and prints all 88 tasks. `--limit 1` executes one as a pilot; omitted or `--limit 0` attempts the full remaining queue. The original checkout remains untouched; Git operations occur in a separate worktree under the kit directory. Keep the kit out of the Nuxel repo.

### Security and physical-safety limits

The agent may have permission to access the live phone; no script can *guarantee* an agent honestly verified physical audio, Wi-Fi, camera or GNSS. Every PR needs human review of receipts and, where needed, owner acceptance. If any hardware capability requires boot-critical changes, **stop and request separate authorization**. Do not leave the phone irrecoverably changed while preparing many PRs.

### Package files

- `scripts/run-31-simple.sh` — direct serial prompt executor.
- `scripts/run-88-pr-queue.py` — Git-worktree version/PR orchestrator with evidence gates.
- `SOL-88-TASK-LIVE-PR-MASTER-PROMPT.md` — model instruction for the entire queue.
- `data/blockers.tsv` and `data/components.tsv` — exact task inventory/order.
- `blocker-prompts/prompts/*.md` — 31 original standalone blocker prompts.
