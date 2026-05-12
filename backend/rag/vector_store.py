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