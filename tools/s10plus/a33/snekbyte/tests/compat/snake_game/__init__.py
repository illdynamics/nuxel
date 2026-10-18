"""Compatibility package for the vendored upstream tests.

The upstream tests in ../upstream/tests import `snake_game.*`, an older module
layout.  The imported game itself ships as `src.*`.  This package is a thin
test-only adapter; it contains no game rules and is never shipped in the PWA.
"""
