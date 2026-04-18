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


def _strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments without touching quoted strings."""
    result = []
    in_string = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and not (text[index] == "*" and text[index + 1] == "/"):
                index += 1
            index += 2
            continue

        result.append(char)
        index += 1

    return "".join(result)


def _remove_trailing_json_commas(text: str) -> str:
    """Remove trailing commas before } or ] without touching quoted strings."""
    result = []
    in_string = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue

        result.append(char)
        index += 1

    return "".join(result)


def _parse_json_object(text: str) -> dict:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("The model returned JSON, but it was not an object.")

    return parsed


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

    candidates = [text]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.append(match.group(0))

    last_error: Exception | None = None
    for candidate in candidates:
        for parser_input in (
            candidate,
            _remove_trailing_json_commas(_strip_json_comments(candidate)).strip(),
        ):
            try:
                return _parse_json_object(parser_input)
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = exc

    raise ValueError("The model response did not contain a valid JSON object.") from last_error


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
