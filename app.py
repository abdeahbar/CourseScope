import json

import streamlit as st

from extractor import analyze_course
from utils import clean_markdown, result_to_markdown


st.set_page_config(page_title="CourseScope", layout="wide")


def read_uploaded_markdown(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    return uploaded_file.getvalue().decode("utf-8", errors="replace")


def display_items(items: list, empty_message: str, render_item) -> None:
    if not items:
        st.info(empty_message)
        return

    for item in items:
        render_item(item)


st.title("CourseScope")
st.write(
    "A local AI tool that extracts prerequisites, learning objectives, expected "
    "results, and competencies from one Markdown course file."
)

model_name = st.text_input("Ollama model name", value="qwen2.5:7b")
uploaded_file = st.file_uploader("Upload a Markdown course file", type=["md", "markdown", "txt"])

uploaded_text = read_uploaded_markdown(uploaded_file)
if uploaded_text and uploaded_text != st.session_state.get("last_uploaded_text"):
    st.session_state["markdown_text"] = clean_markdown(uploaded_text)
    st.session_state["last_uploaded_text"] = uploaded_text

markdown_text = st.text_area(
    "Preview or edit Markdown before analysis",
    value=st.session_state.get("markdown_text", ""),
    height=420,
    placeholder="Paste your Markdown course content here, or upload a file above.",
)
st.session_state["markdown_text"] = markdown_text

if st.button("Analyze Course", type="primary"):
    if not clean_markdown(markdown_text):
        st.error("No Markdown is provided. Upload a file or paste course content first.")
    elif not model_name.strip():
        st.error("Enter an Ollama model name.")
    else:
        with st.spinner("Analyzing course with local Ollama model..."):
            try:
                st.session_state["result"] = analyze_course(markdown_text, model_name.strip())
                st.session_state["error"] = ""
            except RuntimeError as exc:
                st.session_state["result"] = None
                st.session_state["error"] = str(exc)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

result = st.session_state.get("result")
if result:
    st.divider()
    st.header("Extracted result")

    st.subheader("Course title")
    st.write(result.get("course_title") or "Untitled course")

    st.subheader("Prerequisites")
    display_items(
        result.get("prerequisites") or [],
        "No reliable prerequisites found.",
        lambda item: st.markdown(
            f"- **{item.get('name', 'Unnamed prerequisite')}** "
            f"({item.get('level', 'unknown')}, "
            f"{'explicit' if item.get('is_explicit') else 'inferred'}): "
            f"{item.get('reason', '')}"
        ),
    )

    st.subheader("Objectives")
    display_items(
        result.get("objectives") or [],
        "No reliable objectives found.",
        lambda item: st.markdown(
            f"- {item.get('objective', '')} "
            f"({'explicit' if item.get('is_explicit') else 'inferred'})"
        ),
    )

    st.subheader("Expected results")
    display_items(
        result.get("expected_results") or [],
        "No reliable expected results found.",
        lambda item: st.markdown(
            f"- {item.get('result', '')} "
            f"({'explicit' if item.get('is_explicit') else 'inferred'})"
        ),
    )

    st.subheader("Competencies")
    display_items(
        result.get("competencies") or [],
        "No reliable competencies found.",
        lambda item: st.markdown(
            f"- **{item.get('competency', '')}** "
            f"({item.get('category', 'unknown')}, "
            f"{'explicit' if item.get('is_explicit') else 'inferred'})"
        ),
    )

    st.subheader("Missing information")
    missing_information = result.get("missing_information") or []
    if missing_information:
        for item in missing_information:
            st.markdown(f"- {item}")
    else:
        st.write("None")

    st.subheader("Confidence")
    st.write(result.get("confidence") or "unknown")

    raw_json = json.dumps(result, indent=2, ensure_ascii=False)
    markdown_report = result_to_markdown(result)

    st.subheader("Raw JSON")
    st.json(result)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download JSON",
            data=raw_json,
            file_name="course-scope-result.json",
            mime="application/json",
        )
    with col2:
        st.download_button(
            "Download Markdown report",
            data=markdown_report,
            file_name="course-scope-report.md",
            mime="text/markdown",
        )
