import ast
import json
import re
import time
import textwrap

import requests
from rag.vector_store import retrieve


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b-instruct"
REQUEST_TIMEOUT = 180
NUM_PREDICT = 1400
NO_CONTEXT = "No relevant context."
IRRELEVANT_MESSAGE = "Sorry I cant help you with this"


# ─── Ollama caller ─────────────────────────────────────────────────────────────


def call_ollama(prompt: str, retries: int = 2, temperature: float = 0) -> str:
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "options": {"num_predict": NUM_PREDICT},
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json().get("response", "")
            if not result.strip():
                raise ValueError("Empty response from model")

            result = re.sub(r"<\|[^|]+\|>", "", result).strip()
            return result

        except (KeyError, ValueError, requests.RequestException) as e:
            last_error = e
            if attempt == retries:
                return f"Error after {retries + 1} attempts: {str(last_error)}"
            time.sleep(2)


# ─── LLM router ────────────────────────────────────────────────────────────────


def _looks_like_debug_request(query: str, code: str, logs: str) -> bool:
    if code and code.strip():
        return True

    combined = f"{query or ''}\n{logs or ''}".lower()
    debug_signals = [
        "traceback",
        "exception",
        "error",
        "bug",
        "debug",
        "fix",
        "zerodivisionerror",
        "indexerror",
        "keyerror",
        "typeerror",
        "valueerror",
        "syntaxerror",
        "attributeerror",
        "nameerror",
        "python",
    ]
    return any(signal in combined for signal in debug_signals)


def route_prompt(query: str, code: str, logs: str) -> str:
    if _looks_like_debug_request(query, code, logs):
        return "DEBUG"

    prompt = f"""
You are a routing classifier for a Python bug-finding assistant.

The assistant handles:
- debugging Python code
- finding bugs in Python code
- fixing Python errors
- analyzing Python tracebacks or logs
- reviewing Python code for bugs

The assistant does NOT handle:
- casual chat
- general knowledge
- recipes, poems, essays, stories
- non-debugging tasks unrelated to Python bug/error finding

Return ONLY valid JSON in exactly one of these forms:
{{"decision":"DEBUG"}}
{{"decision":"REJECT","message":"{IRRELEVANT_MESSAGE}"}}

Rules:
- If code is present, strongly prefer DEBUG.
- If logs/tracebacks/exceptions are present, strongly prefer DEBUG.
- If the user is asking for Python bug/error analysis, prefer DEBUG.
- Otherwise return REJECT.

Query:
{query or ""}

Code:
```python
{code or ""}
```

Logs:
{logs or ""}
""".strip()

    raw = call_ollama(prompt, retries=1, temperature=0)

    try:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        payload = json.loads(match.group(0) if match else raw)
        decision = str(payload.get("decision", "")).strip().upper()
        if decision == "DEBUG":
            return "DEBUG"
        return "REJECT"
    except Exception:
        return "REJECT"


# ─── Context helper ────────────────────────────────────────────────────────────


def _get_context(query: str, code: str = "", logs: str = "") -> str:
    retrieval_query = query.strip() if query and query.strip() else "python bug debugging"
    signals = set()

    try:
        if code and code.strip():
            tree = ast.parse(textwrap.dedent(code))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    signals.add(node.name)
                elif isinstance(node, ast.AsyncFunctionDef):
                    signals.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    signals.add(node.name)
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        signals.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        signals.add(node.func.attr)
    except Exception:
        pass

    if logs:
        for m in re.findall(r"\b[A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning)\b", logs):
            signals.add(m)

    if signals:
        retrieval_query += "\n" + " ".join(sorted(signals)[:40])

    try:
        context = retrieve(retrieval_query)
        return "\n- ".join(context) if context else NO_CONTEXT
    except Exception:
        return NO_CONTEXT


# ─── AST Pre-Detector ─────────────────────────────────────────────────────────


