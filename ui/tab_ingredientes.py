import streamlit as st
import database as db
from constants import INGREDIENT_CATEGORIES
from .components import _invalidate_ingredient_cache


def render(tab):
    with tab:
        st.markdown('<div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:4px;">🗄️ Ingredientes</div>', unsafe_allow_html=True)
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
                        st.markdown(
                            f"<div style='font-size:0.82rem;color:#aaa;'>"
                            f"Grasa <b style='color:#fff;'>{ing['fat']}%</b> &nbsp;·&nbsp; "
                            f"MSNF <b style='color:#fff;'>{ing['msnf']}%</b> &nbsp;·&nbsp; "
                            f"Azúcares <b style='color:#fff;'>{ing['sugars']}%</b> &nbsp;·&nbsp; "
                            f"Agua <b style='color:#fff;'>{ing['water']}%</b></div>"
                            f"<div style='font-size:0.82rem;color:#aaa;margin-top:3px;'>"
                            f"POD <b style='color:#fff;'>{ing['pod']}</b> &nbsp;·&nbsp; "
                            f"PAC <b style='color:#fff;'>{ing['pac']}</b> &nbsp;·&nbsp; "
                            f"Otros ST <b style='color:#fff;'>{ing['other_st']}%</b>"
                            + (f" &nbsp;·&nbsp; <b style='color:#4ade80;'>${ing['price_per_kg']:.2f}/kg</b>"
                               if ing.get('price_per_kg', 0) else "")
                            + "</div>"
                            + (f"<div style='font-size:0.75rem;color:#555;margin-top:2px;'>{ing['notes']}</div>"
                               if ing.get('notes') else ""),
                            unsafe_allow_html=True
                        )
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
            st.markdown('<div style="font-size:1rem;font-weight:700;color:#fff;margin-bottom:8px;">➕ Agregar ingrediente nuevo</div>', unsafe_allow_html=True)
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
