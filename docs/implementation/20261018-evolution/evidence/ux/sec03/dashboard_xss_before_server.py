"""Own frozen application/SQLite browser fixture for the dashboard drawer probe."""
from pathlib import Path
import hashlib,json,os,sys
sys.dont_write_bytecode=True
SOURCE=Path(__file__).parent/"dashboard-xss-checkout"
sys.path.insert(0,str(SOURCE))
from tests.isolation import prepare_environment,block_external_sockets
for key in ("_METODOBASE_TEST_ROOT","METODOBASE_TEST_DATABASE_URL","METODOBASE_TEST_REDIS_URL","PYTEST_XDIST_WORKER"):
    os.environ.pop(key,None)
temporary=prepare_environment(discard_inherited=True).resolve()
block_external_sockets()
os.environ["BASE_URL"]="http://127.0.0.1:8774"
os.environ["CORS_ORIGINS"]="http://127.0.0.1:8774,http://testserver"
from sqlalchemy.orm import Session
from web.database.engine import get_engine
from web.database.models import Base,Usuario,UserRole
from web.auth import hash_password
engine=get_engine()
assert engine.dialect.name=="sqlite" and Path(engine.url.database).resolve().is_relative_to(temporary)
Base.metadata.create_all(engine)
with Session(engine) as db:
    for suffix in ("owner","other"):
        db.add(Usuario(id="synthetic-drawer-"+suffix,email="drawer-"+suffix+"@example.invalid",
            nombre="Synthetic "+suffix,apellido="",password_hash=hash_password("Synthetic-Drawer-Only-2026!"),
            tipo="gym",role=UserRole.OWNER,activo=True))
    db.commit()
from web.main_web import create_app
sources=["web/templates/dashboard.html","web/static/js/main.js","web/static/js/api.js","web/static/js/components.js",
    "web/static/js/auth-guard.js","web/routes/clientes.py","web/schemas.py","api/schemas.py","web/profile_schemas.py",
    "web/database/repository.py","web/database/models.py","web/auth.py","web/auth_deps.py","web/main_web.py",
    "web/middleware/security_headers.py","web/routes/stats.py","api/routes/stats.py","tests/isolation.py",
    "requirements_web-windows.lock","requirements-test-windows.lock"]
snapshot={"source_commit":"2f8b7f9617503240432e5f6b981f2730c0c9c30e","scope":"Own detached committed source, excluding main stats WIP; own temporary SQLite, real auth and CRUD, providers/sockets external blocked",
    "tables":len(Base.metadata.tables),"port":8774,"sources":[{"path":name,"sha256":hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()} for name in sources]}
(Path(__file__).parent/"dashboard-xss-startup-source.json").write_text(json.dumps(snapshot,indent=2),encoding="utf8")
print("Dedicated synthetic dashboard fixture ready",flush=True)
import uvicorn
uvicorn.run(create_app(),host="127.0.0.1",port=8774,log_level="warning")
