"""
Constantes compartidas entre calculator.py, database.py y app.py.
Centraliza los strings de tipo de producto y máquina para evitar
que un cambio de nombre requiera editar múltiples archivos.
"""

# ── Tipos de producto ─────────────────────────────────────────────────────────
PRODUCT_HELADO    = "Helado/Gelato"
PRODUCT_SORBETE   = "Sorbete"
PRODUCT_GRANITA   = "Granita"
PRODUCT_VEGANO    = "Gelato Vegano"
PRODUCT_FROZEN    = "Frozen Yogurt"
PRODUCT_LIGERO    = "Helado Ligero"

PRODUCT_TYPES = [
    PRODUCT_HELADO,
    PRODUCT_SORBETE,
    PRODUCT_GRANITA,
    PRODUCT_VEGANO,
    PRODUCT_FROZEN,
    PRODUCT_LIGERO,
]

# ── Máquinas ──────────────────────────────────────────────────────────────────
MACHINE_CREAMI_DELUXE   = "Ninja Creami Deluxe"
MACHINE_CREAMI_STANDARD = "Ninja Creami Standard"
MACHINE_PACOJET         = "Pacojet"
MACHINE_MANTECADORA     = "Mantecadora Tradicional"

MACHINES = [
    MACHINE_CREAMI_DELUXE,
    MACHINE_CREAMI_STANDARD,
    MACHINE_PACOJET,
    MACHINE_MANTECADORA,
]

# ── Prioridades de diagnóstico ────────────────────────────────────────────────
PRIORITY_CRITICAL   = "critical"
PRIORITY_IMPORTANT  = "important"
PRIORITY_ADJUSTABLE = "adjustable"

# ── Diagnósticos excluidos del ticket de producción ───────────────────────────
DIAGS_EXCLUIR_TICKET = {"creami_overrun_hint"}

# ── Categorías de ingredientes ────────────────────────────────────────────────
CATEGORY_ALCOHOL = "Alcohol"

# Fracción másica de etanol puro según graduación típica de cada licor.
# Clave: substring en minúsculas del nombre del ingrediente.
# Valor: fracción de etanol puro (0-1) respecto a la masa del ingrediente.
# Fuente: densidad etanol 0.789 g/ml; % vol × densidad / 100.
ALCOHOL_ETHANOL_FRACTION = {
    "ron":        0.316,   # 40% vol → 40 × 0.789 / 100
    "vodka":      0.316,
    "whisky":     0.316,
    "whiskey":    0.316,
    "tequila":    0.316,
    "ginebra":    0.316,
    "gin":        0.316,
    "amaretto":   0.221,   # 28% vol
    "limoncello": 0.237,   # 30% vol
    "baileys":    0.142,   # 18% vol
    "kahlúa":     0.197,   # 25% vol
    "kahlua":     0.197,
    "cointreau":  0.316,   # 40% vol
    "grand marnier": 0.316,
    "kirsch":     0.394,   # 50% vol
    "sambuca":    0.316,
    "frangelico": 0.237,
    "malibu":     0.158,   # 20% vol
    "champagne":  0.094,   # 12% vol
    "vino":       0.094,
    "beer":       0.039,
    "cerveza":    0.039,
}

