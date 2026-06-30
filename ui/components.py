import streamlit as st
import plotly.graph_objects as go
import calculator as calc


def _param_bar(label, val, lo, hi, unit="%", scale_max=None):
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


def _radar_chart(pct: dict, tg: dict):
    labels   = ['ST', 'Grasa', 'MSNF', 'Azúcares', 'POD', 'PAC']
    pct_keys = ['st_pct', 'fat_pct', 'msnf_pct', 'sugars_pct', 'pod_total', 'pac_total']
    tg_keys  = ['st', 'fat', 'msnf', 'sugars', 'pod', 'pac']
    smaxes   = [50, 25, 15, 35, 280, 400]

    vals  = [pct.get(k, 0) for k in pct_keys]
    tg_lo = [tg[k][0]      for k in tg_keys]
    tg_hi = [tg[k][1]      for k in tg_keys]

    def n(v, sm): return min(v / sm * 100, 100) if sm else 0

    r_vals = [n(v, sm) for v, sm in zip(vals,  smaxes)]
    r_lo   = [n(v, sm) for v, sm in zip(tg_lo, smaxes)]
    r_hi   = [n(v, sm) for v, sm in zip(tg_hi, smaxes)]
    theta  = labels + [labels[0]]

    hover_vals = (
        [f"ST {vals[0]:.1f}%", f"Grasa {vals[1]:.1f}%", f"MSNF {vals[2]:.1f}%",
         f"Azúcares {vals[3]:.1f}%", f"POD {vals[4]:.0f}", f"PAC {vals[5]:.0f}"]
    )

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_hi + [r_hi[0]], theta=theta, fill='none',
        line=dict(color='rgba(74,222,128,0.45)', width=1.5, dash='dot'),
        name='Máx objetivo', hoverinfo='skip',
    ))
    fig.add_trace(go.Scatterpolar(
        r=r_lo + [r_lo[0]], theta=theta, fill='none',
        line=dict(color='rgba(74,222,128,0.25)', width=1, dash='dot'),
        name='Mín objetivo', hoverinfo='skip',
    ))
    fig.add_trace(go.Scatterpolar(
        r=r_vals + [r_vals[0]], theta=theta,
        fill='toself', fillcolor='rgba(96,165,250,0.18)',
        line=dict(color='#60a5fa', width=2),
        name='Receta',
        text=hover_vals + [hover_vals[0]],
        hovertemplate='%{text}<extra></extra>',
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100],
                            showticklabels=False, gridcolor='#2d2d44'),
            angularaxis=dict(tickfont=dict(size=11, color='#aaa'), gridcolor='#2d2d44'),
            bgcolor='rgba(30,30,46,0.6)',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.22,
            xanchor='center', x=0.5,
            font=dict(size=10, color='#aaa'),
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(l=55, r=55, t=15, b=55),
        height=290,
    )
    return fig


def _collect_lines():
    lines = []
    for i in range(st.session_state.get("num_rows", 4)):
        n = st.session_state.get(f"ing_name_{i}", "")
        g = st.session_state.get(f"grams_{i}", 0.0)
        p = st.session_state.get(f"price_{i}", 0.0)
        if n and g:
            lines.append({"ingredient_name": n, "grams": g, "price_per_kg": p})
    return lines


def _load_recipe_into_state(lines: list, recipe_id=None, recipe_name: str = "") -> None:
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


def _invalidate_ingredient_cache():
    st.session_state.ing_cache_version += 1


def callback_add_row():
    st.session_state.num_rows += 1


def callback_clear_all():
    for key in list(st.session_state.keys()):
        if key.startswith("ing_name_") or key.startswith("grams_") or key.startswith("price_"):
            del st.session_state[key]
    st.session_state.num_rows = 4
    st.session_state.pop("recipe_loaded_id", None)
    st.session_state.pop("recipe_loaded_name", None)
