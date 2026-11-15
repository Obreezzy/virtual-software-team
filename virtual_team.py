#!/usr/bin/env python3
"""
Virtual Software Team: turns an idea into a small, tested Python program.

Agents: PM -> Architect -> Developer -> Tester -> run tests
        -> fix code (re-check tests if a fix changes nothing) -> Reviewer -> Docs

Free stack: Ollama (local models) or any free OpenAI-compatible API.

Usage:
    python virtual_team.py "a command-line unit converter"
    python virtual_team.py "a to-do list manager" --out ./my_project
    python virtual_team.py "a unit converter" --design DESIGN.md --out ./my_project

Environment variables:
    TEAM_MODEL       Model name             (default: qwen2.5-coder:7b)
    OLLAMA_URL       Ollama server address  (default: http://localhost:11434)
    TEAM_MAX_ROUNDS  Max fix/review rounds  (default: 5)
    TEAM_USE_DOCKER  Set to 1 to run tests inside Docker (no network, safer)
    TEAM_NUM_CTX     Ollama context window in tokens (default: Ollama's own default)
    TEAM_MAX_TOKENS  Max tokens per reply for hosted APIs (default: provider's own limit)
    TEAM_REQUEST_LIMIT  Approx. max tokens per request to a hosted API; longer
                     'continue' requests are shrunk (default 6500, 0 = never shrink)
    TEAM_REASONING_EFFORT  low / medium / high, for reasoning models such as gpt-oss

    Optional: use a hosted OpenAI-compatible API instead of Ollama
    TEAM_API_BASE    e.g. https://api.groq.com/openai/v1
    TEAM_API_KEY     your key for that provider
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# Load settings and keys from a local .env file (never committed to git).
# This must run BEFORE the os.getenv() calls below, or .env would be ignored.
try:
    from dotenv import find_dotenv, load_dotenv
    _env_path = find_dotenv()
    load_dotenv(_env_path or None)
    DOTENV_NOTE = (f"settings file: {_env_path}" if _env_path
                   else "no .env file was found next to virtual_team.py")
except ImportError:
    DOTENV_NOTE = ("python-dotenv is NOT installed, so your .env file is being ignored "
                   "(fix: pip install python-dotenv)")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("TEAM_MODEL", "qwen2.5-coder:7b")
MAX_ROUNDS = int(os.getenv("TEAM_MAX_ROUNDS", "5"))
USE_DOCKER = os.getenv("TEAM_USE_DOCKER", "0") == "1"
API_BASE = os.getenv("TEAM_API_BASE", "").rstrip("/")
API_KEY = os.getenv("TEAM_API_KEY", "")
TEST_TIMEOUT = 30  # seconds
TIMEOUT = int(os.getenv("TEAM_TIMEOUT", "900"))  # max seconds of SILENCE from the model
MAX_TOKENS = int(os.getenv("TEAM_MAX_TOKENS", "0"))  # 0 = provider default
REQUEST_LIMIT = int(os.getenv("TEAM_REQUEST_LIMIT", "6500"))  # approx tokens; 0 = never shrink
REASONING_EFFORT = os.getenv("TEAM_REASONING_EFFORT", "")  # optional
NUM_CTX = int(os.getenv("TEAM_NUM_CTX", "0"))  # 0 = use Ollama's default context size
STRESS = os.getenv("TEAM_STRESS", "1") == "1"  # attack the finished program with hostile input
STRESS_TIMEOUT = 5    # seconds allowed per probe
STRESS_BUDGET = 90    # seconds allowed for the whole stress test
DESIGN_REVIEW = os.getenv("TEAM_DESIGN_REVIEW", "1") == "1"
DESIGN_CHECKS = int(os.getenv("TEAM_DESIGN_CHECKS", "2"))  # verify/fix rounds for the design; 0 = off

def log(who: str, msg: str) -> None:
    print(f"[{who}] {msg}", flush=True)


# --------------------------------------------------------------------------
# Agent: a role (system prompt) + a way to call the model
# --------------------------------------------------------------------------
class ApiError(RuntimeError):
    """A problem reported by the hosted API (rate limit, request too large...)."""


TEAM_CHARTER = (
    "You are one member of a virtual software team. From a single plain-English "
    "idea, the team produces a small, correct, production-quality Python program "
    "with tests and docs. The pipeline is: PM (requirements) -> Architect (design) "
    "-> DesignReview and Verifier (check the design) -> Developer (app.py) -> "
    "Tester (test_app.py) -> automatic test run and stress test -> Reviewer -> "
    "Docs (README). Each member does only their own job and trusts the others to "
    "do theirs. The user will not add detail, so make sensible decisions yourself "
    "and keep the scope small. The finished program must never show a traceback "
    "to its user, never lose data, and never print nonsense such as nan or inf."
)


class Agent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = f"{TEAM_CHARTER}\n\nYour role: {role}"
        self.last_prompt = ""

    def ask(self, prompt: str, fallbacks=()) -> str:
        """Ask the model. If a hosted API says the request is too large (HTTP 413),
        retry with each shorter fallback prompt in turn."""
        candidates = [prompt, *fallbacks]
        for i, candidate in enumerate(candidates):
            try:
                text = self._ask_once(candidate)
            except ApiError as error:
                if "413" in str(error) and i + 1 < len(candidates):
                    log(self.name, "the request is too large for the free tier; "
                                   "retrying with a shorter prompt...")
                    continue
                raise
            self.last_prompt = candidate
            return text

    def _ask_once(self, prompt: str) -> str:
        approx = (len(self.role) + len(prompt)) // 3
        log(self.name, f"working... (prompt about {approx} tokens)")
        if not API_BASE and approx > 0.9 * (NUM_CTX or 4096):
            log(self.name, "WARNING: this prompt may be longer than Ollama's context window "
                           "(its default is often 2048-4096 tokens). If so, the START of the "
                           "prompt (the instructions and design) is silently dropped. "
                           "Set TEAM_NUM_CTX=8192 to raise it (uses about 1 GB more RAM).")
        messages = [
            {"role": "system", "content": self.role},
            {"role": "user", "content": prompt},
        ]
        started = time.time()
        text = self._ask_api(messages) if API_BASE else self._ask_ollama(messages)
        log(self.name, f"done in {time.time() - started:.0f}s")
        return text

    def _ask_ollama(self, messages: list) -> str:
        """Stream the reply so a long generation never trips the timeout.
        The timeout only applies to silence between chunks, not total time."""
        parts, count = [], 0
        with requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODEL,
                "stream": True,
                "options": {"temperature": 0.2, **({"num_ctx": NUM_CTX} if NUM_CTX else {})},
                "messages": messages,
            },
            stream=True,
            timeout=(10, TIMEOUT),
        ) as resp:
            if resp.status_code == 404:
                raise ApiError(
                    f"Ollama does not have the model '{MODEL}'. Install it with "
                    f"`ollama pull {MODEL}`, or set TEAM_MODEL to a name from `ollama list`. "
                    f"If you meant to use Groq, set TEAM_API_BASE, TEAM_API_KEY and "
                    f"TEAM_MODEL in this terminal first (they only last for one terminal window)."
                )
            if resp.status_code >= 400:
                raise ApiError(f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}")
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise RuntimeError(f"Ollama error: {data['error']}")
                parts.append(data.get("message", {}).get("content", ""))
                count += 1
                if count % 100 == 0:
                    print(".", end="", flush=True)  # progress indicator
                if data.get("done"):
                    if data.get("done_reason") == "length":
                        log(self.name, "WARNING: the reply hit the output limit and may be cut off.")
                    break
        if count >= 100:
            print()
        return "".join(parts)

    def _post_api(self, body: dict) -> dict:
        for attempt in range(5):
            resp = requests.post(
                f"{API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json=body,
                timeout=TIMEOUT,
            )
            if resp.status_code == 429:
                if "per day" in resp.text or "TPD" in resp.text:
                    raise ApiError("the daily token limit for this model is used up. "
                                   "Try again later or use another model or provider. "
                                   + resp.text[:300])
                try:
                    retry_after = float(resp.headers.get("retry-after", 0))
                except ValueError:
                    retry_after = 0
                wait = int(min(max(retry_after, 15 * (attempt + 1)), 90))
                log(self.name, f"rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                raise ApiError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            return resp.json()
        raise ApiError("still rate limited after several retries")

    def _ask_api(self, messages: list) -> str:
        """If the reply hits the output limit, ask the model to continue."""
        text = ""
        for _ in range(4):
            msgs = messages
            if text:
                msgs = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": "Continue exactly where you stopped. "
                                                "Do not repeat anything and add no commentary."},
                ]
                approx = sum(len(m["content"]) for m in msgs) // 3
                if REQUEST_LIMIT and approx > REQUEST_LIMIT:
                    # Too big for a free-tier request: send only the end of the text.
                    log(self.name, "continue request would be too large; sending only the end of the text")
                    msgs = [messages[0], {"role": "user", "content":
                            "The following text was cut off. Continue it exactly where it "
                            "stops. Do not repeat anything and add no commentary.\n\n<<<\n"
                            + text[-3000:] + "\n>>>"}]
            body = {"model": MODEL, "temperature": 0.2, "messages": msgs}
            if MAX_TOKENS:
                body["max_tokens"] = MAX_TOKENS
            if REASONING_EFFORT:
                body["reasoning_effort"] = REASONING_EFFORT
            try:
                choice = self._post_api(body)["choices"][0]
            except ApiError as error:
                if text and "413" in str(error):
                    log(self.name, "WARNING: could not continue (request too large); "
                                   "keeping the partial reply.")
                    return text
                raise
            text += choice["message"].get("content") or ""
            if choice.get("finish_reason") != "length":
                return text
            log(self.name, "reply hit the output limit; asking the model to continue...")
        log(self.name, "WARNING: the reply is still cut off after continuing; "
                       "set TEAM_MAX_TOKENS higher or simplify the request.")
        return text


pm = Agent(
    "PM",
    "You are a product manager. Turn the idea into a SHORT requirements list "
    "(max 6 bullets) for a small program that fits in ONE Python file, uses "
    "only the standard library, and has no network access. Keep the scope "
    "small: fewer features done correctly beat many done badly. The user gave "
    "you only one short sentence, so fill in sensible details yourself. Include "
    "one bullet on how invalid input is handled and, if the program keeps data "
    "between runs, one bullet on how it is stored.",
)
architect = Agent(
    "Architect",
    "You are a software architect. Given requirements, write a design for a "
    "single module called app.py. List every function/class with its exact "
    "signature, inputs, outputs and behavior. For anything non-trivial, spell "
    "out the exact rule: the data structure to use (show a tiny example), the "
    "formulas, and which inputs raise which errors. Do NOT write "
    "implementations: no function bodies, only signatures and a tiny data "
    "example. Prefer plain functions and one FLAT lookup table, keyed "
    "directly by the thing being looked up and never nested by category, "
    "over class "
    "hierarchies. Finish with a section titled 'Worked examples': 5-8 lines "
    "in the form `function(args) == result`, covering every category and at "
    "least one error case. Use only well-known, exactly correct values "
    "(for example, 100 C is 212 F). Start with the trickiest case, any rule "
    "that is not a simple multiplication. Write each expected result rounded "
    "to 2 decimal places and double-check the arithmetic. Do not add features "
    "the idea did not ask for (no command-line flags or help screens). "
    "The program file is always named app.py, so any usage text or example "
    "session must say app.py. State every count or length you mention "
    "correctly (count the characters), and make sure every rule, example and "
    "session line agrees. Every error a user can trigger must be caught in "
    "main() and printed as a clean message, never a traceback. For every "
    "input the user types, think about values that parse successfully but "
    "break later and state the rule for them: for numbers parsed with "
    "float() or Decimal(), reject nan, inf and -inf (check math.isfinite or "
    "Decimal.is_finite() BEFORE any comparison) with the same 'must be a "
    "number' message; for text, decide what happens with empty or "
    "whitespace-only input; for dates, impossible calendar days. "
    "Also add an 'Example session' "
    "section: the exact lines a user types into main() and the exact lines it "
    "prints, ending with how the user quits. Keep it small and simple. "
    "Money amounts use decimal.Decimal, never float, with at most 2 decimal "
    "places. A program that takes command-line arguments prints errors to "
    "stderr and exits with a non-zero status; an interactive program prints "
    "the error and keeps running. If the input ends early (end of input or "
    "Ctrl+C) the program ends cleanly. If the program saves data, state: the "
    "file lives in the user's home folder; it is written to a temporary file "
    "and then renamed; a missing file means an empty start; a corrupted file "
    "is renamed to .bak and replaced by an empty one.",
)
design_reviewer = Agent(
    "DesignReview",
    "You are a design reviewer. Check the design against the original idea. "
    "Look for: (1) features the idea never asked for; (2) a worked example "
    "that contradicts the design's own data structure or rules (an input the "
    "parser could not accept, or different error behavior than stated); "
    "(3) hard cases of the idea that no worked example covers, such as "
    "formulas that are not simple multiplication; (3b) inputs that parse but "
    "would crash later and have no stated rule, such as nan or inf for "
    "numbers, empty text, or impossible dates; (4) a missing 'Worked "
    "examples' or 'Example session' section. If the design is sound, reply "
    "with the single word OK. Report only serious problems that would make "
    "the program give wrong results or fail its own examples; ignore style "
    "and minor edge cases. Otherwise reply with a short bullet list (max 5) "
    "of concrete problems.",
)
verifier = Agent(
    "Verifier",
    "You are a meticulous engineer who checks a software design for mistakes by "
    "re-deriving its answers from its RULES. Write ONE self-contained Python "
    "script (standard library only, no input(), no files, no network). "
    "Step 1: implement, in plain Python, every function the design's worked "
    "examples call, following ONLY the design's rules and formulas. Never bend "
    "the implementation to make an example pass: if a rule and an example "
    "disagree, follow the rule. Where a rule is random or touches the user's "
    "files, implement only the deterministic part. "
    "Step 2: after the implementation, add one check per worked-example line "
    "AND one check per claim about a count, length, sum or percentage made "
    "anywhere in the design (for instance a comment saying a string has 28 "
    "characters, or that a total is 391.34, or an example session that prints "
    "a rating for a given input). Two helpers already exist; do NOT define "
    "them: check(label, actual, expected) where actual is a zero-argument "
    "lambda or a value and expected is copied exactly as the design states it; "
    "and check_raises(label, lambda_that_should_raise, ExceptionType, "
    "expected_message_or_None). Wrap each call in its own lambda so one "
    "failure cannot stop the others. Print nothing yourself. Keep the script "
    "SHORT (about 100 lines at most): implement only the functions that the "
    "worked examples call, and write terse checks. "
    "Reply with exactly one ```python code block and nothing else.",
)
developer = Agent(
    "Developer",
    "You are a careful Python developer. Write the COMPLETE contents of app.py "
    "following the design exactly (same names and signatures). Standard "
    "library only. Keep it simple (plain functions, no needless class "
    "hierarchies) and make sure main() works end to end using the functions "
    "you write. Follow the design's data tables, formulas and input formats "
    "literally (keywords such as 'to' are part of the format) and never "
    "hard-code per-case constants that a table or formula already gives. "
    "Wrap the body of main() so that end of input (EOFError) and Ctrl+C "
    "(KeyboardInterrupt) end the program cleanly and no input can ever show a "
    "traceback. Use decimal.Decimal for money. Check math.isfinite() or "
    "Decimal.is_finite() on every parsed number before comparing it. "
    "Reject numbers beyond a sensible maximum (for money, more than 1e12) with "
    "a clean message, because values such as 1e999 are finite for Decimal but "
    "crash rounding. For money, reject more than 2 decimal places with a clear "
    "message instead of silently rounding. Never write a blanket "
    "`except Exception` that prints a vague message such as 'unexpected "
    "problem': catch only the specific exceptions you expect, so that real "
    "bugs are not hidden. When you load saved data, check the type and range of "
    "every value (a balance must be a finite, non-negative number) and treat "
    "anything else as a damaged file with a clear message. Never print Python "
    "repr text in a message (a KeyError's str() has stray quotes: use "
    "e.args[0]). An unknown menu choice or command must print a message such "
    "as 'Invalid option'. If a data file exists but cannot be read, or contains "
    "an invalid record, NEVER continue with empty data that the next save "
    "would write over it, and never silently drop a record: either stop with a "
    "clear one-line message, or first rename the file to <name>.corrupt "
    "(keeping every byte) and tell the user. Never show raw exception text such "
    "as a JSON decoder message to the user. "
    "Reply with exactly one ```python code block and nothing else.",
)
tester = Agent(
    "Tester",
    "You are a QA engineer. Write test_app.py using Python's unittest module "
    "(`import app`). Test ONLY behavior stated in the design, about 6-8 tests. "
    "Use assertAlmostEqual(..., delta=0.01) for any floating-point result. "
    "Never invent behavior the design does not state. Build your tests from "
    "the design's 'Worked examples' and copy their expected values exactly; "
    "never calculate expected values yourself. Also write one end-to-end test "
    "of main() from the design's 'Example session', using "
    "unittest.mock.patch('builtins.input', side_effect=[...]) if the program "
    "reads input (or by passing arguments to main() if it takes them) and "
    "contextlib.redirect_stdout (as a context manager; never reassign "
    "sys.stdout), and use assertIn to check that each expected output line "
    "appears; do not compare the whole output. "
    "Tests must be deterministic, must never touch the user's real files "
    "(use tempfile for any path the program reads or writes), and must not "
    "use the network. For every invalid-input rule in the design (nan, inf, "
    "empty input, zero, negative, unknown command) add a test that the program "
    "reports a clean error instead of raising an exception. "
    "Reply with exactly one ```python code block and nothing else.",
)
reviewer = Agent(
    "Reviewer",
    "You are a strict code reviewer focused on correctness, security, and "
    "clarity. If the code is acceptable, reply with the single word APPROVED. "
    "Otherwise reply with CHANGES NEEDED on the first line, followed by a "
    "short bullet list of the most important problems only (max 5). Check "
    "especially: can any user input cause a traceback; is money handled with "
    "float instead of Decimal; are nan or inf accepted; can saved data be lost "
    "or corrupted (no temporary file, no handling of a damaged file); is end "
    "of input handled; does any error go to the wrong place; does a blanket "
    "`except Exception` hide a real bug behind a vague message; are numbers "
    "beyond a sensible maximum rejected; is data loaded from a file checked "
    "for type and range; if a data file is damaged, does the program carry on "
    "with empty data that the next save would write over it, or silently drop "
    "records, or show raw exception text.",
)
docs = Agent(
    "Docs",
    "You are a technical writer. Write a concise README.md in Markdown: what "
    "the program does, how to run it, how to run the tests, and one example. "
    "Facts you must follow: the program is the single file app.py, the tests "
    "are test_app.py and run with `python -m unittest`. Do NOT invent URLs, "
    "git repositories, folders, or features that are not in the code. Every "
    "example must be something the code can actually do: check it against "
    "the code first. Use plain ASCII characters only: ordinary hyphens, "
    "straight quotes, no special dashes or emoji.",
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def extract_code(text: str) -> str:
    """Pull the largest fenced code block out of a model reply."""
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    code = max(blocks, key=len) if blocks else text
    return code.strip() + "\n"


def raised_inside_app(output: str) -> bool:
    """True if any traceback frame is in app.py itself (not test_app.py)."""
    return bool(re.search(r'File "(?:[^"]*[\\/])?app\.py"', output))


def failure_blocks(output: str) -> dict:
    """Map each failing test's name to the block of failure text for it."""
    blocks = {}
    for chunk in re.split(r"^={20,}\s*$", output, flags=re.M):
        m = re.match(r"\s*(?:FAIL|ERROR): (\w+)", chunk)
        if m:
            blocks[m.group(1)] = chunk.strip()
    return blocks


