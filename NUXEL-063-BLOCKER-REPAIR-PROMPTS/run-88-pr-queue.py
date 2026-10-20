#!/usr/bin/env python3
"""Nuxel sequential 31 blocker + 57 original-branch implementation/PR queue.

Git history is deliberately stacked and PRs MUST be merged into main using
GitHub 'Create a merge commit', in queue order. No force-push/rebase/squash.
Phone testing is delegated to csft with a user-provided USB reachability test.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

KIT = Path(__file__).resolve().parent.parent
BLOCKERS = KIT / "data" / "blockers.tsv"
COMPONENTS = KIT / "data" / "components.tsv"
PROMPTS = KIT / "blocker-prompts" / "prompts"
STATE = KIT / ".nuxel-pr-state"
WT = STATE / "worktree"
BLOCKER_HEADERS = {"execution_order", "issue_id", "priority", "prerequisites", "filename", "title"}
DANGEROUS = re.compile(r"(^|/)(\.env(?:\..+)?|id_rsa|id_ed25519|.*\.(?:pem|key|p12|pfx)|secrets?\.ya?ml)$", re.I)


def run(cmd, cwd=None, capture=True, check=True, env=None):
    cmd = list(map(str, cmd))
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None, check=False, env=env)
    if check and p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {shlex.join(cmd)}\n{(p.stdout or '')[-1300:]}\n{(p.stderr or '')[-1300:]}")
    return (p.stdout or "").strip()


def git(*args, cwd=None):
    return run(["git", *args], cwd=cwd or WT)


def safe_file(path, value):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    tmp.replace(path)


def load_tasks():
    out = []
    with BLOCKERS.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            assert set(row.keys()) == BLOCKER_HEADERS, row.keys()
            ident = row["issue_id"]
            out.append({"key": "B" + ident, "id": ident, "kind": "blocker",
                        "branch": f"repair/063-{ident}-{Path(row['filename']).stem[3:]}",
                        "filename": row["filename"], "title": row["title"]})
    with COMPONENTS.open(encoding="utf-8", newline="") as f:
        for vals in csv.reader(f, delimiter="\t"):
            if not vals or not vals[0]:
                continue
            if len(vals) != 3:
                raise RuntimeError(f"Bad components manifest row: {vals}")
            ident, branch, title = vals
            out.append({"key": ident, "id": ident, "kind": "component",
                        "branch": branch, "filename": f"PROMPT-{ident}.md", "title": title})
    if len(out) != 88 or len(set(t["key"] for t in out)) != 88:
        raise RuntimeError(f"Expected 88 unique tasks, saw {len(out)}")
    return out


def remote_tip(repo, ref):
    s = run(["git", "-C", str(repo), "ls-remote", "origin", "refs/heads/" + ref])
    if not s:
        raise RuntimeError(f"Remote branch absent: {ref}")
    return s.split()[0]


def clean_or_stop():
    status = git("status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"STOP — worktree has uncommitted changes. DO NOT CLEAN automatically.\n{status[:1500]}\nWorktree: {WT}")


def ensure_login(repo):
    run(["gh", "auth", "status"], cwd=repo)
    name = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], cwd=repo)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
        raise RuntimeError("Unable to determine GitHub owner/repository")
    allowed = run(["gh", "api", f"repos/{name}", "--jq", ".allow_merge_commit"], cwd=repo)
    if allowed != "true":
        raise RuntimeError("STOP: GitHub requires merge commits for stacked PRs. Repository does not allow merge commits. Enable them or use a gated one-PR-at-a-time workflow.")
    default = run(["gh", "api", f"repos/{name}", "--jq", ".default_branch"], cwd=repo)
    if default != "main":
        raise RuntimeError(f"Expected GitHub default branch main; got {default}")
    return name


def version(repo):
    v = run(["git", "-C", str(repo), "show", "origin/main:VERSION"])
    m = re.fullmatch(r"v?0\.6\.(\d+)(?:-beta)?", v.strip())
    if not m:
        raise RuntimeError(f"Unknown VERSION in origin/main: {v!r}; resolve before running")
    return int(m.group(1))


def agent_cli(prompt_file, shell, env):
    # Shell positional args avoid shell-quoting a prompt path into source code.
    # When csft is a zsh alias/function, interactive zsh loads the definition.
    # Actual invocation is: csft "$(cat ./path/to/prompt.md)".
    cmd = [shell, "-ic", 'csft "$(cat "./$1")"', "_", str(prompt_file)]
    # zsh -ic starts in the current working directory (the feature worktree).
    p = subprocess.run(cmd, cwd=WT, env=env)
    if p.returncode:
        raise RuntimeError(f"csft exited {p.returncode}; stopping queue on {prompt_file}")


def append_contract(source, task, vers):
    # Git diff --check rejects Markdown hard-break trailing double spaces.
    source = "\n".join(line.rstrip() for line in source.splitlines())
    return source.rstrip() + f"""

