from pathlib import Path
import ast,hashlib,json,subprocess,difflib
R=Path("F:/mb-followup34-20261019");O=Path(__file__).parent
base="54e511b3ac8636c6ffb6c20cd3b4f8d86922ad2e"
git=lambda *a:subprocess.check_output(["git","--no-replace-objects",*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest()
canonical=lambda b:b.replace(b"\r\n",b"\n")
checks={}
for name in ("api/app.py","web/main_web.py","web/database/tenant_context.py","web/database/schema_control.py","web/middleware/csrf.py","web/database/models.py"):
 old=canonical(git("show",base+":"+name));new=canonical((R/name).read_bytes())
 ops=list(difflib.SequenceMatcher(a=old.splitlines(),b=new.splitlines(),autojunk=False).get_opcodes())
 assert all(tag in ("equal","insert") for tag,*_ in ops),name
 checks[name]={"base_sha256":sha(old),"current_raw_sha256":sha((R/name).read_bytes()),"current_gitLF_sha256":sha(new),"old_lines_exact":True,"added_lines":sum(j2-j1 for tag,i1,i2,j1,j2 in ops if tag=="insert")}
old=ast.parse(git("show",base+":web/database/models.py"));new=ast.parse((R/"web/database/models.py").read_bytes())
new.body=[x for x in new.body if not(isinstance(x,ast.ClassDef) and x.name.startswith("Notification")) and not(isinstance(x,ast.ImportFrom) and x.module=="web.database.notification_schema_v1")]
u=next(x for x in new.body if isinstance(x,ast.ClassDef) and x.name=="Usuario")
u.body=[x for x in u.body if not(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="notification_contact_version" for t in x.targets))]
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
name="web/middleware/security_headers.py";s=canonical((R/name).read_bytes()).decode()
for line in ("from web.notification_paths import is_notification_private\n","        notification_api = is_notification_private(request.url.path)\n","                    and not notification_api\n","                or notification_api\n"):
 assert line in s;s=s.replace(line,"",1)
s=s.replace("elif notification_api or followup_api","elif followup_api",1).replace(" or notification_api or export_api"," or export_api",1)
assert s.encode()==canonical(git("show",base+":"+name));checks[name]={"full_inverse_gitLF":True,"base_sha256":sha(s.encode()),"current_raw_sha256":sha((R/name).read_bytes())}
imports=json.loads((O/"root35-handoff-import.json").read_text())
oldtargets=git("ls-tree","-r","--name-only",base,"web/database/alembic/schema_targets").decode().splitlines()
root34="web/database/alembic/schema_targets/20261019_followup_tasks_postgresql.json"
for name in oldtargets:
 if name!=root34:assert canonical((R/name).read_bytes())==git("show",base+":"+name),name
for name,receipt in imports["paths"].items():assert sha((R/name).read_bytes())==receipt["after"]
# Inverse chain to original34 is authenticated by a closed before receipt.
prepared=(O/"integration_notifications36_restore.prepared.py").read_bytes()
inverse=json.loads((O/"restore36-full-inverse.json").read_text())
assert sha(prepared)==inverse["new36_sha256"] and inverse["full_inverse_to_original_raw"]
current=(R/"tests/integration_notifications36_restore.py").read_text(encoding="utf-8")
normalized=current.replace("  # noqa: F401 -- full historical oracle","").replace("| FOLLOWUP_TABLES | set(NOTIFICATION_TABLES)\n","| FOLLOWUP_TABLES | NOTIFICATION_TABLES\n",1)
assert normalized.encode()==prepared
assert sha((R/"tests/integration_followup34_restore.py").read_bytes())==inverse["source34_raw_sha256"]
result={"base":base,"compatibility":checks,"old_model_AST_after_removing_only_new_metadata":True,"old_target_blobs_checked":len(oldtargets),"old_targets_unchanged_except_authorized_ROOT34":True,"restore_inverse_chain":inverse,"restore_current_to_prepared_inverse_exact":True,"root35_import_receipt":imports,"historical_migrations_fixtures_edited":False}
with (O/"final-preservation.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2)
print(json.dumps({"compatibility_files":len(checks),"old_targets":len(oldtargets),"restore_inverse_chain":True}))
