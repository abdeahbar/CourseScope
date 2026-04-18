import json
from pathlib import Path

import streamlit as st

from extractor import analyze_course, list_ollama_models
from utils import clean_markdown, result_to_markdown


st.set_page_config(page_title="CourseScope", layout="wide")
MODELS_DIR = Path(__file__).parent / "models"


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


def list_gguf_models() -> list[str]:
    """Return local GGUF model filenames from the models folder."""
    if not MODELS_DIR.exists():
        return []

    return sorted(path.name for path in MODELS_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".gguf")


def refresh_model_list() -> None:
    """Load local Ollama models into Streamlit session state."""
    try:
        st.session_state["ollama_models"] = list_ollama_models()
        st.session_state["model_list_error"] = ""
    except RuntimeError as exc:
        st.session_state["ollama_models"] = []
        st.session_state["model_list_error"] = str(exc)


st.title("CourseScope")
st.write(
    "A local AI tool that extracts prerequisites, learning objectives, expected "
    "results, and competencies from one Markdown course file."
)

provider_label = st.selectbox("AI provider", options=["Ollama", "llama.cpp"])
provider = "ollama" if provider_label == "Ollama" else "llamacpp"

if provider == "ollama" and (
    "ollama_models" not in st.session_state or st.session_state.get("model_list_error")
):
    refresh_model_list()

model_col, refresh_col = st.columns([4, 1])
with refresh_col:
    st.write("")
    if st.button("Refresh models"):
        if provider == "ollama":
            refresh_model_list()

with model_col:
    if provider == "ollama":
        installed_models = st.session_state.get("ollama_models", [])
        model_options = installed_models or ["qwen2.5:3b-instruct"]
        preferred_models = [
            "qwen2.5:3b-instruct",
            "llama3.2:3b",
            "qwen2.5:7b-instruct",
            "qwen2.5:7b",
        ]
        default_model = next((model for model in preferred_models if model in model_options), model_options[0])
        default_index = model_options.index(default_model)
        selected_model = st.selectbox(
            "Ollama model",
            options=model_options,
            index=default_index,
        )
    else:
        gguf_models = list_gguf_models()
        if gguf_models:
            selected_model = st.selectbox("GGUF model", options=gguf_models, index=0)
        else:
            st.selectbox("GGUF model", options=["No GGUF models found"], index=0, disabled=True)
            selected_model = ""

if provider == "ollama" and st.session_state.get("model_list_error"):
    st.warning(st.session_state["model_list_error"])
elif provider == "ollama" and not st.session_state.get("ollama_models"):
    st.info("No local Ollama models were found. Install one with: ollama pull qwen2.5:3b-instruct")
elif provider == "llamacpp" and not list_gguf_models():
    st.warning("No GGUF models found. Add .gguf files to the models folder.")

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
    elif provider == "ollama" and not selected_model.strip():
        st.error("Select an Ollama model.")
    elif provider == "llamacpp" and not selected_model:
        st.error("Add a GGUF model to the models folder before using llama.cpp.")
    else:
        with st.spinner(f"Analyzing course with {provider_label}..."):
            try:
                model = selected_model.strip() if provider == "ollama" else None
                st.session_state["result"] = analyze_course(markdown_text, provider, model)
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
    st.code(raw_json, language="json")

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
