"""
Pure calculation engine — no dependencies
Rangos y diagnósticos completamente adaptativos por tipo de producto y maquinaria.

Tipos de producto soportados:
  Helado/Gelato       — referencia clásica, mantecadora o Pacojet
  Helado Ligero       — low-fat (2-6% MG), más MSNF compensatorio
  Sorbete             — sin lácteos, fruta base, azúcar libre alta
  Granita             — sorbete rústico, cristales tolerados, menos ST
  Gelato Vegano       — grasa vegetal, sin MSNF, estabilizantes clave
  Frozen Yogurt       — acidez láctica, grasa media-baja

Maquinaria:
  Pacojet             — raspado mecánico; PAC inferior irrelevante,
                        superior crítico; MSNF tolera hasta 12.5%
  Mantecadora         — crioscopia dominante; PAC bilateral importante;
                        MSNF límite 11.5%
"""

# ── CÁLCULO BASE ──────────────────────────────────────────────────────────────

def calc_line(ing, grams):
    """Contribución nutricional de una línea en gramos absolutos."""
    if not ing or not grams:
        return {}
    g = float(grams)
    return {
        'grams':    g,
        'fat':      g * ing['fat']      / 100,
        'msnf':     g * ing['msnf']     / 100,
        'sugars':   g * ing['sugars']   / 100,
        'other_st': g * ing['other_st'] / 100,
        'st':       g * (ing['fat'] + ing['msnf'] + ing['sugars'] + ing['other_st']) / 100,
        'pod':      g * ing['pod'],
        'pac':      g * ing['pac'],
        'water':    g * ing['water']    / 100,
    }


def calc_totals(lines_with_ings):
    """
    lines_with_ings: list of (ingredient_dict, grams, price_per_kg)
    Devuelve totales absolutos en gramos + coste.
    """
    totals = dict(grams=0, fat=0, msnf=0, sugars=0, other_st=0,
                  st=0, pod=0, pac=0, water=0, cost=0)
    for ing, grams, price_per_kg in lines_with_ings:
        if not ing or not grams:
            continue
        c = calc_line(ing, grams)
        for k in totals:
            if k != 'cost':
                totals[k] += c.get(k, 0)
        totals['cost'] += (grams / 1000) * (price_per_kg or 0)
    return totals


def calc_percentages(totals):
    """Porcentajes respecto a la masa total."""
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
        'cost_per_100g': totals['cost'] / m * 100,
    }


# ── RANGOS ADAPTATIVOS ────────────────────────────────────────────────────────

