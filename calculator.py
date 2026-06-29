"""Pure calculation engine — sin dependencias externas."""

import math
from datetime import datetime

from constants import (
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO,
    PRODUCT_FROZEN,  PRODUCT_LIGERO,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    MACHINE_PACOJET,
    PRIORITY_CRITICAL, PRIORITY_IMPORTANT, PRIORITY_ADJUSTABLE,
    DIAGS_EXCLUIR_TICKET, CATEGORY_ALCOHOL, ALCOHOL_ETHANOL_FRACTION,
)

# ── Capacidades de máquinas ───────────────────────────────────────────────────
CREAMI_DELUXE_CAPACITY_G   = 640   # gramos útiles, pote 24oz
CREAMI_STANDARD_CAPACITY_G = 430   # gramos útiles, pote 16oz
PACOJET_CAPACITY_ML        = 500   # ml, beaker estándar

# ── Constantes calóricas ──────────────────────────────────────────────────────
KCAL_FAT     = 9.0
KCAL_PROTEIN = 3.5    # ~35% del MSNF estimado como proteína
KCAL_SUGAR   = 4.0
KCAL_OTHER   = 2.5    # fibra / almidón / cacao: promedio
KCAL_ALCOHOL = 7.0

# ── Perfil de temperatura Ninja Creami ────────────────────────────────────────
CREAMI_FREEZE_TEMP_C    = -18.0
CREAMI_FREEZE_HOURS_MIN = 24
CREAMI_DELTA_T_MIN      = -1.5    # ΔT mínimo para congelar a -18 °C

# ── Perfiles organolépticos de edulcorantes ───────────────────────────────────
# Estructura: (POD, PAC, kcal/g, descripción_sabor, perfil_dulzor)
SWEETENER_PROFILES = {
    'sacarosa':         (1.00, 1.00, 4.0, 'Referencia — dulzor limpio y redondo',        'inmediato'),
    'dextrosa':         (0.75, 1.90, 4.0, 'Frescor suave positivo en boca fría',         'inmediato'),
    'fructosa':         (1.20, 1.90, 4.0, 'Muy dulce en frío, puede ser empalagoso',     'inmediato'),
    'trehalosa':        (0.45, 0.70, 4.0, 'Muy suave, casi neutro, crioprotector',       'lento'),
    'alulosa':          (0.70, 1.00, 0.4, 'El más parecido al azúcar, sin retrogusto',   'inmediato'),
    'eritritol':        (0.65, 1.30, 0.2, 'Efecto frescor/mentolado — limitar a 1.5%',  'inmediato'),
    'maltitol':         (0.75, 0.90, 2.4, 'Similar a sacarosa, posibles molestias GI',   'inmediato'),
    'isomalt':          (0.45, 0.50, 2.0, 'Neutro, antirecristalizante',                 'lento'),
    'azucar invertido': (1.30, 1.90, 4.0, 'Muy antirecristalizante, frescor agradable',  'inmediato'),
    'stevia':           (0.00, 0.00, 0.0, 'Retrogusto amargo/regaliz — máx 0.3 g/kg',   'tardío'),
    'splenda':          (0.00, 0.00, 0.0, 'Stevia + eritritol — ver ambos perfiles',     'tardío'),
    'glucosa de40':     (0.50, 0.80, 4.0, 'Antirecristalizante suave, neutro',           'inmediato'),
    'glucosa de60':     (0.70, 0.90, 4.0, 'Mayor dulzor que DE40, neutro',               'inmediato'),
}


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE ALCOHOL POR LÍNEA (MEJORA: reemplaza placeholder)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_alcohol_lines(lines_with_ings):
    """
    Itera las líneas de la receta e identifica ingredientes alcohólicos
    por categoría ('Alcohol') o por coincidencia de nombre con
    ALCOHOL_ETHANOL_FRACTION.

    Retorna lista de dicts:
      ingredient_name  — nombre del ingrediente
      grams            — gramos en la receta
      ethanol_g        — gramos de etanol puro estimados
      ethanol_fraction — fracción másica de etanol usado
      pac_contrib      — contribución real al PAC (etanol PAC=3.5)
    """
    results = []
    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g = float(grams)
        name_lower = ing.get('name', '').lower()
        category   = ing.get('category', '')

        ethanol_fraction = 0.0

        # Prioridad 1: categoría explícita 'Alcohol' en la BD
        if category == CATEGORY_ALCOHOL:
            # Buscar fracción específica por nombre; si no, usar PAC/3.5 como proxy
            for key, frac in ALCOHOL_ETHANOL_FRACTION.items():
                if key in name_lower:
                    ethanol_fraction = frac
                    break
            if ethanol_fraction == 0.0:
                # Fallback: inferir desde PAC del ingrediente
                # PAC_etanol = 3.5 por definición; otros solutos del licor aportan ~0.5
                pac_ing = float(ing.get('pac', 0))
                pac_azucares = float(ing.get('sugars', 0)) / 100 * float(ing.get('pod', 1))
                pac_alcohol_ing = max(0, pac_ing - pac_azucares)
                ethanol_fraction = min(pac_alcohol_ing / 3.5, 0.5)

        # Prioridad 2: nombre contiene keyword conocido de licor
        elif any(key in name_lower for key in ALCOHOL_ETHANOL_FRACTION):
            for key, frac in ALCOHOL_ETHANOL_FRACTION.items():
                if key in name_lower:
                    ethanol_fraction = frac
                    break

        if ethanol_fraction > 0:
            ethanol_g = g * ethanol_fraction
            results.append({
                'ingredient_name':  ing.get('name', ''),
                'grams':            g,
                'ethanol_g':        ethanol_g,
                'ethanol_fraction': ethanol_fraction,
                'pac_contrib':      ethanol_g * 3.5,
            })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO POR LÍNEA
# ─────────────────────────────────────────────────────────────────────────────

def calc_line(ing, grams):
    """Retorna contribución nutricional por línea (en gramos)."""
    if not ing or not grams:
        return {}
    g = float(grams)
    return {
        'grams':    g,
        'fat':      g * float(ing.get('fat', 0))      / 100,
        'msnf':     g * float(ing.get('msnf', 0))     / 100,
        'sugars':   g * float(ing.get('sugars', 0))   / 100,
        'other_st': g * float(ing.get('other_st', 0)) / 100,
        'st':       g * (float(ing.get('fat', 0)) + float(ing.get('msnf', 0))
                         + float(ing.get('sugars', 0)) + float(ing.get('other_st', 0))) / 100,
        'pod':      g * float(ing.get('pod', 0)),
        'pac':      g * float(ing.get('pac', 0)),
        'water':    g * float(ing.get('water', 0))    / 100,
    }


def calc_totals(lines_with_ings):
    """lines_with_ings: list of (ingredient_dict, grams, price_per_kg)"""
    totals = dict(grams=0, fat=0, msnf=0, sugars=0, other_st=0,
                  st=0, pod=0, pac=0, water=0, cost=0)
    for ing, grams, price_per_kg in lines_with_ings:
        if not ing or not grams:
            continue
        c = calc_line(ing, grams)
        for k in totals:
            if k != 'cost':
                totals[k] += c.get(k, 0)
        try:
            price = float(price_per_kg) if price_per_kg not in (None, '', 'None') else 0.0
        except (ValueError, TypeError):
            price = 0.0
        totals['cost'] += (float(grams) / 1000) * price
    return totals


