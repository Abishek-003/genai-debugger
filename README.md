# GenAI Code Debugger

A multi-pass code debugging pipeline that combines deterministic AST analysis with a locally-hosted Qwen 2.5 Coder 7B model (via Ollama) to identify and fix bugs in Python code. Built with a FastAPI backend and a React + Vite frontend.

***

## Architecture

```
Input: code + logs + question
         │
         ▼
┌─────────────────────────────┐
│      AST Pre-Detector       │  ← deterministic, 100% recall
│  · =+ instead of +=         │
│  · mutable module globals   │
│  · bare division / 0        │
│  · max()/min() empty guard  │
│  · date string comparison   │
└─────────────┬───────────────┘
              │  confirmed_bugs[]
              ▼
┌─────────────────────────────┐
│     LLM First Pass          │  ← explains + fixes confirmed bugs
│   Qwen 2.5 Coder 7B         │    catches semantic bugs from logs
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│     Second Pass             │  ← finds missed bugs (>20 lines)
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│   Critique + Refine         │  ← validates and corrects answer
│   (when logs present)       │    removes hallucinations
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────┐
│     Deduplication           │  ← fingerprints Issue + Fix lines
└─────────────────────────────┘
```

***

## Project Structure

```
GENAI-DEBUGGER/
├── backend/
│   ├── knowledge_base/          # RAG document store
│   ├── models/
│   │   └── request.py           # Pydantic request models
│   ├── rag/                     # Vector store + retrieval
│   ├── routes/
│   │   └── query.py             # FastAPI route — /debug endpoint
│   ├── scripts/
│   │   ├── build_index.py       # Build FAISS/Chroma index
│   │   └── build_knowledge_base.py
│   ├── services/
│   │   └── llm_service.py       # Core pipeline (AST + LLM passes)
│   ├── .env                     # Local config — NOT committed
│   └── main.py                  # FastAPI app entry point
└── frontend/
    ├── src/                     # React components
    ├── public/
    ├── index.html
    ├── package.json
    └── vite.config.js
```

***

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/genai-debugger.git
cd genai-debugger
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
OLLAMA_URL=http://localhost:11434/api/generate
MODEL=qwen2.5-coder:7b-instruct
```

### 3. Pull the model and start Ollama

```bash
ollama pull qwen2.5-coder:7b-instruct
ollama serve
```

### 4. Build the RAG knowledge base

```bash
python scripts/build_knowledge_base.py
python scripts/build_index.py
```

### 5. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

### 6. Frontend setup

```bash
cd ../frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. Backend API at `http://localhost:8000`.

***

## API

### `POST /debug`

**Request body:**

```json
{
  "query": "Identify all the bugs",
  "code": "total = 0\n\ndef process(x):\n    total =+ x\n",
  "logs": "total shows 5 after 3 calls — expected 15"
}
```

**Response:**

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

### Python (direct)

```python
from services.llm_service import run_pipeline

result = run_pipeline(
    query="Identify all the bugs",
    code=your_code_string,
    logs="ZeroDivisionError on line 12"
)
print(result["final_answer"])
```

***

## Bug Patterns Detected

| Pattern | Method |
|---|---|
| `=+` instead of `+=` | AST `UnaryOp(UAdd)` — deterministic |
| Stale mutable globals | Module-level `dict`/`list`/`defaultdict`/`int=0` — deterministic |
| Division without zero-check | AST `BinOp(Div)` — deterministic |
| `max()`/`min()` on empty container | AST `Call` pattern — deterministic |
| Date string `>=` comparison | AST `Compare` + `strftime` — deterministic |
| Call-chain division (e.g. `f(x, x-10)`) | Logs + LLM — semantic |
| Wrong dict key / logic bugs | Logs + LLM — semantic |
| Missing return for int helpers | LLM critique pass — semantic |

***

## Fix Principles

The LLM is guided by four generic reasoning principles rather than hard-coded rules:

1. **Safe fallback must be semantically correct** — `a / b if b != 0 else 0`, never `else 1`
2. **Container guards use `if container` checks** — not non-existent keyword arguments like `default=None`
3. **Int counters passed by value need return + reassign** — `count = helper(..., count)` where helper returns the updated value
4. **All mutable globals move inside entry function** — passed as explicit parameters to every helper that uses them

***

## Known Limitations

- AST pre-detection is Python-only. Other languages rely entirely on the LLM pass.
- Pure logic bugs (wrong dict key, wrong variable name) outside the checklist may be missed by the 7B model.
- Call-chain division tracing requires runtime logs pointing to the crash location.
- The model may occasionally report false positives on date comparisons where formats already match.

***

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Qwen 2.5 Coder 7B (via Ollama) |
| Backend | FastAPI + Python 3.10+ |
| Static Analysis | Python `ast` module |
| RAG | FAISS / ChromaDB vector store |
| Frontend | React + Vite |
| API | REST (JSON) |