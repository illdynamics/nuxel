#!/usr/bin/python3
"""Upgrade only the shipped legacy Settings network grant, never owner choices."""
import json
import os
from pathlib import Path
import tempfile

LEGACY = {'duration': 'session', 'granted_at': 1792500231.2952952,
          'source': 'preserved first-party grant: Settings Wi-Fi controls'}
CURRENT = {'duration': 'always', 'granted_at': 0, 'portal_type': 'network',
           'source': 'first-party-system-grant: Settings Wi-Fi and mobile-data controls'}


def migrate(document):
    if document.get('network:manage') != LEGACY:
        return False
    document['network:manage'] = dict(CURRENT)
    return True


def main():
    path = Path('/var/lib/nuxel/permissions/nuxel-settings.json')
    if not path.exists():
        return  # bridge seeds the new packaged record on first startup
    info = path.lstat()
    import stat
    import pwd
    owners = {0, pwd.getpwnam("nuxel-bridge").pw_uid}
    if not stat.S_ISREG(info.st_mode) or info.st_uid not in owners or info.st_mode & 0o002:
        raise RuntimeError('unexpected Settings permission store')
    document = json.loads(path.read_text())
    if not migrate(document):
        return
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.settings-network-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(document, f, indent=2)
            f.write('\n')
            f.flush()
            os.fchmod(f.fileno(), stat.S_IMODE(info.st_mode))
            os.fchown(f.fileno(), info.st_uid, info.st_gid)
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == '__main__':
    main()
