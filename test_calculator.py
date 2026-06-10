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
from calculator import _get_targets, _status, calc_line, calc_totals, calc_percentages, calc_derived, overrun_calc

# ── Fixtures de ingredientes simulados ───────────────────────────────────────

def ing(fat=0, msnf=0, sugars=0, other_st=0, pod=0, pac=0, water=0):
    return dict(fat=fat, msnf=msnf, sugars=sugars, other_st=other_st,
                pod=pod, pac=pac, water=water)

LECHE     = ing(fat=3.5,  msnf=9.0,  sugars=4.7,  water=82.8, pod=0.10, pac=0.10)
CREMA     = ing(fat=35.0, msnf=6.0,  sugars=3.5,  water=55.5, pod=0.04, pac=0.04)
SACAROSA  = ing(sugars=100.0, pod=1.0, pac=1.0)
LPD       = ing(fat=1.0,  msnf=52.0, sugars=50.0, water=3.0,  pod=0.50, pac=0.50)
DEXTROSA  = ing(sugars=91.0, other_st=0, pod=0.75, pac=1.90, water=9.0)
FRUCTOSA  = ing(sugars=99.5, pod=1.20, pac=1.90, water=0.5)
MANGO     = ing(fat=0.4, sugars=14.0, other_st=0.8, pod=0.14, pac=0.20, water=84.8)
AGUA      = ing(water=100.0)
TREHALOSA = ing(sugars=99.5, pod=0.45, pac=0.70, water=0.5)


# ══════════════════════════════════════════════════════════════════════════════
# calc_line
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcLine:
    def test_empty_returns_empty(self):
        assert calc_line(None, 100) == {}
        assert calc_line(LECHE, 0) == {}

    def test_fat_contribution(self):
        r = calc_line(CREMA, 200)
        assert abs(r['fat'] - 70.0) < 0.01       # 200 * 35% = 70g

    def test_water_contribution(self):
        r = calc_line(LECHE, 500)
        assert abs(r['water'] - 414.0) < 0.01    # 500 * 82.8% = 414g

    def test_st_is_sum_of_components(self):
        r = calc_line(LECHE, 100)
        expected_st = 100 * (3.5 + 9.0 + 4.7 + 0.0) / 100
        assert abs(r['st'] - expected_st) < 0.01

    def test_pod_is_absolute(self):
        # POD es relativo a 1g, no a 100
        r = calc_line(SACAROSA, 150)
        assert abs(r['pod'] - 150.0) < 0.01      # 150 * 1.0 (no /100)

    def test_pac_is_absolute(self):
        r = calc_line(DEXTROSA, 100)
        assert abs(r['pac'] - 190.0) < 0.01      # 100 * 1.90


# ══════════════════════════════════════════════════════════════════════════════
# calc_totals
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcTotals:
    def test_total_mass(self):
        lines = [(LECHE, 650, 0), (CREMA, 200, 0), (SACAROSA, 150, 0)]
        t = calc_totals(lines)
        assert t['grams'] == 1000.0

    def test_cost_calculation(self):
        lines = [(SACAROSA, 1000, 2.0)]   # 1kg a $2/kg = $2
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
        lines = [(SACAROSA, 1000, 1.0)]   # $1/kg → $0.10/100g
        t = calc_totals(lines)
        p = calc_percentages(t)
        assert abs(p['cost_per_100g'] - 0.10) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# _get_targets — rangos adaptativos
# ══════════════════════════════════════════════════════════════════════════════