---

## AUTOMATED PR SESSION CONTRACT — {task['key']}

This prompt is being executed **NOW**, not generated. Implement and verify the
specific component in the currently checked-out Nuxel repository.

- Required target release version: **{vers}**. Update `VERSION`, `CHANGELOG.md`,
  relevant version metadata and user-facing docs with truthful, measurable
  feature/test status. Historical version mentions must remain historical.
- Test the code, regression/failure cases and current S10+ rootfs installer.
  Ensure the latest changes will be included in the GitHub-built S10+ image.
  If this needs release workflow or builder changes, implement and test them.
- Use the phone's **existing live USB console**, verify its current filesystem
  and service topology, back up affected files, deploy ONLY safe userspace
  changes, test actual runtime behavior, save hashes/logs and keep rollback.
- If hardware is blocked, write first-failure evidence, mark BLOCKED, and do
  not invent speaker/firmware/driver success. A physical/owner confirmation
  requirement cannot be satisfied by a unit test.
- You may execute tests and safe live userspace deployment. NO flashing, raw
  partition writes, kernel/bootloader swaps, unapproved reboots, destructive
  resets, unsafe audio-amplifier register changes or bypassing safeguards.
- Create `docs/repair-evidence/{task['key']}.md` containing the exact labels
  `Source checks:`, `Live deployment:`, `Device evidence:`,
  `Hardware verdict:` (HARDWARE VERIFIED, BLOCKED or NOT TESTED),
  `S10+ image parity:`, `Rollback:` with truthful receipts and logs.
- Document touched files, tests, runtime deployment and blockers in the named
  issue's docs. Preserve working phone, user data, configs and USB recovery.
- **DO NOT merge PRs, create tags/releases, force-push, modify origin/main, or
  start a separate parallel agent.** The surrounding queue handles git
  add/commit/push/PR. DO NOT checkout or rebase branches.
- If device or owner testing is unavailable, clearly identify it as NOT TESTED
  or BLOCKED and do not misreport a release as hardware-verified.

