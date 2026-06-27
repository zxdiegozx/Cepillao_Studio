import streamlit as st
import calculator as calc

# Intentar importar la base de datos real
try:
    import database as db
    db.init_db()
    ingredients_raw = db.get_all_ingredients()
except Exception as e:
    st.warning(f"No se pudo conectar a la base de datos: {e}")
    ingredients_raw = [
        {'name': 'Leche entera 3.5%', 'fat': 3.5, 'msnf': 9.0, 'sugars': 4.7,
         'other_st': 0.0, 'pod': 0.10, 'pac': 0.10, 'water': 82.8,
         'price_per_kg': 0, 'calories_per_100g': 0, 'zero_calorie': 0},
        {'name': 'Crema 35% MG', 'fat': 35.0, 'msnf': 6.0, 'sugars': 3.5,
         'other_st': 0.0, 'pod': 0.04, 'pac': 0.04, 'water': 55.5,
         'price_per_kg': 0, 'calories_per_100g': 0, 'zero_calorie': 0},
        {'name': 'Sacarosa', 'fat': 0.0, 'msnf': 0.0, 'sugars': 100.0,
         'other_st': 0.0, 'pod': 1.00, 'pac': 1.00, 'water': 0.0,
         'price_per_kg': 0, 'calories_per_100g': 0, 'zero_calorie': 0},
        {'name': 'Dextrosa monohidrato', 'fat': 0.0, 'msnf': 0.0, 'sugars': 91.0,
         'other_st': 0.0, 'pod': 0.75, 'pac': 1.90, 'water': 9.0,
         'price_per_kg': 0, 'calories_per_100g': 0, 'zero_calorie': 0},
        {'name': 'Agua destilada', 'fat': 0.0, 'msnf': 0.0, 'sugars': 0.0,
         'other_st': 0.0, 'pod': 0.0, 'pac': 0.0, 'water': 100.0,
         'price_per_kg': 0, 'calories_per_100g': 0, 'zero_calorie': 0},
    ]

ingredients_map  = {ing['name']: ing for ing in ingredients_raw}
ingredient_names = list(ingredients_map.keys())

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cepillao' Gelato Studio",
    layout="wide",
    page_icon="🍦"
)

st.markdown("""
<style>
.main { background-color: #13131A; }
div[data-testid="stMetricValue"] { font-size: 22px; font-weight: bold; }
.stExpander { border-left: 3px solid #444; }
</style>
""", unsafe_allow_html=True)

st.title("🍦 Cepillao' Gelato Studio — Formulador Web Pro")
st.caption("Ninja Creami Edition · Diseño balanceado de recetas de heladería artesanal")

# ── Callbacks ─────────────────────────────────────────────────────────────────
def callback_add_row():
    st.session_state.num_rows += 1

def callback_clear_all():
    for key in list(st.session_state.keys()):
        if key.startswith("ing_name_") or key.startswith("grams_") or key.startswith("price_"):
            del st.session_state[key]
    st.session_state.num_rows = 4

if "num_rows" not in st.session_state:
    st.session_state.num_rows = 4

# ── Barra lateral ─────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Parámetros de Mezcla")
product_type = st.sidebar.selectbox(
    "Tipo de Producto",
    ["Helado/Gelato", "Sorbete", "Granita", "Gelato Vegano", "Frozen Yogurt", "Helado Ligero"]
)
machine = st.sidebar.selectbox(
    "Tecnología / Maquinaria",
    ["Ninja Creami Deluxe", "Ninja Creami Standard", "Pacojet", "Mantecadora Tradicional"],
    index=0
)

st.sidebar.divider()
st.sidebar.subheader("📦 Overrun y Producción")
overrun_pct   = st.sidebar.number_input("Overrun (%)", min_value=0, max_value=120,
                                         value=45 if "Creami" in machine else 30, step=5)
target_liters = st.sidebar.number_input("Litros objetivo", min_value=0.1, max_value=50.0,
                                          value=1.0, step=0.5)

