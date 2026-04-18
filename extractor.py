import json

import requests

from prompts import build_extraction_prompt
from utils import clean_markdown, safe_json_parse


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"


def analyze_course(markdown_text: str, model: str) -> dict:
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
            "temperature": 0.1
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
