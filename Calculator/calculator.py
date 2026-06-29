"""
calculator.py — Fachada pública del motor de cálculo.

Re-exporta todas las funciones y constantes que app.py consume.
No contiene lógica: cada función vive en su módulo de responsabilidad única.

Módulos internos:
    calc_core       → líneas, totales, porcentajes, Brix, Aw
    calc_cryoscopy  → ΔT, zonas crioscópicas
    calc_nutrition  → calorías, proteínas, edulcorantes, overrun
    diagnostics     → targets, calc_derived, estabilizantes
    ticket          → formato de ticket de producción
"""

from calc_core import (
    calc_line,
    calc_totals,
    calc_percentages,
    validate_brix,
    calc_water_activity,
)

from calc_cryoscopy import (
    calc_cryoscopy,
)

from calc_nutrition import (
    SWEETENER_PROFILES,
    CREAMI_DELUXE_CAPACITY_G,
    CREAMI_STANDARD_CAPACITY_G,
    calc_calories,
    analyze_sweeteners,
    analyze_protein,
    overrun_calc,
    _detect_alcohol_lines,
)

from diagnostics import (
    get_targets,
    _status,
    calc_derived,
    recommend_stabilizers,
)

# Alias de compatibilidad — app.py llama a _get_targets en algunos lugares
_get_targets = get_targets

from ticket import format_production_ticket

__all__ = [
    # calc_core
    'calc_line', 'calc_totals', 'calc_percentages',
    'validate_brix', 'calc_water_activity',
    # calc_cryoscopy
    'calc_cryoscopy',
    # calc_nutrition
    'SWEETENER_PROFILES',
    'CREAMI_DELUXE_CAPACITY_G', 'CREAMI_STANDARD_CAPACITY_G',
    'calc_calories', 'analyze_sweeteners', 'analyze_protein',
    'overrun_calc', '_detect_alcohol_lines',
    # diagnostics
    'get_targets', '_get_targets', '_status',
    'calc_derived', 'recommend_stabilizers',
    # ticket
    'format_production_ticket',
]
