"""
tests/test_alias_alimentos.py
==============================
Tests para el mapa centralizado de alias de alimentos.

Valida que:
- Los alias se resuelven al nombre canónico correcto.
- Los nombres canónicos se dejan intactos.
- Las funciones de utilidad detectan alias correctamente.
- No hay alias circulares.

Ejecutar con:
    python -m pytest tests/test_alias_alimentos.py -v
"""
import pytest

from core.services.alimentos_alias import (
    ALIAS_MAPA,
    NOMBRES_CANONICOS,
    resolver,
    es_canonico,
    es_alias,
    resolver_lista,
    detectar_alias_en_set,
)


# ---------------------------------------------------------------------------
# 1. Resolución de aliases conocidos
# ---------------------------------------------------------------------------

class TestResolucionAliases:
    """Verifica que cada alias conocido resuelva al nombre canónico esperado."""

    @pytest.mark.parametrize("alias, canonico", [
        ("atun",          "atun_en_agua"),
        ("carne_molida",  "carne_molida_res"),
        ("pavo",          "pavo_pechuga"),
        ("sardina",       "sardinas"),
        ("cerdo_lomo",    "lomo_cerdo"),
        ("tofu",          "tofu_firme"),
    ])
    def test_resolver_alias_a_canonico(self, alias, canonico):
        """Cada alias debe resolver al nombre canónico correcto."""
        assert resolver(alias) == canonico, (
            f"resolver('{alias}') debe retornar '{canonico}'"
        )

    def test_resolver_nombre_canonico_no_cambia(self):
        """Un nombre canónico pasado a resolver() debe retornar el mismo nombre."""
        assert resolver("pechuga_de_pollo") == "pechuga_de_pollo"
        assert resolver("arroz_blanco") == "arroz_blanco"
        assert resolver("aguacate") == "aguacate"

    def test_resolver_nombre_desconocido_pasa(self):
        """Un nombre no registrado (ni alias ni canónico) debe retornarse intacto."""
        assert resolver("alimento_inexistente") == "alimento_inexistente"


# ---------------------------------------------------------------------------
# 2. Verificación de canonicidad
# ---------------------------------------------------------------------------

class TestEsCanonico:
    """Prueba la función es_canonico()."""

    def test_nombres_canonicos_son_canonicos(self):
        """Todos los nombres en NOMBRES_CANONICOS deben pasar es_canonico()."""
        for nombre in NOMBRES_CANONICOS:
            assert es_canonico(nombre), (
                f"'{nombre}' está en NOMBRES_CANONICOS pero es_canonico() retorna False"
            )

    @pytest.mark.parametrize("alias", ["atun", "carne_molida", "pavo", "sardina",
                                        "cerdo_lomo", "tofu"])
    def test_aliases_no_son_canonicos(self, alias):
        """Los aliases NO deben aparecer en NOMBRES_CANONICOS."""
        assert not es_canonico(alias), (
            f"'{alias}' es un alias pero es_canonico() retorna True"
        )


# ---------------------------------------------------------------------------
# 3. Detección de aliases
# ---------------------------------------------------------------------------

class TestEsAlias:
    """Prueba la función es_alias()."""

    @pytest.mark.parametrize("nombre", [
        "atun", "carne_molida", "pavo", "sardina", "cerdo_lomo", "tofu"
    ])
    def test_aliases_son_detectados(self, nombre):
        assert es_alias(nombre)

    def test_canonico_no_es_alias(self):
        assert not es_alias("pechuga_de_pollo")
        assert not es_alias("atun_en_agua")

    def test_desconocido_no_es_alias(self):
        assert not es_alias("alimento_que_no_existe")


# ---------------------------------------------------------------------------
# 4. resolver_lista
# ---------------------------------------------------------------------------

