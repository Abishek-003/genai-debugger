import ast
import time
import textwrap
import requests
from rag.vector_store import retrieve


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b-instruct"


# ─── Ollama caller ─────────────────────────────────────────────────────────────

def call_ollama(prompt: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0,
                    "options": {"num_predict": 1024}
                },
                timeout=180
            )
            response.raise_for_status()
            result = response.json().get("response", "")
            if not result.strip():
                raise ValueError("Empty response from model")
            result = (
                result
                .replace("<|begin▁of▁sentence|>", "")
                .replace("<|end▁of▁sentence|>", "")
                .strip()
            )
            return result
        except (KeyError, ValueError, requests.RequestException) as e:
            if attempt == retries:
                return f"Error after {retries + 1} attempts: {str(e)}"
            time.sleep(2)


# ─── Off-topic guard ───────────────────────────────────────────────────────────

def is_off_topic(query: str, code: str) -> bool:
    if code and code.strip():
        return False
    off_topic_signals = [
        "hello", "hi ", "hey ", "how are you", "what is your name",
        "who are you", "good morning", "good evening",
        "what is the capital", "tell me about", "explain quantum",
        "write a poem", "write an essay", "write a story",
        "what is love", "recommend a movie", "recommend a book",
        "weather today", "stock price",
        "write a function", "write code for", "implement a",
        "create a script", "generate code",
        "recipe for", "how to cook", "best restaurant",
    ]
    return any(s in query.lower() for s in off_topic_signals)


# ─── AST Pre-Detector ─────────────────────────────────────────────────────────

def ast_detect_bugs(source: str) -> list:
    """
    Deterministically find bug patterns:
    - =+ instead of +=   (UnaryOp UAdd assignment)
    - Bare division       (flags for LLM to trace call-chain)
    - max()/min() no guard
    - Mutable module-level globals
    - Date string >= comparison
    """
    bugs = []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as e:
        return [{"line": 0, "code": str(e), "type": "SyntaxError — fix before analysis"}]

    lines = source.splitlines()

    def get_line(node):
        return lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""

    # ── Pass 1: collect module-level mutable names ─────────────────────────────
    mutable_globals = []
    MUTABLE_BUILTINS = {"dict", "list", "defaultdict", "set", "OrderedDict"}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if not isinstance(t, ast.Name):
                    continue
                v = node.value
                if isinstance(v, (ast.Dict, ast.List, ast.Set)):
                    mutable_globals.append((t.id, node.lineno))
                elif isinstance(v, ast.Constant) and v.value in (0, "", 0.0):
                    mutable_globals.append((t.id, node.lineno))
                elif isinstance(v, ast.Call):
                    func_name = ""
                    if isinstance(v.func, ast.Name):
                        func_name = v.func.id
                    elif isinstance(v.func, ast.Attribute):
                        func_name = v.func.attr
                    if func_name in MUTABLE_BUILTINS:
                        mutable_globals.append((t.id, node.lineno))

    if len(mutable_globals) >= 2:
        names = ", ".join(f"`{n}`" for n, _ in mutable_globals)
        first_line = mutable_globals[0][1]
        bugs.append({
            "line": first_line,
            "code": f"{names} — module-level mutable state",
            "type": "stale globals — move ALL inside entry function, pass to helpers"
        })

    # ── Pass 2: walk all nodes ─────────────────────────────────────────────────
    class BugVisitor(ast.NodeVisitor):

        def visit_Assign(self, node):
            if (
                isinstance(node.value, ast.UnaryOp)
                and isinstance(node.value.op, ast.UAdd)
            ):
                bugs.append({
                    "line": node.lineno,
                    "code": get_line(node),
                    "type": "=+ instead of +="
                })
            self.generic_visit(node)

        def visit_BinOp(self, node):
            if isinstance(node.op, ast.Div):
                bugs.append({
                    "line": node.lineno,
                    "code": get_line(node),
                    "type": "division — verify denominator != 0 (trace call-site arguments)"
                })
            self.generic_visit(node)

        def visit_Call(self, node):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            if func_name in ("max", "min") and node.args:
                bugs.append({
                    "line": node.lineno,
                    "code": get_line(node),
                    "type": f"{func_name}() on possibly empty container — add empty guard"
                })
            self.generic_visit(node)

        def visit_Compare(self, node):
            has_gte = any(isinstance(op, (ast.GtE, ast.LtE, ast.Gt, ast.Lt)) for op in node.ops)
            left_is_subscript = isinstance(node.left, ast.Subscript)
            right_has_strftime = any(
                isinstance(c, ast.Attribute) and c.attr == "strftime"
                for c in ast.walk(ast.Expression(body=node))
            )
            if has_gte and left_is_subscript and right_has_strftime:
                bugs.append({
                    "line": node.lineno,
                    "code": get_line(node),
                    "type": "date string comparison — lexicographic; parse back to datetime"
                })
            self.generic_visit(node)

    BugVisitor().visit(tree)

    seen = set()
    unique = []
    for b in bugs:
        key = (b["line"], b["type"][:30])
        if key not in seen:
            seen.add(key)
            unique.append(b)

    unique.sort(key=lambda b: b["line"])
    return unique


