Context: We're running the Teams Flatpak (Electron) on Nuxel mobile Linux. We already bypassed the Linux platform block with a Windows/Chromium spoof (emulateWindowsChromium: true, custom UA, /etc/os-release override). The sign-in flow now reaches "Sign in with your work account — switch Edge profile", which is a Conditional Access policy requiring Microsoft Edge. The Electron app is still being detected as not Edge.

Goal: Get past the "switch Edge profile" screen without requiring a real Edge installation (though using Edge/Chromium as an auth broker is acceptable as a fallback).

Investigate and implement one or more of these approaches (in order of preference):

Deepen the Edge spoof inside the Teams Electron app.

The app already uses Teams' own emulatePlatform.js. Check whether that script can be patched or whether the edgeUserAgent config option in teams-for-linux (if applicable to this build) can be set to a full Edge UA string (e.g. ...Edg/152.0.7977.167 — not just "Chrome").

Check for any Edge-specific headers or client hints (Sec-CH-UA, Sec-CH-UA-Platform) that the conditional access policy may be inspecting, and spoof those via the preload script.

If Teams ships an internal emulateEdge flag or similar, try enabling it.

Use a real browser as the auth broker.

The teams-cli project (pypi) documents a backend that can use an installed Chrome, Chromium, or Edge browser instead of the native Teams app for sign-in, then hand the session back to the app. See if a similar browser-broker flow can be wired into the bridge: launch a dedicated Edge/Chromium profile for the Microsoft login, capture the authenticated session/cookies, and inject them into the Teams Flatpak.

If Microsoft Edge Flatpak is available on the device, use it only for the sign-in step, then export the session.

Satisfy Conditional Access via Microsoft single sign-on for Linux.

Microsoft provides microsoft-identity-broker for Linux, which is designed to satisfy device-based Conditional Access policies for Teams PWA using Edge. Check whether this can be installed on Nuxel and whether it changes the detection from "not Edge" to "compliant Edge".

Constraints:

Do not break the existing Windows spoof that got us past Error 53003.

The Flatpak bwrap sandbox must remain authoritative.

If a real Edge binary is required, find a way to install or bundle it without blowing the phone's storage/RAM budget.

Deliverable: A working end-to-end Teams login that reaches the chat UI, plus a brief note on which approach worked and what files/config were changed.
