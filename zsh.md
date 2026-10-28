# Nuxel — Configurable Zsh Themes, Penguin Banner & Console Welcome

Inspect the existing Nuxel repository and implement the complete Zsh installation, four configurable terminal prompt themes, and console login branding.

Do not just provide instructions: implement the feature, integrate it into the existing Nuxel architecture, test it, and report the results.

## 1. Four selectable prompt themes

Use the four prompt designs below as the canonical theme definitions. Preserve their appearance and color schemes, making only the corrections necessary for reliable Zsh syntax, correct exit-status handling, and safe prompt rendering.

**Default: Option 1 — Clean Blue Gradient with Penguin.**

### Option 1: Clean Blue Gradient with Penguin

```zsh
autoload -Uz colors && colors
setopt prompt_subst

# 256 colors: 117 Ice, 039 Capri, 033 Dodger,
# 081 Cyan, 196 Red Error
PROMPT='%F{117}🐧 %F{117}%n%f%F{039}@%F{033}%m%f %F{081}%~%f %F{081}%(?.%F{081}❯%F{045}❯%F{039}❯.%F{196}❯%F{160}❯%F{124}❯)%f '
RPROMPT='%F{242}%D{%H:%M:%S}%f'
```

### Option 2: Ice Diamond Dual-Line Prompt

```zsh
autoload -Uz colors && colors
setopt prompt_subst

PROMPT='%F{033}┌──[%F{117}🧊 %n%F{033}@%F{081}%m%F{033}]─[%F{255}%~%F{033}]
%F{033}└──%(?.%F{081}◆%f.%F{196}◆%f) '
RPROMPT='%F{039}%(?..[%?])%f'
```

### Option 3: Standard Block Segment

```zsh
autoload -Uz colors && colors
setopt prompt_subst

PROMPT='%K{019}%F{255} 🐧 %n %k%K{033}%F{255} %m %k%K{081}%F{016} %~ %k%(?.%K{045}%F{016}.%K{196}%F{255}) ❯ %k '
RPROMPT='%F{242}%T%f'
```

This theme should work with standard terminal fonts and 256-color support. If Unicode penguin rendering is unavailable, provide a configurable ASCII fallback.

### Option 4: Cyber / Nuxel Tech with Git Detection

```zsh
autoload -Uz colors && colors
setopt prompt_subst

git_branch_prompt() {
  local branch
  branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
  [[ -n "$branch" ]] && echo "%F{039}(%F{117} ${branch}%F{039})%f "
}

PROMPT='%F{081}⚡ %F{117}%n%F{039}@%F{033}%m %F{255}%~%f $(git_branch_prompt)%(?.%F{081}▶.%F{196}▶)%f '
RPROMPT='%F{039}%(?.%F{081}[OK].%F{196}[ERR:%?])%f'
```

Correct any malformed conditional prompt expressions and ensure Git branch rendering works reliably with `prompt_subst`. Prefer a detached-HEAD fallback where practical. Avoid running expensive Git commands on every prompt redraw.

## 2. Persistent configuration

Implement a simple, documented configuration system.

System defaults:

`/etc/nuxel/zsh.conf`

Per-user overrides:

`~/.config/nuxel/zsh.conf`

Example:

```zsh
# Nuxel terminal configuration
NUXEL_PROMPT_STYLE=1
NUXEL_BANNER=1
NUXEL_PROMPT_GIT=1
NUXEL_PROMPT_CLOCK=1
NUXEL_PENGUIN=1
NUXEL_COLOR=1
```

Requirements:

- Option 1 is the default on fresh installations.
- Accept prompt styles 1, 2, 3 and 4.
- Validate configuration values and fall back safely to defaults.
- Per-user settings override system defaults.
- Changing a setting takes effect on the next shell startup.
- Never overwrite an existing user configuration without backing it up.
- Provide a documented method to change the theme without manually editing configuration files.
- Allow colors, banner, penguin, Git information and clock display to be configured independently wherever applicable.
- Do not require Oh My Zsh, Powerlevel10k, external downloads or a large framework.

