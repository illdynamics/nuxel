#!/usr/bin/env python3
"""SonarBird Tier 0 deterministic routing rules.

High-precision only.  A rule may *suggest* CHAT/CODE/SYSTEM; any conflict,
mixed intent, untrusted context or quoted command abstains (ASK).  SYSTEM is
never an authorization: the Supervisor resolves a typed, allowlisted read and
this module's output cannot grant anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

LABELS = ("CHAT", "CODE", "SYSTEM", "ASK")

SYSTEM_VERBS = r"(?:what(?:'s| is)|show|tell me|check|how much|how many|is)"
SYSTEM_TARGETS = (
    r"battery|wifi|wi-fi|bluetooth|volume|storage|disk space|free memory|"
    r"memory usage|thermal|temperature|uptime|kernel version|device model|"
    r"network status|ip address|charging"
)
SYSTEM_READ = re.compile(
    r"^\s*" + SYSTEM_VERBS + r"(?:\s+\w+){0,3}?\s+(" + SYSTEM_TARGETS + r")\b",
    re.IGNORECASE)

CODE_SIGNALS = [
    re.compile(r"```"),
    re.compile(r"^\s*(?:Traceback \(most recent call last\)|"
               r'File "[^"]+", line \d+)', re.MULTILINE),
    re.compile(r"\b(?:error|exception)\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"\.(?:py|rs|c|h|cpp|js|ts|java|kt|sh|service|json|toml|"
               r"yaml|yml|css|html)\b", re.IGNORECASE),
    re.compile(r"\b(?:def|class|fn|impl|#include)\s+\w+"),
    re.compile(r"\b(?:compiler error|stack trace|segfault|unit test|pytest|"
               r"cmake|git diff|refactor|patch this|debug this)\b", re.IGNORECASE),
    re.compile(r"\bwrite (?:me )?(?:a |an )?(?:script|function|program|"
               r"extension|patch|test)\b", re.IGNORECASE),
    re.compile(r"\bfix (?:this|the) (?:code|bug|error|traceback|test|build)\b",
               re.IGNORECASE),
]

CHAT_SIGNALS = [
    re.compile(r"^\s*(?:hi|hello|hey|thanks|thank you|good (?:morning|evening))\b",
               re.IGNORECASE),
    re.compile(r"\b(?:explain|summari[sz]e|brainstorm|imagine|write (?:a )?(?:story|poem)|"
               r"what do you think|why do|compare)\b", re.IGNORECASE),
]

# A quoted span is data (a command, log line or document fragment).  It may
# route to CODE if it is code, but it can never be interpreted as a system
# operation, and instruction-like text always abstains.
# Inline single-backtick text is a quoted command/log fragment: data, never a
# system instruction.  Fenced (triple) backticks are code and are handled by
# CODE_SIGNALS before this masking is applied.
QUOTED = re.compile(r"(?:`[^`\n]*`|\"[^\"]{3,}\"|'[^']{3,}')")
UNTRUSTED_CONTEXT = re.compile(
    r"(?:ignore (?:all |the )?(?:previous|above) instructions|"
    r"system prompt|developer message|"
    r"<\s*/?\s*(?:system|assistant|tool)\s*>)",
    re.IGNORECASE)

# Explicit write/change vocabulary.  Never SYSTEM in v1.
# Shell/command fragments inside quoted spans are data, but a request that
# carries them does not get a SYSTEM dispatch: too easy to smuggle an action.
QUOTED_COMMAND = re.compile(
    r"\b(?:sudo|systemctl|reboot|poweroff|shutdown|rm|mkfs|dd|mount|"
    r"chmod|chown|iptables|nft|nmcli|bash|sh|python|curl|wget)\b|(?:^|\s)[\w./-]+\s+-[a-z]",
    re.IGNORECASE)

WRITE_SIGNAL = re.compile(
    r"\b(?:reboot|restart|shutdown|power off|format|wipe|flash|install|"
    r"uninstall|change|set|enable|disable|turn on|turn off|connect to|"
    r"disconnect|sudo|chmod|chown|delete|remove files)\b", re.IGNORECASE)


@dataclass
class RuleDecision:
    label: Optional[str]
    reason: str
    rule_id: str
    system_target: Optional[str] = None

    def as_dict(self):
        return {"label": self.label, "reason": self.reason,
                "rule_id": self.rule_id, "system_target": self.system_target}


def _unquoted(text: str) -> str:
    return QUOTED.sub(" ", text)


def route_rules(text: str) -> RuleDecision:
    if not isinstance(text, str) or not text.strip():
        return RuleDecision(None, "empty request", "R_EMPTY")
    t = text.strip()
    if len(t) > 16000:
        return RuleDecision("ASK", "request exceeds the text limit", "R_TOO_LONG")
    if UNTRUSTED_CONTEXT.search(t):
        return RuleDecision("ASK", "untrusted instruction-like context",
                            "R_UNTRUSTED_CONTEXT")

    bare = _unquoted(t)
    quoted_cmd = bare != t and bool(QUOTED_COMMAND.search(t))
    read = SYSTEM_READ.match(bare)
    write = bool(WRITE_SIGNAL.search(bare))
    code = any(r.search(t) for r in CODE_SIGNALS)

    if read and quoted_cmd:
        return RuleDecision("ASK", "system read combined with a quoted command",
                            "R_QUOTED_COMMAND")
    if read and (code or write):
        return RuleDecision("ASK", "mixed system operation and code/change request",
                            "R_MIXED_SYSTEM")
    if write:
        return RuleDecision("ASK", "system changes require an explicit typed action",
                            "R_WRITE_NEEDS_TYPED_ACTION")
    if code:
        return RuleDecision("CODE", "code, error or extension signal", "R_CODE_SIGNAL")
    if read:
        return RuleDecision("SYSTEM", "explicit supported system read",
                            "R_SYSTEM_READ", read.group(1).lower())
    if any(r.search(t) for r in CHAT_SIGNALS) and len(t) <= 2000:
        return RuleDecision("CHAT", "high-precision chat cue", "R_CHAT_CUE")
    return RuleDecision(None, "no high-precision rule matched", "R_UNDECIDED")
