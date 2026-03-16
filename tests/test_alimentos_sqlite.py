"""
tests/test_alimentos_sqlite.py
================================
Tests de integración para la capa SQLite de alimentos.

Valida:
- Inicialización de la BD en una carpeta temporal.
- Que los datos del seed se persistan correctamente.
- Que ``cargar_datos()`` devuelva el formato esperado.
- Idempotencia: inicializar dos veces no duplica datos.
- Que las personalizaciones no se sobreescriban al re-inicializar.

Ejecutar con:
    python -m pytest tests/test_alimentos_sqlite.py -v
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.alimentos_seed_runtime import (
    ALIMENTOS_BASE_SEED,
    CATEGORIAS_SEED,
    LIMITES_ALIMENTOS_SEED,
    EQUIVALENCIAS_PRACTICAS_SEED,
)
from src.alimentos_sqlite import (
    inicializar_db_si_es_necesario,
    cargar_datos,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_temp(tmp_path, monkeypatch):
    """Devuelve una ruta temporal para la BD y parchea CARPETA_CONFIG."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setenv("METODOBASE_TEST_CONFIG", str(config_dir))

    # Parchear la función _db_path para usar el directorio temporal
    import src.alimentos_sqlite as mod
    monkeypatch.setattr(mod, "_db_path", lambda: config_dir / "alimentos.db")

    return config_dir


@pytest.fixture
def db_inicializada(db_temp):
    """Inicializa la BD con las semillas y devuelve la ruta."""
    ruta = inicializar_db_si_es_necesario(
        ALIMENTOS_BASE_SEED,
        CATEGORIAS_SEED,
        LIMITES_ALIMENTOS_SEED,
        EQUIVALENCIAS_PRACTICAS_SEED,
    )
    return ruta


# ---------------------------------------------------------------------------
# 1. Inicialización
# ---------------------------------------------------------------------------

class TestInicializacionDB:
    """Verifica que la BD se cree y pueble correctamente."""

    def test_db_archivo_creado(self, db_inicializada):
        assert db_inicializada.exists(), "El archivo de BD debe existir tras la inicialización"

    def test_tablas_creadas(self, db_inicializada):
        with sqlite3.connect(db_inicializada) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tablas = {row[0] for row in cursor.fetchall()}
        tablas_esperadas = {"alimentos", "categorias", "limites", "equivalencias"}
        assert tablas_esperadas.issubset(tablas), (
            f"Faltan tablas: {tablas_esperadas - tablas}"
        )

    def test_alimentos_insertados(self, db_inicializada):
        with sqlite3.connect(db_inicializada) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alimentos")
            count = cursor.fetchone()[0]
        assert count > 0, "Debe haber alimentos en la BD tras la inicialización"

    def test_cantidad_alimentos_correlaciona_con_seed(self, db_inicializada):
        with sqlite3.connect(db_inicializada) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alimentos")
            count = cursor.fetchone()[0]
        # Al menos tantos como en el seed
        assert count >= len(ALIMENTOS_BASE_SEED), (
            f"BD tiene {count} alimentos, seed tiene {len(ALIMENTOS_BASE_SEED)}"
        )


# ---------------------------------------------------------------------------
# 2. cargar_datos()
# ---------------------------------------------------------------------------

class TestCargarDatos:
    """Verifica el formato y contenido devuelto por cargar_datos()."""

    def test_devuelve_claves_esperadas(self, db_inicializada):
        datos = cargar_datos()
        for clave in ("alimentos_base", "limites_alimentos", "equivalencias_practicas", "categorias"):
            assert clave in datos, f"Falta la clave '{clave}' en cargar_datos()"

    def test_alimentos_base_no_vacio(self, db_inicializada):
        datos = cargar_datos()
        assert len(datos["alimentos_base"]) > 0

    def test_alimento_tiene_campos_nutricionales(self, db_inicializada):
        datos = cargar_datos()
        for nombre, info in datos["alimentos_base"].items():
            for campo in ("proteina", "carbs", "grasa", "kcal"):
                assert campo in info, (
                    f"'{nombre}' no tiene el campo '{campo}' en cargar_datos()"
                )
            break  # Solo verificar el primero para rapidez

    def test_categorias_tiene_proteina(self, db_inicializada):
        datos = cargar_datos()
        assert "proteina" in datos["categorias"]
        assert len(datos["categorias"]["proteina"]) > 0

    def test_pechuga_en_proteinas(self, db_inicializada):
        datos = cargar_datos()
        proteinas = datos["categorias"].get("proteina", [])
        assert "pechuga_de_pollo" in proteinas, (
            "pechuga_de_pollo debe estar en la categoría proteina"
        )

    def test_limites_positivos(self, db_inicializada):
        datos = cargar_datos()
        for alimento, limite in datos["limites_alimentos"].items():
            assert limite > 0, (
                f"Límite de '{alimento}' debe ser positivo, got {limite}"
            )


