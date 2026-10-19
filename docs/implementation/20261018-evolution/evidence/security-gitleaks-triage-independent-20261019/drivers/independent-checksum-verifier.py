"""Independent fixed-report checksum verifier; no generalized scanner allowlist."""
from pathlib import PurePosixPath
import hashlib,json,re
FIELDS=('file','line','rule','fingerprint','file_sha256')
sha=lambda b:hashlib.sha256(b).hexdigest()
def canonical(value):
    if not isinstance(value,str) or '\\' in value or ':' in value:return False
    p=PurePosixPath(value)
    return bool(value) and not p.is_absolute() and p.as_posix()==value and all(x not in {'..','.'} for x in p.parts)
def verify(row,proof,raw,target,expected_row,expected_raw_hash,transform=None):
    try:
        if any(row.get(k)!=expected_row[k] for k in FIELDS):return False
        if not canonical(row['file']) or not row['file'].startswith('docs/implementation/20261018-evolution/evidence/'):return False
        if type(row['line']) is not int or row['line']<1:return False
        if sha(raw)!=expected_raw_hash or row['file_sha256']!=expected_raw_hash:return False
        encoding='utf-32' if raw.startswith((b'\xff\xfe\0\0',b'\0\0\xfe\xff')) else 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else None
        if encoding:
            if not transform or transform.get('source_encoding')!=encoding or transform.get('scanner_encoding')!='utf-8':return False
            text=raw.decode(encoding,errors='strict')
            if sha(text.encode())!=transform.get('scanner_sha256'):return False
        else:
            if transform:return False
            text=raw.decode('utf8',errors='strict')
        line=text.split('\n')[row['line']-1]
        pair=re.fullmatch(r'\s*"([^"\\]+)"\s*:\s*"([a-f0-9]{64})"\s*,?\s*',line)
        if not pair or not canonical(pair[1]):return False
        if proof['source_path']!=pair[1] or proof['source_sha256']!=pair[2]:return False
        if sha(target)!=pair[2]:return False
        if proof.get('physical_line_sha256')!=sha(line.rstrip('\r').encode()):return False
        return True
    except (KeyError,TypeError,ValueError,IndexError,UnicodeError):return False

def historical(payload,oid,path,pairs,claimed_digest,derivation):
    if not canonical(path) or (oid,path) not in pairs:return False
    if hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()!=oid:return False
    if derivation=='DERIVED_GitLF_to_CRLF_checksum_not_historical_RAW':
        try:payload.decode('utf8',errors='strict')
        except UnicodeError:return False
        if b'\0' in payload or b'\n' not in payload or b'\r\n' in payload:return False
        payload=payload.replace(b'\n',b'\r\n')
    elif derivation!='Git_blob_bytes':return False
    return sha(payload)==claimed_digest
