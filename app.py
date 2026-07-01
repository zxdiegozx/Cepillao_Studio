import streamlit as st
import pathlib
import database as db
from ui import (
    render_formulador,
    render_recetas,
    render_bases,
    render_ingredientes,
    render_config,
)

st.set_page_config(
    page_title="Cepillao' Gelato Studio",
    layout="wide",
    page_icon="🍦"
)

# ── Base de datos ─────────────────────────────────────────────────────────────
try:
    db.init_db()
except Exception as e:
    st.error(f"Error de base de datos: {e}")

# ── Cache de ingredientes ─────────────────────────────────────────────────────
if "ing_cache_version" not in st.session_state:
    st.session_state.ing_cache_version = 0

@st.cache_data(ttl=300)
def _load_ingredients(version: int):
    try:
        return db.get_all_ingredients()
    except Exception:
        return []

ingredients_raw = _load_ingredients(st.session_state.ing_cache_version)
try:
    _bases_as_ings = db.get_bases_as_ingredients()
except Exception:
    _bases_as_ings = []

ingredients_map  = {ing['name']: ing for ing in ingredients_raw}
for b in _bases_as_ings:
    ingredients_map[b['name']] = b
ingredient_names = sorted(ingredients_map.keys())

# ── Config de usuario ─────────────────────────────────────────────────────────
if "config_params" not in st.session_state:
    try:
        st.session_state.config_params = db.get_user_config()
    except Exception:
        st.session_state.config_params = {}

# ── CSS ───────────────────────────────────────────────────────────────────────
_css_file = pathlib.Path(__file__).parent / ".streamlit" / "custom.css"
if _css_file.exists():
    st.markdown(f"<style>{_css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
else:
    st.warning("⚠️ .streamlit/custom.css no encontrado — estilos desactivados.")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <span class="app-header-logo">🍦</span>
  <div>
    <div class="app-header-title">Cepillao' Gelato Studio</div>
    <div class="app-header-sub">Motor científico · helados, gelato &amp; sorbetes</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_form, tab_recetas, tab_bases, tab_ingredientes, tab_config = st.tabs([
    "🧪 Formulador",
    "📁 Mis Recetas",
    "🧫 Bases de Helado",
    "🗄️ Ingredientes",
    "⚙️ Configuración",
])

render_formulador(tab_form,        ingredients_map, ingredient_names)
render_recetas(tab_recetas)
render_bases(tab_bases,            ingredients_map)
render_ingredientes(tab_ingredientes)
render_config(tab_config)
