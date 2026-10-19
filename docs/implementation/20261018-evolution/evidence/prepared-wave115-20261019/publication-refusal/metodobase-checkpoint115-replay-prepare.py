from pathlib import Path
tmp=Path(r'C:\Users\Consu\AppData\Local\Temp');original=tmp/'metodobase-checkpoint115.py';text=original.read_text()
old="authenticate('qa-r24-independent-20261019','before-fix-manifest.json','f81bfac40691bae01d2b552d46521d518b80f4f72f99838b33e36b722f2fde50')"
new="authenticate('qa-r24-before-private-projection-20261019','manifest.json','7e86caf16cee1c382c0fa694000159213e491f997f40d3e64d85a5db0d3485c4')"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace('evidence/qa-r24-independent-20261019/before-fix-summary.json','evidence/qa-r24-before-private-projection-20261019/before-fix-summary.json')
needle="write(dest/'scope.json',"
extra="""for path in [tmp/'metodobase-checkpoint115.py',tmp/'metodobase-checkpoint115-replay-prepare.py',tmp/'metodobase-checkpoint115-refusal-20261019/receipt.json',tmp/'metodobase-r24-publication-refusal.py']:
    blob=path.read_bytes();assert not sensitive(blob),path
    target=dest/'publication-refusal'/path.name;target.parent.mkdir(exist_ok=True);target.write_bytes(blob)
"""
assert text.count(needle)==1;text=text.replace(needle,extra+needle)
target=tmp/'metodobase-checkpoint115-replay.py';assert not target.exists();target.write_bytes(text.encode())
print('Prepared new replay; refused original driver and raw manifests unchanged.')