Provide an easy theme-selection command, preferably:

```bash
nuxel-theme
nuxel-theme 1
nuxel-theme 2
nuxel-theme 3
nuxel-theme 4
```

Running `nuxel-theme` without arguments should display the available themes and the current selection. If the repository has an existing CLI architecture, integrate the command with it.

## 3. Preserve the Nuxel banner

Install the canonical banner at `/etc/banner` and keep its source template in the repository.

```text
      .--.       _   _ _   ___  _____ _
     |o_o |      | \ | | | / _ \| ____| |
     |:_/ |      |  \| | | | | | |  _| | |
    //   \ \     | |\  | |_| |_| | |___| |___
   (|     | )    |_| \_|\___\___/|_____|_____|
  /'\_   _/`\
  \___)=(___/

                  Mobile Linux for Control Freaks
```

Preserve the intended spacing and alignment. Use a Doom-style NUXEL wordmark if a suitable ASCII version is available.

Integrate the banner with the actual Nuxel console login stack after inspecting the current rootfs and login configuration.

Requirements:

- Show the banner at interactive console login.
- Handle SSH login without unwanted duplication.
- Never print it for non-interactive commands, SCP/SFTP or automation.
- Avoid printing it repeatedly in nested shells.
- Respect `NUXEL_BANNER=0`.
- Do not blindly overwrite `/etc/issue`, `/etc/motd`, PAM configuration, getty units or existing login hooks.
- Ensure the banner works without Unicode block graphics or special fonts.

## 4. Zsh installation and startup

Implement an idempotent installer using existing Nuxel project conventions.

- Detect the available package manager and install Zsh only when needed.
- Configure root and regular users appropriately.
- Offer an explicit option to change the default shell.
- Preserve Bash and recovery access.
- Back up modified files.
- Respect existing shell configuration.
- Keep startup fast and avoid unnecessary subprocesses.
- Support fresh installations and already-running Nuxel environments.
- Avoid changing the default shell for every system account automatically.

Ensure Zsh is configured to load the system configuration first and then the user's overrides, with a clear, predictable precedence.

## 5. Prompt correctness and terminal compatibility

Test all four themes in real Zsh rather than assuming that Bash-compatible syntax is sufficient.

In particular:

- Preserve the previous command's exit status before executing prompt hooks or helper functions.
- Ensure Option 1's three-arrow indicator changes to the red error indicator after a failed command.
- Ensure Option 2 displays the correct success/error diamond and error status when applicable.
- Ensure Option 3 renders its background-color segments correctly.
- Ensure Option 4 displays the Git branch, including safe handling of detached HEAD.
- Ensure right-hand prompts do not overlap input or break terminal redraws.
- Wrap non-printing terminal escape sequences correctly when custom ANSI escapes are used.
- Handle missing Git, unsupported colors, non-TTY environments and narrow terminals gracefully.
- Preserve the original themes' intended appearance.

## 6. Testing and completion

Inspect the existing codebase, rootfs, package conventions and tests before implementing changes.

Add tests for:

1. Default theme selection.
2. All four themes and their configuration.
3. Per-user override precedence.
4. Invalid configuration fallback.
5. Persistence across new shells.
6. Installer idempotency and backup behavior.
7. Correct exit-status indicators.
8. Git branch detection and non-Git directories.
9. Banner login behavior and suppression.
10. Color-disabled and non-interactive environments.
11. Zsh syntax validation and startup performance.

Use temporary test fixtures rather than modifying the developer's actual `/etc` or default shell during unit tests.

Update the documentation with installation, theme selection, configuration options, troubleshooting and rollback instructions.

Finally, run the relevant tests, inspect the diff and report the files changed, test results, installation command, and how to switch between all four themes.

**Acceptance criterion:** Nuxel boots and logs in with the existing penguin banner, starts Zsh with Option 1 by default, and allows users to switch between all four themes persistently without manually editing `.zshrc`.
