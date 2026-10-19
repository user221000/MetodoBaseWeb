from sqlalchemy import event

from tests.test_billing_integrity import billing_case  # noqa: F401


def test_history_query_count_does_not_grow_with_plan_rows(billing_case):
    from web.database.models import PlanGenerado
    client, factory, principal = billing_case
    counts = []
    for total in (1, 25):
        with factory() as db:
            previous = db.query(PlanGenerado).count()
            for _ in range(total - previous):
                db.add(PlanGenerado(gym_id=principal['id'], id_cliente='billing-profile', plan_json='{}'))
            db.commit()
        statements = []
        engine = factory.kw['bind']
        def observed(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                statements.append(statement)
        event.listen(engine, 'before_cursor_execute', observed)
        try:
            response = client.get('/api/usuario/historial')
        finally:
            event.remove(engine, 'before_cursor_execute', observed)
        assert response.status_code == 200
        assert len(response.json()['planes']) == total
        assert len([query for query in statements if 'JOIN clientes' in query]) == 1
        counts.append(len(statements))
    assert counts == [2, 2]
