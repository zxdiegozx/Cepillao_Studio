"""
calculator.py — Fachada hacia el package engine/.

app.py importa `import calculator as calc` y todo funciona igual que antes.
Toda la lógica vive en engine/.
"""
from engine import (
    calc_line, calc_totals, calc_percentages,
    validate_brix, calc_water_activity,
    calc_cryoscopy,
    SWEETENER_PROFILES, CREAMI_DELUXE_CAPACITY_G, CREAMI_STANDARD_CAPACITY_G,
    calc_calories, analyze_sweeteners, analyze_protein,
    overrun_calc, _detect_alcohol_lines,
    get_targets, _get_targets, _status,
    calc_derived, recommend_stabilizers,
    format_production_ticket,
)
