"""
calc_nutrition.py — Nutrición, edulcorantes y overrun.

Responsabilidad única: todo lo relacionado con valor nutricional,
perfiles de sabor de edulcorantes y rendimiento por máquina.

Funciones públicas:
    calc_calories(totals, lines)      → kcal, clasificación calórica/proteica
    analyze_sweeteners(lines)         → desglose POD/PAC por edulcorante
    analyze_protein(lines, totals, pct, product_type) → análisis proteico
    overrun_calc(base_g, or_pct, target_l, machine)   → rendimiento por máquina
    _detect_alcohol_lines(lines)      → detección de etanol (uso interno)
"""

import math

from constants import (
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO, PRODUCT_LIGERO,
    ALCOHOL_ETHANOL_FRACTION,
    PROTEIN_PROFILES, PROTEIN_CLAIM_THRESHOLDS, PROTEIN_FUNCTIONAL_TARGETS,
    CALORIE_CLASSIFICATION, PROTEIN_CLASSIFICATION,
    CREAMI_OVERRUN_PCT,
)

# ── Capacidades físicas ───────────────────────────────────────────────────────
CREAMI_DELUXE_CAPACITY_G   = 640
CREAMI_STANDARD_CAPACITY_G = 430

# ── Factores calóricos de Atwater ─────────────────────────────────────────────
_KCAL_FAT     = 9.0   # grasa
_KCAL_PROTEIN = 3.5   # proteína láctea (FAO/WHO 2003 — no el 4.0 genérico)
_KCAL_SUGAR   = 4.0   # azúcares y almidones disponibles
_KCAL_OTHER   = 2.5   # fibra, cacao, almidón resistente
_KCAL_ALCOHOL = 7.0   # etanol

# ── Perfiles organolépticos de edulcorantes ───────────────────────────────────
# Tupla: (POD, PAC, kcal/g, descripción_sabor, perfil_dulzor)
# PAC alulosa = 1.80 (FIX-1: PM 180 g/mol → teórico 1.90, empírico 1.80)
# PAC eritritol = 1.30 (empírico conservador validado por catas — recristaliza)
SWEETENER_PROFILES = {
    'sacarosa':         (1.00, 1.00, 4.0, 'Referencia — dulzor limpio y redondo',       'inmediato'),
    'dextrosa':         (0.75, 1.90, 4.0, 'Frescor suave positivo en boca fría',        'inmediato'),
    'fructosa':         (1.20, 1.90, 4.0, 'Muy dulce en frío, puede ser empalagoso',    'inmediato'),
    'trehalosa':        (0.45, 0.70, 4.0, 'Muy suave, casi neutro, crioprotector',      'lento'),
    'alulosa':          (0.70, 1.80, 0.4, 'El más parecido al azúcar, sin retrogusto',  'inmediato'),
    'eritritol':        (0.65, 1.30, 0.2, 'Efecto frescor/mentolado — limitar a 1.5%', 'inmediato'),
    'maltitol':         (0.75, 0.90, 2.4, 'Similar a sacarosa, posibles molestias GI',  'inmediato'),
    'isomalt':          (0.45, 0.50, 2.0, 'Muy suave, ideal para inclusiones duras',    'lento'),
    'glucosa':          (0.75, 1.90, 4.0, 'Frescor suave, mejora textura extensible',   'inmediato'),
    'azucar invertido': (1.30, 1.90, 4.0, 'Dulzor intenso, higroscópico, suaviza',      'inmediato'),
    'stevia':           (0.0,  0.0,  0.0, 'Sin PAC/POD propio — corrector dulzor',      'tardío'),
    'splenda':          (0.0,  0.0,  0.0, 'Mezcla eritritol+stevia — sin POD/PAC base', 'tardío'),
}

# Fracción proteica del MSNF (Goff & Hartel 2013)
_PROTEIN_FRAC_MSNF = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE ALCOHOL (privada, usada por calc_calories y diagnostics)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_alcohol_lines(lines_with_ings: list) -> list:
    """Devuelve líneas con ingredientes alcohólicos y su contenido de etanol."""
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
            fraction = 0.316    # fallback genérico 40% vol
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
# CALORÍAS
# ─────────────────────────────────────────────────────────────────────────────

