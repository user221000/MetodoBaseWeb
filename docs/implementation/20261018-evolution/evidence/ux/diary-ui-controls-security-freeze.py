from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).parent
author=Path('F:/MetodoBaseWeb-diary-ui-20261019')
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest_path=author/'docs/implementation/20261018-evolution/evidence/ux/diary-ui-controls-fix-source.json'
raw=manifest_path.read_bytes()
assert sha(raw)=='cfecc433a12a796cf7014a62311002535cb82fd787a90e62a8c76cbcba19ef7d'
manifest=json.loads(raw)
sources={k:(v['sha256'] if isinstance(v,dict) else v) for k,v in manifest['sources'].items()}
sources.update({k:(v['sha256'] if isinstance(v,dict) else v) for k,v in manifest['read_only_dependencies'].items()})
assert len(sources)==57,len(sources)
assert all(sha((author/name).read_bytes())==digest for name,digest in sources.items())
assert subprocess.run(['git','rev-parse','HEAD'],cwd=author,capture_output=True,check=True,text=True).stdout.strip()=='bf46e163f82a318873c4da6b460609520eb80d85'
assert not subprocess.run(['git','diff','--name-only'],cwd=author,capture_output=True,check=True,text=True).stdout
drivers={'machineack-frozen.cjs':'027d50ffe765fb6fca8b2a38cc3c529e4d82d62b079c76699c0b92bbf09fd142','extras-frozen.cjs':'903a4fe4e8fa0ee556f5d9218a3aab7c9c398ad6949bb16e07e53e4f4ab6342b'}
for name,digest in drivers.items():assert sha((root/name).read_bytes())==digest
record={'author_commit':'bf46e163f82a318873c4da6b460609520eb80d85','author_manifest_sha256':sha(raw),'sources':sources,'source_count':len(sources),'tracked_sources_clean':True,'untracked_scope':'Existing QA evidence directories are outside the freeze and not mutated.','independent_drivers':drivers}
(root/('sources-'+sys.argv[1]+'.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'phase':sys.argv[1],'sources':len(sources),'tracked_clean':True}))
