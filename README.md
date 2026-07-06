# AI Cost Checkup — Stage 1 Testing Tool

A small tool that reads an AI API usage export (CSV) and flags where a
company might be overpaying — using an expensive model for a simple task,
or sending way more input context than needed.

## Files in this folder
- `ai_cost_analyzer.py` — the core logic (rules + math). Also runs as a
  command-line tool.
- `app.py` — a simple web page (Streamlit) around the same logic, so a
  customer can upload their CSV and see a report without touching code.
- `sample_usage.csv` — fake but realistic usage data, for testing.
- `requirements.txt` — the 3 packages needed (streamlit, pandas, plotly).

## How to use this for testing (Stage 1, this week)

1. **Find 5 companies/people who use AI APIs** (OpenAI, Anthropic, Google, etc.)
   for a product or internal tool.
2. **Ask them to export their usage data.** Most providers have a usage
   dashboard with a CSV/export option, or you can ask them to pull it from
   their own logging (task name, model, tokens, cost).
3. **Run the report for them** — either:
   - Command line: `python ai_cost_analyzer.py their_file.csv`
   - Or, better: send them the web link (see deployment below) and let them
     upload the file themselves — feels more like a real product, and you
     don't have to touch their data at all.
4. **Read the flagged opportunities out loud to them** and ask: "Does this
   match what you expected? Would this be useful to check every month?"
   Their reaction is your real signal — more important than the numbers.

## Where to deploy it (so people can use it without you)

For this early testing stage, don't build a full production app yet — use
one of these, both free and take under 15 minutes:

### Option A — Streamlit Community Cloud (recommended for Stage 1)
1. Put these files in a GitHub repo (just `app.py`, `ai_cost_analyzer.py`,
   `requirements.txt`, `sample_usage.csv`).
2. Go to https://streamlit.io/cloud, sign in with GitHub, click "New app,"
   point it at your repo and `app.py`.
3. You get a public link like `yourname-ai-cost-checkup.streamlit.app` in a
   few minutes. Send that link straight to a customer.

### Option B — Hugging Face Spaces (if you already have an account there)
Same idea — create a new Space, choose "Streamlit" as the SDK, upload these
files. Also free, also gives you a public link.

Either option is enough for Stage 1. No GPU needed, no server to manage,
free tier is fine for a handful of test users. Only think about your own
server/hosting once you have paying customers and need private data
handling guarantees.

## Important honesty notes
- The pricing numbers in `ai_cost_analyzer.py` (`PRICING` table) are
  approximate and WILL go out of date. Before you show a savings number to
  a real paying customer, check the provider's current pricing page and
  update the table.
- The "simple task" and "high context ratio" rules are a starting guess,
  not a guarantee. Always tell the customer: "This is a signal to
  investigate, not a certain fact — please compare quality before switching
  models."
- Don't ask customers for raw API keys at this stage — a CSV export they
  choose to share is safer for them and easier for you to handle.
