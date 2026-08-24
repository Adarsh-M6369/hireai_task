import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from src.agent import DataAgent
from src.data_analyzer import (
    DataAnalyzer,
    dataframe_to_records,
)
from src.data_loader import (
    get_data_preview,
    get_data_summary,
    load_data,
)
from src.visualization import create_chart


logger = logging.getLogger("csv_data_qa_agent")

router = APIRouter(
    prefix="/api",
    tags=["Data Q&A"],
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


agent = DataAgent()


class QuestionRequest(BaseModel):
    question: str
    session_id: str


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_session_file(session_id: str) -> Path:
    """
    Find the dataset uploaded for a given session.
    Each session's file is prefixed with its session_id, so
    concurrent users/uploads never collide or get mixed up.
    """

    matches = [
        file
        for file in UPLOAD_DIR.iterdir()
        if file.is_file()
        and file.name.startswith(f"{session_id}_")
        and file.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not matches:
        raise HTTPException(
            status_code=400,
            detail=(
                "No dataset found for this session. "
                "Please upload a CSV or Excel file first."
            ),
        )

    # If multiple uploads happened in the same session, use the latest.
    return max(matches, key=os.path.getmtime)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """
    Upload a CSV or Excel file.
    Returns a session_id that must be passed to /ask for
    all follow-up questions about this specific file.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Please upload a CSV or Excel file."
            ),
        )

    session_id = uuid.uuid4().hex
    safe_filename = f"{session_id}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        df = load_data(str(file_path))

        summary = get_data_summary(df)
        preview = get_data_preview(df, rows=5)

        return {
            "message": "File uploaded successfully.",
            "session_id": session_id,
            "filename": file.filename,
            "summary": summary,
            "preview": preview,
        }

    except Exception as e:

        if file_path.exists():
            file_path.unlink()

        logger.exception("Upload failed for %s", file.filename)

        raise HTTPException(
            status_code=400,
            detail=f"Could not process file: {e}",
        )


@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
):
    """
    Ask a natural-language question about a previously
    uploaded dataset, identified by session_id.

    Response shape:
    {
        "question": ...,
        "plan": {...},              # how the AI interpreted the question
        "supporting_data": [...],   # real pandas-computed rows
        "calculation": "...",       # the formula/logic actually used
        "answer": "...",            # plain-language answer
        "chart": "..."              # URL/path to the generated chart
    }
    """

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    latest_file = _get_session_file(request.session_id)

    try:
        # --------------------------------
        # STEP 1: Load the dataset
        # --------------------------------
        df = load_data(str(latest_file))

        # --------------------------------
        # STEP 2: Understand the dataset
        # --------------------------------
        schema = get_data_summary(df)
        preview = get_data_preview(df, rows=5)

        # --------------------------------
        # STEP 3: Ask AI to understand
        # the user's question
        # --------------------------------
        analysis = agent.create_analysis(
            question=question,
            schema=schema,
            preview=preview,
        )

        # --------------------------------
        # STEP 4: Perform REAL computation
        # using Pandas
        # --------------------------------
        analyzer = DataAnalyzer(df)
        result_df = analyzer.execute(analysis)

        result_records = dataframe_to_records(result_df)

        # --------------------------------
        # STEP 5: Generate chart
        # --------------------------------
        chart_path = None

        try:
            chart_path = create_chart(
                result_df,
                title=question,
            )
        except Exception:
            # A failed chart should never break the whole answer.
            logger.exception("Chart generation failed for question: %s", question)

        # --------------------------------
        # STEP 6: Let AI explain the
        # actual computed result
        # --------------------------------
        result_text = result_df.to_string(index=False)

        answer = agent.explain_result(
            question=question,
            analysis=analysis,
            result=result_text,
        )

        # --------------------------------
        # STEP 7: Return everything
        # --------------------------------
        return {
            "question": question,
            "plan": {
                "operation": analysis.get("operation", ""),
                "required_columns": analysis.get("required_columns", []),
                "group_by": analysis.get("group_by", []),
                "aggregation": analysis.get("aggregation", ""),
                "sort": analysis.get("sort", ""),
                "limit": analysis.get("limit"),
            },
            "calculation": analysis.get("calculation_description", ""),
            "supporting_data": result_records,
            "answer": answer,
            "chart": chart_path,
        }

    except HTTPException:
        raise

    except ValueError as e:
        # Validation-type errors (bad columns, unsupported aggregation, etc.)
        logger.warning("Analysis validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception("Unexpected error answering question: %s", question)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while analyzing your question.",
        )