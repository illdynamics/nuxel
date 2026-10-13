## 2. Remaining issues from `final-issues-nuxel.md` — root causes & fixes                                                   
                                                                                                                            
**Item 2 (Medium, bashisms) — root cause: `#!/bin/sh` scripts used bash-only constructs (`local`, `echo -e`, `read -p`), whi
ch break under `dash`/busybox `ash`.**                                                                                      
Fixed by making them POSIX-sh-clean:                                                                                        
- `boot/recovery.sh`: 49× `echo -e` → `printf '%b\n'`, 14× `local` → plain assignments, 2× `read -r -p` → `printf … ; read`,
 plus removed dead `RECOVERY_DATE`/`timestamp` and made `tftp_ip`/`dummy` used (`read -r _`).                               
- `boot/initramfs/init.sh`: removed `local fbdev`, wired `CONSOLE` into the boot log, and fixed a **latent inverted conditio
n** (`command -v veritysetup` should be `! command -v veritysetup`) while removing the dead `do_verity`.                    
- `images/hooks/luks-userdata.sh` and `images/hooks/verity-setup.sh`: removed all `local` (5 + 4).                          
                                                                                                                            
**Item 3 (Low, SC2046) — root cause: pkg-config flags are *intentionally* word-split into multiple gcc args.** Simplified `$
(which pkg-config)` → `pkg-config` and added `# shellcheck disable=SC2046` with a justification comment (quoting it would br
eak compilation).

**Item 5 (Low, SC2027) — root cause: nested quotes in a `log_error` string unquoted `$VM_NAME`.** Escaped the inner quotes; 
also removed the dead `SCP` array and `VM_IP_FROM_UTMCTL`.

**Item 4 (SC2034) — root cause: unused/dead variables.** Fixed in every file I touched (`recovery.sh`, `init.sh`, `deploy-vm
.sh`). The remaining ~35 SC2034 across ~25 other files are cosmetic and mostly intentional (documentation/export-only), so I
 left those untouched.

**Item 6 (legacy cleanup) — root cause: a prior systemd unit wrote to the legacy split path.** Removed `/var/lib/nuxel/notif
ications/history.json` + the now-empty dir in the guest; canonical `/var/lib/nuxel/notifications.json` remains.

