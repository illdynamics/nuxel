# pwnage-95000.md
# NUXEL PWNAGE-95000 — MASTER LIVE DEPLOYMENT AUDIT KICKSTARTER

**Mission:** Execute `full-pwnage-95000.md` completely.

**Objective:** Determine whether every historical Nuxel `pwnage-#####.md` and `full-pwnage-#####.md` task has actually been implemented and deployed to the live Samsung Galaxy S10+ installation.

We have completed many development tasks, but it is currently unclear which changes actually made it onto the phone. Establish the facts.

## 1. Mandatory instructions

1. Read `full-pwnage-95000.md` completely.
2. Locate every historical PWNAGE Kickstarter and full specification.
3. Inspect the entire repository and Git history.
4. Find and inspect the existing deployment scripts in `./scripts`.
5. Use the existing deployment infrastructure to establish what is installed on the phone.
6. Compare repository state, built artifacts, deployment records, and live device state.
7. Produce a complete historical deployment audit.
8. Do not assume that a task is deployed just because its code exists.
9. Do not blindly redeploy everything.
10. Do not modify or overwrite working functionality during the audit.

## 2. SSH access

Use this exact SSH command for the target device:

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

Use this as the primary SSH connection method.

Before performing operations:

- Verify the SSH host identity using the existing known-hosts configuration.
- Verify that the connected device is the intended Samsung Galaxy S10+.
- Verify the Nuxel installation and active build/version.
- Confirm the effective user and permissions.
- Check that the device is reachable before attempting deployment operations.

Do not disable SSH host-key verification. Do not use `StrictHostKeyChecking=no`.

If the connection fails, diagnose the failure and report it. Do not silently substitute another IP address or device.

## 3. Deployment scripts

**The existing deployment scripts are in `./scripts`.**

Inspect them thoroughly.

Identify:

- Which scripts deploy the complete OS.
- Which scripts deploy individual subsystems.
- Which scripts build artifacts.
- Which scripts install or update services.
- Which scripts restart services.
- Which scripts verify deployments.
- Which scripts perform device diagnostics.
- Which scripts support rollback.
- Which scripts are obsolete or superseded.

Read the scripts before executing them.

Do not invent a parallel deployment workflow when the repository already contains one.

## 4. Important rule

This is initially an AUDIT ONLY task.

Do not automatically deploy all historical changes.

First establish exactly what is missing, what is present, what is running, and what has regressed.

Only after producing the audit should you propose and execute a carefully scoped remediation plan.

Any changes must preserve existing user work and the currently functioning installation.
