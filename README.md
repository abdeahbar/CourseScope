# CourseScope

CourseScope is a small local AI tool that analyzes Markdown course files and extracts structured educational metadata.

It extracts:

- prerequisites
- learning objectives
- expected results
- competencies

The tool uses a local Ollama model and a simple Streamlit UI.

## Features

- Upload or paste a Markdown course
- Analyze it using a local Ollama model
- Extract structured course metadata
- Export results as JSON
- Export results as Markdown

## Tech Stack

- Python
- Streamlit
- Ollama
- requests

## Install

```bash
pip install -r requirements.txt
```

## Pull a local model

```bash
ollama pull qwen2.5:7b
```

## Run Ollama

```bash
ollama serve
```

## Run CourseScope

```bash
streamlit run app.py
```

## Default model

```txt
qwen2.5:7b
```

## Project Status

MVP under development.

The goal is to keep this project simple, local-first, and easy to understand.
