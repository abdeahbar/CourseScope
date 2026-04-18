import json
import re
from typing import Any


def clean_markdown(text: str) -> str:
    """Normalize uploaded or pasted Markdown while preserving course content."""
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
    return normalized.strip()


def safe_json_parse(raw_text: str) -> dict:
    """
    Parse JSON from model output.

    Ollama with format=json should return clean JSON, but this also handles
    occasional fenced JSON or extra text around the JSON object.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("The model returned an empty response.")

    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("The model response did not contain a JSON object.")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("The model returned JSON, but it was not an object.")

    return parsed


def _format_bool(value: Any) -> str:
    return "explicit" if value is True else "inferred"


def _format_list_section(items: list, empty_message: str, formatter) -> str:
    if not items:
        return f"- {empty_message}"

    return "\n".join(formatter(item) for item in items)


def result_to_markdown(result: dict) -> str:
    """Convert an extraction result into a readable Markdown report."""
    title = result.get("course_title") or "Untitled course"
    confidence = result.get("confidence") or "unknown"
    missing_information = result.get("missing_information") or []

    prerequisites = _format_list_section(
        result.get("prerequisites") or [],
        "No reliable prerequisites found.",
        lambda item: (
            f"- **{item.get('name', 'Unnamed prerequisite')}** "
            f"({item.get('level', 'unknown')}, {_format_bool(item.get('is_explicit'))})"
            f": {item.get('reason', '')}".rstrip()
        ),
    )

    objectives = _format_list_section(
        result.get("objectives") or [],
        "No reliable objectives found.",
        lambda item: (
            f"- {item.get('objective', '')} "
            f"({_format_bool(item.get('is_explicit'))})"
        ).strip(),
    )

    expected_results = _format_list_section(
        result.get("expected_results") or [],
        "No reliable expected results found.",
        lambda item: (
            f"- {item.get('result', '')} "
            f"({_format_bool(item.get('is_explicit'))})"
        ).strip(),
    )

    competencies = _format_list_section(
        result.get("competencies") or [],
        "No reliable competencies found.",
        lambda item: (
            f"- **{item.get('competency', '')}** "
            f"({item.get('category', 'unknown')}, {_format_bool(item.get('is_explicit'))})"
        ).strip(),
    )

    missing = "\n".join(f"- {item}" for item in missing_information) if missing_information else "- None"

    return f"""# CourseScope Report

## Course title

{title}

## Prerequisites

{prerequisites}

## Learning objectives

{objectives}

## Expected results

{expected_results}

## Competencies

{competencies}

## Missing information

{missing}

## Confidence

{confidence}
"""