# ── Perfiles de fuentes proteicas ─────────────────────────────────────────────
# Cada entrada describe una fuente proteica identificable por substring del nombre.
#
# Campos:
#   protein_fraction  — fracción de proteína sobre masa total del ingrediente (protein_in_total=True)
#                       o sobre MSNF del ingrediente (protein_in_total=False)
#   protein_in_total  — True: fracción sobre masa; False: fracción sobre MSNF
#   tipo              — 'caseína' | 'suero' | 'vegetal' | 'huevo' | 'lácteo_mixto'
#   solubilidad       — 'micelar' | 'soluble' | 'coloidal'
#   t_desnaturaliz_c  — temperatura de desnaturalización (°C)
#   capacidad_espuma  — 1-5 (5=máxima aportación al overrun)
#   capacidad_gel     — 1-5 (5=máxima aportación al cuerpo en congelación)
#   nota              — comportamiento relevante en formulación de helado
#
# Fuentes: Fox & McSweeney "Advanced Dairy Chemistry Vol.1" (2003);
#          Goff & Hartel "Ice Cream" 7th ed. (2013);
#          Damodaran "Food Proteins and Their Applications" (1997)
PROTEIN_PROFILES = {
    # ── Lácteos base ──────────────────────────────────────────────────────────
    "leche en polvo descremada": {
        "protein_fraction": 0.36,   # ~34-36% proteína sobre masa total
        "protein_in_total": True,
        "tipo":             "lácteo_mixto",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 3,
        "capacidad_gel":    3,
        "nota":             "Mezcla 80% caseína / 20% suero. "
                            "Riesgo de arenado si MSNF supera umbral crítico.",
    },
    "leche en polvo entera": {
        "protein_fraction": 0.26,
        "protein_in_total": True,
        "tipo":             "lácteo_mixto",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 2,
        "capacidad_gel":    2,
        "nota":             "Grasa alta reduce funcionalidad proteica relativa.",
    },
    "leche entera": {
        "protein_fraction": 0.36,   # ~36% del MSNF es proteína en leche
        "protein_in_total": False,  # fracción sobre MSNF
        "tipo":             "lácteo_mixto",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 2,
        "capacidad_gel":    2,
        "nota":             "Proteína diluida. Contribuye estructura base.",
    },
    "leche descremada": {
        "protein_fraction": 0.36,
        "protein_in_total": False,
        "tipo":             "lácteo_mixto",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 3,
        "capacidad_gel":    2,
        "nota":             "Sin grasa, mejor funcionalidad espumante relativa.",
    },
    "leche concentrada": {
        "protein_fraction": 0.36,
        "protein_in_total": False,
        "tipo":             "lácteo_mixto",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 3,
        "capacidad_gel":    3,
        "nota":             "MSNF concentrado ~2.5×. Buena fuente de caseína micelar.",
    },
    # ── Caseína micelar ────────────────────────────────────────────────────────
    "caseína micelar": {
        "protein_fraction": 0.88,
        "protein_in_total": True,
        "tipo":             "caseína",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 140,    # muy termoestable
        "capacidad_espuma": 2,
        "capacidad_gel":    5,
        "nota":             "Forma micelas que atrapan agua → cuerpo denso sin grasa. "
                            "No desnaturaliza en pasteurización normal. "
                            "Ideal para helado light con textura cremosa.",
    },
    "caseina micelar": {
        "protein_fraction": 0.88,
        "protein_in_total": True,
        "tipo":             "caseína",
        "solubilidad":      "micelar",
        "t_desnaturaliz_c": 140,
        "capacidad_espuma": 2,
        "capacidad_gel":    5,
        "nota":             "Ver caseína micelar.",
    },
    # ── Proteína de suero ─────────────────────────────────────────────────────
    "suero de leche": {
        "protein_fraction": 0.12,
        "protein_in_total": True,
        "tipo":             "suero",
        "solubilidad":      "soluble",
        "t_desnaturaliz_c": 65,
        "capacidad_espuma": 5,
        "capacidad_gel":    3,
        "nota":             "β-lactoglobulina espuma muy bien. "
                            "No pasteurizar sobre 65°C.",
    },
    "wpc": {
        "protein_fraction": 0.80,
        "protein_in_total": True,
        "tipo":             "suero",
        "solubilidad":      "soluble",
        "t_desnaturaliz_c": 65,
        "capacidad_espuma": 5,
        "capacidad_gel":    4,
        "nota":             "WPC 80%: balance proteína/lactosa. "
                            "Ideal para helado high-protein sin textura calcárea.",
    },
    "wpi": {
        "protein_fraction": 0.90,
        "protein_in_total": True,
        "tipo":             "suero",
        "solubilidad":      "soluble",
        "t_desnaturaliz_c": 65,
        "capacidad_espuma": 5,
        "capacidad_gel":    4,
        "nota":             "WPI 90%: mínima lactosa y grasa. "
                            "Máxima densidad proteica. Gelifica fuerte en caliente.",
    },
    "proteína de suero": {
        "protein_fraction": 0.80,
        "protein_in_total": True,
        "tipo":             "suero",
        "solubilidad":      "soluble",
        "t_desnaturaliz_c": 65,
        "capacidad_espuma": 5,
        "capacidad_gel":    4,
        "nota":             "Excelente para overrun en helado light.",
    },
    # ── Vegetal ───────────────────────────────────────────────────────────────
    "proteína de guisante": {
        "protein_fraction": 0.80,
        "protein_in_total": True,
        "tipo":             "vegetal",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 85,
        "capacidad_espuma": 3,
        "capacidad_gel":    4,
        "nota":             "PDCAAS 0.65. Sabor terroso — enmascarar con vainilla o cacao. "
                            "Sin lactosa ni gluten.",
    },
    "proteína de soja": {
        "protein_fraction": 0.90,
        "protein_in_total": True,
        "tipo":             "vegetal",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 80,
        "capacidad_espuma": 4,
        "capacidad_gel":    4,
        "nota":             "PDCAAS 0.91. Mejor perfil de aminoácidos que guisante. "
                            "Posible alérgeno.",
    },
    "proteína de arroz": {
        "protein_fraction": 0.80,
        "protein_in_total": True,
        "tipo":             "vegetal",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 90,
        "capacidad_espuma": 2,
        "capacidad_gel":    3,
        "nota":             "PDCAAS 0.47. Neutro en sabor. "
                            "Combinar con guisante para perfil de aminoácidos completo.",
    },
    # ── Huevo ─────────────────────────────────────────────────────────────────
    "yema de huevo": {
        "protein_fraction": 0.16,
        "protein_in_total": True,
        "tipo":             "huevo",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 70,
        "capacidad_espuma": 2,
        "capacidad_gel":    5,
        "nota":             "Principalmente emulsionante (lecitina). "
                            "Gelifica fuerte sobre 70°C → base crème anglaise.",
    },
    "clara de huevo": {
        "protein_fraction": 0.11,
        "protein_in_total": True,
        "tipo":             "huevo",
        "solubilidad":      "soluble",
        "t_desnaturaliz_c": 62,
        "capacidad_espuma": 5,
        "capacidad_gel":    3,
        "nota":             "Ovalbúmina: espuma excepcional. "
                            "Desnaturaliza a 62°C → pasteurizar con mucho cuidado.",
    },
    # ── Derivados ─────────────────────────────────────────────────────────────
    "queso crema": {
        "protein_fraction": 0.06,
        "protein_in_total": True,
        "tipo":             "caseína",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 80,
        "capacidad_espuma": 1,
        "capacidad_gel":    4,
        "nota":             "Alta grasa domina. Proteína marginal. Aporta acidez pH ~4.8.",
    },
    "mascarpone": {
        "protein_fraction": 0.04,
        "protein_in_total": True,
        "tipo":             "caseína",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 80,
        "capacidad_espuma": 1,
        "capacidad_gel":    3,
        "nota":             "Muy graso — proteína marginal. No usar como fuente proteica.",
    },
    "yogur": {
        "protein_fraction": 0.36,
        "protein_in_total": False,
        "tipo":             "lácteo_mixto",
        "solubilidad":      "coloidal",
        "t_desnaturaliz_c": 72,
        "capacidad_espuma": 2,
        "capacidad_gel":    3,
        "nota":             "Proteína parcialmente desnaturalizada por acidez. "
                            "Aporta textura cremosa en frozen yogurt.",
    },
}

# Claims nutricionales EU 1924/2006 (referencia)
PROTEIN_CLAIM_THRESHOLDS = {
    "fuente_proteina": 5.0,    # ≥ 5 g/100g producto final (≥10% VRN)
    "alto_proteina":   10.0,   # ≥ 10 g/100g producto final (≥20% VRN)
}

# Rangos funcionales de proteína para helado (g proteína / 100g mezcla)
PROTEIN_FUNCTIONAL_TARGETS = {
    "minimo_estructura":  2.5,   # mínimo para overrun >30% sin grasa compensatoria
    "optimo_light":       4.0,   # óptimo para helado light
    "high_protein":       8.0,   # umbral para claim "alto contenido en proteínas"
    "maximo_recomendado": 12.0,  # sobre este: riesgo de textura calcárea/granulosa
}