def _get_targets(product_type, machine):
    """
    Devuelve un dict con todos los rangos (lo, hi) adaptados al
    tipo de producto y la maquinaria.  Cada clave puede ser:
      - (lo, hi)          → rango bilateral normal
      - (None, hi)        → solo límite superior relevante
      - (lo, None)        → solo límite inferior relevante
    """
    is_pacojet = 'Pacojet' in machine

    # ── Clasificadores de tipo ────────────────────────────────────────────
    is_gelato   = product_type in ('Helado/Gelato',)
    is_light    = 'Ligero' in product_type
    is_sorbet   = 'Sorbete' in product_type
    is_granita  = 'Granita' in product_type
    is_vegan    = 'Vegano'  in product_type
    is_frozen   = 'Frozen'  in product_type
    is_sorbet_like = is_sorbet or is_granita   # sin lácteos

    # ── ST (Sólidos Totales) ──────────────────────────────────────────────
    if is_granita:
        st = (22, 30)       # Granita admite más agua, cristales son parte del carácter
    elif is_sorbet:
        st = (27, 35)
    elif is_light:
        st = (32, 40)       # Compensar grasa baja con más MSNF/azúcar
    elif is_frozen:
        st = (30, 38)
    elif is_vegan:
        st = (34, 42)
    else:                   # Helado/Gelato clásico
        st = (34, 42)

    # ── GRASA ─────────────────────────────────────────────────────────────
    if is_sorbet_like:
        fat = (0, 2)        # Tolerancia mínima (leche de coco ocasional)
    elif is_light:
        fat = (2, 6)        # Helado ligero: grasa reducida intencionalmente
    elif is_vegan:
        fat = (4, 18)       # Amplio: leche de coco, aguacate, pasta frutos secos
    elif is_frozen:
        fat = (2, 10)
    else:                   # Helado/Gelato
        fat = (4, 20)

    # ── MSNF ──────────────────────────────────────────────────────────────
    if is_sorbet_like:
        msnf = (0, 2)
    elif is_vegan:
        msnf = (0, 2)
    elif is_light:
        msnf = (8, 13)      # Más MSNF para compensar grasa reducida
    elif is_frozen:
        msnf = (4, 10)
    else:                   # Helado/Gelato
        msnf = (6, 11)

    # ── MSNF: umbral crítico de arenado varía con maquinaria ─────────────
    # Pacojet: ciclo térmico más corto → menos recristalización de lactosa
    msnf_critical = 12.5 if is_pacojet else 11.5

    # ── AZÚCARES ──────────────────────────────────────────────────────────
    if is_granita:
        sug = (18, 28)      # Granita tolera más azúcar libre
    elif is_sorbet:
        # Fruta madura ya aporta 8-16% azúcares → mínimo más alto
        sug = (16, 26)
    elif is_light:
        sug = (14, 22)      # Margen algo más estrecho
    else:
        sug = (13, 24)

    # ── POD ───────────────────────────────────────────────────────────────
    if is_granita:
        pod = (100, 170)    # Granita: se sirve muy fría, dulzor percibido bajo
    elif is_sorbet_like:
        pod = (115, 180)
    elif is_light:
        pod = (125, 200)
    else:
        pod = (130, 210)

    # ── PAC ───────────────────────────────────────────────────────────────
    # Pacojet: el raspado mecánico hace el límite inferior casi irrelevante.
    # Solo el límite superior importa (no congelar = beaker inutilizable).
    # Mantecadora: PAC bilateral — demasiado bajo → piedra; demasiado alto → no congela.
    if is_pacojet:
        pac = (None, 420)   # Sin límite inferior efectivo; superior crítico
    else:
        if is_sorbet_like:
            pac = (160, 320)    # Sorbete en mantecadora necesita más crioscopia
        elif is_light:
            pac = (140, 300)
        else:
            pac = (150, 320)

    # ── RATIO ST/AGUA ─────────────────────────────────────────────────────
    # Pacojet: raspado compensa algo más de agua libre, pero no indefinidamente
    # Mantecadora: más tolerante al agua libre por batido continuo
    if is_pacojet:
        if is_sorbet_like:
            st_water = (0.45, 0.85)
        else:
            st_water = (0.50, 0.85)
    else:
        # Mantecadora: rango más amplio porque el batido rompe cristales
        if is_sorbet_like:
            st_water = (0.38, 0.95)
        else:
            st_water = (0.42, 0.95)

    return {
        'st':           st,
        'fat':          fat,
        'msnf':         msnf,
        'msnf_critical': msnf_critical,   # valor escalar, no rango
        'sugars':       sug,
        'pod':          pod,
        'pac':          pac,
        'st_water':     st_water,
        # Flags de contexto útiles para diagnósticos
        '_is_pacojet':      is_pacojet,
        '_is_sorbet_like':  is_sorbet_like,
        '_is_sorbet':       is_sorbet,
        '_is_granita':      is_granita,
        '_is_light':        is_light,
        '_is_vegan':        is_vegan,
        '_is_frozen':       is_frozen,
    }


def _status(val, lo, hi):
    """
    Evalúa el estado de un valor respecto a un rango (lo, hi).
    lo o hi pueden ser None para rangos unilaterales.
    """
    if val <= 0:
        return 'empty'
    if lo is not None and val < lo:
        return 'low'
    if hi is not None and val > hi:
        return 'high'
    return 'ok'


# ── MOTOR DE DIAGNÓSTICOS ─────────────────────────────────────────────────────

