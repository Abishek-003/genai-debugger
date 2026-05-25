# FastAPI — Common Errors and Fixes

---

## HTTP 422 Unprocessable Entity

Cause: Request body does not match the Pydantic model — missing required field, wrong type, or malformed JSON.
Fix:
```python
# Model
class QueryRequest(BaseModel):
    query: str
    code: str
    logs: str = ""   # make optional with default to avoid 422 when omitted

# Bad request body (missing 'code') → 422
{"query": "fix this"}

# Good request body
{"query": "fix this", "code": "x =+ 1"}
```

---

## HTTP 500 from unhandled exception in route

Cause: Exception raised inside the route handler is not caught — FastAPI returns 500 with no detail.
Fix:
```python
@router.post("/query")
async def process_query(req: QueryRequest):
    try:
        result = await asyncio.to_thread(run_pipeline, req.query, req.code, req.logs)
        return QueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error. Check logs.")
```

---

## Error: `RuntimeError: no running event loop` when calling async from sync

Cause: Calling `asyncio.get_event_loop().run_until_complete()` inside a FastAPI async route.
Fix: Use `asyncio.to_thread()` for sync blocking calls, or `await` for async ones. Never call `run_until_complete` inside an async context.
```python
# Bad
result = asyncio.get_event_loop().run_until_complete(some_async_fn())

# Good
result = await some_async_fn()
# Or for blocking sync code:
result = await asyncio.to_thread(blocking_sync_fn, arg1, arg2)
```

---

## Error: CORS — Request blocked by browser

Cause: `allow_origins` does not include the frontend origin, or `allow_credentials=True` with `allow_origins=["*"]`.
Fix:
```python
# Bad — wildcard + credentials is forbidden by the CORS spec
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)

# Good — explicit origins with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Error: `AttributeError: 'dict' object has no attribute 'query'`

Cause: FastAPI route expects a Pydantic model but receives a raw dict (common when calling from test code).
Fix:
```python
# Bad — passing dict directly
result = process_query({"query": "...", "code": "..."})

# Good — instantiate the model
result = process_query(QueryRequest(query="...", code="..."))
# Or in tests use the test client
response = client.post("/api/query", json={"query": "...", "code": "..."})
```

---

## Error: Response model validation fails — `KeyError` or missing field

Cause: `run_pipeline()` returns a dict that's missing one of the keys declared in the response model.
Fix:
```python
# Guard before constructing response
required_keys = {"initial_answer", "critique", "final_answer"}
if not required_keys.issubset(result.keys()):
    raise ValueError(f"Pipeline returned incomplete result: {result.keys()}")
return QueryResponse(**result)
```

---

## Error: GZip middleware compresses tiny responses — overhead with no benefit

Cause: `GZipMiddleware` default minimum_size is 500 bytes — compressing small JSON adds CPU with no transfer savings.
Fix:
```python
# Good — only compress responses larger than 1KB
app.add_middleware(GZipMiddleware, minimum_size=1024)
```

---

## Error: Route not found (404) after adding router with prefix

Cause: Router prefix is `/api` but the test/client calls `/query` without the prefix.
Fix:
```python
# Router defined with prefix
router = APIRouter(prefix="/api", tags=["Query"])

@router.post("/query")   # → full path is /api/query

# Bad call
response = client.post("/query", json=payload)

# Good call
response = client.post("/api/query", json=payload)
```

---

## Error: `requests` blocking the event loop in async route

Cause: `requests` is a synchronous library — calling it directly inside an `async def` route blocks the entire event loop.
Fix:
```python
# Bad — blocks event loop
@router.post("/query")
async def process(req: QueryRequest):
    resp = requests.post(OLLAMA_URL, json={...})   # blocks!

# Good — run in thread pool
@router.post("/query")
async def process(req: QueryRequest):
    resp = await asyncio.to_thread(requests.post, OLLAMA_URL, json={...})
```

---

## Error: Lifespan startup fails — RAG index not found

Cause: `from rag.vector_store import index` triggers `build_index()` which tries to fetch URLs — fails if no internet at startup.
Fix:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from rag.vector_store import index, documents
        logger.info(f"RAG index loaded: {len(documents)} chunks")
    except Exception as e:
        logger.warning(f"RAG index load failed: {e} — continuing without RAG")
    yield
```

---

## Error: `/docs` returns 404 in production

Cause: `docs_url` was set to `None` or the app is mounted under a sub-path without updating the root path.
Fix:
```python
# If running behind a proxy at /api
app = FastAPI(docs_url="/docs", root_path="/api")
# Or keep docs_url="/docs" and access at http://host/api/docs
```

---

## Error: Background task still runs after response — modifies response object

Cause: `BackgroundTasks` run after the response is sent — any attempt to modify the response inside a background task has no effect.
Fix: Use background tasks only for side effects (logging, cleanup, notifications) — never for computing the response.

---

## Error: Middleware order — CORS headers missing on error responses

Cause: A middleware added after `CORSMiddleware` raises an exception before CORS headers are attached.
Fix: Always add `CORSMiddleware` first (outermost):
```python
app.add_middleware(CORSMiddleware, ...)   # first = outermost = runs first on request, last on response
app.add_middleware(GZipMiddleware, ...)   # second
```
