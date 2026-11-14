# Habit Tracker  

A tiny command‑line habit tracker that stores daily check‑ins in a JSON file.  
All logic is in a single file **app.py** and uses only the Python standard library.

## What it does  

* Record a check‑in for a habit (`checkin`) and keep a streak of consecutive days.  
* Show the current streak and whether a check‑in is still pending for today (`status`).  
* List all known habit names (`list`).  

The data file (by default `~/.habits.json`) contains a flat dictionary, e.g.:

```json
{
  "exercise": {
    "last_date": "2023-10-05",
    "streak": 6
  },
  "meditate": {
    "last_date": "2023-10-04",
    "streak": 3
  }
}
```

## Running the program  

```bash
python app.py <command> [arguments]
```

Supported sub‑commands:

| command | description |
|---------|-------------|
| `checkin HABIT` | Record a check‑in for *HABIT*. Prints `Checked in: HABIT (streak: N)`. |
| `status`        | Show one line per habit with the current streak and whether a check‑in is pending. |
| `list`          | Print the habit names, one per line. |

All output goes to **stdout**; error messages go to **stderr** and cause the program to exit with status 1.

### Example session  

```text
# (pretend today is 2023-10-05)
$ python app.py status
No habits yet.
$ python app.py checkin exercise
Checked in: exercise (streak: 1)
$ python app.py checkin meditate
Checked in: meditate (streak: 1)
$ python app.py status
exercise      1  done
meditate      1  done
$ python app.py checkin exercise
Error: Already checked in today
```

## Running the tests  

The test suite is in **test_app.py**. Run it with the standard unittest runner:

```bash
python -m unittest test_app.py
```

All tests use a temporary JSON file and a fixed date, so they never touch the real habit file or the real clock.

## Help  

`app.py` uses `argparse`, so the built‑in help is available:

```bash
python app.py -h
```

which prints a short usage description for the three sub‑commands.