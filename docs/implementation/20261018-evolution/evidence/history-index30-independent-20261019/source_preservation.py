"""Authenticate13 RAW sources/85 author proof blobs and old18 target preservation."""
from zipfile import ZipFile,ZIP_DEFLATED
from support import *

frozen=ROOT/FREEZE
assert sha((frozen/'freeze.json').read_bytes())=='d01f5b6b898a896d87a22ab6c6fde51ecd508848e6003d7b1e00a59bbad4e3aa'
assert sha((frozen/'manifest.json').read_bytes())=='21b14926d7514fe877ddd344a1abcf666d413585c9b7126920721c8da8aa3d1b'
freeze=json.loads((frozen/'freeze.json').read_bytes())
manifest=json.loads((frozen/'manifest.json').read_bytes())['files']
for name,expected in manifest.items():
    raw=(frozen/name).read_bytes()
    assert len(raw)==expected['bytes'] and sha(raw)==expected['sha256']
private=Path(freeze['private_exact_RAW_zip'])
assert sha(private.read_bytes())==freeze['private_exact_RAW_zip_sha256']
eol=json.loads((frozen/'staging-EOL-receipt.json').read_bytes())
allowed={row['path']:row for row in eol['source_EOL_only_paths']}
assert set(allowed)=={'web/database/models.py','web/database/schema_control.py'}
raw_sources={};records={}
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=AUTHOR).decode().strip()==HEAD
for name,expected in freeze['source_files'].items():
    raw=(AUTHOR/name).read_bytes();blob=git('show',HEAD+':'+name);work=(ROOT/name).read_bytes()
    assert len(raw)==expected['bytes'] and sha(raw)==expected['sha256']
    if name in allowed:
        assert sha(raw)==allowed[name]['RAW_sha256'] and sha(blob)==allowed[name]['Git_LF_sha256']
        assert raw.replace(b'\r\n',b'\n')==blob
    else:assert raw==blob
    assert work.replace(b'\r\n',b'\n')==blob.replace(b'\r\n',b'\n')
    if name.endswith('.py'):assert ast.dump(ast.parse(raw),include_attributes=False)==ast.dump(ast.parse(blob),include_attributes=False)==ast.dump(ast.parse(work),include_attributes=False)
    raw_sources[name]=raw;records[name]={'raw_sha256':sha(raw),'Git_sha256':sha(blob),'own_checkout_sha256':sha(work)}
assert len(raw_sources)==13
archive_path=TEMP/'authenticated-author-RAW13.zip'
with ZipFile(archive_path,'x',ZIP_DEFLATED) as archive:
    for name,raw in raw_sources.items():archive.writestr(name,raw)
historical=[name for name in git('ls-tree','-r','--name-only',BASE,'web/database/alembic/schema_targets').decode().splitlines() if name.endswith('.json')]
assert len(historical)==18
for name in historical:assert git('show',BASE+':'+name)==git('show',HEAD+':'+name)
for name in ['web/database/alembic/schema_contract_v1.py','web/database/alembic/security_contract_v1.py','web/database/tenant_policy.py','web/database/member_link_policy_v1.py','web/database/member_link_projection_v1.py']:
    assert git('show',BASE+':'+name)==git('show',HEAD+':'+name)
targets={}
for dialect in ['sqlite','postgresql']:
    previous=json.loads((ROOT/'web/database/alembic/schema_targets'/('20261019_client_account_links_'+dialect+'.json')).read_bytes())
    current=json.loads((ROOT/'web/database/alembic/schema_targets'/('20261019_personal_history_index_'+dialect+'.json')).read_bytes())
    physical=current.pop('history_order_index')
    indexes=current['signature']['tables']['planes_generados']['indexes']
    found=[item for item in indexes if item['name']=='ix_planes_gym_cliente_history'];assert len(found)==1
    indexes.remove(found[0]);assert current==previous
    targets[dialect]={'only_new_structural_index':found[0],'physical_contract':physical,'all_other_target_fields_exact_previous29':True}
# The one historical test change retargets its physical index expectation and adds no-temp-sort.
before=ast.parse(git('show',BASE+':tests/test_personal_history_pagination.py'))
after=ast.parse((ROOT/'tests/test_personal_history_pagination.py').read_bytes())
function=next(node for node in after.body if isinstance(node,ast.FunctionDef) and node.name=='test_query_is_readonly_limit_plus_one_without_count_or_plan_json')
extra=[node for node in function.body if isinstance(node,ast.Assert) and any(isinstance(child,ast.Constant) and child.value=='USE TEMP B-TREE FOR ORDER BY' for child in ast.walk(node))]
assert len(extra)==1;function.body.remove(extra[0])
replaced=0
for node in ast.walk(function):
    if isinstance(node,ast.Constant) and node.value=='ix_planes_gym_cliente_history':node.value='ix_planes_gym_fecha';replaced+=1
assert replaced==1 and ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
save('source-preservation.json',{'head':HEAD,'base':BASE,'author_proof_blobs_verified':len(manifest),'sources_verified':records,
     'independent_RAW13_archive':str(archive_path),'RAW13_archive_sha256':sha(archive_path.read_bytes()),
     'private_author_RAW_zip_sha256':freeze['private_exact_RAW_zip_sha256'],'historical18_targets_exact':historical,
     'historical_contracts_and_core_guard_sources_unchanged':True,'target30_deltas':targets,
     'maintained_pagination_AST_exact_except_one_index_literal_and_one_added_no_sort_assert':True})
print(json.dumps({'sources':13,'author_proofs':len(manifest),'historical_targets':18,'source_preservation':'PASS'}))