# ─── Prompt helpers ────────────────────────────────────────────────────────────

def _get_fix_principles() -> str:
    """
    Generic fix principles — teach correct reasoning patterns,
    not specific rules for specific bugs.
    """
    return (
        "### Fix principles:\n"
        "1. When guarding against a zero/empty/None value, the safe fallback must be "
        "semantically correct — not just syntactically safe. "
        "Ask: what should the caller receive when the value is missing? "
        "Return that value, not an arbitrary substitute like 1 or \'dummy\'.\n"
        "   Good: `return a / b if b != 0 else 0`  ← 0 is the correct answer when there is nothing to divide\n"
        "   Bad:  `return a / (b if b != 0 else 1)` ← silently returns wrong result\n\n"
        "2. When a container guard is needed, use an explicit `if container` check — "
        "not a keyword argument that does not exist on the built-in.\n"
        "   Good: `return max(items, key=...) if items else None`\n"
        "   Bad:  `return max(items, key=..., default=None)`  ← max() has no default kwarg\n\n"
        "3. When a mutable value is passed to a helper by value (e.g. an int counter), "
        "changes inside the helper are invisible to the caller. "
        "The helper must return the updated value and the caller must reassign it.\n"
        "   Good: `count = helper(..., count)` where helper does `return count + 1`\n"
        "   Bad:  `helper(..., count)` and expecting count to change\n\n"
        "4. When fixing stale globals, move ALL mutable module-level variables inside "
        "the entry function. Pass every one as a parameter to every helper that uses them.\n\n"
    )


def _get_examples() -> str:
    return (
        "### Output format — copy exactly:\n\n"
        "Bug 1:\n"
        "Issue: `totals[tag][\"sum\"] =+ score`\n"
        "Explanation: `=+` sets sum to score every call instead of accumulating.\n"
        "Fix:\n"
        "```python\n"
        "totals[tag][\"sum\"] += score\n"
        "```\n\n"
        "Bug 2:\n"
        "Issue: `hits =+ 1`\n"
        "Explanation: `=+` resets hits to 1 every call instead of incrementing.\n"
        "Fix:\n"
        "```python\n"
        "hits += 1\n"
        "```\n\n"
        "Bug 3:\n"
        "Issue: `hits = 0`, `cache = {}`, `totals = defaultdict(dict)` — module-level mutable state\n"
        "Explanation: Stale data bleeds between runs. Move ALL inside entry function, pass to helpers.\n"
        "Fix:\n"
        "```python\n"
        "def run(items):\n"
        "    hits   = 0\n"
        "    cache  = {}\n"
        "    totals = defaultdict(dict)\n"
        "    for item in items:\n"
        "        hits = process(item[\"id\"], item[\"score\"], cache, totals, hits)\n"
        "```\n\n"
        "Bug 4:\n"
        "Issue: `return score / base * 100`\n"
        "Explanation: Caller passes `score - 10` as base — when score==10, base==0, ZeroDivisionError.\n"
        "Fix:\n"
        "```python\n"
        "return (score / base) * 100 if base != 0 else 0\n"
        "```\n\n"
        "Bug 5:\n"
        "Issue: `max(cache, key=lambda x: cache[x][\"score\"])`\n"
        "Explanation: ValueError when cache is empty on second clean run.\n"
        "Fix:\n"
        "```python\n"
        "return max(cache, key=lambda x: cache[x][\"score\"]) if cache else None\n"
        "```\n\n"
        "Bug 6:\n"
        "Issue: `return totals[tag][\"sum\"] / totals[tag][\"count\"]`\n"
        "Explanation: ZeroDivisionError when count is 0.\n"
        "Fix:\n"
        "```python\n"
        "return totals[tag][\"sum\"] / totals[tag][\"count\"] if totals[tag][\"count\"] else 0\n"
        "```\n\n"
        "Bug 7:\n"
        "Issue: `if v[\"joined\"] >= cutoff.strftime(\"%d-%m-%Y\")`\n"
        "Explanation: Lexicographic string comparison — \"05-03-2026\" > \"20-01-2026\" is False but should be True.\n"
        "Fix:\n"
        "```python\n"
        "if datetime.datetime.strptime(v[\"joined\"], \"%d-%m-%Y\") >= cutoff\n"
        "```\n\n"
    )


