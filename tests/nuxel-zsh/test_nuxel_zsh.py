#!/usr/bin/env python3
"""Tests for the Nuxel zsh themes, configuration and banner.

All tests use a temporary HOME/config; none touch the developer's /etc,
~/.zshrc or default shell.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "services/nuxel-zsh/nuxel.zsh"
THEME = ROOT / "services/nuxel-zsh/nuxel-theme"
INSTALLER = ROOT / "services/nuxel-zsh/install-nuxel-zsh.sh"
BANNER = ROOT / "services/nuxel-zsh/nuxel-banner"
ZSH = shutil.which("zsh")


pytestmark = pytest.mark.skipif(ZSH is None, reason="zsh is not installed")


def _env(tmp: Path, style: str | None = None, **extra: str) -> dict[str, str]:
    home = tmp / "home"
    config = tmp / "config"
    home.mkdir(parents=True, exist_ok=True)
    (config / "nuxel").mkdir(parents=True, exist_ok=True)
    sysconf = tmp / "system-zsh.conf"
    userconf = config / "nuxel" / "zsh.conf"
    if style is not None:
        userconf.write_text(f"NUXEL_PROMPT_STYLE={style}\n")
    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(config),
        "NUXEL_ZSH_SYSTEM_CONF": str(sysconf),
        "NUXEL_ZSH_USER_CONF": str(userconf),
        "NUXEL_BANNER_FILE": str(BANNER),
        "NUXEL_BANNER": "0",
    })
    env.update(extra)
    return env


def _zsh(tmp: Path, script: str, style: str | None = None, cwd: Path | None = None,
         **extra: str) -> subprocess.CompletedProcess[str]:
    env = _env(tmp, style, **extra)
    return subprocess.run(
        [ZSH, "-f", "-c", f"source {RUNTIME}\n{script}"],
        cwd=str(cwd) if cwd else str(tmp),
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_default_theme_is_one(tmp_path: Path) -> None:
    out = _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"')
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "1"


@pytest.mark.parametrize("style,marker", [
    ("1", "🐧"),
    ("2", "┌──"),
    ("3", "❯"),
    ("4", "⚡"),
])
def test_all_four_themes(tmp_path: Path, style: str, marker: str) -> None:
    out = _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"; print -r -- "$PROMPT"', style=style)
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines()[0] == style
    assert marker in out.stdout


def test_per_user_override_wins(tmp_path: Path) -> None:
    sysconf = tmp_path / "system-zsh.conf"
    sysconf.write_text("NUXEL_PROMPT_STYLE=1\n")
    out = _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"', style="3")
    assert out.stdout.strip() == "3"


def test_invalid_config_falls_back_to_default(tmp_path: Path) -> None:
    out = _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"', style="9")
    assert out.stdout.strip() == "1"


def test_persistence_across_new_shells(tmp_path: Path) -> None:
    assert _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"', style="4").stdout.strip() == "4"
    assert _zsh(tmp_path, 'print -r -- "$NUXEL_PROMPT_STYLE"').stdout.strip() == "4"


def test_theme_cli_writes_and_backs_up(tmp_path: Path) -> None:
    config = tmp_path / "config"
    conf = config / "nuxel" / "zsh.conf"
    conf.parent.mkdir(parents=True)
    conf.write_text("# keep me\nNUXEL_PROMPT_STYLE=2\nNUXEL_BANNER=0\n")
    env = dict(os.environ)
    env.update({"HOME": str(tmp_path / "home"),
                "XDG_CONFIG_HOME": str(config),
                "NUXEL_ZSH_SYSTEM_CONF": str(tmp_path / "system-zsh.conf")})
    run = subprocess.run([shutil.which("sh"), str(THEME), "4"], env=env,
                         text=True, capture_output=True, timeout=10)
    assert run.returncode == 0, run.stderr
    text = conf.read_text()
    assert "NUXEL_PROMPT_STYLE=4" in text
    assert "NUXEL_BANNER=0" in text
    assert "# keep me" in text
    assert list(conf.parent.glob("zsh.conf.bak.*"))
    bad = subprocess.run([shutil.which("sh"), str(THEME), "9"], env=env,
                         text=True, capture_output=True, timeout=10)
    assert bad.returncode == 2


def test_exit_status_indicator_theme1(tmp_path: Path) -> None:
    ok = _zsh(tmp_path, 'true; _nuxel_precmd; print -P -- "$PROMPT"', style="1", NUXEL_COLOR="1")
    bad = _zsh(tmp_path, 'false; _nuxel_precmd; print -P -- "$PROMPT"', style="1", NUXEL_COLOR="1")
    assert "\x1b[38;5;81m" in ok.stdout
    assert "\x1b[38;5;196m" in bad.stdout


def test_exit_status_indicators_other_themes(tmp_path: Path) -> None:
    ok2 = _zsh(tmp_path, 'true; _nuxel_precmd; print -P -- "$PROMPT"', style="2", NUXEL_COLOR="1")
    bad2 = _zsh(tmp_path, 'false; _nuxel_precmd; print -P -- "$PROMPT"', style="2", NUXEL_COLOR="1")
    assert "\x1b[38;5;81m" in ok2.stdout
    assert "\x1b[38;5;196m" in bad2.stdout
    ok3 = _zsh(tmp_path, 'true; _nuxel_precmd; print -P -- "$PROMPT"', style="3", NUXEL_COLOR="1")
    bad3 = _zsh(tmp_path, 'false; _nuxel_precmd; print -P -- "$PROMPT"', style="3", NUXEL_COLOR="1")
    assert "\x1b[48;5;45m" in ok3.stdout
    assert "\x1b[48;5;196m" in bad3.stdout
    ok4 = _zsh(tmp_path, 'true; _nuxel_precmd; print -P -- "$RPROMPT"', style="4", NUXEL_COLOR="1")
    bad4 = _zsh(tmp_path, 'false; _nuxel_precmd; print -P -- "$RPROMPT"', style="4", NUXEL_COLOR="1")
    assert "[OK]" in ok4.stdout
    assert "[ERR:1]" in bad4.stdout


def test_git_branch_and_non_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "a").write_text("a")
    subprocess.run(["git", "add", "a"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "-qb", "nuxel-test"], cwd=repo, check=True)
    out = _zsh(tmp_path, 'true; _nuxel_precmd; print -r -- "$NUXEL_GIT_BRANCH"', style="4", cwd=repo)
    assert out.stdout.strip() == "nuxel-test"
    nonrepo = tmp_path / "plain"
    nonrepo.mkdir()
    out = _zsh(tmp_path, 'true; _nuxel_precmd; print -r -- "X$NUXEL_GIT_BRANCH"', style="4", cwd=nonrepo)
    assert out.stdout.strip() == "X"


def test_color_disabled(tmp_path: Path) -> None:
    out = _zsh(tmp_path, 'print -r -- "$PROMPT"', style="1", NUXEL_COLOR="0")
    assert "%F{" not in out.stdout
    assert "%K{" not in out.stdout
    assert "%n@%m" in out.stdout


def test_non_interactive_has_no_banner(tmp_path: Path) -> None:
    out = _zsh(tmp_path, '_nuxel_precmd; print -r -- "done"')
    assert "Mobile Linux" not in out.stdout
    assert out.stdout.strip().endswith("done")


def _run_interactive(tmp_path: Path, **extra: str) -> str:
    """Run an interactive zsh on a real PTY and return the captured output."""
    import pty
    master, slave = pty.openpty()
    kwargs = {"NUXEL_BANNER": "1"}
    kwargs.update(extra)
    env = _env(tmp_path, "1", **kwargs)
    cmd = f"source {RUNTIME}; _nuxel_precmd; _nuxel_precmd; print -r -- BANNER_END"
    proc = subprocess.Popen([ZSH, "-f", "-i", "-c", cmd], stdin=slave, stdout=slave,
                            stderr=slave, env=env, close_fds=True)
    os.close(slave)
    chunks = []
    try:
        while True:
            try:
                data = os.read(master, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
            if b"BANNER_END" in b"".join(chunks):
                break
    finally:
        os.close(master)
        proc.wait(timeout=10)
    return b"".join(chunks).decode("utf-8", "replace")


def test_interactive_banner_once_and_suppression(tmp_path: Path) -> None:
    out = _run_interactive(tmp_path)
    assert out.count("Mobile Linux") == 1, out
    out = _run_interactive(tmp_path, NUXEL_BANNER="0")
    assert "Mobile Linux" not in out, out


def test_installer_idempotent_and_backs_up(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "etc").mkdir(parents=True)
    zshrc = root / "etc" / "zshrc"
    zshrc.write_text("# existing\n")
    env = dict(os.environ)
    env["PATH"] = os.environ.get("PATH", "") + ":/usr/bin:/bin"
    for _ in range(2):
        run = subprocess.run([shutil.which("sh"), str(INSTALLER), "--root", str(root),
                              "--no-package"], env=env, text=True, capture_output=True,
                             timeout=30)
        assert run.returncode == 0, run.stderr
    text = zshrc.read_text()
    assert text.count("# >>> nuxel-zsh >>>") == 1
    assert list((root / "etc").glob("zshrc.nuxel-rollback.*"))
    assert (root / "usr/lib/nuxel/zsh/nuxel.zsh").is_file()
    assert (root / "usr/local/bin/nuxel-theme").is_file()
    assert (root / "etc/nuxel/zsh.conf").is_file()
    assert (root / "etc/nuxel/banner").is_file()


def test_syntax_and_startup_performance(tmp_path: Path) -> None:
    syntax = subprocess.run([ZSH, "-n", str(RUNTIME)], text=True, capture_output=True)
    assert syntax.returncode == 0, syntax.stderr
    started = time.perf_counter()
    out = _zsh(tmp_path, 'print -r -- ok')
    elapsed = time.perf_counter() - started
    assert out.stdout.strip() == "ok"
    assert elapsed < 2.0, f"zsh startup too slow: {elapsed:.3f}s"
