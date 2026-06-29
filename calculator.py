"""Pure calculation engine — sin dependencias externas."""

import math
from constants import (
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO,
    PRODUCT_FROZEN,  PRODUCT_LIGERO,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    MACHINE_PACOJET,
    PRIORITY_CRITICAL, PRIORITY_IMPORTANT, PRIORITY_ADJUSTABLE,
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
# FIX B1: eliminada la clave duplicada 'azucar invertido' (POD correcto = 1.30)
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

def calc_calories(totals):
    """
    Estima calorías totales y por 100 g desde macronutrientes.
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

    kcal_per_100g = kcal / m * 100
    kcal_per_pote = kcal_per_100g * CREAMI_DELUXE_CAPACITY_G / 100

    return {
        'kcal_total':           round(kcal, 0),
        'kcal_per_100g':        round(kcal_per_100g, 0),
        'kcal_per_pote_deluxe': round(kcal_per_pote, 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES — exportadas (FIX B2)
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
# ─────────────────────────────────────────────────────────────────────────────

def calc_derived(totals, pct, product_type='Helado/Gelato', machine='Ninja Creami Deluxe'):
    """Ratios, crioscopía, semáforo y diagnósticos."""
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

    # ── Crioscopía (Raoult lineal simplificado) ───────────────────────────────
    water_kg     = totals['water'] / 1000
    d['delta_t'] = -totals['pac'] * 0.2746 * water_kg if water_kg > 0 else 0

    # ── Temperatura de servicio ───────────────────────────────────────────────
    if is_creami:
        d['temp_objetivo'] = CREAMI_FREEZE_TEMP_C
        d['congela_ok']    = d['delta_t'] < CREAMI_DELTA_T_MIN
        d['temp_servicio'] = f"Congelar {CREAMI_FREEZE_HOURS_MIN}h a {CREAMI_FREEZE_TEMP_C}°C → procesar"
    elif is_paco:
        d['temp_servicio'] = "Pacotizar a -22°C → servir"
    else:
        d['temp_servicio'] = "-12 a -14 °C"

    # ── Rangos objetivo (FIX B2: via _get_targets exportada) ─────────────────
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

    # ── Semáforo (FIX B2: via _status exportada, soporta lo=None) ────────────
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
        diag(PRIORITY_CRITICAL, 'msnf_arenado', msnf_v > msnf_crit,
             f"MSNF {msnf_v:.1f}% → ARENADO IRREVERSIBLE (umbral Pacojet {msnf_crit}%)",
             "Cristalización de lactosa — defecto permanente. "
             "Reduce leche en polvo descremada de inmediato. "
             "Sustituye por leche líquida o crema.")

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

    d['diagnostics'] = diags
    return d


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE OVERRUN
# ─────────────────────────────────────────────────────────────────────────────

def overrun_calc(base_grams, overrun_pct, target_liters, machine='Ninja Creami Deluxe'):
    """
    Calcula overrun y rendimiento por máquina.

    FIX B3: añadidos los campos 'volume_increase' y 'final_grams_per_liter'
    que los tests unitarios esperan.
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
        'base_needed_g':          base_needed,
        'liters_from_base':       liters_prod,
        'potes_completos':        potes_enteros,
        'potes_total':            potes_exacto,
        'masa_ultimo_pote_g':     resto_g,
        'masa_por_pote_g':        cap,
        # Compatibilidad Pacojet / mantecadora
        'pacojet_beakers':        math.ceil(target_liters * 1000 / ((1 + or_pct) * 500)),
        'mix_per_beaker':         500 / (1 + or_pct),
        # Campos nuevos — requeridos por test_calculator.py
        'volume_increase':        overrun_pct,
        'final_grams_per_liter':  base_grams / liters_prod if liters_prod > 0 else 0,
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

    # REGLA 1: Sorbete sin lácteos — necesita estabilizante
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

    # REGLA 2: Helado light con poca grasa
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

    # REGLA 3: Triple gelificación (Natulac + CMC + fruta con pectina)
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

    # REGLA 4: Natulac con fruta ácida
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

    # REGLA 5: Lecitina — recomendada si hay grasa significativa
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

    # REGLA 6: ST suficientemente alto — no necesita espesante
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

    # REGLA 7: Trehalosa siempre recomendada para Creami
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
# FORMATO DE TICKET DE PRODUCCIÓN (T1)
# Movido aquí desde app.py para ser testeable y reutilizable.
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
    diags_excluir: set = None,
) -> str:
    """
    Genera el texto del ticket de producción.

    Parámetros
    ----------
    recipe_name           : nombre de la receta
    product_type          : tipo de producto (usar constantes de constants.py)
    machine               : máquina (usar constantes de constants.py)
    ingredient_names      : lista de nombres de ingredientes activos
    lines_for_calculator  : lista de (ingredient_dict, grams, price_per_kg)
    totals                : salida de calc_totals()
    pct                   : salida de calc_percentages()
    derived               : salida de calc_derived()
    kcal                  : salida de calc_calories()
    diags_excluir         : set de keys de diagnósticos a omitir (default: {'creami_overrun_hint'})

    Retorna
    -------
    str  — texto plano listo para descargar o imprimir
    """
    from datetime import datetime
    from constants import DIAGS_EXCLUIR_TICKET, MACHINE_PACOJET

    if diags_excluir is None:
        diags_excluir = DIAGS_EXCLUIR_TICKET

    # Líneas de ingredientes
    ing_lines = "\n".join(
        f"  {n:<38} {g:>7.1f} g"
        for (_, g, _), n in zip(lines_for_calculator, ingredient_names)
    )

    # Semáforo
    def sym(k):
        s = derived.get("status", {}).get(k, "ok")
        return "✅" if s == "ok" else "🔺" if s == "high" else "🔻"

    # Diagnósticos filtrados
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

    # Instrucciones por máquina
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
        f"{diag_block}\n"
        f"{instrucciones}\n"
        "══════════════════════════════════════════════"
    )
