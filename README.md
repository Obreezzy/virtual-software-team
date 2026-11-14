# Virtual Software Team

**Give it one sentence. Get back a designed, coded, tested, reviewed and documented Python program.**

Virtual Software Team is a pipeline of AI agents that work like a small
software company. You describe an idea ("a command-line budget tracker"), and
the team turns it into a working project: requirements, a design, the code,
a test suite, a code review and a README. The tests are actually run, and
failures are fed back to the agents until the code passes or the retry budget
runs out.

```
python virtual_team.py "a command-line unit converter" --out ./unit_converter
```

It runs on free options: local models through [Ollama](https://ollama.com), or
any hosted OpenAI-compatible API (for example Groq).

---

## How it works

Every agent is the same thing: a **role** (a system prompt) plus a call to the
model. What makes them a team is the workflow around them and the checks that
keep their output honest.

```
Idea
 |
 v
PM -----------> short requirements list (max 6 bullets)
 |
 v
Architect ----> DESIGN.md: signatures, data structures, rules,
 |              worked examples, example session
 v
DesignReview -> reviewer checks the design against the idea
 |
 v
Verifier -----> writes a script that re-derives every worked example
 |              from the design's own rules and runs it
 |              (mismatches go back to the Architect, up to 2 rounds)
 v
Developer ----> app.py
 |
 v
Tester -------> test_app.py (unittest), built from the worked examples
 |
 v
Run the tests  <------------------------------+
 |                                            |
 |-- tests fail --> Developer fixes code      |
 |                  (or Tester fixes a broken |
 |                  test file) ---------------+
 |
 |-- tests pass --> Reviewer
                      |-- APPROVED -----------> Docs writes README.md
                      |-- CHANGES NEEDED -----> back to Developer
```

### The agents

| Agent | Job |
|---|---|
| **PM** | Turns the idea into a short requirements list for a small, single-file, standard-library-only program. Keeps the scope small. |
| **Architect** | Writes the design for `app.py`: exact function signatures, one flat lookup table, formulas, which inputs raise which errors, 5-8 worked examples, and an example session. Rejects `nan` and `inf`, and decides what empty input does. |
| **DesignReview** | Checks the design against the original idea: features nobody asked for, examples that contradict the rules, hard cases with no example, inputs that parse but crash later. Replies `OK` or lists problems. |
| **Verifier** | Independently re-implements the design's rules in a script and checks every worked example and every stated count or total. Mismatches between the rules and the examples are sent back to the Architect. |
| **Developer** | Writes the complete `app.py` following the design exactly. Also fixes the code when tests fail or the reviewer asks for changes. |
| **Tester** | Writes `test_app.py` with `unittest` from the design's worked examples, including an end-to-end test of `main()`. Tests are deterministic, use temp files, and never touch the network or your real files. |
| **Reviewer** | A strict code review for correctness, security and clarity. Replies `APPROVED` or `CHANGES NEEDED` with up to 5 problems. |
| **Docs** | Writes the final `README.md` for the generated program, using only facts that are in the code. |

### Safeguards built into the pipeline

- **Design is verified before any code is written.** The Verifier catches arithmetic mistakes and contradictions in the examples early, when they are cheap to fix.
- **A fix can never make things worse.** If a round reduces the number of passing tests, the code is reverted to the best version seen so far.
- **Fixes are sanity-checked.** A proposed fix is rejected if it is not valid Python or if it drops a function the tests use.
- **Test bugs and code bugs are routed separately.** A `NameError` or bad import inside the test file goes to the Tester, everything else goes to the Developer.
- **Repeated failures change tactics.** If a fix produces the exact same failure, the Developer is told to rewrite the failing part with a different approach.
- **Missing imports in tests are added automatically** (`sys`, `io`, `contextlib`, `unittest.mock`).
- **Optional Docker sandbox.** Set `TEAM_USE_DOCKER=1` to run the generated tests in a container with no network and 512 MB of memory.
- **Every step is committed** to a local git repository inside the output folder, so you can see how the project evolved.
- **Honest output.** If the code never passed its tests or review, the generated README starts with a warning saying so.

---

## Setup

You need Python 3.10 or newer.

```
git clone https://github.com/Obreezzy/virtual-software-team.git
cd virtual-software-team
pip install requests python-dotenv
```

Then choose where the model runs.

**Option 1: local with Ollama (free, no key)**

```
ollama pull qwen2.5-coder:7b
ollama serve
```

**Option 2: a hosted OpenAI-compatible API (for example Groq)**

Copy the example settings file and fill it in:

```
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

```
TEAM_API_BASE=https://api.groq.com/openai/v1
TEAM_API_KEY=your-key-here
TEAM_MODEL=your-model-name
```

`.env` is listed in `.gitignore`, so your key is never committed. Only
`.env.example`, which holds no secrets, is in the repository.

---

## Usage

```
python virtual_team.py "a command-line to-do list manager"
python virtual_team.py "a to-do list manager" --out ./my_project
python virtual_team.py "a unit converter" --design DESIGN.md --out ./my_project
python virtual_team.py "a password generator" --pause-after-design
```

| Option | What it does |
|---|---|
| `idea` | The idea in plain English (required). |
| `--out FOLDER` | Where to write the project (default `./team_output`). |
| `--design FILE` | Skip the PM, Architect and review. Build from a design file you wrote or edited. |
| `--pause-after-design` | Stop after the design so you can check the worked examples and edit `DESIGN.md` before any code is written. |

### What you get

The output folder contains:

| File | Contents |
|---|---|
| `app.py` | The program. |
| `test_app.py` | The unittest suite. Run it with `python -m unittest -v`. |
| `DESIGN.md` | The final design, including worked examples and an example session. |
| `README.md` | Documentation for the generated program. |
| `last_test_output.txt` | Output of the most recent test run. |
| `DESIGN_CHECK.txt` | Mismatches the Verifier found (only if there were any). |
| `REVIEW_NOTES.md` | Reviewer suggestions that could not be applied (only if that happened). |
| `.git/` | One commit per step of the build. |

---

## Configuration

All settings are environment variables. They can live in `.env`.

| Variable | Default | Meaning |
|---|---|---|
| `TEAM_MODEL` | `qwen2.5-coder:7b` | Model name. |
| `OLLAMA_URL` | `http://localhost:11434` | Address of the Ollama server. |
| `TEAM_API_BASE` | *(empty)* | Base URL of a hosted OpenAI-compatible API. If set, Ollama is not used. |
| `TEAM_API_KEY` | *(empty)* | Key for that provider. |
| `TEAM_MAX_ROUNDS` | `5` | Maximum fix/review rounds. |
| `TEAM_USE_DOCKER` | `0` | `1` runs generated tests in Docker with no network. |
| `TEAM_NUM_CTX` | Ollama default | Context window in tokens for Ollama. Set to `8192` for long designs. |
| `TEAM_MAX_TOKENS` | provider default | Maximum tokens per reply for hosted APIs. |
| `TEAM_REQUEST_LIMIT` | `6500` | Approximate maximum tokens per request to a hosted API. Longer "continue" requests are shrunk. `0` never shrinks. |
| `TEAM_REASONING_EFFORT` | *(empty)* | `low`, `medium` or `high`, for reasoning models. |
| `TEAM_DESIGN_REVIEW` | `1` | `0` turns off the DesignReview agent. |
| `TEAM_DESIGN_CHECKS` | `2` | Verifier rounds for the design. `0` turns the check off. |
| `TEAM_TIMEOUT` | `900` | Seconds of silence from the model before giving up. |

Hosted free tiers have rate and size limits. The team handles them: it waits
and retries on rate limits (HTTP 429), retries with a shorter prompt on
"request too large" (HTTP 413), and asks the model to continue when a reply is
cut off.

---

## Projects built by the team

Each idea below went through the full pipeline.

| Project | What it is |
|---|---|
| `tip_app` | Tip calculator: bill, tip percent and number of people on the command line. |
| `todo_app` | Command-line task manager that stores tasks in a JSON file. |
| `password_app` | Password tool. |
| `expenses` | Expense tracker. |
| `habit` | Habit tracker. |

The `*_design.md` files in the repository are the designs these projects were
built from. They can be fed back in with `--design`.

### Extra human-written test suites

The generated tests cover the design. To check that the agents' output holds up
in practice, some projects also have independent test suites written by hand:

- `tip_app2/test_app.py`: 27 edge cases (`inf`, `nan`, negatives, zero people, huge numbers, bad arguments, rounding). Errors must go to stderr with a non-zero exit code and no traceback.
- `todo_app2/test_todo.py`: 33 tests covering every command, bad input, a corrupted data file and timestamp format. It runs against a temporary home folder, so the real `~/.todo.json` is never touched.

Run them from inside the project folder with `python test_app.py` or
`python test_todo.py`.

---

## Testing the team itself

The goal is to find where the agents break, so ideas get harder in steps. Each
level adds something the previous one did not need.

1. **Level 1: single-function programs.** Tip calculator, unit converter.
2. **Level 2: programs with state.** To-do list with a JSON file, habit tracker.
3. **Level 3 and above:** to be added as the agents are pushed harder.

For each run, record whether the team finished with `APPROVED`, how many rounds
it needed, and which of the independent edge-case tests the generated code
failed.

---

## Limits to know about

- The team builds **small programs in one file** (`app.py`) using only the Python standard library. Larger multi-file projects are not supported yet.
- Small local models can make arithmetic mistakes. The Verifier and the test loop catch most of them, but check `DESIGN.md` yourself or use `--pause-after-design` for anything important.
- "Approved" means the tests passed and the Reviewer agreed. It does not mean the program is free of bugs. That is why the independent edge-case suites exist.
- Generated code runs on your machine during testing. Use `TEAM_USE_DOCKER=1` when you want real isolation.

---

## Security

- API keys go in `.env`, which is git-ignored. Never paste a key into code or commit it.
- If a key is ever committed, revoke it and create a new one. Deleting the file does not remove it from git history.
