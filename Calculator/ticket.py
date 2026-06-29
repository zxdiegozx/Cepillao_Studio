"""
ticket.py — Ticket de producción imprimible.

Responsabilidad única: formatear todos los resultados del motor
en un texto estructurado listo para imprimir o exportar.

Función pública:
    format_production_ticket(...)  → str con el ticket completo
"""

from datetime import datetime

from constants import (
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    DIAGS_EXCLUIR_TICKET,
)
from diagnostics import get_targets, _status
from calc_nutrition import overrun_calc


def format_production_ticket(recipe_name: str, product_type: str, machine: str,
                              ingredient_names: list, lines_for_calculator: list,
                              totals: dict, pct: dict, derived: dict,
                              kcal: dict, protein_data: dict = None) -> str:
    """
    Genera el texto del ticket de producción.

    Los diagnósticos marcados en DIAGS_EXCLUIR_TICKET se omiten.
    """
    m         = totals.get('grams', 0)
    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)
    targets   = derived.get('targets', get_targets(product_type, machine))

    return '\n'.join([
        _header(recipe_name, product_type, machine),
        _block_ingredientes(lines_for_calculator, m),
        _block_composicion(pct, totals, targets, derived),
        _block_calorias(kcal),
        _block_produccion(m, machine, is_creami, derived),
        _block_diagnosticos(derived),
        _instrucciones(is_creami),
        '══════════════════════════════════════════════',
    ])


# ── Bloques privados ──────────────────────────────────────────────────────────

def _header(recipe_name: str, product_type: str, machine: str) -> str:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    return (
        '══════════════════════════════════════════════\n'
        f'  🍦 TICKET PRODUCCIÓN — {recipe_name}\n'
        f'  {product_type} · {machine}\n'
        f'  {ts}'
    )


def _block_ingredientes(lines: list, masa_total: float) -> str:
    rows = ''.join(
        f"  {ing['name']:<30} {float(grams):>6.1f} g\n"
        for ing, grams, _ in lines
        if ing and grams
    )
    return (
        '══════════════════════════════════════════════\n'
        'INGREDIENTES:\n'
        f'{rows}'
        f"  {'─' * 40}\n"
        f'  Masa total:     {masa_total:.0f} g'
    )


def _semaforo(val: float, lo, hi) -> str:
    s = _status(val, lo, hi)
    return {'empty': '⬜', 'low': '🔵', 'ok': '✅', 'high': '🔴'}.get(s, '❓')


def _block_composicion(pct: dict, totals: dict, targets: dict, derived: dict) -> str:
    stw    = derived.get('st_water_ratio')
    stw_lo, stw_hi = targets.get('st_water', (0.42, 0.78))
    stw_sym = _semaforo(stw, stw_lo, stw_hi) if stw is not None else '⬜'
    stw_str = f'{stw:.3f}' if stw is not None else 'n/d'
    dt      = derived.get('delta_t', 0)
    zona    = derived.get('crio_zona', '')
    zona_icons = {
        'muy_bajo': '🔴', 'bajo': '🟡', 'optimo': '✅',
        'alto': '🟡', 'muy_alto': '🔴',
    }

    def sym(k):
        vals = {
            'st': pct.get('st_pct', 0), 'fat': pct.get('fat_pct', 0),
            'msnf': pct.get('msnf_pct', 0), 'sugars': pct.get('sugars_pct', 0),
            'pod': pct.get('pod_total', 0), 'pac': pct.get('pac_total', 0),
        }
        return _semaforo(vals.get(k, 0), *targets.get(k, (None, None)))

    return (
        '\nCOMPOSICIÓN:\n'
        f"  ST:             {pct.get('st_pct', 0):.1f}%   {sym('st')}\n"
        f"  Grasa:          {pct.get('fat_pct', 0):.1f}%   {sym('fat')}\n"
        f"  MSNF:           {pct.get('msnf_pct', 0):.1f}%   {sym('msnf')}\n"
        f"  Azúcares:       {pct.get('sugars_pct', 0):.1f}%   {sym('sugars')}\n"
        f"  Agua libre:     {pct.get('water_pct', 0):.1f}%\n"
        f"  Ratio ST/Agua:  {stw_str}   {stw_sym} (rango {stw_lo:.2f}–{stw_hi:.2f})\n"
        f"  POD:            {pct.get('pod_total', 0):.0f}      {sym('pod')}\n"
        f"  PAC:            {pct.get('pac_total', 0):.0f}      {sym('pac')}\n"
        f"  ΔT crioscopía:  {dt:.2f} °C   {zona_icons.get(zona, '')}"
    )


