from pathlib import Path
import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def load_data(file_path: str) -> pd.DataFrame:
    """
    Load a CSV or Excel file into a Pandas DataFrame.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            # Fallback for files saved with Windows/Excel encodings
            df = pd.read_csv(path, encoding="cp1252")

    elif extension in {".xlsx", ".xls"}:
        df = pd.read_excel(path)

    else:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            "Only CSV and Excel files are supported."
        )

    if df.empty:
        raise ValueError("The uploaded file contains no data.")

    # Normalize column names: strip stray whitespace that can cause
    # silent lookup failures later (e.g. "Region " != "Region").
    df.columns = [str(col).strip() for col in df.columns]

    return df


def get_data_summary(df: pd.DataFrame) -> dict:
    """
    Return useful metadata about the dataset, including a few
    sample values per low-cardinality column. This helps the AI
    correctly identify categorical columns (e.g. 'region', 'quarter')
    and their actual values when building an analysis plan.
    """

    columns = []

    for column in df.columns:

        series = df[column]
        unique_count = int(series.nunique())

        sample_values = None

        if unique_count <= 20:
            sample_values = (
                series.dropna()
                .unique()[:10]
                .tolist()
            )
            # Ensure JSON-safe values (e.g. numpy types, timestamps)
            sample_values = [
                str(value) if not isinstance(
                    value, (int, float, bool, str)
                ) else value
                for value in sample_values
            ]

        columns.append(
            {
                "name": str(column),
                "dtype": str(series.dtype),
                "non_null": int(series.notna().sum()),
                "unique_values": unique_count,
                "sample_values": sample_values,
            }
        )

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_details": columns,
    }


def get_data_preview(
    df: pd.DataFrame,
    rows: int = 5
) -> list[dict]:
    """
    Return a small preview of the dataset.
    """

    preview = df.head(rows).copy()

    # Convert values to JSON-safe representations
    preview = preview.astype(object).where(
        preview.notna(),
        None
    )

    return preview.to_dict(orient="records")