import streamlit as st
import calculator as calc
import database as db
from .components import _load_recipe_into_state, _invalidate_ingredient_cache


def render(tab, ingredients_map: dict):
    with tab:
        st.markdown('<div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:4px;">🧫 Bases de Helado</div>', unsafe_allow_html=True)
        st.caption("Formulaciones reutilizables que aparecen como ingredientes en el formulador (prefijo 🧪).")

        try:
            all_bases = db.get_all_recipes(bases_only=True)
        except Exception as e:
            st.error(f"Error: {e}")
            all_bases = []

        if not all_bases:
            st.info("No tienes bases guardadas. Formula en 🧪 y pulsa **Guardar como Base**.")
            return

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
