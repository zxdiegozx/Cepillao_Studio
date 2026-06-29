"""Pure calculation engine — sin dependencias externas.

CHANGELOG v2.2 (validación intensiva junio 2026)
─────────────────────────────────────────────────
FIX-1  PAC alulosa corregido: 1.00 → 1.80
       Justificación: PM alulosa = 180 g/mol → PAC teórico = 342/180 = 1.90.
       Se usa 1.80 como valor empírico conservador (margen por solvatación).
       Impacta: ΔT crioscópico en recetas light/diabéticas, diagnóstico no_congela.

FIX-2  SWEETENER_PROFILES alulosa kcal corregido: 0.4 ya estaba bien.
       Se añade nota explícita de zero_calorie en BD (requiere zero_calorie=1 en database.py).

FIX-3  overrun_calc: volumen_estimado_ml ahora usa densidad real del helado.
       Helado con overrun tiene densidad < 1 g/mL. Se calcula como:
         densidad_helado = 1.0 / (1 + or_factor)  [aprox. para helado con aire]
         volumen_estimado_ml = masa_final_g / densidad_helado
       Para Creami (overrun ~50%): densidad ≈ 0.667 g/mL.
       El campo masa_final_estimada_g sigue siendo la masa real (sin cambio).

FIX-4  CREAMI_DELTA_T_MIN documentado y marcado como reservado para uso futuro.
       No se elimina para no romper código externo que pueda importarlo.

FIX-5  st_water_ratio: guard contra water_pct = 0 para evitar disparo falso
       del diagnóstico stw_bajo en recetas de polvo puro o edge cases.
"""

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
KCAL_PROTEIN = 3.5   # factor Atwater modificado para proteína láctea (FAO/WHO 2003)
KCAL_SUGAR   = 4.0
KCAL_OTHER   = 2.5   # fibra, cacao, almidón resistente
KCAL_ALCOHOL = 7.0

# ── Perfil de temperatura Ninja Creami ────────────────────────────────────────
CREAMI_FREEZE_TEMP_C    = -18.0
CREAMI_FREEZE_HOURS_MIN = 24
# FIX-4: Constante reservada para un futuro check de "ΔT excesivo que impida re-spin".
# Actualmente NO se usa en ninguna lógica activa. No eliminar — reservada v2.x.
CREAMI_DELTA_T_MIN      = -1.5

# ── Perfiles organolépticos de edulcorantes ───────────────────────────────────
# Estructura: (POD, PAC, kcal/g, descripción_sabor, perfil_dulzor)
#
# FIX-1: PAC de alulosa corregido de 1.00 → 1.80
#   PM alulosa = 180 g/mol → PAC teórico = 342.3/180 = 1.90
#   Valor 1.80 = empírico conservador (margen de solvatación)
#   Fuente: estudios PM molecular + estudio externo junio 2026
#
# NOTA sobre alulosa en BD (database.py):
#   El ingrediente "Alulosa" DEBE tener zero_calorie=1 en la BD.
#   Si está como zero_calorie=0 con sugars=99%, calc_calories la trata
#   como 4 kcal/g en lugar de 0.4 kcal/g → sobreestima ×10 las calorías.
#   Verificar entrada en database.py:
#     ("Alulosa", "Dulcificante", 0.0, 0.0, 99.0, 0.0, 0.70, 1.80, 1.0, ..., 1, ...)
#                                                                ^^^^  zero_calorie=1 ──^
#
# NOTA sobre eritritol (PAC = 1.30):
#   PAC teórico puro = 342.3/122 = 2.80 (PM eritritol = 122 g/mol)
#   El valor 1.30 es empírico conservador validado por catas Diego 2024-2025.
#   Justificación: eritritol recristaliza parcialmente durante congelación,
#   reduciendo su efecto crioscópico real respecto al teórico ideal.
#   Documentado como "empírico validado". No modificar sin nueva evidencia de cata.

