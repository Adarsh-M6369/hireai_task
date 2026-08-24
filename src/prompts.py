import json


def build_analysis_prompt(
    question: str,
    schema: dict,
    preview: list,
) -> str:
    """
    Build the prompt that instructs the AI to translate a natural
    language question into a strict JSON analysis plan that
    DataAnalyzer.execute() can run directly against the dataframe.
    """

    schema_text = json.dumps(schema, indent=2, default=str)
    preview_text = json.dumps(preview, indent=2, default=str)

    return f"""
You are a data analysis planning assistant. You do NOT calculate
answers yourself. You only decide WHAT computation should be run
on the dataset. A separate Python/Pandas engine will execute your
plan and return the real, exact numbers.

DATASET SCHEMA:
{schema_text}

SAMPLE ROWS (first few rows of the actual data):
{preview_text}

USER QUESTION:
"{question}"

Return ONLY a single JSON object (no markdown, no explanation,
no code fences) with this exact structure:

{{
  "operation": "aggregate" | "compare_periods",
  "required_columns": [list of column names needed for the metric(s)],
  "group_by": [list of column names to group by, empty list if none],
  "aggregation": "sum" | "mean" | "median" | "min" | "max" | "count" | "nunique",
  "filters": [
    {{"column": "<column name>", "operator": "==" | "!=" | ">" | "<" | ">=" | "<=" | "in" | "contains", "value": <value or list of values>}}
  ],
  "sort": "ascending" | "descending" | "",
  "limit": <integer or null>,
  "calculation_description": "<one short sentence describing exactly what was calculated, e.g. 'Summed sales by region for Q3 2025'>",

  // ONLY include the fields below when operation is "compare_periods"
  "period_column": "<column name representing time/period, e.g. 'quarter'>",
  "current_period": "<value identifying the current period, e.g. 'Q3 2025'>",
  "previous_period": "<value identifying the previous period, e.g. 'Q2 2025'>",
  "value_column": "<the numeric column being compared, e.g. 'sales'>"
}}

RULES:
1. Use "aggregate" for direct sums/averages/counts/min/max/rankings
   within a single time period or across the whole dataset.
2. Use "compare_periods" ONLY when the question asks about growth,
   change, increase, decrease, or comparison between two time
   periods (e.g. "grew fastest", "compared to last month",
   "change from Q2 to Q3"). When using "compare_periods", you MUST
   also include "group_by" (e.g. ["region"]) so growth can be
   computed per group.
3. Only reference column names that exist in DATASET SCHEMA above.
   Never invent a column name.
4. For "filters", only use columns and values that actually appear
   in the schema or sample rows. Use "in" when the value should
   match any of several options, "contains" for partial text match.
5. If the question does not need filters, return an empty list
   for "filters" - do not omit the key.
6. If the question does not need a limit, set "limit" to null.
7. "calculation_description" must describe the REAL calculation
   plan, in plain language, so a user can verify what was computed.
8. Return valid, parseable JSON only. No trailing commas.
"""