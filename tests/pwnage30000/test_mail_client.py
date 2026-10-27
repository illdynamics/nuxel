"""Offline tests for the Mail transport client (PWNAGE-30000).

Transport sockets are mocked; no real account credentials are used or stored.
The tests cover account persistence/redaction, discovery, credential gating,
and the IMAP/SMTP success and failure paths.
"""
import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'nuxel-bridge', 'src'))
import mail_client  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('NUXEL_APP_DATA_DIR', str(tmp_path))
    return mail_client.MailClient()


def test_account_save_persists_without_password(client):
    r = client.account_save({"id": "a1", "email": "ada@example.org", "name": "Ada",
                             "imap_host": "imap.example.org", "smtp_host": "smtp.example.org",
                             "password": "TOP-SECRET"})
    assert r['success'] is True
    assert r['account'].get('password') is None
    assert r['account']['credentials'] == 'not-stored'
    listed = client.accounts_list()
    assert listed['accounts'][0]['email'] == 'ada@example.org'
    assert 'TOP-SECRET' not in str(listed)


def test_account_requires_valid_email(client):
    with pytest.raises(mail_client.MailError):
        client.account_save({"id": "a1", "email": "not-an-email"})


def test_discovery_gmail_and_unknown(client):
    g = client.discover('someone@gmail.com')
    assert g['success'] is True and g['found'] is True
    assert g['provider']['auth'] == 'oauth2_required'
    u = client.discover('someone@example-corp.com')
    assert u['success'] is True and u['found'] is False


def test_test_connection_needs_credentials(client):
    client.account_save({"id": "a1", "email": "ada@example.org", "imap_host": "imap.example.org"})
    r = client.test_connection('a1', '')
    assert r['success'] is False
    assert r['error_code'] in ('NEEDS_CREDENTIALS', 'NOT_CONFIGURED', 'AUTH_OR_CONNECT_FAILED')


def test_test_connection_success_with_mocks(client):
    client.account_save({"id": "a1", "email": "ada@example.org",
                         "imap_host": "imap.example.org", "imap_port": 993,
                         "smtp_host": "smtp.example.org", "smtp_port": 587})
    with mock.patch.object(mail_client.imaplib, 'IMAP4_SSL') as imap_cls, \
         mock.patch.object(mail_client.smtplib, 'SMTP') as smtp_cls:
        imap_conn = imap_cls.return_value
        smtp_conn = smtp_cls.return_value
        r = client.test_connection('a1', 'secret')
        assert r['success'] is True
        assert r['stages']['incoming']['ok'] is True
        assert r['stages']['outgoing']['ok'] is True
        imap_conn.login.assert_called_with('ada@example.org', 'secret')
        smtp_conn.login.assert_called_with('ada@example.org', 'secret')


def test_imap_list_parses_headers_with_mock(client):
    client.account_save({"id": "a1", "email": "ada@example.org",
                         "imap_host": "imap.example.org", "imap_port": 993})
    with mock.patch.object(mail_client.imaplib, 'IMAP4_SSL') as imap_cls:
        conn = imap_cls.return_value
        conn.select.return_value = ('OK', [b'1'])
        conn.search.return_value = ('OK', [b'1'])
        header = (b'From: bob@example.org\r\nSubject: Hello\r\nDate: Tue, 27 Oct 2026 10:00:00 +0000\r\n\r\n')
        conn.fetch.return_value = ('OK', [(b'1 (BODY[HEADER.FIELDS (FROM SUBJECT DATE)] {123}', header), b')'])
        r = client.imap_list('a1', 'secret', 'INBOX')
        assert r['success'] is True
        assert r['count'] == 1
        assert r['messages'][0]['subject'] == 'Hello'
        assert r['messages'][0]['from'] == 'bob@example.org'


def test_smtp_send_success_with_mock(client):
    client.account_save({"id": "a1", "email": "ada@example.org",
                         "smtp_host": "smtp.example.org", "smtp_port": 587})
    with mock.patch.object(mail_client.smtplib, 'SMTP') as smtp_cls:
        conn = smtp_cls.return_value
        conn.sendmail.return_value = {}
        r = client.smtp_send('a1', 'secret', ['bob@example.org'], 'Hi', 'Body')
        assert r['success'] is True and r['sent'] is True
        conn.login.assert_called_with('ada@example.org', 'secret')


def test_error_redaction():
    assert 'secret' not in mail_client._safe_mail_error(Exception('password=secret login failed'))