class TestResolverLista:
    """Prueba resolver_lista() con distintos inputs."""

    def test_lista_solo_aliases(self):
        resultado = resolver_lista(["atun", "pavo", "sardina"])
        assert resultado == ["atun_en_agua", "pavo_pechuga", "sardinas"]

    def test_lista_mixta(self):
        resultado = resolver_lista(["pechuga_de_pollo", "atun", "salmon"])
        assert resultado == ["pechuga_de_pollo", "atun_en_agua", "salmon"]

    def test_lista_vacia(self):
        assert resolver_lista([]) == []

    def test_sin_duplicados_tras_resolver(self):
        """Si alias y canónico aparecen en la misma lista, no debe haber duplicados."""
        resultado = resolver_lista(["atun", "atun_en_agua"])
        assert resultado.count("atun_en_agua") == 1

    def test_orden_preservado(self):
        """El orden de los elementos originales debe preservarse."""
        entrada = ["salmon", "pavo", "claras_huevo"]
        resultado = resolver_lista(entrada)
        assert resultado[0] == "salmon"
        assert resultado[1] == "pavo_pechuga"
        assert resultado[2] == "claras_huevo"


# ---------------------------------------------------------------------------
# 5. detectar_alias_en_set
# ---------------------------------------------------------------------------

class TestDetectarAliasEnSet:
    """Prueba detectar_alias_en_set() para auditorías."""

    def test_detecta_aliases_conocidos(self):
        aliases_detectados = detectar_alias_en_set(
            {"atun", "pechuga_de_pollo", "sardina", "aguacate"}
        )
        assert "atun" in aliases_detectados
        assert "sardina" in aliases_detectados
        assert "pechuga_de_pollo" not in aliases_detectados
        assert "aguacate" not in aliases_detectados

    def test_set_solo_canonicos_devuelve_vacio(self):
        assert detectar_alias_en_set(
            {"pechuga_de_pollo", "arroz_blanco", "aguacate"}
        ) == {}

    def test_set_vacio(self):
        assert detectar_alias_en_set(set()) == {}


# ---------------------------------------------------------------------------
# 6. Integridad del mapa: no aliases circulares
# ---------------------------------------------------------------------------

class TestIntegridadMapa:
    """Verifica invariantes del ALIAS_MAPA."""

    def test_no_aliases_circulares(self):
        """Un valor en ALIAS_MAPA no debe ser también una clave en ALIAS_MAPA."""
        for alias, canonico in ALIAS_MAPA.items():
            assert canonico not in ALIAS_MAPA, (
                f"Alias circular: '{alias}' → '{canonico}', "
                f"pero '{canonico}' también es alias de '{ALIAS_MAPA[canonico]}'"
            )

    def test_todos_los_canonicos_en_NOMBRES_CANONICOS(self):
        """Cada valor (canónico) del mapa debe existir en NOMBRES_CANONICOS."""
        for alias, canonico in ALIAS_MAPA.items():
            assert canonico in NOMBRES_CANONICOS, (
                f"El canónico '{canonico}' (alias de '{alias}') "
                f"no está en NOMBRES_CANONICOS"
            )

    def test_constantes_core_no_usan_aliases(self):
        """
        Audita LEAN_PROTEINS y FATTY_PROTEINS de constantes.py para detectar
        aliases que aún no han sido corregidos.
        Estos tests documentan las inconsistencias; si se corrigen las constantes,
        deben actualizarse también.
        """
        from config.constantes import LEAN_PROTEINS, FATTY_PROTEINS, PROTEINAS_ESTRUCTURALES

        aliases_encontrados_lean = detectar_alias_en_set(LEAN_PROTEINS)
        aliases_encontrados_fatty = detectar_alias_en_set(FATTY_PROTEINS)
        aliases_encontrados_estructurales = detectar_alias_en_set(PROTEINAS_ESTRUCTURALES)

        # Documentamos los aliases conocidos — el test pasa, pero los registra
        aliases_esperados_lean = {"atun", "pavo", "cerdo_lomo"}
        aliases_esperados_fatty = {"carne_molida", "sardina"}

        assert set(aliases_encontrados_lean.keys()) <= aliases_esperados_lean, (
            f"LEAN_PROTEINS tiene nuevos aliases no documentados: "
            f"{set(aliases_encontrados_lean.keys()) - aliases_esperados_lean}"
        )
        assert set(aliases_encontrados_fatty.keys()) <= aliases_esperados_fatty, (
            f"FATTY_PROTEINS tiene nuevos aliases no documentados: "
            f"{set(aliases_encontrados_fatty.keys()) - aliases_esperados_fatty}"
        )
