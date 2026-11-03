"""Current41 startup with an explicitly owned writable synthetic data mount.

The historical startup program and its catalogue remain byte-for-byte inputs.
Only this successor requires the mount's owner, mode and actual write witness.
"""
from __future__ import annotations

import hashlib

from tests.ci_web41.source_companion import source_bytes

PARENT_SHA256 = "1616b0f8f216ac4f37bd3a725cb59f2a6743cdece5f138a18761227a43e4fc19"
DATA_OPTIONS = "rw,nosuid,nodev,mode=0755,uid=999,gid=999"


def source():
    raw = source_bytes("tests/ci_image57/current41_startup.py")
    if hashlib.sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError("Exact current41 startup parent differs")
    changes = (
        (b"'/data:rw,nosuid,nodev,mode=1777'",
         b"'/data:rw,nosuid,nodev,mode=0755,uid=999,gid=999'"),
        (b"'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true']}",
         b"'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges:true'],\n"
         b"              'Tmpfs': {'/data': 'rw,nosuid,nodev,mode=0755,uid=999,gid=999',\n"
         b"                        '/tmp': 'rw,nosuid,nodev,mode=1777'}}"),
        (b"WITNESS = br'''import hashlib,json,os\n", b"WITNESS = br'''import hashlib,json,os,stat\n"),
        (b"print(json.dumps({'revision':expected_head(),",
         b"data_stat=Path('/data').stat()\n"
         b"owned_probe=Path('/data')/('ci-mount-'+os.urandom(16).hex())\n"
         b"owned_probe.mkdir(mode=0o700)\nowned_probe.rmdir()\n"
         b"print(json.dumps({'data_uid':data_stat.st_uid,'data_gid':data_stat.st_gid,"
         b"'data_mode':stat.S_IMODE(data_stat.st_mode),'data_write':True,'revision':expected_head(),"),
        (b"'effective_capabilities': 0, 'pool_size': 1, 'max_overflow': 0}",
         b"'effective_capabilities': 0, 'pool_size': 1, 'max_overflow': 0,\n"
         b"             'data_uid': 999, 'data_gid': 999, 'data_mode': 0o755, 'data_write': True}"),
    )
    for before, after in changes:
        if raw.count(before) != 1:
            raise ValueError("Exact owned-data startup edit differs")
        raw = raw.replace(before, after, 1)
    return raw


_dispatch = __name__ == "__main__"
_namespace = {"__name__": "tests.ci_image57.owned_data_startup", "__file__": __file__,
              "__package__": "tests.ci_image57"}
exec(compile(source(), __file__, "exec", dont_inherit=True), _namespace)
for _key, _value in _namespace.items():
    if not _key.startswith("__"):
        globals()[_key] = _value

if _dispatch:
    raise SystemExit(_namespace["main"]())