def ast_detect_bugs(source: str, logs: str = "") -> dict:
    findings = {"bugs": [], "risks": [], "smells": []}

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as e:
        return {
            "bugs": [{"line": 0, "code": str(e), "type": "SyntaxError — fix before analysis"}],
            "risks": [],
            "smells": [],
        }

    lines = source.splitlines()
    mutable_builtins = {"dict", "list", "defaultdict", "set", "OrderedDict", "Counter", "deque"}

    def get_line(node):
        lineno = getattr(node, "lineno", 0)
        return lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""

    def add_finding(kind, node, finding_type, code=None):
        findings[kind].append({
            "line": getattr(node, "lineno", 0),
            "code": code if code is not None else get_line(node),
            "type": finding_type,
        })

    def mark_parents(root):
        for parent in ast.walk(root):
            for child in ast.iter_child_nodes(parent):
                child._parent = parent

    def is_with_open_call(node):
        parent = getattr(node, "_parent", None)
        while parent is not None:
            if isinstance(parent, ast.withitem):
                return True
            if isinstance(parent, (ast.With, ast.AsyncWith)):
                return True
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                return False
            parent = getattr(parent, "_parent", None)
        return False

    def contains_error_signal(text):
        tl = (text or "").lower()
        return any(s in tl for s in ["indexerror", "keyerror", "zero division", "zerodivisionerror"])

    mark_parents(tree)

    mutable_globals = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if not isinstance(t, ast.Name):
                    continue
                v = node.value
                if isinstance(v, (ast.Dict, ast.List, ast.Set)):
                    mutable_globals.append((t.id, node.lineno))
                elif isinstance(v, ast.Call):
                    func_name = ""
                    if isinstance(v.func, ast.Name):
                        func_name = v.func.id
                    elif isinstance(v.func, ast.Attribute):
                        func_name = v.func.attr
                    if func_name in mutable_builtins:
                        mutable_globals.append((t.id, node.lineno))

    if len(mutable_globals) >= 2:
        names = ", ".join(f"`{n}`" for n, _ in mutable_globals)
        findings["bugs"].append({
            "line": mutable_globals[0][1],
            "code": f"{names} — module-level mutable state",
            "type": "stale globals — move mutable state inside entry function and pass to helpers",
        })

    class BugVisitor(ast.NodeVisitor):
        def visit_Assign(self, node):
            line = get_line(node).replace(" ", "")
            if "=+" in line:
                add_finding("bugs", node, "=+ instead of +=")
            self.generic_visit(node)

        def visit_BinOp(self, node):
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                add_finding("risks", node, "possible division-like risk — verify denominator cannot become 0")
            self.generic_visit(node)

        def visit_Call(self, node):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in ("max", "min") and node.args:
                has_default = any(kw.arg == "default" for kw in node.keywords)
                if not has_default:
                    add_finding(
                        "risks",
                        node,
                        f"potential empty-container risk in {func_name}() — consider guard if input can be empty",
                    )

            if func_name == "open" and not is_with_open_call(node):
                add_finding(
                    "smells",
                    node,
                    "resource-handling smell — consider `with open(...)` for automatic close",
                )

            self.generic_visit(node)

        def visit_Compare(self, node):
            has_order_compare = any(isinstance(op, (ast.GtE, ast.LtE, ast.Gt, ast.Lt)) for op in node.ops)
            if not has_order_compare or not node.comparators:
                self.generic_visit(node)
                return

            left_has_strftime = any(
                isinstance(c, ast.Attribute) and c.attr == "strftime"
                for c in ast.walk(node.left)
            )
            right_has_strftime = any(
                isinstance(c, ast.Attribute) and c.attr == "strftime"
                for comp in node.comparators
                for c in ast.walk(comp)
            )

            if left_has_strftime or right_has_strftime:
                add_finding(
                    "risks",
                    node,
                    "potential date-string comparison risk — verify formatted strings are safe for ordering",
                )

            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if node.type is None:
                add_finding("bugs", node, "bare except — catches everything and hides real failures")
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                if any(isinstance(stmt, ast.Pass) for stmt in node.body):
                    add_finding("bugs", node, "except Exception: pass — swallows errors")
            self.generic_visit(node)

        def visit_Try(self, node):
            exception_types = []
            for handler in node.handlers:
                if isinstance(handler.type, ast.Name):
                    exception_types.append(handler.type.id)
                elif handler.type is None:
                    exception_types.append("BaseException")
                else:
                    exception_types.append("other")

            if "Exception" in exception_types:
                idx = exception_types.index("Exception")
                if idx < len(exception_types) - 1:
                    add_finding(
                        "bugs",
                        node.handlers[idx],
                        "incorrect exception ordering — broad `Exception` handler may shadow narrower handlers",
                    )

            if "BaseException" in exception_types:
                idx = exception_types.index("BaseException")
                if idx < len(exception_types) - 1:
                    add_finding(
                        "bugs",
                        node.handlers[idx],
                        "incorrect exception ordering — bare except may shadow narrower handlers",
                    )

            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            self._check_function(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            self._check_function(node)
            self.generic_visit(node)

        def _check_function(self, node):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    add_finding("bugs", default, f"mutable default argument in `{node.name}`")
                elif isinstance(default, ast.Call):
                    func_name = ""
                    if isinstance(default.func, ast.Name):
                        func_name = default.func.id
                    elif isinstance(default.func, ast.Attribute):
                        func_name = default.func.attr
                    if func_name in mutable_builtins:
                        add_finding("bugs", default, f"mutable default argument in `{node.name}`")

            returns = [sub.value is not None for sub in ast.walk(node) if isinstance(sub, ast.Return)]
            if returns and any(returns) and not all(returns):
                add_finding("bugs", node, f"inconsistent returns in `{node.name}` — some paths return values, others do not")

            self._detect_unreachable(node.body)

        def _detect_unreachable(self, stmts):
            for i, stmt in enumerate(stmts[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    unreachable_stmt = stmts[i + 1]
                    add_finding(
                        "bugs",
                        unreachable_stmt,
                        "unreachable code — this statement cannot run because control flow already exits earlier",
                    )

                nested_blocks = []
                if isinstance(stmt, ast.If):
                    nested_blocks.extend([stmt.body, stmt.orelse])
                elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                    nested_blocks.extend([stmt.body, stmt.orelse])
                elif isinstance(stmt, (ast.With, ast.AsyncWith, ast.Try)):
                    nested_blocks.append(stmt.body)
                    if hasattr(stmt, "orelse"):
                        nested_blocks.append(stmt.orelse)
                    if hasattr(stmt, "finalbody"):
                        nested_blocks.append(stmt.finalbody)
                    if isinstance(stmt, ast.Try):
                        for handler in stmt.handlers:
                            nested_blocks.append(handler.body)

                for block in nested_blocks:
                    if block:
                        self._detect_unreachable(block)

        def visit_Subscript(self, node):
            if contains_error_signal(logs) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                add_finding(
                    "risks",
                    node,
                    "possible indexing risk — logs suggest an indexing failure, verify bounds before positional access",
                )
            self.generic_visit(node)

    BugVisitor().visit(tree)

    for kind in findings:
        seen = set()
        unique = []
        for f in findings[kind]:
            key = (f["line"], f["type"][:100], f["code"][:180])
            if key not in seen:
                seen.add(key)
                unique.append(f)
        unique.sort(key=lambda x: x["line"])
        findings[kind] = unique

    return findings


# ─── Prompt helpers ────────────────────────────────────────────────────────────


def _get_fix_principles() -> str:
    return (
        "### Fix principles:\n"
        "1. When guarding against a zero/empty/None value, the fallback must be semantically correct.\n"
        "2. Use explicit empty-container guards for risky operations.\n"
        "3. If helper functions update values such as counters, they must return the updated value.\n"
        "4. Move mutable module-level state into the entry function and pass it explicitly.\n"
        "5. Make inconsistent return paths consistent.\n"
        "6. Do not swallow real failures with broad exception handlers.\n"
        "7. If the same bug appears multiple times, report it once.\n"
        "8. For lower-confidence risks, report them only when code or logs support them.\n\n"
    )


def _get_examples() -> str:
    return (
        "### Output format — copy exactly:\n\n"
        "Bug 1:\n"
        "Issue: `hits =+ 1`\n"
        "Explanation: `=+` resets the value instead of incrementing it.\n"
        "Fix:\n"
        "```python\n"
        "hits += 1\n"
        "```\n\n"
        "Bug 2:\n"
        "Issue: `return total / count`\n"
        "Explanation: This can raise ZeroDivisionError when count is 0.\n"
        "Fix:\n"
        "```python\n"
        "return total / count if count else 0\n"
        "```\n\n"
        "Bug 3:\n"
        "Issue: `def add(x, seen=[]):`\n"
        "Explanation: Mutable default arguments are shared across calls.\n"
        "Fix:\n"
        "```python\n"
        "def add(x, seen=None):\n"
        "    seen = [] if seen is None else seen\n"
        "```\n\n"
        "Bug 4:\n"
        "Issue: `except Exception: pass`\n"
        "Explanation: This swallows real failures and hides debugging evidence.\n"
        "Fix:\n"
        "```python\n"
        "except Exception:\n"
        "    raise\n"
        "```\n\n"
    )


def _get_output_rules() -> str:
    return (
        "### Output rules:\n"
        "- Quote the exact buggy line for every bug.\n"
        "- Fix block: corrected code only, 1-4 lines.\n"
        "- Silent about non-bugs.\n"
        "- Start numbering at Bug 1.\n"
        "- No bullet format outside Bug N blocks.\n"
        "- Do not repeat duplicate or near-duplicate bugs.\n"
        "- Only report real bugs in the final Bug N output.\n\n"
    )


def _format_findings(findings: dict) -> str:
    parts = []

    if findings["bugs"]:
        parts.append("High-confidence bugs:")
        parts.extend(f"- Line {b['line']}: `{b['code']}` — {b['type']}" for b in findings["bugs"])

    if findings["risks"]:
        parts.append("\nPotential runtime risks (include only if supported by code/logs):")
        parts.extend(f"- Line {r['line']}: `{r['code']}` — {r['type']}" for r in findings["risks"])

    if findings["smells"]:
        parts.append("\nCode smells (do NOT report unless directly relevant to a real bug):")
        parts.extend(f"- Line {s['line']}: `{s['code']}` — {s['type']}" for s in findings["smells"])

    return "\n".join(parts) if parts else "None"


def _build_prompt(
    findings: dict,
    code: str,
    logs: str,
    query: str,
    context_str: str,
    first_answer: str = "",
) -> str:
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."

    if first_answer:
        task = (
            f"### Already reported — do NOT repeat:\n{first_answer}\n\n"
            "### Your job:\n"
            "Find ONLY clearly supported real bugs missed above.\n"
            "Do not add speculative issues.\n"
            "Do not convert smells into bugs.\n"
            "If none, reply exactly: No additional bugs found.\n\n"
        )
    else:
        task = (
            f"### Static findings:\n{_format_findings(findings)}\n\n"
            "### Your job:\n"
            "1. Write a Bug N block for each high-confidence bug.\n"
            "2. Include a potential runtime risk only if the code or logs support it as a real bug.\n"
            "3. Do not report code smells unless they directly explain a real failure.\n"
            "4. Also find any other real Python bug supported by the code or logs.\n"
            "5. Do not repeat the same bug twice.\n\n"
        )

    return (
        "### Instruction:\n"
        "You are a senior Python software engineer. Find and fix real bugs in the code below.\n\n"
        + task
        + _get_fix_principles()
        + _get_output_rules()
        + _get_examples()
        + f"### Code:\n```python\n{code}\n```\n\n"
        + f"### Logs:\n{logs_text}\n\n"
        + f"### Question:\n{query}\n\n"
        + f"### Context:\n{context_str}\n\n"
        + "### Response:\n"
    )


# ─── LLM passes ───────────────────────────────────────────────────────────────


def generate_answer(findings: dict, query: str, code: str, logs: str, context_str: str) -> str:
    return call_ollama(_build_prompt(findings, code, logs, query, context_str))


def second_pass(findings: dict, query: str, code: str, logs: str, first_answer: str, context_str: str) -> str:
    return call_ollama(
        _build_prompt(
            findings,
            code,
            logs,
            query,
            context_str,
            first_answer=first_answer,
        )
    )


def critique_answer(query: str, code: str, logs: str, answer: str) -> str:
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."

    prompt = (
        "### Instruction:\n"
        "You are a strict Python code-review critic. Review the answer against the code and logs.\n\n"
        "### Checklist:\n"
        "1. Every bug quotes an exact line from the code.\n"
        "2. Bugs are real and supported.\n"
        "3. No duplicate or near-duplicate bug reports exist.\n"
        "4. Fixes are minimal and correct.\n"
        "5. Mutable default argument bugs are caught when present.\n"
        "6. Broad exception swallowing is caught when present.\n"
        "7. Inconsistent return-path bugs are caught when present.\n"
        "8. No invented kwargs, locks, threads, or speculative fixes.\n"
        "9. No 'not a bug' or 'no change needed' entries.\n\n"
        "### Rules:\n"
        "- Do not invent new bugs.\n"
        "- If you claim a bug is wrong or missing, mention the exact quoted line involved.\n\n"
        f"### Code:\n```python\n{code}\n```\n\n"
        f"### Logs:\n{logs_text}\n\n"
        f"### Answer:\n{answer}\n\n"
        "### Response (ONLY this format):\n"
        "Correct? YES\nErrors found: None\nWhat to fix: Nothing\n\n"
        "OR\n\n"
        "Correct? NO\n"
        "Errors found: <specific>\n"
        "What to fix: <one instruction tied to quoted lines>\n"
    )
    return call_ollama(prompt)


def refine_answer(query: str, code: str, logs: str, answer: str, critique: str) -> str:
    logs_text = logs.strip() if logs and logs.strip() else "No logs provided."

    what_to_fix = ""
    for line in critique.splitlines():
        if line.lower().startswith("what to fix:"):
            what_to_fix = line.split(":", 1)[-1].strip()
            break

    prompt = (
        "### Instruction:\n"
        "Fix the answer using the critique.\n"
        "Keep valid bugs, correct wrong ones, and remove duplicate or invented bugs.\n"
        "Do NOT introduce a new bug unless it is directly supported by an exact quoted code line already mentioned in the critique.\n\n"
        + _get_fix_principles()
        + f"### What to fix:\n{what_to_fix or critique}\n\n"
        + f"### Code:\n```python\n{code}\n```\n\n"
        + f"### Logs:\n{logs_text}\n\n"
        + f"### Previous answer:\n{answer}\n\n"
        + "### Response:\n"
    )
    return call_ollama(prompt)


# ─── Deduplication ─────────────────────────────────────────────────────────────


def deduplicate_bugs(text: str) -> str:
    text = (text or "").replace("--- Additional Bugs Found ---", "").strip()

    seen = set()
    output = []
    current_block = []

    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"`+", "", s)
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[^a-z0-9_:/().<>= \-]", "", s)
        return s

    def extract_issue_line(block):
        for line in block:
            stripped = line.strip()
            if stripped.lower().startswith("issue:"):
                return stripped.split(":", 1)[1].strip()
        return ""

    def extract_fix_head(block):
        in_fix = False
        for line in block:
            stripped = line.strip()
            if stripped.startswith("```python"):
                in_fix = True
                continue
            if stripped.startswith("```") and in_fix:
                in_fix = False
                continue
            if in_fix and stripped:
                return stripped
        return ""

    def fingerprint(block):
        issue_line = extract_issue_line(block)
        fix_head = extract_fix_head(block)
        line_match = re.search(r"line\s+(\d+)", normalize("\n".join(block)))
        line_no = line_match.group(1) if line_match else ""
        return "|".join([
            normalize(line_no),
            normalize(issue_line),
            normalize(fix_head),
        ])

    def flush():
        nonlocal current_block
        if not current_block:
            return
        fp = fingerprint(current_block)
        if fp and fp not in seen:
            seen.add(fp)
            output.extend(current_block)
        elif not fp.strip("|"):
            output.extend(current_block)
        current_block = []

    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^bug\s+\d+\s*:$", stripped):
            flush()
            current_block = [line]
        else:
            current_block.append(line)

    flush()
    return "\n".join(output)


def renumber_bugs(text: str, start: int = 1) -> str:
    counter = start

    def repl(match):
        nonlocal counter
        value = f"Bug {counter}:"
        counter += 1
        return value

    return re.sub(r"(?im)^bug\s+\d+\s*:", repl, text or "", flags=re.MULTILINE)


# ─── Response quality filters ─────────────────────────────────────────────────


def is_bad_response(text: str) -> bool:
    tl = (text or "").lower()
    bad_terms = [
        "i don't see any code",
        "no code was provided",
        "please provide the code",
        "waiting for the code",
        "ready to analyze",
        "i'm ready",
        "i am ready",
        "not a bug here",
        "no bug here",
        "no change needed",
        "is already correct",
        "lock.acquire",
        "with lock:",
        "semaphore",
        "thread.join",
        "race condition",
        "default=none",
    ]
    return not tl.strip() or any(term in tl for term in bad_terms)


def is_correct_line_flagged(text: str) -> bool:
    tl = (text or "").lower()
    signals = [
        "is already correct",
        "no bug here",
        "no change needed",
        "not a bug",
        "already correct. no bug",
    ]
    return any(s in tl for s in signals)


# ─── Pipeline ─────────────────────────────────────────────────────────────────


def run_pipeline(query: str, code: str, logs: str) -> dict:
    query = query or ""
    code = code or ""
    logs = logs or ""

    decision = route_prompt(query, code, logs)
    if decision != "DEBUG":
        return {
            "ast_bugs": {"bugs": [], "risks": [], "smells": []},
            "initial_answer": IRRELEVANT_MESSAGE,
            "critique": "Skipped — irrelevant prompt",
            "final_answer": IRRELEVANT_MESSAGE,
        }

    if not code.strip():
        return {
            "ast_bugs": {"bugs": [], "risks": [], "smells": []},
            "initial_answer": "Please provide the Python code snippet or traceback to debug.",
            "critique": "Skipped — no code",
            "final_answer": "Please provide the Python code snippet or traceback to debug.",
        }

    if not query.strip():
        query = "Identify all real Python bugs and errors."

    context_str = _get_context(query, code, logs)
    findings = ast_detect_bugs(code, logs=logs)

    initial = generate_answer(findings, query, code, logs, context_str)
    if is_bad_response(initial) or is_correct_line_flagged(initial):
        initial = generate_answer(findings, query, code, logs, context_str)

    if is_bad_response(initial):
        clean_initial = renumber_bugs(initial, start=1)
        return {
            "ast_bugs": findings,
            "initial_answer": clean_initial,
            "critique": "Skipped — bad initial response",
            "final_answer": clean_initial,
        }

    combined = initial
    if len(code.strip().splitlines()) > 20:
        try:
            second = second_pass(findings, query, code, logs, initial, context_str)
            if (
                second
                and "no additional bugs found" not in second.lower()
                and not is_bad_response(second)
                and not is_correct_line_flagged(second)
            ):
                combined = initial + "\n\n--- Additional Bugs Found ---\n" + second
        except Exception:
            pass

    combined = deduplicate_bugs(combined)

    critique = "Skipped"
    final = combined
    try:
        critique = critique_answer(query, code, logs, combined)
        if "correct? no" in critique.lower():
            refined = refine_answer(query, code, logs, combined, critique)
            if not is_bad_response(refined) and not is_correct_line_flagged(refined):
                final = deduplicate_bugs(refined)
    except Exception:
        critique = "Skipped — critique/refine failed"
        final = combined

    final = deduplicate_bugs(final)
    final = renumber_bugs(final, start=1)

    return {
        "ast_bugs": findings,
        "initial_answer": renumber_bugs(initial, start=1),
        "critique": critique,
        "final_answer": final,
    }