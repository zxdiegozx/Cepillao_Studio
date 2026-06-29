import streamlit as st
import calculator as calc
from constants import (
    PRODUCT_TYPES, MACHINES,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD, MACHINE_MANTECADORA,
    DIAGS_EXCLUIR_TICKET,
    INGREDIENT_CATEGORIES,
    CREAMI_OVERRUN_PCT,
)

# ── set_page_config DEBE ser el primer comando Streamlit ──────────────────────
st.set_page_config(
    page_title="Cepillao' Gelato Studio",
    layout="wide",
    page_icon="🍦"
)

# ── Base de datos e ingredientes ──────────────────────────────────────────────
try:
    import database as db
    db.init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")

if "ing_cache_version" not in st.session_state:
    st.session_state.ing_cache_version = 0

@st.cache_data(ttl=300)
def _load_ingredients(version: int):
    try:
        return db.get_all_ingredients()
    except Exception:
        return []

def _invalidate_ingredient_cache():
    st.session_state.ing_cache_version += 1

ingredients_raw  = _load_ingredients(st.session_state.ing_cache_version)
ingredients_map  = {ing['name']: ing for ing in ingredients_raw}
ingredient_names = list(ingredients_map.keys())

# ── Configuración de parámetros (menú de configuración) ──────────────────────
if "config_params" not in st.session_state:
    st.session_state.config_params = {}   # override de targets