def _build_diagnostics(totals, pct, tgt):
    """
    Genera la lista de diagnósticos priorizados.
    Recibe los totales, porcentajes y el dict de targets ya calculado.
    """
    diags = []

    def diag(priority, key, condition, title, tip):
        if condition:
            diags.append({'priority': priority, 'key': key,
                          'title': title, 'tip': tip})

    # Extraer valores
    st_v   = pct.get('st_pct', 0)
    fat_v  = pct.get('fat_pct', 0)
    msnf_v = pct.get('msnf_pct', 0)
    sug_v  = pct.get('sugars_pct', 0)
    pod_v  = pct.get('pod_total', 0)
    pac_v  = pct.get('pac_total', 0)

    # Ratio ST/Agua
    stw_v  = totals['st'] / totals['water'] if totals['water'] > 0 else 0

    # Extraer rangos
    st_lo,  st_hi   = tgt['st']
    fat_lo, fat_hi  = tgt['fat']
    msnf_lo, msnf_hi= tgt['msnf']
    sug_lo, sug_hi  = tgt['sugars']
    pod_lo, pod_hi  = tgt['pod']
    pac_lo, pac_hi  = tgt['pac']          # pac_lo puede ser None
    stw_lo, stw_hi  = tgt['st_water']

    msnf_crit = tgt['msnf_critical']

    # Flags
    is_pacojet     = tgt['_is_pacojet']
    is_sorbet_like = tgt['_is_sorbet_like']
    is_sorbet      = tgt['_is_sorbet']
    is_granita     = tgt['_is_granita']
    is_light       = tgt['_is_light']
    is_vegan       = tgt['_is_vegan']

    # ── CRÍTICOS ─────────────────────────────────────────────────────────

    # MSNF arenado: umbral diferente según máquina
    diag('critical', 'msnf_arenado',
         msnf_v > msnf_crit and not is_sorbet_like and not is_vegan,
         f"MSNF {msnf_v:.1f}% → RIESGO ARENADO {'(Pacojet: >{msnf_crit}%)' if is_pacojet else '(Mantecadora: >{msnf_crit}%)'}",
         f"Cristalización de lactosa — defecto irreversible en boca. "
         f"{'En Pacojet el umbral es 12.5% por ciclo térmico corto, pero lo has superado.' if is_pacojet else 'Límite estricto en mantecadora por recristalización lenta.'} "
         f"Reduce leche en polvo descremada. Sustituye por leche líquida, crema, o inulina HP.")

    # PAC Pacojet: solo límite superior (el inferior es irrelevante mecánicamente)
    diag('critical', 'pac_pacojet_alto',
         is_pacojet and pac_v > 420,
         f"PAC {pac_v:.0f} → NO CONGELA en Pacojet (−22°C)",
         "Con PAC >420 la mezcla no solidifica: el beaker queda líquido y es inutilizable. "
         "Elimina dextrosa o fructosa en exceso. Reduce alcohol si supera 40g/kg. "
         "Sustituye por trehalosa (PAC=0.7) o glucosa DE40 (PAC=0.64).")

    # PAC mantecadora: límite superior también crítico
    diag('critical', 'pac_mantecadora_alto',
         not is_pacojet and pac_hi is not None and pac_v > pac_hi + 50,
         f"PAC {pac_v:.0f} → EXCESIVO para mantecadora (máx recomendado {pac_hi})",
         "La mezcla no solidificará correctamente. Reduce azúcares depresores: "
         "dextrosa, fructosa, azúcar invertido. Sustituye parcialmente por trehalosa o isomalt.")

    # ST sobreconcentrado
    diag('critical', 'st_alto',
         st_v > 44,
         f"ST {st_v:.1f}% → SOBRECONCENTRADO (máx absoluto ~44%)",
         "Textura de pasta, overrun imposible, cristalización masiva. "
         "Añade leche entera o agua hasta bajar a 34-42% ST.")

    # ── IMPORTANTES ──────────────────────────────────────────────────────

    # ST bajo
    diag('important', 'st_bajo',
         0 < st_v < st_lo,
         f"ST {st_v:.1f}% → bajo (mín {st_lo}%)",
         f"Cuerpo acuoso, cristales grandes en boca. "
         f"{'① Aumenta sacarosa o glucosa atomizada. ② Reduce agua o pulpa de fruta acuosa.' if is_sorbet_like else '① Leche en polvo descremada (+MSNF +ST). ② Inulina HP (no añade dulzor). ③ Sustituye leche entera por crema.'}")

    # Grasa baja (no aplica a sorbetes ni granita)
    diag('important', 'grasa_baja',
         0 < fat_v < fat_lo and not is_sorbet_like,
         f"Grasa {fat_v:.1f}% → baja (mín {fat_lo}%{'  — Helado Ligero: rango intencionalmente estrecho' if is_light else ''})",
         f"{'Helado ligero: normal si es intencional. Para más cuerpo sin grasa: inulina HP + yema + MSNF alto.' if is_light else '① Sustituye leche entera por crema 35%. ② Yema de huevo (32% MG + lecitina natural). ③ Crema de coco si es vegano.'}")

    # Grasa alta
    diag('important', 'grasa_alta',
         fat_hi is not None and fat_v > fat_hi + 2,
         f"Grasa {fat_v:.1f}% → excesiva (máx {fat_hi}%)",
         f"{'Sorbete con exceso de grasa: pierde frescura, textura grumosa en frío.' if is_sorbet_like else 'Sabor mantecoso, overrun pobre, sensación untuosa excesiva. Sustituye parte de crema por leche entera. Compensa estructura con leche en polvo descremada.'}")

    # Azúcares altos
    diag('important', 'azucares_altos',
         sug_v > sug_hi + 2,
         f"Azúcares {sug_v:.1f}% → excesivos (máx {sug_hi}%)",
         f"{'Sorbete muy blando, dificultad de congelación en mantecadora.' if is_sorbet_like else 'Helado muy blando, empalagoso, PAC disparado.'} "
         f"① Trehalosa (mismo ST, POD=0.45, PAC=0.70). ② Isomalt. ③ Inulina HP para mantener volumen sin dulzor.")

    # MSNF bajo (no aplica a sorbetes ni veganos)
    diag('important', 'msnf_bajo',
         0 < msnf_v < msnf_lo and not is_sorbet_like and not is_vegan,
         f"MSNF {msnf_v:.1f}% → bajo (mín {msnf_lo}%{'  — Helado Ligero: MSNF es tu estructura principal' if is_light else ''})",
         f"{'Helado ligero: sin grasa y sin MSNF suficiente, la textura será acuosa y sin cuerpo.' if is_light else 'Poca estructura proteica, overrun pobre, cristales más grandes.'} "
         f"Añade leche en polvo descremada (52% MSNF, la fuente más concentrada).")

    # Ratio ST/Agua bajo — Pacojet
    diag('important', 'stw_bajo_pacojet',
         is_pacojet and stw_lo is not None and 0 < stw_v < stw_lo,
         f"Ratio ST/Agua {stw_v:.3f} → demasiada agua libre (Pacojet, mín {stw_lo})",
         f"El raspado produce capas de hielo visibles. "
         f"{'Concentra azúcares: más sacarosa o glucosa. Reduce pulpa acuosa.' if is_sorbet_like else 'Concentra sólidos: más leche en polvo o azúcar. Considera reducir agua libre.'}")

    # Ratio ST/Agua bajo — Mantecadora (umbral más permisivo)
    diag('important', 'stw_bajo_mantecadora',
         not is_pacojet and stw_lo is not None and 0 < stw_v < stw_lo,
         f"Ratio ST/Agua {stw_v:.3f} → agua libre alta para mantecadora (mín {stw_lo})",
         "La mantecadora tolera más agua libre que Pacojet, pero has superado el mínimo. "
         "Puede resultar en textura granulosa. Aumenta sólidos o reduce dilución.")

    # PAC bajo Pacojet — solo informativo, no alerta real
    diag('adjustable', 'pac_bajo_pacojet',
         is_pacojet and pac_v < 80 and pac_v > 0,
         f"PAC {pac_v:.0f} → muy bajo (Pacojet: irrelevante, solo informativo)",
         "En Pacojet el PAC bajo no es problema: el raspado mecánico crea textura independientemente "
         "de la crioscopia. Solo asegúrate de que la mezcla congele sólida antes del pacotizing (−22°C durante ≥24h).")

    # PAC bajo mantecadora
    diag('adjustable', 'pac_bajo_mantecadora',
         not is_pacojet and pac_lo is not None and 0 < pac_v < pac_lo,
         f"PAC {pac_v:.0f} → bajo para mantecadora (mín {pac_lo})",
         "Helado duro al servir, difícil de porcionar. "
         "① Dextrosa monohidrato (PAC=1.9 — el más potente). ② Fructosa (PAC=1.9). "
         "③ Azúcar invertido (PAC=1.9 + efecto antirecristalizante).")

    # POD bajo
    diag('adjustable', 'pod_bajo',
         0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → dulzor bajo (mín {pod_lo})",
         "① Fructosa (POD=1.2, especialmente dulce en frío). "
         "② 0.5g/kg de Stevia Reb-A (POD ~200, sin impacto ST ni PAC). "
         "③ 1-2g/kg de sal marina fina potencia la percepción de dulzor.")

    # POD alto
    diag('adjustable', 'pod_alto',
         pod_hi is not None and pod_v > pod_hi,
         f"POD {pod_v:.0f} → puede fatigar el paladar (máx {pod_hi})",
         "① Ácido cítrico 1-3g/kg equilibra y eleva frescura. "
         "② Sustituye fructosa por glucosa DE40 (POD=0.5). "
         "③ Sal marina 1g/kg contrarresta el exceso de dulce.")

    # Ratio ST/Agua alto (demasiado denso)
    diag('adjustable', 'stw_alto',
         stw_hi is not None and stw_v > stw_hi,
         f"Ratio ST/Agua {stw_v:.3f} → mezcla muy densa (máx {stw_hi})",
         "Overrun reducido, textura compacta. No es crítico si buscas gelato denso intencional. "
         "Para abrir textura: añade leche entera o reduce ingredientes secos.")

    # Azúcares bajos
    diag('adjustable', 'azucares_bajos',
         0 < sug_v < sug_lo,
         f"Azúcares {sug_v:.1f}% → bajos (mín {sug_lo}%)",
         f"{'① Aumenta sacarosa. ② Fructosa (más dulzor en frío). ③ Glucosa DE40 para textura sin exceso de dulzor.' if not is_sorbet_like else '① Aumenta sacarosa. ② La fruta madura tiene más Brix — revisa madurez. ③ Glucosa DE40 aporta ST sin dulzor excesivo.'}")

    # Tip especial: grasa vegetal en sorbete (0.3-1.5%) puede mejorar textura
    diag('adjustable', 'tip_grasa_sorbete',
         is_sorbet and fat_v == 0,
         "Sorbete sin grasa — tip de textura",
         "Un toque de 0.3-1% de leche de coco o crema de coco (grasa láurica) "
         "puede mejorar notablemente la cremosidad sin comprometer el carácter frutal. "
         "Permanece dentro del rango 0-2% de grasa para sorbete.")

    return diags


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────────────────────

