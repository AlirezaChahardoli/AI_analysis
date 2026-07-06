"""
ai_cost_analyzer.py
--------------------
Stage 1 tool: read an AI API usage export (CSV) and find real cost-saving
opportunities - which tasks are using an expensive model when a cheaper one
would likely work, and which tasks send way more input than they need to.

USAGE (command line):
    python ai_cost_analyzer.py your_usage.csv

EXPECTED CSV COLUMNS (flexible - see COLUMN_ALIASES below):
    task            - name of the feature/use case, e.g. "customer_support_reply"
    model           - model name, e.g. "gpt-4o", "claude-opus-4-1"
    input_tokens    - input/prompt tokens for that row
    output_tokens   - output/completion tokens for that row
    calls           - optional, number of calls this row represents (default 1)
    cost            - optional, real cost in USD. If missing, cost is
                      estimated from the PRICING table below.

If a customer's export uses different column names, either rename the
columns before uploading, or add the name to COLUMN_ALIASES.
"""

import sys
import pandas as pd

# ---------------------------------------------------------------------------
# PRICING TABLE (USD per 1,000 tokens).
# IMPORTANT: prices change often. These numbers are for demo/testing only -
# always check the provider's current pricing page before showing a real
# savings number to a paying customer.
# ---------------------------------------------------------------------------
PRICING = {
    "gpt-4o":            (0.0025, 0.0100),
    "gpt-4o-mini":       (0.00015, 0.0006),
    "gpt-4-turbo":       (0.0100, 0.0300),
    "gpt-3.5-turbo":     (0.0005, 0.0015),
    "claude-opus-4-1":   (0.0150, 0.0750),
    "claude-sonnet-4-5": (0.0030, 0.0150),
    "claude-haiku-4-5":  (0.0008, 0.0040),
    "gemini-1.5-pro":    (0.00125, 0.0050),
    "gemini-1.5-flash":  (0.000075, 0.0003),
}

# Which cheaper model to suggest instead of an expensive one, when a task
# looks simple. Edit freely as new models come out.
CHEAPER_ALTERNATIVE = {
    "gpt-4o":            "gpt-4o-mini",
    "gpt-4-turbo":       "gpt-4o-mini",
    "claude-opus-4-1":   "claude-haiku-4-5",
    "claude-sonnet-4-5": "claude-haiku-4-5",
    "gemini-1.5-pro":    "gemini-1.5-flash",
}

COLUMN_ALIASES = {
    "task":          ["task", "feature", "endpoint", "use_case"],
    "model":         ["model", "model_name"],
    "input_tokens":  ["input_tokens", "prompt_tokens", "in_tokens"],
    "output_tokens": ["output_tokens", "completion_tokens", "out_tokens"],
    "calls":         ["calls", "requests", "count"],
    "cost":          ["cost", "cost_usd", "total_cost"],
}


