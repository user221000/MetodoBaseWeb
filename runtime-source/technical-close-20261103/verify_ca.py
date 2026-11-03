"""Verify the pinned base's already withdrawn G3 root without changing trust."""
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import sys

HERE = Path(__file__).resolve().parent
TARGET_DER = '86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b'
TARGET_SPKI = '8d417db2dd8bf5e3084d1e3f196d583849d81bdd4c00c70b9d39369e96b8c782'
PEM = re.compile(br'-----BEGIN CERTIFICATE-----\s+.*?-----END CERTIFICATE-----', re.S)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ders(raw):
    blocks = PEM.findall(raw)
    require(blocks and not PEM.sub(b'', raw).strip(), 'Unexpected CA framing')
    return [ssl.PEM_cert_to_DER_cert(block.decode('ascii')) for block in blocks]


def tlv(raw, offset):
    require(offset + 2 <= len(raw), 'Truncated DER')
    tag, size = raw[offset], raw[offset + 1]
    start = offset + 2
    if size & 128:
        count = size & 127
        require(1 <= count <= 4 and start + count <= len(raw), 'Unsupported DER length')
        size = int.from_bytes(raw[start:start + count], 'big')
        start += count
    end = start + size
    require(end <= len(raw), 'Truncated DER value')
    return tag, start, end


def spki_hash(raw):
    tag, start, end = tlv(raw, 0)
    require(tag == 48 and end == len(raw), 'Unexpected certificate DER')
    tag, child, _ = tlv(raw, start)
    require(tag == 48, 'Unexpected certificate TBS')
    # Optional explicit version, then serial/signature/issuer/validity/subject.
    if raw[child] == 160:
        child = tlv(raw, child)[2]
    for _ in range(5):
        child = tlv(raw, child)[2]
    tag, _, end = tlv(raw, child)
    require(tag == 48, 'Unexpected subjectPublicKeyInfo')
    return sha(raw[child:end])


def main():
    require(sys.platform == 'linux' and sys.version_info[:3] == (3, 12, 16), 'Pinned Linux Python required')
    require(not os.environ.get('SSL_CERT_FILE') and not os.environ.get('SSL_CERT_DIR'), 'Ambient trust overrides rejected')
    lock = json.loads((HERE / 'source-pins.json').read_bytes())['ca_trust']
    bundle = Path('/etc/ssl/certs/ca-certificates.crt')
    conf = Path('/etc/ca-certificates.conf')
    source = Path('/usr/share/ca-certificates/mozilla/emSign_ECC_Root_CA_-_G3.crt')
    for path in (bundle, conf):
        require(path.is_file() and not path.is_symlink() and path.resolve() == path, 'Unexpected CA input')
    require(sha(bundle.read_bytes()) == lock['ca_bundle_sha256']
            and sha(conf.read_bytes()) == lock['ca_conf_sha256'], 'Pinned base trust files differ')
    require(not source.exists() and not source.is_symlink()
            and b'emSign_ECC_Root_CA_-_G3.crt' not in conf.read_bytes(), 'Withdrawn G3 source/config returned')
    certificates = ders(bundle.read_bytes())
    hashes = sorted(sha(raw) for raw in certificates)
    require(len(hashes) == len(set(hashes)) == 148 and hashes == lock['ca_der_sha256']
            and sha(('\n'.join(hashes) + '\n').encode('ascii')) == lock['ca_set_sha256'], 'Exact148 CA set differs')
    require(TARGET_DER not in hashes and TARGET_SPKI not in {spki_hash(raw) for raw in certificates},
            'Withdrawn G3 certificate or key remains trusted')
    capath = Path('/etc/ssl/certs')
    capath_hashes = set()
    for path in capath.iterdir():
        require(not path.is_symlink() or path.exists(), 'Dangling CA alias')
        if path.is_dir():
            continue
        require(path.is_file() and path.stat().st_size <= 2 * 1024**2, 'Unexpected CApath file')
        capath_hashes.update(sha(raw) for raw in ders(path.read_bytes()))
    paths = ssl.get_default_verify_paths()
    require(paths.cafile and Path(paths.cafile).resolve() == bundle
            and paths.capath and Path(paths.capath).resolve() == capath, 'Default trust paths differ')
    defaults = {sha(raw) for raw in ssl.create_default_context().get_ca_certs(binary_form=True)}
    require(capath_hashes == defaults == set(hashes), 'CApath/default context differs from pinned148 bundle')
    result = {'schema': 'metodobase-exact-os-ca-already-withdrawn-v2',
              'base_image': lock['image'], 'target_DER_sha256': TARGET_DER,
              'target_SPKI_sha256': TARGET_SPKI, 'target_source_config_DER_SPKI_absent': True,
              'CApath_and_default_SSLContext_match': True, 'count': 148,
              'bundle_sha256': lock['ca_bundle_sha256'], 'configuration_sha256': lock['ca_conf_sha256'],
              'ca_set_sha256': lock['ca_set_sha256'], 'ca_der_sha256': hashes,
              'truststore_mutation': False, 'scope': 'Pinned base OS trust only;CPython3.12.16 separately rejects compromised intermediate keys;vendored bundles remain separately inventoried.'}
    output = Path('/usr/local/share/metodobase/ca-root-g3-20261103.json')
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    require(json.loads(output.read_bytes()) == result, 'Trust provenance readback differs')


if __name__ == '__main__':
    main()