SWEETENER_PROFILES = {
    'sacarosa':         (1.00, 1.00, 4.0, 'Referencia — dulzor limpio y redondo',        'inmediato'),
    'dextrosa':         (0.75, 1.90, 4.0, 'Frescor suave positivo en boca fría',         'inmediato'),
    'fructosa':         (1.20, 1.90, 4.0, 'Muy dulce en frío, puede ser empalagoso',     'inmediato'),
    'trehalosa':        (0.45, 0.70, 4.0, 'Muy suave, casi neutro, crioprotector',       'lento'),
    'alulosa':          (0.70, 1.80, 0.4, 'El más parecido al azúcar, sin retrogusto',   'inmediato'),  # FIX-1
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
    Incluye st_water: ratio sólidos totales / agua libre.
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

    Nota sobre zero_calorie:
      Ingredientes con zero_calorie=1 en la BD (eritritol, alulosa, stevia)
      tienen su fracción de azúcares descontada del cálculo calórico.
      Esto es necesario porque estos ingredientes se registran con sugars>0
      por su estructura química, pero aportan <1 kcal/g real.
      Si alulosa NO tiene zero_calorie=1 en BD → sus calorías se sobreestiman ×10.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {'kcal_total': 0, 'kcal_per_100g': 0, 'kcal_per_pote_deluxe': 0,
                'clasificacion_calorica': None, 'clasificacion_proteica': None}

    protein_g = totals.get('msnf', 0) * 0.35   # ~35% del MSNF es proteína (Goff & Hartel 2013)

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
                # Descuenta la fracción de azúcares que ya se sumó a la tasa estándar
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
        _, etiqueta, emoji, desc = list(CALORIE_CLASSIFICATION.values())[-1]
        cal_class = {'key': 'muy_denso', 'etiqueta': etiqueta, 'emoji': emoji,
                     'desc': desc, 'valor': round(kcal_per_100g, 0)}

    # ── Clasificación proteica ────────────────────────────────────────────────
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
                'ingredient_name':  ing.get('name', '?'),
                'grams':            g,
                'ethanol_fraction': fraction,
                'ethanol_g':        round(g * fraction, 2),
            })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# VALIDACIÓN BRIX
# ─────────────────────────────────────────────────────────────────────────────

