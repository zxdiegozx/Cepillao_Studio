"""
diagnostics.py — Sistema de diagnósticos y recomendaciones de formulación.

Responsabilidad única: evaluar la composición de la mezcla y emitir
diagnósticos priorizados con sugerencias de corrección.

Funciones públicas:
    get_targets(product_type, machine)         → rangos objetivo por tipo/máquina
    calc_derived(totals, pct, ...)             → métricas + diagnósticos completos
    recommend_stabilizers(totals, pct, ...)    → recomendaciones de estabilizantes
"""

from constants import (
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO,
    PRODUCT_FROZEN, PRODUCT_LIGERO,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    PRIORITY_CRITICAL, PRIORITY_IMPORTANT, PRIORITY_ADJUSTABLE,
    CREAMI_OVERRUN_PCT,
)
from .calc_cryoscopy import calc_cryoscopy
from .calc_nutrition import _detect_alcohol_lines


# ── Alias público (app.py puede importar _get_targets desde aquí) ─────────────
def get_targets(product_type: str = 'Helado/Gelato',
                machine: str = 'Ninja Creami Deluxe') -> dict:
    """
    Retorna rangos de composición según máquina y tipo de producto.
    Todos los rangos son tuplas (lo, hi).
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
        sugars = (13, 22)
        pod    = (115, 175) if is_sorbet else (125, 200)
        pac    = (120, 260)
        stw    = (0.42, 0.78)
        msnf_c = 11.0
    else:
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
        sugars = (13, 24)
        pod    = (115, 180) if is_sorbet else (130, 210)
        pac    = (150, 320)
        stw    = (0.48, 0.78)
        msnf_c = 11.5

    return {
        'st': st, 'fat': fat, 'msnf': msnf,
        'sugars': sugars, 'pod': pod, 'pac': pac,
        'st_water': stw, 'msnf_critical': msnf_c,
    }


def _status(val: float, lo, hi) -> str:
    """Semáforo de rango: 'empty' | 'low' | 'ok' | 'high'."""
    if val == 0 and lo is not None and lo > 0:
        return 'empty'
    if lo is not None and val < lo:
        return 'low'
    if hi is not None and val > hi:
        return 'high'
    return 'ok'


# ─────────────────────────────────────────────────────────────────────────────
# CALC_DERIVED
# ─────────────────────────────────────────────────────────────────────────────

def calc_derived(totals: dict, pct: dict,
                 product_type: str = 'Helado/Gelato',
                 machine: str = 'Ninja Creami Deluxe',
                 lines_with_ings: list = None,
                 config: dict = None) -> dict:
    """
    Calcula métricas derivadas y genera diagnósticos priorizados.

    config: dict opcional con overrides de rangos desde la UI.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    targets   = get_targets(product_type, machine)
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

    st_v    = pct.get('st_pct',    0)
    fat_v   = pct.get('fat_pct',   0)
    msnf_v  = pct.get('msnf_pct',  0)
    sug_v   = pct.get('sugars_pct', 0)
    pod_v   = pct.get('pod_total',  0)
    pac_v   = pct.get('pac_total',  0)
    water_v = pct.get('water_pct',  0)
    stw_v   = (st_v / water_v) if water_v > 0 else None   # guard FIX-5

    diags: list = []

    def diag(priority, key, condition, title, tip):
        if condition:
            diags.append({'priority': priority, 'key': key, 'title': title, 'tip': tip})

    # ── Crioscopía ────────────────────────────────────────────────────────────
    crio = calc_cryoscopy(totals)
    zona = crio['crio_zona']

    # ── Alcohol ───────────────────────────────────────────────────────────────
    alcohol_lines   = _detect_alcohol_lines(lines_with_ings or [])
    ethanol_total_g = sum(a['ethanol_g'] for a in alcohol_lines)
    ethanol_pct_mix = ethanol_total_g / m * 100 if m else 0
    nombres_alcohol = ', '.join(a['ingredient_name'] for a in alcohol_lines)

    # ── Diagnósticos Creami ───────────────────────────────────────────────────
    if is_creami:
        _diags_crio_creami(diag, zona, crio['delta_t'])
        diag(PRIORITY_IMPORTANT, 'agua_alta_creami', water_v > 70,
             f"Agua libre {water_v:.1f}% → muy alta para Creami",
             "La Creami no tritura bien bases muy acuosas → textura icy. "
             "Añade leche en polvo descremada o reduce líquidos.")
        diag(PRIORITY_ADJUSTABLE, 'agua_baja_creami', 0 < water_v < 48,
             f"Agua libre {water_v:.1f}% → baja",
             "Mezcla muy concentrada → overrun bajo y textura densa. "
             "Añade leche líquida o agua hasta 54-62%.")
        diag(PRIORITY_ADJUSTABLE, 'creami_overrun_hint', True,
             f"Overrun estimado Ninja Creami: ~{CREAMI_OVERRUN_PCT.get(machine, 50)}%",
             f"La {machine} incorpora aire mecánicamente. "
             "ST 28-35% → overrun 50-65% (ligero). ST 35-40% → overrun 35-45% (denso).")

    # ── Diagnósticos Mantecadora ──────────────────────────────────────────────
    if not is_creami:
        diag(PRIORITY_CRITICAL, 'msnf_arenado', msnf_v > msnf_crit,
             f"MSNF {msnf_v:.1f}% → ARENADO IRREVERSIBLE (umbral {msnf_crit}%)",
             "Cristalización de lactosa — defecto permanente. "
             "Reduce leche en polvo descremada.")
        diag(PRIORITY_ADJUSTABLE, 'pac_bajo_mantecadora', 0 < pac_v < pac_lo,
             f"PAC {pac_v:.0f} → bajo para mantecadora (mín {pac_lo})",
             "Helado duro al servir. ① Dextrosa (PAC=1.9). "
             "② Fructosa (PAC=1.9). ③ Azúcar invertido.")
        _diags_crio_mantecadora(diag, zona, crio['delta_t'])

    # ── Ratio ST/Agua ─────────────────────────────────────────────────────────
    if stw_v is not None:
        diag(PRIORITY_IMPORTANT, 'stw_bajo', stw_v < stw_lo,
             f"Ratio ST/Agua {stw_v:.3f} → bajo ({stw_lo:.2f}–{stw_hi:.2f})",
             "Demasiada agua libre → cristales grandes, textura icy. "
             "Añade leche en polvo, azúcar, o reduce líquidos.")
        diag(PRIORITY_ADJUSTABLE, 'stw_alto', stw_v > stw_hi,
             f"Ratio ST/Agua {stw_v:.3f} → alto ({stw_lo:.2f}–{stw_hi:.2f})",
             "Mezcla sobreconcentrada → textura pastosa, overrun difícil. "
             "Añade leche líquida o agua.")

    # ── Generales ─────────────────────────────────────────────────────────────
    st_max = 40 if is_creami else 44
    diag(PRIORITY_CRITICAL, 'st_alto', st_v > st_max,
         f"ST {st_v:.1f}% → SOBRECONCENTRADO",
         "Textura de pasta, overrun imposible. Añade leche entera o agua.")
    diag(PRIORITY_CRITICAL, 'st_bajo', 0 < st_v < st_lo,
         f"ST {st_v:.1f}% → muy bajo (mín {st_lo}%)",
         "Faltarán sólidos para dar cuerpo. Añade leche en polvo o azúcar.")
    diag(PRIORITY_CRITICAL, 'pac_alto', pac_v > pac_hi,
         f"PAC {pac_v:.0f} → excesivo (máx {pac_hi})",
         "Punto de congelación demasiado bajo → helado muy blando.")
    diag(PRIORITY_IMPORTANT, 'fat_alto', fat_v > fat_hi,
         f"Grasa {fat_v:.1f}% → alta (máx {fat_hi}%)",
         "Exceso de grasa → sensación untuosa. Reduce crema o mantequilla.")
    diag(PRIORITY_IMPORTANT, 'msnf_alto_creami', is_creami and msnf_v > msnf_crit,
         f"MSNF {msnf_v:.1f}% → riesgo arenado Creami (umbral {msnf_crit}%)",
         "Reduce leche en polvo descremada.")
    diag(PRIORITY_ADJUSTABLE, 'pod_bajo', 0 < pod_v < pod_lo,
         f"POD {pod_v:.0f} → dulzor bajo (mín {pod_lo})",
         "Añade sacarosa, fructosa o azúcar invertido.")
    diag(PRIORITY_ADJUSTABLE, 'pod_alto', pod_v > pod_hi,
         f"POD {pod_v:.0f} → dulzor excesivo (máx {pod_hi})",
         "Reduce azúcar o sustituye por trehalosa (POD=0.45).")
    diag(PRIORITY_ADJUSTABLE, 'azucar_bajo', 0 < sug_v < sug_lo,
         f"Azúcares {sug_v:.1f}% → bajos (mín {sug_lo}%)",
         "Poca estructura de azúcar → cristales grandes. Añade dextrosa o sacarosa.")

    # ── Alcohol ───────────────────────────────────────────────────────────────
    alcohol_detected = None
    if alcohol_lines:
        diag(PRIORITY_CRITICAL, 'alcohol_exceso', ethanol_pct_mix > 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → NO CONGELA",
             f"Ingredientes: {nombres_alcohol}. Supera 4% → punto de congelación "
             "bajo −18°C. Reduce el licor o usa extracto sin alcohol.")
        diag(PRIORITY_IMPORTANT, 'alcohol_advertencia', 2.5 < ethanol_pct_mix <= 4.0,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol → textura blanda",
             f"Ingredientes: {nombres_alcohol}. Compensa con +20-30g dextrosa.")
        diag(PRIORITY_ADJUSTABLE, 'alcohol_info', ethanol_pct_mix <= 2.5,
             f"Alcohol {ethanol_pct_mix:.1f}% etanol — dosis correcta",
             f"Ingredientes: {nombres_alcohol}. Dentro del rango seguro.")
        alcohol_detected = {
            'lines':           alcohol_lines,
            'ethanol_total_g': round(ethanol_total_g, 1),
            'ethanol_pct':     round(ethanol_pct_mix,  2),
        }

    return {
        **crio,
        'targets':        targets,
        'st_water_ratio': round(stw_v, 3) if stw_v is not None else None,
        'alcohol_detected': alcohol_detected,
        'diagnostics':    diags,
    }


