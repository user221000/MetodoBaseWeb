from pathlib import Path
import ast,hashlib,json
ROOT=Path(r'F:/mb-progress-retirement-ui-20261019');PRIVATE=Path(r'C:/Users/Consu/AppData/Local/Temp/metodobase-sec-gitleaks-peer-private-20261019')
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=json.loads((PRIVATE/'unresolved-v2.STRUCTURAL.json').read_bytes());proofs=[];shapes=[]
for row in rows:
    if row['value_type']!='other':continue
    blob=(ROOT/row['file']).read_bytes();assert sha(blob)==row['file_sha256']
    tree=ast.parse(blob);parents={c:p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    literals=[n for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and sha(n.value.encode())==row['matched_value_sha256'] and n.lineno==row['line']]
    assert len(literals)==1;n=literals[0];parent=parents[n]
    if row['file']=='tests/test_client_link_models.py':
        assert isinstance(parent,ast.keyword)
        call=parents[parent];assert isinstance(call,ast.Call)
        assert (row['line'],parent.arg,ast.unparse(call.func)) in {(23,'key','StoredObject'),(36,'object_key','dict')}
        sqlite=[x for x in ast.walk(tree) if isinstance(x,ast.Call) and ast.unparse(x.func)=='create_engine' and x.args and isinstance(x.args[0],ast.BinOp) and isinstance(x.args[0].op,ast.Add) and isinstance(x.args[0].left,ast.Constant) and x.args[0].left.value=='sqlite:///' and 'tmp_path' in ast.unparse(x.args[0].right)]
        assert len(sqlite)==1
        assert sum(isinstance(x,ast.Constant) and isinstance(x.value,str) and x.value==n.value for x in ast.walk(tree))==2
        proof={'kind':'synthetic_temporary_SQLite_database_object_locator','model_field':parent.arg,'model_or_fixture_constructor':ast.unparse(call.func),'same_literal_used_only_in_two_fixture_positions':True,'SQLite_uri_plus_tmp_path_verified':True,'not_an_authentication_or_provider_credential':'Constant identifies fixture StoredObject and publication FK, no live object store or credential validation is exercised.'}
    else:
        assert row['file'].endswith('/checkpoint116-driver.py')
        assert isinstance(parent,ast.Call) and ast.unparse(parent.func)=='capture' and n in parent.args
        position=parent.args.index(n)
        definition=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='capture')
        args=[a.arg for a in definition.args.args]
        calls=[ast.unparse(x.func) for x in ast.walk(definition) if isinstance(x,ast.Call)]
        scrub=ast.parse(ast.unparse(definition))
        for x in ast.walk(scrub):
            if isinstance(x,ast.Constant) and isinstance(x.value,str):x.value='<literal bytes='+str(len(x.value.encode()))+' sha256='+sha(x.value.encode())+'>'
        shapes.append({'file':row['file'],'capture_args':args,'capture_calls':calls,'capture_function_string_values_removed':ast.unparse(scrub)})
        proof={'kind':'local_capture_output_label_literal','call_argument_position':position,'capture_parameter':args[position],'capture_definition_ast_sha256':sha(ast.dump(definition).encode()),'pending_manual_data_flow_review':True}
    proofs.append({**row,'proof':proof})
(PRIVATE/'literal-proofs.pending.STRUCTURAL.json').write_text(json.dumps(proofs,indent=2)+'\n',encoding='utf8')
print(json.dumps({'literal_proofs':len(proofs),'capture_data_flow':shapes},indent=2))