Complete the specific task now. Do not stop at another implementation plan.
"""


def make_prompt(task, vers):
    if task["kind"] == "blocker":
        source = PROMPTS / task["filename"]
        if not source.is_file():
            raise RuntimeError(f"Missing issue prompt {source}; extract blocker-prompts first")
        dst = WT / "docs" / "repair-prompts" / f"B{task['id']}-{task['filename']}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        safe_file(dst, append_contract(source.read_text(encoding="utf-8"), task, vers))
        return dst.relative_to(WT)
    src = WT / task["filename"]
    if not src.is_file():
        raise RuntimeError(f"Prompt absent from remote branch {task['branch']}: {src}")
    original = src.read_text(encoding="utf-8")
    if "AUTOMATED PR SESSION CONTRACT" in original:
        raise RuntimeError(f"Existing prompt already contains a session contract. Inspect {src}")
    safe_file(src, append_contract(original, task, vers))
    return src.relative_to(WT)


def update_version_docs(task, vers):
    (WT / "VERSION").write_text(vers + "\n", encoding="utf-8")
    path = WT / "CHANGELOG.md"
    if not path.exists():
        raise RuntimeError("No CHANGELOG.md; inspect project history")
    text = path.read_text(encoding="utf-8")
    summary = f"\n## {vers} — {task['key']} (PR candidate)\n\n- {task['title']}: implementation, verification and device results described in this PR's evidence.\n- Hardware status and image parity must be verified separately; this is not proof of physical functionality.\n"
    if not text.startswith("#"):
        raise RuntimeError("Unrecognized CHANGELOG.md, refusing autogenerated edit")
    pos = text.find("\n", 0)
    safe_file(path, text[:pos+1] + summary + text[pos+1:])


def check_secret_paths(base_sha):
    changed = git("status", "--porcelain", "--untracked-files=all")
    names = [line[3:].split(" -> ")[-1] for line in changed.splitlines()]
    names += git("diff", "--name-only", base_sha, "HEAD").splitlines()
    for path in names:
        if DANGEROUS.search(path):
            raise RuntimeError(f"Sensitive path {path}: review manually, no auto push")


def read_evidence(task):
    path = WT / "docs" / "repair-evidence" / f"{task['key']}.md"
    if not path.exists() or path.stat().st_size < 250:
        raise RuntimeError(f"Required evidence missing/too short: {path}")
    body = path.read_text(encoding="utf-8")
    for key in ("Source checks:", "Live deployment:", "Device evidence:",
                "Hardware verdict:", "S10+ image parity:", "Rollback:"):
        if key not in body:
            raise RuntimeError(f"Missing evidence label {key} in {path}")
    verdict = re.search(r"Hardware verdict:\s*(HARDWARE VERIFIED|BLOCKED|NOT TESTED)", body)
    if not verdict:
        raise RuntimeError(f"Use explicit HARDWARE VERIFIED/BLOCKED/NOT TESTED: {path}")
    return verdict.group(1)


def make_pr(repo, task, vers, sha, name, verdict):
    pr_title = f"{vers} | {task['key']}: {task['title']}"
    body = (f"### Nuxel serial implementation queue\n\n"
            f"Task: **{task['key']}** — {task['title']}\n\n"
            f"Target release: `{vers}`. Commit `{sha}`.\n\n"
            f"**MERGE ORDER REQUIRED.** This PR is stacked on the previous queued commit. "
            f"Merge prior PRs into `main` using **Create a merge commit** (NOT squash/rebase), "
            f"then verify this PR's diff and CI again before merging.\n\n"
            f"Any phone deployment is *userspace testing*, not proof that a GitHub release "
            f"exists. Compare device receipts and the built S10+ artifact before claiming parity.\n\n"
            f"Agent hardware verdict: {verdict} (needs independent review).\n\n"
            f"Reviewer: check docs, tests, live-device evidence and BLOCKED/NOT TESTED cases. "
            f"Do not merge an incomplete hardware mission as a verified feature.\n")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
        tmp.write(body)
        tmp_path = tmp.name
    try:
        # gh pr create can fail if one already exists. Always stop for reconciliation.
        cmd = ["gh", "pr", "create", "--base", "main", "--head", task["branch"],
               "--title", pr_title, "--body-file", tmp_path]
        if verdict != "HARDWARE VERIFIED":
            cmd.append("--draft")
        return run(cmd, cwd=repo)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True, help="Original clean Nuxel Git checkout")
    ap.add_argument("--limit", type=int, default=0, help="Run first N unprocessed tasks; 0=all")
    ap.add_argument("--only", default="", help="Only an identifier (cannot skip earlier stacked tasks)")
    ap.add_argument("--dry-run", action="store_true", help="Show 88 queued tasks without touching Git or phone")
    ap.add_argument("--agent-shell", choices=["zsh", "bash"], default="zsh")
    ap.add_argument("--phone-check", default=os.environ.get("NUXEL_PHONE_CHECK", ""),
                    help="Shell command that exits zero only if live USB phone is reachable")
    a = ap.parse_args()
    tasks = load_tasks()
    if a.dry_run:
        for i, t in enumerate(tasks, 1):
            print(f"{i:02d}/88 {t['key']:>3} {t['branch']} {t['filename']}")
        print("Planning only; no csft, Git changes, PRs or phone activity.")
        return
    if a.limit < 0:
        raise RuntimeError("--limit must be >=0")
    if not a.phone_check.strip():
        raise RuntimeError("STOP: set --phone-check 'your verified USB command' or NUXEL_PHONE_CHECK. Do not claim live deployment without a live phone.")
    for tool in ("git", "gh", a.agent_shell):
        if not shutil.which(tool):
            raise RuntimeError(f"Missing executable: {tool}")
    repo = a.repo.expanduser().resolve()
    if not (repo / ".git").exists():
        raise RuntimeError("--repo must point to a Git repository with .git")
    if repo == KIT or repo in KIT.parents or KIT in repo.parents:
        raise RuntimeError("Store this kit OUTSIDE the repository")
    if run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Original Git checkout is dirty: stop and preserve local work")
    run(["git", "-C", str(repo), "fetch", "origin", "--prune"], capture=False)
    ghname = ensure_login(repo)
    current_main = run(["git", "-C", str(repo), "rev-parse", "origin/main"])
    current_version = version(repo)
    if current_version < 3:
        raise RuntimeError(f"Expected main at 0.6.3-beta or later, got 0.6.{current_version}; reconcile release first")
    if STATE.joinpath("state.json").exists():
        st = json.loads(STATE.joinpath("state.json").read_text(encoding="utf-8"))
        if st["main_sha"] != current_main:
            raise RuntimeError("origin/main changed after queue began; STOP for reconciliation")
        if st["start_version"] != current_version:
            raise RuntimeError("VERSION changed after queue began; STOP")
    else:
        STATE.mkdir(parents=True, exist_ok=True)
        st = {"main_sha": current_main, "start_version": current_version, "tip": current_main,
              "completed": [], "repo": ghname}
        safe_file(STATE / "state.json", json.dumps(st, indent=2) + "\n")
    if st.get("repo") != ghname:
        raise RuntimeError("Queue state belongs to a different GitHub repository")
    if not WT.exists():
        run(["git", "-C", str(repo), "worktree", "add", "--detach", str(WT), st["tip"]], capture=False)
    if run(["git", "-C", str(WT), "rev-parse", "--show-toplevel"]) != str(WT):
        raise RuntimeError(f"Worktree mismatch: {WT}")
    clean_or_stop()
    if a.only and a.only not in {t["key"] for t in tasks}:
        raise RuntimeError(f"Unknown task: {a.only}")
    num = 0
    for idx, task in enumerate(tasks):
        if task["key"] in st["completed"]:
            continue
        # Stack consistency: completed keys must always be a prefix.
        if st["completed"] != [t["key"] for t in tasks[:len(st["completed"])]]:
            raise RuntimeError("Queue state non-prefix; manual reconciliation needed")
        if a.only and task["key"] != a.only:
            raise RuntimeError(f"Cannot skip preceding task {task['key']} in cumulative 88-PR mode. Use --limit and resume in order.")
        if a.limit and num >= a.limit:
            break
        print(f"\n========== {idx+1}/88: {task['key']} — {task['title']} ==========" , flush=True)
        if remote_tip(repo, "main") != st["main_sha"]:
            raise RuntimeError("origin/main advanced, stop and reconcile the stacked queue")
        run(["bash", "-lc", a.phone_check], capture=False)
        clean_or_stop()
        if task["kind"] == "component":
            run(["git", "-C", str(repo), "fetch", "origin", task["branch"]], capture=False)
            git("switch", "--detach", f"origin/{task['branch']}")
            # Incorporate cumulative previous work as a MERGE, not rebase: original
            # remote branch remains an ancestor and can be pushed fast-forward.
            # merge-base --is-ancestor returns 1 when a merge is needed.
            p = subprocess.run(["git", "merge-base", "--is-ancestor", st["tip"], "HEAD"], cwd=WT)
            if p.returncode:
                run(["git", "-C", str(WT), "merge", "--no-ff", "-m",
                    f"chore: integrate prior Nuxel queue through {st['completed'][-1] if st['completed'] else 'baseline'}", st["tip"]],
                    capture=False)
        else:
            git("switch", "--detach", st["tip"])
            # Never clobber a pre-existing remote branch that might contain work.
            existing = run(["git", "-C", str(repo), "ls-remote", "origin", "refs/heads/" + task["branch"]])
            if existing:
                raise RuntimeError(f"STOP: repair branch already exists on origin: {task['branch']}")
        vers = f"v0.6.{st['start_version'] + idx + 1}-beta"
        prompt_path = make_prompt(task, vers)
        update_version_docs(task, vers)
        prior_agent_sha = git("rev-parse", "HEAD")
        env = os.environ.copy()
        env.update({"NUXEL_QUEUE_ID":task["key"], "NUXEL_TARGET_VERSION":vers,
                    "NUXEL_PHONE_CHECK":a.phone_check, "NUXEL_QUEUE_REPO":str(WT)})
        print(f"Invoking csft on {prompt_path} in {WT}; version {vers}", flush=True)
        agent_cli(prompt_path, a.agent_shell, env)
        # A successful exit is NOT device proof; repeated USB check and receipts.
        run(["bash", "-lc", a.phone_check], capture=False)
        if subprocess.run(["git", "symbolic-ref", "-q", "--short", "HEAD"], cwd=WT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("Agent switched onto a branch; stop")
        if (WT / "VERSION").read_text(encoding="utf-8").strip() != vers:
            raise RuntimeError(f"VERSION drift: expected {vers}. Repair before PR")
        verdict = read_evidence(task)
        check_secret_paths(st["tip"])
        git("add", "-A")
        run(["git", "-C", str(WT), "diff", "--cached", "--check"])
        staged = git("diff", "--cached", "--name-only")
        if staged:
            git("commit", "-m", f"fix({task['key']}): {task['title']} [{vers}]")
        new_sha = git("rev-parse", "HEAD")
        if new_sha == prior_agent_sha:
            raise RuntimeError("No code/docs/test changes committed by task. Stop instead of publishing empty PR")
        if subprocess.run(["git", "merge-base", "--is-ancestor", st["tip"], "HEAD"], cwd=WT).returncode != 0:
            raise RuntimeError("New task lost cumulative previous work; stop")
        git("push", "origin", f"HEAD:refs/heads/{task['branch']}")
        url = make_pr(repo, task, vers, new_sha, ghname, verdict)
        print(f"PR CREATED: {url}")
        st["tip"] = new_sha
        st["completed"].append(task["key"])
        safe_file(STATE / "state.json", json.dumps(st, indent=2) + "\n")
        with (STATE / "pr-report.tsv").open("a", encoding="utf-8") as report:
            report.write(f"{idx+1}\t{task['key']}\t{vers}\t{task['branch']}\t{new_sha}\t{verdict}\t{url}\n")
        num += 1
        if a.only:
            break
    print(f"\nQueue paused/finished; completed {len(st['completed'])}/88. State: {STATE / 'state.json'}")
    print("IMPORTANT: all PRs are STACKED. Merge them in order using GitHub MERGE COMMITS only; no squash/rebase.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, AssertionError) as e:
        print(f"\nSTOP: {e}", file=sys.stderr)
        sys.exit(1)
