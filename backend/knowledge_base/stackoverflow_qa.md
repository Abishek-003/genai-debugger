# Stack Overflow Top Questions — Python Bug Patterns

---

## ZeroDivisionError

**Q: Why do I get ZeroDivisionError even though I check for zero?**
Cause: The check happens before the denominator is computed, not at the point of division.
Fix:
```python
# Bad
if denom:
    result = compute(a) / compute(b)  # compute(b) can still return 0

# Good
divisor = compute(b)
result = compute(a) / divisor if divisor != 0 else 0
```

---

## KeyError on dict access

**Q: Why does my dict access raise KeyError when the key looks correct?**
Cause: Key does not exist; using `dict[key]` instead of `dict.get(key)`.
Fix:
```python
# Bad
value = data["score"]

# Good
value = data.get("score", 0)
# Or guard explicitly
if "score" in data:
    value = data["score"]
```

---

## =+ instead of +=

**Q: My counter resets to the value every call instead of accumulating — why?**
Cause: `=+` is parsed as `= (+value)` — it assigns, not increments.
Fix:
```python
# Bad
count =+ 1   # assigns +1 every call

# Good
count += 1   # increments
```

---

## Mutable default argument

**Q: Why does my list default argument persist between function calls?**
Cause: Mutable defaults are created once at function definition, shared across all calls.
Fix:
```python
# Bad
def append_item(item, lst=[]):
    lst.append(item)
    return lst

# Good
def append_item(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

---

## max() / min() on empty sequence

**Q: Why does max() raise ValueError on an empty list?**
Cause: Built-in max()/min() raises ValueError when the iterable is empty and no default is given.
Fix:
```python
# Bad
best = max(results, key=lambda x: x["score"])

# Good
best = max(results, key=lambda x: x["score"]) if results else None
# Or use the default keyword (Python 3.4+)
best = max(results, key=lambda x: x["score"], default=None)
```
Note: `default=` works for `max(iterable)` form but NOT for `max(iterable, key=...)` in older Python — always prefer the `if container else` guard for safety.

---

## Stale module-level mutable state

**Q: My function returns wrong results on the second call — state from first call leaks.**
Cause: Mutable objects (dict, list, set) declared at module level are shared across all calls.
Fix:
```python
# Bad
cache = {}
totals = defaultdict(int)

def process(items):
    for item in items:
        cache[item["id"]] = item
        totals[item["tag"]] += item["score"]

# Good
def process(items):
    cache = {}
    totals = defaultdict(int)
    for item in items:
        cache[item["id"]] = item
        totals[item["tag"]] += item["score"]
    return cache, totals
```

---

## TypeError: NoneType is not subscriptable

**Q: I get `TypeError: 'NoneType' object is not subscriptable` — what causes this?**
Cause: A function returns None (missing return or early return) and the caller indexes its result.
Fix:
```python
# Bad
def find_user(uid):
    for u in users:
        if u["id"] == uid:
            return u
    # falls off end → returns None implicitly

name = find_user(42)["name"]  # crashes if not found

# Good
def find_user(uid):
    for u in users:
        if u["id"] == uid:
            return u
    return {}   # or raise, or return None and guard at call site

user = find_user(42)
name = user["name"] if user else "unknown"
```

---

## String date comparison (lexicographic bug)

**Q: My date comparison gives wrong results for DD-MM-YYYY strings.**
Cause: String comparison is lexicographic — "05-03-2026" < "20-01-2026" is False but should be True.
Fix:
```python
# Bad
if record["joined"] >= cutoff.strftime("%d-%m-%Y"):

# Good
import datetime
if datetime.datetime.strptime(record["joined"], "%d-%m-%Y") >= cutoff:
```

---

## Silent exception swallowing

**Q: My code fails silently — no error, but wrong output. How do I debug?**
Cause: `except: pass` or `except Exception: pass` hides all errors.
Fix:
```python
# Bad
try:
    result = compute(data)
except Exception:
    pass

# Good
try:
    result = compute(data)
except Exception as exc:
    logger.error("compute() failed: %s", exc)
    raise
```

---

## int passed to helper doesn't update in caller

**Q: I pass a counter to a helper function and increment it there, but the caller still sees 0.**
Cause: Integers are immutable in Python — the helper gets a copy, changes don't propagate.
Fix:
```python
# Bad
def increment(count):
    count += 1  # only modifies local copy

count = 0
increment(count)
print(count)  # still 0

# Good
def increment(count):
    return count + 1

count = 0
count = increment(count)
print(count)  # 1
```

---

## IndexError on list access

**Q: Why do I get IndexError even though I check `len(lst) > 0`?**
Cause: Checking length once is not safe if the index is computed dynamically or off-by-one.
Fix:
```python
# Bad
if len(lst) > 0:
    return lst[n]  # n might still be >= len(lst)

# Good
if 0 <= n < len(lst):
    return lst[n]
return None
```

---

## requests.get() missing timeout

**Q: My requests call hangs forever in production.**
Cause: `requests.get()` has no default timeout — it blocks indefinitely on slow/unresponsive servers.
Fix:
```python
# Bad
response = requests.get(url)

# Good
response = requests.get(url, timeout=10)
```

---

## Modifying a list while iterating over it

**Q: Items are skipped when I remove from a list during iteration.**
Cause: Removing elements shifts indices mid-loop, causing the iterator to skip items.
Fix:
```python
# Bad
for item in items:
    if item["score"] < 0:
        items.remove(item)

# Good
items = [item for item in items if item["score"] >= 0]
```
