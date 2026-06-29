import streamlit as st
import calculator as calc
from constants import (
    PRODUCT_TYPES, MACHINES,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD, MACHINE_MANTECADORA,
    DIAGS_EXCLUIR_TICKET,
    INGREDIENT_CATEGORIES,
    CREAMI_OVERRUN_PCT,
)

st.set_page_config(
    page_title="Cepillao' Gelato Studio",
    layout="wide",
    page_icon="🍦"
)

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

ingredients_raw = _load_ingredients(st.session_state.ing_cache_version)
try:
    _bases_as_ings = db.get_bases_as_ingredients()
except Exception:
    _bases_as_ings = []

ingredients_map  = {ing['name']: ing for ing in ingredients_raw}
for b in _bases_as_ings:
    ingredients_map[b['name']] = b
ingredient_names = sorted(ingredients_map.keys())

# ── REC 1: config_params cargado desde BD al iniciar sesión ──────────────────
if "config_params" not in st.session_state:
    try:
        st.session_state.config_params = db.get_user_config()
    except Exception:
        st.session_state.config_params = {}

# ── REC 4: CSS desde archivo externo (con fallback inline si no existe) ───────
import pathlib as _pathlib
_css_file = _pathlib.Path(__file__).parent / ".streamlit" / "custom.css"
if _css_file.exists():
    _css = _css_file.read_text(encoding="utf-8")
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)
else:
    st.markdown("""
<style>
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
.gelato-card {
    background: #1e1e2e; border: 1px solid #2d2d44;
    border-radius: 12px; padding: 16px 20px; margin-bottom: 12px;
}
.gelato-card-title {
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #888; margin-bottom: 10px;
}
.param-bar-wrap { margin-bottom: 10px; }
.param-bar-header {
    display: flex; justify-content: space-between;
    align-items: baseline; margin-bottom: 3px;
}
.param-label { font-size: 0.82rem; color: #ccc; }
.param-value { font-size: 1.05rem; font-weight: 700; color: #fff; }
.param-range { font-size: 0.72rem; color: #666; }
.param-bar-bg {
    background: #2d2d44; border-radius: 4px; height: 6px;
    position: relative; overflow: visible;
}
.param-bar-range { position: absolute; height: 100%; background: #2a4a2a; border-radius: 4px; }
.param-bar-fill  { position: absolute; height: 100%; border-radius: 4px; transition: width 0.3s ease; }
.bar-ok    { background: #4ade80; }
.bar-low   { background: #60a5fa; }
.bar-high  { background: #f87171; }
.bar-empty { background: #444; }
.param-status-ok    { color: #4ade80; font-size: 0.75rem; }
.param-status-low   { color: #60a5fa; font-size: 0.75rem; }
.param-status-high  { color: #f87171; font-size: 0.75rem; }
.param-status-empty { color: #666;    font-size: 0.75rem; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge-ok      { background: #14532d; color: #4ade80; }
.badge-warn    { background: #451a03; color: #fb923c; }
.badge-danger  { background: #450a0a; color: #f87171; }
.badge-info    { background: #1e3a5f; color: #60a5fa; }
.diag-item { padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; border-left: 3px solid; }
.diag-critical   { background: #1f0a0a; border-color: #ef4444; }
.diag-important  { background: #1f150a; border-color: #f97316; }
.diag-adjustable { background: #0f1f2f; border-color: #3b82f6; }
.diag-title { font-size: 0.85rem; font-weight: 600; color: #eee; }
.diag-tip   { font-size: 0.78rem; color: #999; margin-top: 3px; }
.ing-row-header {
    display: grid; grid-template-columns: 3fr 1.5fr 1.5fr;
    gap: 6px; font-size: 0.7rem; color: #666;
    text-transform: uppercase; letter-spacing: 0.06em; padding: 0 4px; margin-bottom: 4px;
}
.pote-fill-wrap { background: #1e1e2e; border: 1px solid #2d2d44; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; }
.pote-fill-label { font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.pote-fill-bar-bg { background: #2d2d44; border-radius: 6px; height: 10px; overflow: hidden; }
.pote-fill-bar { height: 100%; border-radius: 6px; }
.section-overline { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #555; margin-bottom: 8px; margin-top: 4px; }
.comp-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px; }
.comp-cell { background: #181828; border-radius: 8px; padding: 10px 12px; border: 1px solid #252540; }
.comp-cell-label { font-size: 0.68rem; color: #666; text-transform: uppercase; letter-spacing: 0.06em; }
.comp-cell-val   { font-size: 1.15rem; font-weight: 700; color: #fff; margin: 2px 0; }
.comp-cell-hint  { font-size: 0.68rem; }
.kcal-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 8px; }
.kcal-cell { background: #181828; border-radius: 8px; padding: 10px 12px; border: 1px solid #252540; text-align: center; }
.kcal-cell-val   { font-size: 1.2rem; font-weight: 800; color: #fff; }
.kcal-cell-label { font-size: 0.68rem; color: #666; text-transform: uppercase; }
div[data-testid="stMetricValue"] { font-size: 18px !important; font-weight: 700 !important; }
div[data-testid="stSidebar"] { background: #111120; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
  <span style="font-size:2rem;">🍦</span>
  <div>
    <div style="font-size:1.5rem;font-weight:800;color:#fff;line-height:1.1">Cepillao' Gelato Studio</div>
    <div style="font-size:0.78rem;color:#666;">Ninja Creami Edition · Formulador artesanal de helados</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_form, tab_recetas, tab_bases, tab_ingredientes, tab_config = st.tabs([
    "🧪 Formulador",
    "📁 Mis Recetas",
    "🧫 Bases de Helado",
    "🗄️ Ingredientes",
    "⚙️ Configuración",
])


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS UI
# ═════════════════════════════════════════════════════════════════════════════

def _param_bar(label, val, lo, hi, unit="%", scale_max=None):
    """Renderiza una barra de parámetro con zona objetivo resaltada."""
    s = calc._status(val, lo, hi)
    bar_class  = {"ok": "bar-ok", "low": "bar-low", "high": "bar-high", "empty": "bar-empty"}[s]
    hint_class = {"ok": "param-status-ok", "low": "param-status-low",
                  "high": "param-status-high", "empty": "param-status-empty"}[s]
    hint_text  = {"ok": "✓ En rango", "low": f"↑ mín {lo}{unit}",
                  "high": f"↓ máx {hi}{unit}", "empty": "—"}[s]

    if scale_max is None:
        scale_max = (hi or 10) * 1.5

    fill_pct   = min(val / scale_max * 100, 100) if scale_max > 0 else 0
    range_lo_p = (lo or 0) / scale_max * 100 if scale_max > 0 else 0
    range_hi_p = (hi or scale_max) / scale_max * 100 if scale_max > 0 else 100

    st.markdown(f"""
<div class="param-bar-wrap">
  <div class="param-bar-header">
    <span class="param-label">{label}</span>
    <span class="param-value">{val:.1f}{unit}</span>
    <span class="{hint_class}">{hint_text}</span>
  </div>
  <div class="param-bar-bg">
    <div class="param-bar-range"
         style="left:{range_lo_p:.1f}%;width:{range_hi_p-range_lo_p:.1f}%;"></div>
    <div class="param-bar-fill {bar_class}"
         style="width:{fill_pct:.1f}%;"></div>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:2px;">
    <span class="param-range">0</span>
    <span class="param-range">rango {lo}–{hi}{unit}</span>
    <span class="param-range">{scale_max:.0f}{unit}</span>
  </div>
</div>""", unsafe_allow_html=True)


def _section(title):
    st.markdown(f'<div class="section-overline">{title}</div>', unsafe_allow_html=True)

def _card_open():
    st.markdown('<div class="gelato-card">', unsafe_allow_html=True)

def _card_close():
    st.markdown('</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# REC 2: HELPERS DEL FORMULADOR — nivel módulo
# ═════════════════════════════════════════════════════════════════════════════

def _collect_lines():
    """Lee el grid de ingredientes del session_state y retorna lista de dicts."""
    lines = []
    for i in range(st.session_state.get("num_rows", 4)):
        n = st.session_state.get(f"ing_name_{i}", "")
        g = st.session_state.get(f"grams_{i}", 0.0)
        p = st.session_state.get(f"price_{i}", 0.0)
        if n and g:
            lines.append({"ingredient_name": n, "grams": g, "price_per_kg": p})
    return lines


def _load_recipe_into_state(lines: list, recipe_id=None, recipe_name: str = "") -> None:
    """
    Inyecta líneas de receta en session_state.
    REC 3: usa st.toast() que sobrevive al st.rerun() posterior.
    """
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in ["ing_name_", "grams_", "price_", "_prev_ing_name_"]):
            del st.session_state[key]
    st.session_state.num_rows = max(len(lines), 4)
    for i, line in enumerate(lines):
        st.session_state[f"ing_name_{i}"] = line["ingredient_name"]
        st.session_state[f"grams_{i}"]    = float(line["grams"])
        st.session_state[f"price_{i}"]    = float(line.get("price_per_kg", 0))
    st.session_state["recipe_loaded_id"]   = recipe_id
    st.session_state["recipe_loaded_name"] = recipe_name
    st.toast(f"✅ «{recipe_name}» cargada en el Formulador", icon="🍦")


def callback_add_row():
    st.session_state.num_rows += 1


def callback_clear_all():
    for key in list(st.session_state.keys()):
        if key.startswith("ing_name_") or key.startswith("grams_") or key.startswith("price_"):
            del st.session_state[key]
    st.session_state.num_rows = 4
    st.session_state.pop("recipe_loaded_id", None)
    st.session_state.pop("recipe_loaded_name", None)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — FORMULADOR
# ═════════════════════════════════════════════════════════════════════════════
with tab_form:

    if "num_rows" not in st.session_state:
        st.session_state.num_rows = 4

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.markdown("### ⚙️ Parámetros de receta")

    recipe_name_input = st.sidebar.text_input(
        "Nombre de la receta",
        value=st.session_state.get("recipe_loaded_name", ""),
        placeholder="Ej: Choco Creami v3"
    )

    # ── REC 5: Indicador visual de receta/base activa ─────────────────────────
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

    st.sidebar.divider()

    # guardar_receta y guardar_como_base siguen dentro del tab
    # porque capturan product_type y machine del sidebar local.
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

    # ── Layout principal ──────────────────────────────────────────────────────
    col_ing, col_panel = st.columns([9, 11], gap="large")

    # ── Columna ingredientes ──────────────────────────────────────────────────
    with col_ing:
        st.markdown('<div class="section-overline">🧾 Ingredientes</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="ing-row-header">
          <span>Ingrediente</span><span>Gramos</span><span>$/kg</span>
        </div>""", unsafe_allow_html=True)

        lines_for_calculator    = []
        active_ingredient_names = []

        for i in range(st.session_state.num_rows):
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
            if ing_name and grams > 0:
                ing_obj = ingredients_map.get(ing_name)
                if ing_obj:
                    lines_for_calculator.append((ing_obj, grams, price))
                    active_ingredient_names.append(ing_name)

        st.button("＋ Agregar fila", on_click=callback_add_row, use_container_width=True)

        if lines_for_calculator:
            masa_tot  = sum(g for _, g, _ in lines_for_calculator)
            costo_tot = sum((g / 1000) * p for _, g, p in lines_for_calculator)
            st.markdown(f"""
            <div style="display:flex;gap:16px;padding:10px 14px;background:#181828;
                 border-radius:8px;margin-top:8px;border:1px solid #252540;">
              <div>
                <div style="font-size:0.68rem;color:#666;text-transform:uppercase;">Masa total</div>
                <div style="font-size:1.1rem;font-weight:700;color:#fff;">{masa_tot:.0f} g</div>
              </div>
              <div>
                <div style="font-size:0.68rem;color:#666;text-transform:uppercase;">Costo est.</div>
                <div style="font-size:1.1rem;font-weight:700;color:#fff;">${costo_tot:.2f}</div>
              </div>
            </div>""", unsafe_allow_html=True)

    # ── Columna análisis ──────────────────────────────────────────────────────
    with col_panel:
        targets_default = calc._get_targets(product_type, machine)
        config_override = st.session_state.config_params.get(f"{product_type}_{machine}", {})

        if not lines_for_calculator:
            tg = targets_default
            st.markdown('<div class="section-overline">📊 Rangos objetivo</div>', unsafe_allow_html=True)
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

        else:
            totals  = calc.calc_totals(lines_for_calculator)
            pct     = calc.calc_percentages(totals)
            derived = calc.calc_derived(
                totals, pct, product_type=product_type, machine=machine,
                lines_with_ings=lines_for_calculator,
                config=config_override or None,
            )
            kcal = calc.calc_calories(totals, lines_for_calculator)
            tg   = derived.get('targets', targets_default)

            # ── Barra de llenado del pote ─────────────────────────────────────
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

            # ── CALORÍAS ──────────────────────────────────────────────────────
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

            pote_kcal = kcal.get('kcal_per_pote_deluxe', 0) if is_creami else 0
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
                <div class="kcal-cell-val">{pote_kcal:.0f}</div>
                <div class="kcal-cell-label">kcal / pote completo</div>
              </div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;">
              {kcal_badge}
              {'<span class="badge badge-info">' + prot_class["emoji"] + " " + prot_class["etiqueta"] + " " + str(prot_class["valor"]) + "g/100g</span>" if prot_class else ""}
            </div>""", unsafe_allow_html=True)

            # ── COMPOSICIÓN CON BARRAS ────────────────────────────────────────
            _section("🧬 Composición")

            c1, c2, c3 = st.columns(3)
            with c1:
                _param_bar("Sólidos Totales", pct.get('st_pct', 0),
                           tg['st'][0], tg['st'][1], "%", scale_max=50)
            with c2:
                _param_bar("Grasa", pct.get('fat_pct', 0),
                           tg['fat'][0], tg['fat'][1], "%", scale_max=25)
            with c3:
                water_v = pct.get('water_pct', 0)
                st.markdown(f"""
                <div class="param-bar-wrap">
                  <div class="param-bar-header">
                    <span class="param-label">Agua libre</span>
                    <span class="param-value">{water_v:.1f}%</span>
                  </div>
                  <div class="param-bar-bg">
                    <div class="param-bar-fill bar-ok" style="width:{min(water_v,100):.1f}%;"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

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

            # ── CRIOSCOPÍA + Aw ───────────────────────────────────────────────
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

            # ── DIAGNÓSTICOS ──────────────────────────────────────────────────
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
                    for d in crits:
                        with st.expander(f"🔴 {d['title']}"):
                            st.markdown(f"<div style='color:#f87171;font-size:0.82rem;'>{d['tip']}</div>",
                                        unsafe_allow_html=True)
                    for d in imps:
                        with st.expander(f"🟠 {d['title']}"):
                            st.markdown(f"<div style='color:#fb923c;font-size:0.82rem;'>{d['tip']}</div>",
                                        unsafe_allow_html=True)
                    for d in adjs:
                        with st.expander(f"🔵 {d['title']}"):
                            st.markdown(f"<div style='color:#93c5fd;font-size:0.82rem;'>{d['tip']}</div>",
                                        unsafe_allow_html=True)

            # ── OVERRUN ───────────────────────────────────────────────────────
            _section("📐 Rendimiento / Overrun")
            or_d = calc.overrun_calc(totals["grams"], overrun_pct, target_liters, machine)
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

            # ── VALIDACIÓN BRIX ───────────────────────────────────────────────
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

            # ── ESTABILIZANTES ────────────────────────────────────────────────
            _section("🧪 Estabilizantes recomendados")
            stab_recs = calc.recommend_stabilizers(
                totals, pct, product_type, machine,
                ingredient_names=active_ingredient_names
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

            # ── EDULCORANTES ──────────────────────────────────────────────────
            sw_data = calc.analyze_sweeteners(lines_for_calculator)
            if sw_data:
                _section("🍬 Edulcorantes")
                for sw in sw_data:
                    if sw.get('warning'):
                        st.markdown(
                            f"<div style='font-size:0.8rem;color:#fb923c;'>{sw['warning']}</div>",
                            unsafe_allow_html=True
                        )
                    st.markdown(
                        f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:2px;'>"
                        f"<b style='color:#fff;'>{sw['nombre']}</b> · "
                        f"POD {sw['pod_contrib']:.0f} ({sw['pct_pod']:.0f}%) · "
                        f"PAC {sw['pac_contrib']:.0f} ({sw['pct_pac']:.0f}%) · "
                        f"{sw['efecto_sabor']}</div>",
                        unsafe_allow_html=True
                    )

            # ── PROTEÍNAS ─────────────────────────────────────────────────────
            prot_data = calc.analyze_protein(lines_for_calculator, totals, pct, product_type)
            if prot_data and prot_data.get('fuentes'):
                _section("💪 Proteínas")
                for f in prot_data['fuentes']:
                    st.markdown(
                        f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:2px;'>"
                        f"<b style='color:#fff;'>{f['nombre']}</b> · "
                        f"{f.get('proteina_g', 0):.1f} g proteína</div>",
                        unsafe_allow_html=True
                    )
                if prot_data.get('sugerencias'):
                    for s in prot_data['sugerencias']:
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:#60a5fa;'>{s['text']}</div>",
                            unsafe_allow_html=True
                        )

            # ── EXPORTAR ──────────────────────────────────────────────────────
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
        all_recipes = db.get_all_recipes(recipes_only=True)
    except Exception as e:
        st.error(f"Error: {e}")
        all_recipes = []

    if not all_recipes:
        st.info("Aún no tienes recetas guardadas.")
    else:
        search = st.text_input("🔍 Buscar receta", placeholder="Nombre...")
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
                    # REC 3: carga simplificada — elimina 12 líneas de código duplicado
                    if st.button("📂 Cargar", key=f"load_{rec['id']}", use_container_width=True):
                        full = db.get_recipe(rec["id"])
                        if full:
                            _load_recipe_into_state(
                                full.get("lines", []),
                                recipe_id=rec["id"],
                                recipe_name=rec["name"]
                            )
                            st.rerun()
                    if st.button("🗑️ Eliminar", key=f"del_{rec['id']}", use_container_width=True):
                        db.delete_recipe(rec["id"])
                        st.warning(f"«{rec['name']}» eliminada.")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — BASES DE HELADO
