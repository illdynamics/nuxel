# SnekByte deployment and rollback

No game payload changed because the latest ZIP was absent. The existing live game already matched the repository.

Launcher integration changed atomically: canonical ID `org.nuxel.SnekByte`, icon mapping and stored-recents migration. Live `apps.js` SHA-256 is `d68efd0f8b3505a68646575f15daaf3d62842d75fe58b50a3e8752a65e198570`; HTTP for the game and icon returned 200.

Rollback source is the private pre-change archive plus `/usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-a63-rollback`. Restore that single file, verify its hash, then reload Home on the next normal session start. Do not delete the live game or its old staging directories until the owner archive has been safely merged.
