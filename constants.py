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
