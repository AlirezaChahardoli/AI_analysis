import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_cost_analyzer import (
    PRICING,
    CHEAPER_ALTERNATIVE,
    load_usage_data,
    analyze,
    compute_monthly_projection,
    generate_share_summary,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Cost Checkup — D8talytics", page_icon="🧾", layout="wide")

INK = "#1B2430"
INK_SOFT = "#5B6472"
LINE = "#D8DEE6"
PAPER = "#F7F9FB"
GREEN = "#1F7A5C"
GREEN_SOFT = "rgba(31,122,92,0.08)"
RED = "#C1443C"
RED_SOFT = "rgba(193,68,60,0.08)"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"], .stMarkdown, p, span, div {{
    font-family: 'Inter', -apple-system, sans-serif;
}}

.stApp {{
    background-color: {PAPER};
}}

/* ---- Receipt header ---- */
.receipt-header {{
    text-align: center;
    padding: 1.6rem 0 1.4rem;
    border-bottom: 2px dashed {LINE};
    margin-bottom: 1.6rem;
}}
.receipt-header .eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 4px;
    text-transform: uppercase;
    font-size: 0.72rem;
    color: {INK_SOFT};
}}
.receipt-header h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    letter-spacing: -0.5px;
    font-size: 2.3rem;
    color: {INK};
    margin: 0.3rem 0 0.2rem;
}}
.receipt-header .sub {{
    color: {INK_SOFT};
    font-size: 0.98rem;
}}

/* ---- Stat cards ---- */
.stat-row {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.4rem 0 1.6rem; }}
.stat-card {{
    flex: 1; min-width: 210px;
    background: #FFFFFF;
    border: 1px solid {LINE};
    border-radius: 6px;
    padding: 1.1rem 1.3rem;
}}
.stat-card .label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {INK_SOFT};
}}
.stat-card .value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.85rem;
    font-weight: 700;
    color: {INK};
    margin-top: 0.25rem;
}}
.stat-card.savings {{ background: {GREEN_SOFT}; border-color: {GREEN}; }}
.stat-card.savings .value {{ color: {GREEN}; }}

/* ---- Stamp badge (the signature element) ---- */
.stamp {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    font-size: 0.78rem;
    border: 3px solid {GREEN};
    color: {GREEN};
    padding: 5px 16px;
    border-radius: 8px;
    transform: rotate(-3deg);
    background: {GREEN_SOFT};
    margin-top: 0.4rem;
}}
.stamp.none {{ border-color: {INK_SOFT}; color: {INK_SOFT}; background: transparent; }}

