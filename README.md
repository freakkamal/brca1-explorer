# BRCA1 Evidence Explorer — Milestone 1

A small working foundation for a research backend. It provides `GET /health`
and FastAPI's interactive `/docs` page. It does not retrieve scientific data,
generate AI summaries, predict drug activity, or provide clinical advice.

## Start here on Windows

1. Extract this ZIP. Open the extracted `brca1-explorer` folder containing this README.
2. In File Explorer's address bar, type `cmd` and press Enter. This opens
   Command Prompt in the correct folder. These commands are for Command Prompt.
3. Check the Python installation from our earlier step:

```bat
py -3.13 --version
```

If that fails, stop and send the error. Install Python from
https://www.python.org/downloads/windows/ if needed. Python 3.12 is also
supported: if already installed, use `py -3.12` in the commands below.

4. Create an isolated package environment and install the dependencies:

```bat
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.prefix != sys.base_prefix)"
```

The final command should show a path inside this folder's `.venv` and `True`.
We explicitly use that interpreter, so activation and PowerShell policy changes
are unnecessary. Internet access is needed for package installation.

5. Run the acceptance tests:

```bat
.venv\Scripts\python.exe -m pytest -q
```

Expected: `3 passed`. Then start the development server:

```bat
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep that window open. Visit http://127.0.0.1:8000/health in your browser.
Expected: `{"status":"ok"}`. Visit http://127.0.0.1:8000/docs to try
`GET /health` using **Try it out**, then **Execute**. Ctrl+C stops the server.
The health endpoint checks only this service's responsiveness.
The docs interface loads JavaScript/CSS from a CDN and needs internet access;
the health endpoint and tests do not make external scientific requests.

## Save your work with Git

Install Git from https://git-scm.com/install/windows and reopen Command Prompt.
The downloaded ZIP contains source files, not a Git history. In the project folder:

```bat
git init -b main
git status
```

Before committing, set your own identity (replace both placeholder values):

```bat
git config user.name "YOUR NAME"
git config user.email "YOUR EMAIL OR GITHUB NOREPLY EMAIL"
git add .
git diff --cached --stat
git commit -m "Add milestone 1 FastAPI foundation"
```

The `.gitignore` excludes environments, credentials and future local data.
Check staged filenames before committing. No GitHub account or paid service is
needed yet. Later we can connect a private GitHub repository together.

## What each file does

| File | Purpose |
| --- | --- |
| `app/main.py` | Defines the API and typed health response |
| `tests/test_app.py` | Checks health, documentation/schema, and absent scientific route |
| `requirements.txt` | Exact tested runtime package versions |
| `requirements-dev.txt` | Exact tested development/test package versions |
| `pytest.ini` | Tells pytest where tests live |
| `.gitignore` | Prevents local environments and secrets entering Git |
| `VALIDATION.md` | Actual verification and environment limitations |

## Common problems

- `py` not recognised: install Python, then reopen Command Prompt.
- `No module named app`: run commands in the folder containing `app` and this README.
- Port 8000 busy: stop the previous server or use `--port 8001` and open that port.
- Browser cannot connect: keep the server running and check the terminal for errors.
- Package download blocked: send the exact error; do not disable certificate checks.
- `/` returns 404: expected; use `/health` or `/docs`.

## Scope and next milestone

No API keys, cloud accounts, database, AI subscription or GPU are required.
Use this as a local development prototype, not a hosted multi-user service.
The next milestone is verified BRCA1 gene/protein retrieval with source identifiers,
retrieval timestamps and explicit error handling. No biological result is included
or simulated in this starter. Stop after confirming this milestone on your computer.

Implementation references:
- https://fastapi.tiangolo.com/tutorial/first-steps/
- https://fastapi.tiangolo.com/tutorial/testing/