def calc_derived(totals, pct, product_type='Helado/Gelato', machine='Pacojet'):
    """
    Calcula ratios, crioscopía, targets adaptativos, estados y diagnósticos.
    Punto de entrada principal para la UI.
    """
    d = {}
    m = totals['grams']
    if m <= 0:
        return d

    # ── Ratios ────────────────────────────────────────────────────────────
    d['ratio_fat_msnf']    = totals['fat']    / totals['msnf']  if totals['msnf']  > 0 else 0
    d['ratio_sugars_st']   = totals['sugars'] / totals['st']    if totals['st']    > 0 else 0
    d['ratio_st_water']    = totals['st']     / totals['water'] if totals['water'] > 0 else 0
    d['ratio_sugar_water'] = totals['sugars'] / totals['water'] if totals['water'] > 0 else 0

    # ── Crioscopía (método Lescure simplificado) ──────────────────────────
    pac       = totals['pac']
    water_kg  = totals['water'] / 1000
    d['delta_t'] = -pac * 0.2746 * water_kg if water_kg > 0 else 0

    # ── Targets adaptativos ───────────────────────────────────────────────
    tgt = _get_targets(product_type, machine)
    d['targets'] = tgt

    # ── Estados (para coloreado en UI) ───────────────────────────────────
    # Para PAC en Pacojet: pac_lo es None → solo penaliza por arriba
    d['status'] = {
        'st':       _status(pct.get('st_pct', 0),    *tgt['st']),
        'fat':      _status(pct.get('fat_pct', 0),   *tgt['fat']),
        'msnf':     _status(pct.get('msnf_pct', 0),  *tgt['msnf']),
        'sugars':   _status(pct.get('sugars_pct', 0),*tgt['sugars']),
        'pod':      _status(pct.get('pod_total', 0),  *tgt['pod']),
        'pac':      _status(pct.get('pac_total', 0),  *tgt['pac']),
        'st_water': _status(d['ratio_st_water'],       *tgt['st_water']),
    }

    # ── Diagnósticos ──────────────────────────────────────────────────────
    d['diagnostics'] = _build_diagnostics(totals, pct, tgt)

    return d


# ── OVERRUN ───────────────────────────────────────────────────────────────────

def overrun_calc(base_grams, overrun_pct, target_liters):
    """
    Calcula parámetros de producción según el overrun deseado.
    base_grams    : masa de la mezcla base que tienes
    overrun_pct   : % de overrun (ej. 30 → 30%)
    target_liters : litros de producto final que quieres obtener
    """
    import math
    or_f = overrun_pct / 100
    base_needed = target_liters * 1000 / (1 + or_f)
    return {
        'base_needed_g':         base_needed,
        'liters_from_base':      base_grams / 1000 * (1 + or_f),
        'pacojet_beakers':       math.ceil(base_needed / 500),   # cada beaker lleva 500g de mezcla
        'mix_per_beaker':        500 / (1 + or_f),
        'volume_increase':       or_f * 100,
        'final_grams_per_liter': 1000 / (1 + or_f),
    }