st.markdown("""
<style>
.main { background-color: #13131A; }
div[data-testid="stMetricValue"] { font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🍦 Cepillao' Gelato Studio")
st.caption("Ninja Creami Edition · Formulador artesanal de helados")

tab_form, tab_recetas, tab_ingredientes, tab_config = st.tabs([
    "🧪 Formulador",
    "📁 Mis Recetas",
    "🗄️ Ingredientes",
    "⚙️ Configuración",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULADOR
# ═════════════════════════════════════════════════════════════════════════════
with tab_form:

    def callback_add_row():
        st.session_state.num_rows += 1

    def callback_clear_all():
        for key in list(st.session_state.keys()):
            if key.startswith("ing_name_") or key.startswith("grams_") or key.startswith("price_"):
                del st.session_state[key]
        st.session_state.num_rows = 4
        st.session_state.pop("recipe_loaded_id", None)
        st.session_state.pop("recipe_loaded_name", None)

    if "num_rows" not in st.session_state:
        st.session_state.num_rows = 4

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.header("⚙️ Parámetros de receta")

    recipe_name_input = st.sidebar.text_input(
        "Nombre de la receta",
        value=st.session_state.get("recipe_loaded_name", ""),
        placeholder="Ej: Choco Creami v3"
    )

    product_type = st.sidebar.selectbox("Tipo de Producto", PRODUCT_TYPES)
    machine      = st.sidebar.selectbox("Maquinaria", MACHINES, index=0)

    is_creami = machine in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD)

    # ── Parámetros de producción — solo Mantecadora ───────────────────────────
    if is_creami:
        overrun_fijo = CREAMI_OVERRUN_PCT.get(machine, 50)
        st.sidebar.info(
            f"**Overrun {machine}:** ~{overrun_fijo}%  \n"
            "_Fijo por diseño mecánico. No configurable._"
        )
        overrun_pct   = overrun_fijo   # interno — no editable
        target_liters = 1.0            # no relevante para Creami
    else:
        overrun_pct   = st.sidebar.number_input("Overrun (%)", 0, 120, 30, step=5)
        target_liters = st.sidebar.number_input("Litros objetivo", 0.1, 50.0, 1.0, step=0.5)

    brix_medido = st.sidebar.number_input(
        "Brix medido (refractómetro)", 0.0, 80.0, 0.0, step=0.5,
        help="Opcional — para validar tu receta contra el refractómetro"
    )

    st.sidebar.divider()

    def guardar_receta():
        nombre = recipe_name_input.strip()
        if not nombre:
            st.sidebar.error("Escribe un nombre para la receta.")
            return
        lines_to_save = []
        for i in range(st.session_state.num_rows):
            n = st.session_state.get(f"ing_name_{i}", "")
            g = st.session_state.get(f"grams_{i}", 0.0)
            p = st.session_state.get(f"price_{i}", 0.0)
            if n and g:
                lines_to_save.append({"ingredient_name": n, "grams": g, "price_per_kg": p})
        if not lines_to_save:
            st.sidebar.error("Añade al menos un ingrediente.")
            return
        recipe_data = {
            "name":         nombre,
            "product_type": product_type,
            "machine":      machine,
            "base_grams":   sum(l["grams"] for l in lines_to_save),
            "notes":        "",
            "lines":        lines_to_save,
        }
        existing_id = st.session_state.get("recipe_loaded_id")
        if existing_id:
            db.update_recipe(existing_id, recipe_data)
            st.sidebar.success(f"✅ «{nombre}» actualizada.")
        else:
            db.save_recipe(recipe_data)
            st.sidebar.success(f"✅ «{nombre}» guardada.")

    st.sidebar.button("💾 Guardar receta", on_click=guardar_receta, use_container_width=True)
    st.sidebar.button("🗑️ Limpiar todo",   on_click=callback_clear_all, use_container_width=True)

    # ── Layout principal ──────────────────────────────────────────────────────
    col_ing, col_panel = st.columns([1, 1], gap="large")

    with col_ing:
        st.subheader("🧾 Ingredientes")

        lines_for_calculator = []
        active_ingredient_names = []

        for i in range(st.session_state.num_rows):
            c1, c2, c3 = st.columns([3, 2, 2])
            ing_name = c1.selectbox(
                f"Ingrediente {i+1}", [""] + ingredient_names,
                key=f"ing_name_{i}", label_visibility="collapsed"
            )
            grams = c2.number_input(
                "g", 0.0, 5000.0, 0.0, step=5.0,
                key=f"grams_{i}", label_visibility="collapsed"
            )
            price = c3.number_input(
                "$/kg", 0.0, step=0.5,
                key=f"price_{i}", label_visibility="collapsed"
            )
            if ing_name and grams > 0:
                ing_obj = ingredients_map.get(ing_name)
                if ing_obj:
                    lines_for_calculator.append((ing_obj, grams, price))
                    active_ingredient_names.append(ing_name)

        st.button("➕ Agregar fila", on_click=callback_add_row, use_container_width=True)

    # ── Panel analítico ───────────────────────────────────────────────────────
    with col_panel:
        st.subheader("📊 Análisis")

        targets_default = calc._get_targets(product_type, machine)
        config_override = st.session_state.config_params.get(f"{product_type}_{machine}", {})

        if not lines_for_calculator:
            st.info("👋 Selecciona ingredientes y gramos para ver el análisis.")
            tg = targets_default
            if is_creami:
                st.markdown(f"""
| Parámetro | Rango objetivo |
|-----------|---------------|
| ST % | {tg['st'][0]} – {tg['st'][1]} % |
| Grasa % | {tg['fat'][0]} – {tg['fat'][1]} % |
| MSNF % | {tg['msnf'][0]} – {tg['msnf'][1]} % |
| Azúcares % | {tg['sugars'][0]} – {tg['sugars'][1]} % |
| POD | {tg['pod'][0]} – {tg['pod'][1]} |
| PAC | {tg['pac'][0]} – {tg['pac'][1]} |
| Ratio ST/Agua | {tg['st_water'][0]:.2f} – {tg['st_water'][1]:.2f} |
""")
        else:
            totals  = calc.calc_totals(lines_for_calculator)
            pct     = calc.calc_percentages(totals)
            derived = calc.calc_derived(
                totals, pct,
                product_type=product_type,
                machine=machine,
                lines_with_ings=lines_for_calculator,
                config=config_override or None,
            )
            kcal = calc.calc_calories(totals, lines_for_calculator)

            # Métricas rápidas
            m1, m2 = st.columns(2)
            m1.metric("Masa total", f"{totals['grams']:.1f} g")
            m2.metric("Costo est.", f"${totals['cost']:.2f}")

            # Llenado del pote Creami
            if is_creami:
                cap  = 640 if machine == MACHINE_CREAMI_DELUXE else 430
                masa = totals["grams"]
                pct_pote = min(masa / cap * 100, 110)
                if 540 <= masa <= cap:
                    msg = f"✅ Perfecto ({masa:.0f} g / {cap} g)"
                elif masa > cap:
                    msg = f"⚠️ Excede {masa - cap:.0f} g el pote"
                else:
                    msg = f"⚠️ Pote poco lleno ({masa:.0f} g / {cap} g)"
                st.progress(min(int(pct_pote), 100), text=msg)

            # ── Calorías + clasificación ──────────────────────────────────────
            st.write("### 🔥 Calorías")
            cal_class  = kcal.get('clasificacion_calorica')
            prot_class = kcal.get('clasificacion_proteica')
            k1, k2, k3 = st.columns(3)
            k1.metric("/ 100 g",        f"{kcal['kcal_per_100g']:.0f} kcal")
            k2.metric("/ porción 120g", f"{kcal['kcal_per_100g'] * 1.2:.0f} kcal")
            if is_creami:
                k3.metric("Pote completo", f"{kcal['kcal_per_pote_deluxe']:.0f} kcal")

            if cal_class:
                color = {"muy_ligero": "success", "ligero": "success",
                         "moderado": "info", "denso": "warning", "muy_denso": "error"}
                fn = getattr(st, color.get(cal_class['key'], 'info'))
                fn(f"{cal_class['emoji']} **{cal_class['etiqueta']}** — {cal_class['desc']}")

            if prot_class:
                st.caption(
                    f"{prot_class['emoji']} **Proteína:** {prot_class['valor']:.1f} g/100g — "
                    f"{prot_class['etiqueta']}  \n_{prot_class['desc']}_"
                )

            # ── Composición ───────────────────────────────────────────────────
            tg = derived.get('targets', targets_default)
            st.write("### 🧬 Composición")

            def metric_row(label, val, lo, hi, unit="%"):
                s = calc._status(val, lo, hi)
                icon = {'ok': '✅', 'low': '🔵', 'high': '🔴', 'empty': '⬜'}.get(s, '❓')
                delta = None
                if s == 'low':  delta = f"↑ mín {lo}{unit}"
                elif s == 'high': delta = f"↓ máx {hi}{unit}"
                st.metric(f"{icon} {label}", f"{val:.1f}{unit}", delta=delta,
                          delta_color="inverse" if s in ('low', 'high') else "normal")

            c1, c2, c3 = st.columns(3)
            with c1:
                metric_row("ST",     pct.get('st_pct', 0),     *tg['st'])
                metric_row("Grasa",  pct.get('fat_pct', 0),    *tg['fat'])
            with c2:
                metric_row("MSNF",   pct.get('msnf_pct', 0),   *tg['msnf'])
                metric_row("Azúcar", pct.get('sugars_pct', 0), *tg['sugars'])
            with c3:
                metric_row("POD",    pct.get('pod_total', 0),  *tg['pod'], unit="")
                metric_row("PAC",    pct.get('pac_total', 0),  *tg['pac'], unit="")

            # Ratio ST/Agua
            stw   = derived.get('st_water_ratio', 0)
            stw_lo, stw_hi = tg.get('st_water', (0.42, 0.78))
            stw_s = calc._status(stw, stw_lo, stw_hi)
            stw_icon = {'ok': '✅', 'low': '🔵', 'high': '🔴'}.get(stw_s, '❓')
            st.metric(
                f"{stw_icon} Ratio ST/Agua",
                f"{stw:.3f}",
                delta=f"rango {stw_lo:.2f}–{stw_hi:.2f}",
                delta_color="normal"
            )

            # ── Crioscopía ────────────────────────────────────────────────────
            st.write("### ❄️ Crioscopía")
            dt = derived.get("delta_t", 0)
            if is_creami:
                if derived.get("congela_ok"):
                    st.success(f"✅ ΔT {dt:.2f}°C — congela correctamente a −18°C")
                else:
                    st.warning(f"⚠️ ΔT {dt:.2f}°C — insuficiente a −18°C. Sube el PAC.")
            else:
                st.info(f"**ΔT:** {dt:.2f} °C")

            # ── Actividad de Agua ─────────────────────────────────────────────
            st.write("### 💧 Actividad de Agua")
            aw_data = calc.calc_water_activity(totals)
            aw_icon = "✅" if aw_data['riesgo_micro'] == 'bajo' else \
                      "⚠️" if aw_data['riesgo_micro'] == 'medio' else "🔴"
            aw1, aw2 = st.columns(2)
            aw1.metric("Aw estimada",  f"{aw_data['aw']:.4f}")
            aw2.metric("Riesgo micro", aw_data['riesgo_micro'].capitalize())
            with st.expander(f"{aw_icon} Interpretación Aw"):
                st.write(aw_data['interpretacion'])
                st.caption(f"Modelo: {aw_data['modelo']}")

            # ── Brix ──────────────────────────────────────────────────────────
            if brix_medido > 0:
                st.write("### 🔭 Validación Brix")
                bx = calc.validate_brix(brix_medido, totals)
                bx1, bx2, bx3 = st.columns(3)
                bx1.metric("Medido",   f"{brix_medido:.1f}°")
                bx2.metric("Esperado", f"{bx['brix_con_msnf']:.1f}°")
                bx3.metric("Delta",    f"{bx['delta_brix']:+.2f}°")
                with st.expander("Interpretación Brix"):
                    st.write(bx['interpretacion'])

            # ── Overrun ───────────────────────────────────────────────────────
            st.write("### 📐 Overrun")
            or_d = calc.overrun_calc(totals["grams"], overrun_pct, target_liters, machine)

            if is_creami:
                cap_label = "24oz" if machine == MACHINE_CREAMI_DELUXE else "16oz"
                o1, o2, o3 = st.columns(3)
                o1.metric(f"Potes base ({cap_label})", f"{or_d['potes_base']:.1f}")
                o2.metric("Overrun fijo",  f"~{or_d['overrun_fijo_pct']}%")
                o3.metric("Masa final est.", f"{or_d['masa_final_estimada_g']:.0f} g")
                if or_d.get("masa_ultimo_pote_g", 0) > 10:
                    st.caption(f"🫙 Último pote: {or_d['masa_ultimo_pote_g']:.0f} g de base")
                st.caption(
                    "ℹ️ El overrun de la Ninja Creami es **mecánico y fijo** (~40-60%). "
                    "No es configurable — depende del proceso de creamify, "
                    "no de la formulación en sí."
                )
            else:
                o1, o2 = st.columns(2)
                o1.metric("Base necesaria",    f"{or_d['base_needed_g']:.0f} g")
                o2.metric("Litros producidos", f"{or_d['liters_from_base']:.2f} L")

            # ── Estabilizantes ────────────────────────────────────────────────
            st.write("### 🧪 Estabilizantes")
            stab_recs = calc.recommend_stabilizers(
                totals, pct, product_type, machine,
                ingredient_names=active_ingredient_names
            )
            if not stab_recs:
                st.success("✅ Sin recomendaciones de estabilizante.")
            else:
                for r in stab_recs:
                    icon = "🔴" if r['priority'] == 'necesario' else \
                           "🟡" if r['priority'] == 'recomendado' else "🔵"
                    with st.expander(f"{icon} {r['stabilizer']} — {r['dose_g_per_kg']}"):
                        st.write(f"**Dosis en receta:** {r['dose_g_recipe']}")
                        st.write(f"**Razón:** {r['reason']}")
                        if r.get('warning'):
                            st.warning(r['warning'])
                        alts = r.get('alternativas', [])
                        if alts:
                            st.write("**Alternativas (elige la que tengas disponible):**")
                            for alt in alts:
                                st.write(f"- {alt}")

            # ── Diagnósticos ──────────────────────────────────────────────────
            st.write("### 🚨 Diagnósticos")
            diags_visibles = [d for d in derived.get("diagnostics", [])
                              if d["key"] not in DIAGS_EXCLUIR_TICKET]
            if not diags_visibles:
                st.success("🎉 ¡Mezcla perfectamente balanceada!")
            else:
                for d in diags_visibles:
                    icon = "🔴" if d["priority"] == "critical" else \
                           "🟡" if d["priority"] == "important" else "🔵"
                    with st.expander(f"{icon} {d['title']}"):
                        st.write(d["tip"])

            # ── Exportar ticket ───────────────────────────────────────────────
            st.divider()
            st.download_button(
                "⬇️ Descargar ticket (.txt)",
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
                    protein_data=calc.analyze_protein(
                        lines_for_calculator, totals, pct, product_type
                    ),
                ).encode("utf-8"),
                file_name="ticket_produccion.txt",
                mime="text/plain",
                use_container_width=True
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — MIS RECETAS
# ═════════════════════════════════════════════════════════════════════════════
with tab_recetas:
    st.subheader("📁 Mis Recetas Guardadas")

    try:
        all_recipes = db.get_all_recipes()
    except Exception as e:
        st.error(f"Error cargando recetas: {e}")
        all_recipes = []

    if not all_recipes:
        st.info("Aún no tienes recetas guardadas. Formula una en la pestaña 🧪 y guárdala.")
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
                            for key in list(st.session_state.keys()):
                                if (key.startswith("ing_name_") or
                                        key.startswith("grams_") or
                                        key.startswith("price_") or
                                        key.startswith("_prev_ing_name_")):
                                    del st.session_state[key]
                            st.session_state.num_rows = max(len(lines), 4)
                            for i, line in enumerate(lines):
                                st.session_state[f"ing_name_{i}"] = line["ingredient_name"]
                                st.session_state[f"grams_{i}"]    = float(line["grams"])
                                st.session_state[f"price_{i}"]    = float(line.get("price_per_kg", 0))
                                st.session_state[f"_prev_ing_name_{i}"] = line["ingredient_name"]
                            st.session_state["recipe_loaded_id"]   = rec["id"]
                            st.session_state["recipe_loaded_name"] = rec["name"]
                            st.success(f"✅ «{rec['name']}» cargada. Ve a la pestaña 🧪 Formulador.")
                            st.rerun()

                    if st.button("🗑️ Eliminar", key=f"del_{rec['id']}", use_container_width=True):
                        db.delete_recipe(rec["id"])
                        st.warning(f"Receta «{rec['name']}» eliminada.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — GESTIÓN DE INGREDIENTES
# ═════════════════════════════════════════════════════════════════════════════
with tab_ingredientes:
    st.subheader("🗄️ Base de Datos de Ingredientes")

    sub_ver, sub_nuevo = st.tabs(["📋 Ver / Editar", "➕ Nuevo ingrediente"])

    with sub_ver:
        try:
            all_ings = db.get_all_ingredients()
        except Exception as e:
            st.error(f"Error: {e}")
            all_ings = []

        search_ing = st.text_input("🔍 Buscar ingrediente", key="search_ing",
                                   placeholder="Nombre o categoría...")
        cats = sorted(set(i["category"] for i in all_ings))
        cat_filter = st.selectbox("Filtrar por categoría", ["Todas"] + cats, key="cat_filter")

        filtered = all_ings
        if search_ing:
            filtered = [i for i in filtered
                        if search_ing.lower() in i["name"].lower()
                        or search_ing.lower() in i["category"].lower()]
        if cat_filter != "Todas":
            filtered = [i for i in filtered if i["category"] == cat_filter]

        st.caption(f"{len(filtered)} ingredientes")

        for ing in filtered:
            with st.expander(f"**{ing['name']}** — _{ing['category']}_"):
                col_datos, col_edit = st.columns([2, 1])

                with col_datos:
                    st.write(f"Grasa: **{ing['fat']}%** | MSNF: **{ing['msnf']}%** | "
                             f"Azúcares: **{ing['sugars']}%** | Agua: **{ing['water']}%**")
                    st.write(f"POD: **{ing['pod']}** | PAC: **{ing['pac']}** | "
                             f"Otros ST: **{ing['other_st']}%**")
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
                        _invalidate_ingredient_cache()
                        st.warning(f"«{ing['name']}» eliminado.")

                if st.session_state.get(edit_key, False):
                    with st.form(f"form_edit_{ing['id']}"):
                        e_name  = st.text_input("Nombre", value=ing['name'])
                        # Categoría: selectbox con lista predefinida + opción actual si no está
                        cat_opts = INGREDIENT_CATEGORIES.copy()
                        if ing['category'] not in cat_opts:
                            cat_opts = [ing['category']] + cat_opts
                        e_cat = st.selectbox("Categoría", cat_opts,
                                             index=cat_opts.index(ing['category']))
                        c1, c2, c3, c4 = st.columns(4)
                        e_fat   = c1.number_input("Grasa %",    value=float(ing['fat']),    step=0.1)
                        e_msnf  = c2.number_input("MSNF %",     value=float(ing['msnf']),   step=0.1)
                        e_sug   = c3.number_input("Azúcares %", value=float(ing['sugars']), step=0.1)
                        e_water = c4.number_input("Agua %",     value=float(ing['water']),  step=0.1)
                        c5, c6, c7, c8 = st.columns(4)
                        e_ost   = c5.number_input("Otros ST %", value=float(ing['other_st']), step=0.1)
                        e_pod   = c6.number_input("POD",        value=float(ing['pod']),   step=0.01)
                        e_pac   = c7.number_input("PAC",        value=float(ing['pac']),   step=0.01)
                        e_price = c8.number_input("Precio/kg $",value=float(ing.get('price_per_kg', 0)), step=0.5)
                        e_notes = st.text_area("Notas", value=ing.get('notes', ''))
                        save_b, cancel_b = st.columns(2)
                        if save_b.form_submit_button("💾 Guardar", use_container_width=True):
                            updated = {**ing,
                                       "name": e_name.strip(), "category": e_cat,
                                       "fat": e_fat, "msnf": e_msnf, "sugars": e_sug,
                                       "other_st": e_ost, "pod": e_pod, "pac": e_pac,
                                       "water": e_water, "notes": e_notes,
                                       "price_per_kg": e_price}
                            db.update_ingredient(ing['id'], updated)
                            _invalidate_ingredient_cache()
                            st.session_state[edit_key] = False
                            st.rerun()
                        if cancel_b.form_submit_button("✖ Cancelar", use_container_width=True):
                            st.session_state[edit_key] = False
                            st.rerun()

    with sub_nuevo:
        st.write("### Agregar ingrediente nuevo")
        st.info(
            "**Selecciona la categoría desde la lista predefinida.** "
            "Esto mantiene la base de datos organizada y facilita el filtrado."
        )

        with st.form("form_nuevo_ing"):
            n_name = st.text_input("Nombre *", placeholder="Ej: Leche de almendra sin azúcar")

            # Categoría: SIEMPRE desde lista predefinida (no texto libre)
            n_cat = st.selectbox(
                "Categoría *",
                INGREDIENT_CATEGORIES,
                help="Selecciona la categoría más apropiada. Esto organiza tu base de datos."
            )

            st.write("**Composición centesimal** (valores en %)")
            col1, col2, col3, col4 = st.columns(4)
            n_fat   = col1.number_input("Grasa %",    0.0, 100.0, 0.0, step=0.1)
            n_msnf  = col2.number_input("MSNF %",     0.0, 100.0, 0.0, step=0.1)
            n_sug   = col3.number_input("Azúcares %", 0.0, 100.0, 0.0, step=0.1)
            n_water = col4.number_input("Agua %",     0.0, 100.0, 0.0, step=0.1)

            col5, col6, col7, col8 = st.columns(4)
            n_ost   = col5.number_input("Otros ST %", 0.0, 100.0, 0.0, step=0.1)
            n_pod   = col6.number_input("POD",        0.0, 10.0,  0.0, step=0.01,
                                        help="Poder Edulcorante relativo a sacarosa=1.0")
            n_pac   = col7.number_input("PAC",        0.0, 10.0,  0.0, step=0.01,
                                        help="Poder Anticongelante relativo a sacarosa=1.0")
            n_price = col8.number_input("Precio/kg $", 0.0, step=0.5)

            n_notes  = st.text_area("Notas técnicas", placeholder="Temperatura de gelificación, pH, etc.")
            n_func   = st.text_input("Función principal", placeholder="Ej: Base proteica, Emulsionante")
            n_zero_c = st.checkbox("Zero calorie (eritritol, stevia, alulosa, etc.)",
                                   help="Marca si este ingrediente no aporta calorías netas.")

            suma = n_fat + n_msnf + n_sug + n_ost + n_water
            if suma > 0:
                st.caption(f"Suma de componentes: **{suma:.1f}%** "
                           f"{'✅' if 98 <= suma <= 102 else '⚠️ debería ser ~100%'}")

            submitted = st.form_submit_button("➕ Agregar ingrediente", use_container_width=True)
            if submitted:
                if not n_name.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    nuevo = {
                        "name": n_name.strip(), "category": n_cat,
                        "fat": n_fat, "msnf": n_msnf, "sugars": n_sug,
                        "other_st": n_ost, "pod": n_pod, "pac": n_pac,
                        "water": n_water, "notes": n_notes, "function": n_func,
                        "brix": 0, "ph": 0,
                        "price_per_kg": n_price,
                        "calories_per_100g": 0,
                        "zero_calorie": 1 if n_zero_c else 0,
                    }
                    try:
                        db.save_ingredient(nuevo)
                        _invalidate_ingredient_cache()
                        st.success(f"✅ «{n_name}» agregado como [{n_cat}].")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — CONFIGURACIÓN DE PARÁMETROS
# ═════════════════════════════════════════════════════════════════════════════
with tab_config:
    st.subheader("⚙️ Configuración de Parámetros de Composición")
    st.markdown(
        "Aquí puedes **ajustar los rangos objetivo** para cada combinación de "
        "tipo de producto y máquina. Útil para prueba y error — experimenta con rangos "
        "más estrictos o más permisivos según tus observaciones de cata.  \n"
        "Los cambios se aplican **inmediatamente** en el Formulador."
    )
    st.info("Los valores por defecto son los estándares científicos de la heladería artesanal. "
            "Modificarlos es tu laboratorio personal.")

    cfg_product = st.selectbox("Tipo de producto", PRODUCT_TYPES, key="cfg_product")
    cfg_machine = st.selectbox("Máquina",          MACHINES,      key="cfg_machine")

    cfg_key     = f"{cfg_product}_{cfg_machine}"
    defaults    = calc._get_targets(cfg_product, cfg_machine)
    saved_cfg   = st.session_state.config_params.get(cfg_key, {})

    def cfg_val(k, idx):
        """Lee valor guardado o default."""
        return saved_cfg.get(k, defaults[k])[idx] if k in defaults else 0.0

    st.write(f"#### Rangos para: **{cfg_product}** · **{cfg_machine}**")
    st.caption("Modifica los mínimos y máximos. Deja en blanco (0) si no aplica.")

    with st.form("form_config"):
        st.write("**Sólidos Totales (ST %)**")
        c1, c2 = st.columns(2)
        st_lo = c1.number_input("ST mín %", 0.0, 60.0, float(cfg_val('st', 0)), step=0.5)
        st_hi = c2.number_input("ST máx %", 0.0, 60.0, float(cfg_val('st', 1)), step=0.5)

        st.write("**Grasa (%)**")
        c1, c2 = st.columns(2)
        fat_lo = c1.number_input("Grasa mín %", 0.0, 40.0, float(cfg_val('fat', 0)), step=0.5)
        fat_hi = c2.number_input("Grasa máx %", 0.0, 40.0, float(cfg_val('fat', 1)), step=0.5)

        st.write("**MSNF (%)**")
        c1, c2 = st.columns(2)
        msnf_lo = c1.number_input("MSNF mín %", 0.0, 20.0, float(cfg_val('msnf', 0)), step=0.5)
        msnf_hi = c2.number_input("MSNF máx %", 0.0, 20.0, float(cfg_val('msnf', 1)), step=0.5)

        st.write("**Azúcares (%)**")
        c1, c2 = st.columns(2)
        sug_lo = c1.number_input("Azúcares mín %", 0.0, 40.0, float(cfg_val('sugars', 0)), step=0.5)
        sug_hi = c2.number_input("Azúcares máx %", 0.0, 40.0, float(cfg_val('sugars', 1)), step=0.5)

        st.write("**POD**")
        c1, c2 = st.columns(2)
        pod_lo = c1.number_input("POD mín", 0.0, 300.0, float(cfg_val('pod', 0)), step=5.0)
        pod_hi = c2.number_input("POD máx", 0.0, 300.0, float(cfg_val('pod', 1)), step=5.0)

        st.write("**PAC**")
        c1, c2 = st.columns(2)
        pac_lo = c1.number_input("PAC mín", 0.0, 500.0, float(cfg_val('pac', 0)), step=5.0)
        pac_hi = c2.number_input("PAC máx", 0.0, 500.0, float(cfg_val('pac', 1)), step=5.0)

        st.write("**Ratio ST/Agua**")
        st.caption(
            "Relación sólidos totales / agua libre. Indicador de concentración de la mezcla. "
            "Valor bajo → demasiada agua libre (cristalización). "
            "Valor alto → mezcla sobreconcentrada (textura pastosa)."
        )
        c1, c2 = st.columns(2)
        stw_lo = c1.number_input("ST/Agua mín", 0.0, 2.0, float(cfg_val('st_water', 0)), step=0.01)
        stw_hi = c2.number_input("ST/Agua máx", 0.0, 2.0, float(cfg_val('st_water', 1)), step=0.01)

        col_save, col_reset = st.columns(2)
        save_clicked  = col_save.form_submit_button("💾 Guardar configuración", use_container_width=True)
        reset_clicked = col_reset.form_submit_button("🔄 Restaurar defaults",   use_container_width=True)

        if save_clicked:
            st.session_state.config_params[cfg_key] = {
                'st':       (st_lo,  st_hi),
                'fat':      (fat_lo, fat_hi),
                'msnf':     (msnf_lo, msnf_hi),
                'sugars':   (sug_lo, sug_hi),
                'pod':      (pod_lo, pod_hi),
                'pac':      (pac_lo, pac_hi),
                'st_water': (stw_lo, stw_hi),
            }
            st.success(f"✅ Configuración guardada para **{cfg_product}** · **{cfg_machine}**")

        if reset_clicked:
            if cfg_key in st.session_state.config_params:
                del st.session_state.config_params[cfg_key]
            st.success("✅ Parámetros restaurados a los valores por defecto.")
            st.rerun()

    # Mostrar configuraciones activas
    if st.session_state.config_params:
        st.divider()
        st.write("#### Configuraciones activas (personalizadas)")
        for key, vals in st.session_state.config_params.items():
            prod, mach = key.split("_", 1)
            st.caption(f"**{prod} · {mach}:** "
                       f"ST {vals['st'][0]}-{vals['st'][1]}% | "
                       f"Grasa {vals['fat'][0]}-{vals['fat'][1]}% | "
                       f"POD {vals['pod'][0]}-{vals['pod'][1]} | "
                       f"PAC {vals['pac'][0]}-{vals['pac'][1]}")
    else:
        st.divider()
        st.caption("Sin personalizaciones activas. Usando parámetros científicos por defecto.")