def _diags_crio_creami(diag, zona: str, dt: float):
    """Diagnósticos crioscópicos específicos para Creami (FIX-6)."""
    diag(PRIORITY_CRITICAL, 'crio_muy_bajo', zona == 'muy_bajo',
         f"ΔT {dt:.2f}°C — base acuosa, textura icy inevitable",
         "Con ΔT > −1.0°C hay pocos solutos para frenar el crecimiento de cristales. "
         "① Añade dextrosa 20–40g. ② Más leche en polvo. ③ Más sacarosa/fructosa.")
    diag(PRIORITY_IMPORTANT, 'crio_bajo', zona == 'bajo',
         f"ΔT {dt:.2f}°C — algo bajo, granuloso probable",
         "Añade 10–20g de dextrosa o ajusta la relación agua/sólidos.")
    diag(PRIORITY_ADJUSTABLE, 'crio_alto', zona == 'alto',
         f"ΔT {dt:.2f}°C — exceso leve de PAC",
         "Puede quedar blando. Reduce dextrosa/fructosa o aumenta trehalosa (PAC=0.70).")
    diag(PRIORITY_CRITICAL, 'crio_muy_alto', zona == 'muy_alto',
         f"ΔT {dt:.2f}°C — exceso severo de PAC",
         "El helado puede quedar parcialmente blando a −18°C. "
         "Causa más común: alcohol >4%. Revisa licores o exceso de poliol.")


