"""Preparation-only source/recipe checks; they never claim a current33 run."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

from tests.ci_google33.workflow import expected_workflow
from tests.run_reviewed_ci30 import require

ROOT=Path(__file__).resolve().parents[2]
BASE='6f822ff50d93e01bb10249556a9bfc4e1a3b246b'


def verify_workflow(value):
    require(value==expected_workflow(),'A required versioned/current CI gate or artifact boundary differs')


def validate_frames():
    result={}
    for filename in ['adaptation-map.json','compatibility-map.json','browser-frame-map.json']:
        mapping=json.loads((ROOT/'tests/ci_google33'/filename).read_bytes())
        for name,entry in mapping.items():
            current=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            require(hashlib.sha256(current).hexdigest()==entry['current_normalized_sha256'],'Prepared framing bytes differ')
            if 'source' in entry:
                original=subprocess.check_output(['git','--no-replace-objects','show',entry.get('source_commit',BASE)+':'+entry['source']],cwd=ROOT).replace(b'\r\n',b'\n')
                require(hashlib.sha256(original).hexdigest()==entry['source_normalized_sha256'],'Original frame source differs')
                if entry.get('full_inverse_exact'):
                    inverse=current.decode()
                    for before,after in reversed(entry.get('witness_additions',[])):inverse=inverse.replace(after,before)
                    if entry.get('addition'):inverse=inverse.replace(entry['addition'][1],entry['addition'][0])
                    for before,after in reversed(entry['framing_pairs']):inverse=inverse.replace(after,before)
                    require(inverse.encode()==original,'Complete frame inverse differs')
                if entry.get('all_function_AST_exact'):
                    functions=lambda raw:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
                    require(functions(current)==functions(original),'An existing function body or assertion changed')
            for original_name,source in entry.get('sources',{}).items():
                raw=(ROOT/original_name).read_bytes().replace(b'\r\n',b'\n')
                require(hashlib.sha256(raw).hexdigest()==source['normalized_sha256'],'An imported original business source changed')
                tree=ast.parse(current);module=original_name[:-3].replace('/','.')
                imported={alias.name for n in tree.body if isinstance(n,ast.ImportFrom) and n.module==module for alias in n.names if alias.name.startswith('test_')}
                require(imported==set(source['functions']),'A wrapper omitted or substituted original business criteria')
            result[name]={'source_bytes_authenticated':True,'full_inverse_or_original_import_mapping':True}
    return result