def validate_brix(measured_brix: float, totals: dict) -> dict:
    """
    Compara Brix medido con refractómetro vs. Brix calculado de la receta.

    El Brix del refractómetro incluye todos los sólidos solubles:
      azúcares + lactosa del MSNF (factor 0.55 — Walstra 2005)
    El valor de referencia correcto es brix_con_msnf, no solo brix_calculado.

    Nota: los refractómetros digitales auto-compensan temperatura a 20°C.
    Los analógicos deben usarse a temperatura de referencia para exactitud.
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
    msnf_g   = totals.get('msnf', 0)
    brix_calc     = sugars_g / m * 100
    brix_con_msnf = (sugars_g + msnf_g * 0.55) / m * 100
    delta         = measured_brix - brix_con_msnf
    sugars_est    = measured_brix * m / 100

    if abs(delta) <= 2:
        estado = 'ok'
        interp = (f"✅ Brix medido ({measured_brix:.1f}°) coincide con lo calculado "
                  f"({brix_con_msnf:.1f}°). Receta correcta.")
    elif delta > 2:
        estado = 'alto'
        interp = (f"⚠️ Brix medido superior al esperado (+{delta:.1f}°). "
                  "Posible azúcar adicional no declarado o fruta más madura.")
    else:
        estado = 'bajo'
        interp = (f"⚠️ Brix medido inferior al esperado ({delta:.1f}°). "
                  "Posible pérdida por fermentación, dilución o error en pesaje.")

    return {
        'brix_calculado':     round(brix_calc, 1),
        'brix_con_msnf':      round(brix_con_msnf, 1),
        'delta_brix':         round(delta, 2),
        'sugars_estimados_g': round(sugars_est, 1),
        'interpretacion':     interp,
        'estado':             estado,
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

    FIX-3: volumen_estimado_ml ahora usa densidad real del helado.
      El helado incorpora aire durante el proceso. Con overrun del 50%,
      la densidad cae a aproximadamente 1/(1 + or_factor) g/mL.
      Esto significa que 960g de helado con 50% overrun ocupan ~1,433 mL,
      no 960 mL como indicaba la versión anterior.

      Densidades de referencia por overrun:
        0%  overrun → densidad ≈ 1.00 g/mL (base líquida, sin aire)
        25% overrun → densidad ≈ 0.80 g/mL
        50% overrun → densidad ≈ 0.67 g/mL  (Ninja Creami Deluxe)
        100% overrun → densidad ≈ 0.50 g/mL (helado industrial)

      Fórmula: densidad = 1.0 / (1 + or_factor)
    """
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

    if is_creami:
        overrun_fijo_pct = CREAMI_OVERRUN_PCT.get(machine, 50)
        or_factor        = overrun_fijo_pct / 100

        cap = CREAMI_DELUXE_CAPACITY_G if machine == MACHINE_CREAMI_DELUXE else CREAMI_STANDARD_CAPACITY_G
        potes_exacto  = base_grams / cap if cap > 0 else 0
        potes_enteros = int(potes_exacto)
        resto_g       = (potes_exacto - potes_enteros) * cap

        masa_final_g = base_grams * (1 + or_factor)

        # FIX-3: densidad real del helado con overrun incorporado
        densidad_helado  = 1.0 / (1 + or_factor)   # g/mL → aprox física
        volumen_final_ml = masa_final_g / densidad_helado

        potes_con_overrun = masa_final_g / cap if cap > 0 else 0

        return {
            'is_creami':             True,
            'overrun_fijo_pct':      overrun_fijo_pct,
            'masa_base_g':           base_grams,
            'masa_final_estimada_g': round(masa_final_g, 0),
            'volumen_estimado_ml':   round(volumen_final_ml, 0),   # FIX-3 corregido
            'densidad_helado_g_ml':  round(densidad_helado, 3),    # nuevo campo informativo
            'potes_base':            round(potes_exacto, 2),
            'potes_completos':       potes_enteros,
            'masa_ultimo_pote_g':    round(resto_g, 0),
            'masa_por_pote_g':       cap,
            'potes_con_overrun':     round(potes_con_overrun, 2),
            # Campos de compatibilidad backward
            'base_needed_g':         base_grams,
            'liters_from_base':      round(volumen_final_ml / 1000, 2),
            'volume_increase':       overrun_fijo_pct,
            'final_grams_per_liter': round(masa_final_g / (volumen_final_ml / 1000), 0) if volumen_final_ml > 0 else 0,
        }

    else:
        # Mantecadora Tradicional
        or_pct      = overrun_pct / 100
        or_factor   = or_pct
        base_needed = target_liters * 1000 / (1 + or_pct) if (1 + or_pct) > 0 else 0
        liters_prod = base_grams / 1000 * (1 + or_pct)

        mix_per_beaker  = base_grams / 2 / (1 + or_pct) if (1 + or_pct) > 0 else 0
        pacojet_beakers = math.ceil(liters_prod / 0.5) if liters_prod > 0 else 0

        # FIX-3: densidad corregida también en mantecadora
        densidad_helado  = 1.0 / (1 + or_factor) if or_factor > 0 else 1.0

        return {
            'is_creami':             False,
            'overrun_pct':           overrun_pct,
            'base_needed_g':         round(base_needed, 0),
            'liters_from_base':      round(liters_prod, 2),
            'target_liters':         target_liters,
            'volume_increase':       overrun_pct,
            'final_grams_per_liter': round(base_grams / liters_prod, 0) if liters_prod > 0 else 0,
            'densidad_helado_g_ml':  round(densidad_helado, 3),    # nuevo campo
            'mix_per_beaker':        round(mix_per_beaker, 1),
            'pacojet_beakers':       pacojet_beakers,
            # No aplicable a mantecadora:
            'potes_completos':       0,
            'masa_ultimo_pote_g':    0,
            'masa_por_pote_g':       0,
            'potes_base':            0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVIDAD DE AGUA — ecuación de Ross (1975)
# ─────────────────────────────────────────────────────────────────────────────

def calc_water_activity(totals: dict) -> dict:
    """
    Aproximación de Ross para Aw en mezclas multicomponente.

    Aw ≈ n_agua / (n_agua + n_solutos_totales)

    Supuestos:
      - 55% del MSNF es lactosa (Walstra 2005)
      - 8% del MSNF son sales minerales
      - PM promedio azúcares = 270 g/mol (entre sacarosa 342 y monos 180)
      - NaCl disocia en 2 iones (factor ×2 en moles)
      - Grasa: no soluble → no afecta Aw (correctamente ignorada)
      - Proteínas: PM ~15,000–25,000 g/mol → contribución molar despreciable

    Limitación conocida: en recetas con alta proporción de monosacáridos
    (alulosa, eritritol, dextrosa), el PM real es ~150–180 g/mol vs. 270
    → la depresión de Aw real es ligeramente mayor (hasta 8-12% más baja).
    Precisión global: ±0.01–0.02 unidades de Aw. Suficiente para evaluación
    de riesgo relativo en producción artesanal.
    """
    m        = totals.get('grams', 0)
    water_g  = totals.get('water', 0)
    sugars_g = totals.get('sugars', 0)
    msnf_g   = totals.get('msnf', 0)

    if water_g <= 0 or m <= 0:
        return {'aw': 1.0, 'aw_pct': 100.0, 'riesgo_micro': 'sin_datos',
                'interpretacion': 'Sin agua — no calculable.', 'modelo': 'Ross (1975)'}

    n_agua     = water_g / 18.015
    n_azucares = sugars_g / 270.0          # PM promedio ponderado
    lactosa_g  = msnf_g * 0.55             # 55% MSNF es lactosa
    sal_g      = msnf_g * 0.08             # 8% MSNF son sales
    n_lactosa  = lactosa_g / 342.0
    n_sal      = sal_g / 58.44 * 2         # disociación iónica NaCl
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

    return {
        'aw':             round(aw, 4),
        'aw_pct':         round(aw * 100, 2),
        'riesgo_micro':   riesgo,
        'interpretacion': interp,
        'modelo':         'Ross (1975)',
    }


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
    m         = totals.get('grams', 0)
    if m <= 0:
        return []

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)

    targets   = _get_targets(product_type, machine)
    if config:
        for key in ('st', 'fat', 'msnf', 'sugars', 'pod', 'pac', 'st_water'):
            if key in config:
                targets[key] = config[key]

    st_pct    = pct.get('st_pct',    0)
    water_pct = pct.get('water_pct', 0)
    fat_pct   = pct.get('fat_pct',   0)

    names = [n.lower() for n in (ingredient_names or [])]

    has_cmc      = any('cmc' in n or 'carboximetil' in n for n in names)
    has_xantana  = any('xantana' in n for n in names)
    has_guar     = any('guar' in n for n in names)
    has_pectina  = any('pectina' in n for n in names)
    has_lecitina = any('lecitina' in n for n in names)
    has_trehalosa= any('trehalosa' in n for n in names)
    has_natulac  = any('natulac' in n or 'carrageen' in n for n in names)
    has_fruta_acida = any(f in n for n in names
                          for f in ('limón', 'lemon', 'maracuyá', 'passion', 'piña',
                                    'pineapple', 'tamarindo', 'fruta de la pasión'))

    recs = []

    # ── AGUA LIBRE ALTA sin estabilizante ────────────────────────────────────
    if water_pct > 62 and not (has_cmc or has_xantana or has_guar or has_pectina):
        if is_sorbet:
            recs.append({
                'stabilizer':    'Goma Guar o Tara',
                'dose_g_per_kg': '1.0–1.5 g/kg',
                'dose_g_recipe': f'{1.2 * m / 1000:.1f} g (referencia)',
                'priority':      'recomendado',
                'reason':        f'Agua libre {water_pct:.1f}% → sorbete muy acuoso. '
                                 'Sin estabilizante: textura icy, cristales gruesos.',
                'warning':       None,
                'alternativas':  [
                    '① Goma Xantana: 0.3–0.5 g/kg — muy estable en pH ácido de frutas.',
                    '② Pectina LM: 1–2 g/kg — sinergia con calcio natural de la fruta.',
                    '③ Goma Tara + Xantana (4:1): excelente para sorbetes ácidos.',
                ],
            })
        else:
            recs.append({
                'stabilizer':    'Espesante / Estabilizante (CMC o Xantana)',
                'dose_g_per_kg': '0.8–1.2 g/kg',
                'dose_g_recipe': f'{1.0 * m / 1000:.1f} g (referencia)',
                'priority':      'recomendado',
                'reason':        f'Agua libre {water_pct:.1f}% → alta para helado/gelato. '
                                 'Sin estabilizante: recristalización rápida y textura icy.',
                'warning':       'No combinar CMC + Natulac/carragenina + fruta ácida '
                                 '→ triple gelificación y colapso elástico.',
                'alternativas':  [
                    '① CMC (Carboximetilcelulosa): 0.8–1.2 g/kg — se hidrata en frío, '
                       'sin pasteurización. Ideal para proceso en frío.',
                    '② Goma Xantana: 0.5–0.8 g/kg — estable pH 2–8, excelente textura.',
                    '③ Goma Guar + LBG (1:1): 0.6+0.6 g/kg — sinergia cremosa, '
                       'requiere pasteurización a 85°C para LBG.',
                ],
            })

    # ── ST BAJO (poca estructura) ─────────────────────────────────────────────
    if st_pct < targets['st'][0] and not is_sorbet:
        recs.append({
            'stabilizer':    'Fibra soluble o Inulina',
            'dose_g_per_kg': '20–40 g/kg',
            'dose_g_recipe': f'{30 * m / 1000:.1f} g (referencia)',
            'priority':      'opcional',
            'reason':        f'ST {st_pct:.1f}% bajo el mínimo ({targets["st"][0]}%). '
                             'La fibra soluble añade sólidos sin aportar dulzor excesivo.',
            'warning':       'Inulina >5% puede dar regusto amargo. Preferir fibra cítrica.',
            'alternativas':  [
                '① Fibra cítrica: 2–5 g/kg — clean label, liga agua sin gomosidad.',
                '② Leche en polvo descremada (LPD): 20–40 g/kg — añade MSNF y proteínas.',
                '③ Inulina: 20–30 g/kg — prebiótica, bajo IG. Máx 5% para evitar amargor.',
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
                '① Goma Xantana: 0.5–0.8 g/kg — muy estable en pH 2–8, no se degrada con ácidos.',
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
                warning = (f"⚠️ Eritritol al {pct_in_mix:.1f}% → efecto mentolado probable. "
                           "Máximo 1.5%")
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

    tgt             = PROTEIN_FUNCTIONAL_TARGETS
    recomendaciones = []

    def rec(priority, titulo, texto):
        recomendaciones.append({'priority': priority, 'titulo': titulo, 'texto': texto})

    if 0 < protein_pct < tgt['minimo_estructura'] and not is_sorbet:
        deficit = tgt['minimo_estructura'] - protein_pct
        rec('important',
            f"Proteína {protein_pct:.1f}% — por debajo del mínimo estructural "
            f"({tgt['minimo_estructura']}%)",
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
    Calcula métricas derivadas y genera diagnósticos priorizados.

    config: dict con rangos configurables desde UI. Si None, usa _get_targets().

    FIX-5: st_water_ratio ahora tiene guard contra water_pct = 0.
      Si la receta tiene water_pct = 0 (polvo puro, edge case), el ratio se
      establece en None y los diagnósticos stw_bajo/stw_alto no se disparan,
      evitando falsos positivos.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)

    targets = _get_targets(product_type, machine)
    if config:
        for key in ('st', 'fat', 'msnf', 'sugars', 'pod', 'pac', 'st_water'):
            if key in config:
                targets[key] = config[key]

    st_lo,  st_hi  = targets['st']
    fat_lo, fat_hi = targets['fat']
    msn_lo, msn_hi = targets['msnf']
    sug_lo, sug_hi = targets['sugars']
    pod_lo, pod_hi = targets['pod']
    pac_lo, pac_hi = targets['pac']
    stw_lo, stw_hi = targets['st_water']
    msnf_crit      = targets.get('msnf_critical', 11.0)

    st_v   = pct.get('st_pct',    0)
    fat_v  = pct.get('fat_pct',   0)
    msnf_v = pct.get('msnf_pct', 0)
    sug_v  = pct.get('sugars_pct', 0)
    pod_v  = pct.get('pod_total', 0)
    pac_v  = pct.get('pac_total', 0)
    water_v= pct.get('water_pct', 0)

    # FIX-5: guard contra water=0 para evitar ratio infinito y falso stw_bajo
    stw_v = (st_v / water_v) if water_v > 0 else None

    d     = {}
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
    # Modelo: Raoult simplificado
    # ΔT = −Kf × (PAC_absoluto / M_sacarosa) / agua_kg
    # Kf = 1.86 °C·kg/mol (constante crioscópica del agua)
    # M_sacarosa = 342.3 g/mol (masa molar de referencia para normalizar PAC)
    # El PAC absoluto acumulado ya pondera todos los azúcares como "equivalentes sacarosa"
    # Precisión: ±0.3°C para mezclas artesanales. Ver Chen (1986) para modelo no lineal.
    M_sacarosa = 342.3
    k_f        = 1.86
    pac_moles  = totals.get('pac', 0) / M_sacarosa
    water_kg   = totals.get('water', 0) / 1000
    delta_t    = -k_f * (pac_moles / water_kg) if water_kg > 0 else 0

    congela_ok = delta_t <= CREAMI_FREEZE_TEMP_C if is_creami else True

    d['delta_t']         = round(delta_t, 2)
    d['congela_ok']      = congela_ok
    d['cryoscopy_model'] = 'Raoult simplificado (Kf=1.86, M_ref=342.3)'
    d['targets']         = targets
    # FIX-5: None si water=0 para evitar falso stw_bajo
    d['st_water_ratio']  = round(stw_v, 3) if stw_v is not None else None

    if is_creami and not congela_ok:
        temp_serv = (f"ΔT {delta_t:.2f}°C — insuficiente para −18°C "
                     f"(mín {CREAMI_FREEZE_TEMP_C}°C)")
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
    # FIX-5: solo dispara si stw_v es un número real (water_v > 0)
    if stw_v is not None:
        diag(PRIORITY_IMPORTANT, 'stw_bajo', stw_v < stw_lo,
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
         "Exceso de grasa → sensación untuosa, cobertura excesiva del paladar. "
         "Reduce crema o mantequilla.")

    diag(PRIORITY_IMPORTANT, 'msnf_alto_creami', is_creami and msnf_v > msnf_crit,
         f"MSNF {msnf_v:.1f}% → riesgo arenado Creami (umbral {msnf_crit}%)",
         "La Creami tritura en frío y puede acelerar cristalización de lactosa. "
         "Reduce leche en polvo descremada.")

    diag(PRIORITY_ADJUSTABLE, 'pod_bajo', 0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → dulzor bajo (mín {pod_lo})",
         "Helado poco dulce. Añade sacarosa, fructosa o azúcar invertido.")

    diag(PRIORITY_ADJUSTABLE, 'pod_alto', pod_v > pod_hi,
         f"POD {pod_v:.0f} → dulzor excesivo (máx {pod_hi})",
         "Helado empalagoso. Reduce azúcar o sustituye por trehalosa (POD=0.45).")

    diag(PRIORITY_ADJUSTABLE, 'azucar_bajo', 0 < sug_v < sug_lo,
         f"Azúcares {sug_v:.1f}% → bajos (mín {sug_lo}%)",
         "Poca estructura de azúcar → cristales grandes. "
         "Añade dextrosa o sacarosa.")

    # ── ALCOHOL ───────────────────────────────────────────────────────────────
    alcohol_lines   = _detect_alcohol_lines(lines_with_ings or [])
    ethanol_total_g = sum(a['ethanol_g'] for a in alcohol_lines)
    ethanol_pct_mix = ethanol_total_g / m * 100 if m > 0 else 0
    nombres_alcohol = ', '.join(a['ingredient_name'] for a in alcohol_lines)

    if alcohol_lines:
        diag(PRIORITY_CRITICAL, 'alcohol_exceso', ethanol_pct_mix > 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → NO CONGELA",
             f"Ingredientes: {nombres_alcohol}. Supera 4% de etanol sobre la mezcla → "
             "el PAC del alcohol baja el punto de congelación por debajo de −18°C. "
             "Reduce el licor o usa extracto sin alcohol.")

        diag(PRIORITY_IMPORTANT, 'alcohol_advertencia', 2.5 < ethanol_pct_mix <= 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → textura blanda",
             f"Ingredientes: {nombres_alcohol}. Entre 2.5-4%: congela pero muy blando. "
             "Compensa con +20-30g de dextrosa.")

        diag(PRIORITY_ADJUSTABLE, 'alcohol_info', ethanol_pct_mix <= 2.5,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol — dosis correcta",
             f"Ingredientes: {nombres_alcohol}. Dosis dentro de rango seguro para congelación.")

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
# TICKET DE PRODUCCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def format_production_ticket(recipe_name, product_type, machine,
                              ingredient_names, lines_for_calculator,
                              totals, pct, derived, kcal, protein_data=None):
    """
    Genera el texto del ticket de producción en formato imprimible.
    Los diagnósticos marcados en DIAGS_EXCLUIR_TICKET se omiten del ticket.
    """
    m         = totals.get('grams', 0)
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    targets   = derived.get('targets', _get_targets(product_type, machine))

    def sym(k):
        m_map = {
            'st':     targets['st'],
            'fat':    targets['fat'],
            'msnf':   targets['msnf'],
            'sugars': targets['sugars'],
            'pod':    targets['pod'],
            'pac':    targets['pac'],
        }
        v_map = {
            'st':     pct.get('st_pct',    0),
            'fat':    pct.get('fat_pct',   0),
            'msnf':   pct.get('msnf_pct', 0),
            'sugars': pct.get('sugars_pct', 0),
            'pod':    pct.get('pod_total', 0),
            'pac':    pct.get('pac_total', 0),
        }
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
        icon = ("🔴" if dg['priority'] == 'critical' else
                "🟡" if dg['priority'] == 'important' else "🔵")
        diag_block += f"  {icon} {dg['title']}\n     → {dg['tip']}\n"
    if not diag_block:
        diag_block = "  ✅ Mezcla balanceada — sin alertas.\n"

    # Overrun
    or_d = overrun_calc(m, 0, 1.0, machine)
    if is_creami:
        overrun_block = (
            f"  Overrun fijo Creami:   ~{or_d['overrun_fijo_pct']}%  (mecánico)\n"
            f"  Masa final estimada:   {or_d['masa_final_estimada_g']:.0f} g\n"
            f"  Volumen estimado:      {or_d['volumen_estimado_ml']:.0f} mL "
            f"(densidad ≈{or_d['densidad_helado_g_ml']:.2f} g/mL)\n"
            f"  Potes (base):          {or_d['potes_base']:.1f} × {or_d['masa_por_pote_g']:.0f} g\n"
        )
    else:
        overrun_block = (
            f"  Litros producidos:     {or_d['liters_from_base']:.2f} L\n"
        )

    # Alcohol
    alc = derived.get('alcohol_detected')
    alcohol_block = ""
    if alc:
        alcohol_block = (
            f"\n  🍾 Alcohol detectado: {alc['ethanol_total_g']} g etanol "
            f"({alc['ethanol_pct']:.2f}% de la mezcla)\n"
        )

    # Calorías
    cal_class  = kcal.get('clasificacion_calorica')
    prot_class = kcal.get('clasificacion_proteica')
    cal_block  = f"  kcal / 100 g:   {kcal['kcal_per_100g']:.0f} kcal"
    if cal_class:
        cal_block += f"  {cal_class['emoji']} {cal_class['etiqueta']}"
    cal_block += "\n"
    if prot_class:
        cal_block += (f"  Proteína:       {prot_class['valor']:.1f} g/100g  "
                      f"{prot_class['emoji']} {prot_class['etiqueta']}\n")

    # Ratio ST/Agua
    stw     = derived.get('st_water_ratio')
    stw_lo, stw_hi = targets.get('st_water', (0.42, 0.78))
    if stw is not None:
        stw_sym = '✅' if stw_lo <= stw <= stw_hi else ('🔵' if stw < stw_lo else '🔴')
        stw_str = f"{stw:.3f}"
    else:
        stw_sym = '⬜'
        stw_str = 'n/d'

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
        f"  Ratio ST/Agua:  {stw_str}   {stw_sym} (rango {stw_lo:.2f}–{stw_hi:.2f})\n"
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
