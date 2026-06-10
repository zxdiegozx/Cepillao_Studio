"""
Cepillao' Gelato Studio — Formulador Web Pro
app.py — UI principal (Streamlit)
"""

import streamlit as st
import plotly.graph_objects as go
import calculator as calc

try:
    import database as db
    db.init_db()
except Exception as e:
    st.error(f"Error inicializando base de datos: {e}")
    st.stop()

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cepillao' Studio",
    layout="wide",
    page_icon="🍦",
    initial_sidebar_state="expanded",
)

# ── ESTILOS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0f0f1a;
    border-right: 1px solid #2a2a3e;
}
[data-testid="stSidebar"] * { color: #e8e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #a0a0c0 !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }

/* Main area */
.main .block-container {
    background: #13131f;
    padding-top: 1.5rem;
    max-width: 1400px;
}

/* Títulos */
h1 { font-family: 'DM Mono', monospace !important; color: #f0e6ff !important; font-size: 1.6rem !important; letter-spacing: -0.02em; }
h2 { color: #c8b8f0 !important; font-size: 1.1rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.06em; }
h3 { color: #9988cc !important; font-size: 0.9rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }

/* Métricas */
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 1.5rem !important;
    color: #d4c4ff !important;
}
[data-testid="stMetricLabel"] { color: #7070a0 !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.08em; }

/* Inputs */
.stNumberInput input, .stSelectbox select, .stTextInput input, .stTextArea textarea {
    background: #1e1e30 !important;
    border: 1px solid #2e2e48 !important;
    color: #e0e0f8 !important;
    border-radius: 6px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
}
.stNumberInput input:focus, .stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #7c5cbf !important;
    box-shadow: 0 0 0 2px rgba(124,92,191,0.25) !important;
}

/* Botones primarios */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c5cbf, #9b6ee0) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    letter-spacing: 0.03em;
}
.stButton > button[kind="secondary"] {
    background: #1e1e30 !important;
    border: 1px solid #3a3a58 !important;
    color: #b0b0d8 !important;
    border-radius: 8px !important;
}
.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0f0f1a;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #7070a0 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-radius: 8px !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    background: #7c5cbf !important;
    color: white !important;
}

/* Expanders / Alertas */
.stExpander { border: 1px solid #2a2a3e !important; border-radius: 8px !important; background: #171726 !important; }
details summary { color: #c0b0e8 !important; font-size: 0.85rem !important; }

/* Info/Success/Warning */
.stAlert { border-radius: 8px !important; border-left-width: 3px !important; }

/* Divider */
hr { border-color: #2a2a3e !important; margin: 1rem 0 !important; }

/* DataFrames */
[data-testid="stDataFrame"] { background: #171726 !important; }

/* Badge pills */
.badge-critical { background:#4a1020; color:#ff7090; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:'DM Mono',monospace; }
.badge-important { background:#3a2a10; color:#ffa040; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:'DM Mono',monospace; }
.badge-adjustable { background:#102030; color:#60b8ff; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-family:'DM Mono',monospace; }

/* Tabla header filas */
.col-header { color: #6060a0; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; }

/* Scrollable ingredient table */
.ing-table-scroll { max-height: 420px; overflow-y: auto; }

/* Status pill inline */
.pill-ok   { color: #50d890; font-size:0.78rem; }
.pill-low  { color: #ffa040; font-size:0.78rem; }
.pill-high { color: #ff6060; font-size:0.78rem; }
.pill-empty{ color: #505070; font-size:0.78rem; }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ────────────────────────────────────────────────────────────────────
def load_ingredients():
    rows = db.get_all_ingredients()
    return {r['name']: r for r in rows}, [r['name'] for r in rows], rows

def pill(status):
    icons = {'ok': '✅', 'low': '🔻', 'high': '🔺', 'empty': '—'}
    return icons.get(status, '—')

def radar_chart(pct, derived, product_type):
    tgts = derived.get('targets', {})
    categories = ['ST %', 'Grasa %', 'MSNF %', 'Azúcares %', 'POD', 'PAC']
    keys       = ['st_pct','fat_pct','msnf_pct','sugars_pct','pod_total','pac_total']
    tgt_keys   = ['st','fat','msnf','sugars','pod','pac']

    vals = [pct.get(k, 0) for k in keys]
    # Normalise to 0-100 against target midpoints
    # lo or hi can be None for unilateral ranges (e.g. PAC in Pacojet has lo=None)
    def norm(val, key):
        if key not in tgts:
            return 50
        lo, hi = tgts[key]
        # Resolve None bounds using the actual value as reference
        if lo is None and hi is None:
            return 50
        if lo is None:
            lo = min(val, hi * 0.5)   # synthesise a lower bound below hi
        if hi is None:
            hi = max(val, lo * 1.5)   # synthesise an upper bound above lo
        mid    = (lo + hi) / 2
        spread = (hi - lo) / 2 or 1
        n = 50 + (val - mid) / spread * 40
        return max(0, min(100, n))
    vals_norm  = [norm(v, k) for v, k in zip(vals, tgt_keys)]
    # Target band = always 50±40 → 10 to 90
    tgt_norm   = [50]*6

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=tgt_norm + [tgt_norm[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(124,92,191,0.08)',
        line=dict(color='rgba(124,92,191,0.35)', dash='dot', width=1),
        name='Rango objetivo',
        hoverinfo='skip',
    ))
    colors = ['#50d890' if abs(v-50)<25 else '#ffa040' if abs(v-50)<40 else '#ff6060' for v in vals_norm]
    fig.add_trace(go.Scatterpolar(
        r=vals_norm + [vals_norm[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(160,100,255,0.15)',
        line=dict(color='#a064ff', width=2),
        name='Receta actual',
        customdata=[[f"{v:.1f}" for v in vals + [vals[0]]]],
        hovertemplate='%{theta}: %{customdata[0]}<extra></extra>',
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(20,20,35,0.6)',
            radialaxis=dict(visible=False, range=[0,100]),
            angularaxis=dict(
                tickfont=dict(color='#9090c0', size=11, family='DM Mono'),
                linecolor='#2a2a40',
            ),
            gridshape='circular',
        ),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, t=30, b=30),
        height=280,
    )
    return fig

def overrun_section(totals):
    st.markdown("### ⚙️ Overrun & Producción")
    c1, c2, c3 = st.columns(3)
    overrun_pct = c1.number_input("Overrun %", min_value=0.0, max_value=200.0, value=30.0, step=5.0, key="overrun_pct")
    target_lt   = c2.number_input("Litros objetivo", min_value=0.1, value=2.0, step=0.5, key="target_lt")
    base_g      = totals['grams']
    if base_g > 0:
        res = calc.overrun_calc(base_g, overrun_pct, target_lt)
        c3.metric("Mix necesario", f"{res['base_needed_g']:.0f} g")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Litros de esta base", f"{res['liters_from_base']:.2f} L")
        cc2.metric("Beakers Pacojet (500ml)", f"{res['pacojet_beakers']}")
        cc3.metric("Mix por beaker", f"{res['mix_per_beaker']:.0f} g")


# ── SESSION STATE ──────────────────────────────────────────────────────────────
def _ss(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

_ss("num_rows", 5)
_ss("active_recipe_id", None)
_ss("recipe_name", "Nueva Receta")
_ss("recipe_notes", "")
_ss("recipe_tasting", "")
_ss("product_type", "Helado/Gelato")
_ss("machine", "Pacojet")
_ss("ing_edit_id", None)
_ss("confirm_del_recipe", None)
_ss("confirm_del_ing", None)
_ss("widget_epoch", 0)   # incrementar fuerza keys únicas → widgets recreados desde cero

def reset_formulator():
    st.session_state.widget_epoch     += 1
    st.session_state.num_rows          = 5
    st.session_state.active_recipe_id  = None
    st.session_state.recipe_name       = "Nueva Receta"
    st.session_state["rn_sidebar"]     = "Nueva Receta"
    st.session_state.recipe_notes      = ""
    st.session_state.recipe_tasting    = ""
    e = st.session_state.widget_epoch
    for i in range(20):
        st.session_state[f"_d_ing_{e}_{i}"]   = "— seleccionar —"
        st.session_state[f"_d_grams_{e}_{i}"] = 0.0
        st.session_state[f"_d_price_{e}_{i}"] = 0.0

def load_recipe_into_state(recipe):
    st.session_state.widget_epoch += 1
    e     = st.session_state.widget_epoch
    lines = recipe.get('lines', [])
    new_num_rows = max(5, len(lines) + 2)

    # Escribir valores en claves con el nuevo epoch — keys frescas, sin historia
    for i in range(new_num_rows + 5):
        st.session_state[f"_d_ing_{e}_{i}"]   = "— seleccionar —"
        st.session_state[f"_d_grams_{e}_{i}"] = 0.0
        st.session_state[f"_d_price_{e}_{i}"] = 0.0
    for i, line in enumerate(lines):
        st.session_state[f"_d_ing_{e}_{i}"]   = line['ingredient_name']
        st.session_state[f"_d_grams_{e}_{i}"] = float(line['grams'])
        st.session_state[f"_d_price_{e}_{i}"] = float(line.get('price_per_kg', 0))

    st.session_state.active_recipe_id = recipe['id']
    st.session_state.recipe_name      = recipe['name']
    st.session_state["rn_sidebar"]    = recipe['name']
    st.session_state.product_type     = recipe.get('product_type', 'Helado/Gelato')
    st.session_state.machine          = recipe.get('machine', 'Pacojet')
    st.session_state.recipe_notes     = recipe.get('notes', '')
    st.session_state.recipe_tasting   = recipe.get('tasting_notes', '')
    st.session_state.num_rows         = new_num_rows


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px 0;">
  <svg width="44" height="54" viewBox="0 0 44 54" xmlns="http://www.w3.org/2000/svg">
    <!-- palo -->
    <rect x="20" y="38" width="4" height="14" rx="2" fill="#c8a97e"/>
    <!-- cuerpo del raspado (cono invertido) -->
    <path d="M6 8 Q6 4 22 4 Q38 4 38 8 L28 38 Q25 42 22 42 Q19 42 16 38 Z" fill="#1a1a2e"/>
    <!-- capa base azul marino -->
    <path d="M6 8 Q6 4 22 4 Q38 4 38 8 L34 22 Q22 20 10 22 Z" fill="#1e3a5f"/>
    <!-- capa roja (jamaica / fresa) -->
    <path d="M10 22 Q22 20 34 22 L30 32 Q22 30 14 32 Z" fill="#c0392b"/>
    <!-- capa amarilla (mango / tamarindo) -->
    <path d="M14 32 Q22 30 30 32 L28 38 Q25 42 22 42 Q19 42 16 38 Z" fill="#f39c12"/>
    <!-- brillo -->
    <ellipse cx="16" cy="10" rx="5" ry="2.5" fill="rgba(255,255,255,0.12)" transform="rotate(-10,16,10)"/>
    <!-- destellos de chamoy / chili en polvo -->
    <circle cx="19" cy="14" r="1.2" fill="#e74c3c" opacity="0.8"/>
    <circle cx="26" cy="11" r="0.9" fill="#e74c3c" opacity="0.7"/>
    <circle cx="23" cy="18" r="0.8" fill="#e74c3c" opacity="0.6"/>
    <!-- granitos de chile -->
    <rect x="13" y="24" width="2" height="1" rx="0.5" fill="#c0392b" opacity="0.7"/>
    <rect x="28" y="26" width="2" height="1" rx="0.5" fill="#c0392b" opacity="0.7"/>
    <rect x="20" y="28" width="2" height="1" rx="0.5" fill="#e67e22" opacity="0.7"/>
  </svg>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:1.1rem;font-weight:600;color:#f0e6ff;line-height:1.1;">Cepillao'</div>
    <div style="font-family:'DM Mono',monospace;font-size:0.85rem;color:#9070c0;letter-spacing:0.08em;">Studio</div>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown("---")

    # Nav
    page = st.radio(
        "Sección",
        ["📐 Formulador", "📚 Recetas", "🧪 Ingredientes"],
        label_visibility="collapsed",
    )

    if page == "📐 Formulador":
        st.markdown("---")
        st.markdown("### Parámetros")
        _product_types = ["Helado/Gelato","Helado Ligero","Sorbete","Granita","Gelato Vegano","Frozen Yogurt"]
        _pt_idx = _product_types.index(st.session_state.product_type) if st.session_state.product_type in _product_types else 0
        st.session_state.product_type = st.selectbox(
            "Tipo de producto",
            _product_types,
            index=_pt_idx,
        )
        # Tooltip contextual por tipo
        _pt_hints = {
            "Helado/Gelato":  "Grasa 4–20% · MSNF 6–11% · ST 34–42%",
            "Helado Ligero":  "Grasa 2–6% · MSNF 8–13% · ST 32–40%",
            "Sorbete":        "Sin lácteos · Grasa 0–2% · ST 27–35%",
            "Granita":        "Cristales tolerados · ST 22–30%",
            "Gelato Vegano":  "Grasa vegetal · Sin MSNF · ST 34–42%",
            "Frozen Yogurt":  "Acidez láctica · Grasa 2–10% · ST 30–38%",
        }
        st.caption(_pt_hints.get(st.session_state.product_type, ""))
        st.session_state.machine = st.selectbox(
            "Maquinaria",
            ["Pacojet","Mantecadora Tradicional"],
            index=["Pacojet","Mantecadora Tradicional"].index(st.session_state.machine),
        )
        st.markdown("---")
        st.markdown("### Receta activa")
        # Sembrar el valor en la key del widget si fue actualizado por un callback
        if "rn_sidebar" not in st.session_state:
            st.session_state["rn_sidebar"] = st.session_state.recipe_name
        st.text_input("Nombre", key="rn_sidebar")
        # Sincronizar de vuelta para que save/guardar lo lean
        st.session_state.recipe_name = st.session_state["rn_sidebar"]
        if st.session_state.active_recipe_id:
            st.caption(f"ID #{st.session_state.active_recipe_id}")
        if st.button("✨ Nueva receta", use_container_width=True, type="secondary"):
            reset_formulator()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: FORMULADOR
# ══════════════════════════════════════════════════════════════════════════════
if page == "📐 Formulador":

    ingredients_map, ingredient_names, ingredients_list = load_ingredients()

    st.markdown("# 📐 Formulador")
    rid = st.session_state.active_recipe_id
    st.caption(f"Receta: **{st.session_state.recipe_name}**" + (f" — guardada #{ rid}" if rid else " — sin guardar"))

    col_tabla, col_panel = st.columns([5, 4], gap="large")

    # ── TABLA DE INGREDIENTES con data_editor ───────────────────────────────
    with col_tabla:
        st.markdown("## Ingredientes")

        import pandas as pd

        # Construir DataFrame inicial desde claves _d_ del epoch actual
        e = st.session_state.widget_epoch
        n = st.session_state.num_rows
        rows_init = []
        for i in range(n):
            rows_init.append({
                "Ingrediente": st.session_state.get(f"_d_ing_{e}_{i}",   ""),
                "Gramos":      st.session_state.get(f"_d_grams_{e}_{i}", 0.0),
                "$/kg":        st.session_state.get(f"_d_price_{e}_{i}", 0.0),
            })
        df_init = pd.DataFrame(rows_init)

        edited_df = st.data_editor(
            df_init,
            key=f"ing_table_{e}",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ingrediente": st.column_config.SelectboxColumn(
                    "Ingrediente",
                    options=[""] + ingredient_names,
                    required=False,
                    width="large",
                ),
                "Gramos": st.column_config.NumberColumn(
                    "Gramos (g)",
                    min_value=0.0,
                    step=5.0,
                    format="%.1f",
                    width="small",
                ),
                "$/kg": st.column_config.NumberColumn(
                    "$ / kg",
                    min_value=0.0,
                    step=0.5,
                    format="$%.2f",
                    width="small",
                ),
            },
        )

        # Construir lines_for_calc desde el DataFrame editado
        lines_for_calc = []
        for _, row in edited_df.iterrows():
            nm = row.get("Ingrediente", "")
            g  = row.get("Gramos", 0.0) or 0.0
            p  = row.get("$/kg", 0.0) or 0.0
            if nm and nm != "" and g > 0:
                ing_dict = ingredients_map.get(nm)
                if ing_dict:
                    lines_for_calc.append((ing_dict, float(g), float(p)))

        ba1, ba2 = st.columns(2)
        ba1.button("🗑 Limpiar tabla", use_container_width=True, type="secondary",
                   on_click=reset_formulator)

        # ── ABRIR RECETA ─────────────────────────────────────────────────────
        st.markdown("")
        if st.button("📂 Abrir receta guardada", use_container_width=True, type="secondary"):
            st.session_state["show_open_recipe"] = not st.session_state.get("show_open_recipe", False)

        if st.session_state.get("show_open_recipe", False):
            saved_recipes = db.get_all_recipes()
            if not saved_recipes:
                st.info("No tienes recetas guardadas todavía.")
            else:
                st.markdown("#### Selecciona una receta")
                search_open = st.text_input("Buscar", placeholder="Filtrar por nombre...", key="search_open_recipe", label_visibility="collapsed")
                filtered_open = [r for r in saved_recipes if search_open.lower() in r['name'].lower()] if search_open else saved_recipes
                for r in filtered_open:
                    col_r, col_btn = st.columns([4, 1])
                    col_r.markdown(f"**{r['name']}** — {r['product_type']} · {r['machine']}")

                    def _make_open_cb(recipe_id):
                        def _cb():
                            full = db.get_recipe(recipe_id)
                            if full:
                                load_recipe_into_state(full)
                            st.session_state["show_open_recipe"] = False
                        return _cb

                    col_btn.button("Abrir", key=f"open_rec_{r['id']}",
                                   use_container_width=True, type="primary",
                                   on_click=_make_open_cb(r['id']))

        st.markdown("---")
        # ── NOTAS DE RECETA ──────────────────────────────────────────────────
        with st.expander("📝 Notas de receta"):
            st.session_state.recipe_notes   = st.text_area("Notas técnicas", value=st.session_state.recipe_notes, height=80, key="notes_form")
            st.session_state.recipe_tasting = st.text_area("Notas de cata", value=st.session_state.recipe_tasting, height=80, key="tasting_form")

        # ── GUARDAR RECETA ───────────────────────────────────────────────────
        st.markdown("---")
        sb1, sb2 = st.columns(2)
        def save_current_recipe():
            lines_data = []
            for _, row in edited_df.iterrows():
                nm = row.get("Ingrediente", "")
                g  = row.get("Gramos", 0.0) or 0.0
                p  = row.get("$/kg", 0.0) or 0.0
                if nm and nm != "" and g > 0:
                    lines_data.append({'ingredient_name': nm, 'grams': float(g), 'price_per_kg': float(p)})
            data = {
                'id':           st.session_state.active_recipe_id,
                'name':         st.session_state.recipe_name,
                'product_type': st.session_state.product_type,
                'machine':      st.session_state.machine,
                'base_grams':   sum(l['grams'] for l in lines_data),
                'notes':        st.session_state.recipe_notes,
                'tasting_notes':st.session_state.recipe_tasting,
                'lines':        lines_data,
            }
            new_id = db.save_recipe(data)
            st.session_state.active_recipe_id = new_id

        if sb1.button("💾 Guardar receta", use_container_width=True, type="primary"):
            if lines_for_calc:
                save_current_recipe()
                st.success(f"Receta **{st.session_state.recipe_name}** guardada.")
            else:
                st.warning("Añade ingredientes antes de guardar.")

        if st.session_state.active_recipe_id:
            if sb2.button("🗑 Eliminar receta", use_container_width=True, type="secondary"):
                st.session_state.confirm_del_recipe = st.session_state.active_recipe_id

        if st.session_state.confirm_del_recipe == st.session_state.active_recipe_id and st.session_state.active_recipe_id:
            st.warning(f"¿Eliminar **{st.session_state.recipe_name}**? Esta acción no se puede deshacer.")
            cc1, cc2 = st.columns(2)
            if cc1.button("✅ Sí, eliminar", type="primary"):
                db.delete_recipe(st.session_state.active_recipe_id)
                reset_formulator()
                st.session_state.confirm_del_recipe = None
                st.success("Receta eliminada.")
                st.rerun()
            if cc2.button("❌ Cancelar"):
                st.session_state.confirm_del_recipe = None
                st.rerun()

        # ── OVERRUN ──────────────────────────────────────────────────────────
        if lines_for_calc:
            st.markdown("---")
            totals_ov = calc.calc_totals(lines_for_calc)
            overrun_section(totals_ov)

    # ── PANEL ANALÍTICO ──────────────────────────────────────────────────────
    with col_panel:
        if not lines_for_calc:
            st.info("👋 Selecciona ingredientes y gramos para ver el análisis.")
        else:
            totals  = calc.calc_totals(lines_for_calc)
            pct     = calc.calc_percentages(totals)
            derived = calc.calc_derived(totals, pct,
                                        product_type=st.session_state.product_type,
                                        machine=st.session_state.machine)

            # Métricas rápidas
            m1, m2, m3 = st.columns(3)
            m1.metric("Masa total", f"{totals['grams']:.0f} g")
            m2.metric("Costo estimado", f"${totals['cost']:.2f}")
            m3.metric("ΔT crioscopía", f"{derived.get('delta_t',0):.2f} °C")

            # Radar
            st.markdown("## Balance")
            fig = radar_chart(pct, derived, st.session_state.product_type)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # Tabla de composición
            st.markdown("## Composición centesimal")
            status = derived.get('status', {})
            tgts   = derived.get('targets', {})

            def row(label, val_str, key, unit=""):
                s = status.get(key, 'empty')
                icon = {'ok':'✅','low':'🔻','high':'🔺','empty':'—'}.get(s,'—')
                rng = tgts.get(key, (0, 0))
                lo, hi = rng if rng else (None, None)
                if lo is None and hi is not None:
                    target_str = f"máx {hi}{unit}"     # solo límite superior (ej. PAC en Pacojet)
                elif lo is not None and hi is None:
                    target_str = f"mín {lo}{unit}"     # solo límite inferior
                elif lo is not None and hi is not None:
                    target_str = f"{lo}–{hi}{unit}"
                else:
                    target_str = "—"
                return f"| {label} | `{val_str}` | {target_str} | {icon} |"

            tbl = """| Parámetro | Valor | Rango objetivo | Estado |
|---|---|---|---|
""" + "\n".join([
                row("Sólidos Totales (ST)", f"{pct.get('st_pct',0):.1f}%", "st", "%"),
                row("Grasa", f"{pct.get('fat_pct',0):.1f}%", "fat", "%"),
                row("MSNF / ESGL", f"{pct.get('msnf_pct',0):.1f}%", "msnf", "%"),
                row("Azúcares", f"{pct.get('sugars_pct',0):.1f}%", "sugars", "%"),
                f"| Agua libre | `{pct.get('water_pct',0):.1f}%` | — | — |",
                row("POD", f"{pct.get('pod_total',0):.0f}", "pod"),
                row("PAC", f"{pct.get('pac_total',0):.0f}", "pac"),
                row("Ratio ST/Agua", f"{derived.get('ratio_st_water',0):.3f}", "st_water"),
            ])
            st.markdown(tbl)

            # Diagnósticos
            st.markdown("## Diagnósticos")
            diags = derived.get('diagnostics', [])
            if not diags:
                st.success("🎉 Mezcla perfectamente balanceada. Sin alertas.")
            else:
                for d in diags:
                    badge = {
                        'critical':   '🔴 CRÍTICO',
                        'important':  '🟡 IMPORTANTE',
                        'adjustable': '🔵 AJUSTABLE',
                    }.get(d['priority'], '')
                    with st.expander(f"{badge} — {d['title']}"):
                        st.markdown(d['tip'])


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: RECETAS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📚 Recetas":

    st.markdown("# 📚 Recetas guardadas")

    recipes = db.get_all_recipes()

    if not recipes:
        st.info("Todavía no tienes recetas guardadas. Ve al Formulador y guarda una.")
    else:
        # Buscador
        search = st.text_input("🔍 Buscar receta", placeholder="Nombre, tipo...", key="recipe_search")
        filtered = [r for r in recipes if search.lower() in r['name'].lower()
                    or search.lower() in r.get('product_type','').lower()] if search else recipes

        st.caption(f"{len(filtered)} receta(s)")
        st.markdown("---")

        for rec in filtered:
            with st.expander(f"**{rec['name']}** — {rec['product_type']} | {rec['machine']}"):
                full = db.get_recipe(rec['id'])
                if not full:
                    continue

                c_info, c_actions = st.columns([4, 1])

                with c_info:
                    if full.get('lines'):
                        rows_txt = "| Ingrediente | Gramos | $/kg |\n|---|---|---|\n"
                        total_g = 0
                        for ln in full['lines']:
                            rows_txt += f"| {ln['ingredient_name']} | {ln['grams']:.1f}g | {ln.get('price_per_kg',0):.2f} |\n"
                            total_g += ln['grams']
                        rows_txt += f"| **TOTAL** | **{total_g:.1f}g** | |\n"
                        st.markdown(rows_txt)
                    if full.get('notes'):
                        st.markdown(f"📝 **Notas:** {full['notes']}")
                    if full.get('tasting_notes'):
                        st.markdown(f"👅 **Cata:** {full['tasting_notes']}")
                    st.caption(f"Creada: {rec.get('created_at','')} | Actualizada: {rec.get('updated_at','')}")

                with c_actions:
                    if st.button("🗑 Eliminar", key=f"del_{rec['id']}", use_container_width=True, type="secondary"):
                        st.session_state.confirm_del_recipe = rec['id']

                    if st.session_state.confirm_del_recipe == rec['id']:
                        st.warning("¿Confirmar?")
                        if st.button("✅ Sí", key=f"delok_{rec['id']}"):
                            db.delete_recipe(rec['id'])
                            st.session_state.confirm_del_recipe = None
                            st.success("Eliminada.")
                            st.rerun()
                        if st.button("❌ No", key=f"delno_{rec['id']}"):
                            st.session_state.confirm_del_recipe = None
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA: INGREDIENTES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧪 Ingredientes":

    st.markdown("# 🧪 Base de datos de ingredientes")

    _, _, ingredients_list = load_ingredients()

    tab_ver, tab_nuevo, tab_editar = st.tabs(["📋 Ver todos", "➕ Nuevo ingrediente", "✏️ Editar / Eliminar"])

    # ── TAB VER ──────────────────────────────────────────────────────────────
    with tab_ver:
        search_ing = st.text_input("🔍 Buscar ingrediente", placeholder="Nombre o categoría...", key="ing_search")
        cats = sorted(list(set(r['category'] for r in ingredients_list)))
        cat_filter = st.selectbox("Filtrar por categoría", ["Todas"] + cats, key="cat_filter")

        filtered_ings = ingredients_list
        if search_ing:
            filtered_ings = [r for r in filtered_ings if search_ing.lower() in r['name'].lower()]
        if cat_filter != "Todas":
            filtered_ings = [r for r in filtered_ings if r['category'] == cat_filter]

        st.caption(f"{len(filtered_ings)} ingrediente(s)")

        if filtered_ings:
            import pandas as pd
            df = pd.DataFrame([{
                'Nombre':    r['name'],
                'Categoría': r['category'],
                'Grasa %':   r['fat'],
                'MSNF %':    r['msnf'],
                'Azúcares%': r['sugars'],
                'Otros ST%': r['other_st'],
                'POD':       r['pod'],
                'PAC':       r['pac'],
                'Agua %':    r['water'],
                'pH':        r.get('ph', 0),
                'Función':   r.get('function',''),
            } for r in filtered_ings])
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             'Grasa %':   st.column_config.NumberColumn(format="%.1f"),
                             'MSNF %':    st.column_config.NumberColumn(format="%.1f"),
                             'Azúcares%': st.column_config.NumberColumn(format="%.1f"),
                             'Otros ST%': st.column_config.NumberColumn(format="%.1f"),
                             'POD':       st.column_config.NumberColumn(format="%.2f"),
                             'PAC':       st.column_config.NumberColumn(format="%.2f"),
                             'Agua %':    st.column_config.NumberColumn(format="%.1f"),
                             'pH':        st.column_config.NumberColumn(format="%.1f"),
                         })

    # ── TAB NUEVO ────────────────────────────────────────────────────────────
    with tab_nuevo:
        st.markdown("### Crear nuevo ingrediente")
        with st.form("form_new_ing"):
            f1, f2 = st.columns(2)
            n_name  = f1.text_input("Nombre *", placeholder="Ej: Leche de almendra")
            n_cat   = f2.selectbox("Categoría *",
                ["Lácteo","Azúcar","Fruta tropical","Fruta europea",
                 "Pasta frutos secos","Cacao/Chocolate","Café/Té/Aroma",
                 "Alcohol","Estabilizante","Emulsionante","Funcional","Base","Otro"])
            st.markdown("##### Composición (%)")
            nc1,nc2,nc3,nc4 = st.columns(4)
            n_fat     = nc1.number_input("Grasa %",    0.0, 100.0, 0.0, 0.1, format="%.2f")
            n_msnf    = nc2.number_input("MSNF %",     0.0, 100.0, 0.0, 0.1, format="%.2f")
            n_sugars  = nc3.number_input("Azúcares %", 0.0, 100.0, 0.0, 0.1, format="%.2f")
            n_other   = nc4.number_input("Otros ST %", 0.0, 100.0, 0.0, 0.1, format="%.2f")
            nd1,nd2,nd3,nd4 = st.columns(4)
            n_pod     = nd1.number_input("POD",  0.0, 10.0, 0.0, 0.01, format="%.3f")
            n_pac     = nd2.number_input("PAC",  0.0, 10.0, 0.0, 0.01, format="%.3f")
            n_water   = nd3.number_input("Agua %",0.0, 100.0,0.0,0.1,  format="%.2f")
            n_ph      = nd4.number_input("pH",   0.0, 14.0, 7.0, 0.1,  format="%.1f")
            ne1, ne2  = st.columns(2)
            n_func    = ne1.text_input("Función", placeholder="Ej: Base baja en grasa")
            n_notes   = ne2.text_input("Notas", placeholder="Ej: Higroscópico, añadir al final")
            submitted = st.form_submit_button("💾 Guardar ingrediente", type="primary", use_container_width=True)
            if submitted:
                if not n_name.strip():
                    st.error("El nombre es obligatorio.")
                elif sum([n_fat, n_msnf, n_sugars, n_other, n_water]) > 101:
                    st.error("La suma de componentes supera 100%. Revisa los valores.")
                else:
                    db.save_ingredient({
                        'name': n_name.strip(), 'category': n_cat,
                        'fat': n_fat, 'msnf': n_msnf, 'sugars': n_sugars,
                        'other_st': n_other, 'pod': n_pod, 'pac': n_pac,
                        'water': n_water, 'ph': n_ph,
                        'function': n_func, 'notes': n_notes,
                    })
                    st.success(f"**{n_name}** creado correctamente.")
                    st.rerun()

    # ── TAB EDITAR / ELIMINAR ────────────────────────────────────────────────
    with tab_editar:
        st.markdown("### Editar o eliminar ingrediente")

        _, ing_names_cur, ings_cur = load_ingredients()
        sel_name = st.selectbox("Selecciona ingrediente", ing_names_cur, key="edit_ing_select")

        if sel_name:
            ing_data = db.get_ingredient_by_name(sel_name)
            if ing_data:
                with st.form("form_edit_ing"):
                    ef1, ef2 = st.columns(2)
                    e_name  = ef1.text_input("Nombre *", value=ing_data['name'])
                    cats_all = ["Lácteo","Azúcar","Fruta tropical","Fruta europea",
                                "Pasta frutos secos","Cacao/Chocolate","Café/Té/Aroma",
                                "Alcohol","Estabilizante","Emulsionante","Funcional","Base","Otro"]
                    cat_idx = cats_all.index(ing_data['category']) if ing_data['category'] in cats_all else 0
                    e_cat   = ef2.selectbox("Categoría *", cats_all, index=cat_idx, key="edit_cat")

                    st.markdown("##### Composición (%)")
                    ec1,ec2,ec3,ec4 = st.columns(4)
                    e_fat    = ec1.number_input("Grasa %",    0.0,100.0,float(ing_data['fat']),   0.1, format="%.2f", key="ef")
                    e_msnf   = ec2.number_input("MSNF %",     0.0,100.0,float(ing_data['msnf']),  0.1, format="%.2f", key="em")
                    e_sugars = ec3.number_input("Azúcares %", 0.0,100.0,float(ing_data['sugars']),0.1, format="%.2f", key="es")
                    e_other  = ec4.number_input("Otros ST %", 0.0,100.0,float(ing_data['other_st']),0.1,format="%.2f",key="eo")
                    ed1,ed2,ed3,ed4 = st.columns(4)
                    e_pod    = ed1.number_input("POD",  0.0,10.0, float(ing_data['pod']),  0.01,format="%.3f",key="ep")
                    e_pac    = ed2.number_input("PAC",  0.0,10.0, float(ing_data['pac']),  0.01,format="%.3f",key="epa")
                    e_water  = ed3.number_input("Agua %",0.0,100.0,float(ing_data['water']),0.1, format="%.2f",key="ew")
                    e_ph     = ed4.number_input("pH",   0.0,14.0, float(ing_data.get('ph',7)),0.1,format="%.1f",key="eph")
                    ee1,ee2  = st.columns(2)
                    e_func   = ee1.text_input("Función", value=ing_data.get('function',''), key="efunc")
                    e_notes  = ee2.text_input("Notas",   value=ing_data.get('notes',''),   key="enotes")

                    save_btn = st.form_submit_button("💾 Actualizar", type="primary", use_container_width=True)
                    if save_btn:
                        db.save_ingredient({
                            'id': ing_data['id'], 'name': e_name.strip(), 'category': e_cat,
                            'fat': e_fat, 'msnf': e_msnf, 'sugars': e_sugars,
                            'other_st': e_other, 'pod': e_pod, 'pac': e_pac,
                            'water': e_water, 'ph': e_ph,
                            'function': e_func, 'notes': e_notes,
                        })
                        st.success(f"**{e_name}** actualizado.")
                        st.rerun()

                st.markdown("---")
                st.markdown("#### ⚠️ Zona de peligro")
                if st.button(f"🗑 Eliminar '{sel_name}'", type="secondary"):
                    st.session_state.confirm_del_ing = ing_data['id']

                if st.session_state.confirm_del_ing == ing_data['id']:
                    st.warning(f"¿Eliminar **{sel_name}** permanentemente? No se puede deshacer.")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("✅ Sí, eliminar", type="primary", key="del_ing_ok"):
                        db.delete_ingredient(ing_data['id'])
                        st.session_state.confirm_del_ing = None
                        st.success(f"**{sel_name}** eliminado.")
                        st.rerun()
                    if dc2.button("❌ Cancelar", key="del_ing_cancel"):
                        st.session_state.confirm_del_ing = None
                        st.rerun()
