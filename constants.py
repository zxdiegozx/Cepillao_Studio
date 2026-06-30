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
# NOTA: Pacojet eliminado. Solo Ninja Creami y Mantecadora Tradicional.
MACHINE_CREAMI_DELUXE   = "Ninja Creami Deluxe"
MACHINE_CREAMI_STANDARD = "Ninja Creami Standard"
MACHINE_MANTECADORA     = "Mantecadora Tradicional"

MACHINES = [
    MACHINE_CREAMI_DELUXE,
    MACHINE_CREAMI_STANDARD,
    MACHINE_MANTECADORA,
]

# ── Overrun fijo estimado Ninja Creami (no configurable — es mecánico) ────────
CREAMI_OVERRUN_PCT = {
    MACHINE_CREAMI_DELUXE:   10,   # empírico real: 5-15%
    MACHINE_CREAMI_STANDARD: 10,   # empírico real: 5-15%
}

# ── Prioridades de diagnóstico ────────────────────────────────────────────────
PRIORITY_CRITICAL   = "critical"
PRIORITY_IMPORTANT  = "important"
PRIORITY_ADJUSTABLE = "adjustable"

# ── Diagnósticos excluidos del ticket de producción ───────────────────────────
DIAGS_EXCLUIR_TICKET = {"creami_overrun_hint"}

# ── Categorías de ingredientes (lista maestra — uso obligatorio en BD) ────────
INGREDIENT_CATEGORIES = [
    "Lácteo – Leche líquida",
    "Lácteo – Crema / Nata",
    "Lácteo – Leche en polvo",
    "Lácteo – Queso / Ricotta",
    "Lácteo – Otro",
    "Vegetal – Leche vegetal",
    "Vegetal – Crema vegetal",
    "Vegetal – Pulpa / Puré de fruta",
    "Vegetal – Fruta fresca / congelada",
    "Vegetal – Fruta seca",
    "Vegetal – Otro",
    "Azúcar – Sacarosa",
    "Azúcar – Dextrosa / Glucosa",
    "Azúcar – Fructosa",
    "Azúcar – Trehalosa",
    "Azúcar – Alulosa",
    "Azúcar – Eritritol",
    "Azúcar – Glucosa líquida / DE40",
    "Azúcar – Azúcar invertido",
    "Azúcar – Otro",
    "Edulcorante intensivo",
    "Estabilizante – Goma",
    "Estabilizante – CMC / Celulosa",
    "Estabilizante – Pectina",
    "Estabilizante – Almidón modificado",
    "Estabilizante – Otro",
    "Emulsionante",
    "Proteína – Suero (WPC/WPI)",
    "Proteína – Caseína / MPC",
    "Proteína – Vegetal",
    "Proteína – Huevo",
    "Saborizante – Cacao / Chocolate",
    "Saborizante – Extracto / Esencia",
    "Saborizante – Pasta / Base",
    "Saborizante – Especias",
    "Inclusions – Trozos / Mix-ins",
    "Alcohol",
    "Otro",
]

