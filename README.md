STEPS TO RUN THE PROJECT and sample output are given below
Both the backend and frontend output images are attached

Follow these steps to run the project
CSV / Data Q&A Agent
An AI agent that answers natural-language questions about CSV/Excel datasets
using real Pandas computation — not guessed numbers. The agent plans the
analysis (via Gemini), a deterministic Pandas engine executes it, and the
answer is explained back in plain language, with a chart and supporting data
table as evidence.
`example_results.md` / `example_results.json` — 10 real questions run
end-to-end against the included sample dataset, with the exact analysis
plan and computed results for each. See that file to verify the engine
actually works before you set up anything.
---
1. Prerequisites
Python 3.10+ (project developed/tested on Python 3.14)
A Google Gemini API key (free tier available) — Get one here
Windows, macOS, or Linux
---
2. Installation
```bash
# 1. Clone or download this repository, then move into it
cd csv-data-qa-agent

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```
`requirements.txt` should include at minimum:
```
fastapi
uvicorn[standard]
pandas
openpyxl
matplotlib
python-dotenv
google-genai
pydantic
streamlit
requests
```
---
3. Configure API keys
Copy the example env file:
```bash
   cp .env.example .env
   ```
(On Windows: `copy .env.example .env`)
Open `.env` and fill in your key:
```
   GEMINI_API_KEY=your_actual_key_here
   ```
That's it — `src/config.py` loads this automatically via `python-dotenv`
at startup. No other configuration is required.
Verify your key is loading correctly:
```bash
python -c "from src.config import settings; print('Gemini key loaded:', bool(settings.GEMINI_API_KEY))"
```
This should print `True`. If it prints `False`, double-check the variable
name in `.env` matches exactly (`GEMINI_API_KEY`), with no quotes and no
extra spaces around the `=`.
---
4. Running the project end to end
This project has two processes that run at the same time: the FastAPI
backend (the actual agent) and the Streamlit frontend (the UI).
Terminal 1 — start the backend:
```bash
python server.py
```
This starts the API at `http://127.0.0.1:8000`. Confirm it's healthy by
visiting `http://127.0.0.1:8000/health` in a browser — it should return
`{"status": "healthy"}`. Interactive API docs are available at
`http://127.0.0.1:8000/docs`.
Terminal 2 — start the frontend:
```bash
streamlit run streamlit_app.py
```
This opens `http://localhost:8501` in your browser automatically.
Using the app:
In the sidebar, upload a CSV or Excel file (a sample file,
`E-Commerce_Sales_Analytics.csv`, is included in this repo for testing).
Once uploaded, type a question in plain English, e.g.:
"What is the total revenue by region?"
"Which product category has the highest average customer rating?"
"How many orders were paid using Cash on Delivery?"
Click Ask. You'll see the AI's analysis plan, the real computed
result table, a chart (when applicable), and a plain-language answer.
Without the UI (API only): use `http://127.0.0.1:8000/docs` to call
`POST /api/upload` (attach a file, copy the returned `session_id`) and then
`POST /api/ask` with `{"question": "...", "session_id": "<the copied id>"}`.
---
5. Reproducing the example results
To regenerate `example_results.md`/`.json` yourself (this runs the real
Pandas engine against the real sample dataset, bypassing the LLM call to
keep it fast, deterministic, and free to re-run):
```bash
python run_examples.py
```
This is useful to verify the computation engine works correctly on your
machine independent of any AI/API key issues.
---
6. Design choices
Separation of "planning" from "computation."
The AI (Gemini) never calculates anything itself — it only translates a
natural-language question into a structured JSON plan (which columns,
which aggregation, which filters, sort order, limit). A deterministic
Pandas engine (`DataAnalyzer`) then executes that plan. This means:
Numbers in the answer are always exactly what Pandas computed — the LLM
cannot hallucinate a number, only misidentify which columns/operation to
use (which surfaces as a clear validation error, not a wrong silent
answer).
The plan itself is shown to the user (`"plan"` in the API response) so
they can verify how their question was interpreted, not just trust the
final answer blindly.
Session-based file isolation.
Each upload gets a random `session_id` (UUID), and all questions for that
session only ever look at that session's file. This avoids one user's
uploaded file accidentally answering a different user's question, and
avoids silent overwrites when two people upload files with the same name.
Explicit, whitelisted operations only.
`DataAnalyzer` supports a fixed set of operations (`sum`, `mean`, `median`,
`min`, `max`, `count`, `nunique`) and a fixed set of filter operators (`==`,
`!=`, `>`, `<`, `>=`, `<=`, `in`, `contains`). The AI cannot execute
arbitrary code against the dataset — it can only select from this safe,
auditable set of operations. This is a deliberate security/reliability
tradeoff over giving the LLM free rein to write and execute pandas code.
Growth/period comparison as a distinct operation type.
Simple aggregation (`"operation": "aggregate"`) and period-over-period
comparison (`"operation": "compare_periods"`) are handled as two separate
code paths, since "how much did X grow" requires two aggregations plus a
percentage-change calculation — a fundamentally different shape of
computation than a single grouped aggregation.
Gemini as the sole model.
An earlier version of this project supported both Gemini and Mistral as a
fallback pair. This was simplified to Gemini-only for reliability and to
reduce configuration surface area (one API key, one code path to test and
debug).
---
7. Tradeoffs and limitations
No true date-range/period bucketing. `compare_periods` matches a
period column by exact value (e.g. `quarter == "Q3 2025"`). If your
dataset only has raw daily dates (like the included sample file) with no
pre-existing "quarter" or "month" column, growth-comparison questions
("which region grew fastest last quarter") will not work out of the box
— the dataset would need a period column added first, or the analyzer
extended to bucket dates into ranges.
Single aggregation/metric per question. A question needing two
different metrics at once (e.g. "compare total revenue AND average
rating by region in one table") isn't supported — `DataAnalyzer` uses
the first non-group-by column found in `required_columns` and ignores
the rest.
No persistent storage. Uploaded files stay on local disk under
`uploads/` indefinitely; there's no automatic cleanup, database, or
multi-day session expiry. Restarting the server does not delete old
uploads, but also does not preserve `session_id`s in memory (sessions
are just derived from filenames on disk, so old session IDs remain valid
as long as the file exists).
Charts are best-effort. `create_chart()` only generates a chart when
the result has 2+ columns and the value column is numeric. Single-value
answers (e.g. "how many orders total") return no chart — this is
intentional, not a bug, since a chart isn't meaningful for one number.
No authentication. Any client that can reach the API can upload
files and ask questions against any known `session_id`. This is fine for
local/demo use but is not production-hardened (no rate limiting, no user
accounts, CORS wide open with `allow_origins=["*"]`).
LLM plan quality depends on the question's clarity and the dataset's
schema. Vague questions, or questions unrelated to the uploaded
dataset's actual columns (e.g. asking about "IPC sections" against
e-commerce sales data), will correctly fail with a `400` validation
error rather than a hallucinated answer — this is by design, but means
the agent cannot answer questions the data doesn't support.
Concurrency. The Pandas engine itself is stateless per-request and
safe under concurrent load. Chart generation uses matplotlib's
object-oriented `Figure` API (not the global `pyplot` state) specifically
to remain safe under concurrent requests.
---
8. Project structure
```
csv-data-qa-agent/
├── src/
│   ├── agent.py            # Gemini client wrapper; builds & parses the analysis plan
│   ├── config.py           # Loads GEMINI_API_KEY from .env
│   ├── data_analyzer.py    # Deterministic Pandas execution engine
│   ├── data_loader.py      # CSV/Excel loading, schema summary, preview
│   ├── prompts.py          # Prompt template defining the strict JSON output schema
│   └── visualization.py    # Chart generation (matplotlib, saved to generated_charts/)
├── app.py                  # FastAPI router: /api/upload, /api/ask
├── main.py                 # FastAPI app instance, CORS, static chart serving
├── server.py                # uvicorn entry point (run this to start the API)
├── streamlit_app.py        # Streamlit frontend
├── run_examples.py          # Reproducible script for the 10 example runs
├── example_results.md/json  # Saved output of the 10 example runs
├── requirements.txt
├── .env.example
└── README.md                 # This file
```

