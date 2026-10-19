# Application lifecycle

Nuxel Home now records CLOSED, LAUNCHING, ACTIVE, BACKGROUND, CLOSING and FAILED.
Opening first removes the prior frame/status/close surface. Load and failure are
visible, Home/close use one cleanup path, focus is blurred, and visibility drives
ACTIVE/BACKGROUND. Native Terminal becomes ACTIVE only after an `{ok:true}` host
reply; refusal or timeout becomes FAILED.
