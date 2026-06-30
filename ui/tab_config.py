"""
tab_config.py — Tab 5: Configuración de rangos objetivo por tipo/máquina.

CAMBIOS EN ESTA VERSIÓN
───────────────────────
El botón "Guardar" ya NO confía ciegamente en la BD. Antes:
    db.set_user_config() tragaba toda excepción (except: pass) y la UI
    SIEMPRE mostraba "✅ persistido en BD", aunque el write hubiera
    fallado. Resultado: badge verde mentiroso → el dato se perdía al
    refrescar y no había forma de saberlo.

Ahora set_user_config() retorna bool (True solo si el read-back confirma
la escritura). Si retorna False, mostramos un diagnóstico real con la
ruta de la DB y si el volumen de Railway está montado, para distinguir
"bug de código" de "volumen mal configurado".

DEPENDE DE: database.py debe exponer set_user_config()->bool,
            delete_user_config()->bool y db_health()->dict.
"""

import streamlit as st
import calculator as calc
import database as db
from constants import PRODUCT_TYPES, MACHINES


def render(tab):
    with tab:
        st.markdown(
            '<div style="font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:4px;">'
            '⚙️ Configuración de Parámetros</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            "Ajusta los **rangos objetivo** por tipo de producto y máquina. "
            "Útil para calibrar según tus catas. Los cambios se aplican inmediatamente "
            "**y se guardan en la base de datos** (persisten entre sesiones)."
        )

        cfg_product = st.selectbox("Tipo de producto", PRODUCT_TYPES, key="cfg_product")
        cfg_machine = st.selectbox("Máquina",          MACHINES,      key="cfg_machine")
        cfg_key     = f"{cfg_product}_{cfg_machine}"
        defaults    = calc._get_targets(cfg_product, cfg_machine)
        saved_cfg   = st.session_state.config_params.get(cfg_key, {})

        def cfg_val(k, idx):
            # saved_cfg viene de BD como listas (round-trip JSON tupla→lista);
            # ambos soportan indexado, así que [idx] funciona en los dos casos.
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
            msnf_lo = c1.number_input("MSNF mín %", 0.0, 20.0, float(cfg_val('msnf', 0)), step=0.5)
            msnf_hi = c2.number_input("MSNF máx %", 0.0, 20.0, float(cfg_val('msnf', 1)), step=0.5)
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

            # ── GUARDAR ────────────────────────────────────────────────────────
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
                # Sesión primero: efecto inmediato en ESTA sesión aunque la BD falle.
                st.session_state.config_params[cfg_key] = nueva_cfg

                # Persistencia VERIFICADA: set_user_config ahora retorna bool real
                # (True solo si el read-back confirmó la escritura en disco).
                if db.set_user_config(cfg_key, nueva_cfg):
                    st.success(
                        f"✅ Guardado y VERIFICADO en BD — {cfg_product} · {cfg_machine}"
                    )
                else:
                    # El dato vive en sesión pero NO sobrevive a un refresh.
                    # Mostramos el porqué real en vez de un falso éxito.
                    try:
                        h = db.db_health()
                    except Exception:
                        h = {"db_path": "?", "volume_mounted": "?", "writable": "?"}
                    st.error(
                        "⚠️ Guardado SOLO en sesión — la BD rechazó la escritura, "
                        "**no sobrevive al refrescar**.\n\n"
                        f"• Ruta DB: `{h.get('db_path')}`\n"
                        f"• Volumen montado: **{h.get('volume_mounted')}**\n"
                        f"• Directorio escribible: **{h.get('writable')}**\n\n"
                        "Si 'Volumen montado' es False en Railway: agrega un Volume "
                        "y confirma que `RAILWAY_VOLUME_MOUNT_PATH` se inyecta. "
                        "Si es True y escribible pero igual falla, revisa el log "
                        "del servidor (set_user_config imprime la excepción)."
                    )

            # ── RESTAURAR DEFAULTS ─────────────────────────────────────────────
            if cr.form_submit_button("🔄 Restaurar defaults", use_container_width=True):
                st.session_state.config_params.pop(cfg_key, None)
                if db.delete_user_config(cfg_key):
                    st.success("✅ Defaults restaurados y eliminados de BD")
                else:
                    st.warning(
                        "Restaurado en sesión, pero el borrado en BD falló — "
                        "podría reaparecer al refrescar. Revisa el log del servidor."
                    )
