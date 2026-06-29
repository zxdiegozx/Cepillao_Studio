"""
calc_cryoscopy.py — Modelo crioscópico de Raoult simplificado.

Responsabilidad única: calcular el descenso del punto de congelación
y clasificar la mezcla en zonas de comportamiento.

Función pública:
    calc_cryoscopy(totals) → dict con delta_t, crio_zona, congela_ok, temp_servicio

Fundamento físico (Raoult simplificado):
    ΔT = −Kf × m
    Kf = 1.86 °C·kg/mol  (constante crioscópica del agua)
    m  = molalidad = moles_soluto / kg_agua

    Los moles de soluto se obtienen normalizando el PAC acumulado por
    M_sacarosa (342.3 g/mol), expresando todos los azúcares como
    "equivalentes sacarosa" en términos de efecto crioscópico.

Zonas de ΔT (física real, FIX-6 v2.2):
    > −1.0°C     muy_bajo  → base acuosa, cristales grandes, icy inevitable
    −1.0 a −1.8  bajo      → granuloso probable
    −1.8 a −4.0  optimo    → zona ideal Creami y mantecadora
    −4.0 a −6.0  alto      → exceso leve, puede quedar blando
    < −6.0°C     muy_alto  → exceso severo o alcohol masivo

    Nota: el ΔT es la temperatura de INICIO de congelación (primer cristal),
    NO la temperatura a la que el helado queda sólido. Un ΔT de −2/−3°C
    es correcto y normal — el helado congela completamente a −18°C porque
    la congelación es un proceso progresivo.
"""

# ── Constantes del modelo ─────────────────────────────────────────────────────
_KF        = 1.86    # °C·kg/mol — constante crioscópica del agua
_M_SAC     = 342.3   # g/mol     — masa molar de referencia (sacarosa)

# Umbrales de zona (°C) — derivados de física de cristalización
_ZONA_MUY_BAJO = -1.0
_ZONA_BAJO     = -1.8
_ZONA_OPTIMO   = -4.0
_ZONA_ALTO     = -6.0

# Etiquetas para UI
_ZONA_LABELS = {
    'sin_agua': "ΔT — sin agua libre, no calculable",
    'muy_bajo': "⚠️ base acuosa, textura icy inevitable",
    'bajo':     "🟡 algo bajo, granuloso probable",
    'optimo':   "✅ zona ideal (−1.8 a −4.0°C)",
    'alto':     "🟡 exceso leve de PAC, puede quedar blando",
    'muy_alto': "🔴 exceso severo de PAC o alcohol",
}


def _clasificar_zona(delta_t: float, water_kg: float) -> str:
    """Devuelve la clave de zona crioscópica según el ΔT calculado."""
    if water_kg <= 0:
        return 'sin_agua'
    if delta_t > _ZONA_MUY_BAJO:
        return 'muy_bajo'
    if delta_t > _ZONA_BAJO:
        return 'bajo'
    if delta_t > _ZONA_OPTIMO:
        return 'optimo'
    if delta_t > _ZONA_ALTO:
        return 'alto'
    return 'muy_alto'


def calc_cryoscopy(totals: dict) -> dict:
    """
    Calcula el descenso crioscópico y clasifica la mezcla por zona.

    Args:
        totals: dict de totales de masa (salida de calc_totals)

    Returns:
        delta_t       (float) — descenso en °C (negativo)
        crio_zona     (str)   — clave de zona: muy_bajo|bajo|optimo|alto|muy_alto
        congela_ok    (bool)  — True si la zona es apta para congelación
        temp_servicio (str)   — texto descriptivo para UI
    """
    pac_moles = totals.get('pac',   0) / _M_SAC
    water_kg  = totals.get('water', 0) / 1000

    delta_t = -_KF * (pac_moles / water_kg) if water_kg > 0 else 0.0

    zona       = _clasificar_zona(delta_t, water_kg)
    congela_ok = zona in ('bajo', 'optimo', 'alto')
    label      = _ZONA_LABELS.get(zona, '')

    return {
        'delta_t':        round(delta_t, 2),
        'crio_zona':      zona,
        'congela_ok':     congela_ok,
        'cryoscopy_model': f'Raoult simplificado (Kf={_KF}, M_ref={_M_SAC})',
        'temp_servicio':  f"ΔT {delta_t:.2f}°C — {label}",
    }
