"""
tests/test_formulador_state.py — Tests de session_state del formulador.

Cubre toda la lógica de callbacks y recolección de datos sin necesitar
un browser ni el servidor de Streamlit. Se mockea st.session_state con
un dict-like simple que replica la API de Streamlit.

Ejecutar:  pytest tests/test_formulador_state.py -v
"""
import pytest
from unittest.mock import patch


# ─────────────────────────────────────────────────────────────────────────────
# MOCK DE SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

class FakeSessionState(dict):
    """dict con acceso por atributo — replica st.session_state."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


@pytest.fixture()
def ss():
    """Session state limpio con num_rows=4 (estado inicial típico)."""
    return FakeSessionState(num_rows=4)


@pytest.fixture(autouse=True)
def patch_st(ss, monkeypatch):
    """Parchea st.session_state y st.toast para todos los tests."""
    import streamlit as st
    monkeypatch.setattr(st, "session_state", ss)
    monkeypatch.setattr(st, "toast", lambda *a, **kw: None)
    return ss


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fill_row(ss, i, name="Leche entera", grams=500.0, price=1.5):
    ss[f"ing_name_{i}"] = name
    ss[f"grams_{i}"]    = grams
    ss[f"price_{i}"]    = price


# ─────────────────────────────────────────────────────────────────────────────
# callback_add_row
# ─────────────────────────────────────────────────────────────────────────────

class TestCallbackAddRow:
    def test_incrementa_num_rows(self, ss):
        from ui.components import callback_add_row
        callback_add_row()
        assert ss["num_rows"] == 5

    def test_preserva_datos_de_filas_existentes(self, ss):
        _fill_row(ss, 0, "Sacarosa", 80.0, 2.0)
        _fill_row(ss, 1, "Crema de leche", 100.0, 5.0)
        from ui.components import callback_add_row
        callback_add_row()
        assert ss["ing_name_0"] == "Sacarosa"
        assert ss["grams_0"]    == 80.0
        assert ss["ing_name_1"] == "Crema de leche"
        assert ss["grams_1"]    == 100.0

    def test_no_crea_datos_en_fila_nueva(self, ss):
        from ui.components import callback_add_row
        callback_add_row()
        assert ss.get("ing_name_4") is None
        assert ss.get("grams_4")    is None

    def test_num_rows_ausente_no_explota(self, ss):
        """Bug principal: si num_rows desaparece del state, no debe crashear."""
        del ss["num_rows"]
        from ui.components import callback_add_row
        callback_add_row()
        assert ss["num_rows"] == 5   # default 4 + 1

    def test_num_rows_none_no_explota(self, ss):
        ss["num_rows"] = None
        from ui.components import callback_add_row
        # No debe lanzar TypeError
        callback_add_row()
        assert isinstance(ss["num_rows"], int)

    def test_multiples_clicks_acumulan(self, ss):
        from ui.components import callback_add_row
        callback_add_row()
        callback_add_row()
        callback_add_row()
        assert ss["num_rows"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# callback_clear_all
# ─────────────────────────────────────────────────────────────────────────────

class TestCallbackClearAll:
    def test_elimina_todas_las_filas(self, ss):
        ss["num_rows"] = 6
        for i in range(6):
            _fill_row(ss, i, f"Ing{i}", float(i * 10 + 10))
        from ui.components import callback_clear_all
        callback_clear_all()
        assert ss["num_rows"] == 4
        for i in range(6):
            assert f"ing_name_{i}" not in ss
            assert f"grams_{i}"    not in ss
            assert f"price_{i}"    not in ss

    def test_elimina_recipe_loaded(self, ss):
        ss["recipe_loaded_id"]   = 42
        ss["recipe_loaded_name"] = "Receta test"
        from ui.components import callback_clear_all
        callback_clear_all()
        assert "recipe_loaded_id"   not in ss
        assert "recipe_loaded_name" not in ss

    def test_preserva_otras_claves(self, ss):
        ss["config_params"]    = {"key": "val"}
        ss["ing_cache_version"] = 7
        from ui.components import callback_clear_all
        callback_clear_all()
        assert ss["config_params"]     == {"key": "val"}
        assert ss["ing_cache_version"] == 7

    def test_idempotente(self, ss):
        """Llamar dos veces no debe crashear."""
        from ui.components import callback_clear_all
        callback_clear_all()
        callback_clear_all()
        assert ss["num_rows"] == 4

    def test_estado_inicial_sin_filas_no_explota(self, ss):
        from ui.components import callback_clear_all
        callback_clear_all()
        assert ss["num_rows"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# _collect_lines
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectLines:
    def test_recoge_filas_completas(self, ss):
        ss["num_rows"] = 3
        _fill_row(ss, 0, "Leche entera", 500.0, 1.2)
        _fill_row(ss, 1, "Sacarosa",     80.0,  2.0)
        _fill_row(ss, 2, "Crema",        100.0, 4.5)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 3
        assert lines[0]["ingredient_name"] == "Leche entera"
        assert lines[0]["grams"] == 500.0
        assert lines[1]["ingredient_name"] == "Sacarosa"
        assert lines[2]["grams"] == 100.0

    def test_omite_filas_vacias(self, ss):
        ss["num_rows"] = 4
        _fill_row(ss, 0, "Leche entera", 500.0)
        # filas 1-3 vacías (no tienen keys)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 1
        assert lines[0]["ingredient_name"] == "Leche entera"

    def test_omite_fila_con_nombre_pero_gramos_cero(self, ss):
        ss["num_rows"] = 2
        _fill_row(ss, 0, "Leche entera", 0.0)  # grams=0
        _fill_row(ss, 1, "Sacarosa",     80.0)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 1
        assert lines[0]["ingredient_name"] == "Sacarosa"

    def test_omite_fila_con_gramos_pero_sin_nombre(self, ss):
        ss["num_rows"] = 2
        ss["ing_name_0"] = ""
        ss["grams_0"]    = 200.0
        _fill_row(ss, 1, "Sacarosa", 80.0)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 1

    def test_estado_vacio_retorna_lista_vacia(self, ss):
        from ui.components import _collect_lines
        assert _collect_lines() == []

    def test_num_rows_ausente_no_explota(self, ss):
        """Bug: si num_rows desaparece, _collect_lines debe devolver [] sin crashear."""
        del ss["num_rows"]
        from ui.components import _collect_lines
        result = _collect_lines()
        assert isinstance(result, list)

    def test_grams_none_no_explota(self, ss):
        """Bug: Streamlit puede poner None en grams si el widget tiene un estado inválido."""
        ss["num_rows"]    = 1
        ss["ing_name_0"]  = "Leche entera"
        ss["grams_0"]     = None   # estado inválido del widget
        ss["price_0"]     = 1.5
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert lines == []   # grams inválido → fila ignorada

    def test_grams_string_no_explota(self, ss):
        """Streamlit puede dejar un string si el usuario escribió algo raro."""
        ss["num_rows"]   = 1
        ss["ing_name_0"] = "Leche entera"
        ss["grams_0"]    = "abc"
        ss["price_0"]    = 0.0
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert lines == []

    def test_grams_float_string_se_parsea(self, ss):
        """Un string numérico válido sí se acepta."""
        ss["num_rows"]   = 1
        ss["ing_name_0"] = "Leche entera"
        ss["grams_0"]    = "450"
        ss["price_0"]    = 0.0
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 1
        assert lines[0]["grams"] == 450.0

    def test_num_rows_float_se_castea(self, ss):
        """num_rows puede volver float si se serializa/deserializa en algún path."""
        ss["num_rows"]   = 2.0
        _fill_row(ss, 0, "Sacarosa", 80.0)
        _fill_row(ss, 1, "Dextrosa", 30.0)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 2

    def test_precio_incluido_correctamente(self, ss):
        ss["num_rows"]   = 1
        _fill_row(ss, 0, "Leche entera", 500.0, 2.8)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert lines[0]["price_per_kg"] == 2.8

    def test_precio_ausente_es_cero(self, ss):
        ss["num_rows"]   = 1
        ss["ing_name_0"] = "Leche entera"
        ss["grams_0"]    = 500.0
        # price_0 no existe en state
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert lines[0]["price_per_kg"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# _load_recipe_into_state
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadRecipeIntoState:
    def _recipe_lines(self):
        return [
            {"ingredient_name": "Leche entera",    "grams": 500.0, "price_per_kg": 1.2},
            {"ingredient_name": "Crema de leche",  "grams": 100.0, "price_per_kg": 4.5},
            {"ingredient_name": "Sacarosa",        "grams": 80.0,  "price_per_kg": 2.0},
        ]

    def test_carga_ingredientes_en_state(self, ss):
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_id=1, recipe_name="Test")
        assert ss["ing_name_0"] == "Leche entera"
        assert ss["grams_0"]    == 500.0
        assert ss["ing_name_1"] == "Crema de leche"
        assert ss["ing_name_2"] == "Sacarosa"

    def test_num_rows_se_ajusta_al_numero_de_lineas(self, ss):
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_name="Test")
        assert ss["num_rows"] == max(len(self._recipe_lines()), 4)

    def test_num_rows_minimo_4_con_receta_corta(self, ss):
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state([
            {"ingredient_name": "Leche entera", "grams": 500.0, "price_per_kg": 0.0}
        ], recipe_name="Una línea")
        assert ss["num_rows"] == 4   # mínimo garantizado

    def test_borra_filas_previas_antes_de_cargar(self, ss):
        ss["num_rows"]   = 6
        for i in range(6):
            _fill_row(ss, i, f"Prev{i}", float(i * 10))
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_name="Nueva")
        # Las filas 3-5 de la receta anterior deben desaparecer
        assert "ing_name_3" not in ss
        assert "ing_name_4" not in ss
        assert "ing_name_5" not in ss

    def test_guarda_recipe_id_y_nombre(self, ss):
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_id=99, recipe_name="Choco v2")
        assert ss["recipe_loaded_id"]   == 99
        assert ss["recipe_loaded_name"] == "Choco v2"

    def test_recipe_id_none_si_no_se_pasa(self, ss):
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_name="Sin ID")
        assert ss["recipe_loaded_id"] is None

    def test_carga_receta_sobre_otra_receta(self, ss):
        """Cargar una segunda receta debe reemplazar completamente la primera."""
        from ui.components import _load_recipe_into_state
        _load_recipe_into_state(self._recipe_lines(), recipe_id=1, recipe_name="Receta A")
        receta_b = [{"ingredient_name": "Dextrosa", "grams": 30.0, "price_per_kg": 3.0}]
        _load_recipe_into_state(receta_b, recipe_id=2, recipe_name="Receta B")
        assert ss["ing_name_0"] == "Dextrosa"
        assert ss["recipe_loaded_name"] == "Receta B"
        # El ingrediente 1 de la receta anterior no debe quedar
        assert "ing_name_1" not in ss

    def test_price_por_kg_opcional_default_cero(self, ss):
        from ui.components import _load_recipe_into_state
        lines = [{"ingredient_name": "Leche entera", "grams": 500.0}]  # sin price
        _load_recipe_into_state(lines, recipe_name="Sin precio")
        assert ss["price_0"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Invariantes del formulador (integración de callbacks)
# ─────────────────────────────────────────────────────────────────────────────

class TestInvariantesFormulador:
    def test_add_row_luego_collect_conserva_datos(self, ss):
        """Secuencia real: llenar filas → agregar fila → recolectar."""
        ss["num_rows"] = 4
        _fill_row(ss, 0, "Leche entera",   500.0, 1.2)
        _fill_row(ss, 1, "Sacarosa",        80.0, 2.0)
        _fill_row(ss, 2, "Crema de leche", 100.0, 4.5)
        from ui.components import callback_add_row, _collect_lines
        callback_add_row()
        lines = _collect_lines()
        assert len(lines) == 3
        names = [l["ingredient_name"] for l in lines]
        assert "Leche entera" in names
        assert "Sacarosa"     in names
        assert "Crema de leche" in names

    def test_clear_luego_collect_es_vacio(self, ss):
        ss["num_rows"] = 4
        _fill_row(ss, 0, "Leche entera", 500.0)
        from ui.components import callback_clear_all, _collect_lines
        callback_clear_all()
        assert _collect_lines() == []

    def test_load_luego_collect_retorna_lineas_cargadas(self, ss):
        from ui.components import _load_recipe_into_state, _collect_lines
        lines_in = [
            {"ingredient_name": "Leche entera", "grams": 500.0, "price_per_kg": 1.2},
            {"ingredient_name": "Sacarosa",     "grams": 80.0,  "price_per_kg": 2.0},
        ]
        _load_recipe_into_state(lines_in, recipe_name="Test")
        collected = _collect_lines()
        assert len(collected) == 2
        assert collected[0]["ingredient_name"] == "Leche entera"
        assert collected[1]["grams"] == 80.0

    def test_add_row_repetido_no_duplica_datos(self, ss):
        _fill_row(ss, 0, "Leche entera", 500.0)
        from ui.components import callback_add_row, _collect_lines
        for _ in range(5):
            callback_add_row()
        lines = _collect_lines()
        assert len(lines) == 1
        assert lines[0]["grams"] == 500.0

    def test_multiples_ingredientes_iguales_se_mantienen_separados(self, ss):
        """Dos filas con el mismo ingrediente pero distintos gramos."""
        ss["num_rows"] = 2
        _fill_row(ss, 0, "Leche entera", 300.0)
        _fill_row(ss, 1, "Leche entera", 200.0)
        from ui.components import _collect_lines
        lines = _collect_lines()
        assert len(lines) == 2
        assert lines[0]["grams"] == 300.0
        assert lines[1]["grams"] == 200.0
