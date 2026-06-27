"""Pure calculation engine — no dependencies"""

import math

# ── Capacidades de máquinas ───────────────────────────────────────────────────
CREAMI_DELUXE_CAPACITY_G   = 640   # gramos útiles, pote 24oz
CREAMI_STANDARD_CAPACITY_G = 430   # gramos útiles, pote 16oz
PACOJET_CAPACITY_ML        = 500   # ml, beaker estándar

# ── Constantes calóricas ──────────────────────────────────────────────────────
KCAL_FAT     = 9.0
KCAL_PROTEIN = 3.5    # 35% del MSNF estimado como proteína
KCAL_SUGAR   = 4.0
KCAL_OTHER   = 2.5    # fibra / almidón / cacao: promedio
KCAL_ALCOHOL = 7.0

# ── Perfil de temperatura Ninja Creami ────────────────────────────────────────
CREAMI_FREEZE_TEMP_C    = -18.0
CREAMI_FREEZE_HOURS_MIN = 24
CREAMI_DELTA_T_MIN      = -1.5    # ΔT mínimo para congelar a -18 °C

# ── Perfiles organolépticos de edulcorantes ───────────────────────────────────
SWEETENER_PROFILES = {
    'sacarosa':         (1.00, 1.00, 4.0, 'Referencia — dulzor limpio y redondo',        'inmediato'),
    'dextrosa':         (0.75, 1.90, 4.0, 'Frescor suave positivo en boca fría',         'inmediato'),
    'fructosa':         (1.20, 1.90, 4.0, 'Muy dulce en frío, puede ser empalagoso',     'inmediato'),
    'trehalosa':        (0.45, 0.70, 4.0, 'Muy suave, casi neutro, crioprotector',       'lento'),
    'alulosa':          (0.70, 1.00, 0.4, 'El más parecido al azúcar, sin retrogusto',   'inmediato'),
    'eritritol':        (0.65, 1.30, 0.2, 'Efecto frescor/mentolado — limitar a 1.5 %',  'inmediato'),
    'maltitol':         (0.75, 0.90, 2.4, 'Similar a sacarosa, posibles molestias GI',   'inmediato'),
    'isomalt':          (0.45, 0.50, 2.0, 'Neutro, antirecristalizante',                 'lento'),
    'azucar invertido': (1.25, 1.90, 4.0, 'Muy antirecristalizante, frescor agradable',  'inmediato'),
    'stevia':           (0.00, 0.00, 0.0, 'Retrogusto amargo/regaliz — máx 0.3 g/kg',   'tardío'),
    'splenda':          (0.00, 0.00, 0.0, 'Stevia + eritritol — ver ambos perfiles',     'tardío'),
    'glucosa de40':     (0.50, 0.80, 4.0, 'Antirecristalizante suave, neutro',           'inmediato'),
    'glucosa de60':     (0.70, 0.90, 4.0, 'Mayor dulzor que DE40, neutro',               'inmediato'),
    'azucar invertido': (1.30, 1.90, 4.0, 'Muy antirecristalizante, frescor agradable',  'inmediato'),
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
        # G1 fix: guard NaN cuando price_per_kg es None o vacío
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

    protein_g = totals.get('msnf', 0) * 0.35   # ~35 % del MSNF es proteína

    kcal = (
        totals.get('fat', 0)      * KCAL_FAT      +
        protein_g                  * KCAL_PROTEIN  +
        totals.get('sugars', 0)   * KCAL_SUGAR    +
        totals.get('other_st', 0) * KCAL_OTHER
    )

    kcal_per_100g = kcal / m * 100
    kcal_per_pote = kcal_per_100g * CREAMI_DELUXE_CAPACITY_G / 100

    return {
        'kcal_total':          round(kcal, 0),
        'kcal_per_100g':       round(kcal_per_100g, 0),
        'kcal_per_pote_deluxe': round(kcal_per_pote, 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DERIVADO — RANGOS, SEMÁFORO, DIAGNÓSTICOS
# ─────────────────────────────────────────────────────────────────────────────

def calc_derived(totals, pct, product_type='Helado/Gelato', machine='Ninja Creami Deluxe'):
    """Ratios, crioscopía, diagnósticos."""
    d = {}
    m = totals['grams']
    if m <= 0:
        return d

    # Ratios
    d['ratio_fat_msnf']    = totals['fat']    / totals['msnf']  if totals['msnf']  > 0 else 0
    d['ratio_sugars_st']   = totals['sugars'] / totals['st']    if totals['st']    > 0 else 0
    d['ratio_st_water']    = totals['st']     / totals['water'] if totals['water'] > 0 else 0
    d['ratio_sugar_water'] = totals['sugars'] / totals['water'] if totals['water'] > 0 else 0

    # Crioscopía estimada (modelo lineal Raoult simplificado)
    pac       = totals['pac']
    water_kg  = totals['water'] / 1000
    d['delta_t'] = -pac * 0.2746 * water_kg if water_kg > 0 else 0

    # Flags de tipo de producto y máquina
    is_sorbet  = 'Sorbete' in product_type or 'Granita' in product_type
    is_vegan   = 'Vegano'  in product_type
    is_frozen  = 'Frozen'  in product_type
    is_creami  = 'Ninja Creami' in machine
    is_paco    = 'Pacojet' in machine

    # ── Rangos objetivo según máquina y tipo de producto ──────────────────────
    if is_creami:
        # Ninja Creami Deluxe / Standard — -18 °C, 640 g, overrun 40-60 %
        if is_sorbet:
            st_lo, st_hi     = 25, 33
            fat_lo, fat_hi   = 0,  2
            msnf_lo, msnf_hi = 0,  1
        elif is_frozen:
            st_lo, st_hi     = 28, 36
            fat_lo, fat_hi   = 2,  8
            msnf_lo, msnf_hi = 3,  9
        elif is_vegan:
            st_lo, st_hi     = 28, 38
            fat_lo, fat_hi   = 2, 15
            msnf_lo, msnf_hi = 0,  2
        else:
            st_lo, st_hi     = 28, 38
            fat_lo, fat_hi   = 4, 15
            msnf_lo, msnf_hi = 5, 10
        sug_lo, sug_hi       = 13, 22
        pod_lo = 115 if is_sorbet else 125
        pod_hi = 175 if is_sorbet else 200
        pac_lo = 120           # mínimo real a -18 °C
        pac_hi = 260
        st_water_lo = 0.42
        st_water_hi = 0.78

        # Temperatura Creami
        d['temp_objetivo']  = CREAMI_FREEZE_TEMP_C
        d['congela_ok']     = d['delta_t'] < CREAMI_DELTA_T_MIN
        d['temp_servicio']  = f"Congelar {CREAMI_FREEZE_HOURS_MIN}h a {CREAMI_FREEZE_TEMP_C}°C → procesar"

    elif is_paco:
        # Pacojet — rangos originales
        if is_sorbet:
            st_lo, st_hi     = 27, 35
            fat_lo, fat_hi   = 0,  2
            msnf_lo, msnf_hi = 0,  2
        elif is_vegan:
            st_lo, st_hi     = 34, 42
            fat_lo, fat_hi   = 2, 18
            msnf_lo, msnf_hi = 0,  2
        elif is_frozen:
            st_lo, st_hi     = 30, 38
            fat_lo, fat_hi   = 2, 10
            msnf_lo, msnf_hi = 4, 10
        else:
            st_lo, st_hi     = 34, 42
            fat_lo, fat_hi   = 4, 20
            msnf_lo, msnf_hi = 6, 11
        sug_lo, sug_hi       = 13, 24
        pod_lo = 115 if is_sorbet else 130
        pod_hi = 180 if is_sorbet else 210
        pac_lo = 200
        pac_hi = 420
        st_water_lo = 0.50
        st_water_hi = 0.78
        d['temp_servicio']  = "Pacotizar a -22°C → servir"

    else:
        # Mantecadora tradicional y otras
        if is_sorbet:
            st_lo, st_hi     = 27, 35
            fat_lo, fat_hi   = 0,  2
            msnf_lo, msnf_hi = 0,  2
        elif is_vegan:
            st_lo, st_hi     = 34, 42
            fat_lo, fat_hi   = 2, 18
            msnf_lo, msnf_hi = 0,  2
        elif is_frozen:
            st_lo, st_hi     = 30, 38
            fat_lo, fat_hi   = 2, 10
            msnf_lo, msnf_hi = 4, 10
        else:
            st_lo, st_hi     = 34, 42
            fat_lo, fat_hi   = 4, 20
            msnf_lo, msnf_hi = 6, 11
        sug_lo, sug_hi       = 13, 24
        pod_lo = 115 if is_sorbet else 130
        pod_hi = 180 if is_sorbet else 210
        pac_lo = 150
        pac_hi = 320
        st_water_lo = 0.48
        st_water_hi = 0.78
        d['temp_servicio']  = "-12 a -14 °C"

    d['targets'] = dict(
        st=(st_lo, st_hi), fat=(fat_lo, fat_hi),
        msnf=(msnf_lo, msnf_hi), sugars=(sug_lo, sug_hi),
        pod=(pod_lo, pod_hi), pac=(pac_lo, pac_hi),
        st_water=(st_water_lo, st_water_hi),
    )

    # ── Semáforo ──────────────────────────────────────────────────────────────
    def status(val, lo, hi):
        if val <= 0: return 'empty'
        if val < lo: return 'low'
        if val > hi: return 'high'
        return 'ok'

    d['status'] = {
        'st':       status(pct.get('st_pct',    0), st_lo,       st_hi),
        'fat':      status(pct.get('fat_pct',   0), fat_lo,      fat_hi),
        'msnf':     status(pct.get('msnf_pct',  0), msnf_lo,     msnf_hi),
        'sugars':   status(pct.get('sugars_pct',0), sug_lo,      sug_hi),
        'pod':      status(pct.get('pod_total', 0), pod_lo,      pod_hi),
        'pac':      status(pct.get('pac_total', 0), pac_lo,      pac_hi),
        'st_water': status(d['ratio_st_water'],     st_water_lo, st_water_hi),
        'water':    status(pct.get('water_pct', 0), 50,          72),
    }

    # ── Diagnósticos ──────────────────────────────────────────────────────────
    diags = []

    def diag(priority, key, condition, title, tip):
        if condition:
            diags.append({'priority': priority, 'key': key, 'title': title, 'tip': tip})

    st_v   = pct.get('st_pct',    0)
    fat_v  = pct.get('fat_pct',   0)
    msnf_v = pct.get('msnf_pct',  0)
    sug_v  = pct.get('sugars_pct',0)
    pod_v  = pct.get('pod_total', 0)
    pac_v  = pct.get('pac_total', 0)
    stw_v  = d['ratio_st_water']
    wat_v  = pct.get('water_pct', 0)

    # ── DIAGNÓSTICOS NINJA CREAMI ─────────────────────────────────────────────
    if is_creami:
        diag('critical', 'st_creami_high', st_v > 40,
             f"ST {st_v:.1f}% → BLOQUE DURO para Ninja Creami",
             "ST >40 % produce bloque que la Creami no puede procesar. "
             "Síntoma: motor forzado, necesitas respin con leche. "
             "Reduce leche en polvo o añade 30-50 g más de leche líquida. "
             "Objetivo para Creami: 28-38 % ST.")

        diag('critical', 'pac_creami_low', 0 < pac_v < 100,
             f"PAC {pac_v:.0f} → NO CONGELA a −18 °C",
             "PAC muy bajo: la mezcla no solidifica completamente en el freezer doméstico. "
             "Añade dextrosa (PAC=1.9) o alulosa (PAC=1.0). Mínimo para Creami: PAC 120.")

        diag('important', 'st_creami_warn', 38 < st_v <= 40,
             f"ST {st_v:.1f}% → puede necesitar respin en Creami",
             "Con ST entre 38-40 % el bloque puede quedar duro. "
             "Deja templar 3-5 minutos antes de procesar. "
             "Si queda granuloso: respin con 1-2 cucharadas de leche fría.")

        diag('important', 'fat_creami_high', fat_v > 15 and not is_sorbet,
             f"Grasa {fat_v:.1f}% → textura gomosa en Creami",
             "La Creami con exceso de grasa produce textura elástica/gomosa. "
             "Reduce crema o sustituye parte por leche líquida. "
             "Objetivo para Creami: grasa 4-15 %.")

        diag('important', 'water_libre_low', 0 < wat_v < 50,
             f"Agua libre {wat_v:.1f}% → mezcla muy concentrada",
             "Poca agua libre: la Creami puede atascarse o dar textura de pasta. "
             "Añade leche líquida o agua destilada hasta llegar a 54-62 % agua libre.")

        diag('adjustable', 'creami_overrun_hint', True,
             "Overrun esperado en Ninja Creami: 40-60 %",
             "La Creami incorpora más aire que el Pacojet. "
             "Mezclas con ST 28-35 % producen overrun 50-60 % (textura aireada). "
             "Mezclas con ST 35-40 % producen overrun 35-45 % (textura más densa).")

    # ── DIAGNÓSTICOS PACOJET ──────────────────────────────────────────────────
    if is_paco:
        diag('critical', 'msnf_high', msnf_v > 11.5,
             f"MSNF {msnf_v:.1f}% → ARENADO IRREVERSIBLE",
             "Cristalización de lactosa — defecto permanente. Reduce leche en polvo descremada "
             "de inmediato. Sustituye por leche líquida o crema.")

        diag('critical', 'pac_pacojet', pac_v > 450,
             f"PAC {pac_v:.0f} → NO CONGELA a −22 °C",
             "Mezcla no solidifica → beaker inutilizable. Elimina dextrosa o fructosa en exceso. "
             "Elimina alcohol si supera 40 g/kg.")

        diag('important', 'stw_low', 0 < stw_v < 0.50,
             f"Ratio ST/Agua {stw_v:.3f} → demasiada agua libre (Pacojet)",
             "El raspado produce capas de hielo. Concentra sólidos: más leche en polvo o azúcar. "
             "En sorbetes de fruta acuosa: reduce pulpa.")

    # ── DIAGNÓSTICOS GENERALES ────────────────────────────────────────────────
    diag('critical', 'st_high', st_v > (40 if is_creami else 44),
         f"ST {st_v:.1f}% → SOBRECONCENTRADO",
         "Textura de pasta, overrun imposible. Añade leche entera o agua hasta el rango objetivo.")

    diag('important', 'st_low', 0 < st_v < st_lo,
         f"ST {st_v:.1f}% → bajos (mín {st_lo}%)",
         "Cristales grandes, cuerpo acuoso. ① Leche en polvo descremada. "
         "② Inulina HP. ③ Sustituye leche por crema.")

    diag('important', 'fat_low', 0 < fat_v < fat_lo and not is_sorbet,
         f"Grasa {fat_v:.1f}% → baja (mín {fat_lo}%)",
         "Textura acuosa, poco cuerpo. ① Sustituye leche por crema 35 %. "
         "② Yema de huevo (32 % MG + lecitina). ③ Crema de coco si es vegano.")

    diag('important', 'fat_high', fat_v > fat_hi + 2 and not is_creami,
         f"Grasa {fat_v:.1f}% → excesiva (máx {fat_hi}%)",
         "Sabor mantecoso, overrun pobre. Sustituye parte de crema por leche entera.")

    diag('important', 'sug_high', sug_v > sug_hi + 2,
         f"Azúcares {sug_v:.1f}% → excesivos (máx {sug_hi}%)",
         "Helado muy blando, empalagoso. ① Trehalosa (mismo ST, POD 0.45). "
         "② Isomalt. ③ Inulina HP para mantener volumen.")

    diag('important', 'msnf_low', 0 < msnf_v < msnf_lo and not is_sorbet and not is_vegan,
         f"MSNF {msnf_v:.1f}% → bajo (mín {msnf_lo}%)",
         "Poca estructura proteica, overrun pobre. Añade leche en polvo descremada "
         "(52 % MSNF, la fuente más concentrada).")

    diag('adjustable', 'pod_low', 0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → dulzor bajo (mín {pod_lo})",
         "① Fructosa (POD 1.2). ② 0.5 g/kg de Stevia Reb-A. "
         "③ 1-2 g/kg de sal marina potencia el dulce.")

    diag('adjustable', 'pod_high', pod_v > pod_hi,
         f"POD {pod_v:.0f} → puede fatigar el paladar",
         "① Ácido cítrico 1-3 g/kg. ② Sustituye fructosa por glucosa DE40 (POD 0.5). "
         "③ Sal marina equilibra.")

    diag('adjustable', 'pac_low', not is_paco and not is_creami and 0 < pac_v < pac_lo,
         f"PAC {pac_v:.0f} → bajo para mantecadora",
         "Helado duro al servir. ① Dextrosa monohidrato (PAC=1.9). "
         "② Fructosa (PAC=1.9). ③ Azúcar invertido.")

    diag('adjustable', 'sug_low', 0 < sug_v < sug_lo,
         f"Azúcares {sug_v:.1f}% → bajos (mín {sug_lo}%)",
         "① Aumenta sacarosa o dextrosa. ② Fructosa si es sorbete. "
         "③ Glucosa DE40 para textura sin exceso de dulzor.")

    d['diagnostics'] = diags
    return d


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE OVERRUN
# ─────────────────────────────────────────────────────────────────────────────

def overrun_calc(base_grams, overrun_pct, target_liters, machine='Ninja Creami Deluxe'):
    or_pct = overrun_pct / 100

    if 'Deluxe' in machine:
        cap = CREAMI_DELUXE_CAPACITY_G
    elif 'Standard' in machine:
        cap = CREAMI_STANDARD_CAPACITY_G
    else:
        cap = PACOJET_CAPACITY_ML   # Pacojet / mantecadora: lógica original

    base_needed    = target_liters * 1000 / (1 + or_pct)
    liters_prod    = base_grams / 1000 * (1 + or_pct)
    potes_exacto   = base_grams / cap if cap > 0 else 0
    potes_enteros  = int(potes_exacto)
    resto_g        = (potes_exacto - potes_enteros) * cap

    return {
        'base_needed_g':       base_needed,
        'liters_from_base':    liters_prod,
        'potes_completos':     potes_enteros,
        'potes_total':         potes_exacto,
        'masa_ultimo_pote_g':  resto_g,
        'masa_por_pote_g':     cap,
        # Compatibilidad hacia atrás (Pacojet)
        'pacojet_beakers':     math.ceil(target_liters * 1000 / ((1 + or_pct) * 500)),
        'mix_per_beaker':      500 / (1 + or_pct),
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

    water_pct  = pct.get('water_pct', 0)
    fat_pct    = pct.get('fat_pct',   0)
    st_pct     = pct.get('st_pct',    0)

    is_sorbet  = 'Sorbete' in product_type or 'Granita' in product_type
    is_creami  = 'Ninja Creami' in machine
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
            'reason':        f'Sorbete sin lácteos con {water_pct:.1f} % agua libre. '
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
            'reason':        f'Grasa baja ({fat_pct:.1f} %) y agua libre alta ({water_pct:.1f} %). '
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
            'reason':        f'ST {st_pct:.1f} % y agua libre {water_pct:.1f} %. '
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

        # Solo incluir si aporta POD/PAC significativo o tiene azúcares
        if pod_contrib > 0.5 or pac_contrib > 0.5 or float(ing.get('sugars', 0)) > 5:
            total_pod += pod_contrib
            total_pac += pac_contrib

            name_lower = ing['name'].lower()
            profile = None
            for key, prof in SWEETENER_PROFILES.items():
                if key in name_lower:
                    profile = prof
                    break

            # Advertencias específicas
            pct_in_mix = g / total_grams_all * 100
            warning = None
            if 'eritritol' in name_lower and pct_in_mix > 1.5:
                warning = f"⚠️ Eritritol al {pct_in_mix:.1f} % → efecto mentolado probable. Máximo 1.5 %"
            elif 'stevia' in name_lower and g > 0.5:
                warning = f"⚠️ Stevia {g:.1f} g → retrogusto posible. Máximo 0.3 g/kg"
            elif 'fructosa' in name_lower and pct_in_mix > 8:
                warning = f"⚠️ Fructosa alta ({pct_in_mix:.1f} %) → puede resultar empalagosa"

            sweetener_lines.append({
                'nombre':        ing['name'],
                'gramos':        g,
                'pod_contrib':   round(pod_contrib, 1),
                'pac_contrib':   round(pac_contrib, 1),
                'sugars_g':      round(g * float(ing.get('sugars', 0)) / 100, 1),
                'kcal_estimadas':round(g * float(ing.get('sugars', 0)) / 100 * 4, 1),
                'efecto_sabor':  profile[3] if profile else 'Sin perfil registrado',
                'perfil_dulzor': profile[4] if profile else '—',
                'warning':       warning,
            })

    # Calcular porcentajes del total
    for s in sweetener_lines:
        s['pct_pod'] = round(s['pod_contrib'] / total_pod * 100, 1) if total_pod > 0 else 0
        s['pct_pac'] = round(s['pac_contrib'] / total_pac * 100, 1) if total_pac > 0 else 0

    return sweetener_lines
