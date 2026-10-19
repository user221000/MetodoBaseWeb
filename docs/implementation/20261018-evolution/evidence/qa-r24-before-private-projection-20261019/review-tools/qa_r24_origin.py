"""Fail before any fixture UUID on mixed web/api/core/tests/config/script source or Base aliases."""
import hashlib,importlib,inspect,json,os,sys
from pathlib import Path
import pytest
ROOT=Path('F:/mb-r24-qa-20261019').resolve()
PREFIXES=('web','api','core','tests','config','scripts','conftest')
def audit(stage):
    models=importlib.import_module('web.database.models');schema=importlib.import_module('web.database.schema_control')
    rows={};aliases={}
    for name,module in list(sys.modules.items()):
        if module is None or not any(name==prefix or name.startswith(prefix+'.') for prefix in PREFIXES):continue
        source=getattr(module,'__file__',None)
        if source:
            path=Path(source).resolve();assert path.is_relative_to(ROOT),('foreign-module-origin',name,str(path))
            rows[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in getattr(module,'__path__',[]):assert Path(path).resolve().is_relative_to(ROOT),('foreign-package-path',name,str(path))
        candidate=vars(module).get('Base')
        if candidate is not None:
            assert candidate is models.Base,('foreign-Base-alias',name)
            aliases[name]=str(Path(inspect.getfile(candidate)).resolve())
    assert Path(inspect.getfile(models.Base)).resolve()==ROOT/'web/database/models.py'
    assert len(models.Base.metadata.tables)==29
    assert schema.expected_head()=='20261019_personal_history_index'
    output=Path(os.environ['QA_HISTORY30_MODULE_ORIGIN_OUT']);output.mkdir(exist_ok=True,parents=True)
    (output/'module-origins.json').write_text(json.dumps({'stage':stage,'all_imported_project_modules_exact_WT30':True,'expected_root':str(ROOT),'module_count':len(rows),'modules':rows,'Base_aliases':aliases,'Base_metadata_tables':29,'actual_expected_head':schema.expected_head(),'own_plugins_and_external_test':'Explicit external QA files are outside these project package namespaces.'},indent=2)+'\n',encoding='utf8')
def pytest_sessionstart(session):
    for name in ['web.database.models','web.database.schema_control','api','core','tests.integration_schema_migrations','scripts.backup_restore','config.settings']:importlib.import_module(name)
    audit('sessionstart-before-any-fixture')
@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef,request):
    audit('before-fixture-'+fixturedef.argname)
    yield
    audit('after-fixture-'+fixturedef.argname)
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    audit('before-test-call');yield;audit('after-test-call')
def pytest_sessionfinish(session,exitstatus):audit('sessionfinish')
