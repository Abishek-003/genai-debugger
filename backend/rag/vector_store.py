import os
import glob
import logging
from typing import Iterable

os.environ.setdefault("USER_AGENT", "genai-debugger/1.0")

from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


logger = logging.getLogger(__name__)

INDEX_PATH = "rag/faiss_index"
KB_FOLDER = "knowledge_base"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SOURCE_URLS = [
    "https://fastapi.tiangolo.com/tutorial/handling-errors/",
    "https://fastapi.tiangolo.com/tutorial/body/",
    "https://fastapi.tiangolo.com/tutorial/response-model/",
    "https://fastapi.tiangolo.com/tutorial/cors/",
    "https://fastapi.tiangolo.com/tutorial/middleware/",
    "https://docs.python.org/3/library/exceptions.html",
    "https://docs.pydantic.dev/latest/concepts/validators/",
    "https://docs.pydantic.dev/latest/concepts/fields/",
]

# Module-level singletons — initialized lazily
_embeddings: HuggingFaceEmbeddings | None = None
_vectorstore: FAISS | None = None

splitter = RecursiveCharacterTextSplitter(
    chunk_size=900,
    chunk_overlap=120,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
)


# ─── Lazy singletons ──────────────────────────────────────────────────────────


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def get_vectorstore() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = load_index()
    return _vectorstore


# ─── Text helpers ─────────────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _safe_preview(text: str, limit: int = 80) -> str:
    text = _normalize_text(text)
    return text[:limit] + ("..." if len(text) > limit else "")


# ─── Document loaders ─────────────────────────────────────────────────────────


def load_from_urls(urls: Iterable[str]) -> list[Document]:
    docs: list[Document] = []
    for url in urls:
        try:
            loader = WebBaseLoader(url)
            loaded = loader.load()
            for doc in loaded:
                doc.metadata = {
                    **doc.metadata,
                    "source_type": "web",
                    "source_url": url,
                }
            docs.extend(loaded)
            logger.info("Loaded %d document(s) from web: %s", len(loaded), url)
        except Exception as e:
            logger.warning("Web loading failed for %s: %s", url, e)
    return docs


def load_from_files(folder: str) -> list[Document]:
    docs: list[Document] = []
    patterns = ["**/*.md", "**/*.txt", "**/*.py"]

    for pattern in patterns:
        for path in glob.glob(os.path.join(folder, pattern), recursive=True):
            try:
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata = {
                        **doc.metadata,
                        "source_type": "file",
                        "file_path": path,
                        "file_name": os.path.basename(path),
                    }
                docs.extend(loaded)
                logger.info("Loaded file: %s", path)
            except Exception as e:
                logger.warning("Skipped %s: %s", path, e)
    return docs


def _fallback_documents() -> list[Document]:
    return [
        Document(
            page_content=(
                "FastAPI debugging patterns: 422 usually indicates request-body or "
                "Pydantic validation mismatch. 500 usually indicates server-side logic "
                "errors or response-model mismatch."
            ),
            metadata={"source_type": "fallback", "topic": "fastapi"},
        ),
        Document(
            page_content=(
                "Python debugging patterns: ZeroDivisionError comes from division, "
                "floor division, or modulo by zero; KeyError comes from missing dict keys; "
                "silent except blocks hide root causes."
            ),
            metadata={"source_type": "fallback", "topic": "python"},
        ),
        Document(
            page_content=(
                "Python mutable default arguments: def f(x, items=[]) shares items "
                "across all calls. Use None and initialize inside the function instead."
            ),
            metadata={"source_type": "fallback", "topic": "python"},
        ),
        Document(
            page_content=(
                "Python inconsistent returns: a function that returns a value on "
                "some paths and nothing on others will return None silently. "
                "Always make all return paths explicit."
            ),
            metadata={"source_type": "fallback", "topic": "python"},
        ),
    ]


def _prepare_documents(documents: list[Document]) -> list[Document]:
    prepared: list[Document] = []
    seen_content: set[str] = set()

    for doc in documents:
        text = _normalize_text(doc.page_content)
        if not text or len(text) < 40:
            continue
        if text in seen_content:
            continue
        seen_content.add(text)
        prepared.append(Document(page_content=text, metadata=doc.metadata))

    return prepared


# ─── Index management ─────────────────────────────────────────────────────────


