# A63 source versus live drift

Pre-change inspection found the deployed SnekByte PWA byte-identical to the repository. Drift existed in Home integration:

- launcher ID was `org.nuxel.Snekbyte`, while the app/manifest canonical ID is `org.nuxel.SnekByte`;
- SnekByte used an emoji instead of the supplied icon pack asset;
- bridge startup fallback fabricated `100%` and charging;
- the service worker precached two nonexistent launcher files;
- `nuxel-web.service` referenced a nonexistent VM mirror and its unprivileged user lacked the S10+ kernel's required AID_INET group.

Live deployed hashes after repair:

| File | SHA-256 |
|---|---|
| `pwa/nuxel-home/index.html` | `a927dbcea10b98e5699e8530d08708504c8429838c00f32c8fb71213b5af7724` |
| `pwa/nuxel-home/manifest.json` | `46695729bb31e68df60f1a820aaf4aeb88bc03fcbf201421c8a51a9d49431f31` |
| `pwa/nuxel-home/sw.js` | `7dc8d7553857a868303d34c03d4df49b7347dfa7a3cf4a938b720d14df9fc713` |
| `js/status-bar.js` | `5148a909c318619d12a16dd2567dfa50460e235fab9bf2e4b0cfefc6e7ccab37` |
| `js/bridge.js` | `bbfc2823118c6f83e99549c348347fd17da20e60fb317de6962c1b0ab513497b` |
| `js/apps.js` | `d68efd0f8b3505a68646575f15daaf3d62842d75fe58b50a3e8752a65e198570` |

All six HTTP paths checked returned 200. The canonical common/native registry still predates several A59 launcher additions; that broader registry convergence is recorded as remaining work rather than silently declared fixed.
