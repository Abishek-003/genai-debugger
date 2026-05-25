# Asyncio — Common Errors and Fixes

---

## Error: `RuntimeError: This event loop is already running`

Cause: Calling `asyncio.run()` or `loop.run_until_complete()` inside an already-running async context (e.g. inside a FastAPI route or Jupyter).
Fix:
```python
# Bad — inside async context
asyncio.run(some_coroutine())

# Good — just await it
await some_coroutine()

# Good — for sync blocking code inside async route
result = await asyncio.to_thread(sync_blocking_fn, arg)
```

---

## Error: `RuntimeError: no running event loop`

Cause: Calling `asyncio.get_event_loop()` from a new thread or after the loop has been closed.
Fix:
```python
# Bad
loop = asyncio.get_event_loop()
loop.run_until_complete(coro())

# Good — always create a fresh loop in new threads
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(coro())
finally:
    loop.close()
```

---

## Error: `requests` blocks event loop inside `async def`

Cause: `requests` is synchronous — calling it directly in an async function blocks the entire event loop, freezing all other coroutines.
Fix:
```python
# Bad
async def call_ollama(prompt):
    resp = requests.post(OLLAMA_URL, json={...})   # blocks!
    return resp.json()

# Good — run in a thread pool
async def call_ollama(prompt):
    resp = await asyncio.to_thread(requests.post, OLLAMA_URL, json={...})
    return resp.json()

# Best — use httpx for true async HTTP
import httpx
async def call_ollama(prompt):
    async with httpx.AsyncClient() as client:
        resp = await client.post(OLLAMA_URL, json={...}, timeout=180)
        return resp.json()
```

---

## Error: Coroutine never awaited — silently does nothing

Cause: Calling an `async def` function without `await` returns a coroutine object that is never executed.
Fix:
```python
# Bad — returns coroutine object, never runs
result = some_async_fn()

# Good
result = await some_async_fn()
```
Python 3.11+ will emit a `RuntimeWarning: coroutine was never awaited` warning for this.

---

## Error: `asyncio.to_thread` not available

Cause: `asyncio.to_thread()` was added in Python 3.9.
Fix for Python 3.8:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

async def run_in_thread(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, fn, *args)
```

---

## Error: Task exception was never retrieved

Cause: `asyncio.create_task()` was used but the task result/exception was never awaited or checked.
Fix:
```python
# Bad — exception silently lost
task = asyncio.create_task(some_coro())

# Good — always await or add a done callback
task = asyncio.create_task(some_coro())
try:
    result = await task
except Exception as e:
    logger.error("Task failed: %s", e)
```

---

## Error: Shared mutable state across coroutines causes race condition

Cause: Multiple coroutines modifying the same dict/list concurrently — `await` points are context-switch points.
Fix: Use `asyncio.Lock()` for shared state:
```python
lock = asyncio.Lock()
shared_cache = {}

async def update_cache(key, value):
    async with lock:
        shared_cache[key] = value
```

---

## Error: `TimeoutError` — async operation hangs forever

Cause: No timeout set on awaitable operations.
Fix:
```python
import asyncio

try:
    result = await asyncio.wait_for(some_coro(), timeout=30.0)
except asyncio.TimeoutError:
    logger.error("Operation timed out")
    result = None
```
