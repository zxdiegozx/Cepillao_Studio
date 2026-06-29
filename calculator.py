"""
calculator.py — Fachada hacia el package engine/.

app.py importa `import calculator as calc` y todo funciona igual que antes.
Toda la lógica vive en engine/.
"""
from engine import *
from engine import _get_targets, _status, _detect_alcohol_lines
