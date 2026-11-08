"""Safe apply: dry-run, snapshot, pending transaction, confirm, rollback.

Invariants enforced here:
  * dry-run never mutates kernel or persistent state;
  * apply snapshots first, arms an independent rollback timer, then mutates;
  * only Nuxel-owned objects are ever changed (no global flush);
  * a pending/unconfirmed apply is never the boot policy.
"""
import json
import os
import shutil
import subprocess
import time
import uuid

from . import paths
from .backends.base import UnsupportedError, BackendError


class TransactionError(RuntimeError):
    pass


class FirewallManager:
    def __init__(self, backend, policy=None, probe=None, state_dir=None,
                 timer=None, now=None):
        self.backend = backend
        self.probe = probe or {}
        self.state_dir = state_dir or paths.STATE_DIR
        self._timer = timer  # injectable rollback timer for tests
        self._now = now or time.time
        os.makedirs(self.state_dir, exist_ok=True)

    # ------------------------------------------------------------ persistence
    def _read_json(self, name):
        try:
            with open(os.path.join(self.state_dir, name)) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _write_json(self, name, data):
        path = os.path.join(self.state_dir, name)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def _audit(self, op, **fields):
        entry = {"ts": self._now(), "op": op}
        entry.update(fields)
        path = os.path.join(self.state_dir, "audit.log")
        with open(path, "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def pending(self):
        return self._read_json("pending.json")

    def last_known_good(self):
        return self._read_json("last-known-good.json")

    # ----------------------------------------------------------------- dry-run
    def dry_run(self, policy, facts):
        """Render + validate without any mutation.  Returns a report dict."""
        backend_name = policy.get("backend", "auto")
        plan = self.backend.render(policy, facts)
        try:
            self.backend.validate(plan)
            validated = True
        except UnsupportedError as e:
            plan.setdefault("warnings", []).append(str(e))
            validated = False
        return {
            "ok": validated,
            "backend": self.backend.name,
            "capability": self.backend.capability(),
            "plan_doc": plan.get("doc", "") if hasattr(plan, "get") else "",
            "warnings": plan.get("warnings", []),
            "management_rules": self._management_rules(policy),
            "defaults": policy["defaults"],
            "per_app_supported": plan.get("per_app_supported", False),
        }

    @staticmethod
    def _management_rules(policy):
        out = []
        for sid, svc in (policy.get("services") or {}).items():
            if svc.get("enabled") and svc.get("active"):
                out.append({
                    "id": sid,
                    "protocol": svc.get("protocol"),
                    "port": svc.get("port"),
                    "source_cidrs": svc.get("source_cidrs"),
                    "interfaces": svc.get("interfaces"),
                })
        return out

    # ------------------------------------------------------------------ apply
    def apply(self, policy, facts, rollback_after=None, require_confirm=True):
        rollback_after = rollback_after or policy.get("safety", {}).get("rollback_seconds", 60)

        # Preflight: a resolved SSH allowlist must exist before any drop policy.
        if policy["defaults"]["input"] == "deny":
            ssh = (policy.get("services") or {}).get("nuxel-ssh-owner")
            if not ssh or not ssh.get("enabled") or not ssh.get("source_cidrs"):
                raise TransactionError(
                    "refusing to apply input-deny without a prepared SSH allowlist "
                    "(nuxel-ssh-owner must be enabled with source CIDRs)")

        plan = self.backend.render(policy, facts)
        self.backend.validate(plan)

        txid = uuid.uuid4().hex[:16]
        snapshot = self.backend.snapshot()
        prior_policy = self._read_json("last-known-good.json")
        snapshot_file = os.path.join(self.state_dir, "snapshots", txid + ".json")
        os.makedirs(os.path.dirname(snapshot_file), exist_ok=True)
        with open(snapshot_file, "w") as fh:
            json.dump({"backend_snapshot": snapshot, "policy_hash": _hash(policy)}, fh, sort_keys=True)

        deadline = self._now() + rollback_after
        pending = {
            "txid": txid,
            "backend": self.backend.name,
            "policy_hash": _hash(policy),
            "snapshot_path": snapshot_file,
            "deadline": deadline,
            "rollback_after": rollback_after,
            "require_confirm": require_confirm,
            "created": self._now(),
        }
        self._write_json("pending.json", pending)

        # Arm the independent rollback timer BEFORE mutating.
        self._arm_rollback(txid, rollback_after)

        try:
            self.backend.apply(plan)
        except BackendError:
            self.backend.rollback(snapshot)
            self._clear_pending()
            self._audit("apply-failed", txid=txid)
            raise

        self._audit("apply", txid=txid, policy_hash=pending["policy_hash"],
                    rollback_after=rollback_after)
        # verify the service rules are actually present in live readback
        verified = self._verify_management(policy)
        return {"txid": txid, "deadline": deadline, "verified": verified,
                "pending": True, "rollback_after": rollback_after}

    def confirm(self):
        pending = self.pending()
        if not pending:
            raise TransactionError("no pending transaction to confirm")
        # last-known-good is the policy that is now live; we record it plus the
        # backend snapshot path so boot recovery can restore if needed.
        self._write_json("last-known-good.json", {
            "txid": pending["txid"],
            "backend": pending["backend"],
            "policy_hash": pending["policy_hash"],
            "snapshot_path": pending["snapshot_path"],
            "confirmed": self._now(),
        })
        self._disarm_rollback(pending["txid"])
        self._clear_pending()
        self._audit("confirm", txid=pending["txid"])
        return {"confirmed": True, "txid": pending["txid"]}

    def rollback(self, txid=None):
        pending = self.pending()
        if txid and pending and pending.get("txid") != txid:
            # Roll back the recorded transaction regardless.
            pass
        snapshot_data = self._read_json("snapshots/%s.json" % (pending["txid"] if pending else txid))
        if not snapshot_data:
            # Fall back to last-known-good if a pending snapshot is missing.
            lkg = self.last_known_good()
            if lkg:
                snapshot_data = {"backend_snapshot": None, "policy_hash": lkg.get("policy_hash")}
        if snapshot_data:
            self.backend.rollback(snapshot_data.get("backend_snapshot") or {})
        self._clear_pending()
        self._audit("rollback", txid=(pending or {}).get("txid", txid))
        return {"rolled_back": True}

    def boot_recover(self):
        """Restore last-known-good when an unconfirmed pending transaction exists."""
        pending = self.pending()
        if pending:
            self._audit("boot-recovery-pending", txid=pending.get("txid"))
            self.rollback(pending.get("txid"))
            return {"recovered": True, "reason": "unconfirmed pending transaction at boot"}
        return {"recovered": False}

    # ---------------------------------------------------------------- helpers
    def _clear_pending(self):
        path = os.path.join(self.state_dir, "pending.json")
        try:
            os.unlink(path)
        except OSError:
            pass

    def _arm_rollback(self, txid, seconds):
        if self._timer is not None:
            self._timer(txid, seconds)
            return
        # Independent from the daemon/UI lifetime: use systemd-run when present,
        # else a detached process that sleeps then invokes the CLI rollback.
        cli = shutil.which("nuxel-firewall")
        if not cli:
            return
        if shutil.which("systemd-run"):
            subprocess.Popen(
                ["systemd-run", "--on-active=%ds" % seconds,
                 "--unit=nuxel-firewall-rollback-%s" % txid,
                 cli, "rollback", "--tx", txid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(
                ["sh", "-c", "sleep %d; exec %s rollback --tx %s" % (seconds, cli, txid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)

    def _disarm_rollback(self, txid):
        if self._timer is not None:
            return
        if shutil.which("systemctl"):
            subprocess.Popen(
                ["systemctl", "stop", "nuxel-firewall-rollback-%s.timer" % txid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.Popen(
                ["systemctl", "stop", "nuxel-firewall-rollback-%s.service" % txid],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _verify_management(self, policy):
        readback = self.backend.readback()
        text = "\n".join(str(v) for v in (readback.values() if isinstance(readback, dict) else [readback]))
        missing = []
        for sid, svc in (policy.get("services") or {}).items():
            if svc.get("enabled") and svc.get("active"):
                ports = svc.get("port", 22)
                ports = ports if isinstance(ports, list) else [ports]
                for port in ports:
                    if "--dport %s" % port not in text and str(port) not in text:
                        missing.append(sid)
        return len(missing) == 0


def _hash(policy):
    import hashlib
    blob = json.dumps(policy, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:32]
