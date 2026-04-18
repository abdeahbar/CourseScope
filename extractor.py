import json
import os

import requests

from prompts import build_extraction_prompt
from utils import clean_markdown, safe_json_parse


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
LLAMACPP_CHAT_URL = os.getenv(
    "LLAMACPP_CHAT_URL",
    "http://127.0.0.1:8080/v1/chat/completions",
)
LLAMACPP_MODEL = os.getenv("LLAMACPP_MODEL", "local-model")
ALLOWED_LEVELS = {"basic", "intermediate", "advanced"}
ALLOWED_CATEGORIES = {"knowledge", "skill", "method", "problem_solving", "communication"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def _as_string(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_bool(value) -> bool:
    return value if isinstance(value, bool) else False


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def normalize_extraction_result(result: dict) -> dict:
    """Keep local model output in the exact JSON shape CourseScope expects."""
    prerequisites = []
    for item in _as_list(result.get("prerequisites")):
        if not isinstance(item, dict):
            continue
        level = _as_string(item.get("level")).lower()
        prerequisites.append(
            {
                "name": _as_string(item.get("name")),
                "reason": _as_string(item.get("reason")),
                "level": level if level in ALLOWED_LEVELS else "basic",
                "is_explicit": _as_bool(item.get("is_explicit")),
            }
        )

    objectives = []
    for item in _as_list(result.get("objectives")):
        if not isinstance(item, dict):
            continue
        objectives.append(
            {
                "objective": _as_string(item.get("objective")),
                "is_explicit": _as_bool(item.get("is_explicit")),
            }
        )

    expected_results = []
    for item in _as_list(result.get("expected_results")):
        if not isinstance(item, dict):
            continue
        expected_results.append(
            {
                "result": _as_string(item.get("result")),
                "is_explicit": _as_bool(item.get("is_explicit")),
            }
        )

    competencies = []
    for item in _as_list(result.get("competencies")):
        if not isinstance(item, dict):
            continue
        category = _as_string(item.get("category")).lower()
        competency = _as_string(item.get("competency"))
        if category not in ALLOWED_CATEGORIES:
            category = competency.lower() if competency.lower() in ALLOWED_CATEGORIES else "knowledge"
        competencies.append(
            {
                "competency": competency,
                "category": category,
                "is_explicit": _as_bool(item.get("is_explicit")),
            }
        )

    missing_information = [
        _as_string(item)
        for item in _as_list(result.get("missing_information"))
        if _as_string(item)
    ]
    confidence = _as_string(result.get("confidence")).lower()

    return {
        "course_title": _as_string(result.get("course_title")),
        "prerequisites": prerequisites,
        "objectives": objectives,
        "expected_results": expected_results,
        "competencies": competencies,
        "missing_information": missing_information,
        "confidence": confidence if confidence in ALLOWED_CONFIDENCE else "low",
    }


def list_ollama_models() -> list[str]:
    """Return the names of locally installed Ollama models."""
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Ollama is not running. Start Ollama to load the model list."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Ollama took too long to return the model list."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not load Ollama models: {exc}") from exc

    if not response.ok:
        raise RuntimeError(f"Ollama returned an error while loading models: {response.text}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned invalid model list JSON: {response.text}") from exc

    model_names = []
    for item in data.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            model_names.append(name)

    return sorted(set(model_names), key=str.lower)


def _invalid_json_result(provider: str, raw_output: str) -> dict:
    return {
        "course_title": "",
        "prerequisites": [],
        "objectives": [],
        "expected_results": [],
        "competencies": [],
        "missing_information": [
            f"{provider} returned invalid JSON. See raw_output for debugging."
        ],
        "confidence": "low",
        "error": "The model returned invalid JSON.",
        "raw_output": raw_output,
    }


def analyze_course_with_ollama(markdown_text: str, model: str) -> dict:
    """
    Analyze a Markdown course with a local Ollama model and return a dict.

    Raises RuntimeError with user-friendly messages for connection, model,
    and JSON parsing errors.
    """
    cleaned_text = clean_markdown(markdown_text)
    if not cleaned_text:
        raise RuntimeError("No Markdown content was provided.")

    prompt = build_extraction_prompt(cleaned_text)
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,
            # Keep the MVP responsive and avoid inheriting a huge global Ollama context.
            "num_ctx": 4096,
            "num_predict": 1200,
        },
    }

    try:
        response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=180)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Ollama is not running. Start Ollama and try again."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "Ollama took too long to respond. Try again or use a smaller model."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not call Ollama: {exc}") from exc

    if response.status_code == 404:
        raise RuntimeError(
            f"The Ollama model '{model}' was not found. Install it with: ollama pull {model}"
        )

    if not response.ok:
        raise RuntimeError(f"Ollama returned an error: {response.text}")

    try:
        ollama_data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned invalid API JSON: {response.text}") from exc

    raw_model_output = ollama_data.get("response", "")

    try:
        return normalize_extraction_result(safe_json_parse(raw_model_output))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "The model returned invalid JSON.\n\nRaw model output:\n"
            f"{raw_model_output}"
        ) from exc


def analyze_course_with_llamacpp(markdown_text: str, model: str | None = None) -> dict:
    """
    Analyze a Markdown course with a running llama.cpp server.

    The llama.cpp server must expose its OpenAI-compatible API at:
    http://127.0.0.1:8080/v1/chat/completions
    """
    cleaned_text = clean_markdown(markdown_text)
    if not cleaned_text:
        raise RuntimeError("No Markdown content was provided.")

    prompt = build_extraction_prompt(cleaned_text)
    api_model = model or LLAMACPP_MODEL
    payload = {
        "model": api_model,
        "messages": [
            {
                "role": "system",
                "content": "You are an educational curriculum analyst. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
        "response_format": {
            "type": "json_object",
        },
    }

    try:
        response = requests.post(LLAMACPP_CHAT_URL, json=payload, timeout=180)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "llama.cpp server is not running. Start llama-server and try again."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "llama.cpp took too long to respond. Try a smaller GGUF model."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not call llama.cpp: {exc}") from exc

    if not response.ok:
        raise RuntimeError(f"llama.cpp returned an error: {response.text}")

    try:
        data = response.json()
        raw_model_output = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"llama.cpp returned invalid API JSON: {response.text}") from exc

    try:
        return normalize_extraction_result(safe_json_parse(raw_model_output))
    except (ValueError, json.JSONDecodeError):
        return _invalid_json_result("llama.cpp", raw_model_output)


def analyze_course(markdown_text: str, provider: str, model: str | None = None) -> dict:
    if provider == "ollama":
        if not model:
            raise RuntimeError("Select an Ollama model.")
        return analyze_course_with_ollama(markdown_text, model)

    if provider == "llamacpp":
        return analyze_course_with_llamacpp(markdown_text, model)

    raise RuntimeError(f"Unknown AI provider: {provider}")