def _diags_crio_mantecadora(diag, zona: str, dt: float):
    """Diagnósticos crioscópicos para mantecadora (FIX-6)."""
    diag(PRIORITY_CRITICAL, 'crio_muy_bajo', zona == 'muy_bajo',
         f"ΔT {dt:.2f}°C — base acuosa, cristales grandes en el mantecado",
         "Añade dextrosa 20–40g o reduce agua libre.")
    diag(PRIORITY_IMPORTANT, 'crio_bajo', zona == 'bajo',
         f"ΔT {dt:.2f}°C — algo bajo para mantecadora",
         "Puede quedar granuloso. Añade 10–20g de dextrosa.")
    diag(PRIORITY_ADJUSTABLE, 'crio_alto', zona == 'alto',
         f"ΔT {dt:.2f}°C — exceso leve de PAC",
         "Puede quedar blando al servir. Reduce dextrosa/fructosa.")
    diag(PRIORITY_CRITICAL, 'crio_muy_alto', zona == 'muy_alto',
         f"ΔT {dt:.2f}°C — exceso severo de PAC o alcohol",
         "Helado muy blando. Revisa licores o exceso de poliol.")


# ─────────────────────────────────────────────────────────────────────────────
# RECOMENDACIONES DE ESTABILIZANTES
# ─────────────────────────────────────────────────────────────────────────────

