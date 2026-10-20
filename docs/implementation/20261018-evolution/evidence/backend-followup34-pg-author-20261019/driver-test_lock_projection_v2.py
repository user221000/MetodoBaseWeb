from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
import uuid
from tests.followup34_http import followup_db,followup_http,create
from web.database.models import Usuario


def test_moved_assignee_lock_never_fetches_other_context_contact_fields(followup_http,record_property):
    c=followup_http;response,_,_=create(c);assert response.status_code==200
    identifier=response.json()["task"]["id"]
    with Session(c["admin"]) as db:
        target=db.get(Usuario,c["member"])
        target.team_gym_id=None;target.nombre="Synthetic other-context name";db.commit()
    sql=[];loaded=[]
    def capture(connection,cursor,statement,parameters,context,many):
        normalized=statement.upper()
        if "FROM USUARIOS" in normalized and "ORDER BY USUARIOS.ID" in normalized:
            sql.append(normalized.split("FROM USUARIOS",1)[0])
    def row_loaded(row,context):
        if row.id==c["member"]:
            loaded.append(set(inspect(row).dict)-{"_sa_instance_state"})
    event.listen(c["engine"],"before_cursor_execute",capture)
    event.listen(Usuario,"load",row_loaded)
    try:
        cancelled=c["raw"].post("/api/seguimiento/tareas/"+identifier+"/cancelar",json={"expected_version":1,"reason":"no_longer_applicable","confirm":True},headers={"Idempotency-Key":str(uuid.uuid4())})
    finally:
        event.remove(c["engine"],"before_cursor_execute",capture)
        event.remove(Usuario,"load",row_loaded)
        record_property("moved_loaded_fields", __import__("json").dumps([sorted(row) for row in loaded]))
        record_property("lock_projection_columns", __import__("json").dumps(sql))
    assert cancelled.status_code==200
    assert cancelled.json()["task"]["responsible"]=={"id":c["member"],"display_name":None,"eligible":False}
    assert sql and loaded, "Real lock SELECT and moved row must both be observed"
    private={"nombre","email","password_hash"}
    assert all(private.isdisjoint(fields) for fields in loaded), "Foreign-context columns were loaded into the lock Session"
    assert all(not any("USUARIOS."+column.upper() in query for column in private) for query in sql), "Lock SELECT fetched unnecessary contact columns"
