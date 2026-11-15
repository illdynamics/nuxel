#!/usr/bin/env python3
"""Live fingerprint enrollment ceremony against the running Nuxel bridge.

Run on the phone (root) from a normal shell; it talks to the local HTTP bridge
as the Settings/Home owner surface.  The real work happens in
fingerprint_provider.py:

  1. refuse unless the Vault keyring is initialised AND unlocked;
  2. start the ceremony, require two edge touches of the sensor oval;
  3. store the enrollment record (HMAC-bound, key inside the Vault);
  4. mark the biometric document enrolled so Security can enable unlock.

No template and no match is ever produced here: this phone's image has no
OEM TEEGrip fingerprint trusted application, and the provider never fakes one.

Usage:  fingerprint-enroll.py [--password VAULT_PASSWORD] [--remove]
"""
import argparse
import json
import subprocess
import sys
import time

BRIDGE = "http://127.0.0.1:8080/api/v1"
SECRET_FILE = "/etc/nuxel/keyring-launcher.secret"
APP = "org.nuxel.Home"


def curl(args, body=None):
    cmd = ["curl", "-s", "--max-time", "90", "-H", "Content-Type: application/json",
           "-H", "X-Nuxel-Bridge-Version: 1"] + args
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {"raw": out[-300:]}


def launcher_vault_token():
    with open(SECRET_FILE) as fh:
        secret = fh.read().strip()
    return curl(["-X", "POST", BRIDGE + "/auth/app-token", "-H",
                 "X-Nuxel-Launcher-Secret: " + secret], {"app_id": "org.nuxel.Vault"})["token"]


def launcher_token():
    with open(SECRET_FILE) as fh:
        secret = fh.read().strip()
    return curl(["-X", "POST", BRIDGE + "/auth/app-token", "-H",
                 "X-Nuxel-Launcher-Secret: " + secret], {"app_id": APP})["token"]


def keyring(token, verb, params=None):
    doc = curl(["-X", "POST", BRIDGE + "/rpc", "-H",
                "Authorization: Bearer " + token,
                "-H", "Origin: http://127.0.0.1:8000",
                "-H", "Referer: http://127.0.0.1:8000/pwa/nuxel-apps/vault/index.html"], {
                    "app_id": "org.nuxel.Vault", "namespace": "keyring",
                    "verb": verb, "params": params or {}})
    return doc.get("result", doc)


def rpc(token, ns, verb, params=None):
    doc = curl(["-X", "POST", BRIDGE + "/rpc", "-H",
                "Authorization: Bearer " + token], {
                    "app_id": APP, "namespace": ns, "verb": verb,
                    "params": params or {}})
    return doc.get("result", doc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--password", default="")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--touches", default="left,right",
                    help="comma list of edges for the two required touches")
    a = ap.parse_args()
    tok = launcher_token()

    if a.remove:
        print(json.dumps(rpc(tok, "fingerprint", "delete", {}), indent=1))
        print(json.dumps(rpc(tok, "security", "set-biometric-unlock",
                             {"enrolled": False}), indent=1))
        return 0

    st = rpc(tok, "fingerprint", "status", {})
    vault = st.get("vault") or {}
    print("vault:", json.dumps(vault))
    if not vault.get("initialized"):
        print("REFUSED: set a Vault master password first (open the Vault).")
        return 2
    if not vault.get("unlocked") and a.password:
        vt = launcher_vault_token()
        u = keyring(vt, "unlock", {"master_password": a.password})
        print("vault unlock:", u.get("success"), u.get("state"), u.get("error"))
        st = rpc(tok, "fingerprint", "status", {})
        vault = st.get("vault") or {}
    if not vault.get("unlocked"):
        print("REFUSED: unlock the Vault first (or pass --password).")
        return 2

    start = rpc(tok, "fingerprint", "ceremony-start", {"label": "Fingerprint"})
    if not start.get("success"):
        print("REFUSED:", start.get("detail") or start.get("error"))
        return 2
    print(start.get("instruction"))
    token = start.get("token")
    for i, edge in enumerate([e.strip() for e in a.touches.split(",") if e.strip()]):
        time.sleep(0.6)
        r = rpc(tok, "fingerprint", "ceremony-touch", {"edge": edge, "token": token})
        print("touch %d (%s edge): %s/%s" % (i + 1, edge, r.get("edges"), r.get("edges_needed")))
    done = rpc(tok, "fingerprint", "ceremony-commit", {"token": token})
    print(json.dumps(done, indent=1))
    if done.get("success"):
        print(json.dumps(rpc(tok, "security", "set-biometric-unlock",
                             {"enrolled": True}), indent=1)[:400])
    return 0 if done.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
