from core.exportador_multi import filtrar_campos_cliente_export


def test_export_filter_removes_sensitive_fields():
    cliente = {
        "nombre": "Ana",
        "edad": 30,
        "peso_kg": 70,
        "estatura_cm": 165,
        "grasa_corporal_pct": 20,
        "objetivo": "deficit",
        "nivel_actividad": "moderada",
        "email": "ana@dominio.com",
        "password_hash": "hash",
    }
    filtrado = filtrar_campos_cliente_export(cliente)
    assert "email" not in filtrado
    assert "password_hash" not in filtrado
    assert filtrado["nombre"] == "Ana"