def _find_column(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None


def load_usage_data(path_or_buffer):
    """Loads a CSV (file path or uploaded file object) into a clean, standard
    dataframe with columns: task, model, input_tokens, output_tokens, calls, cost."""
    df = pd.read_csv(path_or_buffer)
    df.columns = [c.strip().lower() for c in df.columns]

    resolved = {}
    for key, aliases in COLUMN_ALIASES.items():
        col = _find_column(df, aliases)
        if col:
            resolved[key] = col

    if "task" not in resolved or "model" not in resolved:
        raise ValueError(
            "CSV must have a 'task' (or feature/use_case) column and a 'model' column."
        )

    out = pd.DataFrame()
    out["task"] = df[resolved["task"]]
    out["model"] = df[resolved["model"]].astype(str).str.strip().str.lower()
    out["input_tokens"] = df[resolved["input_tokens"]] if "input_tokens" in resolved else 0
    out["output_tokens"] = df[resolved["output_tokens"]] if "output_tokens" in resolved else 0
    out["calls"] = df[resolved["calls"]] if "calls" in resolved else 1

    if "cost" in resolved:
        out["cost"] = df[resolved["cost"]]
    else:
        out["cost"] = out.apply(_estimate_cost_row, axis=1)

    return out


def _estimate_cost_row(row):
    price = PRICING.get(row["model"])
    if not price:
        return 0.0
    in_price, out_price = price
    return (row["input_tokens"] / 1000 * in_price + row["output_tokens"] / 1000 * out_price) * row["calls"]


def analyze(df):
    """Returns (by_model, by_task, flags_df, total_spend, total_potential_savings)."""
    total_spend = df["cost"].sum()

    by_model = (
        df.groupby("model")
        .agg(spend=("cost", "sum"), calls=("calls", "sum"))
        .sort_values("spend", ascending=False)
        .reset_index()
    )

    by_task = (
        df.groupby("task")
        .agg(
            spend=("cost", "sum"),
            calls=("calls", "sum"),
            avg_output_tokens=("output_tokens", "mean"),
            avg_input_tokens=("input_tokens", "mean"),
            model_used=("model", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
        )
        .reset_index()
    )

    flags = []
    SIMPLE_OUTPUT_TOKEN_THRESHOLD = 200   # short answers => task is likely "simple"
    HIGH_CONTEXT_RATIO = 20               # input much bigger than output => bloated prompt?

    for _, row in by_task.iterrows():
        model = row["model_used"]
        cheaper = CHEAPER_ALTERNATIVE.get(model)

        # Flag 1: expensive model used on a task whose replies are short/simple.
        if cheaper and 0 < row["avg_output_tokens"] < SIMPLE_OUTPUT_TOKEN_THRESHOLD:
            task_rows = df[(df["task"] == row["task"]) & (df["model"] == model)]
            current_cost = task_rows["cost"].sum()
            in_p, out_p = PRICING.get(cheaper, (0, 0))
            new_cost = (
                task_rows["input_tokens"].sum() / 1000 * in_p
                + task_rows["output_tokens"].sum() / 1000 * out_p
            )
            savings = max(current_cost - new_cost, 0)
            if savings > 0:
                flags.append({
                    "task": row["task"],
                    "issue": f"Uses '{model}' for short/simple-looking replies (avg {row['avg_output_tokens']:.0f} output tokens).",
                    "suggestion": f"Try '{cheaper}' for this task and compare output quality.",
                    "current_spend": round(current_cost, 2),
                    "estimated_new_spend": round(new_cost, 2),
                    "estimated_savings": round(savings, 2),
                })

        # Flag 2: input tokens much bigger than output tokens - possibly unneeded context.
        if row["avg_output_tokens"] > 0 and (row["avg_input_tokens"] / max(row["avg_output_tokens"], 1)) > HIGH_CONTEXT_RATIO:
            flags.append({
                "task": row["task"],
                "issue": f"Input is about {row['avg_input_tokens']/max(row['avg_output_tokens'],1):.0f}x bigger than output on average.",
                "suggestion": "Review the prompt/context sent for this task - trim unused history, documents, or instructions.",
                "current_spend": round(row["spend"], 2),
                "estimated_new_spend": None,
                "estimated_savings": None,
            })

    flags_df = pd.DataFrame(flags)
    total_potential_savings = flags_df["estimated_savings"].fillna(0).sum() if not flags_df.empty else 0.0

    return by_model, by_task, flags_df, total_spend, total_potential_savings


def print_report(by_model, by_task, flags_df, total_spend, total_savings):
    print("=" * 60)
    print("AI COST ANALYSIS REPORT")
    print("=" * 60)
    print(f"\nTotal spend in this file: ${total_spend:,.2f}")
    print(f"Estimated potential savings found: ${total_savings:,.2f}\n")

    print("-- Spend by model --")
    print(by_model.to_string(index=False))

    print("\n-- Spend by task --")
    print(by_task[["task", "spend", "calls", "model_used"]].to_string(index=False))

    print("\n-- Flagged opportunities --")
    if flags_df.empty:
        print("No obvious issues found with the current rules.")
    else:
        for _, f in flags_df.iterrows():
            print(f"\n[{f['task']}]")
            print(f"  Issue:      {f['issue']}")
            print(f"  Suggestion: {f['suggestion']}")
            if pd.notna(f["estimated_savings"]) and f["estimated_savings"]:
                print(f"  Current spend: ${f['current_spend']:.2f}  ->  Estimated new spend: ${f['estimated_new_spend']:.2f}  (save ${f['estimated_savings']:.2f})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_cost_analyzer.py your_usage.csv")
        sys.exit(1)
    data = load_usage_data(sys.argv[1])
    _by_model, _by_task, _flags_df, _total_spend, _total_savings = analyze(data)
    print_report(_by_model, _by_task, _flags_df, _total_spend, _total_savings)
