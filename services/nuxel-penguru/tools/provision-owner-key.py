#!/usr/bin/env python3
"""Create an owner-local Ed25519 release key without replacing an existing key.

Keep the private key outside the repository. Only the public key is enrolled
on the handset; enrollment and manifest signing are separate explicit steps.
"""
import argparse
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def provision(path):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Refusing symlink private key')
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise ValueError('Existing private key must have mode 0600')
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError('Existing key is not Ed25519')
    else:
        key = Ed25519PrivateKey.generate()
        data = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
    return key.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_key', type=Path)
    parser.add_argument('public_key', type=Path)
    args = parser.parse_args()
    public = provision(args.private_key)
    if args.public_key.exists() and args.public_key.read_bytes() != public:
        parser.error('Refusing to replace a different public key')
    args.public_key.write_bytes(public)
    print('Owner release public key:', args.public_key)
