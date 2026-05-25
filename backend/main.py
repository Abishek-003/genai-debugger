import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from routes.query import router as query_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Ollama Backend...")

    try:
        from rag.vector_store import get_vectorstore

        vectorstore = get_vectorstore()
        app.state.vectorstore = vectorstore
        logger.info("RAG vectorstore loaded successfully")
    except Exception:
        logger.exception("Failed to initialize RAG vectorstore during startup")
        raise

    yield

    logger.info("Shutting down Ollama Backend...")


app = FastAPI(
    title="Ollama Debug Assistant",
    description="RAG-powered code debugging API using local Ollama LLMs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(query_router)


@app.get("/", tags=["Health"])
async def home():
    return {"status": "ok", "message": "Ollama Backend Running"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}