# ═════════════════════════════════════════════════════════════════════════════
with tab_bases:
    st.subheader("🧫 Bases de Helado")
    st.caption("Formulaciones reutilizables que aparecen como ingredientes en el formulador (prefijo 🧪).")

    try:
        all_bases = db.get_all_recipes(bases_only=True)
    except Exception as e:
        st.error(f"Error: {e}")
        all_bases = []

    if not all_bases:
        st.info("No tienes bases guardadas. Formula en 🧪 y pulsa **Guardar como Base**.")
    else:
        search_base = st.text_input("🔍 Buscar", placeholder="Nombre de la base...")
        if search_base:
            all_bases = [b for b in all_bases if search_base.lower() in b["name"].lower()]

        for base in all_bases:
            full  = db.get_recipe(base["id"])
            lines = full.get("lines", []) if full else []
            ings_comp = [(ingredients_map[l["ingredient_name"]], float(l["grams"]), 0)
                         for l in lines if l["ingredient_name"] in ingredients_map and l["grams"]]
            comp_str = ""
            if ings_comp:
                try:
                    t = calc.calc_totals(ings_comp)
                    p = calc.calc_percentages(t)
                    comp_str = (f"ST {p.get('st_pct',0):.1f}% · Grasa {p.get('fat_pct',0):.1f}% · "
                                f"MSNF {p.get('msnf_pct',0):.1f}% · Azúcar {p.get('sugars_pct',0):.1f}% · "
                                f"Agua {p.get('water_pct',0):.1f}%")
                except Exception:
                    comp_str = ""

            with st.expander(f"🧫 **{base['name']}** — {base.get('base_grams',0):.0f}g · {base['product_type']}"):
                if comp_str:
                    st.caption(f"📊 {comp_str}")
                st.caption(f"Guardada: {base.get('updated_at','')[:16]}")
                if lines:
                    for line in lines:
                        st.write(f"  · {line['ingredient_name']}: {float(line['grams']):.1f} g")
                col_a, col_b, col_c = st.columns(3)
                # REC 3: carga simplificada
                if col_a.button("📂 Cargar", key=f"loadbase_{base['id']}", use_container_width=True):
                    _load_recipe_into_state(lines, recipe_id=None, recipe_name=base["name"])
                    st.rerun()
                if col_b.button("📋 Duplicar", key=f"dupbase_{base['id']}", use_container_width=True):
                    db.save_recipe({"name": f"{base['name']} (copia)", "product_type": base["product_type"],
                                    "machine": base["machine"], "base_grams": base.get("base_grams", 0),
                                    "notes": "Copia de base", "is_base": 0, "lines": lines})
                    st.success("✅ Copia guardada en Mis Recetas.")
                if col_c.button("🗑️ Eliminar", key=f"delbase_{base['id']}", use_container_width=True):
                    db.delete_recipe(base["id"])
                    _invalidate_ingredient_cache()
                    st.warning(f"Base «{base['name']}» eliminada.")
                    st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — GESTIÓN DE INGREDIENTES
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
        search_ing = st.text_input("🔍 Buscar", key="search_ing", placeholder="Nombre o categoría...")
        cats = sorted(set(i["category"] for i in all_ings))
        cat_filter = st.selectbox("Filtrar por categoría", ["Todas"] + cats, key="cat_filter")
        filtered = all_ings
        if search_ing:
            filtered = [i for i in filtered if search_ing.lower() in i["name"].lower()
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
                    if st.button("✏️ Editar", key=f"btn_edit_{ing['id']}", use_container_width=True):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                    if st.button("🗑️ Eliminar", key=f"btn_del_ing_{ing['id']}", use_container_width=True):
                        db.delete_ingredient(ing["id"])
                        _invalidate_ingredient_cache()
                        st.warning(f"«{ing['name']}» eliminado.")
                if st.session_state.get(edit_key, False):
                    with st.form(f"form_edit_{ing['id']}"):
                        e_name = st.text_input("Nombre", value=ing['name'])
                        cat_opts = INGREDIENT_CATEGORIES.copy()
                        if ing['category'] not in cat_opts:
                            cat_opts = [ing['category']] + cat_opts
                        e_cat = st.selectbox("Categoría", cat_opts, index=cat_opts.index(ing['category']))
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
                        sv, cn = st.columns(2)
                        if sv.form_submit_button("💾 Guardar", use_container_width=True):
                            db.update_ingredient(ing['id'], {**ing, "name": e_name.strip(),
                                "category": e_cat, "fat": e_fat, "msnf": e_msnf, "sugars": e_sug,
                                "other_st": e_ost, "pod": e_pod, "pac": e_pac, "water": e_water,
                                "notes": e_notes, "price_per_kg": e_price})
                            _invalidate_ingredient_cache()
                            st.session_state[edit_key] = False
                            st.rerun()
                        if cn.form_submit_button("✖ Cancelar", use_container_width=True):
                            st.session_state[edit_key] = False
                            st.rerun()

    with sub_nuevo:
        st.write("### Agregar ingrediente nuevo")
        with st.form("form_nuevo_ing"):
            n_name = st.text_input("Nombre *", placeholder="Ej: Leche de almendra sin azúcar")
            n_cat  = st.selectbox("Categoría *", INGREDIENT_CATEGORIES)
            st.write("**Composición centesimal (%)**")
            col1, col2, col3, col4 = st.columns(4)
            n_fat   = col1.number_input("Grasa %",    0.0, 100.0, 0.0, step=0.1)
            n_msnf  = col2.number_input("MSNF %",     0.0, 100.0, 0.0, step=0.1)
            n_sug   = col3.number_input("Azúcares %", 0.0, 100.0, 0.0, step=0.1)
            n_water = col4.number_input("Agua %",     0.0, 100.0, 0.0, step=0.1)
            col5, col6, col7, col8 = st.columns(4)
            n_ost   = col5.number_input("Otros ST %", 0.0, 100.0, 0.0, step=0.1)
            n_pod   = col6.number_input("POD",        0.0, 10.0,  0.0, step=0.01)
            n_pac   = col7.number_input("PAC",        0.0, 10.0,  0.0, step=0.01)
            n_price = col8.number_input("Precio/kg $", 0.0, step=0.5)
            n_notes  = st.text_area("Notas técnicas")
            n_func   = st.text_input("Función principal")
            n_zero_c = st.checkbox("Zero calorie (eritritol, alulosa, stevia…)")
            suma = n_fat + n_msnf + n_sug + n_ost + n_water
            if suma > 0:
                st.caption(f"Suma: **{suma:.1f}%** {'✅' if 98 <= suma <= 102 else '⚠️ debería ser ~100%'}")
            if st.form_submit_button("➕ Agregar ingrediente", use_container_width=True):
                if not n_name.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    try:
                        db.save_ingredient({"name": n_name.strip(), "category": n_cat,
                            "fat": n_fat, "msnf": n_msnf, "sugars": n_sug, "other_st": n_ost,
                            "pod": n_pod, "pac": n_pac, "water": n_water, "notes": n_notes,
                            "function": n_func, "brix": 0, "ph": 0, "price_per_kg": n_price,
                            "calories_per_100g": 0, "zero_calorie": 1 if n_zero_c else 0})
                        _invalidate_ingredient_cache()
                        st.success(f"✅ «{n_name}» agregado como [{n_cat}].")
                    except Exception as e:
                        st.error(f"Error: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — CONFIGURACIÓN
# ═════════════════════════════════════════════════════════════════════════════
with tab_config:
    st.subheader("⚙️ Configuración de Parámetros")
    st.markdown("Ajusta los **rangos objetivo** por tipo de producto y máquina. "
                "Útil para calibrar según tus catas. Los cambios se aplican inmediatamente "
                "**y se guardan en la base de datos** (persisten entre sesiones).")

    cfg_product = st.selectbox("Tipo de producto", PRODUCT_TYPES, key="cfg_product")
    cfg_machine = st.selectbox("Máquina",          MACHINES,      key="cfg_machine")
    cfg_key     = f"{cfg_product}_{cfg_machine}"
    defaults    = calc._get_targets(cfg_product, cfg_machine)
    saved_cfg   = st.session_state.config_params.get(cfg_key, {})

    def cfg_val(k, idx):
        return saved_cfg.get(k, defaults[k])[idx] if k in defaults else 0.0

    # Indicador visual de config personalizada activa
    if saved_cfg:
        st.markdown(
            f'<div class="badge badge-info">⚙️ Config personalizada activa para '
            f'{cfg_product} · {cfg_machine}</div>',
            unsafe_allow_html=True
        )
        st.markdown("")

    st.write(f"#### Rangos para: **{cfg_product}** · **{cfg_machine}**")

    with st.form("form_config"):
        c1, c2 = st.columns(2)
        st_lo  = c1.number_input("ST mín %",    0.0, 60.0, float(cfg_val('st', 0)), step=0.5)
        st_hi  = c2.number_input("ST máx %",    0.0, 60.0, float(cfg_val('st', 1)), step=0.5)
        c1, c2 = st.columns(2)
        fat_lo = c1.number_input("Grasa mín %", 0.0, 40.0, float(cfg_val('fat', 0)), step=0.5)
        fat_hi = c2.number_input("Grasa máx %", 0.0, 40.0, float(cfg_val('fat', 1)), step=0.5)
        c1, c2 = st.columns(2)
        msnf_lo= c1.number_input("MSNF mín %",  0.0, 20.0, float(cfg_val('msnf', 0)), step=0.5)
        msnf_hi= c2.number_input("MSNF máx %",  0.0, 20.0, float(cfg_val('msnf', 1)), step=0.5)
        c1, c2 = st.columns(2)
        sug_lo = c1.number_input("Azúcares mín %", 0.0, 40.0, float(cfg_val('sugars', 0)), step=0.5)
        sug_hi = c2.number_input("Azúcares máx %", 0.0, 40.0, float(cfg_val('sugars', 1)), step=0.5)
        c1, c2 = st.columns(2)
        pod_lo = c1.number_input("POD mín",     0.0, 300.0, float(cfg_val('pod', 0)), step=5.0)
        pod_hi = c2.number_input("POD máx",     0.0, 300.0, float(cfg_val('pod', 1)), step=5.0)
        c1, c2 = st.columns(2)
        pac_lo = c1.number_input("PAC mín",     0.0, 500.0, float(cfg_val('pac', 0)), step=5.0)
        pac_hi = c2.number_input("PAC máx",     0.0, 500.0, float(cfg_val('pac', 1)), step=5.0)
        c1, c2 = st.columns(2)
        stw_lo = c1.number_input("ST/Agua mín", 0.0,   2.0, float(cfg_val('st_water', 0)), step=0.01)
        stw_hi = c2.number_input("ST/Agua máx", 0.0,   2.0, float(cfg_val('st_water', 1)), step=0.01)

        cs, cr = st.columns(2)
        if cs.form_submit_button("💾 Guardar", use_container_width=True):
            nueva_cfg = {
                'st':       (st_lo,   st_hi),
                'fat':      (fat_lo,  fat_hi),
                'msnf':     (msnf_lo, msnf_hi),
                'sugars':   (sug_lo,  sug_hi),
                'pod':      (pod_lo,  pod_hi),
                'pac':      (pac_lo,  pac_hi),
                'st_water': (stw_lo,  stw_hi),
            }
            # REC 1: guardar en session_state Y persistir en BD
            st.session_state.config_params[cfg_key] = nueva_cfg
            try:
                db.set_user_config(cfg_key, nueva_cfg)
                st.success(f"✅ Guardado para {cfg_product} · {cfg_machine} — persistido en BD")
            except Exception as e:
                st.warning(f"⚠️ Guardado en sesión, pero falló BD: {e}")

        if cr.form_submit_button("🔄 Restaurar defaults", use_container_width=True):
            if cfg_key in st.session_state.config_params:
                del st.session_state.config_params[cfg_key]
            try:
                db.delete_user_config(cfg_key)
                st.success("✅ Defaults restaurados y eliminados de BD")
            except Exception:
                st.success("✅ Defaults restaurados")
