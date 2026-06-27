import streamlit as st
import calculator as calc

# ── Base de datos ──────────────────────────────────────────────────────────────
try:
    import database as db
    db.init_db()
    ingredients_raw = db.get_all_ingredients()
    DB_OK = True
except Exception as e:
    st.error(f"⚠️ Error de base de datos: {e}")
    ingredients_raw = []
    DB_OK = False

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
div[data-testid="stMetricValue"] { font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🍦 Cepillao' Gelato Studio")
st.caption("Ninja Creami Edition · Formulador artesanal de helados")

# ── Inicialización de session_state ───────────────────────────────────────────
if "num_rows" not in st.session_state:
    st.session_state.num_rows = 4

# Pre-inicializar keys de widgets para evitar el warning de value conflict
for _i in range(st.session_state.num_rows):
    if f"grams_{_i}" not in st.session_state:
        st.session_state[f"grams_{_i}"] = 0.0
    if f"price_{_i}" not in st.session_state:
        st.session_state[f"price_{_i}"] = 0.0
    if f"ing_name_{_i}" not in st.session_state:
        st.session_state[f"ing_name_{_i}"] = "-- Seleccionar ingrediente --"

# ── Callbacks (fuera de cualquier bloque with para no redefinirse) ─────────────
def callback_add_row():
    new_i = st.session_state.num_rows
    st.session_state[f"grams_{new_i}"]    = 0.0
    st.session_state[f"price_{new_i}"]    = 0.0
    st.session_state[f"ing_name_{new_i}"] = "-- Seleccionar ingrediente --"
    st.session_state.num_rows += 1

def callback_clear_all():
    for key in list(st.session_state.keys()):
        if key.startswith(("ing_name_", "grams_", "price_")):
            del st.session_state[key]
    st.session_state.num_rows = 4
    st.session_state.pop("recipe_loaded_id", None)
    st.session_state.pop("recipe_loaded_name", None)
    # Re-inicializar las 4 filas vacías
    for _i in range(4):
        st.session_state[f"grams_{_i}"]    = 0.0
        st.session_state[f"price_{_i}"]    = 0.0
        st.session_state[f"ing_name_{_i}"] = "-- Seleccionar ingrediente --"

def guardar_receta():
    """Callback del botón Guardar — lee session_state directamente."""
    nombre = st.session_state.get("_recipe_name_input", "").strip()
    if not nombre:
        st.session_state["_save_error"] = "Escribe un nombre para la receta."
        return
    lines = []
    for i in range(st.session_state.num_rows):
        nom = st.session_state.get(f"ing_name_{i}", "")
        gr  = st.session_state.get(f"grams_{i}", 0.0)
        pr  = st.session_state.get(f"price_{i}", 0.0)
        if nom and nom != "-- Seleccionar ingrediente --" and gr > 0:
            lines.append({"ingredient_name": nom, "grams": gr, "price_per_kg": pr})
    if not lines:
        st.session_state["_save_error"] = "Añade al menos un ingrediente con gramos."
        return
    data = {
        "name":         nombre,
        "product_type": st.session_state.get("_product_type", "Helado/Gelato"),
        "machine":      st.session_state.get("_machine", "Ninja Creami Deluxe"),
        "base_grams":   sum(l["grams"] for l in lines),
        "notes":        "",
        "tasting_notes":"",
        "lines":        lines,
    }
    if st.session_state.get("recipe_loaded_id"):
        data["id"] = st.session_state["recipe_loaded_id"]
    rec_id = db.save_recipe(data)
    st.session_state["recipe_loaded_id"]   = rec_id
    st.session_state["recipe_loaded_name"] = nombre
    st.session_state["_save_error"]        = None
    st.session_state["_save_ok"]           = f"✅ Receta «{nombre}» guardada."

# ── Helpers de visualización (definidos una vez, fuera de loops) ──────────────
def show_param(label, val, key, derived, targets, unit="%"):
    s   = derived["status"].get(key, "ok")
    b   = "🔺" if s == "high" else "🔻" if s == "low" else "✅"
    tgt = targets.get(key)
    rng = f" _(obj {tgt[0]}-{tgt[1]}{unit})_" if tgt else ""
    st.write(f"- **{label}:** {val:.1f}{unit} {b}{rng}")

def generar_ticket(recipe_name, product_type, machine,
                   lines_for_calculator, active_ingredient_names,
                   totals, pct, derived, kcal):
    from datetime import datetime
    ing_lines = "\n".join(
        f"  {n:<38} {g:>7.1f} g"
        for (_, g, _), n in zip(lines_for_calculator, active_ingredient_names)
    )
    sym = lambda k: "✅" if derived["status"].get(k) == "ok" else \
                    "🔺" if derived["status"].get(k) == "high" else "🔻"
    inst = ""
    if "Creami" in machine:
        inst = ("INSTRUCCIONES NINJA CREAMI:\n"
                "  → Congelar 24 h a −18 °C mínimo\n"
                "  → Procesar función \"Ice Cream\"\n"
                "  → Si granuloso: respin sin añadir líquido\n"
                "  → Si muy duro: templar 3-5 min y reintentar")
    elif "Pacojet" in machine:
        inst = ("INSTRUCCIONES PACOJET:\n"
                "  → Verter en beaker, congelar 24 h a −22 °C\n"
                "  → Pacotizar sin descongelar")
    return f"""
══════════════════════════════════════════════
🧊  CEPILLAO' GELATO STUDIO — TICKET DE PRODUCCIÓN
══════════════════════════════════════════════
Receta:    {recipe_name or '—'}
Tipo:      {product_type}
Máquina:   {machine}
Fecha:     {datetime.now().strftime('%d/%m/%Y  %H:%M')}

INGREDIENTES:
{ing_lines}

PARÁMETROS:
  Masa total:     {totals['grams']:.1f} g
  ST:             {pct.get('st_pct', 0):.1f}%   {sym('st')}
  Grasa:          {pct.get('fat_pct', 0):.1f}%   {sym('fat')}
  MSNF:           {pct.get('msnf_pct', 0):.1f}%   {sym('msnf')}
  Azúcares:       {pct.get('sugars_pct', 0):.1f}%   {sym('sugars')}
  Agua libre:     {pct.get('water_pct', 0):.1f}%   {sym('water')}
  POD:            {pct.get('pod_total', 0):.0f}      {sym('pod')}
  PAC:            {pct.get('pac_total', 0):.0f}      {sym('pac')}
  ΔT crioscopía:  {derived.get('delta_t', 0):.2f} °C
  kcal / 100 g:   {kcal['kcal_per_100g']:.0f} kcal
  Costo estimado: ${totals['cost']:.2f}

{inst}
══════════════════════════════════════════════"""


# ── Tabs principales ──────────────────────────────────────────────────────────
tab_form, tab_recetas, tab_ingredientes = st.tabs([
    "🧪 Formulador",
    "📁 Mis Recetas",
    "🗄️ Ingredientes"
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULADOR
# ═════════════════════════════════════════════════════════════════════════════
with tab_form:

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.header("⚙️ Parámetros")

    recipe_name_input = st.sidebar.text_input(
        "Nombre de la receta",
        value=st.session_state.get("recipe_loaded_name", ""),
        placeholder="Ej: Choco Creami v3",
        key="_recipe_name_input"
    )
    product_type = st.sidebar.selectbox(
        "Tipo de Producto",
        ["Helado/Gelato", "Sorbete", "Granita", "Gelato Vegano", "Frozen Yogurt", "Helado Ligero"],
        key="_product_type"
    )
    machine = st.sidebar.selectbox(
        "Maquinaria",
        ["Ninja Creami Deluxe", "Ninja Creami Standard", "Pacojet", "Mantecadora Tradicional"],
        index=0,
        key="_machine"
    )
    overrun_pct   = st.sidebar.number_input(
        "Overrun (%)", 0, 120,
        45 if "Creami" in st.session_state.get("_machine", "Ninja Creami Deluxe") else 30,
        step=5
    )
    target_liters = st.sidebar.number_input("Litros objetivo", 0.1, 50.0, 1.0, step=0.5)

    st.sidebar.divider()
    st.sidebar.button("💾 Guardar receta", use_container_width=True, on_click=guardar_receta)

    # Mostrar mensajes de guardado
    if st.session_state.get("_save_ok"):
        st.sidebar.success(st.session_state.pop("_save_ok"))
    if st.session_state.get("_save_error"):
        st.sidebar.error(st.session_state.pop("_save_error"))

    # ── Layout formulador ──────────────────────────────────────────────────────
    col_tabla, col_panel = st.columns([5, 3], gap="large")

    with col_tabla:
        if st.session_state.get("recipe_loaded_name"):
            st.info(f"✏️ Editando: **{st.session_state['recipe_loaded_name']}**")

        st.subheader("📝 Tabla de Formulación")

        lines_for_calculator    = []
        active_ingredient_names = []

        h1, h2, h3 = st.columns([3, 1, 1])
        h1.markdown("**Ingrediente**")
        h2.markdown("**Gramos (g)**")
        h3.markdown("**Precio/kg ($)**")

        opts = ["-- Seleccionar ingrediente --"] + ingredient_names

        for i in range(st.session_state.num_rows):
            c1, c2, c3 = st.columns([3, 1, 1])

            # Selectbox: sin value= → usa session_state directamente
            chosen_name = c1.selectbox(
                f"Ingrediente {i}",
                options=opts,
                key=f"ing_name_{i}",
                label_visibility="collapsed"
            )

            # number_input: sin value= → usa session_state (ya inicializado arriba)
            grams = c2.number_input(
                f"Gramos {i}", min_value=0.0, step=5.0,
                key=f"grams_{i}", label_visibility="collapsed"
            )

            # Precio: si el ingrediente tiene precio en BD y el campo está a 0, sugerirlo
            if (chosen_name != "-- Seleccionar ingrediente --"
                    and st.session_state.get(f"price_{i}", 0.0) == 0.0):
                bd_price = float(ingredients_map.get(chosen_name, {}).get("price_per_kg", 0) or 0)
                if bd_price > 0:
                    st.session_state[f"price_{i}"] = bd_price

            price = c3.number_input(
                f"Precio {i}", min_value=0.0, step=0.5,
                key=f"price_{i}", label_visibility="collapsed"
            )

            if chosen_name != "-- Seleccionar ingrediente --" and grams > 0:
                lines_for_calculator.append((ingredients_map[chosen_name], grams, price))
                active_ingredient_names.append(chosen_name)

        st.write("")
        b1, b2, _ = st.columns([1.5, 1.5, 4])
        b1.button("➕ Añadir fila",  use_container_width=True, on_click=callback_add_row)
        b2.button("🗑️ Limpiar todo", use_container_width=True, on_click=callback_clear_all)

        if active_ingredient_names:
            st.caption(f"🧮 {len(active_ingredient_names)} ingredientes activos")

        # ── Secciones adicionales (solo si hay ingredientes) ──────────────────
        if lines_for_calculator:
            # Calcular UNA SOLA VEZ — se reutiliza en panel derecho y aquí
            totals  = calc.calc_totals(lines_for_calculator)
            pct     = calc.calc_percentages(totals)

            # Panel de Edulcorantes
            st.divider()
            st.subheader("🍬 Edulcorantes")
            sweet_data = calc.analyze_sweeteners(lines_for_calculator)
            if sweet_data:
                for s in sweet_data:
                    with st.expander(f"**{s['nombre']}** — {s['gramos']:.1f} g"):
                        ca, cb, cc = st.columns(3)
                        ca.metric("POD", f"{s['pod_contrib']:.1f}", f"{s['pct_pod']:.0f}% total")
                        cb.metric("PAC", f"{s['pac_contrib']:.1f}", f"{s['pct_pac']:.0f}% total")
                        cc.metric("kcal", f"{s['kcal_estimadas']:.0f}")
                        st.caption(f"Sabor: {s['efecto_sabor']} · Dulzor: {s['perfil_dulzor']}")
                        if s["warning"]:
                            st.warning(s["warning"])
            else:
                st.info("No se detectan edulcorantes significativos.")

            # Recomendaciones de estabilizantes
            st.divider()
            st.subheader("🧪 Estabilizantes")
            stab_recs = calc.recommend_stabilizers(
                totals, pct, product_type, machine, active_ingredient_names
            )
            if stab_recs:
                for rec in stab_recs:
                    icon = "🔴" if rec["priority"] == "necesario" else \
                           "🟡" if rec["priority"] == "recomendado" else "🔵"
                    with st.expander(f"{icon} **{rec['stabilizer']}** — {rec['dose_g_recipe']}"):
                        st.write(f"**Dosis/kg:** {rec['dose_g_per_kg']}")
                        st.write(rec["reason"])
                        if rec.get("warning"):
                            st.warning(rec["warning"])
            else:
                st.success("✅ Sin estabilizantes adicionales necesarios.")

    # ── Panel analítico derecho ───────────────────────────────────────────────
    with col_panel:
        st.subheader("📊 Análisis")

        if not lines_for_calculator:
            st.info("👋 Selecciona ingredientes y gramos para ver el análisis.")
            if "Creami" in machine:
                st.markdown("""
| Parámetro | Ninja Creami |
|-----------|-------------|
| ST % | 28 – 38 % |
| Grasa % | 4 – 15 % |
| MSNF % | 5 – 10 % |
| Azúcares % | 13 – 22 % |
| POD | 125 – 200 |
| PAC | 120 – 260 |
| Agua libre | 50 – 72 % |
""")
        else:
            # totals y pct ya calculados en col_tabla — reutilizar
            derived = calc.calc_derived(totals, pct, product_type=product_type, machine=machine)
            kcal    = calc.calc_calories(totals)

            # Métricas principales
            m1, m2 = st.columns(2)
            m1.metric("Masa total", f"{totals['grams']:.1f} g")
            m2.metric("Costo est.", f"${totals['cost']:.2f}")

            # Llenado del pote Creami
            if "Creami" in machine:
                cap  = 640 if "Deluxe" in machine else 430
                masa = totals["grams"]
                if 540 <= masa <= cap:
                    msg = f"✅ Perfecto ({masa:.0f} g / {cap} g)"
                elif masa > cap:
                    msg = f"⚠️ Excede {masa - cap:.0f} g el pote"
                else:
                    msg = f"⚠️ Pote poco lleno ({masa:.0f} g / {cap} g)"
                st.progress(min(int(masa / cap * 100), 100), text=msg)

            # Calorías
            st.write("### 🔥 Calorías")
            k1, k2 = st.columns(2)
            k1.metric("/ 100 g",        f"{kcal['kcal_per_100g']:.0f} kcal")
            k2.metric("/ porción 120 g", f"{kcal['kcal_per_100g'] * 1.2:.0f} kcal")
            if "Creami" in machine:
                st.caption(f"Pote completo: **{kcal['kcal_per_pote_deluxe']:.0f} kcal**")

            # Composición
            st.write("### 🧪 Composición")
            targets = derived.get("targets", {})
            show_param("ST",        pct.get("st_pct",    0), "st",     derived, targets)
            show_param("Grasa",     pct.get("fat_pct",   0), "fat",    derived, targets)
            show_param("MSNF",      pct.get("msnf_pct",  0), "msnf",   derived, targets)
            show_param("Azúcares",  pct.get("sugars_pct",0), "sugars", derived, targets)
            show_param("Agua libre",pct.get("water_pct", 0), "water",  derived, targets)

            pod_v = pct.get("pod_total", 0)
            pac_v = pct.get("pac_total", 0)
            pod_s = derived["status"].get("pod", "ok")
            pac_s = derived["status"].get("pac", "ok")
            st.write(f"- **POD:** {pod_v:.0f} {'✅' if pod_s=='ok' else '🔺' if pod_s=='high' else '🔻'}")
            st.write(f"- **PAC:** {pac_v:.0f} {'✅' if pac_s=='ok' else '🔺' if pac_s=='high' else '🔻'}")
            st.write(f"- **ST/Agua:** {derived.get('ratio_st_water', 0):.3f}")

            # Crioscopía
            st.write("### ❄️ Crioscopía")
            dt = derived.get("delta_t", 0)
            st.info(f"**ΔT:** {dt:.2f} °C")
            if "Creami" in machine:
                if derived.get("congela_ok"):
                    st.success("✅ Congela correctamente a −18 °C")
                else:
                    st.warning("⚠️ ΔT insuficiente a −18 °C — sube el PAC")
            ts = derived.get("temp_servicio", "")
            if ts:
                st.caption(f"🌡️ {ts}")

            # Overrun
            st.write("### 📐 Overrun")
            or_d = calc.overrun_calc(totals["grams"], overrun_pct, target_liters, machine)
            if "Creami" in machine:
                cap_label = "24oz" if "Deluxe" in machine else "16oz"
                o1, o2 = st.columns(2)
                o1.metric(f"Potes Creami {cap_label}", f"{or_d['potes_total']:.1f}")
                o2.metric("Masa/pote",                  f"{or_d['masa_por_pote_g']:.0f} g")
                if or_d.get("masa_ultimo_pote_g", 0) > 10:
                    st.caption(f"🫙 Último pote: {or_d['masa_ultimo_pote_g']:.0f} g")
            else:
                o1, o2 = st.columns(2)
                o1.metric("Beakers",    f"{or_d['pacojet_beakers']}")
                o2.metric("Mix/beaker", f"{or_d['mix_per_beaker']:.0f} g")
            o3, o4 = st.columns(2)
            o3.metric("Base necesaria",   f"{or_d['base_needed_g']:.0f} g")
            o4.metric("Litros producidos", f"{or_d['liters_from_base']:.2f} L")

            # Diagnósticos
            st.write("### 🚨 Diagnósticos")
            diags_visibles = [d for d in derived.get("diagnostics", [])
                              if d["key"] != "creami_overrun_hint"]
            if not diags_visibles:
                st.success("🎉 ¡Mezcla perfectamente balanceada!")
            else:
                for d in derived.get("diagnostics", []):
                    icon = "🔴" if d["priority"] == "critical" else \
                           "🟡" if d["priority"] == "important" else "🔵"
                    with st.expander(f"{icon} {d['title']}"):
                        st.write(d["tip"])

            # Ticket de producción
            st.divider()
            ticket = generar_ticket(
                recipe_name_input, product_type, machine,
                lines_for_calculator, active_ingredient_names,
                totals, pct, derived, kcal
            )
            st.download_button(
                "⬇️ Descargar ticket (.txt)",
                data=ticket.encode("utf-8"),
                file_name="ticket_produccion.txt",
                mime="text/plain",
                use_container_width=True
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — MIS RECETAS
# ═════════════════════════════════════════════════════════════════════════════
with tab_recetas:
    st.subheader("📁 Mis Recetas Guardadas")

    if not DB_OK:
        st.error("Base de datos no disponible.")
    else:
        try:
            all_recipes = db.get_all_recipes()
        except Exception as e:
            st.error(f"Error cargando recetas: {e}")
            all_recipes = []

        if not all_recipes:
            st.info("Aún no tienes recetas guardadas. Formula una en 🧪 y guárdala desde el sidebar.")
        else:
            search = st.text_input("🔍 Buscar receta", placeholder="Escribe parte del nombre...")
            if search:
                all_recipes = [r for r in all_recipes if search.lower() in r["name"].lower()]

            for rec in all_recipes:
                with st.expander(f"**{rec['name']}** — {rec['product_type']} · {rec['machine']}"):
                    col_info, col_actions = st.columns([3, 1])

                    with col_info:
                        st.caption(f"Guardada: {rec.get('updated_at', '')[:16]}")
                        st.write(f"**Base:** {rec.get('base_grams', 0):.0f} g")
                        if rec.get("notes"):
                            st.write(f"**Notas:** {rec['notes']}")

                    with col_actions:
                        if st.button("📂 Cargar", key=f"load_{rec['id']}", use_container_width=True):
                            full = db.get_recipe(rec["id"])
                            if full:
                                lines = full.get("lines", [])
                                # Limpiar estado actual
                                for key in list(st.session_state.keys()):
                                    if key.startswith(("ing_name_", "grams_", "price_")):
                                        del st.session_state[key]
                                st.session_state.num_rows = max(len(lines), 4)
                                # Cargar líneas — inicializa primero las vacías
                                for i in range(st.session_state.num_rows):
                                    if i < len(lines):
                                        line = lines[i]
                                        st.session_state[f"ing_name_{i}"] = line["ingredient_name"]
                                        st.session_state[f"grams_{i}"]    = float(line["grams"])
                                        st.session_state[f"price_{i}"]    = float(line.get("price_per_kg", 0))
                                    else:
                                        st.session_state[f"ing_name_{i}"] = "-- Seleccionar ingrediente --"
                                        st.session_state[f"grams_{i}"]    = 0.0
                                        st.session_state[f"price_{i}"]    = 0.0
                                st.session_state["recipe_loaded_id"]   = rec["id"]
                                st.session_state["recipe_loaded_name"] = rec["name"]
                                st.rerun()

                        if st.button("🗑️ Eliminar", key=f"del_{rec['id']}", use_container_width=True):
                            db.delete_recipe(rec["id"])
                            st.warning(f"Receta «{rec['name']}» eliminada.")
                            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — GESTIÓN DE INGREDIENTES
# ═════════════════════════════════════════════════════════════════════════════
with tab_ingredientes:
    st.subheader("🗄️ Base de Datos de Ingredientes")

    if not DB_OK:
        st.error("Base de datos no disponible.")
    else:
        sub_ver, sub_nuevo = st.tabs(["📋 Ver / Editar", "➕ Nuevo ingrediente"])

        with sub_ver:
            try:
                all_ings = db.get_all_ingredients()
            except Exception as e:
                st.error(f"Error: {e}")
                all_ings = []

            col_search, col_cat = st.columns([2, 1])
            search_ing = col_search.text_input("🔍 Buscar ingrediente", key="search_ing",
                                               placeholder="Nombre o categoría...")
            cats       = sorted(set(i["category"] for i in all_ings))
            cat_filter = col_cat.selectbox("Categoría", ["Todas"] + cats, key="cat_filter")

            filtered = all_ings
            if search_ing:
                filtered = [i for i in filtered
                            if search_ing.lower() in i["name"].lower()
                            or search_ing.lower() in i["category"].lower()]
            if cat_filter != "Todas":
                filtered = [i for i in filtered if i["category"] == cat_filter]

            st.caption(f"{len(filtered)} de {len(all_ings)} ingredientes")

            for ing in filtered:
                with st.expander(f"**{ing['name']}** — _{ing['category']}_"):
                    col_datos, col_edit = st.columns([2, 1])

                    with col_datos:
                        st.write(
                            f"Grasa: **{ing['fat']}%** | MSNF: **{ing['msnf']}%** | "
                            f"Azúcares: **{ing['sugars']}%** | Agua: **{ing['water']}%**"
                        )
                        st.write(
                            f"POD: **{ing['pod']}** | PAC: **{ing['pac']}** | "
                            f"Otros ST: **{ing['other_st']}%**"
                        )
                        if ing.get("price_per_kg", 0):
                            st.write(f"Precio: **${ing['price_per_kg']:.2f}/kg**")
                        if ing.get("notes"):
                            st.caption(ing["notes"])

                    with col_edit:
                        edit_key = f"edit_open_{ing['id']}"
                        if st.button("✏️ Editar", key=f"btn_edit_{ing['id']}",
                                     use_container_width=True):
                            st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                        if st.button("🗑️ Eliminar", key=f"btn_del_ing_{ing['id']}",
                                     use_container_width=True):
                            db.delete_ingredient(ing["id"])
                            st.warning(f"«{ing['name']}» eliminado.")
                            st.rerun()

                    if st.session_state.get(edit_key, False):
                        st.divider()
                        with st.form(key=f"form_edit_{ing['id']}"):
                            st.write("**Editar ingrediente**")
                            e_name  = st.text_input("Nombre",    value=ing["name"])
                            e_cat   = st.text_input("Categoría", value=ing["category"])
                            c1e, c2e, c3e, c4e = st.columns(4)
                            e_fat   = c1e.number_input("Grasa %",    value=float(ing["fat"]      or 0), step=0.1)
                            e_msnf  = c2e.number_input("MSNF %",     value=float(ing["msnf"]     or 0), step=0.1)
                            e_sug   = c3e.number_input("Azúcares %", value=float(ing["sugars"]   or 0), step=0.1)
                            e_water = c4e.number_input("Agua %",     value=float(ing["water"]    or 0), step=0.1)
                            c5e, c6e, c7e, c8e = st.columns(4)
                            e_pod   = c5e.number_input("POD",        value=float(ing["pod"]      or 0), step=0.01)
                            e_pac   = c6e.number_input("PAC",        value=float(ing["pac"]      or 0), step=0.01)
                            e_ost   = c7e.number_input("Otros ST %", value=float(ing["other_st"] or 0), step=0.1)
                            e_price = c8e.number_input("Precio/kg $",value=float(ing.get("price_per_kg", 0) or 0), step=0.5)
                            e_notes = st.text_area("Notas",   value=ing.get("notes",    ""))
                            e_func  = st.text_input("Función", value=ing.get("function", ""))

                            if st.form_submit_button("💾 Guardar cambios"):
                                db.save_ingredient({
                                    "id": ing["id"], "name": e_name, "category": e_cat,
                                    "fat": e_fat, "msnf": e_msnf, "sugars": e_sug,
                                    "other_st": e_ost, "pod": e_pod, "pac": e_pac,
                                    "water": e_water, "notes": e_notes, "function": e_func,
                                    "brix": ing.get("brix", 0), "ph": ing.get("ph", 0),
                                    "price_per_kg": e_price,
                                    "calories_per_100g": ing.get("calories_per_100g", 0),
                                    "zero_calorie": ing.get("zero_calorie", 0),
                                })
                                st.success(f"✅ «{e_name}» actualizado.")
                                st.session_state[edit_key] = False
                                st.rerun()

        with sub_nuevo:
            st.write("### Agregar ingrediente nuevo")
            with st.form("form_nuevo_ing"):
                n_name = st.text_input("Nombre *",    placeholder="Ej: Leche de almendra sin azúcar")
                n_cat  = st.text_input("Categoría *", placeholder="Ej: Vegetal, Lácteo, Azúcar...")

                st.write("**Composición centesimal** (valores en %)")
                col1, col2, col3, col4 = st.columns(4)
                n_fat   = col1.number_input("Grasa %",    0.0, 100.0, 0.0, step=0.1)
                n_msnf  = col2.number_input("MSNF %",     0.0, 100.0, 0.0, step=0.1)
                n_sug   = col3.number_input("Azúcares %", 0.0, 100.0, 0.0, step=0.1)
                n_water = col4.number_input("Agua %",     0.0, 100.0, 0.0, step=0.1)

                col5, col6, col7, col8 = st.columns(4)
                n_ost   = col5.number_input("Otros ST %", 0.0, 100.0, 0.0, step=0.1)
                n_pod   = col6.number_input("POD", 0.0, 10.0, 0.0, step=0.01,
                                            help="Poder Edulcorante relativo a sacarosa=1.0")
                n_pac   = col7.number_input("PAC", 0.0, 10.0, 0.0, step=0.01,
                                            help="Poder Anticongelante relativo a sacarosa=1.0")
                n_price = col8.number_input("Precio/kg $", 0.0, step=0.5)

                n_notes = st.text_area("Notas técnicas",   placeholder="pH, temperatura de gelificación, etc.")
                n_func  = st.text_input("Función principal", placeholder="Ej: Base proteica, Emulsionante")

                suma = n_fat + n_msnf + n_sug + n_ost + n_water
                if suma > 0:
                    st.caption(
                        f"Suma de componentes: **{suma:.1f}%** "
                        f"{'✅' if 98 <= suma <= 102 else '⚠️ debería ser ~100 %'}"
                    )

                if st.form_submit_button("➕ Agregar ingrediente", use_container_width=True):
                    if not n_name.strip() or not n_cat.strip():
                        st.error("Nombre y categoría son obligatorios.")
                    else:
                        try:
                            db.save_ingredient({
                                "name": n_name.strip(), "category": n_cat.strip(),
                                "fat": n_fat, "msnf": n_msnf, "sugars": n_sug,
                                "other_st": n_ost, "pod": n_pod, "pac": n_pac,
                                "water": n_water, "notes": n_notes, "function": n_func,
                                "brix": 0, "ph": 0, "price_per_kg": n_price,
                                "calories_per_100g": 0, "zero_calorie": 0,
                            })
                            st.success(f"✅ «{n_name}» agregado a la base de datos.")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al guardar: {ex}")