def build_index(include_web: bool = False) -> FAISS:
    logger.info("Building RAG index...")
    os.makedirs(KB_FOLDER, exist_ok=True)
    os.makedirs(INDEX_PATH, exist_ok=True)

    all_docs: list[Document] = []

    local_docs = load_from_files(KB_FOLDER)
    all_docs.extend(local_docs)

    if include_web:
        web_docs = load_from_urls(SOURCE_URLS)
        all_docs.extend(web_docs)

    all_docs = _prepare_documents(all_docs)

    if not all_docs:
        logger.warning("No local/web docs found. Using fallback documents.")
        all_docs = _fallback_documents()

    chunks = splitter.split_documents(all_docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata = {
            **chunk.metadata,
            "chunk_id": i,
            "chunk_total": len(chunks),
            "preview": _safe_preview(chunk.page_content),
        }

    logger.info("Split into %d chunks", len(chunks))

    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(INDEX_PATH)
    logger.info("Index saved at %s with %d chunks", INDEX_PATH, len(chunks))
    return vectorstore


def load_index() -> FAISS:
    """
    Load existing FAISS index if available, otherwise build a new one.
    allow_dangerous_deserialization is required by LangChain's pickle-based FAISS
    loader. Only enable this when loading from a trusted, locally generated index.
    """
    index_file = os.path.join(INDEX_PATH, "index.faiss")
    pkl_file = os.path.join(INDEX_PATH, "index.pkl")

    if os.path.exists(index_file) and os.path.exists(pkl_file):
        logger.info("Loading existing FAISS index from %s", INDEX_PATH)
        return FAISS.load_local(
            INDEX_PATH,
            get_embeddings(),
            allow_dangerous_deserialization=True,  # safe: locally generated index only
        )

    logger.info("No existing index found. Building a new one.")
    return build_index(include_web=False)


def rebuild_index(include_web: bool = False) -> FAISS:
    global _vectorstore
    _vectorstore = build_index(include_web=include_web)
    return _vectorstore


# ─── Query builder ────────────────────────────────────────────────────────────


def _extract_keywords(text: str) -> list[str]:
    raw = (text or "").lower()
    tokens = []
    for token in raw.replace("\n", " ").split():
        token = token.strip(".,:;()[]{}<>\"'`")
        if len(token) < 3:
            continue
        tokens.append(token)

    interesting = {
        "zerodivisionerror", "keyerror", "indexerror", "typeerror", "valueerror",
        "attributeerror", "httpexception", "validationerror", "timeout",
        "fastapi", "pydantic", "langchain", "faiss", "ollama", "requests",
        "asyncio", "cors", "middleware", "responsemodel", "response_model",
        "json", "traceback", "exception", "nameerror", "runtimeerror",
        "importerror", "oserror", "filenotfounderror", "recursionerror",
    }

    keep = []
    for token in tokens:
        if token in interesting or "error" in token or "exception" in token:
            keep.append(token)

    seen: set[str] = set()
    ordered = []
    for token in keep:
        if token not in seen:
            seen.add(token)
            ordered.append(token)

    return ordered[:15]


def build_retrieval_query(query: str, code: str = "", logs: str = "") -> str:
    parts = []

    if query and query.strip():
        parts.append(query.strip())

    code_signals = _extract_keywords(code)
    log_signals = _extract_keywords(logs)

    if code_signals:
        parts.append("code signals: " + " ".join(code_signals))

    if log_signals:
        parts.append("log signals: " + " ".join(log_signals))

    combined = " | ".join(parts).strip()
    return combined or "python bug debugging"


# ─── Retrieval ────────────────────────────────────────────────────────────────


def retrieve(
    query: str,
    code: str = "",
    logs: str = "",
    k: int = 6,
    min_score: float = 0.20,
    fallback_k: int = 3,
) -> list[str]:
    """
    Retrieve relevant context chunks for a debugging query.

    Returns a list of plain-text chunks for use in prompts.
    Score thresholding is heuristic: FAISS relevance scores can vary depending
    on the distance metric and LangChain version. The fallback ensures at
    least fallback_k results are always returned.
    """
    retrieval_query = build_retrieval_query(query, code, logs)

    try:
        results = get_vectorstore().similarity_search_with_relevance_scores(
            retrieval_query,
            k=k,
        )
    except Exception as e:
        logger.exception("Vector search failed: %s", e)
        return []

    filtered: list[str] = []
    seen: set[str] = set()

    # Dedup key: preview of content + source, to avoid near-duplicate chunks
    seen_keys: set[str] = set()

    for doc, score in results:
        text = _normalize_text(doc.page_content)
        if not text:
            continue
        if score < min_score:
            continue

        # Dedup by normalized text content
        if text in seen:
            continue

        # Also dedup by source + preview to catch paraphrased duplicates
        source = doc.metadata.get("source_url") or doc.metadata.get("file_path") or ""
        preview = _safe_preview(text, limit=60)
        dedup_key = f"{source}|{preview}"
        if dedup_key in seen_keys:
            continue

        seen.add(text)
        seen_keys.add(dedup_key)
        filtered.append(text)

    # Fallback: if nothing passed threshold, return top results regardless of score
    if not filtered:
        logger.info(
            "No chunks passed threshold %.2f for query: %s. Falling back to top %d results.",
            min_score,
            _safe_preview(retrieval_query, 120),
            fallback_k,
        )
        for doc, _score in results[:fallback_k]:
            text = _normalize_text(doc.page_content)
            if text and text not in seen:
                seen.add(text)
                filtered.append(text)

    logger.info(
        "Retrieved %d/%d chunks for query: %s",
        len(filtered),
        k,
        _safe_preview(retrieval_query, 120),
    )
    return filtered