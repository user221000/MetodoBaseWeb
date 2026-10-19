"""Offline preparation checks; no product33, PostgreSQL, browser or issuer run."""
import copy
import json

import pytest

from tests.ci_google33 import history,offline,resource_guard
from tests.ci_google33.workflow import expected_workflow
from tests.ci_mfa31.workflow import expected_workflow as version31_workflow


def test_all_prepared_frames_keep_complete_inverse_or_original_function_objects():
    assert len(offline.validate_frames())==30


@pytest.mark.parametrize('schema',['31','32'])
def test_versioned_oracles_are_exact_regular_git_objects_without_materialization(schema):
    spec=history.specifications()[schema]
    files=history.specification(history.ROOT,spec)
    assert len(files)==spec['files']
    assert sum(value[2] for value in files.values())==spec['regular_bytes']


def test_historical_metadata_cannot_self_update_its_executable_digest(tmp_path,monkeypatch):
    directory=tmp_path/'tests/ci_google33';directory.mkdir(parents=True)
    data=history.specifications();data['31']['tree']='0'*40
    (directory/'historical-sources.json').write_text(json.dumps(data),encoding='utf8')
    monkeypatch.setattr(history,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='metadata differs'):history.specifications()


def test_composition_retains_complete_historical30_and_web_desktop_redis_gates():
    old=version31_workflow();new=expected_workflow()
    for name in ['historical-ci30','historical-postgres','historical-image']:
        assert new['jobs'][name]==old['jobs'][name]
    assert new['permissions']==old['permissions'] and new['on']==old['on']
    for name in ['test-web','test-desktop']:
        runs=[s['run'] for s in new['jobs'][name]['steps'] if 'run' in s]
        for step in old['jobs'][name]['steps']:
            if 'run' in step and ('tests/run_isolated.py' in step['run'] or 'check_coverage.py' in step['run'] or './/skipped' in step['run']):
                assert step['run'] in runs
    assert set(new['jobs']['ci-success']['needs'])==set(new['jobs'])-{'ci-success'}


@pytest.mark.parametrize('mode',['job','gate','upload','historical-cwd','coverage','n2','no-skips','desktop','success'])
def test_no_required_job_or_boundary_can_be_removed_from_composition(mode):
    value=copy.deepcopy(expected_workflow())
    if mode=='job':del value['jobs']['historical31-postgres']
    elif mode=='gate':value['jobs']['current-postgres']['steps'][-2]['run']='echo no-op'
    elif mode=='upload':value['jobs']['current-postgres']['steps'][-1]['with']['path']='**/*'
    elif mode=='historical-cwd':value['jobs']['historical31-image']['defaults']['run']['working-directory']='${{ github.workspace }}'
    elif mode in {'coverage','n2','no-skips'}:
        match={'coverage':'check_coverage.py','n2':'-n 2','no-skips':'.//skipped'}[mode]
        next(s for s in value['jobs']['test-web']['steps'] if match in s.get('run',''))['run']='echo omitted'
    elif mode=='desktop':del value['jobs']['test-desktop']
    elif mode=='success':value['jobs']['ci-success']['needs'].remove('current-postgres')
    with pytest.raises(ValueError):offline.verify_workflow(value)


@pytest.mark.parametrize('query',[
    'CREATE DATABASE production','DROP DATABASE metodobase_test_rls_deadbeefdead; DROP DATABASE production',
    'DROP DATABASE metodobase_test_rls_deadbeefdead WITH (FORCE);',
    'CREATE ROLE another','ALTER USER existing SUPERUSER','DROP ROLE existing',
    'SELECT pg_terminate_backend(123)',
])
def test_resource_guard_denies_foreign_ddl_multi_statements_and_global_mutations(query):
    with pytest.raises(AssertionError):resource_guard.parse_ddl(query)


@pytest.mark.parametrize('name',[
    'metodobase_test_migrations_'+'a'*12,'metodobase_test_rls_'+'b'*12,
    'metodobase_test_google_'+'c'*32,'metodobase_test_progress_'+'d'*32,
    'metodobase_test_followup_'+'e'*16,
])
def test_only_canonical_uuid_contracts_reach_the_separate_ownership_checks(name):
    create,drop=resource_guard.parse_ddl('CREATE DATABASE "'+name+'" TEMPLATE template0')
    assert create.group(1)==name and drop is None
    create,drop=resource_guard.parse_ddl('DROP DATABASE "'+name+'" WITH (FORCE)')
    assert create is None and drop.group(1)==name
    # Matching a spelling grants no ownership: execute also requires its own
    # pre-CREATE lease/OID/birth and fresh zero-session query before ordinary DROP.
    assert resource_guard.OWNED=={}
