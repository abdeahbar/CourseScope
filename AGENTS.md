# AGENTS.md

## Project Name

CourseScope

## Project Purpose

CourseScope is a small local AI tool that analyzes Markdown course files and extracts structured educational metadata using a local Ollama model or a local llama.cpp server.

It extracts:

- Prerequisites
- Learning objectives
- Expected results
- Competencies

The output should be valid JSON and optionally exported as Markdown.

## Development Philosophy

This project is an MVP of MVP.

Keep everything:

- simple
- local-first
- easy to understand
- easy to modify
- not over-engineered

Do not add unnecessary architecture.

## Tech Stack

Use:

- Python 3.10+
- Streamlit
- requests
- Ollama local API
- llama.cpp OpenAI-compatible local API

Ollama endpoint:

http://localhost:11434/api/generate

llama.cpp endpoint:

http://127.0.0.1:8080/v1/chat/completions

## Project Structure

Expected structure:

```text
course-scope/
|-- app.py
|-- extractor.py
|-- prompts.py
|-- utils.py
|-- requirements.txt
|-- README.md
|-- AGENTS.md
|-- .gitignore
|-- input/
|   `-- sample-course.md
`-- output/
    `-- .gitkeep
```

## Agent Rules

When modifying this project:

1. Keep the code simple.
2. Do not add a database.
3. Do not add authentication.
4. Do not add Docker unless explicitly requested.
5. Do not add a complex backend.
6. Do not add queues or workers.
7. Do not add batch processing yet.
8. Process one Markdown course at a time.
9. Prefer readable code over clever code.
10. Add comments only where useful.

## UI Requirements

The Streamlit UI should allow the user to:

- upload a Markdown file
- preview/edit the Markdown
- choose an Ollama model
- analyze the course
- view extracted metadata
- download JSON output
- download Markdown report

## AI Extraction Requirements

The model must return this JSON structure:

```json
{
  "course_title": "",
  "prerequisites": [
    {
      "name": "",
      "reason": "",
      "level": "basic | intermediate | advanced",
      "is_explicit": true
    }
  ],
  "objectives": [
    {
      "objective": "",
      "is_explicit": true
    }
  ],
  "expected_results": [
    {
      "result": "",
      "is_explicit": true
    }
  ],
  "competencies": [
    {
      "competency": "",
      "category": "knowledge | skill | method | problem_solving | communication",
      "is_explicit": true
    }
  ],
  "missing_information": [],
  "confidence": "low | medium | high"
}
```

## Prompting Rules

The AI should:

- avoid hallucination
- mark inferred items with `"is_explicit": false`
- mark clearly written items with `"is_explicit": true`
- use simple student-friendly language
- return only valid JSON
- never add text outside the JSON

## Error Handling

The app should clearly handle:

- missing Markdown input
- Ollama not running
- model not installed
- invalid JSON returned by the model

If parsing fails, show the raw model output for debugging.

## Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run app:

```bash
streamlit run app.py
```

Pull default model:

```bash
ollama pull qwen2.5:7b
```

## What Not To Add

Do not add:

- database
- login
- Docker
- API server
- complex folder processing
- cloud services
- paid APIs
- unnecessary frameworks

This project must stay small and useful.
