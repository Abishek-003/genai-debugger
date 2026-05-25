# Python Errors — Bug Patterns and Fixes

---

## ZeroDivisionError

Cause: Dividing by zero — denominator is 0 or becomes 0 through computation.
```python
# Bad
avg = total / count

# Good
avg = total / count if count != 0 else 0
```
Common trap — denominator computed from user input:
```python
# Bad
def score(a, b):
    return a / (b - 10)   # ZeroDivisionError when b == 10

# Good
def score(a, b):
    denom = b - 10
    return a / denom if denom != 0 else 0
```

---

## TypeError: unsupported operand type(s)

Cause: Operation applied to incompatible types — e.g., adding str and int.
```python
# Bad
result = user_input + 5    # user_input is a string from input()

# Good
result = int(user_input) + 5
```

---

## AttributeError: 'NoneType' object has no attribute '...'

Cause: A function returned None (missing return, early exit, or failed lookup) and the caller accesses an attribute.
```python
# Bad
def get_user(uid):
    for u in users:
        if u["id"] == uid:
            return u
    # implicit return None

user = get_user(42)
print(user["name"])   # AttributeError if not found

# Good
user = get_user(42)
if user is not None:
    print(user["name"])
```

---

## NameError: name '...' is not defined

Cause: Variable used before assignment, or typo in variable name.
```python
# Bad
def process():
    if condition:
        result = compute()
    return result   # NameError if condition was False

# Good
def process():
    result = None   # initialize before conditional
    if condition:
        result = compute()
    return result
```

---

## KeyError on dict access

Cause: Key does not exist in the dictionary.
```python
# Bad
value = data["score"]

# Good — use .get() with a default
value = data.get("score", 0)

# Or guard explicitly
if "score" in data:
    value = data["score"]
```

---

## IndexError: list index out of range

Cause: Accessing index >= len(list), or negative index beyond the start.
```python
# Bad
first = items[0]   # IndexError if items is empty

# Good
first = items[0] if items else None
```

---

## StopIteration raised from generator inside try/except

Cause: In Python 3.7+, `StopIteration` raised inside a generator is converted to `RuntimeError`.
```python
# Bad — StopIteration inside generator becomes RuntimeError
def gen():
    try:
        yield next(some_iterator)
    except SomeError:
        pass

# Good — use explicit check
def gen():
    item = next(some_iterator, None)
    if item is not None:
        yield item
```

---

## RecursionError: maximum recursion depth exceeded

Cause: Infinite or very deep recursion — missing base case or wrong termination condition.
```python
# Bad — missing base case
def factorial(n):
    return n * factorial(n - 1)

# Good
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

---

## =+ instead of +=

Cause: `=+` is parsed as `= (+value)` — assigns positive value, does not accumulate.
```python
# Bad
total =+ score   # assigns +score every iteration

# Good
total += score   # accumulates
```

---

## Mutable default argument

Cause: Default mutable object is shared across all calls.
```python
# Bad
def append(item, lst=[]):
    lst.append(item)
    return lst

# Good
def append(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

---

## Modifying list while iterating

Cause: Removing items shifts indices, causing items to be skipped.
```python
# Bad
for item in items:
    if item < 0:
        items.remove(item)

# Good
items = [item for item in items if item >= 0]
```

---

## Comparing with `is` instead of `==`

Cause: `is` checks identity (same object in memory), not equality.
```python
# Bad
if result is "ok":   # may fail even for equal strings (implementation-defined)

# Good
if result == "ok":
```
Exception: `is None` and `is not None` are correct and preferred.

---

## Integer immutability — counter not updated in caller

Cause: Integers are immutable — modifying inside a function doesn't affect the caller's variable.
```python
# Bad
def increment(count):
    count += 1   # only modifies local copy

count = 0
increment(count)
print(count)   # 0 — unchanged

# Good
def increment(count):
    return count + 1

count = 0
count = increment(count)
print(count)   # 1
```

---

## Stale module-level mutable state

Cause: Dict/list/set at module level is shared and accumulates state across calls.
```python
# Bad — bleeds state between requests
cache = {}
results = []

def run(data):
    for item in data:
        cache[item["id"]] = item
        results.append(item["score"])

# Good — fresh state per call
def run(data):
    cache = {}
    results = []
    for item in data:
        cache[item["id"]] = item
        results.append(item["score"])
    return cache, results
```

---

## String date comparison — lexicographic error

Cause: Comparing date strings lexicographically gives wrong order for non-ISO formats.
```python
# Bad — "05-03-2026" > "20-01-2026" is False (wrong)
if record["date"] >= cutoff.strftime("%d-%m-%Y"):

# Good — parse first
import datetime
if datetime.datetime.strptime(record["date"], "%d-%m-%Y") >= cutoff:
```
ISO format (YYYY-MM-DD) compares correctly as strings; DD-MM-YYYY does not.

---

## Silent exception swallowing

Cause: `except: pass` hides all errors — bugs become invisible.
```python
# Bad
try:
    result = process(data)
except Exception:
    pass

# Good
try:
    result = process(data)
except Exception as exc:
    logger.error("process() failed: %s", exc)
    raise
```

---

## max() / min() on empty iterable

Cause: `max([])` raises `ValueError: max() arg is an empty sequence`.
```python
# Bad
best = max(scores)

# Good
best = max(scores) if scores else None
# Or use default= keyword (only available in Python 3.4+ for max(iterable))
best = max(scores, default=None)
```

---

## requests.get without timeout

Cause: Hangs indefinitely on unresponsive server.
```python
# Bad
resp = requests.get(url)

# Good
resp = requests.get(url, timeout=10)
```

---

## Inconsistent return types

Cause: Function returns a value on some paths and nothing (None) on others.
```python
# Bad
def compute(x):
    if x > 0:
        return x * 2
    # implicit return None when x <= 0

# Good
def compute(x):
    if x > 0:
        return x * 2
    return 0   # explicit and consistent
```

---

## f-string expression with side effects

Cause: Calling a function with side effects inside an f-string makes debugging confusing.
```python
# Bad
logger.info(f"Result: {process_and_save(data)}")  # side effect hidden in log line

# Good
result = process_and_save(data)
logger.info(f"Result: {result}")
```

---

## Catching too broad an exception class

Cause: `except Exception` catches everything including `KeyboardInterrupt` subclasses and programming errors.
```python
# Bad
except Exception:
    pass

# Good — catch only what you expect
except (ValueError, KeyError) as exc:
    logger.warning("Expected error: %s", exc)
```