def _get_output_rules() -> str:
    return (
        "### Output rules:\n"
        "- Quote the exact buggy line for every bug\n"
        "- Fix block: corrected code only, 1-3 lines\n"
        "- Silent about non-bugs — never write \'not a bug\' or \'no change needed\'\n"
        "- No ### headers, no bullet format\n\n"
    )


def _build_slim_prompt(confirmed_bugs: list, code: str, logs: str,
                       query: str, context_str: str,
                       first_answer: str = "") -> str:
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."

    if confirmed_bugs:
        bug_list = "\n".join(
            f"  - Line {b['line']}: `{b['code']}` — {b['type']}"
            for b in confirmed_bugs
        )
        task = (
            f"### Confirmed bugs (static analysis):\n{bug_list}\n\n"
            "### Your job:\n"
            "1. Write a Bug N block for each confirmed bug above.\n"
            "2. Check logs for additional semantic bugs NOT in the list.\n\n"
        )
    else:
        task = (
            "### Your job:\n"
            "Analyze the code and logs. Report only clearly visible bugs.\n\n"
        )

    if first_answer:
        task = (
            f"### Already reported — do NOT repeat:\n{first_answer}\n\n"
            "### Your job:\n"
            "Find ONLY bugs missed above. If none → reply: No additional bugs found.\n\n"
        )

    return (
        "### Instruction:\n"
        "You are a senior software engineer. Find and fix every bug in the code below.\n\n"
        + task
        + _get_fix_principles()
        + _get_output_rules()
        + _get_examples()
        + f"### Code:\n```python\n{code}\n```\n\n"
        + f"### Logs:\n{logs_text}\n\n"
        + f"### Question:\n{query}\n\n"
        + f"### Context:\n{context_str}\n\n"
        + "### Response (Bug N: format only):\n"
    )


# ─── LLM passes ───────────────────────────────────────────────────────────────

def generate_answer(confirmed_bugs: list, query: str, code: str, logs: str) -> str:
    context = retrieve(query)
    context_str = "\n- ".join(context) if context else "No relevant context."
    return call_ollama(_build_slim_prompt(confirmed_bugs, code, logs, query, context_str))


def second_pass(confirmed_bugs: list, query: str, code: str,
                logs: str, first_answer: str) -> str:
    context = retrieve(query)
    context_str = "\n- ".join(context) if context else "No relevant context."
    return call_ollama(
        _build_slim_prompt(confirmed_bugs, code, logs, query, context_str,
                           first_answer=first_answer)
    )