# Nombre de contenedor según máquina
if "Creami" in machine:
    cap_g = 640 if "Deluxe" in machine else 430
    contenedor_label = f"Potes Creami {'24oz' if 'Deluxe' in machine else '16oz'}"
else:
    contenedor_label = "Beakers Pacojet"

# ── Layout principal ──────────────────────────────────────────────────────────
col_tabla, col_panel = st.columns([5, 3], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMNA IZQUIERDA — FORMULADOR
# ─────────────────────────────────────────────────────────────────────────────
with col_tabla:
    st.subheader("📝 Tabla de Formulación")

    lines_for_calculator = []
    active_ingredient_names = []

    # Encabezados
    h1, h2, h3 = st.columns([3, 1, 1])
    h1.markdown("**Ingrediente**")
    h2.markdown("**Gramos (g)**")
    h3.markdown("**Precio/kg ($)**")

    for i in range(st.session_state.num_rows):
        c1, c2, c3 = st.columns([3, 1, 1])

        chosen_name = c1.selectbox(
            f"Ingrediente {i}",
            options=["-- Seleccionar ingrediente --"] + ingredient_names,
            key=f"ing_name_{i}",
            label_visibility="collapsed"
        )

        grams = c2.number_input(
            f"Gramos {i}", min_value=0.0, value=0.0, step=5.0,
            key=f"grams_{i}", label_visibility="collapsed"
        )

        # Precio: se muestra el de la BD si existe, pero es editable
        default_price = 0.0
        if chosen_name != "-- Seleccionar ingrediente --":
            ing_data = ingredients_map.get(chosen_name, {})
            default_price = float(ing_data.get('price_per_kg', 0) or 0)

        price = c3.number_input(
            f"Precio {i}", min_value=0.0, value=default_price, step=0.5,
            key=f"price_{i}", label_visibility="collapsed"
        )

        if chosen_name != "-- Seleccionar ingrediente --" and grams > 0:
            ing_dict = ingredients_map[chosen_name]
            lines_for_calculator.append((ing_dict, grams, price))
            active_ingredient_names.append(chosen_name)

    st.write("")
    btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 4])
    btn_col1.button("➕ Añadir Ingrediente", use_container_width=True, on_click=callback_add_row)
    btn_col2.button("🗑️ Limpiar Todo",       use_container_width=True, on_click=callback_clear_all)

    # Contador de ingredientes activos
    if active_ingredient_names:
        st.caption(f"🧮 {len(active_ingredient_names)} ingredientes activos")

    # ── Panel de Edulcorantes ─────────────────────────────────────────────────
    if lines_for_calculator:
        st.divider()
        st.subheader("🍬 Panel de Edulcorantes")
        sweet_data = calc.analyze_sweeteners(lines_for_calculator)

        if sweet_data:
            # Tabla de edulcorantes
            for s in sweet_data:
                with st.expander(f"**{s['nombre']}** — {s['gramos']:.1f} g"):
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("POD aportado",  f"{s['pod_contrib']:.1f}",
                                 f"{s['pct_pod']:.1f}% del total")
                    col_b.metric("PAC aportado",  f"{s['pac_contrib']:.1f}",
                                 f"{s['pct_pac']:.1f}% del total")
                    col_c.metric("kcal estimadas", f"{s['kcal_estimadas']:.1f} kcal")
                    st.write(f"**Perfil de sabor:** {s['efecto_sabor']}")
                    st.write(f"**Tipo de dulzor:** {s['perfil_dulzor']}")
                    if s['warning']:
                        st.warning(s['warning'])
        else:
            st.info("No se detectan edulcorantes significativos en la receta actual.")

        # ── Recomendaciones de estabilizantes ────────────────────────────────
        st.divider()
        st.subheader("🧪 Recomendaciones de Estabilizantes")
        totals_tmp = calc.calc_totals(lines_for_calculator)
        pct_tmp    = calc.calc_percentages(totals_tmp)
        stab_recs  = calc.recommend_stabilizers(
            totals_tmp, pct_tmp, product_type, machine, active_ingredient_names
        )

        if stab_recs:
            for rec in stab_recs:
                icon = "🔴" if rec['priority'] == 'necesario' else \
                       "🟡" if rec['priority'] == 'recomendado' else "🔵"
                with st.expander(f"{icon} **{rec['stabilizer']}** — {rec['dose_g_recipe']}"):
                    st.write(f"**Dosis por kg:** {rec['dose_g_per_kg']}")
                    st.write(f"**Razón técnica:** {rec['reason']}")
                    if rec.get('warning'):
                        st.warning(rec['warning'])
        else:
            st.success("✅ No se necesitan estabilizantes adicionales para esta formulación.")


