# Your Codebase — Auto-scanned

## File: main.py
```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routes.query import router as query_router

# Configure logging once at entry point
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ─── Lifespan: startup + shutdown logic ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Ollama Backend...")
    # Pre-load the RAG index here so first request isn't slow
    from rag.vector_store import index, documents
    logger.info(f"✅ RAG index loaded — {len(documents)} chunks ready")
    yield
    # Shutdown
    logger.info("🛑 Shutting down Ollama Backend...")


# ─── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Ollama Debug Assistant",
    description="RAG-powered code debugging API using local Ollama LLMs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ─── Middleware (order matters — CORS must be first) ───────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


# ─── Routes ────────────────────────────────────────────────────────────────────
app.include_router(query_router)


# ─── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def home():
    return {"status": "ok", "message": "Ollama Backend Running 🚀"}
```

## File: routes\query.py
```python
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from models.request import QueryRequest
from services.llm_service import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Query"])


# 🔹 Response model — documents what the endpoint returns
class QueryResponse(BaseModel):
    initial_answer: str
    critique: str
    final_answer: str


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Debug code using the LLM pipeline",
    status_code=200
)
async def process_query(req: QueryRequest):
    try:
        result = await asyncio.to_thread(run_pipeline, req.query, req.code, req.logs)
        
        # Guard: ensure all expected keys are present
        if not all(k in result for k in ("initial_answer", "critique", "final_answer")):
            raise ValueError(f"Pipeline returned incomplete result: {result.keys()}")
        
        return QueryResponse(**result)

    except ValueError as e:
        logger.error(f"Pipeline value error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error in /query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error. Check logs.")
```

## File: services\llm_service.py
```python
import requests
from rag.vector_store import retrieve
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"


# 🔹 Base call to Ollama
def call_ollama(prompt: str):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json()["response"]
    except Exception as e:
        return f"Error calling Ollama: {str(e)}"


# 🔥 1. GENERATOR
def generate_answer(query, code, logs):
    context = retrieve(query)

    prompt = f"""
You are a senior software engineer.

Use the following context if relevant:
{context}

Query:
{query}

Code:
{code}

Logs:
{logs}

Give:
- Issue
- Explanation
- Fix
"""

    return call_ollama(prompt)


# 🔥 2. CRITIC (STRONGER)
def critique_answer(query, code, logs, answer):
    prompt = f"""
You are a strict code reviewer.

Check the answer carefully.

Rules:
- Detect incorrect logic
- Detect unnecessary complexity
- Detect invalid code syntax
- Be VERY strict

Output format:
- Correct? (YES/NO)
- Errors found:
- What should be fixed:

Query:
{query}

Code:
{code}

Answer:
{answer}
"""
    return call_ollama(prompt)


# 🔥 3. REFINER (CONTROLLED)
def refine_answer(query, code, logs, answer, critique):
    prompt = f"""
You are a senior engineer fixing an answer.

Rules:
- ONLY correct mistakes
- DO NOT add new unrelated examples
- Ensure code is syntactically valid
- Keep answer short and precise

Query:
{query}

Code:
{code}

Initial Answer:
{answer}

Critique:
{critique}

Give FINAL correct answer only.
"""
    return call_ollama(prompt)


# 🔥 SAFETY CHECK
def is_bad_response(text):
    text = text.lower()
    return any(word in text for word in [
        "fibonacci", "random example", "irrelevant"
    ])


# 🚀 FINAL PIPELINE
def run_pipeline(query, code, logs):
    initial = generate_answer(query, code, logs)
    critique = critique_answer(query, code, logs, initial)

    if "INCORRECT" in critique:
        final = refine_answer(query, code, logs, initial, critique)
    else:
        final = initial

    return {
        "initial_answer": initial,
        "critique": critique,
        "final_answer": final
    }
```

## File: rag\vector_store.py
```python
import os
import glob
import logging

os.environ.setdefault("USER_AGENT", "genai-debugger/1.0")

from langchain_community.document_loaders import WebBaseLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

INDEX_PATH      = "rag/faiss_index"
KB_FOLDER       = "knowledge_base/"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SOURCE_URLS = [
    "https://fastapi.tiangolo.com/tutorial/handling-errors/",
    "https://fastapi.tiangolo.com/tutorial/body/",
    "https://fastapi.tiangolo.com/tutorial/response-model/",
    "https://docs.python.org/3/library/exceptions.html",
]

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", ".", " "]
)

def load_from_urls(urls):
    try:
        loader = WebBaseLoader(urls)
        docs = loader.load()
        logger.info(f"Loaded {len(docs)} pages from web")
        return docs
    except Exception as e:
        logger.warning(f"Web loading failed: {e}")
        return []

def load_from_files(folder):
    docs = []
    for path in glob.glob(os.path.join(folder, "**/*.md"), recursive=True):
        try:
            loader = TextLoader(path, encoding="utf-8")
            docs.extend(loader.load())
            logger.info(f"Loaded file: {path}")
        except Exception as e:
            logger.warning(f"Skipped {path}: {e}")
    return docs

def build_index():
    logger.info("Building RAG index...")
    all_docs = []
    all_docs.extend(load_from_urls(SOURCE_URLS))
    os.makedirs(KB_FOLDER, exist_ok=True)
    all_docs.extend(load_from_files(KB_FOLDER))

    if not all_docs:
        from langchain.schema import Document
        all_docs = [Document(page_content="FastAPI is a modern Python web framework.")]

    chunks = splitter.split_documents(all_docs)
    logger.info(f"Split into {len(chunks)} chunks")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(INDEX_PATH, exist_ok=True)
    vectorstore.save_local(INDEX_PATH)
    logger.info(f"Index saved — {len(chunks)} chunks")
    return vectorstore

def load_index():
    if os.path.exists(os.path.join(INDEX_PATH, "index.faiss")):
        logger.info(f"Loading existing FAISS index from {INDEX_PATH}")
        return FAISS.load_local(
            INDEX_PATH, embeddings,
            allow_dangerous_deserialization=True
        )
    return build_index()

vectorstore = load_index()

def retrieve(query: str, k: int = 3, threshold: float = 0.25) -> list[str]:
    results = vectorstore.similarity_search_with_relevance_scores(query, k=k)
    filtered = [doc.page_content for doc, score in results if score >= threshold]
    logger.info(f"Retrieved {len(filtered)}/{k} chunks for: '{query[:60]}'")
    return filtered
```

## File: models\request.py
```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    code: str = ""
    logs: str = ""
```