def _block_calorias(kcal: dict) -> str:
    cal   = kcal.get('clasificacion_calorica')
    prot  = kcal.get('clasificacion_proteica')
    lines = [f"\nCALORÍAS / NUTRICIÓN:"]
    cal_line = f"  kcal / 100 g:   {kcal['kcal_per_100g']:.0f} kcal"
    if cal:
        cal_line += f"  {cal['emoji']} {cal['etiqueta']}"
    lines.append(cal_line)
    if prot:
        lines.append(f"  Proteína:       {prot['valor']:.1f} g/100g  {prot['emoji']} {prot['etiqueta']}")
    lines.append(f"  Costo estimado: ${kcal.get('cost', 0):.2f}" if 'cost' in kcal else '')
    return '\n'.join(l for l in lines if l)


def _block_produccion(m: float, machine: str, is_creami: bool, derived: dict) -> str:
    or_d = overrun_calc(m, 0, 1.0, machine)
    alc  = derived.get('alcohol_detected')

    if is_creami:
        prod = (
            f"\nPRODUCCIÓN:\n"
            f"  Overrun fijo Creami:   ~{or_d['overrun_fijo_pct']}%  (mecánico)\n"
            f"  Masa final estimada:   {or_d['masa_final_estimada_g']:.0f} g\n"
            f"  Volumen estimado:      {or_d['volumen_estimado_ml']:.0f} mL "
            f"(densidad ≈{or_d['densidad_helado_g_ml']:.2f} g/mL)\n"
            f"  Potes (base):          {or_d['potes_base']:.1f} × {or_d['masa_por_pote_g']:.0f} g"
        )
    else:
        prod = (
            f"\nPRODUCCIÓN:\n"
            f"  Litros producidos:     {or_d['liters_from_base']:.2f} L"
        )

    if alc:
        prod += (f"\n\n  🍾 Alcohol detectado: {alc['ethanol_total_g']} g etanol "
                 f"({alc['ethanol_pct']:.2f}% de la mezcla)")
    return prod


def _block_diagnosticos(derived: dict) -> str:
    diags = [d for d in derived.get('diagnostics', [])
             if d['key'] not in DIAGS_EXCLUIR_TICKET]
    if not diags:
        return '\nDIAGNÓSTICOS:\n  ✅ Mezcla balanceada — sin alertas.'
    icons = {'critical': '🔴', 'important': '🟡', 'adjustable': '🔵'}
    rows  = '\n'.join(
        f"  {icons.get(d['priority'], '⚪')} {d['title']}\n     → {d['tip']}"
        for d in diags
    )
    return f'\nDIAGNÓSTICOS:\n{rows}'


def _instrucciones(is_creami: bool) -> str:
    if is_creami:
        return (
            '\nINSTRUCCIONES NINJA CREAMI:\n'
            '  1. Mezclar y pasteurizar a 85°C / 15 seg\n'
            '  2. Enfriar a <4°C (baño de hielo)\n'
            '  3. Congelar mín. 24h a −18°C\n'
            '  4. Procesar con función Ice Cream o Lite Ice Cream\n'
            '  5. Si queda granuloso: Re-spin sin añadir líquido'
        )
    return (
        '\nINSTRUCCIONES MANTECADORA:\n'
        '  1. Pasteurizar a 85°C / 15 seg\n'
        '  2. Madurar en frío 4-12h a 4°C\n'
        '  3. Mantecado según overrun objetivo\n'
        '  4. Endurecimiento: −18°C mín. 2h'
    )
