# Nuxel zsh runtime — configurable prompt, banner, no framework.
# Sourced from /etc/zshrc by install-nuxel-zsh.sh.  Safe to source from any
# interactive zsh; non-interactive shells get the config but no banner.

autoload -Uz colors 2>/dev/null && colors
setopt prompt_subst 2>/dev/null || true

: ${NUXEL_ZSH_SYSTEM_CONF:=/etc/nuxel/zsh.conf}
: ${NUXEL_ZSH_USER_CONF:=${XDG_CONFIG_HOME:-$HOME/.config}/nuxel/zsh.conf}
: ${NUXEL_BANNER_FILE:=/etc/nuxel/banner}

# Defaults (Option 1 is the fresh-install default).
: ${NUXEL_PROMPT_STYLE:=1}
: ${NUXEL_BANNER:=1}
: ${NUXEL_PROMPT_GIT:=1}
: ${NUXEL_PROMPT_CLOCK:=1}
: ${NUXEL_PENGUIN:=1}
: ${NUXEL_COLOR:=1}

_nuxel_bool() {
    case ${1:-} in 0|1) return 0 ;; *) return 1 ;; esac
}

# Source system defaults first, then the per-user override.  Values are
# validated after both files have been read, so an invalid user value falls
# back to the documented default instead of breaking the prompt.
_nuxel_read_conf() {
    local file=$1
    [[ -r $file ]] || return 0
    # Config files are trusted user-owned policy.  Errors are contained so a
    # broken file cannot make a shell unusable.
    source "$file" 2>/dev/null || true
}
_nuxel_read_conf "$NUXEL_ZSH_SYSTEM_CONF"
_nuxel_read_conf "$NUXEL_ZSH_USER_CONF"

case ${NUXEL_PROMPT_STYLE:-} in 1|2|3|4) ;; *) NUXEL_PROMPT_STYLE=1 ;; esac
for _nuxel_v in NUXEL_BANNER NUXEL_PROMPT_GIT NUXEL_PROMPT_CLOCK NUXEL_PENGUIN NUXEL_COLOR; do
    eval "_nuxel_val=\${$_nuxel_v:-1}"
    _nuxel_bool "$_nuxel_val" || eval "$_nuxel_v=1"
done
unset _nuxel_v _nuxel_val

NUXEL_LAST_STATUS=${NUXEL_LAST_STATUS:-0}
NUXEL_GIT_BRANCH=${NUXEL_GIT_BRANCH:-}
NUXEL_GIT_CACHE_AT=0

# Git is evaluated once per prompt at most, and only every 2 s.  A detached
# HEAD is shown explicitly instead of producing an empty segment.
_nuxel_update_git() {
    (( NUXEL_PROMPT_GIT )) || { NUXEL_GIT_BRANCH=; return 0; }
    local now=${EPOCHSECONDS:-$(date +%s)}
    (( now - NUXEL_GIT_CACHE_AT < 2 )) && return 0
    NUXEL_GIT_CACHE_AT=$now
    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        local branch
        branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
        if [[ -z $branch ]]; then
            branch="detached@$(git rev-parse --short HEAD 2>/dev/null || print -n '?')"
        fi
        NUXEL_GIT_BRANCH=$branch
    else
        NUXEL_GIT_BRANCH=
    fi
}

nuxel_git_segment() {
    (( NUXEL_PROMPT_GIT )) || return 0
    [[ -n $NUXEL_GIT_BRANCH ]] || return 0
    if (( NUXEL_COLOR )); then
        print -n "%F{039}(%F{117} ${NUXEL_GIT_BRANCH}%F{039})%f "
    else
        print -n "(${NUXEL_GIT_BRANCH}) "
    fi
}

_nuxel_banner_once() {
    (( NUXEL_BANNER )) || return 0
    [[ -o interactive ]] || return 0
    [[ -t 1 ]] || return 0
    [[ -n ${NUXEL_BANNER_SHOWN:-} ]] && return 0
    [[ -n ${NUXEL_BANNER_PRINTED:-} ]] && return 0
    NUXEL_BANNER_PRINTED=1
    export NUXEL_BANNER_SHOWN=1
    local b=${NUXEL_BANNER_FILE:-/etc/nuxel/banner}
    if [[ ! -r $b ]]; then
        b=${(%):-%x}; b=${b:A:h}/nuxel-banner
    fi
    [[ -r $b ]] && cat "$b"
    return 0
}

_nuxel_precmd() {
    local st=$?
    NUXEL_LAST_STATUS=$st
    _nuxel_update_git
    _nuxel_banner_once
    # Returning the previous status preserves %(?.…) in every theme even
    # though precmd itself ran successfully.
    return $st
}

autoload -Uz add-zsh-hook 2>/dev/null && add-zsh-hook precmd _nuxel_precmd

# ── Theme definitions ────────────────────────────────────────────────────
# ASCII fallbacks are used when NUXEL_PENGUIN=0; the layout is otherwise
# unchanged.  Color is removed centrally below when NUXEL_COLOR=0.
if (( NUXEL_PENGUIN )); then
    _nuxel_penguin='🐧'
    _nuxel_ice='🧊'
    _nuxel_bolt='⚡'
else
    _nuxel_penguin='>_'
    _nuxel_ice='[]'
    _nuxel_bolt='>>'
fi

case $NUXEL_PROMPT_STYLE in
1)
    PROMPT="%F{117}${_nuxel_penguin} %F{117}%n%f%F{039}@%F{033}%m%f %F{081}%~%f %F{081}%(?.%F{081}❯%F{045}❯%F{039}❯.%F{196}❯%F{160}❯%F{124}❯)%f "
    (( NUXEL_PROMPT_CLOCK )) && RPROMPT='%F{242}%D{%H:%M:%S}%f' || RPROMPT=''
    ;;
2)
    PROMPT="%F{033}┌──[%F{117}${_nuxel_ice} %n%F{033}@%F{081}%m%F{033}]─[%F{255}%~%F{033}]"$'\n'"%F{033}└──%(?.%F{081}◆%f.%F{196}◆%f) "
    if (( NUXEL_PROMPT_CLOCK )); then
        RPROMPT='%F{039}%(?..[%?]) %F{242}%D{%H:%M:%S}%f'
    else
        RPROMPT='%F{039}%(?..[%?])%f'
    fi
    ;;
3)
    PROMPT="%K{019}%F{255} ${_nuxel_penguin} %n %k%K{033}%F{255} %m %k%K{081}%F{016} %~ %k%(?.%K{045}%F{016}.%K{196}%F{255}) ❯ %k "
    (( NUXEL_PROMPT_CLOCK )) && RPROMPT='%F{242}%T%f' || RPROMPT=''
    ;;
4)
    PROMPT="%F{081}${_nuxel_bolt} %F{117}%n%F{039}@%F{033}%m %F{255}%~%f \$(nuxel_git_segment)%(?.%F{081}▶.%F{196}▶)%f "
    if (( NUXEL_PROMPT_CLOCK )); then
        RPROMPT='%F{039}%(?.%F{081}[OK] %F{242}%D{%H:%M:%S}.%F{196}[ERR:%?])%f'
    else
        RPROMPT='%F{039}%(?.%F{081}[OK].%F{196}[ERR:%?])%f'
    fi
    ;;
esac
unset _nuxel_penguin _nuxel_ice _nuxel_bolt

if (( ! NUXEL_COLOR )); then
    PROMPT='%n@%m %~ %# '
    RPROMPT=''
fi
