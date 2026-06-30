import streamlit as st
import database as db
from .components import _load_recipe_into_state


def render(tab):
    with tab:
        st.markdown('<div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:4px;">📁 Mis Recetas</div>', unsafe_allow_html=True)
        try:
            all_recipes = db.get_all_recipes(recipes_only=True)
        except Exception as e:
            st.error(f"Error: {e}")
            all_recipes = []

        if not all_recipes:
            st.info("Aún no tienes recetas guardadas.")
            return

        search = st.text_input("🔍 Buscar receta", placeholder="Nombre...")
        if search:
            all_recipes = [r for r in all_recipes if search.lower() in r["name"].lower()]

        for rec in all_recipes:
            with st.expander(f"**{rec['name']}** — {rec['product_type']} · {rec['machine']}"):
                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f"<div style='font-size:0.75rem;color:#555;'>Guardada: {rec.get('updated_at','')[:16]}</div>"
                        f"<div style='font-size:0.88rem;color:#ccc;margin-top:3px;'>"
                        f"Base: <b style='color:#fff;'>{rec.get('base_grams',0):.0f} g</b>"
                        f" &nbsp;·&nbsp; {rec['product_type']} · {rec['machine']}</div>"
                        + (f"<div style='font-size:0.78rem;color:#666;margin-top:2px;'>{rec['notes']}</div>"
                           if rec.get('notes') else ""),
                        unsafe_allow_html=True
                    )
                with col_actions:
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
