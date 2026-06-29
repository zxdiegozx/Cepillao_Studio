"""Pure calculation engine — sin dependencias externas."""

import math
from datetime import datetime

from constants import (
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO,
    PRODUCT_FROZEN,  PRODUCT_LIGERO,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    MACHINE_MANTECADORA,
    PRIORITY_CRITICAL, PRIORITY_IMPORTANT, PRIORITY_ADJUSTABLE,
    DIAGS_EXCLUIR_TICKET, CATEGORY_ALCOHOL, ALCOHOL_ETHANOL_FRACTION,
    PROTEIN_PROFILES, PROTEIN_CLAIM_THRESHOLDS, PROTEIN_FUNCTIONAL_TARGETS,
    CALORIE_CLASSIFICATION, PROTEIN_CLASSIFICATION,
    CREAMI_OVERRUN_PCT,
)

# ── Capacidades de máquinas ───────────────────────────────────────────────────
CREAMI_DELUXE_CAPACITY_G   = 640   # gramos útiles, pote 24oz
CREAMI_STANDARD_CAPACITY_G = 430   # gramos útiles, pote 16oz

# ── Constantes calóricas ──────────────────────────────────────────────────────
KCAL_FAT     = 9.0
KCAL_PROTEIN = 3.5
KCAL_SUGAR   = 4.0
KCAL_OTHER   = 2.5
KCAL_ALCOHOL = 7.0

# ── Perfil de temperatura Ninja Creami ────────────────────────────────────────
CREAMI_FREEZE_TEMP_C    = -18.0
CREAMI_FREEZE_HOURS_MIN = 24
CREAMI_DELTA_T_MIN      = -1.5

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
    'isomalt':          (0.45, 0.50, 2.0, 'Muy suave, ideal para inclusiones duras',     'lento'),
    'glucosa':          (0.75, 1.90, 4.0, 'Frescor suave, mejora textura extensible',    'inmediato'),
    'azucar invertido': (1.30, 1.90, 4.0, 'Dulzor intenso, higroscópico, suaviza',       'inmediato'),
    'stevia':           (0.0,  0.0,  0.0, 'Sin PAC/POD propio — corrector dulzor',       'tardío'),
    'splenda':          (0.0,  0.0,  0.0, 'Mezcla eritritol+stevia — sin POD/PAC base', 'tardío'),
}


# ─────────────────────────────────────────────────────────────────────────────
# TARGETS POR MÁQUINA Y TIPO (incluye ratio ST/agua)
# ─────────────────────────────────────────────────────────────────────────────

def _get_targets(product_type='Helado/Gelato', machine='Ninja Creami Deluxe'):
    """
    Retorna rangos de composición según máquina y tipo de producto.
    Todos los rangos son (lo, hi).
    Incluye st_water: ratio sólidos totales / agua libre (relevante para AMBAS máquinas).
    """
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    is_vegan  = product_type == PRODUCT_VEGANO
    is_frozen = product_type == PRODUCT_FROZEN
    is_light  = product_type == PRODUCT_LIGERO
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

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

    else:  # Mantecadora Tradicional
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
    """Semáforo: 'empty' | 'low' | 'ok' | 'high'."""
    if val == 0 and lo is not None and lo > 0:
        return 'empty'
    if lo is not None and val < lo:
        return 'low'
    if hi is not None and val > hi:
        return 'high'
    return 'ok'


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO LINEAL
# ─────────────────────────────────────────────────────────────────────────────

