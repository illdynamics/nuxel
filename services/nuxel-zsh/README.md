# Nuxel zsh — four prompt themes, banner, no framework

This is the Nuxel terminal shell integration required by `zsh.md`.  It is a
small, dependency-free zsh runtime (no Oh My Zsh, no Powerlevel10k) with four
selectable prompts, a persistent configuration, and the canonical Nuxel login
banner.

## Install

On the phone (as root):

```sh
sh services/nuxel-zsh/install-nuxel-zsh.sh
```

The installer:

* installs `zsh` through `dnf`/`apt`/`pacman`/`zypper` only when it is missing;
* installs `/usr/lib/nuxel/zsh/nuxel.zsh`, `/usr/local/bin/nuxel-theme`,
  `/etc/nuxel/zsh.conf`, `/etc/nuxel/banner`, and
  `/etc/profile.d/nuxel-banner.sh`;
* appends one marked block to `/etc/zshrc` (backing it up first);
* is idempotent — a second run does not duplicate the block or overwrite an
  existing system configuration.

It does **not** change any user's login shell unless asked:

```sh
sh install-nuxel-zsh.sh --set-shell nuxel
```

For staging/tests, use `--root DIR --no-package`.

## Themes

| # | Name | Notes |
|---|---|---|
| 1 | Clean Blue Gradient with Penguin | fresh-install default |
| 2 | Ice Diamond dual-line | error status on the right |
| 3 | Standard block segments | 256-colour blocks |
| 4 | Cyber / Nuxel tech with Git branch | cached Git lookup, detached-HEAD fallback |

```sh
nuxel-theme          # show the current theme and choices
nuxel-theme 1        # write ~/.config/nuxel/zsh.conf
nuxel-theme 2
nuxel-theme 3
nuxel-theme 4
nuxel-theme reset    # remove the user override (backup kept)
sudo nuxel-theme 2 --system
```

Changing a theme takes effect in the next shell.  `nuxel-theme` preserves
unrelated settings in the user file and writes a timestamped backup before
changing it.

## Configuration

System defaults: `/etc/nuxel/zsh.conf`
Per-user overrides: `~/.config/nuxel/zsh.conf`

```zsh
NUXEL_PROMPT_STYLE=1
NUXEL_BANNER=1
NUXEL_PROMPT_GIT=1
NUXEL_PROMPT_CLOCK=1
NUXEL_PENGUIN=1
NUXEL_COLOR=1
```

Precedence is system defaults, then the per-user file, then validation.  An
invalid `NUXEL_PROMPT_STYLE` falls back to `1`; invalid booleans fall back to
`1`.  `NUXEL_PENGUIN=0` switches to ASCII markers, and `NUXEL_COLOR=0` disables
all prompt colours (the prompt remains readable in a monochrome terminal).

## Banner

`/etc/nuxel/banner` is the canonical banner.  The runtime prints it once for an
interactive login shell on a real terminal.  It is suppressed for
non-interactive commands, pipes, SCP/SFTP, nested shells (`NUXEL_BANNER_SHOWN`),
and `NUXEL_BANNER=0`.  `/etc/issue`, `/etc/motd`, PAM and getty units are not
modified.

## Rollback

```sh
rm -f /usr/lib/nuxel/zsh/nuxel.zsh /usr/local/bin/nuxel-theme
rm -f /usr/lib/nuxel/zsh/nuxel-theme /usr/lib/nuxel/zsh/nuxel-banner
rm -f /etc/profile.d/nuxel-banner.sh
# restore the newest backup of /etc/zshrc if you want to remove the source block
ls -1 /etc/zshrc.nuxel-rollback.*
```

The per-user `~/.config/nuxel/zsh.conf` is never deleted by the installer.

## Tests

```sh
pytest -q tests/nuxel-zsh
```

The tests use temporary config files and a temporary `HOME`; they never modify
the developer's real `/etc` or default shell.