/* ---- Flag cards ---- */
.flag-card {{
    background: #FFFFFF;
    border-left: 4px solid {RED};
    border-radius: 3px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.7rem;
    box-shadow: 0 1px 2px rgba(20,30,45,0.05);
}}
.flag-card.bloat {{ border-left-color: #B8860B; }}
.flag-card .top-row {{ display:flex; justify-content: space-between; align-items:baseline; flex-wrap: wrap; gap: 0.4rem; }}
.flag-card .task-name {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.02rem; color: {INK}; }}
.flag-card .tag {{
    font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 1px;
    text-transform: uppercase; color: {INK_SOFT}; border: 1px solid {LINE}; border-radius: 4px; padding: 2px 8px;
}}
.flag-card .issue {{ color: {INK_SOFT}; font-size: 0.92rem; margin: 0.35rem 0; }}
.flag-card .suggestion {{
    color: {INK}; font-size: 0.9rem; background: {PAPER}; border: 1px solid {LINE};
    padding: 0.35rem 0.6rem; border-radius: 4px; display: inline-block;
}}
.flag-card .money-row {{ font-family: 'JetBrains Mono', monospace; margin-top: 0.55rem; font-size: 0.92rem; color: {INK}; }}
.flag-card .money-row .save {{ color: {GREEN}; font-weight: 700; }}

/* Ledger-style divider */
.ledger-divider {{
    border: none; border-top: 1px dashed {LINE}; margin: 1.6rem 0;
}}

section[data-testid="stSidebar"] {{
    background-color: #FFFFFF;
    border-right: 1px solid {LINE};
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    layout=go.Layout(
        font=dict(family="Inter, sans-serif", color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[GREEN, "#3D5A80", "#B8860B", RED, "#5B6472", "#8FA6B2"],
    )
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="receipt-header">
        <div class="eyebrow">*** D8talytics ***</div>
        <h1>🧾 AI Cost Checkup</h1>
        <div class="sub">Upload your AI API usage export — get an itemized receipt of where the money is going, and what you could save.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — options
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Detection settings")
    simple_threshold = st.slider(
        "Reply length considered \"simple\" (tokens)", 20, 500, 200, step=10,
        help="Tasks whose average output is shorter than this are flagged as candidates for a cheaper model.",
    )
    context_ratio = st.slider(
        "Flag context bloat when input is this many times bigger than output", 5, 100, 20, step=5,
    )

    st.markdown("### 💲 Pricing table")
    st.caption("Prices change often — edit these to match today's real pricing before sharing a report.")
    pricing_df = pd.DataFrame(
        [{"model": m, "input_$_per_1k": v[0], "output_$_per_1k": v[1]} for m, v in PRICING.items()]
    )
    edited_pricing_df = st.data_editor(
        pricing_df, num_rows="dynamic", use_container_width=True, hide_index=True, key="pricing_editor"
    )
    pricing_override = {
        row["model"].strip().lower(): (float(row["input_$_per_1k"]), float(row["output_$_per_1k"]))
        for _, row in edited_pricing_df.iterrows()
        if isinstance(row["model"], str) and row["model"].strip()
    }

    st.markdown("### 📁 No file yet?")
    sample_path = Path(__file__).parent / "sample_usage.csv"
    if sample_path.exists():
        st.download_button("Download sample CSV", sample_path.read_bytes(), "sample_usage.csv", "text/csv")

uploaded = st.file_uploader("Upload usage CSV", type="csv", label_visibility="collapsed")

with st.expander("What columns should my CSV have?"):
    st.markdown(
        """
        - **task** (or feature / use_case) — name of the feature that made the call
        - **model** — model name, e.g. `gpt-4o`, `claude-opus-4-1`
        - **input_tokens**, **output_tokens** — tokens used per call
        - **calls** — optional, number of calls this row represents (default 1)
        - **cost** — optional; if missing, cost is estimated from the pricing table
        - **date** — optional; if present, unlocks a monthly spend projection
        """
    )

if not uploaded:
    st.info("👆 Upload a CSV to get your receipt, or grab the sample file from the sidebar.")
    st.stop()

try:
    raw_df = load_usage_data(uploaded)
except Exception as e:
    st.error(f"Could not read this file: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Filters (only shown once data is loaded)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔎 Filters")
    all_tasks = sorted(raw_df["task"].unique().tolist())
    all_models = sorted(raw_df["model"].unique().tolist())
    picked_tasks = st.multiselect("Tasks", all_tasks, default=all_tasks)
    picked_models = st.multiselect("Models", all_models, default=all_models)

    date_range = None
    if "date" in raw_df.columns and raw_df["date"].notna().any():
        min_d, max_d = raw_df["date"].min().date(), raw_df["date"].max().date()
        if min_d != max_d:
            date_range = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)

filtered_df = raw_df[raw_df["task"].isin(picked_tasks) & raw_df["model"].isin(picked_models)]
if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered_df = filtered_df[(filtered_df["date"].isna()) | ((filtered_df["date"] >= start) & (filtered_df["date"] <= end))]

if filtered_df.empty:
    st.warning("No rows match the current filters — widen your selection in the sidebar.")
    st.stop()

by_model, by_task, flags_df, total_spend, total_savings, priced_df = analyze(
    filtered_df,
    pricing=pricing_override or None,
    simple_output_threshold=simple_threshold,
    high_context_ratio=context_ratio,
)
monthly = compute_monthly_projection(priced_df)

# ---------------------------------------------------------------------------
# Stat row + stamp
# ---------------------------------------------------------------------------
pct = (total_savings / total_spend * 100) if total_spend else 0
stat_cards = f"""
<div class="stat-row">
    <div class="stat-card">
        <div class="label">Total Spend</div>
        <div class="value">${total_spend:,.2f}</div>
    </div>
    <div class="stat-card savings">
        <div class="label">Potential Savings</div>
        <div class="value">${total_savings:,.2f}</div>
        <div class="stamp{' none' if total_savings == 0 else ''}">
            {'✓ savings found — ' + f'{pct:.0f}%' if total_savings > 0 else 'no savings flagged'}
        </div>
    </div>
"""
if monthly:
    proj, days = monthly
    stat_cards += f"""
    <div class="stat-card">
        <div class="label">Projected Monthly Spend</div>
        <div class="value">${proj:,.2f}</div>
        <div style="font-size:0.75rem;color:{INK_SOFT};margin-top:0.3rem;">based on {days} day(s) of data</div>
    </div>
    """
stat_cards += "</div>"
st.markdown(stat_cards, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_opportunities, tab_details, tab_share = st.tabs(
    ["📊 Overview", "🚩 Opportunities", "📋 Details", "✉️ Share report"]
)

with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Spend by model**")
        fig = px.bar(by_model, x="model", y="spend", **PLOTLY_TEMPLATE)
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Spend by task**")
        fig2 = px.pie(by_task, names="task", values="spend", hole=0.5, **PLOTLY_TEMPLATE)
        fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=340)
        st.plotly_chart(fig2, use_container_width=True)

    if "date" in priced_df.columns and priced_df["date"].notna().any():
        st.markdown("**Spend over time**")
        daily = priced_df.dropna(subset=["date"]).groupby(priced_df["date"].dt.date)["cost"].sum().reset_index()
        fig3 = px.line(daily, x="date", y="cost", markers=True, **PLOTLY_TEMPLATE)
        fig3.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
        st.plotly_chart(fig3, use_container_width=True)

with tab_opportunities:
    if flags_df.empty:
        st.info("No obvious issues found with the current detection settings — try loosening the sliders in the sidebar.")
    else:
        for _, f in flags_df.iterrows():
            card_class = "flag-card bloat" if f["type"] == "Context bloat" else "flag-card"
            money_html = ""
            if pd.notna(f["estimated_savings"]) and f["estimated_savings"]:
                money_html = (
                    f'<div class="money-row">${f["current_spend"]:,.2f} → ${f["estimated_new_spend"]:,.2f} '
                    f'&nbsp;<span class="save">save ${f["estimated_savings"]:,.2f}</span></div>'
                )
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="top-row">
                        <span class="task-name">{f['task']}</span>
                        <span class="tag">{f['type']}</span>
                    </div>
                    <div class="issue">{f['issue']}</div>
                    <div class="suggestion">💡 {f['suggestion']}</div>
                    {money_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.download_button(
            "⬇️ Download opportunities as CSV",
            flags_df.to_csv(index=False).encode(),
            "ai_cost_opportunities.csv",
            "text/csv",
        )

with tab_details:
    st.markdown("**Spend by model**")
    st.dataframe(by_model, use_container_width=True)
    st.markdown("**Spend by task**")
    st.dataframe(by_task, use_container_width=True)
    st.markdown("**Raw priced rows**")
    st.dataframe(priced_df, use_container_width=True)
    st.download_button(
        "⬇️ Download full priced data as CSV",
        priced_df.to_csv(index=False).encode(),
        "ai_cost_priced_data.csv",
        "text/csv",
    )

with tab_share:
    st.markdown("A short, plain-English summary — copy this straight into an email or Slack message.")
    summary = generate_share_summary(by_task, flags_df, total_spend, total_savings, monthly)
    st.text_area("Summary", summary, height=140, label_visibility="collapsed")
    st.caption("Tip: pair this with the CSV from the Opportunities tab when you send it along.")load a CSV to get started.")
