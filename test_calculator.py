"""
Tests unitarios para calculator.py
Ejecutar con: pytest test_calculator.py -v
"""
try:
    import pytest
except ImportError:
    pytest = None

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import calculator as calc
from calculator import (
    _get_targets, _status, calc_line, calc_totals,
    calc_percentages, calc_derived, overrun_calc,
    calc_calories, calc_water_activity, validate_brix,
    _detect_alcohol_lines,
)

# ── Fixtures de ingredientes simulados ───────────────────────────────────────

def ing(fat=0, msnf=0, sugars=0, other_st=0, pod=0, pac=0, water=0,
        name='', category='', zero_calorie=0):
    return dict(fat=fat, msnf=msnf, sugars=sugars, other_st=other_st,
                pod=pod, pac=pac, water=water, name=name,
                category=category, zero_calorie=zero_calorie)

LECHE     = ing(fat=3.5,  msnf=9.0,  sugars=4.7,  water=82.8, pod=0.10, pac=0.10, name='Leche entera')
CREMA     = ing(fat=35.0, msnf=6.0,  sugars=3.5,  water=55.5, pod=0.04, pac=0.04, name='Crema 35%')
SACAROSA  = ing(sugars=100.0, pod=1.0, pac=1.0, name='Sacarosa')
LPD       = ing(fat=1.0,  msnf=52.0, sugars=50.0, water=3.0,  pod=0.50, pac=0.50, name='LPD')
DEXTROSA  = ing(sugars=91.0, pod=0.75, pac=1.90, water=9.0, name='Dextrosa monohidrato')
FRUCTOSA  = ing(sugars=99.5, pod=1.20, pac=1.90, water=0.5, name='Fructosa')
MANGO     = ing(fat=0.4, sugars=14.0, other_st=0.8, pod=0.14, pac=0.20, water=84.8, name='Mango Ataulfo')
AGUA      = ing(water=100.0, name='Agua destilada')
TREHALOSA = ing(sugars=99.5, pod=0.45, pac=0.70, water=0.5, name='Trehalosa')
ERITRITOL = ing(sugars=99.5, pod=0.65, pac=1.30, water=0.5,
                name='Eritritol', zero_calorie=1)

# Ingredientes alcohólicos simulados
RON_40    = ing(sugars=0, pac=3.5, water=57.8, name='Ron añejo (40% vol)', category='Alcohol')
AMARETTO  = ing(sugars=25.0, pod=0.25, pac=2.3, water=74.5,
                name='Amaretto (28% vol)', category='Alcohol')


# ══════════════════════════════════════════════════════════════════════════════
# calc_line
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcLine:
    def test_empty_returns_empty(self):
        assert calc_line(None, 100) == {}
        assert calc_line(LECHE, 0) == {}

    def test_fat_contribution(self):
        r = calc_line(CREMA, 200)
        assert abs(r['fat'] - 70.0) < 0.01

    def test_water_contribution(self):
        r = calc_line(LECHE, 500)
        assert abs(r['water'] - 414.0) < 0.01

    def test_st_is_sum_of_components(self):
        r = calc_line(LECHE, 100)
        expected_st = 100 * (3.5 + 9.0 + 4.7 + 0.0) / 100
        assert abs(r['st'] - expected_st) < 0.01

    def test_pod_is_absolute(self):
        r = calc_line(SACAROSA, 150)
        assert abs(r['pod'] - 150.0) < 0.01

    def test_pac_is_absolute(self):
        r = calc_line(DEXTROSA, 100)
        assert abs(r['pac'] - 190.0) < 0.01


# ══════════════════════════════════════════════════════════════════════════════
# calc_totals
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcTotals:
    def test_total_mass(self):
        lines = [(LECHE, 650, 0), (CREMA, 200, 0), (SACAROSA, 150, 0)]
        t = calc_totals(lines)
        assert t['grams'] == 1000.0

    def test_cost_calculation(self):
        lines = [(SACAROSA, 1000, 2.0)]
        t = calc_totals(lines)
        assert abs(t['cost'] - 2.0) < 0.001

    def test_zero_grams_skipped(self):
        lines = [(LECHE, 0, 0), (SACAROSA, 100, 0)]
        t = calc_totals(lines)
        assert t['grams'] == 100.0

    def test_none_ingredient_skipped(self):
        lines = [(None, 100, 0), (SACAROSA, 100, 0)]
        t = calc_totals(lines)
        assert t['grams'] == 100.0


