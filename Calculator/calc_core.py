"""
calc_core.py — Cálculo lineal y métricas de composición.

Responsabilidad única: transformar gramos de ingredientes en totales
y porcentajes de composición. Sin diagnósticos, sin UI, sin efectos.

Funciones públicas:
    calc_line(ing, grams)         → dict de masa por componente
    calc_totals(lines)            → dict de totales acumulados
    calc_percentages(totals)      → dict de porcentajes sobre masa total
    validate_brix(brix, totals)   → comparación refractómetro vs. calculado
    calc_water_activity(totals)   → Aw por ecuación de Ross (1975)
"""

from constants import (
    MACHINE_CREAMI_DELUXE,
    MACHINE_CREAMI_STANDARD,
)

# ── Masas molares y fracciones del MSNF ──────────────────────────────────────
_PM_AGUA        = 18.015
_PM_AZUCARES    = 270.0   # promedio ponderado sacarosa(342)/monos(180)
_PM_LACTOSA     = 342.0
_PM_SAL         = 58.44
_LACTOSA_FRAC   = 0.55    # 55% del MSNF es lactosa (Walstra 2005)
_SAL_FRAC       = 0.08    # 8% del MSNF son sales minerales
_LACTOSA_MSNF   = _LACTOSA_FRAC   # alias legible


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO LINEAL
# ─────────────────────────────────────────────────────────────────────────────

def calc_line(ing: dict, grams: float) -> dict:
    """Desglosa un ingrediente en sus componentes en masa absoluta (gramos)."""
    if not ing or not grams:
        return {}
    g = float(grams)
    fat      = float(ing.get('fat',      0))
    msnf     = float(ing.get('msnf',     0))
    sugars   = float(ing.get('sugars',   0))
    other_st = float(ing.get('other_st', 0))
    return {
        'grams':    g,
        'fat':      g * fat      / 100,
        'msnf':     g * msnf     / 100,
        'sugars':   g * sugars   / 100,
        'other_st': g * other_st / 100,
        'st':       g * (fat + msnf + sugars + other_st) / 100,
        'pod':      g * float(ing.get('pod', 0)),
        'pac':      g * float(ing.get('pac', 0)),
        'water':    g * float(ing.get('water', 0)) / 100,
    }


def calc_totals(lines_with_ings: list) -> dict:
    """
    Suma todos los ingredientes en totales absolutos.

    Args:
        lines_with_ings: lista de tuplas (ingredient_dict, grams, price_per_kg)

    Returns:
        dict con grams, fat, msnf, sugars, other_st, st, pod, pac, water, cost
    """
    totals = dict(grams=0, fat=0, msnf=0, sugars=0, other_st=0,
                  st=0, pod=0, pac=0, water=0, cost=0)
    for ing, grams, price_per_kg in lines_with_ings:
        if not ing or not grams:
            continue
        line = calc_line(ing, grams)
        for k in totals:
            if k != 'cost':
                totals[k] += line.get(k, 0)
        try:
            price = float(price_per_kg) if price_per_kg not in (None, '', 'None') else 0.0
        except (ValueError, TypeError):
            price = 0.0
        totals['cost'] += (float(grams) / 1000) * price
    return totals


def calc_percentages(totals: dict) -> dict:
    """
    Convierte totales absolutos a porcentajes sobre la masa total.

    POD y PAC se expresan como valores absolutos (no %), ya que son
    adimensionales relativos a la sacarosa y se comparan con rangos objetivo.
    """
    m = totals['grams']
    if m <= 0:
        return {}
    return {
        'st_pct':        totals['st']     / m * 100,
        'fat_pct':       totals['fat']    / m * 100,
        'msnf_pct':      totals['msnf']   / m * 100,
        'sugars_pct':    totals['sugars'] / m * 100,
        'water_pct':     totals['water']  / m * 100,
        'pod_total':     totals['pod'],
        'pac_total':     totals['pac'],
        'cost_per_100g': totals['cost']   / m * 100,
    }


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIÓN BRIX
# ─────────────────────────────────────────────────────────────────────────────

