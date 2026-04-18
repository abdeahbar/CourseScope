# CourseScope

CourseScope is a small local AI tool that reads one Markdown course file and
extracts structured educational metadata with a local AI model.

It extracts:

- Prerequisites needed before studying the course
- Learning objectives of the course
- Expected results after studying the course
- Competencies developed by the course

The app runs locally with Streamlit and supports two local AI providers:

- Ollama
- llama.cpp server

Ollama uses model names and calls:

```text
http://localhost:11434/api/generate
```

llama.cpp uses a loaded `.gguf` model and calls:

```text
http://127.0.0.1:8080/v1/chat/completions
```

No database, authentication, Docker, or external API is required. After the
local model is installed, the app can work offline.

## Requirements

- Python 3.10+
- Ollama installed and running, or a llama.cpp server running locally
- A local Ollama model name or a local `.gguf` model file

## Install dependencies

From this folder, run:

```bash
pip install -r requirements.txt
```

## Use Ollama

Ollama uses model names such as `qwen2.5:3b-instruct`. Start Ollama on your
machine. In most installations, Ollama runs automatically. You can also start it
manually:

```bash
ollama serve
```

## Pull a model

Install the recommended MVP model used by CourseScope:

```bash
ollama pull qwen2.5:3b-instruct
```

You can use another local Ollama model by selecting it in the app.

In the app, select:

```text
AI provider: Ollama
```

CourseScope will load installed Ollama models from:

```text
http://localhost:11434/api/tags
```

## Use llama.cpp

llama.cpp uses local `.gguf` files. Put GGUF models in:

```text
models/
```

For example:

```text
models/qwen2.5-7b-instruct-q4_k_m.gguf
```

GGUF model files are ignored by git.

Start llama.cpp server manually:

```powershell
.\llama-server.exe -m .\models\qwen2.5-7b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8080 -c 4096 -ngl 99 --flash-attn
```

In the app, select:

```text
AI provider: llama.cpp
```

CourseScope lists `.gguf` files from the `models/` folder and sends requests to:

```text
http://127.0.0.1:8080/v1/chat/completions
```

## Run the Streamlit app

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal.

On Windows, you can also use the included PowerShell scripts:

```powershell
.\setup_venv.ps1
.\run_app.ps1
```

`run_app.ps1` stops existing Ollama processes, clears known bad local
overrides, starts Ollama with CourseScope settings, then starts the Streamlit
app. It sets a local Ollama context length of `4096` for this app so large
global Ollama settings do not make the MVP slow or memory-heavy.

The script can also start llama.cpp, but it is disabled by default. To enable
it, edit the variables at the top of `run_app.ps1`:

```powershell
$LLAMA_SERVER_PATH = ".\llama.cpp\llama-server.exe"
$LLAMA_MODEL_PATH = ".\models\model.gguf"
$LLAMA_PORT = 8080
$START_LLAMA_CPP = $true
```

## Performance notes

For faster local analysis, start with a smaller instruction model such as
`qwen2.5:3b-instruct`, `llama3.2:3b`, or `qwen2.5:7b-instruct`.

The app explicitly sends these Ollama options:

```json
{
  "num_ctx": 4096,
  "num_predict": 1200,
  "temperature": 0.1
}
```

This prevents CourseScope from inheriting very large global Ollama context
settings.

To check whether Ollama is using the GPU, run:

```powershell
ollama ps
```

If the `PROCESSOR` column shows `100% CPU`, check the Ollama server log at:

```text
%LOCALAPPDATA%\Ollama\server.log
```

## How to use

1. Upload a Markdown course file, or paste course content into the text area.
2. Edit the Markdown if needed.
3. Select one of your locally installed Ollama models.
4. Click **Analyze Course**.
5. Review the structured result and raw JSON.
6. Download the result as JSON or as a Markdown report.

## Sample file

A sample course is included at:

```text
input/sample-course.md
```

## Expected JSON output

The model is instructed to return this structure:

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

## Error handling

The app shows clear errors when:

- No Markdown is provided
- Ollama is not running
- The selected model is not installed
- The model returns invalid JSON

If JSON parsing fails, the raw model output is shown to help debugging.