def calc_percentages(totals):
    """Todos los % relativos a la masa total."""
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
        'cost_per_100g': totals['cost']   / m * 100 if m > 0 else 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE CALORÍAS
# ─────────────────────────────────────────────────────────────────────────────

def calc_calories(totals, lines_with_ings=None):
    """
    Estima calorías totales y por 100 g desde macronutrientes.
    Si se pasan lines_with_ings, descuenta calorías de ingredientes
    zero_calorie (eritritol, stevia, alulosa) que la BD marca como tal.

    Retorna dict: kcal_total, kcal_per_100g, kcal_per_pote_deluxe.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {'kcal_total': 0, 'kcal_per_100g': 0, 'kcal_per_pote_deluxe': 0}

    protein_g = totals.get('msnf', 0) * 0.35   # ~35% del MSNF es proteína

    kcal = (
        totals.get('fat', 0)      * KCAL_FAT      +
        protein_g                  * KCAL_PROTEIN  +
        totals.get('sugars', 0)   * KCAL_SUGAR    +
        totals.get('other_st', 0) * KCAL_OTHER
    )

    # Descontar calorías de ingredientes marcados zero_calorie en BD
    if lines_with_ings:
        for ing, grams, _ in lines_with_ings:
            if not ing or not grams:
                continue
            if ing.get('zero_calorie', 0):
                g = float(grams)
                # Restar lo que se sumó por azúcares de ese ingrediente
                kcal -= g * float(ing.get('sugars', 0)) / 100 * KCAL_SUGAR

    # Añadir calorías de alcohol detectado
    if lines_with_ings:
        alcohol_lines = _detect_alcohol_lines(lines_with_ings)
        for a in alcohol_lines:
            kcal += a['ethanol_g'] * KCAL_ALCOHOL

    kcal = max(0, kcal)
    kcal_per_100g = kcal / m * 100
    kcal_per_pote = kcal_per_100g * CREAMI_DELUXE_CAPACITY_G / 100

    return {
        'kcal_total':           round(kcal, 0),
        'kcal_per_100g':        round(kcal_per_100g, 0),
        'kcal_per_pote_deluxe': round(kcal_per_pote, 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# D3: VALIDACIÓN BRIX (refractómetro) vs CÁLCULO
# ─────────────────────────────────────────────────────────────────────────────

def validate_brix(measured_brix: float, totals: dict) -> dict:
    """
    Compara el Brix medido en el refractómetro con el Brix calculado
    desde los azúcares de la receta.

    El refractómetro mide sólidos solubles totales (°Brix), que en helados
    equivale aproximadamente a (azúcares + sólidos lácteos solubles) / masa total.
    Para mezclas con alto MSNF, el refractómetro sobreestima el Brix de azúcares
    porque también detecta lactosa y minerales del suero.

    Parámetros
    ----------
    measured_brix : lectura real del refractómetro (°Brix)
    totals        : salida de calc_totals()

    Retorna
    -------
    dict con:
      brix_calculado      — Brix teórico desde azúcares puros
      brix_con_msnf       — Brix corregido incluyendo sólidos lácteos solubles
      delta_brix          — diferencia (medido - calculado_corregido)
      estado              — 'ok' | 'bajo' | 'alto' | 'sin_datos'
      interpretacion      — texto explicativo para el usuario
      sugars_estimados_g  — gramos de azúcar inferidos desde el Brix medido
    """
    m = totals.get('grams', 0)
    if m <= 0 or measured_brix <= 0:
        return {
            'brix_calculado':     0,
            'brix_con_msnf':      0,
            'delta_brix':         0,
            'estado':             'sin_datos',
            'interpretacion':     'Sin datos suficientes para validar.',
            'sugars_estimados_g': 0,
        }

    brix_calc = totals['sugars'] / m * 100

    # Corrección MSNF: la lactosa (~55% del MSNF) es soluble y visible al refractómetro
    lactosa_g      = totals.get('msnf', 0) * 0.55
    minerales_g    = totals.get('msnf', 0) * 0.08
    brix_con_msnf  = (totals['sugars'] + lactosa_g + minerales_g) / m * 100

    delta = measured_brix - brix_con_msnf
    tolerancia = 1.5  # °Brix — margen aceptable de error de campo

    if abs(delta) <= tolerancia:
        estado = 'ok'
        interpretacion = (
            f"✅ Brix medido {measured_brix:.1f}° concuerda con el cálculo "
            f"({brix_con_msnf:.1f}° esperado incluyendo MSNF). "
            "La receta está dentro de tolerancia de campo (±1.5°)."
        )
    elif delta < -tolerancia:
        estado = 'bajo'
        interpretacion = (
            f"⚠️ Brix medido {measured_brix:.1f}° es {abs(delta):.1f}° menor al esperado "
            f"({brix_con_msnf:.1f}°). Posibles causas: "
            "① el azúcar no se disolvió completamente antes de medir, "
            "② el refractómetro necesita calibración con agua destilada, "
            "③ los gramos de azúcar en la receta son mayores que los pesados realmente."
        )
    else:
        estado = 'alto'
        interpretacion = (
            f"⚠️ Brix medido {measured_brix:.1f}° es {delta:.1f}° mayor al esperado "
            f"({brix_con_msnf:.1f}°). Posibles causas: "
            "① hay más azúcar del declarado (frutas más maduras, leche condensada con más sólidos), "
            "② el instrumento está descalibrado o tiene residuo de mezcla anterior."
        )

    sugars_est = max(0, measured_brix / 100 * m - lactosa_g - minerales_g)

    return {
        'brix_calculado':     round(brix_calc, 1),
        'brix_con_msnf':      round(brix_con_msnf, 1),
        'delta_brix':         round(delta, 2),
        'estado':             estado,
        'interpretacion':     interpretacion,
        'sugars_estimados_g': round(sugars_est, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES — exportadas
# ─────────────────────────────────────────────────────────────────────────────

def _get_targets(product_type: str, machine: str) -> dict:
    """
    Retorna rangos objetivo para un tipo de producto y máquina.
    Todos los rangos son (lo, hi). PAC Pacojet tiene lo=None (sin mínimo).
    Incluye msnf_critical: umbral de arenado diferenciado por máquina.
    """
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    is_vegan  = product_type == PRODUCT_VEGANO
    is_frozen = product_type == PRODUCT_FROZEN
    is_light  = product_type == PRODUCT_LIGERO
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_paco   = machine == MACHINE_PACOJET

    if is_creami:
        if is_sorbet:
            st = (25, 33); fat = (0, 2);  msnf = (0, 1)
        elif is_frozen:
            st = (28, 36); fat = (2, 8);  msnf = (3, 9)
        elif is_vegan:
            st = (28, 38); fat = (2, 15); msnf = (0, 2)
        elif is_light:
            st = (26, 34); fat = (2, 6);  msnf = (8, 12)
        else:
            st = (28, 38); fat = (4, 15); msnf = (5, 10)
        sugars        = (13, 22)
        pod           = (115, 175) if is_sorbet else (125, 200)
        pac           = (120, 260)
        st_water      = (0.42, 0.78)
        msnf_critical = 11.0

    elif is_paco:
        if is_sorbet:
            st = (27, 35); fat = (0, 2);  msnf = (0, 2)
        elif is_vegan:
            st = (34, 42); fat = (2, 18); msnf = (0, 2)
        elif is_frozen:
            st = (30, 38); fat = (2, 10); msnf = (4, 10)
        elif is_light:
            st = (30, 38); fat = (2, 6);  msnf = (8, 13)
        else:
            st = (34, 42); fat = (4, 20); msnf = (6, 11)
        sugars        = (13, 24)
        pod           = (115, 180) if is_sorbet else (130, 210)
        pac           = (None, 420)   # solo límite superior
        st_water      = (0.50, 0.78)
        msnf_critical = 12.5

    else:  # Mantecadora Tradicional y otras
        if is_sorbet:
            st = (27, 35); fat = (0, 2);  msnf = (0, 2)
        elif is_vegan:
            st = (34, 42); fat = (2, 18); msnf = (0, 2)
        elif is_frozen:
            st = (30, 38); fat = (2, 10); msnf = (4, 10)
        elif is_light:
            st = (30, 38); fat = (2, 6);  msnf = (8, 12)
        else:
            st = (34, 42); fat = (4, 20); msnf = (6, 11)
        sugars        = (13, 24)
        pod           = (115, 180) if is_sorbet else (130, 210)
        pac           = (150, 320)
        st_water      = (0.48, 0.78)
        msnf_critical = 11.5

    return {
        'st':            st,
        'fat':           fat,
        'msnf':          msnf,
        'sugars':        sugars,
        'pod':           pod,
        'pac':           pac,
        'st_water':      st_water,
        'msnf_critical': msnf_critical,
    }


def _status(val: float, lo, hi) -> str:
    """
    Semáforo de rango: 'empty' | 'low' | 'ok' | 'high'.
    lo y/o hi pueden ser None para rangos unilaterales (ej. PAC Pacojet).
    """
    if val <= 0:
        return 'empty'
    if lo is not None and val < lo:
        return 'low'
    if hi is not None and val > hi:
        return 'high'
    return 'ok'


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DERIVADO — RANGOS, SEMÁFORO, DIAGNÓSTICOS
# MEJORA: ahora acepta lines_with_ings para diagnósticos por ingrediente
# ─────────────────────────────────────────────────────────────────────────────

def calc_derived(totals, pct, product_type='Helado/Gelato', machine='Ninja Creami Deluxe',
                 lines_with_ings=None):
    """
    Ratios, crioscopía, semáforo y diagnósticos.

    Parámetros
    ----------
    totals          : salida de calc_totals()
    pct             : salida de calc_percentages()
    product_type    : constante PRODUCT_*
    machine         : constante MACHINE_*
    lines_with_ings : list of (ingredient_dict, grams, price_per_kg) — opcional,
                      necesario para diagnósticos de alcohol precisos
    """
    d = {}
    m = totals['grams']
    if m <= 0:
        return d

    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    is_vegan  = product_type == PRODUCT_VEGANO
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_paco   = machine == MACHINE_PACOJET

    # ── Ratios ────────────────────────────────────────────────────────────────
    d['ratio_fat_msnf']    = totals['fat']    / totals['msnf']  if totals['msnf']  > 0 else 0
    d['ratio_sugars_st']   = totals['sugars'] / totals['st']    if totals['st']    > 0 else 0
    d['ratio_st_water']    = totals['st']     / totals['water'] if totals['water'] > 0 else 0
    d['ratio_sugar_water'] = totals['sugars'] / totals['water'] if totals['water'] > 0 else 0

    # ── Crioscopía ────────────────────────────────────────────────────────────
    # Modelo molar corregido basado en la ley de Raoult con PM efectivo.
    # Para mezclas concentradas (Brix ≥ 22°) aplica corrección Chen-Leighton.
    water_kg  = totals['water'] / 1000
    pac_total = totals['pac']
    sugars_kg = totals['sugars'] / 1000
    brix_est  = sugars_kg / (water_kg + sugars_kg) * 100 if (water_kg + sugars_kg) > 0 else 0

    if water_kg > 0 and pac_total > 0:
        PM_SACAROSA = 342.0
        KF_AGUA     = 1.858
        molalidad   = pac_total / PM_SACAROSA / water_kg

        if brix_est >= 22:
            B = 0.004
            d['delta_t']         = -KF_AGUA * molalidad * (1 + B * molalidad)
            d['cryoscopy_model'] = 'Chen-Leighton'
        else:
            d['delta_t']         = -KF_AGUA * molalidad
            d['cryoscopy_model'] = 'Raoult'
    else:
        d['delta_t']         = 0.0
        d['cryoscopy_model'] = 'n/a'

    d['brix_estimado'] = round(brix_est, 1)

    # ── Temperatura de servicio ───────────────────────────────────────────────
    if is_creami:
        d['temp_objetivo'] = CREAMI_FREEZE_TEMP_C
        d['congela_ok']    = d['delta_t'] < CREAMI_DELTA_T_MIN
        d['temp_servicio'] = f"Congelar {CREAMI_FREEZE_HOURS_MIN}h a {CREAMI_FREEZE_TEMP_C}°C → procesar"
    elif is_paco:
        d['temp_servicio'] = "Pacotizar a -22°C → servir"
    else:
        d['temp_servicio'] = "-12 a -14 °C"

    # ── Rangos objetivo ───────────────────────────────────────────────────────
    tgt = _get_targets(product_type, machine)
    d['targets'] = tgt

    st_lo,  st_hi  = tgt['st']
    fat_lo, fat_hi = tgt['fat']
    sug_lo, sug_hi = tgt['sugars']
    pac_lo, pac_hi = tgt['pac']
    pod_lo, pod_hi = tgt['pod']
    stw_lo, stw_hi = tgt['st_water']
    msnf_crit      = tgt['msnf_critical']

    st_v   = pct.get('st_pct',    0)
    fat_v  = pct.get('fat_pct',   0)
    msnf_v = pct.get('msnf_pct',  0)
    sug_v  = pct.get('sugars_pct',0)
    pod_v  = pct.get('pod_total', 0)
    pac_v  = pct.get('pac_total', 0)
    stw_v  = d['ratio_st_water']
    wat_v  = pct.get('water_pct', 0)

    # ── Semáforo ──────────────────────────────────────────────────────────────
    d['status'] = {
        'st':       _status(st_v,   st_lo,           st_hi),
        'fat':      _status(fat_v,  fat_lo,          fat_hi),
        'msnf':     _status(msnf_v, *tgt['msnf']),
        'sugars':   _status(sug_v,  sug_lo,          sug_hi),
        'pod':      _status(pod_v,  pod_lo,          pod_hi),
        'pac':      _status(pac_v,  pac_lo,          pac_hi),
        'st_water': _status(stw_v,  stw_lo,          stw_hi),
        'water':    _status(wat_v,  50,              72),
    }

    # ── Diagnósticos ──────────────────────────────────────────────────────────
    diags = []

    def diag(priority, key, condition, title, tip):
        if condition:
            diags.append({'priority': priority, 'key': key, 'title': title, 'tip': tip})

    # ── NINJA CREAMI ──────────────────────────────────────────────────────────
    if is_creami:
        diag(PRIORITY_CRITICAL, 'st_creami_high', st_v > 40,
             f"ST {st_v:.1f}% → BLOQUE DURO para Ninja Creami",
             "ST >40% produce bloque que la Creami no puede procesar. "
             "Síntoma: motor forzado, necesitas respin con leche. "
             "Reduce leche en polvo o añade 30-50 g más de leche líquida. "
             "Objetivo para Creami: 28-38% ST.")

        diag(PRIORITY_CRITICAL, 'pac_creami_low', 0 < pac_v < 100,
             f"PAC {pac_v:.0f} → NO CONGELA a −18 °C",
             "PAC muy bajo: la mezcla no solidifica completamente en el freezer doméstico. "
             "Añade dextrosa (PAC=1.9) o alulosa (PAC=1.0). Mínimo para Creami: PAC 120.")

        diag(PRIORITY_IMPORTANT, 'st_creami_warn', 38 < st_v <= 40,
             f"ST {st_v:.1f}% → puede necesitar respin en Creami",
             "Con ST entre 38-40% el bloque puede quedar duro. "
             "Deja templar 3-5 minutos antes de procesar. "
             "Si queda granuloso: respin con 1-2 cucharadas de leche fría.")

        diag(PRIORITY_IMPORTANT, 'fat_creami_high', fat_v > 15 and not is_sorbet,
             f"Grasa {fat_v:.1f}% → textura gomosa en Creami",
             "La Creami con exceso de grasa produce textura elástica/gomosa. "
             "Reduce crema o sustituye parte por leche líquida. "
             "Objetivo para Creami: grasa 4-15%.")

        diag(PRIORITY_IMPORTANT, 'water_libre_low', 0 < wat_v < 50,
             f"Agua libre {wat_v:.1f}% → mezcla muy concentrada",
             "Poca agua libre: la Creami puede atascarse o dar textura de pasta. "
             "Añade leche líquida o agua destilada hasta llegar a 54-62% agua libre.")

        diag(PRIORITY_ADJUSTABLE, 'creami_overrun_hint', True,
             "Overrun esperado en Ninja Creami: 40-60%",
             "La Creami incorpora más aire que el Pacojet. "
             "Mezclas con ST 28-35% producen overrun 50-60% (textura aireada). "
             "Mezclas con ST 35-40% producen overrun 35-45% (textura más densa).")

    # ── PACOJET ───────────────────────────────────────────────────────────────
    if is_paco:
        ratio_lactosa_msnf = totals['sugars'] / totals['msnf'] if totals['msnf'] > 0 else 0
        msnf_crit_efectivo = msnf_crit if ratio_lactosa_msnf > 0.3 else msnf_crit + 3.0

        diag(PRIORITY_CRITICAL, 'msnf_arenado', msnf_v > msnf_crit_efectivo,
             f"MSNF {msnf_v:.1f}% → ARENADO IRREVERSIBLE (umbral {msnf_crit_efectivo:.1f}%)",
             "Cristalización de lactosa — defecto permanente. "
             "Reduce leche en polvo descremada de inmediato. "
             "Sustituye por leche líquida o crema. "
             + (f"(Umbral elevado a {msnf_crit_efectivo:.1f}% porque el MSNF proviene principalmente "
                "de proteína sin lactosa como WPC/WPI.)"
                if msnf_crit_efectivo > msnf_crit else ""))

        diag(PRIORITY_CRITICAL, 'pac_pacojet_alto', pac_v > 450,
             f"PAC {pac_v:.0f} → NO CONGELA a −22 °C",
             "Mezcla no solidifica → beaker inutilizable. "
             "Elimina dextrosa o fructosa en exceso. "
             "Elimina alcohol si supera 40 g/kg.")

        diag(PRIORITY_IMPORTANT, 'stw_low', 0 < stw_v < 0.50,
             f"Ratio ST/Agua {stw_v:.3f} → demasiada agua libre (Pacojet)",
             "El raspado produce capas de hielo. "
             "Concentra sólidos: más leche en polvo o azúcar. "
             "En sorbetes de fruta acuosa: reduce pulpa.")

    # ── MANTECADORA ───────────────────────────────────────────────────────────
    if not is_creami and not is_paco:
        diag(PRIORITY_CRITICAL, 'msnf_arenado', msnf_v > msnf_crit,
             f"MSNF {msnf_v:.1f}% → ARENADO IRREVERSIBLE (umbral {msnf_crit}%)",
             "Cristalización de lactosa — defecto permanente. "
             "Reduce leche en polvo descremada.")

        diag(PRIORITY_ADJUSTABLE, 'pac_bajo_mantecadora', 0 < pac_v < pac_lo,
             f"PAC {pac_v:.0f} → bajo para mantecadora (mín {pac_lo})",
             "Helado duro al servir. "
             "① Dextrosa monohidrato (PAC=1.9). "
             "② Fructosa (PAC=1.9). "
             "③ Azúcar invertido.")

    # ── GENERALES ─────────────────────────────────────────────────────────────
    st_max = 40 if is_creami else 44
    diag(PRIORITY_CRITICAL, 'st_alto', st_v > st_max,
         f"ST {st_v:.1f}% → SOBRECONCENTRADO",
         "Textura de pasta, overrun imposible. "
         "Añade leche entera o agua hasta el rango objetivo.")

    diag(PRIORITY_IMPORTANT, 'st_bajo', 0 < st_v < st_lo,
         f"ST {st_v:.1f}% → bajos (mín {st_lo}%)",
         "Cristales grandes, cuerpo acuoso. "
         "① Leche en polvo descremada. "
         "② Inulina HP. "
         "③ Sustituye leche por crema.")

    diag(PRIORITY_IMPORTANT, 'grasa_baja', 0 < fat_v < fat_lo and not is_sorbet,
         f"Grasa {fat_v:.1f}% → baja (mín {fat_lo}%)",
         "Textura acuosa, poco cuerpo. "
         "① Sustituye leche por crema 35%. "
         "② Yema de huevo (32% MG + lecitina). "
         "③ Crema de coco si es vegano.")

    diag(PRIORITY_IMPORTANT, 'grasa_alta', fat_v > fat_hi + 2 and not is_creami,
         f"Grasa {fat_v:.1f}% → excesiva (máx {fat_hi}%)",
         "Sabor mantecoso, overrun pobre. "
         "Sustituye parte de crema por leche entera.")

    diag(PRIORITY_IMPORTANT, 'azucar_alto', sug_v > sug_hi + 2,
         f"Azúcares {sug_v:.1f}% → excesivos (máx {sug_hi}%)",
         "Helado muy blando, empalagoso. "
         "① Trehalosa (mismo ST, POD 0.45). "
         "② Isomalt. "
         "③ Inulina HP para mantener volumen.")

    diag(PRIORITY_IMPORTANT, 'msnf_bajo', 0 < msnf_v < tgt['msnf'][0] and not is_sorbet and not is_vegan,
         f"MSNF {msnf_v:.1f}% → bajo (mín {tgt['msnf'][0]}%)",
         "Poca estructura proteica, overrun pobre. "
         "Añade leche en polvo descremada (52% MSNF).")

    diag(PRIORITY_ADJUSTABLE, 'pod_bajo', 0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → dulzor bajo (mín {pod_lo})",
         "① Fructosa (POD 1.2). "
         "② 0.5 g/kg de Stevia Reb-A. "
         "③ 1-2 g/kg de sal marina potencia el dulce.")

    diag(PRIORITY_ADJUSTABLE, 'pod_alto', pod_v > pod_hi,
         f"POD {pod_v:.0f} → puede fatigar el paladar",
         "① Ácido cítrico 1-3 g/kg. "
         "② Sustituye fructosa por glucosa DE40 (POD 0.5). "
         "③ Sal marina equilibra.")

    diag(PRIORITY_ADJUSTABLE, 'azucar_bajo', 0 < sug_v < sug_lo,
         f"Azúcares {sug_v:.1f}% → bajos (mín {sug_lo}%)",
         "① Aumenta sacarosa o dextrosa. "
         "② Fructosa si es sorbete. "
         "③ Glucosa DE40 para textura sin exceso de dulzor.")

    # ── ALCOHOL — detección real por línea (MEJORA: reemplaza placeholder) ────
    alcohol_lines = _detect_alcohol_lines(lines_with_ings or [])
    if alcohol_lines:
        ethanol_total_g = sum(a['ethanol_g'] for a in alcohol_lines)
        ethanol_pct_mix = ethanol_total_g / m * 100

        nombres_alcohol = ", ".join(a['ingredient_name'] for a in alcohol_lines)

        diag(PRIORITY_CRITICAL, 'alcohol_exceso',
             ethanol_pct_mix > 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → NO CONGELA",
             f"Ingredientes: {nombres_alcohol}. "
             f"Etanol estimado: {ethanol_total_g:.1f} g en {m:.0f} g de mezcla. "
             "Con >4% etanol el punto de congelación cae por debajo de −18 °C. "
             "Reduce el licor o usa extracto sin alcohol.")

        diag(PRIORITY_IMPORTANT, 'alcohol_advertencia',
             2.5 < ethanol_pct_mix <= 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → textura blanda",
             f"Ingredientes: {nombres_alcohol}. "
             f"Etanol estimado: {ethanol_total_g:.1f} g. "
             "Entre 2.5-4%: congela pero puede quedar muy blando. "
             "Compensa con +20-30 g de dextrosa para subir el PAC de azúcares.")

        diag(PRIORITY_ADJUSTABLE, 'alcohol_info',
             ethanol_pct_mix <= 2.5,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol — dosis correcta",
             f"Ingredientes: {nombres_alcohol}. "
             f"Etanol estimado: {ethanol_total_g:.1f} g. "
             "Dosis dentro de rango seguro para congelación. "
             "El alcohol aporta aroma y suaviza ligeramente la textura.")

        # Guardar datos de alcohol en d para uso en UI/ticket
        d['alcohol_detected'] = {
            'lines':           alcohol_lines,
            'ethanol_total_g': round(ethanol_total_g, 1),
            'ethanol_pct':     round(ethanol_pct_mix, 2),
        }
    else:
        d['alcohol_detected'] = None

    d['diagnostics'] = diags
    return d


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE OVERRUN
# ─────────────────────────────────────────────────────────────────────────────

def overrun_calc(base_grams, overrun_pct, target_liters, machine='Ninja Creami Deluxe'):
    """
    Calcula overrun y rendimiento por máquina.
    Incluye campos 'volume_increase' y 'final_grams_per_liter'.
    """
    or_pct = overrun_pct / 100

    if 'Deluxe' in machine:
        cap = CREAMI_DELUXE_CAPACITY_G
    elif 'Standard' in machine:
        cap = CREAMI_STANDARD_CAPACITY_G
    else:
        cap = PACOJET_CAPACITY_ML

    base_needed    = target_liters * 1000 / (1 + or_pct)
    liters_prod    = base_grams / 1000 * (1 + or_pct)
    potes_exacto   = base_grams / cap if cap > 0 else 0
    potes_enteros  = int(potes_exacto)
    resto_g        = (potes_exacto - potes_enteros) * cap

    return {
        'base_needed_g':         base_needed,
        'liters_from_base':      liters_prod,
        'potes_completos':       potes_enteros,
        'potes_total':           potes_exacto,
        'masa_ultimo_pote_g':    resto_g,
        'masa_por_pote_g':       cap,
        'pacojet_beakers':       math.ceil(target_liters * 1000 / ((1 + or_pct) * 500)),
        'mix_per_beaker':        500 / (1 + or_pct),
        'volume_increase':       overrun_pct,
        'final_grams_per_liter': base_grams / liters_prod if liters_prod > 0 else 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# D5: ACTIVIDAD DE AGUA — ecuación de Ross
# ─────────────────────────────────────────────────────────────────────────────

def calc_water_activity(totals: dict) -> dict:
    """
    Estima la actividad de agua (Aw) usando la ecuación de Ross (1975).

    Ross: Aw ≈ n_agua / (n_agua + n_solutos)
    Incluye contribución de lactosa (55% del MSNF), minerales iónicos (8% MSNF),
    y azúcares con PM promedio ponderado de 270 g/mol.

    Retorna dict: aw, aw_pct, riesgo_micro, interpretacion, modelo.
    """
    m       = totals.get('grams', 0)
    water_g = totals.get('water', 0)
    sugars_g = totals.get('sugars', 0)
    msnf_g  = totals.get('msnf', 0)

    if water_g <= 0 or m <= 0:
        return {
            'aw': 1.0, 'aw_pct': 100.0,
            'riesgo_micro': 'sin_datos',
            'interpretacion': 'Sin agua en la mezcla — no se puede calcular Aw.',
            'modelo': 'Ross (1975)',
        }

    n_agua     = water_g / 18.015
    n_azucares = sugars_g / 270.0
    lactosa_g  = msnf_g * 0.55
    sal_g      = msnf_g * 0.08
    n_lactosa  = lactosa_g / 342.0
    n_sal      = sal_g / 58.44 * 2   # disociación iónica NaCl

    n_solutos_total = n_azucares + n_lactosa + n_sal
    aw = n_agua / (n_agua + n_solutos_total)
    aw = max(0.0, min(1.0, aw))

    if aw < 0.85:
        riesgo = 'bajo'
        interpretacion = (
            f"✅ Aw {aw:.3f} — actividad de agua muy baja. "
            "Crecimiento microbiano inhibido para la mayoría de patógenos. "
            "Estabilidad microbiológica excelente en almacenamiento congelado."
        )
    elif aw < 0.91:
        riesgo = 'medio'
        interpretacion = (
            f"⚠️ Aw {aw:.3f} — zona intermedia. "
            "Levaduras osmófilas pueden crecer si hay descongelación parcial. "
            "Mantener cadena de frío estricta. "
            "Considera añadir trehalosa (crioprotector) para mejorar estabilidad."
        )
    else:
        riesgo = 'alto'
        interpretacion = (
            f"🔴 Aw {aw:.3f} — actividad de agua alta (mezcla muy diluida). "
            "Normal para bases lácteas estándar — controlar pasteurización y "
            "tiempo entre mezcla y congelación (máximo 2 horas a temperatura ambiente)."
        )

    return {
        'aw':            round(aw, 4),
        'aw_pct':        round(aw * 100, 2),
        'riesgo_micro':  riesgo,
        'interpretacion': interpretacion,
        'modelo':        'Ross (1975)',
    }


# ─────────────────────────────────────────────────────────────────────────────
# RECOMENDACIONES DE ESTABILIZANTES
# ─────────────────────────────────────────────────────────────────────────────

def recommend_stabilizers(totals, pct, product_type, machine, ingredient_names=None):
    """
    Analiza la mezcla y recomienda estabilizantes personalizados.
    Retorna lista de dicts con: stabilizer, dose_g_per_kg, dose_g_recipe,
                                priority, reason, warning.
    """
    recs = []
    m = totals.get('grams', 0)
    if m <= 0:
        return recs

    water_pct = pct.get('water_pct', 0)
    fat_pct   = pct.get('fat_pct',   0)
    st_pct    = pct.get('st_pct',    0)

    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    names_lower = [n.lower() for n in (ingredient_names or [])]

    has_cmc       = any('cmc' in n or 'carboximetil' in n for n in names_lower)
    has_xantana   = any('xantana' in n or 'xanthan' in n for n in names_lower)
    has_pectina   = any('pectina' in n for n in names_lower)
    has_natulac   = any('natulac' in n for n in names_lower)
    has_lecitina  = any('lecitina' in n for n in names_lower)
    has_trehalosa = any('trehalosa' in n for n in names_lower)
    has_fruta_pectina = any(f in n for n in names_lower
                            for f in ['cambur', 'banana', 'mango', 'fresa', 'mora',
                                      'melocotón', 'durazno'])
    has_fruta_acida = any(f in n for n in names_lower
                          for f in ['maracuyá', 'limón', 'piña', 'naranja'])

    if is_sorbet and water_pct > 65 and not has_cmc and not has_xantana and not has_pectina:
        dose_cmc = 1.5 if water_pct > 72 else 1.2
        recs.append({
            'stabilizer':    'CMC + Xantana',
            'dose_g_per_kg': f'CMC: {dose_cmc} g/kg + Xantana: 0.8 g/kg',
            'dose_g_recipe': f'CMC: {dose_cmc * m/1000:.1f} g + Xantana: {0.8 * m/1000:.1f} g',
            'priority':      'necesario',
            'reason':        f'Sorbete sin lácteos con {water_pct:.1f}% agua libre. '
                             'Sin estabilizante: cristales visibles y textura de granizado.',
            'warning':       'En frutas ácidas (pH<4.5): usa más Xantana y menos CMC. '
                             'Xantana es estable en ácido, CMC se degrada a pH<4.'
        })

    elif not is_sorbet and fat_pct < 5 and water_pct > 63 and not has_cmc:
        dose_cmc = min(1.5, (water_pct - 58) / 10 * 1.5)
        recs.append({
            'stabilizer':    'CMC',
            'dose_g_per_kg': f'{dose_cmc:.1f} g/kg',
            'dose_g_recipe': f'{dose_cmc * m/1000:.1f} g',
            'priority':      'recomendado',
            'reason':        f'Grasa baja ({fat_pct:.1f}%) y agua libre alta ({water_pct:.1f}%). '
                             'La grasa retiene agua naturalmente; sin ella el CMC compensa.',
            'warning':       'Si ya tienes Natulac: reduce CMC a 0.5 g/kg máximo. '
                             'Si la fruta tiene pectina natural (cambur, mango): no añadas CMC.'
        })

    if has_natulac and has_cmc and has_fruta_pectina:
        recs.append({
            'stabilizer':    '⚠️ ADVERTENCIA — Triple gelificación',
            'dose_g_per_kg': 'Elimina el CMC',
            'dose_g_recipe': 'Elimina el CMC de la receta',
            'priority':      'necesario',
            'reason':        'Detectado: Natulac + CMC + fruta con pectina. '
                             'Causa triple gelificación → textura elástica/gomosa.',
            'warning':       'Regla fija: Natulac + fruta de pectina alta → NUNCA añadir CMC.'
        })

    if has_natulac and has_fruta_acida and not has_xantana:
        recs.append({
            'stabilizer':    'Xantana',
            'dose_g_per_kg': '0.8 g/kg',
            'dose_g_recipe': f'{0.8 * m/1000:.1f} g',
            'priority':      'recomendado',
            'reason':        'Natulac (carragenina) se degrada con pH<4.5. '
                             'La xantana compensa y es estable en ácido.',
            'warning':       None
        })

    if not has_lecitina and fat_pct > 4 and not is_sorbet:
        recs.append({
            'stabilizer':    'Lecitina de girasol',
            'dose_g_per_kg': '2.5-3 g/kg',
            'dose_g_recipe': f'{2.5 * m/1000:.1f}-{3.0 * m/1000:.1f} g',
            'priority':      'recomendado',
            'reason':        'Emulsiona la grasa en la base láctea. '
                             'Mejora cremosidad, reduce cristales, mejor liberación de aromas.',
            'warning':       'Premezclar en seco con la leche en polvo antes de añadir a líquidos.'
        })

    if st_pct >= 38 and water_pct <= 58 and not is_sorbet and not recs:
        recs.append({
            'stabilizer':    '✅ Sin espesante necesario',
            'dose_g_per_kg': '—',
            'dose_g_recipe': '—',
            'priority':      'opcional',
            'reason':        f'ST {st_pct:.1f}% y agua libre {water_pct:.1f}%. '
                             'Los sólidos naturales son suficientes para retener el agua.',
            'warning':       'Si añades espesante con estos sólidos → riesgo de textura gomosa.'
        })

    if not has_trehalosa and is_creami:
        recs.append({
            'stabilizer':    'Trehalosa (crioprotector)',
            'dose_g_per_kg': '12-18 g/kg',
            'dose_g_recipe': f'{15 * m/1000:.1f} g (referencia)',
            'priority':      'recomendado',
            'reason':        'Protege la microestructura durante el re-congelado. '
                             'Especialmente útil si no consumes el pote completo de una vez. '
                             'No aporta dulzor significativo (POD=0.45).',
            'warning':       None
        })

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE EDULCORANTES
# ─────────────────────────────────────────────────────────────────────────────

def analyze_sweeteners(lines_with_ings):
    """
    Desglosa el impacto de cada edulcorante en la receta.
    Retorna lista de dicts con contribución individual a POD, PAC, calorías y efecto de sabor.
    """
    sweetener_lines = []
    total_pod = 0
    total_pac = 0
    total_grams_all = sum(float(g) for _, g, _ in lines_with_ings if g) or 1

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g = float(grams)
        pod_contrib = g * float(ing.get('pod', 0))
        pac_contrib = g * float(ing.get('pac', 0))

        if pod_contrib > 0.5 or pac_contrib > 0.5 or float(ing.get('sugars', 0)) > 5:
            total_pod += pod_contrib
            total_pac += pac_contrib

            name_lower = ing['name'].lower()
            profile = None
            for key, prof in SWEETENER_PROFILES.items():
                if key in name_lower:
                    profile = prof
                    break

            pct_in_mix = g / total_grams_all * 100
            warning = None
            if 'eritritol' in name_lower and pct_in_mix > 1.5:
                warning = f"⚠️ Eritritol al {pct_in_mix:.1f}% → efecto mentolado probable. Máximo 1.5%"
            elif 'stevia' in name_lower and g > 0.5:
                warning = f"⚠️ Stevia {g:.1f} g → retrogusto posible. Máximo 0.3 g/kg"
            elif 'fructosa' in name_lower and pct_in_mix > 8:
                warning = f"⚠️ Fructosa alta ({pct_in_mix:.1f}%) → puede resultar empalagosa"

            sweetener_lines.append({
                'nombre':         ing['name'],
                'gramos':         g,
                'pod_contrib':    round(pod_contrib, 1),
                'pac_contrib':    round(pac_contrib, 1),
                'sugars_g':       round(g * float(ing.get('sugars', 0)) / 100, 1),
                'kcal_estimadas': round(g * float(ing.get('sugars', 0)) / 100 * 4, 1),
                'efecto_sabor':   profile[3] if profile else 'Sin perfil registrado',
                'perfil_dulzor':  profile[4] if profile else '—',
                'warning':        warning,
            })

    for s in sweetener_lines:
        s['pct_pod'] = round(s['pod_contrib'] / total_pod * 100, 1) if total_pod > 0 else 0
        s['pct_pac'] = round(s['pac_contrib'] / total_pac * 100, 1) if total_pac > 0 else 0

    return sweetener_lines


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE PROTEÍNAS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_protein(lines_with_ings, totals, pct, product_type='Helado/Gelato'):
    """
    Analiza el contenido proteico de la receta por fuente y emite recomendaciones.

    Estrategia de estimación
    ------------------------
    Cada ingrediente puede tener proteína en dos formas en la BD:
      a) protein_in_total=True  → proteína_g = grams × protein_fraction
      b) protein_in_total=False → proteína_g = msnf_g × protein_fraction
         (para leches líquidas donde el MSNF ya está calculado por calc_line)

    Para ingredientes sin perfil en PROTEIN_PROFILES se aplica el fallback
    del motor de calorías existente: proteína ≈ MSNF × 0.36 (fracción media
    de proteína en el MSNF de leche, Goff & Hartel 2013).

    Retorna
    -------
    dict con:
      fuentes          — lista de dicts por ingrediente con proteína detectada
      protein_total_g  — gramos totales de proteína en la mezcla
      protein_pct      — % proteína sobre masa total
      protein_per_100g — g de proteína por 100g de mezcla
      tipo_dominante   — tipo de proteína mayoritario ('caseína'|'suero'|'vegetal'|'huevo'|'lácteo_mixto')
      score_espuma     — 1-5 ponderado por gramos (proxy de capacidad de overrun)
      score_gel        — 1-5 ponderado por gramos (proxy de cuerpo en congelación)
      claim            — None | 'fuente_proteina' | 'alto_proteina'
      advertencias     — lista de strings con alertas de proceso
      recomendaciones  — lista de dicts con ajustes sugeridos
    """
    from constants import (
        PROTEIN_PROFILES, PROTEIN_CLAIM_THRESHOLDS,
        PROTEIN_FUNCTIONAL_TARGETS,
        PRODUCT_LIGERO, PRODUCT_VEGANO, PRODUCT_SORBETE, PRODUCT_GRANITA,
    )

    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_light   = product_type == PRODUCT_LIGERO
    is_vegan   = product_type == PRODUCT_VEGANO
    is_sorbet  = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)

    fuentes        = []
    protein_total  = 0.0
    espuma_sum     = 0.0
    gel_sum        = 0.0
    peso_sum       = 0.0
    tipo_pesos     = {}   # {tipo: gramos_proteina}
    advertencias   = []

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g        = float(grams)
        name_low = ing.get('name', '').lower()

        # Buscar perfil por substring (más largo primero para evitar match parcial)
        perfil = None
        matched_key = ''
        for key in sorted(PROTEIN_PROFILES.keys(), key=len, reverse=True):
            if key in name_low:
                perfil = PROTEIN_PROFILES[key]
                matched_key = key
                break

        if perfil:
            if perfil['protein_in_total']:
                prot_g = g * perfil['protein_fraction']
            else:
                # fracción sobre MSNF del ingrediente
                msnf_g = g * float(ing.get('msnf', 0)) / 100
                prot_g = msnf_g * perfil['protein_fraction']
        else:
            # Fallback: proteína ≈ MSNF × 0.36 (misma constante que calc_calories)
            msnf_g = g * float(ing.get('msnf', 0)) / 100
            prot_g = msnf_g * 0.36
            if msnf_g > 0:
                perfil = {
                    'tipo': 'lácteo_mixto',
                    'solubilidad': 'micelar',
                    't_desnaturaliz_c': 72,
                    'capacidad_espuma': 2,
                    'capacidad_gel': 2,
                    'nota': 'Estimado como lácteo mixto (fallback 36% del MSNF).',
                }

        if prot_g < 0.05:
            continue   # contribución despreciable (<0.05g)

        protein_total += prot_g
        tipo = perfil['tipo'] if perfil else 'lácteo_mixto'
        tipo_pesos[tipo] = tipo_pesos.get(tipo, 0) + prot_g

        # Ponderación de scores por gramos de proteína
        esp = perfil['capacidad_espuma'] if perfil else 2
        gel = perfil['capacidad_gel']    if perfil else 2
        espuma_sum += esp * prot_g
        gel_sum    += gel * prot_g
        peso_sum   += prot_g

        # Advertencia de temperatura de desnaturalización
        t_denat = perfil.get('t_desnaturaliz_c', 999) if perfil else 999
        if t_denat < 75:
            advertencias.append(
                f"⚠️ {ing['name']}: desnaturaliza a {t_denat}°C — "
                "no pasteurizar sobre esa temperatura o perderás funcionalidad espumante."
            )

        fuentes.append({
            'nombre':        ing['name'],
            'gramos':        g,
            'proteina_g':    round(prot_g, 2),
            'tipo':          tipo,
            'solubilidad':   perfil.get('solubilidad', '—') if perfil else '—',
            'espuma':        esp,
            'gel':           gel,
            't_denat':       t_denat if t_denat < 999 else None,
            'nota':          perfil.get('nota', '') if perfil else '',
            'perfil_clave':  matched_key or '(fallback)',
        })

    protein_pct     = protein_total / m * 100
    protein_per_100 = protein_pct   # idéntico — claridad en API

    score_espuma = espuma_sum / peso_sum if peso_sum > 0 else 0
    score_gel    = gel_sum    / peso_sum if peso_sum > 0 else 0

    tipo_dominante = max(tipo_pesos, key=tipo_pesos.get) if tipo_pesos else 'n/d'

    # Pct por tipo
    pct_por_tipo = {
        t: round(v / protein_total * 100, 1)
        for t, v in tipo_pesos.items()
    } if protein_total > 0 else {}

    # Claim nutricional
    thr = PROTEIN_CLAIM_THRESHOLDS
    if protein_per_100 >= thr['alto_proteina']:
        claim = 'alto_proteina'
    elif protein_per_100 >= thr['fuente_proteina']:
        claim = 'fuente_proteina'
    else:
        claim = None

    # ── Recomendaciones ───────────────────────────────────────────────────────
    tgt = PROTEIN_FUNCTIONAL_TARGETS
    recomendaciones = []

    def rec(priority, titulo, texto):
        recomendaciones.append({'priority': priority, 'titulo': titulo, 'texto': texto})

    # 1. Mínimo estructural para overrun
    if 0 < protein_pct < tgt['minimo_estructura'] and not is_sorbet:
        deficit = tgt['minimo_estructura'] - protein_pct
        rec('important',
            f"Proteína {protein_pct:.1f}% — por debajo del mínimo estructural ({tgt['minimo_estructura']}%)",
            f"Con menos de {tgt['minimo_estructura']}% de proteína el helado tiene poco cuerpo "
            f"y el overrun cae por debajo del 30%. "
            f"Necesitas ~{deficit * m / 100:.0f} g más de proteína. "
            "Opciones: ① LPD (+52g MSNF por 100g) ② WPC 80% ③ Caseína micelar.")

    # 2. Óptimo para helado light
    if is_light and protein_pct < tgt['optimo_light']:
        rec('important',
            f"Helado Ligero: proteína {protein_pct:.1f}% — debajo del óptimo ({tgt['optimo_light']}%)",
            f"En helados light la proteína reemplaza parte de la función de la grasa. "
            f"Objetivo: {tgt['optimo_light']}% proteína. "
            "Caseína micelar (0.88 prot/g) es la mejor opción: "
            "aporta cuerpo sin lactosa extra ni riesgo de arenado.")

    # 3. Exceso — riesgo de textura calcárea
    if protein_pct > tgt['maximo_recomendado']:
        rec('critical',
            f"Proteína {protein_pct:.1f}% — exceso (máx recomendado {tgt['maximo_recomendado']}%)",
            "Por encima del 12% la proteína no hidratada forma agregados en congelación → "
            "textura calcárea, grumosa o harinosa. "
            "Reduce WPC/WPI y sustituye por caseína micelar (gelifica mejor a bajas dosis) "
            "o por MSNF de leche líquida.")

    # 4. Mezcla vegana sin proteína
    if is_vegan and protein_total < 1.0:
        rec('important',
            "Gelato Vegano sin fuente proteica",
            "Sin proteína la emulsión vegetal es inestable → separación de fases en congelación. "
            "Añade: ① Proteína de guisante 20-30g/kg "
            "② Proteína de soja 15-25g/kg "
            "③ WPI (si no requiere ser 100% vegetal) 20-30g/kg.")

    # 5. Temperatura de pasteurización cruzada
    tiene_suero  = 'suero' in tipo_pesos
    tiene_caseina = 'caseína' in tipo_pesos or 'lácteo_mixto' in tipo_pesos
    if tiene_suero and tiene_caseina:
        rec('adjustable',
            "Mezcla caseína + suero: temperatura de pasteurización crítica",
            "Con WPC/WPI en la misma receta que caseína, pasteurizar a 72-75°C/15s. "
            "No superar 80°C o el suero desnaturaliza y pierde capacidad espumante. "
            "Si usas WPI solo, baja la temperatura a 68-70°C.")

    # 6. Score de espuma bajo para tipo de producto
    if score_espuma < 2.5 and not is_sorbet and not is_vegan:
        rec('adjustable',
            f"Score espuma {score_espuma:.1f}/5 — overrun puede ser limitado",
            "Las proteínas actuales tienen baja capacidad espumante. "
            "Para mejorar overrun: ① añade WPC (espuma=5) 20-30g/kg "
            "② clara de huevo pasteurizada 30-50g/kg "
            "③ suero de leche líquido 50-100g/kg.")

    # 7. Proteína vegetal dominante — alerta de sabor
    if tipo_dominante == 'vegetal' and protein_pct > 3:
        rec('adjustable',
            "Proteína vegetal dominante — gestión de sabor",
            "Proteínas vegetales (guisante, arroz) tienen notas terrosas/amargas perceptibles "
            "sobre 3% de la mezcla. "
            "Estrategias: ① combinar con 0.3-0.5% extracto de vainilla "
            "② usar cacao alcalino ≥15g/kg (enmascara completamente) "
            "③ mezclar guisante+arroz 50/50 (perfil de aminoácidos más completo y sabor más neutro).")

    return {
        'fuentes':         fuentes,
        'protein_total_g': round(protein_total, 2),
        'protein_pct':     round(protein_pct, 2),
        'protein_per_100g': round(protein_per_100, 2),
        'tipo_dominante':  tipo_dominante,
        'pct_por_tipo':    pct_por_tipo,
        'score_espuma':    round(score_espuma, 1),
        'score_gel':       round(score_gel, 1),
        'claim':           claim,
        'advertencias':    advertencias,
        'recomendaciones': recomendaciones,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TICKET DE PRODUCCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def format_production_ticket(
    recipe_name: str,
    product_type: str,
    machine: str,
    ingredient_names: list,
    lines_for_calculator: list,
    totals: dict,
    pct: dict,
    derived: dict,
    kcal: dict,
    protein_data: dict = None,
    diags_excluir: set = None,
) -> str:
    """
    Genera el texto del ticket de producción.
    protein_data : salida de analyze_protein() — opcional.
    """
    if diags_excluir is None:
        diags_excluir = DIAGS_EXCLUIR_TICKET

    ing_lines = "\n".join(
        f"  {n:<38} {g:>7.1f} g"
        for (_, g, _), n in zip(lines_for_calculator, ingredient_names)
    )

    def sym(k):
        s = derived.get("status", {}).get(k, "ok")
        return "✅" if s == "ok" else "🔺" if s == "high" else "🔻"

    diags_activos = [
        d for d in derived.get("diagnostics", [])
        if d["key"] not in diags_excluir
    ]
    diag_block = ""
    if diags_activos:
        diag_block = "\nDIAGNÓSTICOS:\n" + "\n".join(
            f"  [{d['priority'].upper()}] {d['title']}"
            for d in diags_activos
        )

    # Bloque de alcohol si fue detectado
    alcohol_block = ""
    alc = derived.get('alcohol_detected')
    if alc:
        alcohol_block = (
            f"\nALCOHOL DETECTADO:\n"
            f"  Etanol estimado: {alc['ethanol_total_g']:.1f} g "
            f"({alc['ethanol_pct']:.2f}% de la mezcla)\n"
            + "\n".join(
                f"  · {a['ingredient_name']}: {a['ethanol_g']:.1f} g etanol"
                for a in alc['lines']
            )
        )

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    if is_creami:
        instrucciones = (
            "INSTRUCCIONES NINJA CREAMI:\n"
            "  → Congelar 24 h a −18 °C mínimo\n"
            '  → Procesar función "Ice Cream"\n'
            "  → Si granuloso: respin sin añadir líquido\n"
            "  → Si muy duro: templar 3-5 min y reintentar"
        )
    elif machine == MACHINE_PACOJET:
        instrucciones = (
            "INSTRUCCIONES PACOJET:\n"
            "  → Verter en beaker, congelar 24 h a −22 °C\n"
            "  → Pacotizar sin descongelar"
        )
    else:
        instrucciones = ""

    return (
        "\n"
        "══════════════════════════════════════════════\n"
        "🧊  CEPILLAO' GELATO STUDIO — TICKET DE PRODUCCIÓN\n"
        "══════════════════════════════════════════════\n"
        f"Receta:    {recipe_name or '—'}\n"
        f"Tipo:      {product_type}\n"
        f"Máquina:   {machine}\n"
        f"Fecha:     {datetime.now().strftime('%d/%m/%Y  %H:%M')}\n"
        "\n"
        "INGREDIENTES:\n"
        f"{ing_lines}\n"
        "\n"
        "PARÁMETROS:\n"
        f"  Masa total:     {totals['grams']:.1f} g\n"
        f"  ST:             {pct.get('st_pct', 0):.1f}%   {sym('st')}\n"
        f"  Grasa:          {pct.get('fat_pct', 0):.1f}%   {sym('fat')}\n"
        f"  MSNF:           {pct.get('msnf_pct', 0):.1f}%   {sym('msnf')}\n"
        f"  Azúcares:       {pct.get('sugars_pct', 0):.1f}%   {sym('sugars')}\n"
        f"  Agua libre:     {pct.get('water_pct', 0):.1f}%   {sym('water')}\n"
        f"  POD:            {pct.get('pod_total', 0):.0f}      {sym('pod')}\n"
        f"  PAC:            {pct.get('pac_total', 0):.0f}      {sym('pac')}\n"
        f"  ΔT crioscopía:  {derived.get('delta_t', 0):.2f} °C\n"
        f"  kcal / 100 g:   {kcal['kcal_per_100g']:.0f} kcal\n"
        f"  Costo estimado: ${totals['cost']:.2f}\n"
        + (f"  Proteína:       {protein_data['protein_per_100g']:.1f} g/100g"
           + (f"  [{protein_data['claim'].replace('_',' ').upper()}]"
              if protein_data.get('claim') else "")
           + f"  ({protein_data['tipo_dominante']})\n"
           if protein_data else "")
        + f"{alcohol_block}"
        f"{diag_block}\n"
        f"{instrucciones}\n"
        "══════════════════════════════════════════════"
    )
