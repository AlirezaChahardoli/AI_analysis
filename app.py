import streamlit as st
import plotly.express as px
from ai_cost_analyzer import load_usage_data, analyze

st.set_page_config(page_title="AI Cost Checkup", layout="wide")

st.title("💸 AI Cost Checkup")
st.write(
    "Upload your AI API usage export (CSV) and get a free, instant report "
    "showing where you might be overpaying."
)

with st.expander("What columns should my CSV have?"):
    st.markdown(
        """
        - **task** (or feature / use_case) — name of the feature that made the call
        - **model** — model name, e.g. `gpt-4o`, `claude-opus-4-1`
        - **input_tokens**, **output_tokens** — tokens used per call
        - **calls** — optional, number of calls this row represents (default 1)
        - **cost** — optional; if missing, cost is estimated from a built-in pricing table

        Don't have a CSV handy? Try `sample_usage.csv` (included in this project) first.
        """
    )

uploaded = st.file_uploader("Upload usage CSV", type="csv")

if uploaded:
    try:
        df = load_usage_data(uploaded)
    except Exception as e:
        st.error(f"Could not read this file: {e}")
        st.stop()

    by_model, by_task, flags_df, total_spend, total_savings = analyze(df)

    col1, col2 = st.columns(2)
    col1.metric("Total spend in this file", f"${total_spend:,.2f}")
    col2.metric("Potential savings found", f"${total_savings:,.2f}")

    st.subheader("Spend by model")
    st.plotly_chart(px.bar(by_model, x="model", y="spend"), use_container_width=True)

    st.subheader("Spend by task")
    st.dataframe(by_task, use_container_width=True)

    st.subheader("🚩 Flagged opportunities")
    if flags_df.empty:
        st.info("No obvious issues found with the current rules.")
    else:
        st.dataframe(flags_df, use_container_width=True)
        st.download_button(
            "Download this report as CSV",
            flags_df.to_csv(index=False).encode(),
            "ai_cost_report.csv",
            "text/csv",
        )
else:
    st.info("👆 Upload a CSV to get started.")