def critique_answer(query: str, code: str, logs: str, answer: str) -> str:
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."
    prompt = (
        "### Instruction:\n"
        "You are a strict code reviewer. Check this answer against the code.\n\n"
        "### Checklist:\n"
        "1. Every bug quotes an EXACT line from the code — not invented.\n"
        "2. Every `=+` line is caught.\n"
        "3. ALL mutable globals flagged + fix passes them as parameters to every helper.\n"
        "4. Call-chain division: does the denominator become 0 given real input values?\n"
        "5. `max()`/`min()` — is the empty guard `if container else None` (not a kwarg)?\n"
        "6. Division guard returns 0 on zero denominator (not `else 1` or other substitute).\n"
        "7. Date string comparison bug caught with correct stored format.\n"
        "8. Int counters passed to helpers: does helper return updated value, caller reassign?\n"
        "9. No duplicates. No non-existent kwarg usage. No thread/lock suggestions.\n"
        "10. No \'not a bug\' or \'no change needed\' entries.\n\n"
        f"### Code:\n```python\n{code}\n```\n\n"
        f"### Logs:\n{logs_text}\n\n"
        f"### Answer:\n{answer}\n\n"
        "### Response (ONLY this format):\n"
        "Correct? YES\nErrors found: None\nWhat to fix: Nothing\n\n"
        "OR:\n\n"
        "Correct? NO\n"
        "Errors found: <specific>\n"
        "What to fix: <one instruction>\n"
    )
    return call_ollama(prompt)


def refine_answer(query: str, code: str, logs: str,
                  answer: str, critique: str) -> str:
    what_to_fix = ""
    for line in critique.splitlines():
        if line.lower().startswith("what to fix:"):
            what_to_fix = line.split(":", 1)[-1].strip()
            break
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."
    prompt = (
        "### Instruction:\n"
        "Fix the answer per critique. Apply fix principles carefully.\n\n"
        + _get_fix_principles()
        + f"### What to fix:\n{what_to_fix or critique}\n\n"
        "### Rules:\n"
        "- KEEP valid bugs\n"
        "- ADD confirmed missing bugs\n"
        "- REMOVE: invented lines, duplicates, non-existent kwargs, "
        "wrong fallback values, thread/lock suggestions, \'not a bug\' entries\n"
        "- Bug N: / Issue: / Explanation: / Fix: format only\n\n"
        f"### Code:\n```python\n{code}\n```\n\n"
        f"### Logs:\n{logs_text}\n\n"
        f"### Answer:\n{answer}\n\n"
        "### Response:\n"
    )
    return call_ollama(prompt)


# ─── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate_bugs(text: str) -> str:
    # Strip separator before processing so second-pass blocks merge cleanly
    text = text.replace("--- Additional Bugs Found ---", "").strip()

    seen = set()
    output = []
    current_block = []

    def _fingerprint(block):
        issue = next(
            (l.lower().strip() for l in block if l.strip().lower().startswith("issue:")), ""
        )
        in_fix, fix_line = False, ""
        for l in block:
            if l.strip().startswith("```python"):
                in_fix = True
                continue
            if in_fix and l.strip() and not l.strip().startswith("```"):
                fix_line = l.lower().strip()
                break
        return issue + "|" + fix_line

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("bug ") and ":" in stripped and len(stripped) < 20:
            if current_block:
                fp = _fingerprint(current_block)
                if fp and fp not in seen:
                    seen.add(fp)
                    output.extend(current_block)
                elif not fp.strip("|"):
                    output.extend(current_block)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        fp = _fingerprint(current_block)
        if fp and fp not in seen:
            output.extend(current_block)
        elif not fp.strip("|"):
            output.extend(current_block)

    return "\n".join(output)


# ─── Response quality filters ─────────────────────────────────────────────────

def is_bad_response(text: str) -> bool:
    tl = text.lower()
    bad = [
        "fibonacci", "i don\'t see any code", "no code was provided",
        "without running", "speculative", "impossible to find",
        "from queue import", "lock = lock()", "with lock:",
        "lock.acquire", "semaphore", "asyncio", "multiprocessing",
        "error after 3 attempts", "error after 2 attempts",
        "i\'m ready", "i am ready", "please provide the code",
        "waiting for the code", "ready to analyze",
        "t.join()", "race condition",
        ".clear()  # clear", "active_sessions.clear()",
        "sale_registry.clear()", "user_registry.clear()",
        "dept_scores.clear()",
        "### bug 1", "### bug 2", "### bug 3",
        "- **description**:", "- **impact**:",
        # Wrong fix patterns
        "+ 0.001", "+ 1e-", "epsilon",
        "else 1))", "else 1) *", "!= 0 else 1)",  # wrong fallback
        ", default=none)",                          # non-existent kwarg
        "default=none",
        # Non-bug reporting
        "no change needed", "is already correct",
        "not a bug here", "no bug here", "not a bug",
    ]
    return any(w in tl for w in bad)