def calc_calories(totals: dict, lines_with_ings: list = None) -> dict:
    """
    Estima calorías totales y por 100g usando factores de Atwater.

    Los ingredientes con zero_calorie=1 en BD (eritritol, alulosa, stevia)
    tienen su fracción de azúcares descontada. Sin ese flag, la alulosa
    se calcularía como 4 kcal/g en lugar de 0.4 kcal/g.
    """
    m = totals.get('grams', 0)
    if m <= 0:
        return {
            'kcal_total': 0, 'kcal_per_100g': 0,
            'kcal_per_pote_deluxe': 0,
            'clasificacion_calorica': None, 'clasificacion_proteica': None,
        }

    protein_g = totals.get('msnf', 0) * _PROTEIN_FRAC_MSNF
    kcal = (
        totals.get('fat',      0) * _KCAL_FAT     +
        protein_g                 * _KCAL_PROTEIN  +
        totals.get('sugars',   0) * _KCAL_SUGAR   +
        totals.get('other_st', 0) * _KCAL_OTHER
    )

    if lines_with_ings:
        for ing, grams, _ in lines_with_ings:
            if ing and grams and ing.get('zero_calorie', 0):
                g = float(grams)
                kcal -= g * float(ing.get('sugars', 0)) / 100 * _KCAL_SUGAR
        for a in _detect_alcohol_lines(lines_with_ings):
            kcal += a['ethanol_g'] * _KCAL_ALCOHOL

    kcal          = max(0, kcal)
    kcal_per_100g = kcal / m * 100
    kcal_per_pote = kcal_per_100g * CREAMI_DELUXE_CAPACITY_G / 100

    cal_class  = _clasificar_calorico(kcal_per_100g)
    prot_class = _clasificar_proteico(protein_g / m * 100)

    return {
        'kcal_total':             round(kcal,          0),
        'kcal_per_100g':          round(kcal_per_100g, 0),
        'kcal_per_pote_deluxe':   round(kcal_per_pote, 0),
        'clasificacion_calorica': cal_class,
        'clasificacion_proteica': prot_class,
    }


def _clasificar_calorico(kcal_per_100g: float) -> dict | None:
    for key, (max_k, etiqueta, emoji, desc) in CALORIE_CLASSIFICATION.items():
        if kcal_per_100g <= max_k:
            return {'key': key, 'etiqueta': etiqueta, 'emoji': emoji,
                    'desc': desc, 'valor': round(kcal_per_100g, 0)}
    _, etiqueta, emoji, desc = list(CALORIE_CLASSIFICATION.values())[-1]
    return {'key': 'muy_denso', 'etiqueta': etiqueta, 'emoji': emoji,
            'desc': desc, 'valor': round(kcal_per_100g, 0)}


def _clasificar_proteico(protein_per_100g: float) -> dict | None:
    for key, (min_p, max_p, etiqueta, emoji, desc) in PROTEIN_CLASSIFICATION.items():
        if min_p <= protein_per_100g < max_p:
            return {'key': key, 'etiqueta': etiqueta, 'emoji': emoji,
                    'desc': desc, 'valor': round(protein_per_100g, 1)}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# EDULCORANTES
# ─────────────────────────────────────────────────────────────────────────────