# ─────────────────────────────────────────────────────────────────────────────
# COLUMNA DERECHA — PANEL ANALÍTICO
# ─────────────────────────────────────────────────────────────────────────────
with col_panel:
    st.subheader("📊 Resumen Analítico")

    if lines_for_calculator:
        totals  = calc.calc_totals(lines_for_calculator)
        pct     = calc.calc_percentages(totals)
        derived = calc.calc_derived(totals, pct,
                                    product_type=product_type, machine=machine)
        kcal    = calc.calc_calories(totals)

        # ── Métricas principales ──────────────────────────────────────────────
        m1, m2 = st.columns(2)
        m1.metric("Masa Total",      f"{totals['grams']:.1f} g")
        m2.metric("Coste Estimado",  f"${totals['cost']:.2f}")

        # Indicador de llenado del pote Creami
        if "Creami" in machine:
            cap_pote = 640 if "Deluxe" in machine else 430
            masa     = totals['grams']
            pct_pote = min(masa / cap_pote * 100, 110)

            if 540 <= masa <= cap_pote:
                fill_color, fill_msg = "normal", f"✅ Perfecto ({masa:.0f} g / {cap_pote} g)"
            elif masa > cap_pote:
                fill_color, fill_msg = "inverse", f"⚠️ Excede {masa - cap_pote:.0f} g el pote"
            else:
                fill_color, fill_msg = "off",  f"⚠️ Pote poco lleno ({masa:.0f} g / {cap_pote} g)"

            st.progress(min(int(pct_pote), 100), text=fill_msg)

        # ── Calorías ──────────────────────────────────────────────────────────
        st.write("### 🔥 Calorías estimadas")
        c1k, c2k, c3k = st.columns(3)
        c1k.metric("/ 100 g",      f"{kcal['kcal_per_100g']:.0f} kcal")
        c2k.metric("/ porción 120g", f"{kcal['kcal_per_100g'] * 1.2:.0f} kcal")
        if "Creami" in machine:
            c3k.metric("/ pote completo", f"{kcal['kcal_per_pote_deluxe']:.0f} kcal")
        else:
            c3k.metric("Total receta", f"{kcal['kcal_total']:.0f} kcal")

        # ── Composición centesimal ────────────────────────────────────────────
        st.write("### 🧪 Composición Centesimal")

        targets = derived.get('targets', {})

        def display_parameter(label, val, status_key, unit="%"):
            status = derived['status'].get(status_key, 'ok')
            badge  = "🔺" if status == 'high' else "🔻" if status == 'low' else "✅"
            tgt    = targets.get(status_key)
            tgt_str = f"  _(objetivo {tgt[0]}-{tgt[1]}{unit})_" if tgt else ""
            st.write(f"- **{label}:** {val:.1f}{unit} {badge}{tgt_str}")

        display_parameter("Sólidos Totales (ST)",      pct.get('st_pct',    0), 'st')
        display_parameter("Grasa",                     pct.get('fat_pct',   0), 'fat')
        display_parameter("MSNF / ESGL",               pct.get('msnf_pct',  0), 'msnf')
        display_parameter("Azúcares",                  pct.get('sugars_pct',0), 'sugars')
        display_parameter("Agua libre",                pct.get('water_pct', 0), 'water')
        display_parameter("POD",  pct.get('pod_total', 0), 'pod', "")
        display_parameter("PAC",  pct.get('pac_total', 0), 'pac', "")

        # Ratio ST/Agua
        stw = derived.get('ratio_st_water', 0)
        stw_status = derived['status'].get('st_water', 'ok')
        stw_badge  = "🔺" if stw_status == 'high' else "🔻" if stw_status == 'low' else "✅"
        st.write(f"- **Ratio ST/Agua:** {stw:.3f} {stw_badge}")

        # ── Crioscopía ────────────────────────────────────────────────────────
        st.write("### ❄️ Crioscopía")
        delta_t = derived.get('delta_t', 0)
        st.info(f"**ΔT estimado:** {delta_t:.2f} °C")

        if "Creami" in machine:
            congela = derived.get('congela_ok', False)
            if congela:
                st.success("✅ Congela correctamente a −18 °C")
            else:
                st.warning("⚠️ ΔT insuficiente — puede no solidificar bien a −18 °C. "
                           "Añade dextrosa o alulosa para elevar el PAC.")

        # Temperatura de servicio
        temp_srv = derived.get('temp_servicio', '')
        if temp_srv:
            st.caption(f"🌡️ {temp_srv}")

        # ── Overrun ───────────────────────────────────────────────────────────
        st.write("### 📐 Overrun")
        or_data = calc.overrun_calc(totals['grams'], overrun_pct, target_liters, machine)

        if "Creami" in machine:
            o1, o2 = st.columns(2)
            o1.metric(contenedor_label,     f"{or_data['potes_total']:.1f}")
            o2.metric("Masa / pote",        f"{or_data['masa_por_pote_g']:.0f} g")
            resto = or_data.get('masa_ultimo_pote_g', 0)
            if resto > 10:
                st.caption(f"🫙 Último pote parcial: {resto:.0f} g")
        else:
            o1, o2 = st.columns(2)
            o1.metric("Beakers",            f"{or_data['pacojet_beakers']}")
            o2.metric("Mix/beaker",         f"{or_data['mix_per_beaker']:.0f} g")

        o3, o4 = st.columns(2)
        o3.metric("Base necesaria",         f"{or_data['base_needed_g']:.0f} g")
        o4.metric("Litros producidos",      f"{or_data['liters_from_base']:.2f} L")

        # ── Diagnósticos ──────────────────────────────────────────────────────
        st.write("### 🚨 Alertas y Diagnósticos")
        diagnostics = derived.get('diagnostics', [])

        # Filtrar el hint informativo de overrun si no hay más diagnósticos
        real_diags = [d for d in diagnostics if d['priority'] != 'adjustable'
                      or d['key'] != 'creami_overrun_hint']
        hint_overrun = next((d for d in diagnostics
                             if d['key'] == 'creami_overrun_hint'), None)

        if not real_diags:
            st.success("🎉 ¡Mezcla perfectamente balanceada!")
        else:
            for diag in diagnostics:
                icon = "🔴" if diag['priority'] == 'critical' else \
                       "🟡" if diag['priority'] == 'important' else "🔵"
                with st.expander(f"{icon} {diag['title']}"):
                    st.write(diag['tip'])

        # ── Exportar receta ───────────────────────────────────────────────────
        st.divider()
        st.write("### 📋 Exportar Ticket de Producción")

        def generar_ticket():
            from datetime import datetime
            lines_txt = "\n".join(
                f"  {ingredients_map[n]['name'] if n in ingredients_map else n:<35} "
                f"{g:>7.1f} g"
                for (_, g, _), n in zip(lines_for_calculator, active_ingredient_names)
            )
            ing_lines_raw = []
            for i in range(st.session_state.num_rows):
                nom = st.session_state.get(f"ing_name_{i}", "")
                gr  = st.session_state.get(f"grams_{i}", 0)
                if nom and nom != "-- Seleccionar ingrediente --" and gr > 0:
                    ing_lines_raw.append(f"  {nom:<35} {gr:>7.1f} g")
            lines_txt = "\n".join(ing_lines_raw)

            status_sym = lambda k: "✅" if derived['status'].get(k) == 'ok' else \
                                   "🔺" if derived['status'].get(k) == 'high' else \
                                   "🔻" if derived['status'].get(k) == 'low' else "—"

            instrucciones = ""
            if "Creami" in machine:
                instrucciones = (
                    "INSTRUCCIONES NINJA CREAMI:\n"
                    "  → Congelar 24 h a −18 °C mínimo\n"
                    "  → Procesar función \"Ice Cream\" (o \"Lite Ice Cream\" para ST bajo)\n"
                    "  → Si granuloso: respin sin añadir líquido\n"
                    "  → Si muy duro: templar 3-5 min y reintentar"
                )
            elif "Pacojet" in machine:
                instrucciones = (
                    "INSTRUCCIONES PACOJET:\n"
                    "  → Verter en beaker, tapar y congelar 24 h a −22 °C\n"
                    "  → Pacotizar sin descongelar\n"
                    "  → Servir inmediatamente o mantener a −14 °C"
                )

            ticket = f"""
══════════════════════════════════════════════
🧊  CEPILLAO' GELATO STUDIO — TICKET DE PRODUCCIÓN
══════════════════════════════════════════════
Tipo:      {product_type}
Máquina:   {machine}
Fecha:     {datetime.now().strftime('%d/%m/%Y  %H:%M')}

INGREDIENTES:
{lines_txt}

PARÁMETROS:
  Masa total:      {totals['grams']:.1f} g
  ST:              {pct.get('st_pct', 0):.1f}%    {status_sym('st')}
  Grasa:           {pct.get('fat_pct', 0):.1f}%    {status_sym('fat')}
  MSNF:            {pct.get('msnf_pct', 0):.1f}%    {status_sym('msnf')}
  Azúcares:        {pct.get('sugars_pct', 0):.1f}%    {status_sym('sugars')}
  Agua libre:      {pct.get('water_pct', 0):.1f}%    {status_sym('water')}
  POD:             {pct.get('pod_total', 0):.0f}       {status_sym('pod')}
  PAC:             {pct.get('pac_total', 0):.0f}       {status_sym('pac')}
  Ratio ST/Agua:   {derived.get('ratio_st_water', 0):.3f}
  ΔT crioscopía:   {derived.get('delta_t', 0):.2f} °C
  Calorías/100 g:  {kcal['kcal_per_100g']:.0f} kcal
  Coste estimado:  ${totals['cost']:.2f}

{instrucciones}
══════════════════════════════════════════════"""
            return ticket

        ticket_txt = generar_ticket()
        st.download_button(
            "⬇️ Descargar Ticket (.txt)",
            data=ticket_txt.encode('utf-8'),
            file_name="ticket_produccion.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:
        st.info("👋 Selecciona ingredientes y asígnales gramos en la tabla izquierda "
                "para comenzar el análisis automático.")

        # Mostrar guía rápida de rangos según máquina seleccionada
        st.write("### 📖 Rangos de referencia")
        if "Creami" in machine:
            st.markdown("""
| Parámetro | Rango Ninja Creami |
|-----------|-------------------|
| ST %      | 28 – 38 %         |
| Grasa %   | 4 – 15 %          |
| MSNF %    | 5 – 10 %          |
| Azúcares % | 13 – 22 %        |
| POD       | 125 – 200         |
| PAC       | 120 – 260         |
| Agua libre | 50 – 72 %        |
| ΔT mínimo | < −1.5 °C         |
""")
        elif "Pacojet" in machine:
            st.markdown("""
| Parámetro | Rango Pacojet |
|-----------|--------------|
| ST %      | 34 – 42 %    |
| Grasa %   | 4 – 20 %     |
| MSNF %    | 6 – 11 %     |
| Azúcares % | 13 – 24 %   |
| POD       | 130 – 210    |
| PAC       | 200 – 420    |
""")
