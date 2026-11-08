# Animation Profile — PWNAGE-85000

## Tokens

| Token | Value | Use |
|---|---:|---|
| `--nx-motion-press` | 90 ms | button/app press |
| `--nx-motion-fast` | 140 ms | status/nav chrome, small menus |
| `--nx-motion-standard` | 180 ms | Quick Settings/panel entry |
| `--nx-motion-navigation` | 200 ms | app grid page slide |
| `--nx-motion-emphasis` | 230 ms | rare emphasis only |
| reduced | 70/90/100/110/120 ms | essential feedback |
| off | 0 ms | near-instant |

Easing: `cubic-bezier(.2,.8,.2,1)` standard; `cubic-bezier(.4,0,1,1)` exit.

## Applied

- App-item press: scale 0.94 over 90 ms (was 0.88 with `--transition-fast`).
- `.nx-btn` press: scale 0.98 over 90 ms.
- Quick Settings entry: token-driven opacity/translateY.
- Status bar / system navigation hide-show: token-driven transform/opacity.
- App grid page slide: 200 ms token.
- Lockscreen wiggle remains one-shot; reduced/off disables it.
- Display-off pauses all animations/transitions and hides large Home layers.

## Explicitly avoided

No `backdrop-filter`, animated blur, large shadows, layout animation, permanent `will-change`, spring loops, full-screen animated layers, or continuous decorative motion. Transforms are not claimed GPU-accelerated; the software compositor cost was measured rather than assumed.

## Tests

`tests/pwnage85000/test_motion_contract.py` — 7 passed:
- token upper bounds
- reduced/off paths
- core rules use tokens
- no layout animation in core rules
- no backdrop blur
- restrained press scale
- persisted/shared motion preference

Visual smoothness and touch acceptance remain **NEEDS_OWNER_TEST**.
