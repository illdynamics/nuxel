#!/usr/bin/env python3
"""Read-only manifest verifier of a copied A43 payload; never installs."""
import tarfile,hashlib,json,sys
p=sys.argv[1]
with tarfile.open(p,'r:gz') as tf:
  manifest=json.load(tf.extractfile('manifest.json'))
  assert manifest['version']=='v0.6.3-beta'
  assert len(manifest['files'])==19
  for entry in manifest['files']:
    assert '..' not in entry['source'].split('/') and not entry['source'].startswith('/')
    m=tf.getmember('files/'+entry['source']);assert m.isfile() and not m.issym()
    data=tf.extractfile(m).read()
    assert len(data)==entry['bytes']
    assert hashlib.sha256(data).hexdigest()==entry['sha256']
print('Verified payload hashes and 19 safe regular files')