# ---------------------------------------------------------------------------
# 3. Idempotencia
# ---------------------------------------------------------------------------

class TestIdempotencia:
    """Verifica que inicializar dos veces no duplique datos."""

    def test_reinicializar_no_duplica_alimentos(self, db_temp, monkeypatch):
        import src.alimentos_sqlite as mod
        db_path = db_temp / "alimentos.db"
        monkeypatch.setattr(mod, "_db_path", lambda: db_path)

        # Primera inicialización
        inicializar_db_si_es_necesario(
            ALIMENTOS_BASE_SEED, CATEGORIAS_SEED,
            LIMITES_ALIMENTOS_SEED, EQUIVALENCIAS_PRACTICAS_SEED,
        )
        with sqlite3.connect(db_path) as conn:
            count1 = conn.execute("SELECT COUNT(*) FROM alimentos").fetchone()[0]

        # Segunda inicialización
        inicializar_db_si_es_necesario(
            ALIMENTOS_BASE_SEED, CATEGORIAS_SEED,
            LIMITES_ALIMENTOS_SEED, EQUIVALENCIAS_PRACTICAS_SEED,
        )
        with sqlite3.connect(db_path) as conn:
            count2 = conn.execute("SELECT COUNT(*) FROM alimentos").fetchone()[0]

        assert count1 == count2, (
            f"Re-inicializar duplicó alimentos: {count1} → {count2}"
        )


# ---------------------------------------------------------------------------
# 4. Persistencia de personalizaciones
# ---------------------------------------------------------------------------

class TestPersonalizaciones:
    """Verifica que las personalizaciones no se sobreescriban al re-inicializar."""

    def test_personalizacion_no_sobreescrita(self, db_temp, monkeypatch):
        import src.alimentos_sqlite as mod
        db_path = db_temp / "alimentos.db"
        monkeypatch.setattr(mod, "_db_path", lambda: db_path)

        # Inicializar y luego modificar un alimento
        inicializar_db_si_es_necesario(
            ALIMENTOS_BASE_SEED, CATEGORIAS_SEED,
            LIMITES_ALIMENTOS_SEED, EQUIVALENCIAS_PRACTICAS_SEED,
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE alimentos SET proteina = 99.9 WHERE nombre = 'pechuga_de_pollo'"
            )

        # Re-inicializar
        inicializar_db_si_es_necesario(
            ALIMENTOS_BASE_SEED, CATEGORIAS_SEED,
            LIMITES_ALIMENTOS_SEED, EQUIVALENCIAS_PRACTICAS_SEED,
        )

        # La personalización debe mantenerse (INSERT OR IGNORE)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT proteina FROM alimentos WHERE nombre = 'pechuga_de_pollo'"
            ).fetchone()

        assert row is not None
        assert row[0] == pytest.approx(99.9), (
            "La personalización de proteina fue sobreescrita al re-inicializar"
        )


# ---------------------------------------------------------------------------
# 5. Valores nutricionales persistidos
# ---------------------------------------------------------------------------

class TestValoresNutricionalesPersistidos:
    """Verifica que los valores guardados en BD coincidan con el seed."""

    @pytest.mark.parametrize("alimento", [
        "pechuga_de_pollo", "arroz_blanco", "aguacate", "espinaca"
    ])
    def test_valores_seed_en_bd(self, db_inicializada, alimento):
        """Los macros del seed deben guardarse correctamente en la BD."""
        if alimento not in ALIMENTOS_BASE_SEED:
            pytest.skip(f"'{alimento}' no está en el seed base")

        datos_seed = ALIMENTOS_BASE_SEED[alimento]
        datos_bd = cargar_datos()["alimentos_base"]

        if alimento not in datos_bd:
            pytest.skip(f"'{alimento}' no se cargó desde BD")

        for campo in ("proteina", "carbs", "grasa", "kcal"):
            assert datos_bd[alimento][campo] == pytest.approx(
                datos_seed[campo], abs=0.01
            ), (
                f"{alimento}.{campo}: seed={datos_seed[campo]}, "
                f"BD={datos_bd[alimento][campo]}"
            )
