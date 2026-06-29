"""
engine/__init__.py — Package de cálculo de Cepillao' Gelato Studio.

Expone toda la API pública que app.py consume a través de calculator.py.

Estructura del package:
    engine/
        calc_core.py       → calc_line, calc_totals, calc_percentages, Brix, Aw
        calc_cryoscopy.py  → delta_t, zonas crioscópicas
        calc_nutrition.py  → calorías, proteínas, edulcorantes, overrun
        diagnostics.py     → targets, calc_derived, estabilizantes
        ticket.py          → formato ticket de producción
"""

from .calc_core import (
    calc_line,
    calc_totals,
    calc_percentages,
    validate_brix,
    calc_water_activity,
)

from .calc_cryoscopy import (
    calc_cryoscopy,
)

from .calc_nutrition import (
    SWEETENER_PROFILES,
    CREAMI_DELUXE_CAPACITY_G,
    CREAMI_STANDARD_CAPACITY_G,
    calc_calories,
    analyze_sweeteners,
    analyze_protein,
    overrun_calc,
    _detect_alcohol_lines,
)

from .diagnostics import (
    get_targets,
    _status,
    calc_derived,
    recommend_stabilizers,
)

# Alias de compatibilidad — app.py llama calc._get_targets()
_get_targets = get_targets

from .ticket import format_production_ticket

__all__ = [
    'calc_line', 'calc_totals', 'calc_percentages',
    'validate_brix', 'calc_water_activity',
    'calc_cryoscopy',
    'SWEETENER_PROFILES', 'CREAMI_DELUXE_CAPACITY_G', 'CREAMI_STANDARD_CAPACITY_G',
    'calc_calories', 'analyze_sweeteners', 'analyze_protein',
    'overrun_calc', '_detect_alcohol_lines',
    'get_targets', '_get_targets', '_status',
    'calc_derived', 'recommend_stabilizers',
    'format_production_ticket',
]
