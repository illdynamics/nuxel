"""A minimal stand-in for pygame, enough to IMPORT the original SnekByte modules.

The upstream sources import pygame at module scope (src/config.py, src/snake.py,
src/food.py, src/poop.py) purely for drawing.  The game RULES do not touch it, so
the parity harness needs the import to succeed and nothing more.  This stub is
deliberately tiny and does NOT pretend to render: every drawing call is a no-op
that raises if a test ever tries to assert on pixels — rendering parity is not
claimed anywhere in this port.

It is only ever used by tools/s10plus/a33/snekbyte/{gen-parity-fixtures.py,
tests/test-snek-parity.py}; the shipped PWA never imports Python.
"""
import sys
import types


def _noop(*a, **k):
    return None


class Rect(object):
    def __init__(self, *args, **kw):
        # pygame.Rect accepts both Rect((x, y), (w, h)) and Rect(x, y, w, h).
        if len(args) == 4:
            self.x, self.y, self.w, self.h = args
        elif len(args) == 2:
            (self.x, self.y), (self.w, self.h) = args
        else:
            self.x = kw.get("x", 0)
            self.y = kw.get("y", 0)
            self.w = kw.get("w", kw.get("width", 0))
            self.h = kw.get("h", kw.get("height", 0))
        self.topleft = (self.x, self.y)
        self.center = (self.x + self.w / 2.0, self.y + self.h / 2.0)

    def __eq__(self, other):
        return (isinstance(other, Rect) and (self.x, self.y, self.w, self.h) ==
                (other.x, other.y, other.w, other.h))

    def __repr__(self):
        return "Rect(%r, %r, %r, %r)" % (self.x, self.y, self.w, self.h)


class Event(object):
    """Minimal pygame.event.Event for the upstream unit tests."""
    def __init__(self, type, **kw):
        self.type = type
        for k, v in kw.items():
            setattr(self, k, v)


class Surface(object):
    def __init__(self, size=(0, 0)):
        self.size = size

    def fill(self, *a, **k):
        return None

    def blit(self, *a, **k):
        return None


class _Font(object):
    def __init__(self, *a, **k):
        pass

    def render(self, text, *a, **k):
        return Surface((len(str(text)) * 8, 16))

    def get_rect(self, **k):
        return Rect((0, 0), (10, 10))


def _draw_rect(*a, **k):
    return None


def install():
    """Install the stub into sys.modules if the real pygame is absent."""
    try:
        import pygame  # noqa: F401
        return False
    except Exception:
        pass
    m = types.ModuleType("pygame")
    m.init = _noop
    m.quit = _noop
    m.display = types.SimpleNamespace(set_mode=lambda *a, **k: Surface(a[0] if a else (0, 0)),
                                      set_caption=_noop, flip=_noop, update=_noop)
    m.draw = types.SimpleNamespace(rect=_draw_rect, line=_noop)
    m.font = types.SimpleNamespace(Font=_Font, get_default_font=lambda: "stub",
                                   init=_noop, SysFont=lambda *a, **k: _Font())
    m.time = types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda *a, **k: 0))
    m.event = types.SimpleNamespace(get=lambda *a, **k: [], Event=Event)
    m.Rect = Rect
    m.Surface = Surface
    m.QUIT = 256
    m.KEYDOWN = 768
    m.K_UP, m.K_DOWN, m.K_LEFT, m.K_RIGHT = 273, 274, 276, 275
    m.K_RETURN, m.K_ESCAPE, m.K_q, m.K_a = 13, 27, 113, 97
    m.locals = types.SimpleNamespace(**{k: getattr(m, k) for k in dir(m) if k.startswith("K_")})
    sys.modules["pygame"] = m
    sys.modules["pygame.locals"] = m.locals
    return True