def analyze_sweeteners(lines_with_ings: list) -> list:
    """Desglosa la contribución de cada edulcorante al POD, PAC y calorías."""
    rows        = []
    total_pod   = 0.0
    total_pac   = 0.0
    total_grams = sum(float(g) for _, g, _ in lines_with_ings if g) or 1

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g           = float(grams)
        pod_contrib = g * float(ing.get('pod', 0))
        pac_contrib = g * float(ing.get('pac', 0))

        if pod_contrib <= 0.5 and pac_contrib <= 0.5 and float(ing.get('sugars', 0)) <= 5:
            continue

        total_pod += pod_contrib
        total_pac += pac_contrib

        name_lower = ing['name'].lower()
        profile    = next((p for k, p in SWEETENER_PROFILES.items() if k in name_lower), None)
        pct_in_mix = g / total_grams * 100
        warning    = _sweetener_warning(name_lower, g, pct_in_mix)

        rows.append({
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

    for row in rows:
        row['pct_pod'] = round(row['pod_contrib'] / total_pod * 100, 1) if total_pod else 0
        row['pct_pac'] = round(row['pac_contrib'] / total_pac * 100, 1) if total_pac else 0

    return rows


def _sweetener_warning(name: str, grams: float, pct_in_mix: float) -> str | None:
    if 'eritritol' in name and pct_in_mix > 1.5:
        return f"⚠️ Eritritol al {pct_in_mix:.1f}% → efecto mentolado probable. Máximo 1.5%"
    if 'stevia' in name and grams > 0.5:
        return f"⚠️ Stevia {grams:.1f} g → retrogusto posible. Máximo 0.3 g/kg"
    if 'fructosa' in name and pct_in_mix > 8:
        return f"⚠️ Fructosa alta ({pct_in_mix:.1f}%) → puede resultar empalagosa"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PROTEÍNAS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_protein(lines_with_ings: list, totals: dict, pct: dict,
                    product_type: str = 'Helado/Gelato') -> dict:
    """Analiza fuentes proteicas, scores funcionales y claims nutricionales."""
    m = totals.get('grams', 0)
    if m <= 0:
        return {}

    is_sorbet = product_type in (PRODUCT_SORBETE, PRODUCT_GRANITA)
    fuentes, advertencias = [], []
    protein_total = espuma_sum = gel_sum = peso_sum = 0.0
    tipo_pesos: dict = {}

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g        = float(grams)
        name_low = ing.get('name', '').lower()
        perfil, matched_key = _match_protein_profile(name_low)
        prot_g = _calc_protein_g(g, ing, perfil)

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
            'nombre': ing['name'], 'gramos': g,
            'proteina_g': round(prot_g, 2), 'tipo': tipo,
            'espuma': esp, 'gel': gel,
            't_denat': t_denat if t_denat < 999 else None,
            'nota': perfil.get('nota', '') if perfil else '',
            'perfil_clave': matched_key or '(fallback)',
        })

    protein_pct    = protein_total / m * 100
    tipo_dominante = max(tipo_pesos, key=tipo_pesos.get) if tipo_pesos else 'n/d'
    claim          = _protein_claim(protein_pct)
    recomendaciones = _protein_recommendations(protein_pct, m, is_sorbet)

    return {
        'fuentes':          fuentes,
        'protein_total_g':  round(protein_total, 1),
        'protein_pct':      round(protein_pct,   2),
        'protein_per_100g': round(protein_pct,   1),
        'tipo_dominante':   tipo_dominante,
        'score_espuma':     round(espuma_sum / peso_sum, 1) if peso_sum else 0,
        'score_gel':        round(gel_sum    / peso_sum, 1) if peso_sum else 0,
        'claim':            claim,
        'advertencias':     advertencias,
        'recomendaciones':  recomendaciones,
    }


def _match_protein_profile(name_low: str):
    for key in sorted(PROTEIN_PROFILES.keys(), key=len, reverse=True):
        if key in name_low:
            return PROTEIN_PROFILES[key], key
    return None, ''


def _calc_protein_g(g: float, ing: dict, perfil: dict | None) -> float:
    if perfil:
        if perfil['protein_in_total']:
            return g * perfil['protein_fraction']
        msnf_g = g * float(ing.get('msnf', 0)) / 100
        return msnf_g * perfil['protein_fraction']
    msnf_g = g * float(ing.get('msnf', 0)) / 100
    return msnf_g * 0.36   # fallback 36% MSNF


def _protein_claim(protein_per_100g: float) -> str | None:
    thr = PROTEIN_CLAIM_THRESHOLDS
    if protein_per_100g >= thr['alto_proteina']:
        return 'alto_proteina'
    if protein_per_100g >= thr['fuente_proteina']:
        return 'fuente_proteina'
    return None


