# LangChain & RAG — Common Errors and Fixes

---

## Error: `ValueError: Expected EmbeddingsType, got <class 'NoneType'>`

Cause: The embedding model returned None — usually because the input text was empty or the model failed silently.
Fix:
```python
# Guard before embedding
texts = [t for t in texts if t and t.strip()]
if not texts:
    return []
vectorstore = FAISS.from_texts(texts, embeddings)
```

---

## Error: FAISS `allow_dangerous_deserialization` warning / crash

Cause: Loading a FAISS index saved by a different version without the safety flag.
Fix:
```python
# Bad
vectorstore = FAISS.load_local(path, embeddings)

# Good
vectorstore = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
```
Note: Only use this flag on indexes you generated yourself.

---

## Error: `IndexError: list index out of range` on `results[0]`

Cause: `similarity_search()` returned an empty list — query had no matches above the threshold.
Fix:
```python
results = vectorstore.similarity_search(query, k=3)
if not results:
    return "No relevant context found."
return results[0].page_content
```

---

## Error: Retrieved chunks are irrelevant / low quality

Cause: Chunk size too large (500+ tokens) loses precision; chunk overlap too small loses context across boundaries.
Fix:
```python
# Better defaults for code/technical docs
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)
```

---

## Error: `similarity_search_with_relevance_scores` returns wrong scores

Cause: FAISS returns L2 distances by default — lower is better, but `with_relevance_scores` normalizes to [0,1] where higher is better. Threshold direction gets confused.
Fix:
```python
results = vectorstore.similarity_search_with_relevance_scores(query, k=k)
# Score is 0-1 where 1 = most similar — filter > threshold, not < threshold
filtered = [doc.page_content for doc, score in results if score > threshold]
```

---

## Error: RAG index is stale after adding new documents

Cause: `FAISS.save_local()` was not called after `add_documents()` — in-memory index updated but disk index not.
Fix:
```python
vectorstore.add_documents(new_docs)
vectorstore.save_local(INDEX_PATH)  # must persist manually
```

---

## Error: `HuggingFaceEmbeddings` slow on first call

Cause: Model downloads on first use and loads into memory on every process restart.
Fix: Pre-load at app startup in the lifespan handler, not inside the request handler:
```python
@asynccontextmanager
async def lifespan(app):
    from rag.vector_store import index  # triggers load once
    yield
```

---

## Error: WebBaseLoader returns empty documents

Cause: The target page uses JavaScript rendering — `WebBaseLoader` is a plain HTTP fetcher and cannot execute JS.
Fix: Use static pages only, or switch to `AsyncHtmlLoader` + `Html2TextTransformer`, or scrape to a local `.md` file first.

---

## Error: `RecursiveCharacterTextSplitter` splits mid-sentence in code

Cause: Default separators split on whitespace, breaking code blocks.
Fix:
```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=60,
    separators=["\n```\n", "\n\n", "\n", " "]  # respect code fences
)
```

---

## Error: Retrieval returns the same chunk repeatedly

Cause: Only one document in the store, or all documents are near-duplicates (e.g. same page scraped multiple times).
Fix:
```python
# Deduplicate documents before indexing
seen = set()
unique_docs = []
for doc in all_docs:
    h = hash(doc.page_content[:200])
    if h not in seen:
        seen.add(h)
        unique_docs.append(doc)
vectorstore = FAISS.from_documents(unique_docs, embeddings)
```

---

## Error: `TypeError: TextLoader.__init__() got unexpected keyword argument 'encoding'`

Cause: Older version of `langchain-community` does not support the `encoding` kwarg on `TextLoader`.
Fix:
```python
# Bad (old versions)
loader = TextLoader(path, encoding="utf-8")

# Good — open manually
from langchain.schema import Document
with open(path, encoding="utf-8") as f:
    docs = [Document(page_content=f.read(), metadata={"source": path})]
```

---

## Error: FAISS index not found on startup after Docker rebuild

Cause: Index saved inside the container filesystem — wiped on rebuild.
Fix: Mount the index path as a Docker volume:
```yaml
volumes:
  - ./rag/faiss_index:/app/rag/faiss_index
```

---

## Best Practice: Query with code, not the user question

Querying the vector store with the user's natural language question retrieves topic matches, not bug-pattern matches. Query with the actual code snippet for better results:
```python
# Bad
results = retrieve(query)          # "why does this crash" → vague

# Good
results = retrieve(code[:500])     # actual code → matches error patterns
```
