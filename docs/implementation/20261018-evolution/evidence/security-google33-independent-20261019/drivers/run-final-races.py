from pathlib import Path
import hashlib,json
T=Path(r'C:/Users/Consu/AppData/Local/Temp');R=Path(r'F:/mb-security-google33-peer-20261019');O=R/'docs/implementation/20261018-evolution/evidence/security-google33-independent-20261019'
driver=T/'metodobase-sec-google33-peer-run-pg-20261019.py';raw=driver.read_bytes();source=raw.decode()
source=source.replace("phase=sys.argv[1] if len(sys.argv)>1 else 'pg-functional'","phase='pg-final-races'")
source=source.replace("assert phase in {'pg-functional','pg-migration-restore'}","assert phase=='pg-final-races'")
lines=source.splitlines();index=next(i for i,line in enumerate(lines) if line.startswith('files='));lines[index]="files=['tests/test_security_google33_postgres_peer.py','tests/test_security_google33_canonical_race_peer.py']"
source='\n'.join(lines)+'\n'
source=source.replace("names+=['tests/test_security_google33_peer.py','tests/test_security_google33_postgres_peer.py']","names+=['tests/test_security_google33_peer.py','tests/test_security_google33_postgres_peer.py','tests/test_security_google33_canonical_race_peer.py']")
source=source.replace("run=subprocess.run(cmd,cwd=R,env=environment,capture_output=True,timeout=480)","cmd+=['-k','two_pool1_workers or canonical_http_new_gym_subject_collision or actual33_contract']\nrun=subprocess.run(cmd,cwd=R,env=environment,capture_output=True,timeout=480)")
assert source!=raw.decode() and "phase='pg-final-races'" in source
(O/'final-race-launcher-binding.json').write_bytes((json.dumps({'base_driver_sha256':hashlib.sha256(raw).hexdigest(),'executed_adapter_sha256':hashlib.sha256(source.encode()).hexdigest(),'changes':'Only phase/artifact label, two selected peer modules, explicit source-photo inclusion and focused case selection. Same private profile/lease/quiet/closure driver.'},indent=2)+'\n').encode())
exec(compile(source,str(driver),'exec'))