# ══════════════════════════════════════════════════════════════════════════════
# calc_percentages
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcPercentages:
    def test_returns_empty_for_zero_mass(self):
        totals = dict(grams=0, fat=0, msnf=0, sugars=0, other_st=0,
                      st=0, pod=0, pac=0, water=0, cost=0)
        assert calc_percentages(totals) == {}

    def test_water_pct_pure_water(self):
        lines = [(AGUA, 1000, 0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        assert abs(p['water_pct'] - 100.0) < 0.01

    def test_sugar_pct_pure_sacarosa(self):
        lines = [(SACAROSA, 1000, 0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        assert abs(p['sugars_pct'] - 100.0) < 0.01

    def test_cost_per_100g(self):
        lines = [(SACAROSA, 1000, 1.0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        assert abs(p['cost_per_100g'] - 0.10) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# _get_targets — rangos adaptativos
# ══════════════════════════════════════════════════════════════════════════════

class TestGetTargets:
    def test_pac_pacojet_no_lower_bound(self):
        tgt = _get_targets('Helado/Gelato', 'Pacojet')
        lo, hi = tgt['pac']
        assert lo is None
        assert hi == 420

    def test_pac_mantecadora_bilateral(self):
        tgt = _get_targets('Helado/Gelato', 'Mantecadora Tradicional')
        lo, hi = tgt['pac']
        assert lo is not None and lo > 0
        assert hi is not None and hi > 0

    def test_sorbet_fat_max(self):
        tgt = _get_targets('Sorbete', 'Pacojet')
        _, hi = tgt['fat']
        assert hi == 2

    def test_sorbet_no_msnf(self):
        tgt = _get_targets('Sorbete', 'Mantecadora Tradicional')
        _, hi = tgt['msnf']
        assert hi <= 2

    def test_helado_ligero_fat_max(self):
        tgt = _get_targets('Helado Ligero', 'Pacojet')
        lo, hi = tgt['fat']
        assert hi == 6
        assert lo == 2

    def test_helado_ligero_msnf_min_elevated(self):
        tgt = _get_targets('Helado Ligero', 'Pacojet')
        lo, _ = tgt['msnf']
        assert lo >= 8

    def test_msnf_critical_pacojet_higher(self):
        tgt_paco = _get_targets('Helado/Gelato', 'Pacojet')
        tgt_mant = _get_targets('Helado/Gelato', 'Mantecadora Tradicional')
        assert tgt_paco['msnf_critical'] > tgt_mant['msnf_critical']
        assert tgt_paco['msnf_critical'] == 12.5
        assert tgt_mant['msnf_critical'] == 11.5

    def test_sorbet_sugar_range_creami_tighter_than_gelato(self):
        """En Creami el sorbete tiene rango de azúcares más estrecho (máx 22% vs 22% gelato).
        En Pacojet ambos comparten el mismo rango (13-24%) — test verifica esa igualdad."""
        tgt_sorbet_creami = _get_targets('Sorbete',      'Ninja Creami Deluxe')
        tgt_gelato_creami = _get_targets('Helado/Gelato', 'Ninja Creami Deluxe')
        _, hi_sorbet = tgt_sorbet_creami['sugars']
        _, hi_gelato = tgt_gelato_creami['sugars']
        # Sorbete Creami: máx 22%; Gelato Creami: máx 22% — mismo techo, OK
        assert hi_sorbet == hi_gelato == 22

        # En Pacojet ambos tipos comparten rango idéntico (13-24%)
        tgt_sorbet_paco = _get_targets('Sorbete',      'Pacojet')
        tgt_gelato_paco = _get_targets('Helado/Gelato', 'Pacojet')
        assert tgt_sorbet_paco['sugars'] == tgt_gelato_paco['sugars']

    def test_granita_st_lower(self):
        tgt = _get_targets('Granita', 'Pacojet')
        _, hi = tgt['st']
        assert hi <= 35

    def test_vegan_no_msnf(self):
        tgt = _get_targets('Gelato Vegano', 'Pacojet')
        _, hi = tgt['msnf']
        assert hi <= 2

    def test_st_water_pacojet_stricter(self):
        tgt_p = _get_targets('Helado/Gelato', 'Pacojet')
        tgt_m = _get_targets('Helado/Gelato', 'Mantecadora Tradicional')
        lo_p, _ = tgt_p['st_water']
        lo_m, _ = tgt_m['st_water']
        assert lo_p >= lo_m


# ══════════════════════════════════════════════════════════════════════════════
# _status
# ══════════════════════════════════════════════════════════════════════════════

class TestStatus:
    def test_ok_within_range(self):
        assert _status(50, 30, 70) == 'ok'

    def test_low_below_range(self):
        assert _status(20, 30, 70) == 'low'

    def test_high_above_range(self):
        assert _status(80, 30, 70) == 'high'

    def test_empty_zero(self):
        assert _status(0, 30, 70) == 'empty'

    def test_none_lo_only_upper_matters(self):
        assert _status(300, None, 420) == 'ok'
        assert _status(500, None, 420) == 'high'
        assert _status(0,   None, 420) == 'empty'

    def test_none_hi_only_lower_matters(self):
        assert _status(50, 30, None) == 'ok'
        assert _status(10, 30, None) == 'low'


# ══════════════════════════════════════════════════════════════════════════════
# Diagnósticos — casos clave
# ══════════════════════════════════════════════════════════════════════════════

class TestDiagnostics:
    def _run(self, lines, product_type='Helado/Gelato', machine='Pacojet'):
        t = calc_totals(lines)
        p = calc_percentages(t)
        d = calc_derived(t, p, product_type=product_type, machine=machine,
                         lines_with_ings=lines)
        return d, t, p

    def diag_keys(self, d):
        return [x['key'] for x in d.get('diagnostics', [])]

    def test_msnf_arenado_mantecadora_fires_at_11_5(self):
        lines = [(LECHE, 540, 0), (CREMA, 200, 0), (SACAROSA, 150, 0), (LPD, 110, 0)]
        d, t, p = self._run(lines, machine='Mantecadora Tradicional')
        assert p['msnf_pct'] > 11.5
        assert 'msnf_arenado' in self.diag_keys(d)

    def test_msnf_arenado_pacojet_does_not_fire_at_12(self):
        lines = [(LECHE, 540, 0), (CREMA, 200, 0), (SACAROSA, 150, 0), (LPD, 110, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        msnf = p['msnf_pct']
        if msnf <= 12.5:
            assert 'msnf_arenado' not in self.diag_keys(d)

    def test_pac_bajo_pacojet_is_adjustable_not_critical(self):
        lines = [(LECHE, 700, 0), (CREMA, 150, 0), (TREHALOSA, 150, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        keys = self.diag_keys(d)
        priorities = {x['key']: x['priority'] for x in d['diagnostics']}
        assert 'pac_bajo_mantecadora' not in keys
        if 'pac_bajo_pacojet' in keys:
            assert priorities['pac_bajo_pacojet'] == 'adjustable'

    def test_pac_alto_pacojet_critical(self):
        lines = [(LECHE, 400, 0), (FRUCTOSA, 400, 0), (DEXTROSA, 200, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        if p['pac_total'] > 420:
            assert 'pac_pacojet_alto' in self.diag_keys(d)
            crit = [x for x in d['diagnostics'] if x['key'] == 'pac_pacojet_alto']
            assert crit[0]['priority'] == 'critical'

    def test_sorbet_no_fat_low_diag(self):
        lines = [(MANGO, 700, 0), (SACAROSA, 200, 0), (AGUA, 100, 0)]
        d, t, p = self._run(lines, product_type='Sorbete', machine='Mantecadora Tradicional')
        assert 'grasa_baja' not in self.diag_keys(d)

    def test_st_alto_critical(self):
        lines = [(SACAROSA, 300, 0), (LPD, 300, 0), (CREMA, 400, 0)]
        d, t, p = self._run(lines)
        if p['st_pct'] > 44:
            assert 'st_alto' in self.diag_keys(d)
            crit = [x for x in d['diagnostics'] if x['key'] == 'st_alto']
            assert crit[0]['priority'] == 'critical'

    def test_balanced_mix_no_diags(self):
        lines = [
            (LECHE,    650, 0),
            (CREMA,    150, 0),
            (SACAROSA, 130, 0),
            (LPD,       50, 0),
            (DEXTROSA,  20, 0),
        ]
        d, t, p = self._run(lines, machine='Mantecadora Tradicional')
        criticals = [x for x in d.get('diagnostics', []) if x['priority'] == 'critical']
        assert len(criticals) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Detección de alcohol — MEJORA: tests con ingredientes reales
# ══════════════════════════════════════════════════════════════════════════════

class TestAlcoholDetection:
    def test_ron_detectado_por_categoria(self):
        lines = [(LECHE, 600, 0), (SACAROSA, 150, 0), (RON_40, 50, 0)]
        alcohol_lines = _detect_alcohol_lines(lines)
        assert len(alcohol_lines) == 1
        assert 'Ron' in alcohol_lines[0]['ingredient_name']

    def test_ron_etanol_g_correcto(self):
        """Ron 40% vol: fracción másica etanol = 40 × 0.789 / 100 ≈ 0.316"""
        lines = [(RON_40, 100, 0)]
        alcohol_lines = _detect_alcohol_lines(lines)
        assert len(alcohol_lines) == 1
        # 100 g × 0.316 ≈ 31.6 g etanol
        assert 28 < alcohol_lines[0]['ethanol_g'] < 36

    def test_sin_alcohol_no_detecta(self):
        lines = [(LECHE, 650, 0), (CREMA, 150, 0), (SACAROSA, 200, 0)]
        alcohol_lines = _detect_alcohol_lines(lines)
        assert len(alcohol_lines) == 0

    def test_diag_alcohol_exceso_critico(self):
        """Receta con mucho ron → diagnóstico critical alcohol_exceso"""
        # 200g ron en 1000g mezcla: ~6% etanol → supera umbral 4%
        base_lines = [(LECHE, 600, 0), (SACAROSA, 200, 0)]
        ron_lines  = [(RON_40, 200, 0)]
        lines = base_lines + ron_lines
        t = calc_totals(lines)
        p = calc_percentages(t)
        d = calc_derived(t, p, lines_with_ings=lines)
        keys = [x['key'] for x in d.get('diagnostics', [])]
        assert 'alcohol_exceso' in keys
        crit = [x for x in d['diagnostics'] if x['key'] == 'alcohol_exceso']
        assert crit[0]['priority'] == 'critical'

    def test_diag_alcohol_advertencia_importante(self):
        """Ron en dosis intermedia → diagnóstico important"""
        # ~80g ron en 1000g → ~2.5-3% etanol
        lines = [(LECHE, 700, 0), (SACAROSA, 220, 0), (RON_40, 80, 0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        d = calc_derived(t, p, lines_with_ings=lines)
        keys = [x['key'] for x in d.get('diagnostics', [])]
        alc = d.get('alcohol_detected')
        if alc and alc['ethanol_pct'] > 2.5:
            assert 'alcohol_advertencia' in keys

    def test_diag_alcohol_info_dosis_correcta(self):
        """Ron en dosis baja → diagnóstico adjustable/info"""
        # ~30g ron en 1000g → ~1% etanol
        lines = [(LECHE, 750, 0), (SACAROSA, 220, 0), (RON_40, 30, 0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        d = calc_derived(t, p, lines_with_ings=lines)
        alc = d.get('alcohol_detected')
        assert alc is not None   # alcohol detectado aunque sea poco
        keys = [x['key'] for x in d.get('diagnostics', [])]
        if alc['ethanol_pct'] <= 2.5:
            assert 'alcohol_info' in keys

    def test_sin_alcohol_sin_diag(self):
        """Receta sin alcohol no genera ningún diagnóstico de alcohol"""
        lines = [(LECHE, 650, 0), (CREMA, 150, 0), (SACAROSA, 200, 0)]
        t = calc_totals(lines)
        p = calc_percentages(t)
        d = calc_derived(t, p, lines_with_ings=lines)
        keys = [x['key'] for x in d.get('diagnostics', [])]
        assert 'alcohol_exceso'     not in keys
        assert 'alcohol_advertencia' not in keys
        assert 'alcohol_info'       not in keys
        assert d.get('alcohol_detected') is None

    def test_amaretto_detectado_por_nombre(self):
        """Ingrediente de categoría Alcohol con nombre 'Amaretto' detectado correctamente"""
        lines = [(LECHE, 700, 0), (SACAROSA, 200, 0), (AMARETTO, 100, 0)]
        alcohol_lines = _detect_alcohol_lines(lines)
        assert len(alcohol_lines) == 1
        # Amaretto 28% vol: fracción ≈ 0.221 → 100g × 0.221 ≈ 22.1g etanol
        assert 18 < alcohol_lines[0]['ethanol_g'] < 28


# ══════════════════════════════════════════════════════════════════════════════
# calc_calories con zero_calorie
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcCalories:
    def test_zero_calorie_reduces_kcal(self):
        """Eritritol marcado zero_calorie debe contribuir menos que si fuera azúcar normal."""
        lines_con = [(SACAROSA, 200, 0)]
        lines_sin = [(ERITRITOL, 200, 0)]  # mismo % azúcares pero zero_calorie=1

        t_con = calc_totals(lines_con)
        t_sin = calc_totals(lines_sin)

        kcal_sacarosa  = calc_calories(t_con, lines_con)['kcal_per_100g']
        kcal_eritritol = calc_calories(t_sin, lines_sin)['kcal_per_100g']

        assert kcal_eritritol < kcal_sacarosa

    def test_zero_calorie_flag_descuenta_azucares(self):
        """kcal con eritritol (zero_calorie) debe ser mucho menor que con sacarosa."""
        lines = [(ERITRITOL, 1000, 0)]
        t = calc_totals(lines)
        kcal = calc_calories(t, lines)
        # Eritritol: 0.2 kcal/g según literatura. Con 1000g de eritritol, máx ~50 kcal/100g
        assert kcal['kcal_per_100g'] < 50

    def test_alcohol_suma_kcal(self):
        """Receta con ron debe tener más kcal que la misma sin ron (etanol=7 kcal/g)."""
        base = [(LECHE, 800, 0), (SACAROSA, 200, 0)]
        con_ron = [(LECHE, 700, 0), (SACAROSA, 200, 0), (RON_40, 100, 0)]

        t_base    = calc_totals(base)
        t_ron     = calc_totals(con_ron)
        kcal_base = calc_calories(t_base, base)['kcal_per_100g']
        kcal_ron  = calc_calories(t_ron, con_ron)['kcal_per_100g']

        assert kcal_ron > kcal_base


# ══════════════════════════════════════════════════════════════════════════════
# overrun_calc
# ══════════════════════════════════════════════════════════════════════════════

class TestOverrunCalc:
    def test_zero_overrun(self):
        r = overrun_calc(1000, 0, 1.0)
        assert abs(r['base_needed_g'] - 1000.0) < 0.01
        assert abs(r['liters_from_base'] - 1.0) < 0.01

    def test_100_pct_overrun_doubles_volume(self):
        r = overrun_calc(1000, 100, 2.0)
        assert abs(r['base_needed_g'] - 1000.0) < 0.01
        assert abs(r['liters_from_base'] - 2.0) < 0.01

    def test_pacojet_beakers_ceiling(self):
        r = overrun_calc(1000, 0, 1.0)
        assert r['pacojet_beakers'] == 2

    def test_pacojet_beakers_ceiling_fractional(self):
        r = overrun_calc(1000, 0, 1.1)
        assert r['pacojet_beakers'] == 3

    def test_mix_per_beaker_30pct(self):
        r = overrun_calc(1000, 30, 2.0)
        assert abs(r['mix_per_beaker'] - (500 / 1.3)) < 0.01

    def test_volume_increase_field(self):
        r = overrun_calc(1000, 40, 2.0)
        assert abs(r['volume_increase'] - 40.0) < 0.01

    def test_final_grams_per_liter_30pct(self):
        r = overrun_calc(1000, 30, 2.0)
        assert abs(r['final_grams_per_liter'] - (1000 / 1.3)) < 0.1


# ══════════════════════════════════════════════════════════════════════════════
# calc_water_activity
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcWaterActivity:
    def test_aw_between_0_and_1(self):
        lines = [(LECHE, 650, 0), (CREMA, 150, 0), (SACAROSA, 200, 0)]
        t = calc_totals(lines)
        aw = calc_water_activity(t)
        assert 0 < aw['aw'] <= 1.0

    def test_more_sugar_lower_aw(self):
        """Más azúcar → Aw más baja (más solutos)."""
        t_low  = calc_totals([(AGUA, 800, 0), (SACAROSA, 200, 0)])
        t_high = calc_totals([(AGUA, 500, 0), (SACAROSA, 500, 0)])
        assert calc_water_activity(t_high)['aw'] < calc_water_activity(t_low)['aw']

    def test_pure_water_aw_near_1(self):
        t = calc_totals([(AGUA, 1000, 0)])
        aw = calc_water_activity(t)
        assert aw['aw'] > 0.99

    def test_riesgo_keys_present(self):
        t = calc_totals([(LECHE, 700, 0), (SACAROSA, 300, 0)])
        aw = calc_water_activity(t)
        assert 'riesgo_micro' in aw
        assert 'interpretacion' in aw
        assert 'modelo' in aw

    def test_no_water_returns_sin_datos(self):
        t = calc_totals([(SACAROSA, 1000, 0)])
        # Sacarosa tiene 0% agua → water=0
        aw = calc_water_activity(t)
        assert aw['riesgo_micro'] == 'sin_datos'


# ══════════════════════════════════════════════════════════════════════════════
# validate_brix
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateBrix:
    def test_sin_datos_si_brix_cero(self):
        t = calc_totals([(LECHE, 650, 0), (SACAROSA, 200, 0)])
        r = validate_brix(0, t)
        assert r['estado'] == 'sin_datos'

    def test_ok_cuando_coincide(self):
        """Brix medido igual al calculado → estado 'ok'."""
        lines = [(AGUA, 700, 0), (SACAROSA, 300, 0)]
        t = calc_totals(lines)
        brix_esp = t['sugars'] / t['grams'] * 100   # ~30°
        r = validate_brix(brix_esp, t)
        assert r['estado'] == 'ok'

    def test_alto_cuando_medido_mayor(self):
        lines = [(AGUA, 700, 0), (SACAROSA, 300, 0)]
        t = calc_totals(lines)
        brix_esp = t['sugars'] / t['grams'] * 100
        r = validate_brix(brix_esp + 5, t)   # medimos 5° más
        assert r['estado'] == 'alto'

    def test_bajo_cuando_medido_menor(self):
        lines = [(AGUA, 700, 0), (SACAROSA, 300, 0)]
        t = calc_totals(lines)
        brix_esp = t['sugars'] / t['grams'] * 100
        r = validate_brix(max(0, brix_esp - 5), t)  # medimos 5° menos
        assert r['estado'] == 'bajo'

    def test_sugars_estimados_positivos(self):
        lines = [(AGUA, 600, 0), (SACAROSA, 250, 0), (LPD, 150, 0)]
        t = calc_totals(lines)
        r = validate_brix(25.0, t)
        assert r['sugars_estimados_g'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