class TestGetTargets:
    # PAC Pacojet — solo límite superior, inferior None
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

    # Sorbete — grasa máxima 2%
    def test_sorbet_fat_max(self):
        tgt = _get_targets('Sorbete', 'Pacojet')
        _, hi = tgt['fat']
        assert hi == 2

    def test_sorbet_no_msnf(self):
        tgt = _get_targets('Sorbete', 'Mantecadora Tradicional')
        _, hi = tgt['msnf']
        assert hi <= 2

    # Helado Ligero — grasa restringida, MSNF elevado
    def test_helado_ligero_fat_max(self):
        tgt = _get_targets('Helado Ligero', 'Pacojet')
        lo, hi = tgt['fat']
        assert hi == 6
        assert lo == 2

    def test_helado_ligero_msnf_min_elevated(self):
        tgt = _get_targets('Helado Ligero', 'Pacojet')
        lo, _ = tgt['msnf']
        assert lo >= 8   # más MSNF para compensar grasa baja

    # MSNF crítico: Pacojet más permisivo
    def test_msnf_critical_pacojet_higher(self):
        tgt_paco = _get_targets('Helado/Gelato', 'Pacojet')
        tgt_mant = _get_targets('Helado/Gelato', 'Mantecadora Tradicional')
        assert tgt_paco['msnf_critical'] > tgt_mant['msnf_critical']
        assert tgt_paco['msnf_critical'] == 12.5
        assert tgt_mant['msnf_critical'] == 11.5

    # Azúcares sorbete — mínimo más alto
    def test_sorbet_sugar_min_higher_than_gelato(self):
        tgt_sorbet = _get_targets('Sorbete', 'Pacojet')
        tgt_gelato = _get_targets('Helado/Gelato', 'Pacojet')
        lo_sorbet, _ = tgt_sorbet['sugars']
        lo_gelato, _ = tgt_gelato['sugars']
        assert lo_sorbet > lo_gelato

    # Granita — ST más bajo
    def test_granita_st_lower(self):
        tgt = _get_targets('Granita', 'Pacojet')
        _, hi = tgt['st']
        assert hi <= 30

    # Vegano — sin MSNF
    def test_vegan_no_msnf(self):
        tgt = _get_targets('Gelato Vegano', 'Pacojet')
        _, hi = tgt['msnf']
        assert hi <= 2

    # Ratio ST/Agua Pacojet más restrictivo que mantecadora
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
        d = calc_derived(t, p, product_type=product_type, machine=machine)
        return d, t, p

    def diag_keys(self, d):
        return [x['key'] for x in d.get('diagnostics', [])]

    # MSNF arenado — umbral diferente por máquina
    def test_msnf_arenado_mantecadora_fires_at_11_5(self):
        # LPD=110g en 1000g base → ~11.78% MSNF (supera umbral 11.5% mantecadora)
        lines = [(LECHE, 540, 0), (CREMA, 200, 0), (SACAROSA, 150, 0), (LPD, 110, 0)]
        d, t, p = self._run(lines, machine='Mantecadora Tradicional')
        assert p['msnf_pct'] > 11.5
        assert 'msnf_arenado' in self.diag_keys(d)

    def test_msnf_arenado_pacojet_does_not_fire_at_12(self):
        # Mismo caso en Pacojet — no debe dispararse por debajo de 12.5%
        lines = [(LECHE, 540, 0), (CREMA, 200, 0), (SACAROSA, 150, 0), (LPD, 110, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        msnf = p['msnf_pct']
        if msnf <= 12.5:
            assert 'msnf_arenado' not in self.diag_keys(d)

    # PAC Pacojet — no penaliza PAC bajo
    def test_pac_bajo_pacojet_is_adjustable_not_critical(self):
        lines = [(LECHE, 700, 0), (CREMA, 150, 0), (TREHALOSA, 150, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        keys = self.diag_keys(d)
        priorities = {x['key']: x['priority'] for x in d['diagnostics']}
        # No debe haber crítico ni importante por PAC bajo
        assert 'pac_bajo_mantecadora' not in keys
        if 'pac_bajo_pacojet' in keys:
            assert priorities['pac_bajo_pacojet'] == 'adjustable'

    # PAC alto Pacojet — sí es crítico
    def test_pac_alto_pacojet_critical(self):
        # Mucha fructosa → PAC muy alto
        lines = [(LECHE, 400, 0), (FRUCTOSA, 400, 0), (DEXTROSA, 200, 0)]
        d, t, p = self._run(lines, machine='Pacojet')
        if p['pac_total'] > 420:
            assert 'pac_pacojet_alto' in self.diag_keys(d)
            crit = [x for x in d['diagnostics'] if x['key'] == 'pac_pacojet_alto']
            assert crit[0]['priority'] == 'critical'

    # Sorbete — fat_low no se dispara
    def test_sorbet_no_fat_low_diag(self):
        lines = [(MANGO, 700, 0), (SACAROSA, 200, 0), (AGUA, 100, 0)]
        d, t, p = self._run(lines, product_type='Sorbete', machine='Mantecadora Tradicional')
        assert 'grasa_baja' not in self.diag_keys(d)

    # ST sobreconcentrado — crítico
    def test_st_alto_critical(self):
        lines = [(SACAROSA, 300, 0), (LPD, 300, 0), (CREMA, 400, 0)]
        d, t, p = self._run(lines)
        if p['st_pct'] > 44:
            assert 'st_alto' in self.diag_keys(d)
            crit = [x for x in d['diagnostics'] if x['key'] == 'st_alto']
            assert crit[0]['priority'] == 'critical'

    # Mezcla equilibrada — sin diagnósticos
    def test_balanced_mix_no_diags(self):
        lines = [
            (LECHE,    650, 0),
            (CREMA,    150, 0),
            (SACAROSA, 130, 0),
            (LPD,       50, 0),
            (DEXTROSA,  20, 0),
        ]
        d, t, p = self._run(lines, machine='Mantecadora Tradicional')
        criticals = [x for x in d.get('diagnostics',[]) if x['priority'] == 'critical']
        assert len(criticals) == 0


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
        # 1 litro con 0% overrun → 1000g / 500g por beaker = 2 beakers exactos
        r = overrun_calc(1000, 0, 1.0)
        assert r['pacojet_beakers'] == 2

    def test_pacojet_beakers_ceiling_fractional(self):
        # 1.1 litros → 1100g / 500g = 2.2 → ceil = 3
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
