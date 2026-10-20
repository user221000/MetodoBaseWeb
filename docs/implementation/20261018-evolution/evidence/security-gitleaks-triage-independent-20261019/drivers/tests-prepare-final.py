from pathlib import Path
ROOT=Path(r'F:/mb-security-gitleaks-triage-peer-20261019')
OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019'
dest=OUT/'tests-first-setup';dest.mkdir()
names=['tests-before.json','tests-after.json','tests-summary.json','tests.STRUCTURAL.json','pip-before.raw.log','pip-after.raw.log']
assert all((OUT/n).resolve().parent==OUT.resolve() and (dest/n).resolve().parent==dest.resolve() and not (dest/n).exists() for n in names)
for name in names:(OUT/name).rename(dest/name)
driver=Path(__file__).with_name('metodobase-sec-gitleaks-peer-tests-20261019.py')
source=driver.read_text(encoding='utf8')
source=source.replace("OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019'","OUT=ROOT/'docs/implementation/20261018-evolution/evidence/security-gitleaks-triage-independent-20261019/tests-final'\nOUT.mkdir()")
source=source.replace('pytest-run','pytest-final').replace('tests.xml','tests-final.xml').replace('tests-stdout.raw.log','tests-final-stdout.raw.log').replace('tests-stderr.raw.log','tests-final-stderr.raw.log')
driver.with_name('metodobase-sec-gitleaks-peer-tests-final-20261019.py').write_text(source,encoding='utf8')
print('Original setup RAW retained; final output paths are distinct')