def passed_count(output: str) -> int:
    """Number of tests that passed, from unittest's output."""
    m = re.search(r"^Ran (\d+) tests?", output, re.M)
    total = int(m.group(1)) if m else 0
    return max(total - len(failure_blocks(output)), 0)


def looks_like_test_bug(block: str) -> bool:
    """True for a mistake in the test file itself: the traceback never enters
    app.py and ends in a NameError, a bad import, or a missing attribute on a
    module other than app."""
    if raised_inside_app(block) or re.search(r"from 'app'|module 'app'|named 'app'", block):
        return False
    return bool(
        re.search(r"^(?:NameError|ImportError|ModuleNotFoundError|SyntaxError|IndentationError)\b", block, re.M)
        or re.search(r"^AttributeError: module '(?!app')", block, re.M)
    )


def add_missing_imports(code: str) -> str:
    """Models often use sys, io, contextlib or unittest.mock without importing
    them. Add any missing standard-library import deterministically."""
    lines = []
    for mod in ("sys", "io", "contextlib"):
        if re.search(rf"\b{mod}\.", code) and not re.search(rf"^\s*import {mod}\b", code, re.M):
            lines.append(f"import {mod}")
    if re.search(r"\bunittest\.mock\b", code) and not re.search(
        r"^\s*(?:import unittest\.mock|from unittest import mock|from unittest\.mock import)", code, re.M
    ):
        lines.append("import unittest.mock")
    return ("\n".join(lines) + "\n" + code) if lines else code


