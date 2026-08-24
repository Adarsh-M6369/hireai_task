import pandas as pd
import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="CSV / Data Q&A Agent",
    page_icon="📊",
    layout="wide",
)

# ------------------------------------------------------------------
# Session state setup
# ------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "filename" not in st.session_state:
    st.session_state.filename = None

if "summary" not in st.session_state:
    st.session_state.summary = None

if "history" not in st.session_state:
    st.session_state.history = []  # list of {question, response} dicts


st.title("📊 CSV / Data Q&A Agent")
st.caption(
    "Upload a CSV or Excel file, then ask natural-language questions "
    "about your data. Answers are backed by real Pandas computation."
)


# ------------------------------------------------------------------
# Sidebar: upload + session status
# ------------------------------------------------------------------

with st.sidebar:
    st.header("1. Upload your dataset")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is not None:
        if st.button("Upload", type="primary", width="stretch"):
            with st.spinner("Uploading and analyzing file..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                        )
                    }
                    response = requests.post(
                        f"{API_BASE_URL}/api/upload",
                        files=files,
                        timeout=60,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.session_id = data["session_id"]
                        st.session_state.filename = data["filename"]
                        st.session_state.summary = data["summary"]
                        st.session_state.history = []
                        st.success(f"Uploaded: {data['filename']}")
                    else:
                        detail = response.json().get("detail", response.text)
                        st.error(f"Upload failed: {detail}")

                except requests.exceptions.ConnectionError:
                    st.error(
                        "Could not reach the API. Is your FastAPI server "
                        "running at "
                        f"{API_BASE_URL}? (python server.py)"
                    )
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

    st.divider()

    if st.session_state.session_id:
        st.success(f"Active file: **{st.session_state.filename}**")

        if st.session_state.summary:
            st.metric("Rows", st.session_state.summary.get("rows", "—"))
            st.metric("Columns", st.session_state.summary.get("columns", "—"))

            with st.expander("Column details"):
                columns_df = pd.DataFrame(
                    st.session_state.summary.get("column_details", [])
                )

                # sample_values holds lists of mixed types (str/int/float/None)
                # across rows, which PyArrow can't serialize as a single
                # column type. Convert to a plain display string instead.
                if "sample_values" in columns_df.columns:
                    columns_df["sample_values"] = columns_df[
                        "sample_values"
                    ].apply(
                        lambda values: (
                            ", ".join(str(v) for v in values)
                            if isinstance(values, list)
                            else ""
                        )
                    )

                st.dataframe(columns_df, width="stretch")

        if st.button("Start over / clear session", width="stretch"):
            st.session_state.session_id = None
            st.session_state.filename = None
            st.session_state.summary = None
            st.session_state.history = []
            st.rerun()
    else:
        st.info("No file uploaded yet.")


# ------------------------------------------------------------------
# Main panel: ask questions
# ------------------------------------------------------------------

st.header("2. Ask a question")

if not st.session_state.session_id:
    st.warning("Upload a file from the sidebar first.")
else:
    question = st.text_input(
        "Your question",
        placeholder="e.g. What is the total revenue by region?",
    )

    ask_clicked = st.button("Ask", type="primary")

    if ask_clicked and question.strip():
        with st.spinner("Analyzing your question..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/ask",
                    json={
                        "question": question.strip(),
                        "session_id": st.session_state.session_id,
                    },
                    timeout=120,
                )

                if response.status_code == 200:
                    st.session_state.history.insert(0, response.json())
                else:
                    detail = response.json().get("detail", response.text)
                    st.error(f"Error: {detail}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not reach the API. Is your FastAPI server "
                    f"running at {API_BASE_URL}?"
                )
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    elif ask_clicked:
        st.warning("Please type a question first.")


# ------------------------------------------------------------------
# Render answer history (most recent first)
# ------------------------------------------------------------------

for entry in st.session_state.history:

    st.divider()
    st.subheader(f"❓ {entry.get('question', '')}")

    plan = entry.get("plan") or {}
    if plan:
        with st.expander("🔍 Analysis plan", expanded=False):
            st.json(plan)

    calculation = entry.get("calculation")
    if calculation:
        st.caption(f"🧮 {calculation}")

    supporting_data = entry.get("supporting_data") or []
    if supporting_data:
        st.markdown("**📊 Supporting data**")
        st.dataframe(
            pd.DataFrame(supporting_data),
            width="stretch",
        )

    chart = entry.get("chart")
    if chart:
        chart_url = f"{API_BASE_URL}{chart}"
        st.image(chart_url, width="stretch")

    answer = entry.get("answer")
    if answer:
        st.markdown("**✅ Answer**")
        st.write(answer)