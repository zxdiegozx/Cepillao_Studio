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