def is_correct_line_flagged(text: str) -> bool:
    signals = [
        "count += 1` is correct",
        "count += 1` does not need",
        "already correct. no bug",
        "is already correct",
        "no bug here",
        "no change needed",
        "is correct. no",
        "not a bug",
    ]
    tl = text.lower()
    return any(s.lower() in tl for s in signals)


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(query: str, code: str, logs: str) -> dict:
    if is_off_topic(query, code):
        return {
            "ast_bugs":       [],
            "initial_answer": "This tool only answers code debugging questions.",
            "critique":       "Skipped — off-topic",
            "final_answer":   "This tool only answers code debugging questions. Please provide a code snippet."
        }

    if not code or not code.strip():
        return {
            "ast_bugs":       [],
            "initial_answer": "No code provided.",
            "critique":       "Skipped — no code",
            "final_answer":   "No code provided. Please paste a code snippet to debug."
        }

    if not query or not query.strip():
        query = "Identify all the bugs"
    if logs is None:
        logs = ""

    # Step 1 — deterministic AST pre-detection
    confirmed_bugs = ast_detect_bugs(code)

    # Step 2 — LLM first pass (retry once if bad)
    initial = generate_answer(confirmed_bugs, query, code, logs)
    if is_bad_response(initial) or is_correct_line_flagged(initial):
        initial = generate_answer(confirmed_bugs, query, code, logs)
    if is_bad_response(initial):
        return {
            "ast_bugs":       confirmed_bugs,
            "initial_answer": initial,
            "critique":       "Skipped — bad initial response",
            "final_answer":   initial
        }

    # Step 3 — second pass for code > 20 lines
    combined = initial
    if len(code.strip().splitlines()) > 20:
        try:
            second = second_pass(confirmed_bugs, query, code, logs, initial)
            if (
                second
                and "no additional bugs found" not in second.lower()
                and not is_bad_response(second)
                and not is_correct_line_flagged(second)
            ):
                combined = initial + "\n\n--- Additional Bugs Found ---\n" + second
        except Exception:
            pass

    # Step 4 — dedup (also strips separator)
    combined = deduplicate_bugs(combined)

    # Step 5 — critique + refine (only when logs present)
    critique = "Skipped"
    final = combined
    if logs and logs.strip():
        try:
            critique = critique_answer(query, code, logs, combined)
            correct_line = critique.lower().split("correct?")[-1][:30]

            if "no" in correct_line:
                refined = refine_answer(query, code, logs, combined, critique)
                ef = critique.lower()
                removing = any(w in ef for w in [
                    "duplicate", "remove", "thread.join", "race condition",
                    ".clear()", "wrong fix", "correct line", "invented",
                    "not in the code", "epsilon", "not a bug", "no change needed",
                    "not allowed", "wrong fallback", "else 1", "default=none",
                    "non-existent kwarg", "kwarg",
                ])
                adding = any(w in ef for w in [
                    "missed", "not found", "not all globals", "second =+",
                    "date string", "avg", "helpers", "call chain",
                    "denominator", "counter", "reassign", "return updated",
                ])

                if not is_bad_response(refined) and not is_correct_line_flagged(refined):
                    if removing or (adding and len(refined.strip()) > len(combined.strip())):
                        final = deduplicate_bugs(refined)
                    else:
                        final = combined
                else:
                    final = combined
        except Exception:
            critique = "Skipped — timeout"
            final = combined

    # Step 6 — final dedup
    final = deduplicate_bugs(final)

    return {
        "ast_bugs":       confirmed_bugs,
        "initial_answer": initial,
        "critique":       critique,
        "final_answer":   final
    }