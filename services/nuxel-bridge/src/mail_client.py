#!/usr/bin/env python3
"""Nuxel Mail transport client (PWNAGE-30000).

The PWA cannot open IMAP/SMTP sockets, so the root-owned HTTP bridge is the
transport owner.  This module implements account configuration, provider
autodiscovery suggestions, a staged connection test, IMAP header fetch and SMTP
submission using the standard library (imaplib/smtplib) over TLS only.

CREDENTIALS: passwords/refresh tokens are accepted per request and are NEVER
persisted, logged, or returned.  The bridge is the only process that sees them,
and it holds them only for the duration of the transport call.  TLS certificate
validation is always on (no ssl._create_unverified_context here).

Account configuration (host/port/tls) is persisted in
NUXEL_APP_DATA_DIR/mail/accounts.json.  Passwords are not part of that file.
"""
from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

try:
    import imaplib
except Exception:  # pragma: no cover
    imaplib = None

DEFAULT_DATA_DIR = "/var/lib/nuxel/app-data"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Modern provider discovery.  These are suggestions for official endpoints, not
# a claim that every tenant/account uses identical servers.
PROVIDERS = {
    "gmail.com": {
        "incoming": {"type": "imap", "host": "imap.gmail.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.gmail.com", "port": 465, "tls": True},
        "auth": "oauth2_required",
        "note": "Gmail requires OAuth2 for IMAP/SMTP; a password will be refused.",
    },
    "googlemail.com": {
        "incoming": {"type": "imap", "host": "imap.gmail.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.gmail.com", "port": 465, "tls": True},
        "auth": "oauth2_required",
        "note": "Gmail requires OAuth2 for IMAP/SMTP; a password will be refused.",
    },
    "outlook.com": {
        "incoming": {"type": "imap", "host": "outlook.office365.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.office365.com", "port": 587, "tls": True},
        "auth": "oauth2_or_password",
    },
    "hotmail.com": {
        "incoming": {"type": "imap", "host": "outlook.office365.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.office365.com", "port": 587, "tls": True},
        "auth": "oauth2_or_password",
    },
    "live.com": {
        "incoming": {"type": "imap", "host": "outlook.office365.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.office365.com", "port": 587, "tls": True},
        "auth": "oauth2_or_password",
    },
    "office365.com": {
        "incoming": {"type": "imap", "host": "outlook.office365.com", "port": 993, "tls": True},
        "outgoing": {"type": "smtp", "host": "smtp.office365.com", "port": 587, "tls": True},
        "auth": "oauth2_or_password",
    },
}


class MailError(Exception):
    pass


