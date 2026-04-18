import json

import requests

from prompts import build_extraction_prompt
from utils import clean_markdown, safe_json_parse


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
LLAMACPP_CHAT_URL = "http://127.0.0.1:8080/v1/chat/completions"


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
        return safe_json_parse(raw_model_output)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "The model returned invalid JSON.\n\nRaw model output:\n"
            f"{raw_model_output}"
        ) from exc


def analyze_course_with_llamacpp(markdown_text: str) -> dict:
    """
    Analyze a Markdown course with a running llama.cpp server.

    The llama.cpp server must expose its OpenAI-compatible API at:
    http://127.0.0.1:8080/v1/chat/completions
    """
    cleaned_text = clean_markdown(markdown_text)
    if not cleaned_text:
        raise RuntimeError("No Markdown content was provided.")

    prompt = build_extraction_prompt(cleaned_text)
    payload = {
        "model": "local-model",
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
        return safe_json_parse(raw_model_output)
    except (ValueError, json.JSONDecodeError):
        return _invalid_json_result("llama.cpp", raw_model_output)


def analyze_course(markdown_text: str, provider: str, model: str | None = None) -> dict:
    if provider == "ollama":
        if not model:
            raise RuntimeError("Select an Ollama model.")
        return analyze_course_with_ollama(markdown_text, model)

    if provider == "llamacpp":
        return analyze_course_with_llamacpp(markdown_text)

    raise RuntimeError(f"Unknown AI provider: {provider}")