def calc_line(ing, grams):
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
# CÁLCULO DE CALORÍAS + CLASIFICACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def calc_calories(totals, lines_with_ings=None):
    """
    Estima calorías y emite clasificación saludable / proteica.

    Retorna dict: kcal_total, kcal_per_100g, kcal_per_pote_deluxe,
                  clasificacion_calorica (dict), clasificacion_proteica (dict).
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {'kcal_total': 0, 'kcal_per_100g': 0, 'kcal_per_pote_deluxe': 0,
                'clasificacion_calorica': None, 'clasificacion_proteica': None}

    protein_g = totals.get('msnf', 0) * 0.35

    kcal = (
        totals.get('fat', 0)      * KCAL_FAT     +
        protein_g                  * KCAL_PROTEIN +
        totals.get('sugars', 0)   * KCAL_SUGAR   +
        totals.get('other_st', 0) * KCAL_OTHER
    )

    if lines_with_ings:
        for ing, grams, _ in lines_with_ings:
            if not ing or not grams:
                continue
            if ing.get('zero_calorie', 0):
                g = float(grams)
                kcal -= g * float(ing.get('sugars', 0)) / 100 * KCAL_SUGAR

        alcohol_lines = _detect_alcohol_lines(lines_with_ings)
        for a in alcohol_lines:
            kcal += a['ethanol_g'] * KCAL_ALCOHOL

    kcal = max(0, kcal)
    kcal_per_100g = kcal / m * 100
    kcal_per_pote = kcal_per_100g * CREAMI_DELUXE_CAPACITY_G / 100

    # ── Clasificación calórica ────────────────────────────────────────────────
    cal_class = None
    for key, (max_k, etiqueta, emoji, desc) in CALORIE_CLASSIFICATION.items():
        if kcal_per_100g <= max_k:
            cal_class = {
                'key':      key,
                'etiqueta': etiqueta,
                'emoji':    emoji,
                'desc':     desc,
                'valor':    round(kcal_per_100g, 0),
            }
            break
    if cal_class is None:
        # fallback muy_denso
        _, etiqueta, emoji, desc = list(CALORIE_CLASSIFICATION.values())[-1]
        cal_class = {'key': 'muy_denso', 'etiqueta': etiqueta, 'emoji': emoji,
                     'desc': desc, 'valor': round(kcal_per_100g, 0)}

    # ── Clasificación proteica (usando MSNF proxy) ────────────────────────────
    protein_per_100g = protein_g / m * 100
    prot_class = None
    for key, (min_p, max_p, etiqueta, emoji, desc) in PROTEIN_CLASSIFICATION.items():
        if min_p <= protein_per_100g < max_p:
            prot_class = {
                'key':      key,
                'etiqueta': etiqueta,
                'emoji':    emoji,
                'desc':     desc,
                'valor':    round(protein_per_100g, 1),
            }
            break

    return {
        'kcal_total':              round(kcal, 0),
        'kcal_per_100g':           round(kcal_per_100g, 0),
        'kcal_per_pote_deluxe':    round(kcal_per_pote, 0),
        'clasificacion_calorica':  cal_class,
        'clasificacion_proteica':  prot_class,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE ALCOHOL
# ─────────────────────────────────────────────────────────────────────────────

def _detect_alcohol_lines(lines_with_ings):
    result = []
    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        name_low = ing.get('name', '').lower()
        cat_low  = ing.get('category', '').lower()
        fraction = 0.0
        for key, frac in ALCOHOL_ETHANOL_FRACTION.items():
            if key in name_low:
                fraction = frac
                break
        if fraction == 0.0 and 'alcohol' in cat_low:
            fraction = 0.316  # fallback genérico 40% vol
        if fraction > 0:
            g = float(grams)
            result.append({
                'ingredient_name': ing.get('name', '?'),
                'grams':           g,
                'ethanol_fraction': fraction,
                'ethanol_g':       round(g * fraction, 2),
            })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIÓN BRIX
# ─────────────────────────────────────────────────────────────────────────────

def validate_brix(measured_brix: float, totals: dict) -> dict:
    m = totals.get('grams', 0)
    if m <= 0:
        return {}
    sugars_g = totals.get('sugars', 0)
    msnf_g   = totals.get('msnf', 0)
    brix_calc       = sugars_g / m * 100
    brix_con_msnf   = (sugars_g + msnf_g * 0.55) / m * 100
    delta           = measured_brix - brix_con_msnf
    sugars_est      = measured_brix * m / 100

    if abs(delta) <= 2:
        interp = f"✅ Brix medido ({measured_brix:.1f}°) coincide con lo calculado ({brix_con_msnf:.1f}°). Receta correcta."
    elif delta > 2:
        interp = f"⚠️ Brix medido superior al esperado (+{delta:.1f}°). Posible azúcar adicional no declarado o fruta más madura."
    else:
        interp = f"⚠️ Brix medido inferior al esperado ({delta:.1f}°). Posible pérdida por fermentación, dilución o error en pesaje."

    return {
        'brix_calculado':     round(brix_calc, 1),
        'brix_con_msnf':      round(brix_con_msnf, 1),
        'delta_brix':         round(delta, 2),
        'sugars_estimados_g': round(sugars_est, 1),
        'interpretacion':     interp,
    }


# ─────────────────────────────────────────────────────────────────────────────
# OVERRUN — Ninja Creami (fijo) vs Mantecadora (configurable)
# ─────────────────────────────────────────────────────────────────────────────

def overrun_calc(base_grams, overrun_pct, target_liters, machine='Ninja Creami Deluxe'):
    """
    Ninja Creami: overrun es FIJO (mecánico, ~40-60%).
    Solo calcula potes obtenidos y masa final estimada con overrun fijo.
    No es relevante el overrun objetivo ni los litros objetivo para Creami.

    Mantecadora Tradicional: overrun configurable + cálculo completo de producción.
    """
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

    if is_creami:
        # Overrun fijo estimado mecánicamente por la Creami
        overrun_fijo_pct = CREAMI_OVERRUN_PCT.get(machine, 50)
        or_factor        = overrun_fijo_pct / 100

        cap = CREAMI_DELUXE_CAPACITY_G if machine == MACHINE_CREAMI_DELUXE else CREAMI_STANDARD_CAPACITY_G
        potes_exacto  = base_grams / cap if cap > 0 else 0
        potes_enteros = int(potes_exacto)
        resto_g       = (potes_exacto - potes_enteros) * cap

        # Masa final incluye el aire incorporado (overrun)
        masa_final_g      = base_grams * (1 + or_factor)
        volumen_final_ml  = masa_final_g          # densidad ≈ 1 g/ml pre-congelado
        potes_con_overrun = masa_final_g / cap if cap > 0 else 0

        return {
            'is_creami':             True,
            'overrun_fijo_pct':      overrun_fijo_pct,
            'masa_base_g':           base_grams,
            'masa_final_estimada_g': round(masa_final_g, 0),
            'volumen_estimado_ml':   round(volumen_final_ml, 0),
            'potes_base':            round(potes_exacto, 2),
            'potes_completos':       potes_enteros,
            'masa_ultimo_pote_g':    round(resto_g, 0),
            'masa_por_pote_g':       cap,
            'potes_con_overrun':     round(potes_con_overrun, 2),
            # Campos de compatibilidad backward (no usados en UI Creami)
            'base_needed_g':         base_grams,
            'liters_from_base':      round(volumen_final_ml / 1000, 2),
            'volume_increase':       overrun_fijo_pct,
            'final_grams_per_liter': round(base_grams / (volumen_final_ml / 1000), 0) if volumen_final_ml > 0 else 0,
        }

    else:
        # Mantecadora Tradicional — overrun y litros son configurables
        or_pct         = overrun_pct / 100
        base_needed    = target_liters * 1000 / (1 + or_pct)
        liters_prod    = base_grams / 1000 * (1 + or_pct)

        return {
            'is_creami':             False,
            'overrun_pct':           overrun_pct,
            'base_needed_g':         round(base_needed, 0),
            'liters_from_base':      round(liters_prod, 2),
            'target_liters':         target_liters,
            'volume_increase':       overrun_pct,
            'final_grams_per_liter': round(base_grams / liters_prod, 0) if liters_prod > 0 else 0,
            # No aplicable:
            'potes_completos':       0,
            'masa_ultimo_pote_g':    0,
            'masa_por_pote_g':       0,
            'potes_base':            0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVIDAD DE AGUA — ecuación de Ross
# ─────────────────────────────────────────────────────────────────────────────

def calc_water_activity(totals: dict) -> dict:
    m        = totals.get('grams', 0)
    water_g  = totals.get('water', 0)
    sugars_g = totals.get('sugars', 0)
    msnf_g   = totals.get('msnf', 0)

    if water_g <= 0 or m <= 0:
        return {'aw': 1.0, 'aw_pct': 100.0, 'riesgo_micro': 'sin_datos',
                'interpretacion': 'Sin agua — no calculable.', 'modelo': 'Ross (1975)'}

    n_agua     = water_g / 18.015
    n_azucares = sugars_g / 270.0
    lactosa_g  = msnf_g * 0.55
    sal_g      = msnf_g * 0.08
    n_lactosa  = lactosa_g / 342.0
    n_sal      = sal_g / 58.44 * 2
    n_solutos  = n_azucares + n_lactosa + n_sal
    aw = max(0.0, min(1.0, n_agua / (n_agua + n_solutos)))

    if aw < 0.85:
        riesgo = 'bajo'
        interp = (f"✅ Aw {aw:.3f} — muy baja. Crecimiento microbiano inhibido. "
                  "Estabilidad microbiológica excelente en almacenamiento congelado.")
    elif aw < 0.91:
        riesgo = 'medio'
        interp = (f"⚠️ Aw {aw:.3f} — zona intermedia. "
                  "Levaduras osmófilas pueden crecer si hay descongelación parcial. "
                  "Mantener cadena de frío estricta.")
    else:
        riesgo = 'alto'
        interp = (f"🔴 Aw {aw:.3f} — alta (mezcla muy diluida). "
                  "Normal en bases lácteas estándar — controla pasteurización y tiempo a T° ambiente.")

    return {'aw': round(aw, 4), 'aw_pct': round(aw * 100, 2),
            'riesgo_micro': riesgo, 'interpretacion': interp, 'modelo': 'Ross (1975)'}


# ─────────────────────────────────────────────────────────────────────────────
# RECOMENDACIONES DE ESTABILIZANTES — genéricas, basadas en deficiencia
# ─────────────────────────────────────────────────────────────────────────────

def recommend_stabilizers(totals, pct, product_type, machine, ingredient_names=None,
                          config=None):
    """
    Recomienda estabilizantes en función de las deficiencias de la mezcla.
    Las recomendaciones son GENÉRICAS (familia de ingrediente, no marca específica).
    config: dict opcional con overrides de parámetros (viene de st.session_state config).
    """
    recs = []
    m         = totals.get('grams', 0)
    water_pct = pct.get('water_pct', 0)
    fat_pct   = pct.get('fat_pct', 0)
    st_pct    = pct.get('st_pct', 0)

    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    names_lower = [n.lower() for n in (ingredient_names or [])]

    has_cmc           = any('cmc' in n or 'carboximetil' in n for n in names_lower)
    has_xantana       = any('xantana' in n or 'xanthan' in n for n in names_lower)
    has_pectina       = any('pectina' in n for n in names_lower)
    has_natulac       = any('natulac' in n for n in names_lower)
    has_lecitina      = any('lecitina' in n for n in names_lower)
    has_trehalosa     = any('trehalosa' in n for n in names_lower)
    has_goma_guar     = any('guar' in n for n in names_lower)
    has_algarro        = any('algarro' in n or 'algarroba' in n or 'lbg' in n for n in names_lower)
    has_fruta_pectina = any(f in n for n in names_lower
                            for f in ['cambur', 'banana', 'mango', 'fresa', 'mora',
                                      'melocotón', 'durazno'])
    has_fruta_acida   = any(f in n for n in names_lower
                            for f in ['maracuyá', 'limón', 'piña', 'naranja'])

    # ── TRIPLE GELIFICACIÓN (Natulac + CMC + fruta con pectina) ──────────────
    if has_natulac and has_cmc and has_fruta_pectina:
        recs.append({
            'stabilizer':    '⚠️ ADVERTENCIA — Triple gelificación',
            'dose_g_per_kg': 'Elimina el CMC',
            'dose_g_recipe': 'Elimina el CMC de la receta',
            'priority':      'necesario',
            'reason':        'Detectado: carragenina (Natulac) + CMC + fruta con pectina. '
                             'Causa triple gelificación → textura elástica/gomosa irreversible.',
            'warning':       'Regla fija: carragenina + fruta de pectina alta → NUNCA añadir CMC.',
            'alternativas':  [],
        })

    # ── SORBETE SIN ESTABILIZANTE ─────────────────────────────────────────────
    if is_sorbet and water_pct > 65 and not has_cmc and not has_xantana and not has_pectina and not has_goma_guar:
        dose_cmc = 1.5 if water_pct > 72 else 1.2
        recs.append({
            'stabilizer':    'Hidrocoloide hidrofílico',
            'dose_g_per_kg': f'1.0–1.5 g/kg (ajustar al agua libre)',
            'dose_g_recipe': f'~{dose_cmc * m / 1000:.1f} g',
            'priority':      'necesario',
            'reason':        f'Sorbete con {water_pct:.1f}% agua libre sin estabilizante. '
                             'Sin hidrocoloide: cristales visibles y textura de granizado.',
            'warning':       'En frutas ácidas (pH<4.5): priorizar Xantana sobre CMC.',
            'alternativas':  [
                '① CMC (carboximetilcelulosa): 1.0–1.5 g/kg — hidrofílico clásico, '
                   'muy efectivo en pH neutro. Degradación parcial en pH<4.',
                '② Goma Xantana: 0.5–0.8 g/kg — estable en ácido, excelente cuerpo, '
                   'no cambia dulzor. Usar sola o combinada con CMC.',
                '③ Pectina LM (baja metoxilación): 1–2 g/kg — natural, ideal con frutas '
                   'ricas en calcio. Gelifica en frío sin necesidad de iones.',
                '④ Goma Guar: 1.0–1.5 g/kg — muy hidrofílica, económica, '
                   'buena sinergia con Xantana (ratio 2:1 Guar:Xantana).',
                '⑤ LBG (algarroba): 1.0–2.0 g/kg — sinergia con Xantana para cuerpo '
                   'cremoso, pero requiere temperatura >80°C para hidratar.',
            ],
        })

    # ── HELADO SIN GRASA, AGUA ALTA ──────────────────────────────────────────
    elif not is_sorbet and fat_pct < 5 and water_pct > 63 and not has_cmc and not has_xantana:
        dose_cmc = min(1.5, (water_pct - 58) / 10 * 1.5)
        recs.append({
            'stabilizer':    'Espesante reticulante',
            'dose_g_per_kg': f'{dose_cmc:.1f}–{min(dose_cmc + 0.3, 1.5):.1f} g/kg',
            'dose_g_recipe': f'~{dose_cmc * m / 1000:.1f} g',
            'priority':      'recomendado',
            'reason':        f'Grasa baja ({fat_pct:.1f}%) + agua libre alta ({water_pct:.1f}%). '
                             'Sin grasa que retenga agua → cristalización acelerada.',
            'warning':       'No combinar con carragenina si hay fruta con pectina alta.',
            'alternativas':  [
                '① CMC: 0.8–1.5 g/kg — opción estándar para helados light/bajos en grasa.',
                '② Goma Xantana: 0.3–0.6 g/kg — se puede combinar con CMC para sinergia.',
                '③ Inulina HP (cadena larga): 30–50 g/kg — reemplaza grasa '
                   'funcionalmente, aporta cuerpo y cremosidad sin calorías.',
                '④ Proteína de suero (WPC/WPI): 20–40 g/kg — aporta cuerpo, '
                   'mejora overrun y reduce cristalización (doble función: proteína + estabilizante).',
            ],
        })

    # ── CARRAGENINA CON FRUTA ÁCIDA (sin Xantana) ────────────────────────────
    if has_natulac and has_fruta_acida and not has_xantana:
        recs.append({
            'stabilizer':    'Goma estable en ácido',
            'dose_g_per_kg': '0.5–0.8 g/kg',
            'dose_g_recipe': f'{0.6 * m / 1000:.1f} g (referencia)',
            'priority':      'recomendado',
            'reason':        'Carragenina (ej. Natulac) se degrada con pH<4.5. '
                             'Fruta ácida detectada → riesgo de sinéresis y pérdida de cuerpo.',
            'warning':       None,
            'alternativas':  [
                '① Goma Xantana: 0.5–0.8 g/kg — muy estable en pH 2-8, no se degrada con ácidos.',
                '② Pectina LM: 1–2 g/kg — paradójicamente estable en frutas ácidas con calcio.',
                '③ Goma Guar + Xantana (2:1): sinergia, buen cuerpo en pH bajo.',
            ],
        })

    # ── EMULSIONANTE (helados cremosos sin lecitina) ──────────────────────────
    if not has_lecitina and fat_pct > 4 and not is_sorbet:
        recs.append({
            'stabilizer':    'Emulsionante',
            'dose_g_per_kg': '2–3 g/kg',
            'dose_g_recipe': f'{2.5 * m / 1000:.1f} g (referencia)',
            'priority':      'recomendado',
            'reason':        f'Grasa {fat_pct:.1f}% sin emulsionante → riesgo de separación '
                             'grasa/agua y textura gruesa.',
            'warning':       'Premezclar en seco con polvos lácteos antes de añadir líquidos.',
            'alternativas':  [
                '① Lecitina de girasol en polvo: 2–3 g/kg — limpia, sin alérgeno soja, '
                   'fácil de integrar en seco.',
                '② Lecitina de soja: 2–3 g/kg — más económica, misma función. '
                   'Alérgeno declarable.',
                '③ Yema de huevo: 30–50 g/kg — emulsificación natural + sabor, '
                   'requiere pasteurización a 72°C.',
                '④ Mono y diglicéridos (MDG): 1.5–2.5 g/kg — sinergiza con lecitina '
                   'para mayor cremosidad y resistencia al derretimiento.',
            ],
        })

    # ── CRIOPROTECTOR CREAMI ──────────────────────────────────────────────────
    if not has_trehalosa and is_creami:
        recs.append({
            'stabilizer':    'Crioprotector (azúcar)',
            'dose_g_per_kg': '12–18 g/kg',
            'dose_g_recipe': f'{15 * m / 1000:.1f} g (referencia)',
            'priority':      'recomendado',
            'reason':        'Protege la microestructura durante el re-congelado post-proceso. '
                             'Especialmente útil si no consumes el pote completo de una sola vez.',
            'warning':       None,
            'alternativas':  [
                '① Trehalosa: 12–18 g/kg — crioprotector por excelencia, POD=0.45 (no endulza). '
                   'Estabiliza membranas celulares y reduce recristalización.',
                '② Dextrosa monohidrato: 20–40 g/kg — doble función: PAC alto + cierta '
                   'crioprotección. Más económica que trehalosa.',
                '③ Eritritol (máx 1.5% de la masa total): efecto crioprotector secundario '
                   'sin calorías. No superar 1.5% o genera efecto mentolado.',
            ],
        })

    # ── MEZCLA BIEN BALANCEADA ────────────────────────────────────────────────
    if st_pct >= 38 and water_pct <= 58 and not is_sorbet and not recs:
        recs.append({
            'stabilizer':    '✅ Sin espesante adicional necesario',
            'dose_g_per_kg': '—',
            'dose_g_recipe': '—',
            'priority':      'opcional',
            'reason':        f'ST {st_pct:.1f}% y agua libre {water_pct:.1f}%. '
                             'Los sólidos naturales son suficientes para retener el agua.',
            'warning':       'Si añades espesante con estos sólidos → riesgo de textura gomosa.',
            'alternativas':  [],
        })

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE EDULCORANTES
# ─────────────────────────────────────────────────────────────────────────────

def analyze_sweeteners(lines_with_ings):
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
    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_light  = product_type == PRODUCT_LIGERO
    is_vegan  = product_type == PRODUCT_VEGANO
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)

    fuentes       = []
    protein_total = 0.0
    espuma_sum    = 0.0
    gel_sum       = 0.0
    peso_sum      = 0.0
    tipo_pesos    = {}
    advertencias  = []

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g        = float(grams)
        name_low = ing.get('name', '').lower()

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
                msnf_g = g * float(ing.get('msnf', 0)) / 100
                prot_g = msnf_g * perfil['protein_fraction']
        else:
            msnf_g = g * float(ing.get('msnf', 0)) / 100
            prot_g = msnf_g * 0.36
            if msnf_g > 0:
                perfil = {'tipo': 'lácteo_mixto', 'solubilidad': 'micelar',
                          't_desnaturaliz_c': 72, 'capacidad_espuma': 2,
                          'capacidad_gel': 2, 'nota': 'Fallback 36% MSNF'}

        if prot_g < 0.05:
            continue

        protein_total += prot_g
        tipo = perfil['tipo'] if perfil else 'lácteo_mixto'
        tipo_pesos[tipo] = tipo_pesos.get(tipo, 0) + prot_g

        esp = perfil['capacidad_espuma'] if perfil else 2
        gel = perfil['capacidad_gel']    if perfil else 2
        espuma_sum += esp * prot_g
        gel_sum    += gel * prot_g
        peso_sum   += prot_g

        t_denat = perfil.get('t_desnaturaliz_c', 999) if perfil else 999
        if t_denat < 75:
            advertencias.append(
                f"⚠️ {ing['name']}: desnaturaliza a {t_denat}°C — "
                "no pasteurizar sobre esa temperatura.")

        fuentes.append({
            'nombre':       ing['name'],
            'gramos':       g,
            'proteina_g':   round(prot_g, 2),
            'tipo':         tipo,
            'espuma':       esp,
            'gel':          gel,
            't_denat':      t_denat if t_denat < 999 else None,
            'nota':         perfil.get('nota', '') if perfil else '',
            'perfil_clave': matched_key or '(fallback)',
        })

    protein_pct     = protein_total / m * 100
    protein_per_100 = protein_pct
    score_espuma    = espuma_sum / peso_sum if peso_sum > 0 else 0
    score_gel       = gel_sum    / peso_sum if peso_sum > 0 else 0
    tipo_dominante  = max(tipo_pesos, key=tipo_pesos.get) if tipo_pesos else 'n/d'

    thr = PROTEIN_CLAIM_THRESHOLDS
    if protein_per_100 >= thr['alto_proteina']:
        claim = 'alto_proteina'
    elif protein_per_100 >= thr['fuente_proteina']:
        claim = 'fuente_proteina'
    else:
        claim = None

    tgt            = PROTEIN_FUNCTIONAL_TARGETS
    recomendaciones = []

    def rec(priority, titulo, texto):
        recomendaciones.append({'priority': priority, 'titulo': titulo, 'texto': texto})

    if 0 < protein_pct < tgt['minimo_estructura'] and not is_sorbet:
        deficit = tgt['minimo_estructura'] - protein_pct
        rec('important',
            f"Proteína {protein_pct:.1f}% — por debajo del mínimo estructural ({tgt['minimo_estructura']}%)",
            f"Necesitas ~{deficit * m / 100:.0f} g más de proteína para cuerpo estable. "
            "Opciones: WPC/WPI, leche en polvo descremada adicional, yema de huevo.")

    return {
        'fuentes':          fuentes,
        'protein_total_g':  round(protein_total, 1),
        'protein_pct':      round(protein_pct, 2),
        'protein_per_100g': round(protein_per_100, 1),
        'tipo_dominante':   tipo_dominante,
        'score_espuma':     round(score_espuma, 1),
        'score_gel':        round(score_gel, 1),
        'claim':            claim,
        'advertencias':     advertencias,
        'recomendaciones':  recomendaciones,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNÓSTICOS COMPLETOS
# ─────────────────────────────────────────────────────────────────────────────

def calc_derived(totals, pct, product_type='Helado/Gelato', machine='Ninja Creami Deluxe',
                 lines_with_ings=None, config=None):
    """
    config: dict con rangos configurables desde UI. Si None, usa _get_targets().
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)

    targets   = _get_targets(product_type, machine)
    # Permitir override de targets desde config (menú configuración)
    if config:
        for key in ('st', 'fat', 'msnf', 'sugars', 'pod', 'pac', 'st_water'):
            if key in config:
                targets[key] = config[key]

    st_lo,  st_hi   = targets['st']
    fat_lo, fat_hi  = targets['fat']
    msn_lo, msn_hi  = targets['msnf']
    sug_lo, sug_hi  = targets['sugars']
    pod_lo, pod_hi  = targets['pod']
    pac_lo, pac_hi  = targets['pac']
    stw_lo, stw_hi  = targets['st_water']
    msnf_crit       = targets.get('msnf_critical', 11.0)

    st_v    = pct.get('st_pct',     0)
    fat_v   = pct.get('fat_pct',    0)
    msnf_v  = pct.get('msnf_pct',  0)
    sug_v   = pct.get('sugars_pct', 0)
    pod_v   = pct.get('pod_total',  0)
    pac_v   = pct.get('pac_total',  0)
    water_v = pct.get('water_pct',  0)
    stw_v   = st_v / water_v if water_v > 0 else 0

    d    = {}
    diags = []

    def sym(k):
        m_map = {'st': (st_lo, st_hi), 'fat': (fat_lo, fat_hi),
                 'msnf': (msn_lo, msn_hi), 'sugars': (sug_lo, sug_hi),
                 'pod': (pod_lo, pod_hi), 'pac': (pac_lo, pac_hi)}
        v_map = {'st': st_v, 'fat': fat_v, 'msnf': msnf_v,
                 'sugars': sug_v, 'pod': pod_v, 'pac': pac_v}
        lo, hi = m_map.get(k, (None, None))
        s = _status(v_map.get(k, 0), lo, hi)
        return {'empty': '⬜', 'low': '🔵', 'ok': '✅', 'high': '🔴'}.get(s, '❓')

    def diag(priority, key, condition, title, tip):
        if condition:
            diags.append({'priority': priority, 'key': key, 'title': title, 'tip': tip})

    # ── Crioscopía ────────────────────────────────────────────────────────────
    M_sacarosa = 342.3
    k_f = 1.86
    pac_moles = totals['pac'] / M_sacarosa if totals.get('pac', 0) > 0 else 0
    water_kg  = totals.get('water', 0) / 1000
    delta_t   = -k_f * (pac_moles / water_kg) if water_kg > 0 else 0
    congela_ok = delta_t <= CREAMI_FREEZE_TEMP_C if is_creami else True

    d['delta_t']         = round(delta_t, 2)
    d['congela_ok']      = congela_ok
    d['cryoscopy_model'] = 'Simplified Raoult'
    d['targets']         = targets
    d['st_water_ratio']  = round(stw_v, 3)

    if is_creami and not congela_ok:
        temp_serv = f"ΔT {delta_t:.2f}°C — insuficiente para −18°C (mín {CREAMI_FREEZE_TEMP_C}°C)"
    elif is_creami:
        temp_serv = f"ΔT {delta_t:.2f}°C ✅ — congela correctamente a −18°C"
    else:
        temp_serv = f"ΔT {delta_t:.2f}°C"
    d['temp_servicio'] = temp_serv

    # ── CREAMI diagnósticos ───────────────────────────────────────────────────
    if is_creami:
        diag(PRIORITY_CRITICAL, 'no_congela', not congela_ok,
             f"ΔT {delta_t:.2f}°C — NO CONGELA a −18°C",
             "PAC insuficiente para solidificar a la temperatura del congelador. "
             "① Añade dextrosa (+20-30g). "
             "② Sustituye parte de sacarosa por dextrosa o fructosa. "
             "③ Reduce el agua libre.")

        diag(PRIORITY_IMPORTANT, 'agua_alta_creami', water_v > 70,
             f"Agua libre {water_v:.1f}% → muy alta para Creami",
             "La Creami no tritura bien bases muy acuosas → textura icy. "
             "Añade leche en polvo descremada o reduce líquidos.")

        diag(PRIORITY_ADJUSTABLE, 'agua_baja_creami', 0 < water_v < 48,
             f"Agua libre {water_v:.1f}% → baja",
             "Mezcla muy concentrada → overrun bajo y textura densa. "
             "Añade leche líquida o agua hasta 54-62% agua libre.")

        diag(PRIORITY_ADJUSTABLE, 'creami_overrun_hint', True,
             f"Overrun estimado Ninja Creami: ~{CREAMI_OVERRUN_PCT.get(machine, 50)}%",
             f"La {machine} incorpora aire mecánicamente en el proceso de 'creamify'. "
             "El overrun real depende de la composición: "
             "ST 28-35% → overrun 50-65% (textura ligera/aireada). "
             "ST 35-40% → overrun 35-45% (textura más densa). "
             "El overrun NO es configurable — es fijo por el mecanismo de la máquina.")

    # ── MANTECADORA diagnósticos ──────────────────────────────────────────────
    if not is_creami:
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

    # ── RATIO ST/AGUA ─────────────────────────────────────────────────────────
    diag(PRIORITY_IMPORTANT, 'stw_bajo', 0 < stw_v < stw_lo,
         f"Ratio ST/Agua {stw_v:.3f} → por debajo del rango ({stw_lo:.2f}–{stw_hi:.2f})",
         "Demasiada agua libre relativa a los sólidos → cristales grandes, textura icy. "
         "Concentra la mezcla: más leche en polvo, más azúcar, o reduce agua/líquidos.")

    diag(PRIORITY_ADJUSTABLE, 'stw_alto', stw_v > stw_hi,
         f"Ratio ST/Agua {stw_v:.3f} → por encima del rango ({stw_lo:.2f}–{stw_hi:.2f})",
         "Mezcla muy concentrada → textura pastosa, overrun difícil. "
         "Añade leche líquida o agua hasta equilibrar.")

    # ── GENERALES ─────────────────────────────────────────────────────────────
    st_max = 40 if is_creami else 44
    diag(PRIORITY_CRITICAL, 'st_alto', st_v > st_max,
         f"ST {st_v:.1f}% → SOBRECONCENTRADO",
         "Textura de pasta, overrun imposible. Añade leche entera o agua.")

    diag(PRIORITY_CRITICAL, 'st_bajo', 0 < st_v < st_lo,
         f"ST {st_v:.1f}% → muy bajo (mín {st_lo}%)",
         "Faltarán sólidos para dar cuerpo. Añade leche en polvo o azúcar.")

    diag(PRIORITY_CRITICAL, 'pac_alto', pac_v > pac_hi,
         f"PAC {pac_v:.0f} → excesivo (máx {pac_hi})",
         "Punto de congelación demasiado bajo → helado no solidifica o queda muy blando.")

    diag(PRIORITY_IMPORTANT, 'fat_alto', fat_v > fat_hi,
         f"Grasa {fat_v:.1f}% → alta (máx {fat_hi}%)",
         "Posible separación de grasa o textura mantecosa. Reduce crema o mantequilla.")

    diag(PRIORITY_IMPORTANT, 'msnf_alto_creami', is_creami and msnf_v > msnf_crit,
         f"MSNF {msnf_v:.1f}% → alto para Creami (umbral {msnf_crit}%)",
         "Con la Creami el MSNF alto puede causar arenado al re-congelar. "
         "Reduce leche en polvo descremada.")

    diag(PRIORITY_ADJUSTABLE, 'pod_bajo', 0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → bajo (mín {pod_lo}). Helado poco dulce",
         "① Añade sacarosa (+10-20g). "
         "② Fructosa para sorbetes (POD=1.2). "
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

    # ── ALCOHOL ───────────────────────────────────────────────────────────────
    alcohol_lines = _detect_alcohol_lines(lines_with_ings or [])
    if alcohol_lines:
        ethanol_total_g = sum(a['ethanol_g'] for a in alcohol_lines)
        ethanol_pct_mix = ethanol_total_g / m * 100
        nombres_alcohol = ", ".join(a['ingredient_name'] for a in alcohol_lines)

        diag(PRIORITY_CRITICAL, 'alcohol_exceso', ethanol_pct_mix > 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → NO CONGELA",
             f"Ingredientes: {nombres_alcohol}. Etanol estimado: {ethanol_total_g:.1f} g. "
             "Con >4% etanol el punto de congelación cae por debajo de −18°C. "
             "Reduce el licor o usa extracto sin alcohol.")

        diag(PRIORITY_IMPORTANT, 'alcohol_advertencia', 2.5 < ethanol_pct_mix <= 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → textura blanda",
             f"Ingredientes: {nombres_alcohol}. Entre 2.5-4%: congela pero muy blando. "
             "Compensa con +20-30g de dextrosa.")

        diag(PRIORITY_ADJUSTABLE, 'alcohol_info', ethanol_pct_mix <= 2.5,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol — dosis correcta",
             f"Ingredientes: {nombres_alcohol}. Dosis dentro de rango seguro para congelación.")

        d['alcohol_detected'] = {
            'lines': alcohol_lines,
            'ethanol_total_g': round(ethanol_total_g, 1),
            'ethanol_pct':     round(ethanol_pct_mix, 2),
        }
    else:
        d['alcohol_detected'] = None

    d['diagnostics'] = diags
    return d


# ─────────────────────────────────────────────────────────────────────────────
# TICKET DE PRODUCCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def format_production_ticket(recipe_name, product_type, machine,
                              ingredient_names, lines_for_calculator,
                              totals, pct, derived, kcal, protein_data=None):
    m = totals.get('grams', 0)
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

    targets = derived.get('targets', _get_targets(product_type, machine))

    def sym(k):
        m_map = {'st': targets['st'], 'fat': targets['fat'],
                 'msnf': targets['msnf'], 'sugars': targets['sugars'],
                 'pod': targets['pod'], 'pac': targets['pac']}
        v_map = {'st': pct.get('st_pct', 0), 'fat': pct.get('fat_pct', 0),
                 'msnf': pct.get('msnf_pct', 0), 'sugars': pct.get('sugars_pct', 0),
                 'pod': pct.get('pod_total', 0), 'pac': pct.get('pac_total', 0)}
        lo, hi = m_map.get(k, (None, None))
        s = _status(v_map.get(k, 0), lo, hi)
        return {'empty': '⬜', 'low': '🔵', 'ok': '✅', 'high': '🔴'}.get(s, '❓')

    # Ingredientes
    ing_block = ""
    for ing, grams, price in lines_for_calculator:
        if not ing or not grams:
            continue
        ing_block += f"  {ing['name']:<30} {float(grams):>6.1f} g\n"

    # Diagnósticos (excluir los marcados)
    diags_visibles = [d for d in derived.get('diagnostics', [])
                      if d['key'] not in DIAGS_EXCLUIR_TICKET]
    diag_block = ""
    for dg in diags_visibles:
        icon = "🔴" if dg['priority'] == 'critical' else \
               "🟡" if dg['priority'] == 'important' else "🔵"
        diag_block += f"  {icon} {dg['title']}\n     → {dg['tip']}\n"
    if not diag_block:
        diag_block = "  ✅ Mezcla balanceada — sin alertas.\n"

    # Bloque overrun
    or_d = overrun_calc(m, 0, 1.0, machine)
    if is_creami:
        overrun_block = (
            f"  Overrun fijo Creami:   ~{or_d['overrun_fijo_pct']}%  (mecánico)\n"
            f"  Masa final estimada:   {or_d['masa_final_estimada_g']:.0f} g\n"
            f"  Potes (base):          {or_d['potes_base']:.1f} × {or_d['masa_por_pote_g']:.0f} g\n"
        )
    else:
        overrun_block = (
            f"  Litros producidos:     {or_d['liters_from_base']:.2f} L\n"
        )

    # Bloque alcohol
    alc = derived.get('alcohol_detected')
    alcohol_block = ""
    if alc:
        alcohol_block = (
            f"\n  🍾 Alcohol detectado: {alc['ethanol_total_g']} g etanol "
            f"({alc['ethanol_pct']:.2f}% de la mezcla)\n"
        )

    # Bloque calorías con clasificación
    cal_class  = kcal.get('clasificacion_calorica')
    prot_class = kcal.get('clasificacion_proteica')
    cal_block  = f"  kcal / 100 g:   {kcal['kcal_per_100g']:.0f} kcal"
    if cal_class:
        cal_block += f"  {cal_class['emoji']} {cal_class['etiqueta']}"
    cal_block += "\n"
    if prot_class:
        cal_block += f"  Proteína:       {prot_class['valor']:.1f} g/100g  {prot_class['emoji']} {prot_class['etiqueta']}\n"

    # Ratio ST/Agua
    stw = derived.get('st_water_ratio', 0)
    stw_lo, stw_hi = targets.get('st_water', (0.42, 0.78))
    stw_sym = '✅' if stw_lo <= stw <= stw_hi else ('🔵' if stw < stw_lo else '🔴')

    instrucciones = (
        "INSTRUCCIONES NINJA CREAMI:\n"
        "  1. Mezclar y pasteurizar a 85°C / 15 seg\n"
        "  2. Enfriar a <4°C (baño de hielo)\n"
        "  3. Congelar mín. 24h a −18°C\n"
        "  4. Procesar con función Ice Cream o Lite Ice Cream\n"
        "  5. Si queda granuloso: Re-spin sin añadir líquido"
        if is_creami else
        "INSTRUCCIONES MANTECADORA:\n"
        "  1. Pasteurizar a 85°C / 15 seg\n"
        "  2. Madurar en frío 4-12h a 4°C\n"
        "  3. Mantecado según overrun objetivo\n"
        "  4. Endurecimiento: −18°C mín. 2h"
    )

    return (
        "══════════════════════════════════════════════\n"
        f"  🍦 TICKET PRODUCCIÓN — {recipe_name}\n"
        f"  {product_type} · {machine}\n"
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        "══════════════════════════════════════════════\n"
        "INGREDIENTES:\n"
        f"{ing_block}"
        f"  {'─' * 40}\n"
        f"  Masa total:     {m:.0f} g\n"
        "\nCOMPOSICIÓN:\n"
        f"  ST:             {pct.get('st_pct', 0):.1f}%   {sym('st')}\n"
        f"  Grasa:          {pct.get('fat_pct', 0):.1f}%   {sym('fat')}\n"
        f"  MSNF:           {pct.get('msnf_pct', 0):.1f}%   {sym('msnf')}\n"
        f"  Azúcares:       {pct.get('sugars_pct', 0):.1f}%   {sym('sugars')}\n"
        f"  Agua libre:     {pct.get('water_pct', 0):.1f}%\n"
        f"  Ratio ST/Agua:  {stw:.3f}   {stw_sym} (rango {stw_lo:.2f}–{stw_hi:.2f})\n"
        f"  POD:            {pct.get('pod_total', 0):.0f}      {sym('pod')}\n"
        f"  PAC:            {pct.get('pac_total', 0):.0f}      {sym('pac')}\n"
        f"  ΔT crioscopía:  {derived.get('delta_t', 0):.2f} °C\n"
        f"\nCALORÍAS / NUTRICIÓN:\n"
        f"{cal_block}"
        f"  Costo estimado: ${totals['cost']:.2f}\n"
        f"\nPRODUCCIÓN:\n"
        f"{overrun_block}"
        f"{alcohol_block}"
        f"\nDIAGNÓSTICOS:\n"
        f"{diag_block}"
        f"\n{instrucciones}\n"
        "══════════════════════════════════════════════"
    )
