"""Move operations endpoints to one shared mount; preserve route payloads."""
from pathlib import Path
import hashlib
import json

root=Path(r'F:\mb-saas-observability-20261019')
out=Path(r'C:\Users\Consu\AppData\Local\Temp\metodobase-saas-observability-source-change-v2-20261019')
out.mkdir(exist_ok=False)
(out/'driver.py').write_bytes(Path(__file__).read_bytes())
api=root/'api/app.py'
web=root/'web/main_web.py'
before={str(p.relative_to(root)):p.read_bytes() for p in [api,web]}
text=api.read_text(encoding='utf8')
for name in ['MetricsMiddleware','get_metrics_summary','check_metrics_alerts','get_error_alerter']:
    needle='\n    '+name+',\n'
    assert text.count(needle)==1
    text=text.replace(needle,'\n')
block='''    app.add_middleware(
        MetricsMiddleware,
        exclude_paths=["/metrics", "/health", "/health/ready"],
    )
'''
assert text.count(block)==1
text=text.replace(block,'')
start=text.index('    from fastapi import Depends\n')
end=text.index('    # '+chr(0x2500)*2+' Static files',start)
text=text[:start]+text[end:]
needle='    return app\n'
replacement='    from web.observability.routes import configure_observability\n    configure_observability(app)\n'+needle
assert text.count(needle)==1
text=text.replace(needle,replacement)
api.write_text(text,encoding='utf8',newline='\n')
text=web.read_text(encoding='utf8')
assert text.count(needle)==1
web.write_text(text.replace(needle,replacement),encoding='utf8',newline='\n')
for name,blob in before.items():(out/(name.replace('/','--')+'.before.raw')).write_bytes(blob)
record={'changes':['One shared protected operations-router/middleware mount in both real factories.',
 'No operations key configured remains403; missing/wrong/non-ASCII headers deny. Operations payloads preserve existingAPI capabilities.',
 'All operations success/denial replies no-store/no-referrer; middleware outer of request handling, no exception values retained.',
 'Metric500 recording added separately with unchanged declared-route/unknown-label privacy policy.'],
 'before_RAW':{n:hashlib.sha256(b).hexdigest() for n,b in before.items()},
 'after_RAW':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [api,web]}}
(out/'receipt.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(record))
