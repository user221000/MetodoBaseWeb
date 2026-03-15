"""
Tests de licenciamiento (flujo key_v2).
"""

import json
from datetime import datetime, timedelta

from core.licencia import GestorLicencias


def _gestor_tmp(tmp_path, monkeypatch) -> GestorLicencias:
    monkeypatch.setattr(GestorLicencias, "ARCHIVO_CONFIG", str(tmp_path / "licencia_config.json"))
    monkeypatch.setattr(GestorLicencias, "ARCHIVO_LICENCIA", str(tmp_path / "licencia.lic"))
    monkeypatch.setattr(GestorLicencias, "SALT_MASTER", "TEST_SALT")
    return GestorLicencias()


def test_emisor_deshabilitado_por_defecto(monkeypatch):
    monkeypatch.delenv("METODO_BASE_EMISOR", raising=False)
    assert GestorLicencias.emisor_habilitado() is False


def test_emisor_habilitado_con_flag(monkeypatch):
    monkeypatch.setenv("METODO_BASE_EMISOR", "1")
    assert GestorLicencias.emisor_habilitado() is True


def test_key_v2_activa_y_valida(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=6)

    ok, _ = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key,
        periodo_meses=6,
    )
    assert ok is True

    valida, _, lic = gestor.validar_licencia()
    assert valida is True
    assert lic is not None
    assert lic.get("formato") == "key_v2"
    assert lic.get("periodo_meses") == 6
    assert "activation_key" not in lic
    assert "key_fingerprint" in lic


def test_key_invalida_no_activa(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    ok, msg = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion="MB06-XXXX-XXXX-XXXX-XXXX",
        periodo_meses=6,
    )
    assert ok is False
    assert "Key invalida" in msg


def test_key_de_3_meses_no_vale_para_12(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key_3 = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=3)

    ok, msg = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key_3,
        periodo_meses=12,
    )
    assert ok is False
    assert "Key invalida" in msg


def test_detecta_expiracion_en_v2(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    periodo = 3
    key_raw = gestor._generar_key_raw(id_inst, periodo)

    fecha_emision = datetime.now() - timedelta(days=130)
    fecha_exp = gestor._sumar_meses(fecha_emision, periodo)
    sello = gestor._generar_sello_v2(
        nombre_gym="Gym Test",
        id_instalacion=id_inst,
        fecha_emision=fecha_emision,
        fecha_expiracion=fecha_exp,
        periodo_meses=periodo,
        key_raw=key_raw,
    )

    lic = {
        "formato": "key_v2",
        "nombre_gym": "Gym Test",
        "id_instalacion": id_inst,
        "key_fingerprint": gestor._fingerprint_key(key_raw),
        "periodo_meses": periodo,
        "fecha_emision": fecha_emision.isoformat(),
        "fecha_expiracion": fecha_exp.isoformat(),
        "activa": True,
        "sello": sello,
    }
    with open(gestor.ruta_licencia, "w", encoding="utf-8") as f:
        json.dump(lic, f, indent=2, ensure_ascii=False)

    valida, msg, _ = gestor.validar_licencia()
    assert valida is False
    assert "expirada" in msg.lower()


def test_archivo_licencia_no_guarda_key_plana(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=9)
    ok, _ = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key,
        periodo_meses=9,
    )
    assert ok is True

    with open(gestor.ruta_licencia, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "activation_key" not in data
    assert "key_fingerprint" in data
    assert data["key_fingerprint"] != key


def test_guarda_plan_comercial_y_canal_venta(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=6)

    ok, _ = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key,
        periodo_meses=6,
        plan_comercial="semestral",
        canal_venta="whatsapp",
    )
    assert ok is True

    with open(gestor.ruta_licencia, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("plan_comercial") == "semestral"
    assert data.get("canal_venta") == "whatsapp"


def test_obtener_estado_licencia_expone_campos_comerciales(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=12)

    ok, _ = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key,
        periodo_meses=12,
        plan_comercial="anual",
    )
    assert ok is True

    estado = gestor.obtener_estado_licencia()
    assert estado["activa"] is True
    assert estado["plan_comercial"] == "anual"
    assert estado["plan_label"] == "Plan Anual"
    assert estado["fecha_corte"] != ""
    assert 300 <= int(estado["dias_restantes"]) <= 365


def test_plan_semestral_usa_180_dias_exactos(tmp_path, monkeypatch):
    gestor = _gestor_tmp(tmp_path, monkeypatch)
    id_inst = gestor.obtener_id_instalacion()
    key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=6)

    ok, _ = gestor.activar_licencia_con_key(
        nombre_gym="Gym Test",
        key_activacion=key,
        periodo_meses=6,
        plan_comercial="semestral",
    )
    assert ok is True

    with open(gestor.ruta_licencia, "r", encoding="utf-8") as f:
        data = json.load(f)

    fecha_emision = datetime.fromisoformat(data["fecha_emision"])
    fecha_expiracion = datetime.fromisoformat(data["fecha_expiracion"])
    assert (fecha_expiracion - fecha_emision).days == 180