# ── Categoría de alcohol (para detección de etanol) ───────────────────────────
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
# protein_fraction: fracción de proteína sobre el peso del ingrediente (o del MSNF).
# protein_in_total: True = fracción sobre gramos totales del ing.; False = sobre MSNF.
PROTEIN_PROFILES = {
    # Whey / suero
    "wpc":            {"tipo": "suero",    "protein_fraction": 0.80, "protein_in_total": True,  "capacidad_espuma": 5, "capacidad_gel": 3, "solubilidad": "alta",    "t_desnaturaliz_c": 72,  "nota": "WPC 80% — excelente espumante"},
    "wpi":            {"tipo": "suero",    "protein_fraction": 0.90, "protein_in_total": True,  "capacidad_espuma": 5, "capacidad_gel": 3, "solubilidad": "muy alta","t_desnaturaliz_c": 72,  "nota": "WPI 90% — máxima pureza suero"},
    "proteína de suero": {"tipo": "suero", "protein_fraction": 0.80, "protein_in_total": True,  "capacidad_espuma": 5, "capacidad_gel": 3, "solubilidad": "alta",    "t_desnaturaliz_c": 72,  "nota": "Whey genérico 80%"},
    "whey":           {"tipo": "suero",    "protein_fraction": 0.80, "protein_in_total": True,  "capacidad_espuma": 5, "capacidad_gel": 3, "solubilidad": "alta",    "t_desnaturaliz_c": 72,  "nota": "Whey protein"},
    # Caseína
    "caseína":        {"tipo": "caseína",  "protein_fraction": 0.90, "protein_in_total": True,  "capacidad_espuma": 2, "capacidad_gel": 5, "solubilidad": "micelar", "t_desnaturaliz_c": 140, "nota": "Caseína — alta gelificación, termoestable"},
    "mpc":            {"tipo": "caseína",  "protein_fraction": 0.80, "protein_in_total": True,  "capacidad_espuma": 2, "capacidad_gel": 5, "solubilidad": "micelar", "t_desnaturaliz_c": 140, "nota": "MPC 80%"},
    "leche en polvo descremada": {"tipo": "lácteo_mixto", "protein_fraction": 0.36, "protein_in_total": False, "capacidad_espuma": 3, "capacidad_gel": 3, "solubilidad": "micelar", "t_desnaturaliz_c": 75, "nota": "LPD — 36% del MSNF es proteína mixta"},
    "leche en polvo": {"tipo": "lácteo_mixto", "protein_fraction": 0.36, "protein_in_total": False, "capacidad_espuma": 3, "capacidad_gel": 3, "solubilidad": "micelar", "t_desnaturaliz_c": 75, "nota": "Leche polvo — 36% MSNF"},
    # Vegetal
    "proteína de guisante": {"tipo": "vegetal", "protein_fraction": 0.82, "protein_in_total": True, "capacidad_espuma": 3, "capacidad_gel": 4, "solubilidad": "media", "t_desnaturaliz_c": 90, "nota": "Pea protein — buena gelificación vegana"},
    "proteína de soya":     {"tipo": "vegetal", "protein_fraction": 0.90, "protein_in_total": True, "capacidad_espuma": 4, "capacidad_gel": 4, "solubilidad": "alta",  "t_desnaturaliz_c": 80, "nota": "Soy protein isolate"},
    "proteína de arroz":    {"tipo": "vegetal", "protein_fraction": 0.80, "protein_in_total": True, "capacidad_espuma": 2, "capacidad_gel": 3, "solubilidad": "media", "t_desnaturaliz_c": 85, "nota": "Rice protein — poco espumante"},
    # Huevo
    "clara de huevo":  {"tipo": "huevo", "protein_fraction": 0.11, "protein_in_total": True, "capacidad_espuma": 5, "capacidad_gel": 4, "solubilidad": "alta",   "t_desnaturaliz_c": 60,  "nota": "Albumina — espumante excepcional; desnaturaliza a 60°C"},
    "huevo entero":    {"tipo": "huevo", "protein_fraction": 0.13, "protein_in_total": True, "capacidad_espuma": 4, "capacidad_gel": 4, "solubilidad": "alta",   "t_desnaturaliz_c": 68,  "nota": "Huevo — yema aporta lecitina"},
    "yema de huevo":   {"tipo": "huevo", "protein_fraction": 0.16, "protein_in_total": True, "capacidad_espuma": 3, "capacidad_gel": 5, "solubilidad": "micelar","t_desnaturaliz_c": 68,  "nota": "Yema — alta gelificación, lecitina natural"},
}

# ── Umbrales de claim proteico (g proteína / 100 g producto) ─────────────────
PROTEIN_CLAIM_THRESHOLDS = {
    "fuente_proteina": 5.0,    # ≥5 g/100g → "fuente de proteína"
    "alto_proteina":   10.0,   # ≥10 g/100g → "alto en proteína"
}

# ── Targets funcionales de proteína para recomendaciones ─────────────────────
PROTEIN_FUNCTIONAL_TARGETS = {
    "minimo_estructura": 2.5,   # % mínimo para cuerpo en helado sin sorbet
    "optimo_overrun":    3.5,   # % donde la espuma de overrun es más estable
    "alto_proteina":    10.0,   # % target en helado proteico
}

# ── Clasificación calórica del helado ────────────────────────────────────────
# Rangos por 100g de producto (base sin overrun)
CALORIE_CLASSIFICATION = {
    # (max_kcal, etiqueta, emoji, descripción)
    "muy_ligero":  (80,  "Muy ligero",  "🥗", "Muy bajo en calorías — apto para dietas estrictas (< 80 kcal/100g)"),
    "ligero":      (130, "Ligero",      "💚", "Bajo en calorías — helado de dieta o light (80-130 kcal/100g)"),
    "moderado":    (180, "Moderado",    "🟡", "Calorías moderadas — helado artesanal estándar (130-180 kcal/100g)"),
    "denso":       (240, "Calórico",    "🟠", "Alto en calorías — gelato cremoso o con mucha grasa (180-240 kcal/100g)"),
    "muy_denso":   (999, "Muy calórico","🔴", "Muy alto en calorías — receta indulgente o con mucho azúcar/grasa (> 240 kcal/100g)"),
}

# ── Clasificación proteica ────────────────────────────────────────────────────
PROTEIN_CLASSIFICATION = {
    # (min_g, max_g, etiqueta, emoji, descripción)
    "muy_bajo":       (0,    2.5,  "Proteína muy baja",  "⬇️",  "< 2.5 g/100g — sin aporte proteico significativo"),
    "bajo":           (2.5,  5.0,  "Proteína baja",      "📊",  "2.5-5 g/100g — aporte modesto"),
    "fuente":         (5.0,  10.0, "Fuente de proteína", "💪",  "5-10 g/100g — califica como 'fuente de proteína' (Codex)"),
    "alto":           (10.0, 20.0, "Alto en proteína",   "🏋️", "10-20 g/100g — helado proteico"),
    "muy_alto":       (20.0, 999,  "Muy alto proteína",  "⚡",  "> 20 g/100g — suplemento proteico"),
}
