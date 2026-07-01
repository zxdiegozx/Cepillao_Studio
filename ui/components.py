import streamlit as st
import plotly.graph_objects as go
import calculator as calc


def _param_bar(label, val, lo, hi, unit="%", scale_max=None):
    s = calc._status(val, lo, hi)
    if scale_max is None:
        scale_max = (hi or 10) * 1.5

    fill_pct = min(max(val / scale_max * 100, 0), 100) if scale_max else 0
    zone_lo  = (lo or 0) / scale_max * 100 if scale_max else 0
    zone_hi  = min((hi or scale_max) / scale_max * 100, 100) if scale_max else 100
    zone_w   = max(zone_hi - zone_lo, 0)

    val_str = f"{val:.0f}" if unit == "" else f"{val:.1f}"

    # Paleta por estado
    _C = {
        "ok":    ("linear-gradient(90deg,#16a34a,#22c55e,#4ade80)",
                  "rgba(34,197,94,0.18)", "#4ade80",
                  f"✓ En rango"),
        "low":   ("linear-gradient(90deg,#1e3a8a,#3b82f6,#93c5fd)",
                  "rgba(59,130,246,0.18)", "#93c5fd",
                  f"↑ bajo {lo}{unit}"),
        "high":  ("linear-gradient(90deg,#7f1d1d,#ef4444,#fca5a5)",
                  "rgba(239,68,68,0.18)", "#fca5a5",
                  f"↓ sobre {hi}{unit}"),
        "empty": ("linear-gradient(90deg,#1e1e38,#2d2d50)",
                  "rgba(80,80,120,0.08)", "#444",
                  "—"),
    }
    grad, badge_bg, badge_fg, badge_txt = _C[s]

    st.markdown(f"""
<div class="pbar-wrap">
  <div class="pbar-header">
    <span class="pbar-label">{label}</span>
    <div style="display:flex;align-items:center;gap:8px;">
      <span class="pbar-value">{val_str}{unit}</span>
      <span style="font-size:0.6rem;font-weight:700;letter-spacing:0.06em;
             text-transform:uppercase;padding:2px 8px;border-radius:999px;
             background:{badge_bg};color:{badge_fg};">{badge_txt}</span>
    </div>
  </div>
  <div style="position:relative;height:10px;margin:2px 0 6px;">
    <div style="position:absolute;inset:0;background:#0d0d1a;border-radius:999px;overflow:hidden;">
      <div style="position:absolute;top:0;bottom:0;
                  left:{zone_lo:.2f}%;width:{zone_w:.2f}%;
                  background:rgba(34,197,94,0.07);
                  border-left:1.5px solid rgba(34,197,94,0.28);
                  border-right:1.5px solid rgba(34,197,94,0.28);"></div>
      <div style="position:absolute;top:0;bottom:0;left:0;
                  width:{fill_pct:.2f}%;
                  background:{grad};
                  border-radius:999px;"></div>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;">
    <span style="font-size:0.58rem;color:#3a3a55;">0</span>
    <span style="font-size:0.58rem;color:#3a5a3a;letter-spacing:0.03em;">óptimo {lo}–{hi}{unit}</span>
    <span style="font-size:0.58rem;color:#3a3a55;">{scale_max:.0f}{unit}</span>
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
    num_rows = st.session_state.get("num_rows", 4)
    # Guard: num_rows puede llegar como float o None si el state se corrompe
    try:
        num_rows = int(num_rows)
    except (TypeError, ValueError):
        num_rows = 4
    for i in range(num_rows):
        n = st.session_state.get(f"ing_name_{i}", "") or ""
        g = st.session_state.get(f"grams_{i}", 0.0)
        p = st.session_state.get(f"price_{i}", 0.0)
        # Guard: grams puede llegar como None o NaN cuando el widget falla
        try:
            g = float(g) if g is not None else 0.0
            p = float(p) if p is not None else 0.0
        except (TypeError, ValueError):
            g, p = 0.0, 0.0
        if n and g > 0:
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
    try:
        current = int(st.session_state.get("num_rows") or 4)
    except (TypeError, ValueError):
        current = 4
    st.session_state.num_rows = current + 1


def callback_clear_all():
    for key in list(st.session_state.keys()):
        if key.startswith("ing_name_") or key.startswith("grams_") or key.startswith("price_"):
            del st.session_state[key]
    st.session_state.num_rows = 4
    st.session_state.pop("recipe_loaded_id", None)
    st.session_state.pop("recipe_loaded_name", None)
