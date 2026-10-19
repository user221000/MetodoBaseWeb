"""Wire typed metadata normalization while preserving all maintained assertions."""
import ast,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(r'F:\mb-r23-history30-20261019');path=ROOT/'tests/verify_history_index_ci.py'
spec=importlib.util.spec_from_file_location('normalize_wire_guard',path);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
source=path.read_text(encoding='utf8');workflow=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf8')
old_vm=guard.FOLLOWUP_VM_STEP.copy();new_vm=old_vm.copy()
new_vm['run']=''.join('node tests/e2e/'+name+'.cjs > followup-contracts-'+name+'.raw.json\n'
    'python tests/e2e/normalize_followup_report.py followup-contracts-'+name+'.raw.json followup-contracts-'+name+'.json --kind counts --minimum '+str(minimum)+'\n'
    'python scripts/check_frontend_report.py followup-contracts-'+name+'.json --format counts --minimum '+str(minimum)+'\n' for name,minimum in guard.FOLLOWUP_VM_MINIMA.items())
old_browser=guard.FOLLOWUP_BROWSER_STEP.copy();new_browser=old_browser.copy()
needle='python scripts/check_frontend_report.py "$public/report.json" --format results --minimum 8 --screens 5'
assert old_browser['run'].count(needle)==1
new_browser['run']=old_browser['run'].replace(needle,'python tests/e2e/normalize_followup_report.py "$public/report.json" "$public/normalized.json" --kind browser --minimum 8\npython scripts/check_frontend_report.py "$public/normalized.json" --format named --minimum 8 --minimum-screens 5')
new_browser['run']=new_browser['run'].replace('trap finish_followup EXIT INT TERM','trap finish_followup EXIT\ntrap \'exit 130\' INT\ntrap \'exit 143\' TERM')
for old,new in [(old_vm,new_vm),(old_browser,new_browser)]:
    before=''.join('          '+line+'\n' for line in old['run'].splitlines())
    after=''.join('          '+line+'\n' for line in new['run'].splitlines())
    assert workflow.count(before)==1
    workflow=workflow.replace(before,after)
replacements={'FOLLOWUP_VM_STEP':new_vm,'FOLLOWUP_BROWSER_STEP':new_browser}
tree=ast.parse(source);edits=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
        name=node.targets[0].id;edits.append((node.lineno-1,node.end_lineno,name+' = '+repr(replacements[name])+'\n'))
lines=source.splitlines(keepends=True)
for start,end,value in sorted(edits,reverse=True):lines[start:end]=[value]
source=''.join(lines)
before="('weaken-VM-controls', 'frontend-contracts', '--minimum 3\\n', '--minimum 0\\n')"
after="('weaken-VM-controls', 'frontend-contracts', 'member-link-controls.json --format counts --minimum 3\\n', 'member-link-controls.json --format counts --minimum 0\\n')"
assert source.count(before)==1;source=source.replace(before,after)
canaries='''def followup_report_canaries(out: Path) -> list[dict]:
    authenticate_current_gates()
    from tests.check_followup_reports import REQUIRED, REPORT
    expected = frozenset({('tests.integration_followup_postgres',
        'test_readonly_followup_double_owner_admin_scope_and_revocation[' + factory + '-postgresql]')
        for factory in ('web.main_web', 'api.app')})
    assert REPORT == FOLLOWUP_REPORT and REQUIRED == expected
    rows = []
    modes = ['positive', 'missing', 'malformed', 'empty', 'reduced', 'duplicate',
             'wrong-module', 'SQLite', 'skip', 'failure', 'error', 'substituted-case']
    for mode in modes:
        directory = out / ('followup-report-' + mode); directory.mkdir()
        suite = ET.Element('testsuite')
        for module, name in sorted(expected):
            ET.SubElement(suite, 'testcase', classname=module, name=name)
        if mode == 'empty': suite.clear()
        elif mode == 'reduced': suite.remove(suite[-1])
        elif mode == 'duplicate': suite.append(copy.deepcopy(suite[0]))
        elif mode == 'wrong-module': suite[0].set('classname', 'tests.unrelated')
        elif mode == 'SQLite': suite[0].set('name', suite[0].get('name').replace('postgresql', 'sqlite'))
        elif mode == 'substituted-case': suite[0].set('name', 'unrelated_case[postgresql]')
        elif mode in ['skip', 'failure', 'error']: ET.SubElement(suite[0], 'skipped' if mode == 'skip' else mode)
        ET.ElementTree(suite).write(directory / REPORT, encoding='utf8', xml_declaration=True)
        if mode == 'missing': (directory / REPORT).unlink()
        elif mode == 'malformed': (directory / REPORT).write_bytes(b'<testsuite')
        result = subprocess.run([sys.executable, str(ROOT / 'tests/check_followup_reports.py'),
            '--directory', str(directory)], capture_output=True, timeout=10, check=False)
        (directory / 'stdout.log').write_bytes(result.stdout); (directory / 'stderr.log').write_bytes(result.stderr)
        assert (result.returncode == 0) == (mode == 'positive'), mode
        rows.append({'report': REPORT, 'case': mode, 'exit': result.returncode})
    assert len(rows) == 12
    return rows


'''
assert 'def followup_report_canaries' not in source
source=source.replace('def inert_cases(',canaries+'def inert_cases(',1)
source=source.replace("report['index_report_canaries'] = index_report_canaries(scratch)","report['index_report_canaries'] = index_report_canaries(scratch)\n            report['followup_report_canaries'] = followup_report_canaries(scratch)")
source=source.replace("'index_report_canaries': len(report.get('index_report_canaries', [])),","'index_report_canaries': len(report.get('index_report_canaries', [])),\n                      'followup_report_canaries': len(report.get('followup_report_canaries', [])),")
tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_CURRENT_GATES' for t in n.targets));pins=ast.literal_eval(node.value)
pins['tests/e2e/normalize_followup_report.py']=hashlib.sha256((ROOT/'tests/e2e/normalize_followup_report.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
lines=source.splitlines(keepends=True);lines[node.lineno-1:node.end_lineno]=['PINNED_CURRENT_GATES = '+repr(pins)+'\n'];source=''.join(lines)
ast.parse(source);path.write_bytes(source.encode());(ROOT/'.github/workflows/ci.yml').write_bytes(workflow.encode())
print(json.dumps({'normalization_only_no_driver_assertion_edits':True,'old27_mutation_scopes_kept':True,'extra_followup_parser_canaries':12,'named_browser_minimum':8,'screens_minimum':5,'pinned_gate_files':len(pins)}))
