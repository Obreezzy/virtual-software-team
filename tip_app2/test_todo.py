"""Test suite for todo.py.

Put this file in the same folder as todo.py and run:
    python test_todo.py

Every test runs todo.py as a subprocess with HOME/USERPROFILE pointed at a
fresh temporary folder, so your real ~/.todo.json is never touched.
"""
import json
import os
import subprocess
import sys
import tempfile

TODO = "todo.py"


class Sandbox:
    """A throwaway home directory plus a helper to run todo.py inside it."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name
        self.db = os.path.join(self.home, ".todo.json")

    def run(self, *args, stdin=""):
        env = dict(os.environ)
        env["HOME"] = self.home
        env["USERPROFILE"] = self.home
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("HOMEDRIVE", None)
        env.pop("HOMEPATH", None)
        return subprocess.run(
            [sys.executable, TODO, *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=10,
        )

    def read_db(self):
        with open(self.db, "r", encoding="utf-8") as f:
            return json.load(f)

    def close(self):
        self._tmp.cleanup()


# ---------- assertion helpers ----------

def describe(r):
    return (f"exit={r.returncode} stdout={r.stdout.strip()!r} "
            f"stderr={r.stderr.strip()!r}")


def ok(r, text=None):
    assert r.returncode == 0, f"expected success, got {describe(r)}"
    assert "Traceback" not in r.stderr, f"traceback shown: {describe(r)}"
    if text is not None:
        assert text in r.stdout, f"expected {text!r} in stdout, got {describe(r)}"


def err(r, text=None):
    assert r.returncode != 0, f"expected failure, got {describe(r)}"
    assert "Traceback" not in r.stderr, f"traceback shown: {describe(r)}"
    assert r.stderr.strip(), f"error message should go to stderr: {describe(r)}"
    assert not r.stdout.strip(), f"nothing should be on stdout: {describe(r)}"
    if text is not None:
        assert text.lower() in r.stderr.lower(), (
            f"expected {text!r} in stderr, got {describe(r)}")


# ---------- tests ----------

def test_help_no_args(s):
    ok(s.run(), "Usage")


def test_help_flags(s):
    ok(s.run("-h"), "Usage")
    ok(s.run("--help"), "Usage")


def test_list_empty_creates_file(s):
    ok(s.run("list"), "No tasks.")
    assert s.read_db() == [], "new file should contain an empty list"


def test_add_and_ids(s):
    ok(s.run("add", "Buy milk"), "Added task 1.")
    ok(s.run("add", "Walk dog"), "Added task 2.")
    tasks = s.read_db()
    assert [t["id"] for t in tasks] == [1, 2]
    assert tasks[0]["description"] == "Buy milk"
    assert tasks[0]["completed"] is False
    assert tasks[0]["created"], "created timestamp missing"


def test_add_joins_multiple_words(s):
    ok(s.run("add", "Call", "the", "plumber"), "Added task 1.")
    assert s.read_db()[0]["description"] == "Call the plumber"


def test_add_trims_whitespace(s):
    ok(s.run("add", "  padded  "), "Added task 1.")
    assert s.read_db()[0]["description"] == "padded"


def test_add_unicode(s):
    ok(s.run("add", "Café résumé"), "Added task 1.")
    assert s.read_db()[0]["description"] == "Café résumé"


def test_add_no_description(s):
    err(s.run("add"), "description")


def test_add_blank_description(s):
    err(s.run("add", "   "), "empty")
    assert s.read_db() == [], "blank task must not be saved"


def test_list_shows_tasks(s):
    s.run("add", "One")
    s.run("add", "Two")
    r = s.run("list")
    ok(r, "[ ] One")
    assert "[ ] Two" in r.stdout


def test_done_marks_task(s):
    s.run("add", "One")
    ok(s.run("done", "1"), "Marked task 1 as completed.")
    assert s.read_db()[0]["completed"] is True
    ok(s.run("list"), "[x] One")


def test_done_is_repeatable(s):
    s.run("add", "One")
    ok(s.run("done", "1"))
    ok(s.run("done", "1"))


def test_list_filters(s):
    s.run("add", "Open task")
    s.run("add", "Finished task")
    s.run("done", "2")
    pending = s.run("list", "--pending")
    ok(pending, "Open task")
    assert "Finished task" not in pending.stdout
    done = s.run("list", "--done")
    ok(done, "Finished task")
    assert "Open task" not in done.stdout
    both = s.run("list", "--all")
    ok(both, "Open task")
    assert "Finished task" in both.stdout


def test_list_filter_empty(s):
    s.run("add", "Open task")
    ok(s.run("list", "--done"), "No tasks.")


def test_done_missing_id(s):
    s.run("add", "One")
    err(s.run("done", "99"), "not found")


def test_done_bad_id(s):
    err(s.run("done", "abc"), "integer")
    err(s.run("done", "1.5"), "integer")


def test_done_wrong_arg_count(s):
    err(s.run("done"), "exactly one")
    err(s.run("done", "1", "2"), "exactly one")


def test_remove_task(s):
    s.run("add", "One")
    s.run("add", "Two")
    ok(s.run("remove", "1"), "Removed task 1.")
    assert [t["id"] for t in s.read_db()] == [2]


def test_remove_missing_and_twice(s):
    s.run("add", "One")
    err(s.run("remove", "5"), "not found")
    ok(s.run("remove", "1"))
    err(s.run("remove", "1"), "not found")


def test_remove_bad_args(s):
    err(s.run("remove"), "exactly one")
    err(s.run("remove", "x"), "integer")
    err(s.run("remove", "1", "2"), "exactly one")


def test_ids_use_max_plus_one(s):
    s.run("add", "A")
    s.run("add", "B")
    s.run("add", "C")
    s.run("remove", "2")
    ok(s.run("add", "D"), "Added task 4.")
    assert [t["id"] for t in s.read_db()] == [1, 3, 4]


def test_clear_force(s):
    s.run("add", "A")
    s.run("add", "B")
    s.run("done", "1")
    ok(s.run("clear", "--force"), "Cleared 1 completed task(s).")
    remaining = s.read_db()
    assert [t["id"] for t in remaining] == [2]


def test_clear_nothing_to_clear(s):
    s.run("add", "A")
    ok(s.run("clear", "--force"), "No completed tasks to clear.")
    assert len(s.read_db()) == 1


def test_clear_confirm_yes(s):
    s.run("add", "A")
    s.run("done", "1")
    ok(s.run("clear", stdin="y\n"), "Cleared 1")
    assert s.read_db() == []


def test_clear_confirm_no(s):
    s.run("add", "A")
    s.run("done", "1")
    ok(s.run("clear", stdin="n\n"), "No completed tasks to clear.")
    assert len(s.read_db()) == 1, "answering n must keep the task"


def test_clear_confirm_eof(s):
    s.run("add", "A")
    s.run("done", "1")
    ok(s.run("clear", stdin=""))
    assert len(s.read_db()) == 1, "EOF must count as no"


def test_unknown_command_and_options(s):
    err(s.run("frobnicate"), "unknown command")
    err(s.run("list", "--bogus"), "unknown option")
    err(s.run("clear", "--bogus"), "unknown option")


def test_corrupted_json_is_backed_up(s):
    with open(s.db, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    ok(s.run("list"), "No tasks.")
    assert s.read_db() == [], "fresh file should be an empty list"
    bak = s.db + ".bak"
    assert os.path.exists(bak), ".bak backup was not created"
    with open(bak, "r", encoding="utf-8") as f:
        assert f.read() == "{ this is not json", "backup should hold the old content"


def test_json_not_a_list_is_backed_up(s):
    with open(s.db, "w", encoding="utf-8") as f:
        json.dump({"id": 1}, f)
    ok(s.run("list"), "No tasks.")
    assert os.path.exists(s.db + ".bak"), ".bak backup was not created"


def test_data_persists_between_runs(s):
    s.run("add", "Persistent")
    s.run("done", "1")
    r = s.run("list")
    ok(r, "[x] Persistent")


def test_no_leftover_tmp_file(s):
    s.run("add", "A")
    assert not os.path.exists(s.db + ".tmp"), "temp file left behind"


# ---------- runner ----------

def main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = 0
    for name, func in tests:
        sandbox = Sandbox()
        try:
            func(sandbox)
            print(f"[PASS] {name}")
            passed += 1
        except AssertionError as exc:
            print(f"[FAIL] {name}\n        {exc}")
        except Exception as exc:  # unexpected harness error
            print(f"[ERROR] {name}\n        {type(exc).__name__}: {exc}")
        finally:
            sandbox.close()
    print(f"\n{passed}/{len(tests)} tests passed.")
    sys.exit(0 if passed == len(tests) else 1)


if __name__ == "__main__":
    main()