class MailClient:
    def __init__(self, root: str | None = None):
        root = root or os.environ.get("NUXEL_APP_DATA_DIR") or DEFAULT_DATA_DIR
        self.accounts_path = Path(root) / "mail" / "accounts.json"
        self._mkdir()

    def _mkdir(self) -> None:
        self.accounts_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_accounts(self) -> list:
        try:
            with self.accounts_path.open("r", encoding="utf-8") as fh:
                doc = json.load(fh)
            accounts = doc.get("accounts") if isinstance(doc, dict) else None
            return accounts if isinstance(accounts, list) else []
        except (OSError, ValueError):
            return []

    def _write_accounts(self, accounts: list) -> None:
        self._mkdir()
        tmp = self.accounts_path.with_suffix(".json.tmp")
        data = json.dumps({"schema_version": 1, "accounts": accounts,
                           "credentials": "not-stored", "updated_at": int(time.time())},
                          indent=2, sort_keys=True) + "\n"
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, self.accounts_path)

    def _redact(self, account: dict) -> dict:
        out = dict(account)
        out.pop("password", None)
        out["credentials"] = "not-stored"
        return out

    # ---- account configuration -------------------------------------------
    def accounts_list(self) -> dict:
        return {"success": True, "accounts": [self._redact(a) for a in self._read_accounts()],
                "credentials": "not-stored"}

    def account_save(self, account: dict) -> dict:
        if not isinstance(account, dict):
            raise MailError("account must be an object")
        email = (account.get("email") or "").strip()
        if not EMAIL_RE.match(email):
            raise MailError("a valid email address is required")
        clean = {
            "id": str(account.get("id") or ("acct-%d" % int(time.time() * 1000))),
            "email": email,
            "name": (account.get("name") or "").strip() or email.split("@")[0],
            "incoming_type": str(account.get("incoming_type") or "imap").lower(),
            "imap_host": (account.get("imap_host") or "").strip(),
            "imap_port": int(account.get("imap_port") or 993),
            "smtp_host": (account.get("smtp_host") or "").strip(),
            "smtp_port": int(account.get("smtp_port") or 587),
            "tls": bool(account.get("tls", True)),
            "updated_at": int(time.time()),
        }
        accounts = self._read_accounts()
        idx = next((i for i, a in enumerate(accounts) if a.get("id") == clean["id"]), None)
        if idx is None:
            idx = next((i for i, a in enumerate(accounts) if a.get("email") == email), None)
        if idx is not None:
            accounts[idx] = clean
        else:
            accounts.append(clean)
        self._write_accounts(accounts)
        return {"success": True, "account": self._redact(clean), "count": len(accounts)}

    def account_delete(self, account_id: str) -> dict:
        accounts = self._read_accounts()
        remaining = [a for a in accounts if a.get("id") != account_id]
        if len(remaining) == len(accounts):
            return {"success": False, "error": "account not found", "error_code": "NOT_FOUND"}
        self._write_accounts(remaining)
        return {"success": True, "deleted": True, "count": len(remaining)}

    def discover(self, email: str) -> dict:
        domain = (email or "").split("@")[-1].lower() if "@" in (email or "") else ""
        provider = PROVIDERS.get(domain)
        if provider is None:
            return {"success": True, "found": False,
                    "detail": "no official autodiscover entry for this domain; configure hosts manually"}
        return {"success": True, "found": True, "domain": domain, "provider": provider}

    # ---- transport --------------------------------------------------------
    def _account_by_id(self, account_id: str):
        account_id = str(account_id or "")
        for a in self._read_accounts():
            if a.get("id") == account_id or a.get("email") == account_id:
                return a
        return None

    def test_connection(self, account_id: str, password: str) -> dict:
        account = self._account_by_id(account_id)
        if account is None:
            return {"success": False, "stage": "account", "error": "account not found",
                    "error_code": "NOT_FOUND"}
        if not account.get("imap_host"):
            return {"success": False, "stage": "incoming", "error": "incoming server host is not configured",
                    "error_code": "NOT_CONFIGURED"}
        result = {"success": True, "stages": {}}
        if account.get("incoming_type", "imap") == "imap":
            incoming = self._imap_login(account, password)
            result["stages"]["incoming"] = incoming
            if not incoming.get("ok"):
                return {"success": False, "stage": "incoming", "error": incoming.get("error"),
                        "error_code": incoming.get("error_code", "INCOMING_FAILED"), "stages": result["stages"]}
        if account.get("smtp_host"):
            outgoing = self._smtp_login(account, password)
            result["stages"]["outgoing"] = outgoing
            if not outgoing.get("ok"):
                return {"success": False, "stage": "outgoing", "error": outgoing.get("error"),
                        "error_code": outgoing.get("error_code", "OUTGOING_FAILED"), "stages": result["stages"]}
        return result

    def _imap_login(self, account: dict, password: str) -> dict:
        if imaplib is None:
            return {"ok": False, "error": "imaplib unavailable", "error_code": "UNAVAILABLE"}
        if not password:
            return {"ok": False, "error": "a password/token is required for this account",
                    "error_code": "NEEDS_CREDENTIALS"}
        host, port = account.get("imap_host"), int(account.get("imap_port") or 993)
        try:
            conn = imaplib.IMAP4_SSL(host, port, ssl_context=ssl.create_default_context())
            conn.login(account.get("email"), password)
            conn.logout()
            return {"ok": True, "server": host}
        except Exception as exc:  # noqa: BLE001 - never include the password
            return {"ok": False, "error": _safe_mail_error(exc), "error_code": "AUTH_OR_CONNECT_FAILED"}

    def _smtp_login(self, account: dict, password: str) -> dict:
        if not password:
            return {"ok": False, "error": "a password/token is required for this account",
                    "error_code": "NEEDS_CREDENTIALS"}
        host, port = account.get("smtp_host"), int(account.get("smtp_port") or 587)
        try:
            ctx = ssl.create_default_context()
            conn = smtplib.SMTP(host, port, timeout=20)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()
            conn.login(account.get("email"), password)
            conn.quit()
            return {"ok": True, "server": host}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": _safe_mail_error(exc), "error_code": "AUTH_OR_CONNECT_FAILED"}

    def imap_list(self, account_id: str, password: str, folder: str = "INBOX") -> dict:
        if imaplib is None:
            return {"success": False, "error": "imaplib unavailable", "error_code": "UNAVAILABLE"}
        account = self._account_by_id(account_id)
        if account is None:
            return {"success": False, "error": "account not found", "error_code": "NOT_FOUND"}
        if not password:
            return {"success": False, "error": "a password/token is required to fetch mail",
                    "error_code": "NEEDS_CREDENTIALS", "messages": []}
        folder = (folder or "INBOX").strip('"')
        try:
            conn = imaplib.IMAP4_SSL(account.get("imap_host"), int(account.get("imap_port") or 993),
                                     ssl_context=ssl.create_default_context())
            conn.login(account.get("email"), password)
            status, _ = conn.select(folder, readonly=True)
            if status != "OK":
                conn.logout()
                return {"success": False, "error": "cannot open folder %s" % folder,
                        "error_code": "FOLDER_FAILED", "messages": []}
            typ, data = conn.search(None, "ALL")
            uids = data[0].split() if typ == "OK" and data and data[0] else []
            messages = []
            for uid in uids[-100:]:
                try:
                    ftyp, fdata = conn.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    if ftyp != "OK" or not fdata:
                        continue
                    chunks = []
                    for part in fdata:
                        if isinstance(part, tuple):
                            chunks.extend(p for p in part if isinstance(p, bytes))
                        elif isinstance(part, bytes):
                            chunks.append(part)
                    raw = b"\r\n".join(chunks)
                    raw = _strip_imap_literal(raw)
                    messages.append(self._parse_header(raw, uid.decode()))
                except Exception:  # noqa: BLE001 - skip a malformed message, report the rest
                    continue
            conn.logout()
            return {"success": True, "folder": folder, "messages": messages, "count": len(messages)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": _safe_mail_error(exc),
                    "error_code": "IMAP_FAILED", "messages": []}

    def _parse_header(self, raw: bytes, uid: str) -> dict:
        import email
        msg = email.message_from_bytes(raw)
        subject = str(msg.get("Subject") or "(no subject)")
        frm = str(msg.get("From") or "")
        date = str(msg.get("Date") or "")
        return {"id": uid, "folder": "INBOX", "from": frm[:200], "subject": subject[:300],
                "date": date[:80], "flags": [], "read": False}

    def smtp_send(self, account_id: str, password: str, to, subject: str, body: str) -> dict:
        account = self._account_by_id(account_id)
        if account is None:
            return {"success": False, "error": "account not found", "error_code": "NOT_FOUND"}
        if not password:
            return {"success": False, "error": "a password/token is required to send mail",
                    "error_code": "NEEDS_CREDENTIALS"}
        if not account.get("smtp_host"):
            return {"success": False, "error": "outgoing server host is not configured",
                    "error_code": "NOT_CONFIGURED"}
        recipients = to if isinstance(to, list) else [to]
        recipients = [str(r) for r in recipients if str(r).strip()]
        if not recipients:
            return {"success": False, "error": "at least one recipient is required",
                    "error_code": "NO_RECIPIENTS"}
        try:
            msg = EmailMessage()
            msg["From"] = account.get("email")
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject or ""
            msg.set_content(body or "")
            ctx = ssl.create_default_context()
            host, port = account.get("smtp_host"), int(account.get("smtp_port") or 587)
            conn = smtplib.SMTP(host, port, timeout=30)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()
            conn.login(account.get("email"), password)
            refused = conn.sendmail(account.get("email"), recipients, msg.as_string())
            conn.quit()
            return {"success": True, "sent": True, "message_id": msg.get("Message-ID"),
                    "accepted": len(recipients) - len(refused or {}), "refused": refused or {}}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": _safe_mail_error(exc), "error_code": "SMTP_FAILED"}


def _strip_imap_literal(raw: bytes) -> bytes:
    """Remove the IMAP fetch envelope line and closing parenthesis so the
    remaining bytes are exactly the RFC 5322 header block."""
    raw = re.sub(rb"^[^\r\n]*\{\d+\}\r\n", b"", raw)
    raw = raw.strip(b"\r\n")
    if raw.endswith(b")"):
        raw = raw[:-1]
    return raw


def _safe_mail_error(exc: Exception) -> str:
    """Return a useful transport error WITHOUT echoing credentials or secrets."""
    text = str(exc)
    text = re.sub(r"(?i)(password|passwd|token)=[^ ]+", r"\1=REDACTED", text)
    return text[:200]


def mail_client(root: str | None = None) -> MailClient:
    return MailClient(root)
