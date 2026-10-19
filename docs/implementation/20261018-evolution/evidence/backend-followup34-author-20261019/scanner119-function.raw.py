def scan(blob,name,depth=0):
    assert depth<5
    for match in re.finditer(rb'\.[a-f0-9]{64}(?![a-f0-9])',blob):
        p=match.start()
        assert not(p>=30 and re.fullmatch(rb'[A-Za-z0-9_-]{30}',blob[p-30:p])),name
    assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:sk_live_|rk_live_)[A-Za-z0-9]+|otpauth://totp/[^\s\x22\x27]+\?secret=[A-Z2-7]{16,}',blob),name
    if name.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(blob)) as arc:
            members=[(m.filename,arc.read(m)) for m in arc.infolist() if not m.is_dir()]
    elif name.lower().endswith('.tar'):
        with tarfile.open(fileobj=io.BytesIO(blob)) as arc:
            members=[]
            for m in arc.getmembers():
                if m.isdir():continue
                assert m.isreg(),(name,m.name)
                members.append((m.name,arc.extractfile(m).read()))
    else:return
    seen=set()
    for child,data in members:
        p=PurePosixPath(child)
        assert not p.is_absolute() and '..' not in p.parts and child not in seen and len(data)<50_000_000
        seen.add(child)
        scan(data,name+'/'+child,depth+1)
