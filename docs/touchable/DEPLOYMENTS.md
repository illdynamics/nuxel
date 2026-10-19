# Deployments and rollback

`tools/touchable/deploy-pwa.py` stages one reviewed PWA bundle, verifies every
hash, saves originals, atomically replaces files, and restarts nuxel-wayland
once. Readiness/service failure rolls back the whole group. Each deployment has
a unique `/var/tmp/nuxel-<label>/backup/` directory and receipt.

First bundle: `evidence/deploy-taps-20261018/plan.json` (nine PWA assets).
Staging exposed a pre-existing `nuxel_live.push_bytes` retry bug: after a lost
decode receipt, the retry deleted the source parts and truncated install.py.
The hash gate stopped before target mutation. New transfer code keeps parts until
verified readback and uses content-addressed part names. An executable lost-receipt
test verifies the destination remains correct.

The installer then correctly refused an unanticipated path: this phone serves
`pwa/nuxel-home -> ../nuxel-home`. That exact measured userspace root is now allowed.
No target was changed by that refusal. Original staging/guard evidence is retained.
The staged bundle is reused; final deployment status belongs to receipt.json.
