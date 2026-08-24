import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import router


app = FastAPI(
    title="CSV / Data Q&A Agent",
    description=(
        "AI agent that answers natural-language questions "
        "about CSV and Excel datasets using real computation."
    ),
    version="1.0.0",
)

# ------------------------------------------------------------------
# CORS - allows a frontend running on a different origin/port
# (e.g. React/Vite on localhost:5173) to call this API.
# Tighten allow_origins to your actual frontend URL in production.
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Serve generated charts as static files so the frontend can load
# them directly via a URL like /charts/<filename>.png
#
# NOTE: this points at "generated_charts", matching the folder name
# referenced in server.py's reload_excludes. If visualization.py
# saves charts somewhere else, update this directory name to match.
# ------------------------------------------------------------------
os.makedirs("generated_charts", exist_ok=True)
app.mount(
    "/charts",
    StaticFiles(directory="generated_charts"),
    name="charts",
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "CSV / Data Q&A Agent is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# ------------------------------------------------------------------
# NOTE: No uvicorn.run() block here on purpose.
# server.py is the single canonical entry point for running this
# app (it already configures host/port/reload_excludes correctly).
# Start the app with:
#     python server.py
# ------------------------------------------------------------------