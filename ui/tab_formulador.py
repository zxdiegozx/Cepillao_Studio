import streamlit as st
import calculator as calc
import database as db
import restricciones
from constants import (
    PRODUCT_TYPES, MACHINES,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
    DIAGS_EXCLUIR_TICKET,
    CREAMI_OVERRUN_PCT,
)
from .components import (
    _param_bar, _section, _radar_chart,
    _collect_lines, _load_recipe_into_state,
    _invalidate_ingredient_cache,
    callback_add_row, callback_clear_all,
)


def render(tab, ingredients_map: dict, ingredient_names: list):
    with tab:

        # Garantiza que num_rows sea siempre un int válido ≥ 4.
        # Si Streamlit borra el estado en un rerun inesperado, el formulario
        # se queda vacío pero no explota con TypeError/AttributeError.
        try:
            st.session_state.num_rows = max(4, int(st.session_state.get("num_rows", 4)))
        except (TypeError, ValueError):
            st.session_state.num_rows = 4

        # ── Sidebar ───────────────────────────────────────────────────────────
        st.sidebar.markdown("### ⚙️ Parámetros de receta")

        recipe_name_input = st.sidebar.text_input(
            "Nombre de la receta",
            value=st.session_state.get("recipe_loaded_name", ""),
            placeholder="Ej: Choco Creami v3"
        )

        _loaded_name = st.session_state.get("recipe_loaded_name", "")
        _loaded_id   = st.session_state.get("recipe_loaded_id")
        if _loaded_name:
            _tipo_carga = "Receta" if _loaded_id else "Base"
            st.sidebar.markdown(
                f"""<div style="background:#0f2a0f;border:1px solid #2d4a2d;border-radius:8px;
                padding:8px 12px;margin:4px 0 8px;font-size:0.78rem;">
                <span style="color:#666;text-transform:uppercase;letter-spacing:0.06em;
                font-size:0.68rem;">{_tipo_carga} activa</span><br>
                <span style="color:#4ade80;font-weight:600;">📂 {_loaded_name}</span>
                </div>""",
                unsafe_allow_html=True
            )

        product_type = st.sidebar.selectbox("Tipo de Producto", PRODUCT_TYPES)
        machine      = st.sidebar.selectbox("Maquinaria", MACHINES, index=0)
        is_creami    = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

        if is_creami:
            overrun_fijo = CREAMI_OVERRUN_PCT.get(machine, 50)
            st.sidebar.markdown(
                f"""<div style="background:#1a2a1a;border:1px solid #2d4a2d;border-radius:8px;
                padding:10px 12px;margin:6px 0;font-size:0.82rem;">
                <b style="color:#4ade80;">Overrun {machine.split()[-1]}:</b>
                <span style="color:#fff;"> ~{overrun_fijo}%</span><br>
                <span style="color:#666;">Fijo por diseño mecánico</span>
                </div>""", unsafe_allow_html=True
            )
            overrun_pct   = overrun_fijo
            target_liters = 1.0
        else:
            overrun_pct   = st.sidebar.number_input("Overrun (%)", 0, 120, 30, step=5)
            target_liters = st.sidebar.number_input("Litros objetivo", 0.1, 50.0, 1.0, step=0.5)

        brix_medido = st.sidebar.number_input(
            "Brix medido (°Bx)", 0.0, 80.0, 0.0, step=0.5,
            help="Opcional — validación con refractómetro"
        )

        escala = st.sidebar.number_input(
            "Escalar receta (×)", 0.25, 20.0, 1.0, step=0.25,
            help="Multiplica todos los gramos para calcular producción a mayor/menor escala"
        )

        st.sidebar.divider()

        def guardar_receta():
            nombre = recipe_name_input.strip()
            if not nombre:
                st.sidebar.error("Escribe un nombre.")
                return
            lines = _collect_lines()
            if not lines:
                st.sidebar.error("Añade al menos un ingrediente.")
                return
            data = {"name": nombre, "product_type": product_type, "machine": machine,
                    "base_grams": sum(l["grams"] for l in lines),
                    "notes": "", "is_base": 0, "lines": lines}
            existing_id = st.session_state.get("recipe_loaded_id")
            if existing_id:
                db.update_recipe(existing_id, data)
                st.sidebar.success(f"✅ «{nombre}» actualizada.")
            else:
                db.save_recipe(data)
                st.sidebar.success(f"✅ «{nombre}» guardada.")

        def guardar_como_base():
            nombre = recipe_name_input.strip()
            if not nombre:
                st.sidebar.error("Escribe un nombre.")
                return
            lines = _collect_lines()
            if not lines:
                st.sidebar.error("Añade al menos un ingrediente.")
                return
            data = {"name": nombre, "product_type": product_type, "machine": machine,
                    "base_grams": sum(l["grams"] for l in lines),
                    "notes": "Base de helado — concentrado reutilizable",
                    "is_base": 1, "lines": lines}
            db.save_recipe(data)
            _invalidate_ingredient_cache()
            st.sidebar.success(f"🧫 «{nombre}» guardada como Base.")

        st.sidebar.button("💾 Guardar receta",    on_click=guardar_receta,    use_container_width=True)
        st.sidebar.button("🧫 Guardar como Base", on_click=guardar_como_base, use_container_width=True)
        st.sidebar.button("🗑️ Limpiar todo",      on_click=callback_clear_all, use_container_width=True)

        # ── Layout principal ──────────────────────────────────────────────────
        col_ing, col_panel = st.columns([9, 11], gap="large")

        # ── Columna ingredientes ──────────────────────────────────────────────
        with col_ing:
            st.markdown('<div class="section-overline">🧾 Ingredientes</div>', unsafe_allow_html=True)
            st.markdown('<div class="ing-col-header">', unsafe_allow_html=True)
            _h1, _h2, _h3 = st.columns([3, 1.5, 1.5])
            _h1.caption("Ingrediente")
            _h2.caption("Gramos")
            _h3.caption("$/kg")
            st.markdown('</div>', unsafe_allow_html=True)

            lines_for_calculator    = []
            active_ingredient_names = []

            for i in range(st.session_state.num_rows):
                st.markdown(f'<div class="ing-row-wrap" id="ing-row-{i}">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([3, 1.5, 1.5])
                ing_name = c1.selectbox(
                    f"ing_{i}", [""] + ingredient_names,
                    key=f"ing_name_{i}", label_visibility="collapsed"
                )
                grams = c2.number_input(
                    f"g_{i}", 0.0, 5000.0, 0.0, step=5.0,
                    key=f"grams_{i}", label_visibility="collapsed",
                    format="%.0f"
                )
                price = c3.number_input(
                    f"p_{i}", 0.0, step=0.5,
                    key=f"price_{i}", label_visibility="collapsed",
                    format="%.2f"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                if ing_name and grams > 0:
                    ing_obj = ingredients_map.get(ing_name)
                    if ing_obj:
                        lines_for_calculator.append((ing_obj, grams, price))
                        active_ingredient_names.append(ing_name)

            st.button("＋ Agregar fila", on_click=callback_add_row, use_container_width=True)

            if lines_for_calculator:
                if escala != 1.0:
                    lines_for_calculator = [(ing, g * escala, p) for ing, g, p in lines_for_calculator]
                masa_tot  = sum(g for _, g, _ in lines_for_calculator)
                costo_tot = sum((g / 1000) * p for _, g, p in lines_for_calculator)
                escala_txt = f" ×{escala:.2g}" if escala != 1.0 else ""
                st.markdown(f"""
                <div style="display:flex;gap:16px;padding:10px 14px;background:#181828;
                     border-radius:8px;margin-top:8px;border:1px solid #252540;">
                  <div>
                    <div style="font-size:0.68rem;color:#666;text-transform:uppercase;">Masa total{escala_txt}</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#fff;">{masa_tot:.0f} g</div>
                  </div>
                  <div>
                    <div style="font-size:0.68rem;color:#666;text-transform:uppercase;">Costo est.</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#fff;">${costo_tot:.2f}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # ── Columna análisis ──────────────────────────────────────────────────
        with col_panel:
            try:
                _render_panel(
                    lines_for_calculator, active_ingredient_names,
                    product_type, machine, is_creami,
                    overrun_pct, target_liters, brix_medido,
                    recipe_name_input,
                )
            except Exception as _err:
                st.error(f"⚠️ Error en el panel de análisis: {_err}")
                st.caption("Los datos del formulario están intactos. "
                           "Revisa la consola para el traceback completo.")


# ═════════════════════════════════════════════════════════════════════════════
# Panel de análisis (columna derecha)
# ═════════════════════════════════════════════════════════════════════════════

def _render_panel(lines_for_calculator, active_ingredient_names,
                  product_type, machine, is_creami,
                  overrun_pct, target_liters, brix_medido,
                  recipe_name_input):
    targets_default = calc._get_targets(product_type, machine)
    config_override = st.session_state.config_params.get(f"{product_type}_{machine}", {})

    if not lines_for_calculator:
        # FIX: el preview de rangos debe reflejar la config manual del usuario,
        # no solo los defaults. Antes hacía `tg = targets_default` y por eso
        # "ajustar no repercutía" mientras no hubiera ingredientes cargados:
        # el bloque de abajo siempre mostraba los valores de fábrica.
        tg = dict(targets_default)
        for _k in ('st', 'fat', 'msnf', 'sugars', 'pod', 'pac', 'st_water'):
            if _k in config_override:
                tg[_k] = config_override[_k]
        _ov = ' · ⚙️ personalizado' if config_override else ''
        st.markdown(f'<div class="section-overline">📊 Rangos objetivo{_ov}</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="comp-grid">
          <div class="comp-cell"><div class="comp-cell-label">ST</div>
            <div class="comp-cell-val">{tg['st'][0]}–{tg['st'][1]}%</div></div>
          <div class="comp-cell"><div class="comp-cell-label">Grasa</div>
            <div class="comp-cell-val">{tg['fat'][0]}–{tg['fat'][1]}%</div></div>
          <div class="comp-cell"><div class="comp-cell-label">MSNF</div>
            <div class="comp-cell-val">{tg['msnf'][0]}–{tg['msnf'][1]}%</div></div>
          <div class="comp-cell"><div class="comp-cell-label">Azúcares</div>
            <div class="comp-cell-val">{tg['sugars'][0]}–{tg['sugars'][1]}%</div></div>
          <div class="comp-cell"><div class="comp-cell-label">POD</div>
            <div class="comp-cell-val">{tg['pod'][0]}–{tg['pod'][1]}</div></div>
          <div class="comp-cell"><div class="comp-cell-label">PAC</div>
            <div class="comp-cell-val">{tg['pac'][0]}–{tg['pac'][1]}</div></div>
        </div>""", unsafe_allow_html=True)
        st.caption("Selecciona ingredientes y gramos para ver el análisis en vivo.")
        return

    totals        = calc.calc_totals(lines_for_calculator)
    pct           = calc.calc_percentages(totals)
    alcohol_lines = calc._detect_alcohol_lines(lines_for_calculator)
    derived       = calc.calc_derived(
        totals, pct, product_type=product_type, machine=machine,
        lines_with_ings=lines_for_calculator,
        config=config_override or None,
        alcohol_lines=alcohol_lines,
    )
    kcal         = calc.calc_calories(totals, lines_for_calculator, alcohol_lines=alcohol_lines)
    prot_data    = calc.analyze_protein(lines_for_calculator, totals, pct, product_type)
    restricciones_activas = restricciones.verificar(
        lines_for_calculator, totals, pct, product_type, machine
    )
    tg   = derived.get('targets', targets_default)
    or_d = calc.overrun_calc(totals["grams"], overrun_pct, target_liters, machine)

    # ── Barra de llenado del pote ─────────────────────────────────────────────
    if is_creami:
        cap  = 640 if machine == MACHINE_CREAMI_DELUXE else 430
        masa = totals["grams"]
        fill_pct = min(masa / cap * 100, 100)
        if masa < 450:
            bar_color, msg_color, msg = "#3b82f6", "#60a5fa", f"Pote poco lleno — {masa:.0f}/{cap}g"
        elif masa <= cap:
            bar_color, msg_color, msg = "#4ade80", "#4ade80", f"Perfecto — {masa:.0f}/{cap}g"
        else:
            bar_color, msg_color, msg = "#f87171", "#f87171", f"Excede {masa-cap:.0f}g el pote"
        cap_label = "24 oz" if machine == MACHINE_CREAMI_DELUXE else "16 oz"
        st.markdown(f"""
        <div class="pote-fill-wrap">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span class="pote-fill-label">🫙 Pote Creami {cap_label}</span>
            <span style="font-size:0.8rem;color:{msg_color};font-weight:600;">{msg}</span>
          </div>
          <div class="pote-fill-bar-bg">
            <div class="pote-fill-bar"
                 style="width:{fill_pct:.1f}%;background:{bar_color};"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── CALORÍAS ──────────────────────────────────────────────────────────────
    _section("🔥 Calorías y Nutrición")
    cal_class  = kcal.get('clasificacion_calorica')
    prot_class = kcal.get('clasificacion_proteica')

    kcal_badge = ""
    if cal_class:
        badge_colors = {
            "muy_ligero": ("badge-ok",     "#4ade80"),
            "ligero":     ("badge-ok",     "#4ade80"),
            "moderado":   ("badge-info",   "#60a5fa"),
            "denso":      ("badge-warn",   "#fb923c"),
            "muy_denso":  ("badge-danger", "#f87171"),
        }
        bc, _ = badge_colors.get(cal_class['key'], ("badge-info", "#60a5fa"))
        kcal_badge = f'<span class="badge {bc}">{cal_class["emoji"]} {cal_class["etiqueta"]}</span>'

    if is_creami:
        _tercera_val = kcal.get('kcal_per_pote_deluxe', 0)
        _tercera_lbl = "kcal / pote completo"
    else:
        _or_factor   = overrun_pct / 100
        _tercera_val = kcal['kcal_per_100g'] / 100 * (1000 / (1 + _or_factor))
        _tercera_lbl = f"kcal / L (~{overrun_pct:.0f}% OR)"

    st.markdown(f"""
    <div class="kcal-grid">
      <div class="kcal-cell">
        <div class="kcal-cell-val">{kcal['kcal_per_100g']:.0f}</div>
        <div class="kcal-cell-label">kcal / 100g</div>
      </div>
      <div class="kcal-cell">
        <div class="kcal-cell-val">{kcal['kcal_per_100g']*1.2:.0f}</div>
        <div class="kcal-cell-label">kcal / porción 120g</div>
      </div>
      <div class="kcal-cell">
        <div class="kcal-cell-val">{_tercera_val:.0f}</div>
        <div class="kcal-cell-label">{_tercera_lbl}</div>
      </div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">
      {kcal_badge}
      {'<span class="badge badge-info">' + prot_class["emoji"] + " " + prot_class["etiqueta"] + " " + str(prot_class["valor"]) + "g/100g</span>" if prot_class else ""}
    </div>""", unsafe_allow_html=True)

    # ── COMPOSICIÓN CON BARRAS ────────────────────────────────────────────────
    _section("🧬 Composición")

    c1, c2, c3 = st.columns(3)
    with c1:
        _param_bar("Sólidos Totales", pct.get('st_pct', 0),
                   tg['st'][0], tg['st'][1], "%", scale_max=50)
    with c2:
        _param_bar("Grasa", pct.get('fat_pct', 0),
                   tg['fat'][0], tg['fat'][1], "%", scale_max=25)
    with c3:
        water_v  = pct.get('water_pct', 0)
        water_lo = max(0, round(100 - tg['st'][1], 1))
        water_hi = round(100 - tg['st'][0], 1)
        _param_bar("Agua libre", water_v, water_lo, water_hi, "%", scale_max=100)

    c1, c2, c3 = st.columns(3)
    with c1:
        _param_bar("MSNF", pct.get('msnf_pct', 0),
                   tg['msnf'][0], tg['msnf'][1], "%", scale_max=15)
    with c2:
        _param_bar("Azúcares", pct.get('sugars_pct', 0),
                   tg['sugars'][0], tg['sugars'][1], "%", scale_max=35)
    with c3:
        stw    = derived.get('st_water_ratio', 0)
        stw_lo, stw_hi = tg.get('st_water', (0.42, 0.78))
        _param_bar("Ratio ST/Agua", stw, stw_lo, stw_hi, "", scale_max=1.2)

    c1, c2 = st.columns(2)
    with c1:
        _param_bar("POD", pct.get('pod_total', 0),
                   tg['pod'][0], tg['pod'][1], "", scale_max=280)
    with c2:
        _param_bar("PAC", pct.get('pac_total', 0),
                   tg['pac'][0], tg['pac'][1], "", scale_max=400)

    with st.expander("🕸️ Radar de Composición", expanded=False):
        st.plotly_chart(_radar_chart(pct, tg), use_container_width=True,
                        config={'displayModeBar': False})

    # ── CRIOSCOPÍA + Aw ───────────────────────────────────────────────────────
    _section("❄️ Crioscopía  ·  💧 Actividad de Agua")
    dt      = derived.get("delta_t", 0)
    aw_data = calc.calc_water_activity(totals)

    crio_ok    = derived.get("congela_ok", True)
    crio_color = "#4ade80" if crio_ok else "#f87171"
    crio_icon  = "✓" if crio_ok else "✗"
    crio_label = "Congela a −18°C" if crio_ok else "No congela a −18°C"

    aw_riesgo = aw_data['riesgo_micro']
    aw_colors = {"bajo": "#4ade80", "medio": "#fb923c", "alto": "#f87171"}
    aw_color  = aw_colors.get(aw_riesgo, "#888")

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
      <div class="comp-cell">
        <div class="comp-cell-label">ΔT crioscópico</div>
        <div class="comp-cell-val" style="color:{crio_color};">{dt:.2f}°C</div>
      </div>
      <div class="comp-cell">
        <div class="comp-cell-label">Estado</div>
        <div class="comp-cell-val" style="color:{crio_color};font-size:0.9rem;">{crio_icon} {crio_label}</div>
      </div>
      <div class="comp-cell">
        <div class="comp-cell-label">Aw estimada</div>
        <div class="comp-cell-val">{aw_data.get('aw', 0):.3f}</div>
      </div>
      <div class="comp-cell">
        <div class="comp-cell-label">Riesgo micro</div>
        <div class="comp-cell-val" style="color:{aw_color};font-size:0.85rem;">{aw_riesgo.upper()}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── DIAGNÓSTICOS ──────────────────────────────────────────────────────────
    diags = derived.get("diagnostics", [])
    if diags:
        _section("🩺 Diagnósticos")
        crits = [d for d in diags if d['priority'] == 'critical']
        imps  = [d for d in diags if d['priority'] == 'important']
        adjs  = [d for d in diags if d['priority'] == 'adjustable'
                 and d.get('key') not in DIAGS_EXCLUIR_TICKET]

        if not crits and not imps and not adjs:
            st.markdown('<div class="badge badge-ok">✓ Formulación dentro de rangos</div>',
                        unsafe_allow_html=True)
        else:
            _diag_html = ""
            for d in crits:
                _diag_html += (f'<div class="diag-item diag-critical">'
                               f'<div class="diag-title">🔴 {d["title"]}</div>'
                               f'<div class="diag-tip">{d["tip"]}</div></div>')
            for d in imps:
                _diag_html += (f'<div class="diag-item diag-important">'
                               f'<div class="diag-title">🟠 {d["title"]}</div>'
                               f'<div class="diag-tip">{d["tip"]}</div></div>')
            for d in adjs:
                _diag_html += (f'<div class="diag-item diag-adjustable">'
                               f'<div class="diag-title">🔵 {d["title"]}</div>'
                               f'<div class="diag-tip">{d["tip"]}</div></div>')
            st.markdown(_diag_html, unsafe_allow_html=True)

    # ── RESTRICCIONES ─────────────────────────────────────────────────────────
    if restricciones_activas:
        _section("🚫 Restricciones de Formulación")
        _tipo_icon = {
            'incompatibilidad': '⚡',
            'cota_superior':    '🔺',
            'contexto':         '🏷️',
            'proceso':          '🔧',
        }
        _sev_class = {
            'critico':    'diag-critical',
            'importante': 'diag-important',
            'ajustable':  'diag-adjustable',
        }
        _sev_dot = {
            'critico':    '🔴',
            'importante': '🟠',
            'ajustable':  '🔵',
        }
        _rest_html = ""
        for r in restricciones_activas:
            sev   = r['severidad']
            icon  = _tipo_icon.get(r['tipo'], '⚠️')
            dot   = _sev_dot.get(sev, '⚪')
            clase = _sev_class.get(sev, 'diag-adjustable')
            ings  = r.get('ingredientes', [])
            ings_html = (
                f'<div style="font-size:0.7rem;color:#666;margin-top:3px;">'
                f'Ingredientes: {", ".join(ings[:4])}</div>'
                if ings else ""
            )
            _rest_html += (
                f'<div class="diag-item {clase}">'
                f'<div class="diag-title">{dot} {icon} {r["titulo"]}</div>'
                f'<div class="diag-tip">{r["detalle"]}</div>'
                f'{ings_html}'
                f'</div>'
            )
        st.markdown(_rest_html, unsafe_allow_html=True)

    # ── OVERRUN ───────────────────────────────────────────────────────────────
    _section("📐 Rendimiento / Overrun")
    if or_d.get('is_creami'):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Potes base</div>
          <div class="comp-cell-val">{or_d['potes_completos']} + resto</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Masa final est.</div>
          <div class="comp-cell-val">{or_d['masa_final_estimada_g']:.0f} g</div>
        </div>""", unsafe_allow_html=True)
        c3.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Volumen est.</div>
          <div class="comp-cell-val">{or_d['volumen_estimado_ml']:.0f} ml</div>
        </div>""", unsafe_allow_html=True)
        if or_d.get("masa_ultimo_pote_g", 0) > 10:
            st.caption(f"🫙 Último pote: {or_d['masa_ultimo_pote_g']:.0f} g de base")
        _n_potes = or_d['potes_completos'] + (1 if or_d.get('masa_ultimo_pote_g', 0) > 10 else 0)
        if totals['cost'] > 0 and _n_potes > 0:
            st.caption(f"💰 Costo por pote: ${totals['cost'] / _n_potes:.2f}")
    else:
        c1, c2 = st.columns(2)
        c1.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Base necesaria</div>
          <div class="comp-cell-val">{or_d['base_needed_g']:.0f} g</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Litros producidos</div>
          <div class="comp-cell-val">{or_d['liters_from_base']:.2f} L</div>
        </div>""", unsafe_allow_html=True)
        if totals['cost'] > 0 and or_d['liters_from_base'] > 0:
            st.caption(f"💰 Costo por litro: ${totals['cost'] / or_d['liters_from_base']:.2f}")

    # ── VALIDACIÓN BRIX ───────────────────────────────────────────────────────
    if brix_medido > 0:
        _section("🔭 Validación Brix")
        bx = calc.validate_brix(brix_medido, totals)
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Brix medido</div>
          <div class="comp-cell-val">{brix_medido:.1f}°</div>
        </div>""", unsafe_allow_html=True)
        c2.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Brix esperado</div>
          <div class="comp-cell-val">{bx['brix_con_msnf']:.1f}°</div>
        </div>""", unsafe_allow_html=True)
        delta_c = "#4ade80" if abs(bx['delta_brix']) <= 2 else "#f87171"
        c3.markdown(f"""<div class="comp-cell">
          <div class="comp-cell-label">Delta</div>
          <div class="comp-cell-val" style="color:{delta_c};">{bx['delta_brix']:+.2f}°</div>
        </div>""", unsafe_allow_html=True)
        st.caption(bx['interpretacion'])

    # ── ESTABILIZANTES ────────────────────────────────────────────────────────
    _section("🧪 Estabilizantes recomendados")
    stab_recs = calc.recommend_stabilizers(
        totals, pct, product_type, machine,
        ingredient_names=active_ingredient_names,
        config=config_override or None,
    )
    if not stab_recs:
        st.markdown("✅ Sistema de estabilización completo.")
    else:
        for r in stab_recs:
            prio_color = {"necesario":   "#ef4444",
                          "recomendado": "#fb923c",
                          "opcional":    "#3b82f6"}.get(r.get('priority', 'opcional'), "#3b82f6")
            with st.expander(f"● {r['stabilizer']} — {r['dose_g_per_kg']}"):
                st.markdown(f"**Dosis en receta:** {r['dose_g_recipe']}")
                st.markdown(
                    f"<span style='color:#aaa;font-size:0.82rem;'>{r['reason']}</span>",
                    unsafe_allow_html=True
                )
                if r.get('warning'):
                    st.warning(r['warning'])
                for alt in r.get('alternativas', []):
                    st.markdown(
                        f"<div style='font-size:0.8rem;color:#999;padding:2px 0;'>{alt}</div>",
                        unsafe_allow_html=True
                    )

    # ── EDULCORANTES ──────────────────────────────────────────────────────────
    sw_data = calc.analyze_sweeteners(lines_for_calculator)
    if sw_data:
        _section("🍬 Edulcorantes")
        _sw_html = '<div class="gelato-card">'
        for sw in sw_data:
            if sw.get('warning'):
                _sw_html += (f"<div style='font-size:0.79rem;color:#fb923c;"
                             f"margin-bottom:4px;'>{sw['warning']}</div>")
            _sw_html += (
                f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:6px;"
                f"padding-bottom:6px;border-bottom:1px solid #2d2d44;'>"
                f"<b style='color:#fff;'>{sw['nombre']}</b> · "
                f"POD {sw['pod_contrib']:.0f} ({sw['pct_pod']:.0f}%) · "
                f"PAC {sw['pac_contrib']:.0f} ({sw['pct_pac']:.0f}%) · "
                f"{sw['efecto_sabor']}</div>"
            )
        _sw_html += '</div>'
        st.markdown(_sw_html, unsafe_allow_html=True)

    # ── PROTEÍNAS ─────────────────────────────────────────────────────────────
    if prot_data and prot_data.get('fuentes'):
        _section("💪 Proteínas")
        _prot_html = '<div class="gelato-card">'
        for f in prot_data['fuentes']:
            _prot_html += (
                f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:6px;"
                f"padding-bottom:6px;border-bottom:1px solid #2d2d44;'>"
                f"<b style='color:#fff;'>{f['nombre']}</b> · "
                f"{f.get('proteina_g', 0):.1f} g proteína · "
                f"<span style='color:#555;'>{f.get('tipo','')}</span></div>"
            )
        if prot_data.get('recomendaciones'):
            for s in prot_data['recomendaciones']:
                _prot_html += (f"<div style='font-size:0.78rem;color:#60a5fa;"
                               f"padding-top:4px;'>{s['texto']}</div>")
        _prot_html += '</div>'
        st.markdown(_prot_html, unsafe_allow_html=True)

    # ── EXPORTAR ──────────────────────────────────────────────────────────────
    st.divider()
    st.download_button(
        "⬇️ Descargar ticket de producción (.txt)",
        data=calc.format_production_ticket(
            recipe_name=recipe_name_input,
            product_type=product_type,
            machine=machine,
            ingredient_names=active_ingredient_names,
            lines_for_calculator=lines_for_calculator,
            totals=totals,
            pct=pct,
            derived=derived,
            kcal=kcal,
            protein_data=prot_data,
        ).encode("utf-8"),
        file_name="ticket_produccion.txt",
        mime="text/plain",
        use_container_width=True
    )
