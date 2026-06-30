import streamlit as st
import calculator as calc
import database as db
from constants import PRODUCT_TYPES, MACHINES


def render(tab):
    with tab:
        st.markdown('<div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:4px;">⚙️ Configuración de Parámetros</div>', unsafe_allow_html=True)
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

        if saved_cfg:
            st.markdown(
                f'<div class="badge badge-info">⚙️ Config personalizada activa para '
                f'{cfg_product} · {cfg_machine}</div>',
                unsafe_allow_html=True
            )
            st.markdown("")

        st.markdown(
            f'<div style="font-size:0.92rem;font-weight:600;color:#fff;margin:8px 0;">'
            f'Rangos para <span style="color:#60a5fa;">{cfg_product}</span>'
            f' · <span style="color:#60a5fa;">{cfg_machine}</span></div>',
            unsafe_allow_html=True
        )

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
