import uuid
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure
import pandas as pd


CHART_DIR = Path("generated_charts")
CHART_DIR.mkdir(exist_ok=True)


def create_chart(
    result: pd.DataFrame,
    title: str = "Analysis Result"
) -> str | None:

    if result.empty:
        return None

    if len(result.columns) < 2:
        return None

    x_column = result.columns[0]
    y_column = result.columns[-1]

    if not pd.api.types.is_numeric_dtype(
        result[y_column]
    ):
        return None

    # Use the object-oriented Figure API instead of the global
    # pyplot state machine. This avoids cross-request interference
    # when multiple charts are generated concurrently.
    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)

    x_values = result[x_column].astype(str)

    if len(result) <= 15:
        ax.bar(x_values, result[y_column])
    else:
        ax.plot(x_values, result[y_column], marker="o")

    ax.set_title(title)
    ax.set_xlabel(str(x_column))
    ax.set_ylabel(str(y_column))

    ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()

    # Unique filename per chart: avoids overwriting previous charts,
    # race conditions on concurrent requests, and stale browser caching.
    filename = f"{uuid.uuid4().hex}.png"
    file_path = CHART_DIR / filename

    fig.savefig(file_path)

    # Return a URL path matching the /charts static mount in main.py,
    # not a raw filesystem path, so the frontend can load it directly.
    return f"/charts/{filename}"