<img width="1788" height="790" alt="image" src="https://github.com/user-attachments/assets/e0936523-704f-4381-aaa4-f6248c8ccf2d" />
<img width="1748" height="788" alt="image" src="https://github.com/user-attachments/assets/c4722a1e-1c7d-4626-a206-0e698cfddaae" />
<img width="1777" height="785" alt="image" src="https://github.com/user-attachments/assets/3bd03810-90f2-418f-b0ab-900d55d7ae84" />
<img width="1796" height="812" alt="image" src="https://github.com/user-attachments/assets/816ffea7-5e85-4baa-952c-d3f62e21484d" />
<img width="1811" height="857" alt="image" src="https://github.com/user-attachments/assets/30e2ec92-3e50-41c0-a3e2-cbb07657e504" />
<img width="1785" height="891" alt="image" src="https://github.com/user-attachments/assets/bdb424ff-956b-4877-bde7-1054c23440c2" />
<img width="1865" height="856" alt="image" src="https://github.com/user-attachments/assets/857750f4-d0d9-4472-980e-b73fe3e70d6b" />
<img width="1865" height="856" alt="image" src="https://github.com/user-attachments/assets/429e37b3-71b2-49bf-bc1a-afeaed996939" />
<img width="1812" height="840" alt="image" src="https://github.com/user-attachments/assets/9607c369-c69f-4dfc-8875-9a7bcdf5c3a0" />
<img width="1837" height="801" alt="image" src="https://github.com/user-attachments/assets/dcbf1b1f-578f-4f67-9bff-0f5ea74420d0" />
<img width="1836" height="851" alt="image" src="https://github.com/user-attachments/assets/1799316f-52c9-43f7-a8fa-c6722b932f58" />
<img width="1836" height="851" alt="image" src="https://github.com/user-attachments/assets/6892cae6-5dfc-4210-bbfe-8d1f2483ceb4" />
<img width="1820" height="832" alt="image" src="https://github.com/user-attachments/assets/4c05039b-ccbe-498b-8c7b-8a6ec435e4d8" />
<img width="1807" height="842" alt="image" src="https://github.com/user-attachments/assets/44bb58de-2093-4e66-80c3-8b61ed49acf0" />
<img width="1820" height="832" alt="image" src="https://github.com/user-attachments/assets/cda7ffa8-8da8-483b-ba8c-2cce5edbcaf0" />

