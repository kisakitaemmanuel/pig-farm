"""
PigFarm Dashboard — Streamlit
Run with:  streamlit run pigfarm_dashboard.py
Install:   pip install streamlit pandas plotly numpy
"""

import math
import random
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PigFarm Dashboard",
    page_icon="🐷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;900&family=DM+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #020617;
    color: #f1f5f9;
}
.block-container { padding-top: 1.5rem; max-width: 1100px; }

/* Metric cards */
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 16px 18px;
}
.price-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 10px;
}
.rec-badge {
    display: inline-block;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 3px 8px;
    border-radius: 20px;
}
.section-header {
    font-size: 15px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 12px;
}
div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 14px 18px;
}
div[data-testid="stMetricValue"] { color: #f59e0b; font-weight: 800; }
div[data-testid="stMetricLabel"] { color: #64748b; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
TOTAL_RATIO = 2.2
DAILY_FEED_PER_PIG = 2.5
HERD_SIZE = 100
DAILY_TOTAL_FEED = DAILY_FEED_PER_PIG * HERD_SIZE  # 250 kg

COMMODITIES = [
    {"id": "maize",         "label": "Maize (Grain)",       "unit": "kg",   "emoji": "🌽", "color": "#f59e0b"},
    {"id": "maize_bran",    "label": "Maize Bran",          "unit": "kg",   "emoji": "🟤", "color": "#d97706"},
    {"id": "cassava_flour", "label": "Cassava Flour",       "unit": "kg",   "emoji": "🍠", "color": "#84cc16"},
    {"id": "soya_beans",    "label": "Soya Beans",          "unit": "kg",   "emoji": "🫘", "color": "#22c55e"},
    {"id": "mukene",        "label": "Mukene (Silver Fish)","unit": "kg",   "emoji": "🐟", "color": "#38bdf8"},
    {"id": "pig_medicine",  "label": "Pig Medicine",        "unit": "dose", "emoji": "💊", "color": "#a78bfa"},
]

MEDICINES = [
    {"name": "Ivermectin (100ml)",       "price": 28000, "per": "bottle", "doses": 2},
    {"name": "Amoxicillin (500mg×100)",  "price": 45000, "per": "pack",   "doses": 1},
    {"name": "Multivitamin Injection",   "price": 22000, "per": "bottle", "doses": 3},
    {"name": "Dewormer (Albendazole)",   "price": 18000, "per": "pack",   "doses": 2},
    {"name": "ASF Vaccine (50 doses)",   "price": 95000, "per": "vial",   "doses": 2},
    {"name": "Foot & Mouth Vaccine",     "price": 72000, "per": "vial",   "doses": 2},
]

BASE_PRICES = {
    "maize": 1200, "maize_bran": 850, "cassava_flour": 900,
    "soya_beans": 2800, "mukene": 4500, "pig_medicine": 1800,
}

SOURCES = ["Farmgain Africa", "Tridge"]

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def fmt_ugx(n: float) -> str:
    return f"UGX {int(round(n)):,}"

def get_rec(change: float, forecast: list, current: float) -> dict:
    if not forecast:
        return {"label": "NEUTRAL", "color": "#94a3b8", "bg": "#1e293b"}
    fc_change = ((forecast[0]["forecast"] - current) / current) * 100
    if change < -3 and fc_change > 5:
        return {"label": "BUY NOW",  "color": "#22c55e", "bg": "#052e16"}
    if change < 0:
        return {"label": "GOOD BUY","color": "#86efac", "bg": "#14532d"}
    if change > 5:
        return {"label": "HOLD OFF","color": "#f87171", "bg": "#450a0a"}
    if fc_change > 10:
        return {"label": "BUY SOON","color": "#fbbf24", "bg": "#422006"}
    return {"label": "NEUTRAL",  "color": "#94a3b8", "bg": "#1e293b"}

# ─── DATA GENERATION ──────────────────────────────────────────────────────────
@st.cache_data
def seed_prices():
    now = datetime.now()
    all_data = {}
    for c in COMMODITIES:
        cid = c["id"]
        base = BASE_PRICES[cid]
        history = []
        for i in range(90):
            days_ago = 89 - i
            t = days_ago / 89
            seasonal = math.sin((t + len(cid) * 0.1) * math.pi * 2) * base * 0.08
            trend    = (random.random() - 0.48) * base * 0.003 * days_ago
            noise    = (random.random() - 0.5) * base * 0.04
            price    = max(int(base + seasonal + trend + noise), int(base * 0.6))
            date     = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            history.append({"date": date, "price": price,
                             "source": random.choice(SOURCES)})
        current = history[-1]["price"]
        prev    = history[-2]["price"]
        change  = round(((current - prev) / prev) * 100, 1)
        all_data[cid] = {
            "current": current,
            "change":  change,
            "history": history,
            "source":  history[-1]["source"],
        }
    return all_data

def generate_forecast(history: list, months: int = 6) -> list:
    recent_avg = sum(d["price"] for d in history[-30:]) / 30
    slope = (history[-1]["price"] - history[-30]["price"]) / 30
    result = []
    now = datetime.now()
    for i in range(months):
        day      = (i + 1) * 30
        trend    = slope * day * 0.3
        seasonal = math.sin((i / months) * math.pi * 2) * recent_avg * 0.07
        forecast = int(recent_avg + trend + seasonal)
        lower    = int(forecast * 0.88)
        upper    = int(forecast * 1.12)
        month_dt = now.replace(day=1) + timedelta(days=32 * (i + 1))
        result.append({
            "month":    month_dt.strftime("%b %y"),
            "forecast": forecast,
            "lower":    lower,
            "upper":    upper,
        })
    return result

# ─── PLOTLY THEME DEFAULTS ────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="DM Sans"),
    margin=dict(t=20, b=30, l=10, r=10),
    xaxis=dict(showgrid=False, color="#475569"),
    yaxis=dict(showgrid=True,  gridcolor="rgba(255,255,255,0.05)", color="#475569"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
prices = seed_prices()

# ─── HEADER ───────────────────────────────────────────────────────────────────
today_str = datetime.now().strftime("%A, %d %B %Y")
st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
  <span style="font-size:32px">🐷</span>
  <div>
    <div style="font-size:22px;font-weight:900;color:#f1f5f9;letter-spacing:-0.5px;">PigFarm Dashboard</div>
    <div style="font-size:11px;color:#475569;">Uganda · {today_str} &nbsp;
      <span style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);
        border-radius:20px;padding:2px 8px;font-size:10px;color:#4ade80;font-weight:700;">
        🟢 LIVE PRICES
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab_market, tab_feed, tab_medicine = st.tabs(["📈 Market Prices", "🌾 Feed Calculator", "💊 Medicine Tracker"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MARKET PRICES
# ══════════════════════════════════════════════════════════════════════════════
with tab_market:

    # Quick stats
    c1, c2, c3 = st.columns(3)
    c1.metric("🐷 Herd Size",          f"{HERD_SIZE} pigs")
    c2.metric("🌾 Daily Feed",         f"{DAILY_TOTAL_FEED} kg")
    c3.metric("📊 Tracked Commodities", f"{len(COMMODITIES)}")

    st.markdown("### Commodity Prices")
    st.caption("Click a commodity name to see its trend and forecast below.")

    # Build price cards as a 2-column grid
    commodity_names = [f"{c['emoji']} {c['label']}" for c in COMMODITIES]
    selected_label  = st.radio("Select commodity", commodity_names,
                               horizontal=True, label_visibility="collapsed")
    selected_c      = next(c for c in COMMODITIES
                           if f"{c['emoji']} {c['label']}" == selected_label)
    sel_data        = prices[selected_c["id"]]

    # Price card grid
    cols = st.columns(3)
    for idx, c in enumerate(COMMODITIES):
        d        = prices[c["id"]]
        forecast = generate_forecast(d["history"])
        rec      = get_rec(d["change"], forecast, d["current"])
        arrow    = "▲" if d["change"] > 0 else "▼"
        chg_col  = "#f87171" if d["change"] > 0 else "#4ade80"

        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background:{'rgba(251,191,36,0.08)' if c['id']==selected_c['id'] else 'rgba(255,255,255,0.03)'};
                border:{'1.5px solid #f59e0b' if c['id']==selected_c['id'] else '1px solid rgba(255,255,255,0.07)'};
                border-radius:14px;padding:14px 16px;margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <span style="font-size:22px">{c['emoji']}</span>
                <span style="background:{rec['bg']};color:{rec['color']};font-size:9px;
                  font-weight:800;letter-spacing:1px;padding:3px 7px;border-radius:20px;
                  border:1px solid {rec['color']}44">{rec['label']}</span>
              </div>
              <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{c['label']}</div>
              <div style="font-size:20px;font-weight:800;color:#f1f5f9;margin-top:2px;">{fmt_ugx(d['current'])}</div>
              <div style="font-size:11px;color:{chg_col};margin-top:4px;">{arrow} {abs(d['change'])}% today</div>
              <div style="font-size:10px;color:#475569;margin-top:2px;">📡 {d['source']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Trend Chart ──────────────────────────────────────────────────────────
    st.markdown(f"#### {selected_c['emoji']} {selected_c['label']} — Price Trend")
    range_opt = st.radio("Range", ["7D", "30D", "90D"], index=1, horizontal=True)
    n_days    = {"7D": 7, "30D": 30, "90D": 90}[range_opt]
    sliced    = sel_data["history"][-n_days:]
    avg_price = int(sum(d["price"] for d in sliced) / len(sliced))

    df_trend = pd.DataFrame(sliced)
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_trend["date"], y=df_trend["price"],
        mode="lines", name="Price/kg",
        line=dict(color=selected_c["color"], width=2.5),
        fill="tozeroy",
        fillcolor=f"rgba({int(selected_c['color'][1:3],16)},"
                  f"{int(selected_c['color'][3:5],16)},"
                  f"{int(selected_c['color'][5:7],16)},0.08)",
    ))
    fig_trend.add_hline(y=avg_price, line_dash="dot", line_color="#475569",
                        annotation_text=f"Avg {fmt_ugx(avg_price)}",
                        annotation_font_color="#64748b")
    fig_trend.update_layout(**CHART_LAYOUT, height=260,
                            yaxis_tickformat=",",
                            hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── Forecast Chart ────────────────────────────────────────────────────────
    st.markdown(f"#### 🔮 6-Month Price Forecast — {selected_c['label']}")
    forecast = generate_forecast(sel_data["history"], 6)
    df_fc    = pd.DataFrame(forecast)

    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(
        x=df_fc["month"], y=df_fc["upper"],
        mode="lines", line=dict(width=0), showlegend=False, name="Upper",
    ))
    fig_fc.add_trace(go.Scatter(
        x=df_fc["month"], y=df_fc["lower"],
        mode="lines", line=dict(width=0), showlegend=False,
        fill="tonexty",
        fillcolor=f"rgba({int(selected_c['color'][1:3],16)},"
                  f"{int(selected_c['color'][3:5],16)},"
                  f"{int(selected_c['color'][5:7],16)},0.15)",
        name="Confidence Band",
    ))
    fig_fc.add_trace(go.Scatter(
        x=df_fc["month"], y=df_fc["forecast"],
        mode="lines+markers", name="Forecast",
        line=dict(color=selected_c["color"], width=2.5),
        marker=dict(color=selected_c["color"], size=8),
    ))
    fig_fc.update_layout(**CHART_LAYOUT, height=240, yaxis_tickformat=",")
    st.plotly_chart(fig_fc, use_container_width=True)

    # Forecast table
    cur = sel_data["current"]
    rows = []
    for f in forecast:
        chg = round(((f["forecast"] - cur) / cur) * 100, 1)
        rows.append({
            "Month":    f["month"],
            "Forecast": fmt_ugx(f["forecast"]),
            "Low":      fmt_ugx(f["lower"]),
            "High":     fmt_ugx(f["upper"]),
            "vs Today": f"{'▲' if chg > 0 else '▼'} {abs(chg)}%",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FEED CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_feed:
    st.markdown("### ⚙️ Feed Settings")

    col_a, col_b = st.columns(2)
    with col_a:
        num_pigs = st.number_input("Number of Pigs", min_value=1, value=100, step=1)
    with col_b:
        kg_per_pig = st.number_input("kg / Pig / Day", min_value=0.1, value=2.5, step=0.1, format="%.1f")

    st.markdown("""
    <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);
        border-radius:10px;padding:12px 16px;margin:8px 0 16px 0;">
      <div style="font-size:11px;color:#f59e0b;font-weight:700;">FORMULA RATIO (Maize Bran : Cassava Flour : Soya Beans)</div>
      <div style="font-size:22px;font-weight:900;color:#fbbf24;margin-top:4px;">1 : 1 : 0.2</div>
    </div>
    """, unsafe_allow_html=True)

    # Calculations
    bran    = prices["maize_bran"]["current"]
    cassava = prices["cassava_flour"]["current"]
    soya    = prices["soya_beans"]["current"]
    mukene  = prices["mukene"]["current"]

    total_kg   = num_pigs * kg_per_pig
    bran_kg    = (1 / TOTAL_RATIO) * total_kg
    cassava_kg = (1 / TOTAL_RATIO) * total_kg
    soya_kg    = (0.2 / TOTAL_RATIO) * total_kg
    mukene_kg  = total_kg * 0.1

    daily_feed_cost  = bran * bran_kg + cassava * cassava_kg + soya * soya_kg
    daily_supp_cost  = mukene * mukene_kg
    daily_total      = daily_feed_cost + daily_supp_cost
    weekly_total     = daily_total * 7
    monthly_total    = daily_total * 30

    # Ingredient breakdown
    st.markdown("### 🌾 Daily Ingredient Breakdown")
    ic1, ic2, ic3 = st.columns(3)
    ingredients = [
        ("🟤 Maize Bran",    bran_kg,    bran,    "#d97706"),
        ("🍠 Cassava Flour", cassava_kg, cassava, "#84cc16"),
        ("🫘 Soya Beans",    soya_kg,    soya,    "#22c55e"),
    ]
    for col, (label, kg, price_per_kg, color) in zip([ic1, ic2, ic3], ingredients):
        col.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid {color}33;
            border-radius:14px;padding:16px;text-align:center;">
          <div style="font-size:11px;color:#64748b;">{label}</div>
          <div style="font-size:24px;font-weight:900;color:{color};margin-top:6px;">{kg:.1f} kg</div>
          <div style="font-size:10px;color:#475569;">per day</div>
          <div style="font-size:14px;font-weight:700;color:#f1f5f9;margin-top:6px;">
            {fmt_ugx(price_per_kg * kg)}
          </div>
          <div style="font-size:10px;color:#64748b;">daily cost</div>
        </div>
        """, unsafe_allow_html=True)

    # Cost summary
    st.markdown("### 💰 Cost Summary")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("📅 Daily Feed Cost",   fmt_ugx(daily_total))
    sc2.metric("📆 Weekly Feed Cost",  fmt_ugx(weekly_total))
    sc3.metric("🗓️ Monthly Feed Cost", fmt_ugx(monthly_total))

    # Mukene supplement
    st.markdown(f"""
    <div style="background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.15);
        border-radius:14px;padding:14px 18px;margin:12px 0;
        display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-size:13px;font-weight:700;color:#38bdf8;">🐟 Mukene Supplement (10% of mix)</div>
        <div style="font-size:11px;color:#475569;margin-top:3px;">
          {mukene_kg:.1f} kg/day · {fmt_ugx(mukene)}/kg
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:16px;font-weight:800;color:#38bdf8;">{fmt_ugx(daily_supp_cost)}</div>
        <div style="font-size:10px;color:#475569;">daily supplement cost</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Monthly cost bar chart
    st.markdown("#### 📊 Monthly Cost Breakdown")
    bar_data = pd.DataFrame({
        "Ingredient": ["Maize Bran", "Cassava Flour", "Soya Beans", "Mukene Supp."],
        "Monthly Cost": [
            round(bran * bran_kg * 30),
            round(cassava * cassava_kg * 30),
            round(soya * soya_kg * 30),
            round(daily_supp_cost * 30),
        ],
        "Color": ["#d97706", "#84cc16", "#22c55e", "#38bdf8"],
    })
    fig_bar = go.Figure()
    for _, row in bar_data.iterrows():
        fig_bar.add_trace(go.Bar(
            x=[row["Ingredient"]], y=[row["Monthly Cost"]],
            marker_color=row["Color"], name=row["Ingredient"],
            showlegend=False,
        ))
    fig_bar.update_traces(marker_line_width=0)
    fig_bar.update_layout(**CHART_LAYOUT, height=230,
                          yaxis_tickformat=",",
                          bargap=0.3)
    st.plotly_chart(fig_bar, use_container_width=True)

    # Grand total
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(217,119,6,0.05));
        border:1px solid rgba(245,158,11,0.25);border-radius:16px;padding:18px 22px;
        display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
      <div>
        <div style="font-size:12px;color:#f59e0b;font-weight:700;letter-spacing:1px;">
          TOTAL MONTHLY FEED COST
        </div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">incl. Mukene supplement</div>
      </div>
      <div style="font-size:30px;font-weight:900;color:#fbbf24;">{fmt_ugx(monthly_total)}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MEDICINE TRACKER
# ══════════════════════════════════════════════════════════════════════════════
with tab_medicine:

    total_cycle = sum(m["price"] * m["doses"] for m in MEDICINES)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(167,139,250,0.15),rgba(139,92,246,0.05));
        border:1px solid rgba(167,139,250,0.2);border-radius:16px;padding:20px 22px;margin-bottom:16px;">
      <div style="font-size:12px;color:#a78bfa;font-weight:700;letter-spacing:1px;">
        ESTIMATED MONTHLY MEDICINE COST
      </div>
      <div style="font-size:34px;font-weight:900;color:#f1f5f9;margin-top:4px;">{fmt_ugx(total_cycle)}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">for 100 pigs per treatment cycle</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💊 Medicine Checklist")
    st.caption("Check off items as you procure them.")

    checked_total = 0
    for i, med in enumerate(MEDICINES):
        cycle_cost = med["price"] * med["doses"]
        done = st.checkbox(
            f"**{med['name']}** — {med['doses']}× per cycle · "
            f"{fmt_ugx(med['price'])}/{med['per']} · "
            f"**Cycle cost: {fmt_ugx(cycle_cost)}**",
            key=f"med_{i}"
        )
        if done:
            checked_total += cycle_cost

    # Progress bar
    if checked_total > 0:
        pct = checked_total / total_cycle
        st.markdown("#### Procurement Progress")
        st.progress(pct, text=f"{fmt_ugx(checked_total)} procured of {fmt_ugx(total_cycle)} ({pct*100:.0f}%)")

    # Summary totals
    st.markdown("---")
    m1, m2 = st.columns(2)
    m1.metric("💰 Full Cycle Cost",       fmt_ugx(total_cycle))
    m2.metric("✅ Procured So Far",        fmt_ugx(checked_total))

    remaining = total_cycle - checked_total
    st.metric("🔲 Remaining to Procure",   fmt_ugx(remaining))

    # Cost per medicine bar chart
    st.markdown("#### 📊 Cost Per Medicine (per cycle)")
    med_df = pd.DataFrame({
        "Medicine":   [m["name"].split(" ")[0] for m in MEDICINES],
        "Cycle Cost": [m["price"] * m["doses"] for m in MEDICINES],
    })
    fig_med = go.Figure(go.Bar(
        x=med_df["Medicine"],
        y=med_df["Cycle Cost"],
        marker=dict(
            color=med_df["Cycle Cost"],
            colorscale=[[0, "#7c3aed"], [1, "#a78bfa"]],
            showscale=False,
        ),
        text=[fmt_ugx(v) for v in med_df["Cycle Cost"]],
        textposition="outside",
        textfont=dict(color="#c4b5fd", size=10),
    ))
    fig_med.update_layout(**CHART_LAYOUT, height=260, yaxis_tickformat=",", showlegend=False)
    st.plotly_chart(fig_med, use_container_width=True)

    # Full medicine table
    st.markdown("#### 📋 Full Medicine Reference Table")
    table_rows = [{
        "Medicine":        m["name"],
        "Price":           fmt_ugx(m["price"]),
        "Per":             m["per"],
        "Doses / Cycle":   m["doses"],
        "Cycle Cost":      fmt_ugx(m["price"] * m["doses"]),
    } for m in MEDICINES]
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