def clean_tests(text: str) -> str:
    return add_missing_imports(extract_code(text))


def without_examples(text: str) -> str:
    """Drop the 'Worked examples' and 'Example session' sections (the tests already
    cover them). Used to shrink prompts that are too big for a free-tier request."""
    parts = re.split(r"(?m)^(?=## )", text)
    keep = [p for p in parts
            if not re.match(r"##\s*(?:\d+\.\s*)?(?:Worked examples|Example session)", p, re.I)]
    out = "".join(keep)
    if len(out) < len(text):
        out += "\n(The worked examples and example session were left out to save space; the tests cover them.)\n"
    return out


def signatures_only(code: str) -> str:
    keep = [line for line in code.splitlines()
            if re.match(r"(def |class |import |from |[A-Z_][A-Z0-9_]*\s*=)", line)]
    return "\n".join(keep) + "\n# (function bodies left out to save space)"


def merge_patch(code: str, patch: str):
    """Merge a patch (only the changed top-level functions/classes, plus any new
    imports or constants) into code. Returns the merged source, or None if the
    patch cannot be understood. A reply that is really the whole file also works."""
    try:
        old_tree, new_tree = ast.parse(code), ast.parse(patch)
    except SyntaxError:
        return None
    defs = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    patch_nodes = [n for n in new_tree.body
                   if isinstance(n, defs + (ast.Import, ast.ImportFrom, ast.Assign))]
    if not any(isinstance(n, defs) for n in patch_nodes):
        return None
    old_defs = {n.name for n in old_tree.body if isinstance(n, defs)}
    patch_defs = {n.name for n in patch_nodes if isinstance(n, defs)}
    has_guard = any(isinstance(n, ast.If) and "__name__" in ast.dump(n.test) for n in new_tree.body)
    if has_guard and len(patch_defs & old_defs) >= 0.8 * len(old_defs):
        return patch  # the model sent the whole file; use it as it is

    lines = code.splitlines()
    patch_lines = patch.splitlines()

    def span(node, source_lines):
        first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        return first - 1, node.end_lineno  # slice bounds

    def segment(node):
        a, b = span(node, patch_lines)
        return patch_lines[a:b]

    def target_names(node):
        return {t.id for t in node.targets if isinstance(t, ast.Name)}

    replacements, additions, new_imports = [], [], []
    old_imports = {ast.dump(n) for n in old_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    for node in patch_nodes:
        if isinstance(node, defs):
            match = next((o for o in old_tree.body if isinstance(o, defs) and o.name == node.name), None)
            if match is not None:
                a, b = span(match, lines)
                replacements.append((a, b, segment(node)))
            else:
                additions.append(segment(node))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if ast.dump(node) not in old_imports:
                new_imports.append(segment(node))
        else:  # a module-level constant
            match = next((o for o in old_tree.body if isinstance(o, ast.Assign)
                          and target_names(o) & target_names(node)), None)
            if match is not None:
                a, b = span(match, lines)
                replacements.append((a, b, segment(node)))
            else:
                new_imports.append(segment(node))
    for a, b, new in sorted(replacements, key=lambda r: -r[0]):
        lines[a:b] = new
    if additions:
        guard = next((i for i, l in enumerate(lines) if l.startswith("if __name__")), len(lines))
        block = []
        for add in additions:
            block += ["", ""] + add
        lines[guard:guard] = block + ([""] if guard < len(lines) else [])
    if new_imports:
        last_import = max([n.end_lineno for n in ast.parse("\n".join(lines)).body
                           if isinstance(n, (ast.Import, ast.ImportFrom))] or [0])
        flat = [l for seg in new_imports for l in seg]
        lines[last_import:last_import] = flat
    merged = "\n".join(lines) + "\n"
    try:
        ast.parse(merged)
    except SyntaxError:
        return None
    return merged


def fix_prompts(design: str, code: str, test_code: str, feedback: str) -> list:
    """The full fix prompt first, then progressively shorter versions that are
    tried only if the hosted API says the request is too large."""
    def make(d, t, f):
        return (
            f"Design:\n{d}\n\nCurrent app.py:\n```python\n{code}```\n\n"
            f"Tests (test_app.py):\n```python\n{t}```\n\n"
            f"{f}\n\nFirst, in 2-3 sentences outside any code block, "
            f"trace the first failing test step by step through app.py and "
            f"name the exact line where it goes wrong. Then return ONLY the "
            f"top-level functions or classes you changed or added, each one "
            f"COMPLETE, in ONE python code block (add any new import lines or "
            f"module-level constants too). Do NOT repeat functions you did not "
            f"change and do not return the whole file."
        )
    short = without_examples(design)
    return [
        make(design, test_code, feedback),
        make(short, test_code, feedback),
        make(short, "(left out to save space)", feedback[-2500:]),
        make("(left out to save space; the tests and the failure output below show "
             "what is required)", "(left out to save space)", feedback[-2500:]),
        make("(left out)", "(left out)", feedback[-1200:]),
    ]


def defined_names(code: str):
    """Top-level function/class/variable names in code, or None on a syntax error."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def fix_problem(old_code: str, new_code: str, test_code: str):
    """Describe what is wrong with a proposed fix, or return None if it looks sane."""
    new_names = defined_names(new_code)
    if new_names is None:
        return "it is not valid Python (syntax error)"
    old_names = defined_names(old_code) or set()
    used = set(re.findall(r"\bapp\.(\w+)", test_code))
    for imported in re.findall(r"from app import ([\w, ]+)", test_code):
        used.update(n.strip() for n in imported.split(","))
    lost = sorted((old_names & used) - new_names)
    if lost:
        return "it lost these names that the tests use: " + ", ".join(lost)
    return None


def run_tests(workdir: Path) -> tuple[bool, str]:
    """Run the unittest suite. Use Docker for real isolation if enabled."""
    if USE_DOCKER:
        cmd = [
            "docker", "run", "--rm", "--network", "none", "--memory", "512m",
            "-v", f"{workdir.resolve()}:/work", "-w", "/work",
            "python:3.12-slim", "python", "-B", "-m", "unittest", "-v",
        ]
    else:
        cmd = [sys.executable, "-B", "-m", "unittest", "-v"]
    try:
        p = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=TEST_TIMEOUT,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        output = (p.stdout + p.stderr)[-20000:]
        return p.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Tests timed out after {TEST_TIMEOUT}s (infinite loop?)."


# --------------------------------------------------------------------------
# Stress test: attack the finished program with hostile input. No model is
# involved, so every finding is a real crash, hang or nonsense result.
# --------------------------------------------------------------------------
HOSTILE_VALUES = [
    "nan", "inf", "-inf", "1e999", "-1", "0", "0.0", "abc", "", "   ",
    "9" * 400, "café ☃", "--help", "1/0", "None", "[]", "' OR 1=1 --",
]
QUIT_WORDS = "\nquit\nexit\nq\n"
NOT_A_COMMAND = {"true", "false", "none", "yes", "no", "utf-8"}


def command_words(code: str, limit: int = 15) -> list:
    """Guess the program's command words (like deposit or add) from its source,
    by looking at what strings it compares input against."""
    word = r'["\']([A-Za-z][\w-]{1,14})["\']'
    found = []
    found += re.findall(r'(?:==|!=)\s*' + word, code)
    found += re.findall(word + r'\s*(?:==|!=)', code)
    found += re.findall(word + r'\s*:\s*[A-Za-z_]\w*\s*[,}]', code)  # {"add": cmd_add}
    found += re.findall(r'add_parser\(\s*' + word, code)
    for group in re.findall(r'\bin\s*[(\[{]([^)\]}]{0,200})[)\]}]', code):
        found += re.findall(word, group)
    seen, out = set(), []
    for w in found:
        if w.lower() not in seen and w.lower() not in NOT_A_COMMAND:
            seen.add(w.lower())
            out.append(w)
    return out[:limit]


def _probe(sandbox: Path, args: list, stdin_text: str):
    """Run app.py once in an empty sandbox with a throwaway home folder, so the
    program can never touch the user's real files. Returns the finished process,
    or None if it timed out."""
    if USE_DOCKER:
        cmd = ["docker", "run", "--rm", "-i", "--network", "none", "--memory", "512m",
               "-v", f"{sandbox.resolve()}:/work", "-w", "/work",
               "python:3.12-slim", "python", "-B", "app.py", *args]
    else:
        cmd = [sys.executable, "-B", "app.py", *args]
    import shutil
    for item in sandbox.iterdir():  # every probe starts from a clean slate
        if item.name != "app.py":
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink()
                except OSError:
                    pass
    home = str(sandbox / "_home")
    os.makedirs(home, exist_ok=True)
    try:
        return subprocess.run(
            cmd, cwd=sandbox, input=stdin_text, capture_output=True, text=True,
            timeout=STRESS_TIMEOUT, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
                 "HOME": home, "USERPROFILE": home},
        )
    except subprocess.TimeoutExpired:
        return None


def stress_test(workdir: Path) -> list:
    """Return a list of problems found (empty = the program survived)."""
    import shutil
    import tempfile
    app = workdir / "app.py"
    if not app.exists():
        return []
    code = app.read_text(encoding="utf-8", errors="replace")

    probes = [("no input at all (the input ends immediately)", [], ""),
              ("only blank lines", [], "\n  \n\t\n")]
    for v in HOSTILE_VALUES:
        probes.append((f"the input line {v[:30]!r}", [], v + QUIT_WORDS))
        probes.append((f"the command-line argument {v[:30]!r}", [v], ""))
    # Menu programs ask for a number, then a name, then an amount. Create an
    # account first, then answer each menu option's prompts with a hostile value.
    for v in HOSTILE_VALUES:
        steps = "".join(f"{n}\nAcct\n{v}\n{v}\n" for n in "12345")
        probes.append((f"menu options 1-5 answered with 'Acct' and then {v[:30]!r}",
                       [], "1\nAcct\n10\n" + steps + QUIT_WORDS))
    for w in command_words(code):
        lines = [w] + [f"{w} {v}" for v in HOSTILE_VALUES]
        probes.append((f"the commands {w!r} followed by hostile values", [], "\n".join(lines) + QUIT_WORDS))
        for v in ("nan", "abc", "-1"):
            probes.append((f"the arguments {w} {v}", [w, v], ""))
        probes.append((f"the argument {w!r} alone", [w], ""))

    # nan and inf can only appear if the program parses numbers with float/Decimal
    parses_numbers = bool(re.search(r"\b(?:float|Decimal)\s*\(", code))
    findings, seen = [], set()
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        shutil.copy(app, sandbox / "app.py")
        for label, args, stdin_text in probes:
            if len(findings) >= 5 or time.time() - started > STRESS_BUDGET:
                break
            p = _probe(sandbox, args, stdin_text)
            if p is None:
                key = ("hang",)
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        f"Given {label}, app.py did not finish within {STRESS_TIMEOUT} seconds "
                        f"(an infinite loop, or it keeps waiting after the input has ended).")
                continue
            text = (p.stderr or "") + (p.stdout or "")
            if "Traceback (most recent call last)" in text:
                err = p.stderr if "Traceback" in p.stderr else p.stdout
                lines = err.strip().splitlines()
                frames = re.findall(r'File ".*?app\.py", line (\d+)', err)
                key = (frames[-1] if frames else "", lines[-1].split(":")[0] if lines else "")
                if key not in seen:
                    seen.add(key)
                    findings.append(f"Given {label}, app.py crashed with a traceback:\n"
                                    + "\n".join(lines[-4:]))
                continue
            vague = re.search(r"(?i)unexpected (?:problem|error)|something went wrong|"
                              r"internal error|please restart|unhandled|an error occurred", text)
            if vague:
                key = ("vague", vague.group(0).lower())
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        f"Given {label}, app.py printed the vague message {vague.group(0)!r}. "
                        f"A blanket `except Exception` is hiding a real bug. Find which "
                        f"exception is raised (for example a Decimal InvalidOperation from a "
                        f"huge number such as 1e999, or a wrongly typed value loaded from the "
                        f"data file), remove the blanket handler and handle that case with a "
                        f"specific, clear message.")
                continue
            for line in (p.stdout.splitlines() if parses_numbers else []):
                if re.search(r"(?i)\b(error|invalid|must|not a|cannot|unknown|usage|unrecognized|expected)", line):
                    continue
                if re.search(r"(?<![\w.'\"])-?(?:nan|inf|infinity)(?![\w'\"])", line, re.I):
                    key = ("nan", line.strip()[:20])
                    if key not in seen:
                        seen.add(key)
                        findings.append(f"Given {label}, app.py printed {line.strip()[:80]!r} "
                                        f"as if it were a normal result (nan or inf was accepted).")
                    break
    return findings


def git_commit(workdir: Path, message: str) -> None:
    try:
        if not (workdir / ".git").exists():
            # If the output folder is already inside another git repository (for
            # example your main project folder), do not create a nested repository
            # there: it would stop the parent repo from tracking these files.
            inside = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"], cwd=workdir,
                capture_output=True, text=True)
            if inside.returncode == 0 and inside.stdout.strip() == "true":
                return
            subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=workdir, check=True)
        subprocess.run(
            ["git", "-c", "user.name=AI Team", "-c", "user.email=team@local",
             "commit", "-q", "-m", message],
            cwd=workdir, check=True, stdout=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # git is optional


# --------------------------------------------------------------------------
# The workflow
# --------------------------------------------------------------------------
DESIGN_CHAR_MAP = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...",
    "\u00a0": " ", "\u202f": " ", "\u2003": " ", "\u2002": " ", "\u2009": " ",
    "\u200b": "", "\ufe0f": "", "\u20e3": "",
    "\u2022": "-", "\u2192": "->", "\u2190": "<-", "\u2260": "!=",
    "\u2264": "<=", "\u2265": ">=", "\u00d7": "x",
}


def clean_design(text: str) -> str:
    """Replace special dashes, quotes and emoji marks with plain ASCII. A single
    non-breaking hyphen copied into code or a message can break the program."""
    for bad, good in DESIGN_CHAR_MAP.items():
        text = text.replace(bad, good)
    return text


def design_warnings(text: str) -> list:
    problems = []
    for heading in ("Worked examples", "Example session"):
        if heading.lower() not in text.lower():
            problems.append(f"it has no '{heading}' section")
    if text.count("```") % 2:
        problems.append("it ends inside an unclosed code block (the design may be cut off)")
    odd = sorted({c for c in text if ord(c) > 127})
    if odd:
        problems.append("it still contains non-ASCII characters: " + " ".join(odd[:10]))
    return problems


CHECK_HELPERS = '''\
def check(label, actual, expected):
    try:
        got = actual() if callable(actual) else actual
    except Exception as e:
        print(f"MISMATCH {label}: the rules raise {type(e).__name__}: {e}")
        return
    try:
        if isinstance(got, float) or isinstance(expected, float):
            ok = abs(float(got) - float(expected)) <= 0.006
        else:
            ok = got == expected
    except Exception:
        ok = got == expected
    print(("OK " if ok else "MISMATCH ") + f"{label}: design says {expected!r}, rules give {got!r}")


def check_raises(label, func, exc, message=None):
    try:
        func()
    except exc as e:
        if message is not None and str(e) != message:
            print(f"MISMATCH {label}: design says message {message!r}, rules give {str(e)!r}")
        else:
            print(f"OK {label}")
    except Exception as e:
        print(f"MISMATCH {label}: design says {exc.__name__}, rules raise {type(e).__name__}: {e}")
    else:
        print(f"MISMATCH {label}: design says {exc.__name__} is raised, but the rules do not raise")

'''


def run_design_check(design: str, idea: str, outdir: Path):
    """Have the Verifier re-derive the design's examples from its rules, run that
    script, and return a list of mismatch lines (empty = consistent) or None if
    the check could not be run."""
    prompt = f"Original idea: {idea}\n\nDesign:\n{design}"
    error = ""
    for attempt in range(2):
        try:
            reply = verifier.ask(prompt if not error else
                                 f"{prompt}\n\nYour previous script failed to run:\n{error}\n"
                                 f"Return the corrected full script.")
        except (ApiError, requests.RequestException) as exc:
            log("DesignCheck", f"skipped (could not reach the model: {str(exc)[:120]})")
            return None
        script = outdir / "_design_check.py"
        script.write_text(CHECK_HELPERS + "\n" + extract_code(reply), encoding="utf-8")
        try:
            p = subprocess.run(
                [sys.executable, "-I", "-B", str(script.resolve())], cwd=outdir, capture_output=True,
                text=True, timeout=20, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            )
        except subprocess.TimeoutExpired:
            error = "The script ran for more than 20 seconds (infinite loop?)."
            continue
        lines = [l for l in p.stdout.splitlines() if l.startswith(("OK ", "MISMATCH "))]
        if p.returncode != 0 or not lines:
            error = (p.stderr or "It printed no OK/MISMATCH lines.")[-800:]
            continue
        return [l for l in lines if l.startswith("MISMATCH")]
    log("DesignCheck", "skipped (the verification script would not run)")
    return None


def build(idea: str, outdir: Path, pause: bool = False, design_file: str = "") -> bool:
    outdir.mkdir(parents=True, exist_ok=True)

    if design_file:
        design = Path(design_file).read_text(encoding="utf-8")
        requirements = design  # the design already says what the program must do
        log("System", f"Using the design in {design_file} (skipping PM, Architect and review)")
        (outdir / "DESIGN.md").write_text(design, encoding="utf-8")
    else:
        requirements = pm.ask(f"Idea: {idea}")
        design = architect.ask(f"Original idea: {idea}\n\nRequirements:\n{requirements}")
        (outdir / "DESIGN.md").write_text(design, encoding="utf-8")  # keep the draft even if a later step fails
        critique = "OK"
        if DESIGN_REVIEW:
            critique = design_reviewer.ask(
                f"Original idea: {idea}\n\nRequirements:\n{requirements}\n\nDesign:\n{design}"
            )
        if not re.fullmatch(r"OK\W*", critique.strip(), re.I):
            log("DesignReview", "problems found: " + " ".join(critique.split())[:150])
            try:
                design = architect.ask(
                    f"Original idea: {idea}\n\nRequirements:\n{requirements}\n\n"
                    f"Your previous design:\n{design}\n\nA reviewer found these problems:\n"
                    f"{critique}\n\nReturn the full corrected design."
                )
            except (ApiError, requests.RequestException) as error:
                log("DesignReview", f"could not rewrite the design ({str(error)[:150]}). "
                                    f"Keeping the first design; check it yourself.")
        design = clean_design(design)
        for round_no in range(1, DESIGN_CHECKS + 1):
            mismatches = run_design_check(design, idea, outdir)
            if mismatches is None:
                break
            if not mismatches:
                log("DesignCheck", "every worked example and count matches the rules")
                break
            log("DesignCheck", f"round {round_no}: {len(mismatches)} mismatch(es) between "
                               f"the rules and the examples:")
            for line in mismatches[:6]:
                log("DesignCheck", "  " + line[:160])
            (outdir / "DESIGN_CHECK.txt").write_text("\n".join(mismatches), encoding="utf-8")
            try:
                design = clean_design(architect.ask(
                    f"Original idea: {idea}\n\nRequirements:\n{requirements}\n\n"
                    f"Your design:\n{design}\n\nAn independent script re-derived the answers "
                    f"from your rules and found these mismatches:\n" + "\n".join(mismatches) +
                    "\n\nFor each mismatch decide whether the rule or the example is wrong "
                    "and fix the design so that the rules, the worked examples, the "
                    "example session and every stated count agree. Recompute each number. "
                    "Return the full corrected design."
                ))
            except (ApiError, requests.RequestException) as exc:
                log("DesignCheck", f"could not rewrite the design ({str(exc)[:120]}); "
                                   f"keeping it. Check DESIGN.md yourself.")
                break
        else:
            if DESIGN_CHECKS:
                final = run_design_check(design, idea, outdir)
                if final:
                    log("DesignCheck", f"WARNING: {len(final)} mismatch(es) remain after "
                                       f"{DESIGN_CHECKS} fix round(s); see DESIGN.md")
        (outdir / "DESIGN.md").write_text(design, encoding="utf-8")
        if pause:
            print(f"\n[System] Design saved to {outdir / 'DESIGN.md'}")
            print("[System] Check the worked examples with a calculator and fix any "
                  "mistakes in that file, then save it.")
            input("[System] Press Enter to continue (Ctrl+C to stop)... ")
            design = (outdir / "DESIGN.md").read_text(encoding="utf-8")

    design = clean_design(design)
    (outdir / "DESIGN.md").write_text(design, encoding="utf-8")
    for problem in design_warnings(design):
        log("DesignCheck", f"WARNING: {problem}")
    if design_file and DESIGN_CHECKS:
        found = run_design_check(design, idea, outdir)
        if found:
            log("DesignCheck", f"WARNING: {len(found)} mismatch(es) in your design file:")
            for line in found[:6]:
                log("DesignCheck", "  " + line[:160])
        elif found is not None:
            log("DesignCheck", "every worked example and count matches the rules")

    code = extract_code(developer.ask(f"Original idea: {idea}\n\nDesign:\n{design}"))
    (outdir / "app.py").write_text(code, encoding="utf-8")
    test_code = clean_tests(
        tester.ask(
            f"Original idea: {idea}\n\nDesign:\n{design}\n\nCurrent app.py:\n```python\n{code}```",
            fallbacks=[
                f"Original idea: {idea}\n\nDesign:\n{design}\n\n"
                f"Current app.py (signatures only):\n```python\n{signatures_only(code)}\n```"
            ],
        )
    )
    (outdir / "test_app.py").write_text(test_code, encoding="utf-8")
    git_commit(outdir, "Initial version")

    approved = False
    review_skipped = False
    last_stress = []  # stress-test problems found in the latest round
    last_output = ""
    best = None  # (tests passing, code, test_code) for the best version seen so far
    for rnd in range(1, MAX_ROUNDS + 1):
        log("System", f"Round {rnd}/{MAX_ROUNDS}: running tests")
        ok, output = run_tests(outdir)
        warning = ""
        if not ok:
            score = passed_count(output)
            # A "fix" must never leave things worse than the best version seen so
            # far (compared only while the test file is unchanged).
            if best and best[2] == test_code and score < best[0] and code != best[1]:
                log("System", f"The last change made things worse ({best[0]} -> {score} "
                              f"tests passing); reverting to the best version.")
                warning = (
                    f"\n\nWARNING: your previous attempt reduced the passing tests from "
                    f"{best[0]} to {score} and was reverted. Try a different approach."
                )
                code = best[1]
                (outdir / "app.py").write_text(code, encoding="utf-8")
                ok, output = run_tests(outdir)
                score = passed_count(output)
            if best is None or best[2] != test_code or score > best[0]:
                best = (score, code, test_code)
        (outdir / "last_test_output.txt").write_text(output, encoding="utf-8")

        fix_code, fix_tests = True, False
        test_names, blocks = set(), {}
        if ok:
            best = (passed_count(output), code, test_code)
            last_stress = stress_test(outdir) if STRESS else []
            if last_stress:
                log("System", f"Tests passed, but the stress test found {len(last_stress)} "
                              f"problem(s) with hostile input:")
                for line in last_stress:
                    log("Stress", line.splitlines()[0][:160])
                verdict = "\n".join(last_stress)
                code_feedback = (
                    "The tests pass, but an automatic stress test fed hostile input to "
                    "app.py and found these real problems:\n\n" + verdict +
                    "\n\nFix every one. Validate input before using it (reject nan, inf, "
                    "empty and malformed values with a clean message), handle end of input, "
                    "and make sure no input can ever show a traceback or hang the program. "
                    "Keep every function the tests use."
                )
            else:
                log("System", "Tests" + (" and stress test" if STRESS else "") +
                              " passed. Sending to review.")
                verdict = reviewer.ask(f"```python\n{code}```")
                if verdict.strip().upper().startswith("APPROVED"):
                    approved = True
                    break
                code_feedback = f"The reviewer requested changes:\n{verdict}"
        else:
            last_stress = []
            blocks = failure_blocks(output)
            # Mistakes inside the test file itself (missing import, undefined name)
            # go to the Tester. Everything else goes to the Developer.
            test_names = {n for n, t in blocks.items() if looks_like_test_bug(t)}
            code_names = set(blocks) - test_names
            fix_tests = bool(test_names)
            fix_code = bool(code_names) or not fix_tests
            log("System", f"Tests failed: {len(blocks)} failing | "
                          f"{len(test_names)} test-file mistakes")
            shown = [blocks[n][-800:] for n in sorted(code_names)]
            code_feedback = "The tests failed with this output:\n" + (
                "\n\n".join(shown) if shown else output[-3000:]
            ) + warning
            if output == last_output:
                code_feedback += (
                    "\n\nWARNING: your previous fix produced the exact same failure. "
                    "Do not make a tiny edit. Re-read the design and rewrite the "
                    "failing part with a different approach."
                )
            last_output = output

        if rnd == MAX_ROUNDS:
            break  # out of retries; keep the latest versions

        if fix_tests:
            names = ", ".join(sorted(test_names))
            evidence = "\n\n".join(blocks[n][-800:] for n in sorted(test_names))
            def tester_fix_prompt(d, c, t):
                return (
                    f"Design:\n{d}\n\napp.py:\n```python\n{c}```\n\n"
                    f"Current test_app.py:\n```python\n{t}```\n\n"
                    f"These tests need attention: {names}\n\n"
                    f"Their failure output:\n{evidence}\n\n"
                    f"If the failure is a mistake in the test file itself (a missing "
                    f"import, an undefined name, wrong use of unittest.mock or "
                    f"sys.stdout), fix the test file. Do not change any expected "
                    f"values. Return the full test_app.py."
                )
            try:
                test_code = clean_tests(
                    tester.ask(
                        tester_fix_prompt(design, code, test_code),
                        fallbacks=[
                            tester_fix_prompt(without_examples(design), signatures_only(code), test_code),
                            tester_fix_prompt("(omitted to save space)", signatures_only(code), test_code),
                        ],
                    )
                )
            except ApiError as error:
                if "413" not in str(error):
                    raise
                log("System", "The test-file fix does not fit the free tier's request size; "
                              "keeping the current tests and fixing the code instead.")
            (outdir / "test_app.py").write_text(test_code, encoding="utf-8")
            git_commit(outdir, f"Fix tests, round {rnd}")

        if fix_code:
            prompts = fix_prompts(design, code, test_code, code_feedback)
            try:
                reply_code = extract_code(developer.ask(prompts[0], fallbacks=prompts[1:]))
                new_code = merge_patch(code, reply_code) or reply_code
            except ApiError as error:
                if ok and "413" in str(error):
                    # The tests already pass; only the reviewer's suggestions do not fit the
                    # free tier's request size. Keep the working code and save the notes.
                    (outdir / "REVIEW_NOTES.md").write_text(
                        "# Requested changes (not applied)\n\n" + verdict + "\n",
                        encoding="utf-8")
                    log("System", "The reviewer's changes do not fit the free tier's request size; "
                                  "keeping the current code (all tests pass). Notes: REVIEW_NOTES.md")
                    review_skipped = True
                    break
                if "413" in str(error):
                    # Even the shortest prompt is too big for the free tier. Stop fixing,
                    # keep the best code so far and still write the README and notes.
                    log("System", "Even the shortest fix request is too large for the free tier; "
                                  "stopping here with the current code. See last_test_output.txt.")
                    break
                raise
            problem = fix_problem(code, new_code, test_code)
            if problem:
                log("System", f"Rejected the fix: {problem}. Asking again.")
                try:
                    retry_code = extract_code(
                        developer.ask(
                            developer.last_prompt + f"\n\nYour previous reply was rejected because "
                            f"{problem}. Return ONLY the changed top-level functions, each one "
                            f"COMPLETE and valid Python, in one code block."
                        )
                    )
                    new_code = merge_patch(code, retry_code) or retry_code
                    problem = fix_problem(code, new_code, test_code)
                except ApiError as error:
                    if "413" not in str(error):
                        raise
                    problem = "the retry did not fit the free tier's request size"
            if problem:
                log("System", f"Rejected again ({problem}); keeping the previous code.")
            else:
                code = new_code
            (outdir / "app.py").write_text(code, encoding="utf-8")
            git_commit(outdir, f"Fix code, round {rnd}")

    readme = docs.ask(
        f"Requirements:\n{requirements}\n\napp.py:\n```python\n{code}```",
        fallbacks=[
            f"Requirements:\n{without_examples(requirements)}\n\napp.py:\n```python\n{code}```",
            f"Requirements:\n{without_examples(requirements)}\n\napp.py (signatures only):\n"
            f"```python\n{signatures_only(code)}\n```",
        ],
    )
    readme = clean_design(readme)
    if review_skipped:
        readme = (
            "> **Note:** all tests pass, but the reviewer's requested changes could not be "
            "applied (see REVIEW_NOTES.md).\n\n"
        ) + readme
    elif not approved:
        why = ("its stress test (some hostile input still causes problems)"
               if last_stress else "all of its tests or the review")
        readme = (
            f"> **Warning:** this code did not pass {why}. "
            "See last_test_output.txt. Parts of this README may be inaccurate.\n\n"
        ) + readme
    (outdir / "README.md").write_text(readme, encoding="utf-8")
    git_commit(outdir, "Add README" if approved else "Add README (unresolved issues)")

    if approved:
        log("System", f"Done. Output in {outdir} (passed tests and review).")
    elif review_skipped:
        log("System", f"Done. Output in {outdir}. All tests pass; the reviewer's changes were NOT "
                      f"applied (see REVIEW_NOTES.md).")
    else:
        log("System", f"Done, but NOT fully resolved. See {outdir / 'last_test_output.txt'}")
    return approved


def main() -> None:
    try:  # Windows consoles often cannot print every character a model writes
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="Virtual software team")
    parser.add_argument("idea", nargs="?", default="",
                        help='e.g. "a command-line budget tracker" (asked for if left out)')
    parser.add_argument("--out", default="",
                        help="output folder (default: team_output/<name made from the idea>)")
    parser.add_argument("--pause-after-design", action="store_true",
                        help="stop after the design so you can check and edit DESIGN.md")
    parser.add_argument("--design", default="",
                        help="use this design file instead of generating one")
    args = parser.parse_args()

    idea = args.idea.strip()
    if not idea:
        try:
            idea = input("What should the team build? ").strip()
        except EOFError:
            idea = ""
    if not idea:
        sys.exit("No idea given. Example: python virtual_team.py \"a bank account manager\"")
    if args.out:
        out_dir = Path(args.out)
    else:  # its own folder next to the other projects, e.g. bank_account_manager_app
        slug = re.sub(r"[^a-z0-9]+", "_", idea.lower()).strip("_")
        slug = re.sub(r"^(?:a|an|the)_", "", slug)[:30].strip("_") or "project"
        out_dir, n = Path(f"{slug}_app"), 2
        while out_dir.exists() and any(out_dir.iterdir()):  # never overwrite an earlier project
            out_dir, n = Path(f"{slug}_app{n}"), n + 1
    args.out = str(out_dir)

    where = API_BASE or OLLAMA_URL
    log("System", f"Model: {MODEL} via {where} | max rounds: {MAX_ROUNDS}")
    if not API_BASE:
        log("System", "NOTE: TEAM_API_BASE is not set, so this run uses LOCAL Ollama (slow on "
                      "8 GB of RAM). To use Groq, set TEAM_API_BASE, TEAM_API_KEY and TEAM_MODEL "
                      "in your .env file (or in this terminal). " + DOTENV_NOTE)
    try:
        build(idea, out_dir, args.pause_after_design, args.design)
    except ApiError as error:
        sys.exit(f"API error: {error}\nFiles written so far are in {args.out}.")
    except requests.ReadTimeout:
        sys.exit(
            f"The model was silent for {TIMEOUT}s. Your PC may be out of memory: "
            f"close other apps, try a smaller model, or raise TEAM_TIMEOUT. "
            f"Files written so far are in {args.out}."
        )
    except requests.ConnectionError:
        sys.exit(f"Cannot reach {where}. Is Ollama running? (ollama serve)")


if __name__ == "__main__":
    main()