def _protein_recommendations(protein_pct: float, m: float, is_sorbet: bool) -> list:
    tgt = PROTEIN_FUNCTIONAL_TARGETS
    if 0 < protein_pct < tgt['minimo_estructura'] and not is_sorbet:
        deficit = tgt['minimo_estructura'] - protein_pct
        return [{'priority': 'important',
                 'titulo': f"Proteína {protein_pct:.1f}% — bajo mínimo estructural",
                 'texto': (f"Necesitas ~{deficit * m / 100:.0f} g más de proteína. "
                           "Opciones: WPC/WPI, leche en polvo descremada, yema de huevo.")}]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# OVERRUN
# ─────────────────────────────────────────────────────────────────────────────

def overrun_calc(base_grams: float, overrun_pct: float,
                 target_liters: float, machine: str = 'Ninja Creami Deluxe') -> dict:
    """
    Calcula rendimiento por máquina.

    Ninja Creami: overrun fijo mecánico (~40-60%). No es configurable.
    Mantecadora:  overrun configurable por el formulador.

    La densidad del helado con overrun es 1/(1+or_factor) g/mL:
      - 0% overrun  → 1.00 g/mL
      - 50% overrun → 0.67 g/mL  (Creami Deluxe)
      - 100%        → 0.50 g/mL  (industrial)
    """
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    return (_overrun_creami(base_grams, machine) if is_creami
            else _overrun_mantecadora(base_grams, overrun_pct, target_liters))


def _overrun_creami(base_grams: float, machine: str) -> dict:
    overrun_fijo = CREAMI_OVERRUN_PCT.get(machine, 50)
    or_factor    = overrun_fijo / 100
    cap          = (CREAMI_DELUXE_CAPACITY_G if machine == MACHINE_CREAMI_DELUXE
                    else CREAMI_STANDARD_CAPACITY_G)

    potes_exacto  = base_grams / cap if cap else 0
    potes_enteros = int(potes_exacto)
    resto_g       = (potes_exacto - potes_enteros) * cap
    masa_final_g  = base_grams * (1 + or_factor)
    densidad      = 1.0 / (1 + or_factor)
    volumen_ml    = masa_final_g / densidad

    return {
        'is_creami':             True,
        'overrun_fijo_pct':      overrun_fijo,
        'masa_base_g':           base_grams,
        'masa_final_estimada_g': round(masa_final_g, 0),
        'volumen_estimado_ml':   round(volumen_ml,   0),
        'densidad_helado_g_ml':  round(densidad,     3),
        'potes_base':            round(potes_exacto, 2),
        'potes_completos':       potes_enteros,
        'masa_ultimo_pote_g':    round(resto_g,      0),
        'masa_por_pote_g':       cap,
        'potes_con_overrun':     round(masa_final_g / cap, 2) if cap else 0,
        # campos compatibilidad backward
        'base_needed_g':         base_grams,
        'liters_from_base':      round(volumen_ml / 1000, 2),
        'volume_increase':       overrun_fijo,
        'final_grams_per_liter': round(masa_final_g / (volumen_ml / 1000), 0) if volumen_ml else 0,
    }


def _overrun_mantecadora(base_grams: float, overrun_pct: float,
                          target_liters: float) -> dict:
    or_pct      = overrun_pct / 100
    or_factor   = or_pct
    base_needed = target_liters * 1000 / (1 + or_pct) if (1 + or_pct) else 0
    liters_prod = base_grams / 1000 * (1 + or_pct)
    densidad    = 1.0 / (1 + or_factor) if or_factor else 1.0
    mix_beaker  = base_grams / 2 / (1 + or_pct) if (1 + or_pct) else 0

    return {
        'is_creami':             False,
        'overrun_pct':           overrun_pct,
        'base_needed_g':         round(base_needed,  0),
        'liters_from_base':      round(liters_prod,  2),
        'target_liters':         target_liters,
        'volume_increase':       overrun_pct,
        'final_grams_per_liter': round(base_grams / liters_prod, 0) if liters_prod else 0,
        'densidad_helado_g_ml':  round(densidad,     3),
        'mix_per_beaker':        round(mix_beaker,   1),
        'pacojet_beakers':       math.ceil(liters_prod / 0.5) if liters_prod else 0,
        # no aplica a mantecadora
        'potes_completos':  0, 'masa_ultimo_pote_g': 0,
        'masa_por_pote_g':  0, 'potes_base':         0,
    }
