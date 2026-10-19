from pathlib import Path
import ast,hashlib,json
TEMP=Path(r'C:\Users\Consu\AppData\Local\Temp');ROOT=Path(r'F:\mb-retirement32-public-qa-20261019')
path=ROOT/'tests/test_qa_retirement32_public.py';before=path.read_text(encoding='utf8')
assert "    assert 'set-cookie' not in response.headers" in before
after=before.replace("    assert 'set-cookie' not in response.headers", "    assert all(value.split('=', 1)[0] == '_csrf' for value in response.headers.get_list('set-cookie'))")
old='@pytest.fixture\ndef legitimate_member(progress_http, monkeypatch):'
new="""@pytest.fixture
def legitimate_member(progress_http, monkeypatch):
    if progress_http['factory'] == 'web.main_web':
        return _prepare_legitimate_member(progress_http, monkeypatch)
    # The historical API factory does not mount team creation. Prepare the
    # real supported genealogy through web, keeping the same migrated DB and
    # actual registered accounts; retire only through the target API client.
    from fastapi.testclient import TestClient
    from web.main_web import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as setup:
        result = _prepare_legitimate_member({**progress_http, 'client_http': setup}, monkeypatch)
    return {**result, 'client_http': progress_http['client_http']}


def _prepare_legitimate_member(progress_http, monkeypatch):"""
assert after.count(old)==1;after=after.replace(old,new)
tests=lambda s:[ast.dump(node,include_attributes=False) for node in ast.parse(s).body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')]
assert tests(before)==tests(after) and len(tests(after))==4
with (TEMP/'metodobase-retirement32-qa-http-v2.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(after)
path.write_text(after,encoding='utf8',newline='\n')
runner=(TEMP/'metodobase-retirement32-qa-http-run.py').read_text(encoding='utf8')
runner=runner.replace('qa-http-20261019','qa-http-v2-20261019').replace('qa-retirement32-http-independent-20261019','qa-retirement32-http-v2-independent-20261019')
copy="with (ROOT/'tests/test_qa_retirement32_public.py').open('xb') as stream:stream.write((TEMP/'metodobase-retirement32-qa-http.py').read_bytes())"
assert runner.count(copy)==1;runner=runner.replace(copy,"assert (ROOT/'tests/test_qa_retirement32_public.py').read_bytes()==(TEMP/'metodobase-retirement32-qa-http-v2.py').read_bytes()")
start=runner.index("for name in ('progress_retirement','progress_retirement_dom'):");end=runner.index('command=',start)
runner=runner[:start]+runner[end:]
runner=runner.replace(",'tests/test_progress_retirement_ui.py','tests/test_progress_retirement_ui_contract.py'",'')
runner=runner.replace('8 SSR are existing source replays;45 VM synthetic cases are separate overlapping scopes, not new API acceptance.','This run repeats only the8 own HTTP cases after correcting the incidental-CSRF and creation-factory harness assumptions. Prior8 SSR/45VM results remain separate, unchanged source.')
ast.parse(runner)
with (TEMP/'metodobase-retirement32-qa-http-v2-run.py').open('x',encoding='utf8',newline='\n') as stream:stream.write(runner)
proof={'before_test_SHA256':hashlib.sha256(before.encode()).hexdigest(),'after_test_SHA256':hashlib.sha256(after.encode()).hexdigest(),'all4_test_function_ASTs_exact':True,
    'changes':'Only private response helper permits the existing unprivileged _csrf cookie and no other cookie. For api.app target only, supported real web team invitation genealogy is prepared over the same actual SQLite, then original API TestClient exercises retirement. No route mounting, auth override or product edit;8 original reds/errors retained.'}
with (TEMP/'metodobase-retirement32-qa-http-v2-preparation.json').open('x',encoding='utf8') as stream:json.dump(proof,stream,indent=2)
print('Only own helper assumptions corrected; four semantic tests AST exact')
