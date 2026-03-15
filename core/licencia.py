"""
Sistema de licenciamiento por gimnasio.

Flujo endurecido:
- La app no auto-genera licencias.
- La activacion se hace con una key pre-generada por el proveedor.
- Los periodos permitidos son 3, 6, 9 y 12 meses.
"""

import base64
import calendar
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from config.constantes import APP_DATA_DIR, CARPETA_CONFIG


class GestorLicencias:
    """
    Gestiona licencias de software por gimnasio.

    Las licencias nuevas usan formato ``key_v2`` y se validan con:
    - ID de instalacion
    - Key de activacion generada por proveedor
    - Periodo en meses (3/6/9/12)
    - Sello interno de integridad
    """

    ARCHIVO_LICENCIA = os.path.join(APP_DATA_DIR, "licencia.lic")
    ARCHIVO_CONFIG = os.path.join(CARPETA_CONFIG, "licencia_config.json")
    SALT_MASTER: str = os.environ.get("METODO_BASE_SALT", "METODO_BASE_2026_CH")
    PERIODOS_VALIDOS_MESES = (3, 6, 9, 12)
    PLANES_COMERCIALES = {
        "semestral": {"periodo_meses": 6, "duracion_dias": 180, "label": "Plan Semestral"},
        "anual": {"periodo_meses": 12, "duracion_dias": 365, "label": "Plan Anual"},
    }

    def __init__(self) -> None:
        self.ruta_licencia = Path(self.ARCHIVO_LICENCIA)
        self.ruta_config = Path(self.ARCHIVO_CONFIG)
        self.ruta_config.parent.mkdir(parents=True, exist_ok=True)
        if not self.ruta_config.exists():
            self._crear_config_inicial()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _crear_config_inicial(self) -> None:
        config = {
            "id_instalacion": str(uuid.uuid4()),
            "fecha_primera_instalacion": datetime.now().isoformat(),
            "version": "1.0.0",
        }
        with open(self.ruta_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _obtener_id_instalacion(self) -> str:
        try:
            with open(self.ruta_config, "r", encoding="utf-8") as f:
                return json.load(f).get("id_instalacion", "")
        except (json.JSONDecodeError, OSError):
            self._crear_config_inicial()
            with open(self.ruta_config, "r", encoding="utf-8") as f:
                return json.load(f)["id_instalacion"]

    @staticmethod
    def _normalizar_key(key: str) -> str:
        return "".join(ch for ch in str(key).upper() if ch.isalnum())

    @staticmethod
    def _formatear_key(raw_key: str) -> str:
        grupos = [raw_key[i : i + 4] for i in range(0, len(raw_key), 4)]
        return "-".join(grupos)

    @staticmethod
    def _sumar_meses(fecha: datetime, meses: int) -> datetime:
        mes_idx = fecha.month - 1 + meses
        anio = fecha.year + mes_idx // 12
        mes = mes_idx % 12 + 1
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        dia = min(fecha.day, ultimo_dia)
        return fecha.replace(year=anio, month=mes, day=dia)

    @classmethod
    def _normalizar_plan_comercial(cls, plan_comercial: str | None) -> str:
        plan = (plan_comercial or "").strip().lower()
        return plan if plan in cls.PLANES_COMERCIALES else ""

    @classmethod
    def _inferir_plan_comercial(cls, periodo_meses: int, duracion_dias: int | None = None) -> str:
        for key, meta in cls.PLANES_COMERCIALES.items():
            if periodo_meses == int(meta["periodo_meses"]):
                return key
        if duracion_dias is not None:
            for key, meta in cls.PLANES_COMERCIALES.items():
                if duracion_dias == int(meta["duracion_dias"]):
                    return key
        return ""

    def _generar_hash(self, nombre_gym: str, id_instalacion: str, fecha_expiracion: str) -> str:
        datos = f"{nombre_gym}|{id_instalacion}|{fecha_expiracion}|{self.SALT_MASTER}"
        return hashlib.sha256(datos.encode("utf-8")).hexdigest()

    def _generar_key_raw(self, id_instalacion: str, periodo_meses: int) -> str:
        payload = f"MBv2|{id_instalacion}|{periodo_meses}|{self.SALT_MASTER}"
        digest = hmac.new(
            self.SALT_MASTER.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        token = base64.b32encode(digest[:10]).decode("ascii").rstrip("=").upper()
        return f"MB{periodo_meses:02d}{token}"

    def _generar_sello_v2(
        self,
        nombre_gym: str,
        id_instalacion: str,
        fecha_emision: datetime,
        fecha_expiracion: datetime,
        periodo_meses: int,
        key_raw: str,
    ) -> str:
        payload = (
            f"LICv2|{nombre_gym}|{id_instalacion}|{fecha_emision.isoformat()}|"
            f"{fecha_expiracion.isoformat()}|{periodo_meses}|{key_raw}|{self.SALT_MASTER}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _fingerprint_key(self, key_raw: str) -> str:
        payload = f"KEYFP|{key_raw}|{self.SALT_MASTER}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _migrar_v2_sin_key(self, lic: Dict, key_raw: str) -> None:
        """Migra archivo v2 para no almacenar activation_key en claro."""
        if "activation_key" not in lic:
            return
        lic["key_fingerprint"] = self._fingerprint_key(key_raw)
        lic.pop("activation_key", None)
        try:
            with open(self.ruta_licencia, "w", encoding="utf-8") as f:
                json.dump(lic, f, indent=2, ensure_ascii=False)
        except OSError:
            # Si no se puede persistir, no bloqueamos el uso; la validacion ya paso.
            pass

    @staticmethod
    def emisor_habilitado() -> bool:
        """
        Habilita emision de keys solo en entorno de proveedor.

        Reglas:
        - En binario congelado (cliente) siempre bloqueado.
        - En desarrollo, requiere `METODO_BASE_EMISOR=1`.
        """
        if getattr(sys, "frozen", False):
            return False
        return os.environ.get("METODO_BASE_EMISOR", "").strip() == "1"

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def obtener_id_instalacion(self) -> str:
        """ID que debe compartir el cliente para que generes la key."""
        return self._obtener_id_instalacion()

    def generar_key_activacion(self, id_instalacion_cliente: str, periodo_meses: int) -> str:
        """
        Genera la key de activacion que escribira el proveedor en la UI.
        """
        if not id_instalacion_cliente or not id_instalacion_cliente.strip():
            raise ValueError("El ID de instalacion no puede estar vacio")
        if periodo_meses not in self.PERIODOS_VALIDOS_MESES:
            raise ValueError("Periodo invalido. Usa 3, 6, 9 o 12 meses.")

        raw_key = self._generar_key_raw(id_instalacion_cliente.strip(), periodo_meses)
        return self._formatear_key(raw_key)

    def activar_licencia_con_key(
        self,
        nombre_gym: str,
        key_activacion: str,
        periodo_meses: int,
        email_contacto: str = "",
        telefono_contacto: str = "",
        plan_comercial: str | None = None,
        canal_venta: str = "",
    ) -> Tuple[bool, str]:
        """
        Activa licencia local validando key + periodo para esta instalacion.
        """
        if periodo_meses not in self.PERIODOS_VALIDOS_MESES:
            return False, "Periodo invalido. Usa 3, 6, 9 o 12 meses."
        if not nombre_gym or not nombre_gym.strip():
            return False, "El nombre del gimnasio no puede estar vacio."
        if not key_activacion or not key_activacion.strip():
            return False, "Debes ingresar una key de activacion."

        plan = self._normalizar_plan_comercial(plan_comercial)
        if not plan:
            plan = self._inferir_plan_comercial(periodo_meses)
        if plan:
            periodo_plan = int(self.PLANES_COMERCIALES[plan]["periodo_meses"])
            if periodo_plan != periodo_meses:
                return False, "El plan comercial no coincide con el periodo seleccionado."

        id_instalacion = self._obtener_id_instalacion()
        key_esperada_raw = self._generar_key_raw(id_instalacion, periodo_meses)
        key_ingresada_raw = self._normalizar_key(key_activacion)
        if not hmac.compare_digest(key_ingresada_raw, key_esperada_raw):
            return False, "Key invalida para esta instalacion o para el periodo seleccionado."

        fecha_emision = datetime.now()
        if plan:
            dias_plan = int(self.PLANES_COMERCIALES[plan]["duracion_dias"])
            fecha_expiracion = fecha_emision + timedelta(days=dias_plan)
        else:
            fecha_expiracion = self._sumar_meses(fecha_emision, periodo_meses)
        sello = self._generar_sello_v2(
            nombre_gym=nombre_gym.strip(),
            id_instalacion=id_instalacion,
            fecha_emision=fecha_emision,
            fecha_expiracion=fecha_expiracion,
            periodo_meses=periodo_meses,
            key_raw=key_esperada_raw,
        )

        licencia = {
            "formato": "key_v2",
            "nombre_gym": nombre_gym.strip(),
            "id_instalacion": id_instalacion,
            "key_fingerprint": self._fingerprint_key(key_esperada_raw),
            "periodo_meses": periodo_meses,
            "plan_comercial": plan,
            "canal_venta": (canal_venta or "").strip(),
            "fecha_emision": fecha_emision.isoformat(),
            "fecha_expiracion": fecha_expiracion.isoformat(),
            "email_contacto": email_contacto,
            "telefono_contacto": telefono_contacto,
            "version_software": "1.0.0",
            "activa": True,
            "sello": sello,
        }

        with open(self.ruta_licencia, "w", encoding="utf-8") as f:
            json.dump(licencia, f, indent=2, ensure_ascii=False)
        return True, f"Licencia activada hasta {fecha_expiracion.strftime('%Y-%m-%d')}"

    def generar_licencia_gym(
        self,
        nombre_gym: str,
        duracion_dias: int = 365,
        email_contacto: str = "",
        telefono_contacto: str = "",
        id_instalacion_cliente: str = None,
        plan_comercial: str | None = None,
        canal_venta: str = "",
    ) -> str:
        """
        Compatibilidad legacy: genera licencia por dias.
        """
        if not nombre_gym or not nombre_gym.strip():
            raise ValueError("El nombre del gimnasio no puede estar vacio")
        if duracion_dias <= 0:
            raise ValueError("La duracion debe ser mayor a 0 dias")

        id_instalacion = id_instalacion_cliente or self._obtener_id_instalacion()
        fecha_emision = datetime.now()
        fecha_expiracion = fecha_emision + timedelta(days=duracion_dias)

        hash_licencia = self._generar_hash(
            nombre_gym,
            id_instalacion,
            fecha_expiracion.strftime("%Y-%m-%d"),
        )

        licencia = {
            "nombre_gym": nombre_gym.strip(),
            "id_instalacion": id_instalacion,
            "clave": hash_licencia,
            "plan_comercial": (
                self._normalizar_plan_comercial(plan_comercial)
                or self._inferir_plan_comercial(periodo_meses=0, duracion_dias=duracion_dias)
            ),
            "canal_venta": (canal_venta or "").strip(),
            "fecha_emision": fecha_emision.isoformat(),
            "fecha_expiracion": fecha_expiracion.isoformat(),
            "duracion_dias": duracion_dias,
            "email_contacto": email_contacto,
            "telefono_contacto": telefono_contacto,
            "version_software": "1.0.0",
            "activa": True,
        }

        with open(self.ruta_licencia, "w", encoding="utf-8") as f:
            json.dump(licencia, f, indent=2, ensure_ascii=False)

        return hash_licencia

    def _validar_licencia_v2(self, lic: Dict) -> Tuple[bool, str, Optional[Dict]]:
        requeridos = (
            "formato",
            "nombre_gym",
            "id_instalacion",
            "periodo_meses",
            "fecha_emision",
            "fecha_expiracion",
            "activa",
            "sello",
        )
        for campo in requeridos:
            if campo not in lic:
                return False, f"Licencia corrupta: falta campo '{campo}'", None

        if lic.get("formato") != "key_v2":
            return False, "Licencia invalida: formato desconocido.", None
        if not lic.get("activa", False):
            return False, "Licencia desactivada. Contacta a soporte.", None
        if lic["id_instalacion"] != self._obtener_id_instalacion():
            return False, "Licencia invalida: ID de instalacion no coincide.", None

        try:
            periodo_meses = int(lic["periodo_meses"])
        except (TypeError, ValueError):
            return False, "Licencia corrupta: periodo invalido.", None
        if periodo_meses not in self.PERIODOS_VALIDOS_MESES:
            return False, "Licencia invalida: periodo no permitido.", None

        plan_guardado = self._normalizar_plan_comercial(lic.get("plan_comercial", ""))
        if lic.get("plan_comercial") and not plan_guardado:
            return False, "Licencia invalida: plan_comercial desconocido.", None
        if plan_guardado:
            periodo_plan = int(self.PLANES_COMERCIALES[plan_guardado]["periodo_meses"])
            if periodo_meses != periodo_plan:
                return False, "Licencia invalida: plan comercial no coincide con periodo.", None

        key_esperada_raw = self._generar_key_raw(lic["id_instalacion"], periodo_meses)
        # Flujo endurecido: no guardamos key en claro, solo huella.
        if "key_fingerprint" in lic:
            fp_esperado = self._fingerprint_key(key_esperada_raw)
            if not hmac.compare_digest(str(lic["key_fingerprint"]), fp_esperado):
                return False, "Licencia invalida: huella de key no corresponde.", None
        # Compatibilidad con archivos v2 anteriores que guardaban activation_key.
        elif "activation_key" in lic:
            key_guardada_raw = self._normalizar_key(lic["activation_key"])
            if not hmac.compare_digest(key_guardada_raw, key_esperada_raw):
                return False, "Licencia invalida: key no corresponde al equipo o periodo.", None
            self._migrar_v2_sin_key(lic, key_esperada_raw)
        else:
            return False, "Licencia corrupta: falta key_fingerprint.", None

        try:
            fecha_emision = datetime.fromisoformat(lic["fecha_emision"])
            fecha_exp = datetime.fromisoformat(lic["fecha_expiracion"])
        except ValueError:
            return False, "Licencia corrupta: fechas invalidas.", None

        if plan_guardado:
            dias_plan = int(self.PLANES_COMERCIALES[plan_guardado]["duracion_dias"])
            fecha_exp_esperada = fecha_emision + timedelta(days=dias_plan)
        else:
            fecha_exp_esperada = self._sumar_meses(fecha_emision, periodo_meses)
        if fecha_exp.date() != fecha_exp_esperada.date():
            return False, "Licencia invalida: fecha de expiracion alterada.", None

        sello_esperado = self._generar_sello_v2(
            nombre_gym=lic["nombre_gym"],
            id_instalacion=lic["id_instalacion"],
            fecha_emision=fecha_emision,
            fecha_expiracion=fecha_exp,
            periodo_meses=periodo_meses,
            key_raw=key_esperada_raw,
        )
        if not hmac.compare_digest(str(lic["sello"]), sello_esperado):
            return False, "Licencia invalida: sello de seguridad no coincide.", None

        ahora = datetime.now()
        if ahora > fecha_exp:
            dias = (ahora - fecha_exp).days
            return False, f"Licencia expirada hace {dias} dias. Renueva tu licencia.", None

        dias_rest = (fecha_exp - ahora).days
        if dias_rest <= 30:
            return True, f"Licencia valida - expira en {dias_rest} dias", lic
        return True, f"Licencia valida ({dias_rest} dias restantes)", lic

    def _validar_licencia_legacy(self, lic: Dict) -> Tuple[bool, str, Optional[Dict]]:
        for campo in ("nombre_gym", "id_instalacion", "clave", "fecha_expiracion", "activa"):
            if campo not in lic:
                return False, f"Licencia corrupta: falta campo '{campo}'", None

        if not lic.get("activa", False):
            return False, "Licencia desactivada. Contacta a soporte.", None

        if lic["id_instalacion"] != self._obtener_id_instalacion():
            return False, "Licencia invalida: ID de instalacion no coincide.", None

        fecha_exp_str = str(lic["fecha_expiracion"]).split("T")[0]
        hash_esperado = self._generar_hash(
            lic["nombre_gym"],
            lic["id_instalacion"],
            fecha_exp_str,
        )
        if lic["clave"] != hash_esperado:
            return False, "Licencia invalida: hash de seguridad no coincide.", None

        try:
            fecha_exp = datetime.fromisoformat(lic["fecha_expiracion"])
        except ValueError:
            return False, "Licencia corrupta: fecha de expiracion invalida.", None

        ahora = datetime.now()
        if ahora > fecha_exp:
            dias = (ahora - fecha_exp).days
            return False, f"Licencia expirada hace {dias} dias. Renueva tu licencia.", None

        dias_rest = (fecha_exp - ahora).days
        if dias_rest <= 30:
            return True, f"Licencia valida - expira en {dias_rest} dias", lic
        return True, f"Licencia valida ({dias_rest} dias restantes)", lic

    def validar_licencia(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida la licencia actual.

        Returns:
            (es_valida, mensaje, datos_licencia | None)
        """
        if not self.ruta_licencia.exists():
            return False, "No se encontro archivo de licencia. Ingresa tu key para activar.", None

        try:
            with open(self.ruta_licencia, "r", encoding="utf-8") as f:
                lic = json.load(f)
        except json.JSONDecodeError:
            return False, "Licencia corrupta: formato JSON invalido.", None
        except OSError as exc:
            return False, f"Error leyendo licencia: {exc}", None

        if lic.get("formato") == "key_v2":
            return self._validar_licencia_v2(lic)
        return self._validar_licencia_legacy(lic)

    def renovar_licencia(self, duracion_dias: int = 365) -> Tuple[bool, str]:
        """Renovacion legacy por dias. Para key_v2 se usa una nueva key."""
        _, _, lic = self.validar_licencia()
        if not lic:
            return False, "No hay licencia existente para renovar."

        if lic.get("formato") == "key_v2":
            return (
                False,
                "Licencia key_v2: usa una nueva key (3/6/9/12 meses) para renovar.",
            )

        fecha_exp = datetime.fromisoformat(lic["fecha_expiracion"])
        base = max(datetime.now(), fecha_exp)
        nueva_exp = base + timedelta(days=duracion_dias)

        nuevo_hash = self._generar_hash(
            lic["nombre_gym"],
            lic["id_instalacion"],
            nueva_exp.strftime("%Y-%m-%d"),
        )
        lic["clave"] = nuevo_hash
        lic["fecha_expiracion"] = nueva_exp.isoformat()
        lic["fecha_renovacion"] = datetime.now().isoformat()
        lic["activa"] = True

        with open(self.ruta_licencia, "w", encoding="utf-8") as f:
            json.dump(lic, f, indent=2, ensure_ascii=False)
        return True, f"Licencia renovada hasta {nueva_exp.strftime('%Y-%m-%d')}"

    def desactivar_licencia(self) -> Tuple[bool, str]:
        """Desactiva la licencia (transferencia / revocacion)."""
        try:
            with open(self.ruta_licencia, "r", encoding="utf-8") as f:
                lic = json.load(f)
            lic["activa"] = False
            lic["fecha_desactivacion"] = datetime.now().isoformat()
            with open(self.ruta_licencia, "w", encoding="utf-8") as f:
                json.dump(lic, f, indent=2, ensure_ascii=False)
            return True, "Licencia desactivada exitosamente"
        except Exception as exc:
            return False, f"Error desactivando licencia: {exc}"

    def obtener_info_licencia(self) -> Optional[Dict]:
        """Devuelve los datos crudos de la licencia, o None."""
        if not self.ruta_licencia.exists():
            return None
        try:
            with open(self.ruta_licencia, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def obtener_estado_licencia(self) -> Dict:
        """
        Estado resumido para UI de admin.

        Campos relevantes:
        - dias_restantes
        - fecha_corte (YYYY-MM-DD)
        - renovar_ahora (True/False)
        """
        valida, mensaje, lic = self.validar_licencia()
        if not lic:
            lic = self.obtener_info_licencia()
        if not lic:
            return {
                "activa": False,
                "mensaje": mensaje,
                "plan_comercial": "",
                "plan_label": "Sin licencia",
                "canal_venta": "",
                "dias_restantes": 0,
                "fecha_corte": "",
                "renovar_ahora": True,
            }

        fecha_exp = None
        fecha_corte = ""
        dias_restantes = 0
        try:
            fecha_exp = datetime.fromisoformat(str(lic.get("fecha_expiracion", "")))
            fecha_corte = fecha_exp.strftime("%Y-%m-%d")
            dias_restantes = max(0, (fecha_exp - datetime.now()).days)
        except (TypeError, ValueError):
            pass

        plan = self._normalizar_plan_comercial(lic.get("plan_comercial", ""))
        if not plan:
            periodo = int(lic.get("periodo_meses", 0) or 0)
            duracion_dias = int(lic.get("duracion_dias", 0) or 0)
            plan = self._inferir_plan_comercial(periodo_meses=periodo, duracion_dias=duracion_dias)
        plan_label = self.PLANES_COMERCIALES.get(plan, {}).get("label", "Plan personalizado")

        return {
            "activa": bool(valida),
            "mensaje": mensaje,
            "plan_comercial": plan,
            "plan_label": plan_label,
            "canal_venta": str(lic.get("canal_venta", "") or ""),
            "dias_restantes": dias_restantes,
            "fecha_corte": fecha_corte,
            "renovar_ahora": (not valida) or dias_restantes <= 30,
        }


def generar_licencia_cli() -> None:
    """CLI para generar key de activacion por instalacion y periodo."""
    if not GestorLicencias.emisor_habilitado():
        print("Generador de keys deshabilitado en este entorno.")
        print("Habilitalo solo en la PC emisora con: METODO_BASE_EMISOR=1")
        return

    print("=" * 60)
    print("GENERADOR DE KEYS - METODO BASE")
    print("Consultoria Hernandez")
    print("=" * 60)
    print()

    gestor = GestorLicencias()

    print("Periodo disponible:")
    print("  1. 3 meses")
    print("  2. 6 meses")
    print("  3. 9 meses")
    print("  4. 12 meses")
    opcion = input("\nSelecciona opcion [1-4]: ").strip()
    mapa = {"1": 3, "2": 6, "3": 9, "4": 12}
    if opcion not in mapa:
        print("Opcion invalida")
        return
    periodo = mapa[opcion]

    id_inst = input("ID de instalacion del cliente: ").strip()
    if not id_inst:
        print("Error: el ID de instalacion no puede estar vacio")
        return

    try:
        key = gestor.generar_key_activacion(id_instalacion_cliente=id_inst, periodo_meses=periodo)
        print("\n" + "=" * 60)
        print("KEY GENERADA")
        print("=" * 60)
        print(f"ID instalacion : {id_inst}")
        print(f"Periodo        : {periodo} meses")
        print(f"Key activacion : {key}")
        print("=" * 60)
    except Exception as exc:
        print(f"\nError generando key: {exc}")


if __name__ == "__main__":
    generar_licencia_cli()