def validate_brix(measured_brix: float, totals: dict) -> dict:
    """
    Compara Brix medido en refractómetro con el Brix calculado de la receta.

    El refractómetro lee azúcares + lactosa del MSNF (factor 0.55).
    El delta de ±2° es el umbral estándar de control de proceso.

    Nota: refractómetros digitales auto-compensan temperatura a 20°C.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {}
    if not measured_brix or measured_brix <= 0:
        return {
            'brix_calculado':     0,
            'brix_con_msnf':      0,
            'delta_brix':         0,
            'sugars_estimados_g': 0,
            'interpretacion':     'Sin medición Brix ingresada.',
            'estado':             'sin_datos',
        }

    sugars_g = totals.get('sugars', 0)
    msnf_g   = totals.get('msnf',   0)

    brix_calc     = sugars_g / m * 100
    brix_con_msnf = (sugars_g + msnf_g * _LACTOSA_MSNF) / m * 100
    delta         = measured_brix - brix_con_msnf
    sugars_est    = measured_brix * m / 100

    if abs(delta) <= 2:
        estado = 'ok'
        interp = (f"✅ Brix medido ({measured_brix:.1f}°) coincide con lo calculado "
                  f"({brix_con_msnf:.1f}°). Receta correcta.")
    elif delta > 2:
        estado = 'alto'
        interp = (f"⚠️ Brix medido superior al esperado (+{delta:.1f}°). "
                  "Posible azúcar no declarado o fruta más madura.")
    else:
        estado = 'bajo'
        interp = (f"⚠️ Brix medido inferior al esperado ({delta:.1f}°). "
                  "Posible dilución, fermentación o error en pesaje.")

    return {
        'brix_calculado':     round(brix_calc,     1),
        'brix_con_msnf':      round(brix_con_msnf, 1),
        'delta_brix':         round(delta,          2),
        'sugars_estimados_g': round(sugars_est,     1),
        'interpretacion':     interp,
        'estado':             estado,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVIDAD DE AGUA — ecuación de Ross (1975)
# ─────────────────────────────────────────────────────────────────────────────

def calc_water_activity(totals: dict) -> dict:
    """
    Estima la actividad de agua (Aw) por la ecuación de Ross.

    Aw ≈ n_agua / (n_agua + n_solutos)

    Supuestos:
      - 55% del MSNF es lactosa (Walstra 2005)
      - 8% del MSNF son sales; NaCl disocia en 2 iones
      - PM promedio de azúcares = 270 g/mol
      - Grasa y proteínas no contribuyen significativamente a n_solutos
    Precisión: ±0.01–0.02 unidades. Suficiente para evaluación de riesgo relativo.
    """
    m        = totals.get('grams',  0)
    water_g  = totals.get('water',  0)
    sugars_g = totals.get('sugars', 0)
    msnf_g   = totals.get('msnf',   0)

    if water_g <= 0 or m <= 0:
        return {
            'aw': 1.0, 'aw_pct': 100.0,
            'riesgo_micro': 'sin_datos',
            'interpretacion': 'Sin agua — no calculable.',
            'modelo': 'Ross (1975)',
        }

    n_agua    = water_g  / _PM_AGUA
    n_azucar  = sugars_g / _PM_AZUCARES
    n_lactosa = (msnf_g * _LACTOSA_FRAC) / _PM_LACTOSA
    n_sal     = (msnf_g * _SAL_FRAC) / _PM_SAL * 2   # ×2 por disociación iónica
    n_solutos = n_azucar + n_lactosa + n_sal

    aw = max(0.0, min(1.0, n_agua / (n_agua + n_solutos)))

    if aw < 0.85:
        riesgo = 'bajo'
        interp = (f"✅ Aw {aw:.3f} — crecimiento microbiano inhibido. "
                  "Estabilidad microbiológica excelente en almacenamiento congelado.")
    elif aw < 0.91:
        riesgo = 'medio'
        interp = (f"⚠️ Aw {aw:.3f} — levaduras osmófilas pueden crecer "
                  "si hay descongelación parcial. Mantener cadena de frío.")
    else:
        riesgo = 'alto'
        interp = (f"🔴 Aw {aw:.3f} — alta (mezcla muy diluida). "
                  "Normal en bases lácteas estándar. Controla pasteurización.")

    return {
        'aw':             round(aw,       4),
        'aw_pct':         round(aw * 100, 2),
        'riesgo_micro':   riesgo,
        'interpretacion': interp,
        'modelo':         'Ross (1975)',
    }
