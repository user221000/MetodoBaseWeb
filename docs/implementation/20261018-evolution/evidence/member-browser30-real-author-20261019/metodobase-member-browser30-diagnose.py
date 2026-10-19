"""Retain the failed attempt; expose only sanitized own-fixture diagnostics."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import zipfile

TEMP=Path('C:/Users/Consu/AppData/Local/Temp')
RUN=TEMP/'metodobase-member-browser30-author-8x89ac13/real30'
OUT=Path('F:/mb-member-browser30-20261019/docs/implementation/20261018-evolution/evidence/member-browser30-real-author-20261019')
private=json.loads((TEMP/'metodobase-qa-pg55483-private-ok6hrpyq/env.json').read_text(encoding='utf-8-sig'))
owned='metodobase_test_migrations_1c1d356de44e'
matches=[]
for candidate in TEMP.glob('metodobase-member-browser-*'):
    if not candidate.is_dir() or datetime.fromtimestamp(candidate.stat().st_ctime,timezone.utc)<datetime(2026,10,19,14,32,tzinfo=timezone.utc):continue
    metadata=candidate/'owned-database.json'
    if metadata.is_file() and json.loads(metadata.read_bytes())['names']==[owned]:matches.append(candidate)
assert len(matches)==1
phase=matches[0]
(RUN/'diagnostic-phase.private.json').write_text(json.dumps({'phase':str(phase)})+'\n',encoding='utf8')
secrets=[str(private[k]) for k in ['METODOBASE_TEST_MIGRATOR_URL','METODOBASE_TEST_POSTGRES_URL']]
if (phase/'mail.private.json').is_file():secrets.extend(row['token'] for row in json.loads((phase/'mail.private.json').read_bytes()))
def sanitized(raw):
    text=raw.decode('utf8',errors='replace')
    for value in secrets:text=text.replace(value,'[REDACTED_PRIVATE_VALUE]')
    text=re.sub(r'postgres(?:ql)?(?:\+psycopg2)?://[^\s\x22\x27<>]+','[REDACTED_POSTGRES_URL]',text)
    return text
names=['fixture.private.log','browser-result.json','browser-error.private.log','normalizer.private.log','parser.private.log','startup.json','database-closure.json']
for name in names:
    if (phase/name).is_file():
        text=sanitized((phase/name).read_bytes())
        (OUT/('failed-'+name.replace('.private',''))).write_text(text,encoding='utf8')
        if name in ['fixture.private.log','browser-result.json','browser-error.private.log']:
            print(name+'\n'+text)
