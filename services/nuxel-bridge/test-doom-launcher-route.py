#!/usr/bin/env python3
"""Crispy Doom launch route: Home must open the Nuxel touch launcher.

The installed Flathub app id stays authoritative, but a bare `flatpak run`
drops the game into a small desktop window on the S10+.  The bridge therefore
resolves this one app id to the Nuxel wrapper, which opens the GTK4 WAD picker
when called without game switches and execs the real Crispy Doom binary when a
switch is supplied.

No Flatpak, D-Bus, display or handset is touched: `is_installed` is stubbed.
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(HERE, "src", "flatpak_provider.py")
WRAPPER = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-flatpak-doom")
LAUNCHER = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-doom-launcher")

FAILS = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def load_provider():
    spec = importlib.util.spec_from_file_location("nuxel_flatpak_provider_route", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main() -> int:
    mod = load_provider()
    provider = mod.FlatpakProvider.__new__(mod.FlatpakProvider)
    installed = {mod.CRISPY_DOOM_APP_ID, "org.gnome.TextEditor"}
    provider.is_installed = lambda app_id: app_id in installed

    argv = provider.launch_argv("io.github.fabiangreffrath.Doom")
    check(argv == [mod.CRISPY_DOOM_WRAPPER],
          "Crispy Doom resolves to the Nuxel wrapper, not raw flatpak run (%r)" % (argv,))
    check(mod.CRISPY_DOOM_WRAPPER == "/usr/lib/nuxel/nuxel-flatpak-doom",
          "the wrapper path is the installed absolute path")

    other = provider.launch_argv("org.gnome.TextEditor")
    check(other and other[0] == mod.FLATPAK and other[-1] == "org.gnome.TextEditor",
          "other Flatpaks keep the generic software-rendering launch (%r)" % (other,))
    check(other and "--env=GSK_RENDERER=cairo" in other,
          "other Flatpaks still force the cairo software path")

    check(provider.launch_argv("io.github.fabiangreffrath.Doom;sh") is None,
          "path/shell-shaped ids are refused")
    check(provider.launch_argv("org.example.NotInstalled") is None,
          "an uninstalled id is refused")

    wrapper = open(WRAPPER, encoding="utf-8").read()
    check("exec /usr/lib/nuxel/nuxel-doom-launcher" in wrapper,
          "the wrapper opens the touch launcher on a bare invocation")
    check("exec /usr/lib/nuxel/nuxel-crispy-doom" in wrapper,
          "the wrapper still reaches Crispy Doom for game switches")
    check(os.path.isfile(LAUNCHER),
          "the GTK launcher source is present alongside the wrapper")

    print("\n%d failure(s)" % len(FAILS))
    return len(FAILS)


if __name__ == "__main__":
    raise SystemExit(main())
