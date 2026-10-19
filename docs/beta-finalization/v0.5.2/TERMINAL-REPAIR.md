# Terminal repair

The A34 `term_close_window()` fix remains in the native host and is used by
`term.close`, `close-terminal`, and Home. v0.5.2 also fixes OSK history dispatch,
tracked-line Backspace, Shift, symbols, and keyboard dismissal/restore. Terminal
still uses the real forkpty backend; no simulated shell was added.
