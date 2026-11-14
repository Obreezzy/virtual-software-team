# Virtual Software Team

**Describe what you want in one sentence. Get back a designed, coded, tested, stress-tested, reviewed and documented Python program.**

Virtual Software Team is a pipeline of AI agents that work like a small
software company. You give it a plain-English idea, and the team decides
everything else: the requirements, the design, the code, the tests, the
handling of bad input, the review and the README. Nothing needs to be spelled
out. The finished program is run, attacked with hostile input, and sent back for
fixes until it holds up or the retry budget runs out.

```
python virtual_team.py "a bank account manager"
```

That is the whole interface. The output goes into its own folder,
`team_output/a_bank_account_manager`, so earlier projects are never overwritten.
Run it with no idea at all and it asks you what to build.

It runs on free options: local models through [Ollama](https://ollama.com), or
any hosted OpenAI-compatible API (for example Groq).

---

## How it works

Every agent is a **role** (a system prompt) plus a call to the model. All of
them start with the same short team charter, so each one knows the whole
pipeline, what its own job is, and what the finished program must guarantee:
no traceback shown to the user, no lost data, and no nonsense such as `nan` or
`inf`.

```
Idea (one sentence)
 |
 v
PM -----------> short requirements list (max 6 bullets), filling in any
 |              details the user did not give
 v
Architect ----> DESIGN.md: signatures, data structures, rules, error
 |              handling, worked examples, example session
 v
DesignReview -> checks the design against the idea
 |
 v
Verifier -----> writes a script that re-derives every worked example from
 |              the design's own rules and runs it; mismatches go back to
 |              the Architect (up to 2 rounds)
 v
Developer ----> app.py
 |
 v
Tester -------> test_app.py (unittest), built from the worked examples
 |
 v
 +--> Run the tests ----- fail --> Developer fixes the code
 |                                (or Tester fixes a broken test file)
 |        | pass
 |        v
 |    Stress test ------- crash, hang or nan --> Developer fixes the code
 |        | survives
 |        v
 |    Reviewer ---------- CHANGES NEEDED -----> Developer fixes the code
 |        | APPROVED
 +--------+ (loops back until done or out of rounds)
          v
        Docs -------> README.md
```

### The agents

| Agent | Job |
|---|---|
| **PM** | Turns the one-sentence idea into a short requirements list for a small, single-file, standard-library-only program, including how invalid input and stored data are handled. |
| **Architect** | Writes the design for `app.py`: exact signatures, one flat lookup table, formulas, which inputs raise which errors, 5-8 worked examples and an example session. Rules covered: money uses `Decimal`, `nan` and `inf` are rejected, errors go to stderr for command-line programs, input can end early, and saved data is written safely and a corrupted file is backed up. |
| **DesignReview** | Checks the design against the original idea: features nobody asked for, examples that contradict the rules, hard cases with no example, inputs that parse but crash later. Replies `OK` or lists problems. |
| **Verifier** | Independently re-implements the design's rules in a script and checks every worked example and every stated count or total. Mismatches go back to the Architect. |
| **Developer** | Writes the complete `app.py` following the design exactly, wraps `main()` so end of input and Ctrl+C end cleanly, and fixes the code when tests, the stress test or the reviewer find problems. |
| **Tester** | Writes `test_app.py` with `unittest` from the worked examples, including an end-to-end test of `main()` and a test for every invalid-input rule. Tests are deterministic, use temp files, and never touch the network or real files. |
| **Reviewer** | A strict code review. Checks in particular for tracebacks reachable from user input, float used for money, accepted `nan` or `inf`, data that could be lost or corrupted, and unhandled end of input. Replies `APPROVED` or `CHANGES NEEDED`. |
| **Docs** | Writes the final `README.md` for the generated program, using only facts that are in the code. |

### The stress test

After the tests pass, the team attacks the finished program with hostile input.
This step is plain code with no model involved, so every finding is a real
crash, not a guess. It runs `app.py` in an empty sandbox with a throwaway home
folder, so it can never touch your real files.

It tries:
- no input at all, and only blank lines
- `nan`, `inf`, `-inf`, `1e999`, `0`, negatives, text instead of numbers
- empty and whitespace-only values, a 400-digit number, accented and symbol characters
- `--help`, `1/0`, `None`, `[]` and a SQL-injection string
- every value above as an input line and as a command-line argument
- each command word it finds in the code (like `deposit` or `add`), alone and followed by each hostile value

It reports a **traceback**, a program that **hangs** past 5 seconds, and a
program that **prints `nan` or `inf` as a result**. The real traceback is sent
to the Developer, who must fix it. If the program cannot be fixed within the
round limit, the generated README starts with a warning saying so.

### Other safeguards

- **The design is verified before any code is written**, when mistakes are cheap to fix.
- **A fix can never make things worse.** If a round reduces the passing tests, the code is reverted to the best version seen.
- **Fixes are sanity-checked.** A fix is rejected if it is not valid Python or drops a function the tests use.
- **Test bugs and code bugs are routed separately.** A `NameError` inside the test file goes to the Tester, everything else goes to the Developer.
- **Repeated failures change tactics.** If a fix produces the exact same failure, the Developer is told to take a different approach.
- **Missing imports in tests are added automatically** (`sys`, `io`, `contextlib`, `unittest.mock`).
- **Optional Docker sandbox.** `TEAM_USE_DOCKER=1` runs the tests and the stress test in a container with no network and 512 MB of memory.
- **Every step is committed** to a local git repository inside the output folder.
- **Honest output.** If the program never passed, its README opens with a warning.

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
python virtual_team.py                                   (asks what to build)
python virtual_team.py "a unit converter" --out ./converter
python virtual_team.py "a password generator" --pause-after-design
python virtual_team.py "a unit converter" --design DESIGN.md
```

| Option | What it does |
|---|---|
| `idea` | The idea in plain English. If left out, the team asks for it. |
| `--out FOLDER` | Where to write the project. Default: `team_output/<name made from the idea>`, with `_2`, `_3`... added if that folder is already used. |
| `--design FILE` | Skip the PM, Architect and review. Build from a design file you wrote or edited. |
| `--pause-after-design` | Stop after the design so you can check the worked examples and edit `DESIGN.md` before any code is written. |

### What you get

| File | Contents |
|---|---|
| `app.py` | The program. |
| `test_app.py` | The unittest suite. Run it with `python -m unittest -v`. |
| `DESIGN.md` | The final design, including worked examples and an example session. |
| `README.md` | Documentation for the generated program. |
| `last_test_output.txt` | Output of the most recent test run. |
| `DESIGN_CHECK.txt` | Mismatches the Verifier found (only if there were any). |
| `REVIEW_NOTES.md` | Requested changes that could not be applied (only if that happened). |
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
| `TEAM_STRESS` | `1` | `0` turns the stress test off. |
| `TEAM_USE_DOCKER` | `0` | `1` runs generated code in Docker with no network. |
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
| `expenses_app` | Expense tracker. |
| `habit_app2` | Habit tracker. |

The `*_design.md` files in the repository are the designs these projects were
built from. They can be fed back in with `--design`.

---

## Limits to know about

- The team builds **small programs in one file** (`app.py`) using only the Python standard library. Larger multi-file projects are not supported yet.
- Small local models can make arithmetic mistakes. The Verifier and the test loop catch most of them, but check `DESIGN.md` yourself or use `--pause-after-design` for anything important.
- "Approved" means the tests passed, the stress test found nothing, and the Reviewer agreed. It does not prove the program is free of bugs.
- The stress test cannot know what a program is *supposed* to do. It finds crashes, hangs and `nan`/`inf` results, not wrong business logic.
- Generated code runs on your machine during testing. Use `TEAM_USE_DOCKER=1` when you want real isolation.

---

## Security

- API keys go in `.env`, which is git-ignored. Never paste a key into code or commit it.
- If a key is ever committed, revoke it and create a new one. Deleting the file does not remove it from git history.