def recommend_stabilizers(totals: dict, pct: dict, product_type: str,
                           machine: str, ingredient_names: list = None,
                           config: dict = None) -> list:
    """
    Genera recomendaciones de estabilizantes basadas en deficiencias de la mezcla.
    Las recomendaciones son genéricas (familia, no marca específica).
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return []

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    targets   = get_targets(product_type, machine)
    if config:
        for key in ('st', 'fat', 'msnf', 'sugars', 'pod', 'pac', 'st_water'):
            if key in config:
                targets[key] = config[key]

    st_pct    = pct.get('st_pct',    0)
    water_pct = pct.get('water_pct', 0)
    fat_pct   = pct.get('fat_pct',   0)

    names = [n.lower() for n in (ingredient_names or [])]
    has = lambda *keys: any(k in n for n in names for k in keys)

    has_cmc       = has('cmc', 'carboximetil')
    has_xantana   = has('xantana')
    has_guar      = has('guar')
    has_pectina   = has('pectina')
    has_lecitina  = has('lecitina')
    has_trehalosa = has('trehalosa')
    has_natulac   = has('natulac', 'carrageen')
    has_fruta_ac  = has('limón', 'lemon', 'maracuyá', 'passion', 'piña',
                        'pineapple', 'tamarindo', 'fruta de la pasión')
    has_espesante = has_cmc or has_xantana or has_guar or has_pectina

    recs = []

    if water_pct > 62 and not has_espesante:
        recs.append(_rec_agua_alta(m, is_sorbet))

    if st_pct < targets['st'][0] and not is_sorbet:
        recs.append(_rec_st_bajo(m, targets))

    if has_natulac and has_fruta_ac and not has_xantana:
        recs.append(_rec_carragenina_acida(m))

    if not has_lecitina and fat_pct > 4 and not is_sorbet:
        recs.append(_rec_emulsionante(m, fat_pct))

    if not has_trehalosa and is_creami:
        recs.append(_rec_crioprotector(m))

    if st_pct >= 38 and water_pct <= 58 and not is_sorbet and not recs:
        recs.append(_rec_ok(st_pct, water_pct))

    return recs


def _rec_agua_alta(m: float, is_sorbet: bool) -> dict:
    if is_sorbet:
        return {
            'stabilizer':    'Goma Guar o Tara',
            'dose_g_per_kg': '1.0–1.5 g/kg',
            'dose_g_recipe': f'{1.2 * m / 1000:.1f} g',
            'priority':      'recomendado',
            'reason':        'Sorbete muy acuoso → cristales gruesos sin estabilizante.',
            'warning':       None,
            'alternativas':  [
                '① Goma Xantana: 0.3–0.5 g/kg — estable en pH ácido.',
                '② Pectina LM: 1–2 g/kg — sinergia con calcio de la fruta.',
                '③ Goma Tara + Xantana (4:1): excelente para sorbetes ácidos.',
            ],
        }
    return {
        'stabilizer':    'CMC o Goma Xantana',
        'dose_g_per_kg': '0.8–1.2 g/kg',
        'dose_g_recipe': f'{1.0 * m / 1000:.1f} g',
        'priority':      'recomendado',
        'reason':        'Agua libre alta → recristalización rápida sin estabilizante.',
        'warning':       'No combinar CMC + Natulac/carragenina + fruta ácida → triple gelificación.',
        'alternativas':  [
            '① CMC: 0.8–1.2 g/kg — se hidrata en frío, sin pasteurización.',
            '② Goma Xantana: 0.5–0.8 g/kg — estable pH 2–8.',
            '③ Goma Guar + LBG (1:1): 0.6+0.6 g/kg — sinergia cremosa, requiere 85°C.',
        ],
    }


def _rec_st_bajo(m: float, targets: dict) -> dict:
    return {
        'stabilizer':    'Fibra soluble o Inulina',
        'dose_g_per_kg': '20–40 g/kg',
        'dose_g_recipe': f'{30 * m / 1000:.1f} g',
        'priority':      'opcional',
        'reason':        f'ST bajo el mínimo ({targets["st"][0]}%). La fibra añade sólidos sin dulzor.',
        'warning':       'Inulina >5% puede dar regusto amargo. Preferir fibra cítrica.',
        'alternativas':  [
            '① Fibra cítrica: 2–5 g/kg — clean label, liga agua sin gomosidad.',
            '② Leche en polvo descremada: 20–40 g/kg — añade MSNF y proteínas.',
            '③ Inulina: 20–30 g/kg — prebiótica, bajo IG. Máx 5% para evitar amargor.',
        ],
    }


def _rec_carragenina_acida(m: float) -> dict:
    return {
        'stabilizer':    'Goma estable en ácido',
        'dose_g_per_kg': '0.5–0.8 g/kg',
        'dose_g_recipe': f'{0.6 * m / 1000:.1f} g',
        'priority':      'recomendado',
        'reason':        'Carragenina se degrada con pH<4.5. Fruta ácida detectada → sinéresis.',
        'warning':       None,
        'alternativas':  [
            '① Goma Xantana: 0.5–0.8 g/kg — muy estable en pH 2–8.',
            '② Pectina LM: 1–2 g/kg — estable en frutas ácidas con calcio.',
            '③ Goma Guar + Xantana (2:1): buen cuerpo en pH bajo.',
        ],
    }


def _rec_emulsionante(m: float, fat_pct: float) -> dict:
    return {
        'stabilizer':    'Emulsionante',
        'dose_g_per_kg': '2–3 g/kg',
        'dose_g_recipe': f'{2.5 * m / 1000:.1f} g',
        'priority':      'recomendado',
        'reason':        f'Grasa {fat_pct:.1f}% sin emulsionante → separación y textura gruesa.',
        'warning':       'Premezclar en seco con polvos lácteos antes de añadir líquidos.',
        'alternativas':  [
            '① Lecitina de girasol en polvo: 2–3 g/kg — limpia, sin alérgeno soja.',
            '② Lecitina de soja: 2–3 g/kg — más económica.',
            '③ Yema de huevo: 30–50 g/kg — emulsificación natural, requiere 72°C.',
            '④ Mono y diglicéridos: 1.5–2.5 g/kg — sinergia con lecitina.',
        ],
    }


def _rec_crioprotector(m: float) -> dict:
    return {
        'stabilizer':    'Crioprotector (azúcar)',
        'dose_g_per_kg': '12–18 g/kg',
        'dose_g_recipe': f'{15 * m / 1000:.1f} g',
        'priority':      'recomendado',
        'reason':        'Protege la microestructura en el re-congelado post-proceso.',
        'warning':       None,
        'alternativas':  [
            '① Trehalosa: 12–18 g/kg — crioprotector por excelencia, POD=0.45.',
            '② Dextrosa monohidrato: 20–40 g/kg — PAC alto + crioprotección.',
            '③ Eritritol (máx 1.5% mezcla): crioprotección sin calorías.',
        ],
    }


def _rec_ok(st_pct: float, water_pct: float) -> dict:
    return {
        'stabilizer':    '✅ Sin espesante adicional necesario',
        'dose_g_per_kg': '—',
        'dose_g_recipe': '—',
        'priority':      'opcional',
        'reason':        f'ST {st_pct:.1f}% y agua libre {water_pct:.1f}% — sólidos suficientes.',
        'warning':       'Añadir espesante con estos sólidos → riesgo de textura gomosa.',
        'alternativas':  [],
    }
