# GenAI Code Debugger

A multi-pass Python code debugging pipeline that combines deterministic AST analysis with a locally hosted Qwen 2.5 Coder model through Ollama to identify, explain, and fix bugs in Python code. The project uses a FastAPI backend, a React + Vite frontend, and a small RAG layer for retrieval-backed prompting.[1][2][3][4]

***

## Overview

The pipeline first performs deterministic AST-based bug detection for known structural patterns, then sends the code, logs, and retrieved context to the local model for explanation and semantic bug discovery. It can optionally run a second pass on longer files, critique the answer against a checklist, refine the result, and deduplicate repeated bug reports before returning the final response.[5][1][2]

## Architecture

```text
Input: code + logs + question
         │
         ▼
┌─────────────────────────────┐
│       AST Pre-Detector      │
│  · =+ instead of +=         │
│  · mutable module globals   │
│  · bare division            │
│  · max()/min() empty guard  │
│  · date string comparison   │
└─────────────┬───────────────┘
              │ confirmed_bugs[]
              ▼
┌─────────────────────────────┐
│       LLM First Pass        │
│  · explain + fix AST bugs   │
│  · inspect logs for         │
│    semantic/runtime bugs    │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│        Second Pass          │
│  · used for longer code     │
│  · finds additional bugs    │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│      Critique + Refine      │
│  · validates answer format  │
│  · removes hallucinations   │
│  · adds missed issues       │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│       Dedup + Renumber      │
│  · merge duplicate blocks   │
│  · normalize Bug 1..N       │
└─────────────────────────────┘
```

***

## Project Structure

```text
GENAI-DEBUGGER/
├── backend/
│   ├── knowledge_base/          # RAG source documents
│   ├── models/
│   │   └── request.py           # Pydantic request schema(s)
│   ├── rag/                     # Vector store and retrieval helpers
│   ├── routes/
│   │   └── query.py             # FastAPI route(s), including /debug
│   ├── scripts/
│   │   ├── build_index.py       # Build vector index
│   │   └── build_knowledge_base.py
│   ├── services/
│   │   └── llm_service.py       # AST + LLM multi-pass pipeline
│   ├── .env                     # Local environment config
│   └── main.py                  # FastAPI app entry point
└── frontend/
    ├── src/                     # React source
    ├── public/
    ├── index.html
    ├── package.json
    └── vite.config.js
```

***

## Features

- Deterministic AST pre-detection for recurring Python bug patterns.
- Multi-pass local LLM analysis using Ollama's `POST /api/generate` endpoint.[1][2]
- Optional second-pass review for longer code snippets.
- Critique-and-refine stage to reduce hallucinated fixes.
- Deduplication of repeated bug blocks.
- Final renumbering so output starts consistently from `Bug 1`.
- FastAPI backend for API access and a Vite-based React frontend for local interaction.[3][4][6]

***

## Supported Bug Patterns

| Pattern | Detection Method |
|---|---|
| `=+` instead of `+=` | AST `UnaryOp(UAdd)` |
| Stale module-level mutable state | AST module-level assignment scan |
| Division without zero check | AST `BinOp(Div)` |
| `max()` / `min()` on possibly empty container | AST `Call` pattern |
| Date-string comparison against `strftime(...)` | AST `Compare` pattern |
| Call-chain division issues | Logs + LLM reasoning |
| Counter reassign / return-flow issues | LLM critique + refine |
| Other semantic bugs visible from logs | LLM passes |

***

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Qwen 2.5 Coder via Ollama API |
| Backend | FastAPI + Python |
| Static Analysis | Python `ast` module |
| Retrieval | FAISS / Chroma-style vector store layer |
| Frontend | React + Vite |
| API Style | REST JSON |

***

## Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama installed locally
- The required Ollama model pulled locally before starting the backend.[2][1]

***

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/genai-debugger.git
cd genai-debugger
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
# Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
OLLAMA_URL=http://localhost:11434/api/generate
MODEL=qwen2.5-coder:7b-instruct
```

Ollama serves its local API under `http://localhost:11434/api`, and `/api/generate` is the text generation endpoint used by this project.[2][1]

### 3. Pull model and start Ollama

```bash
ollama pull qwen2.5-coder:7b-instruct
ollama serve
```

### 4. Build the knowledge base and index

```bash
python scripts/build_knowledge_base.py
python scripts/build_index.py
```

### 5. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

FastAPI projects are commonly run with Uvicorn using `main:app --reload`, and local development is typically accessed on `http://127.0.0.1:8000` or `http://localhost:8000`.[3][7]

### 6. Frontend setup

```bash
cd ../frontend
npm install
npm run dev
```

Vite uses port `5173` by default in development unless overridden in config or CLI flags.[4][6][8]

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

***

## API

### `POST /debug`

**Request body**

```json
{
  "query": "Identify all the bugs",
  "code": "total = 0\n\ndef process(x):\n    total =+ x\n",
  "logs": "total shows 5 after 3 calls — expected 15"
}
```

**Example response**

```json
{
  "ast_bugs": [
    {
      "line": 4,
      "code": "total =+ x",
      "type": "=+ instead of +="
    }
  ],
  "initial_answer": "Bug 1:\nIssue: ...",
  "critique": "Correct? NO\n...",
  "final_answer": "Bug 1:\nIssue: `total =+ x`\nExplanation: ...\nFix:\n```python\ntotal += x\n```"
}
```

***

## Python Usage

```python
from services.llm_service import run_pipeline

result = run_pipeline(
    query="Identify all the bugs",
    code=your_code_string,
    logs="ZeroDivisionError on line 12"
)

print(result["final_answer"])
```

If the current pipeline includes output normalization, the final answer should be renumbered from `Bug 1` before returning to the caller.

***

## Fix Principles

The prompt design uses general debugging principles instead of overfitting to a single checklist:

1. Safe fallbacks must be semantically correct.
2. Empty-container guards should use explicit `if container` checks.
3. Integer counters passed into helpers must be returned and reassigned when updated.
4. Mutable module-level state should move inside the entry function and be passed explicitly where needed.

***

## Limitations

- AST pre-detection is Python-specific.
- Deeper semantic bugs still depend on the local model and log quality.
- Very small local models may miss long-range call-chain issues.
- False positives are still possible on some date-comparison and division patterns.
- Exact behavior depends on the current `llm_service.py` pipeline and prompt wording.

***
