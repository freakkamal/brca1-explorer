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

## Milestone 2: BRCA1 identity retrieval

Implemented:
- GET /health: service health check.
- GET /proteins/brca1: human BRCA1 protein identity from UniProt,
  accession P38398.
- GET /genes/brca1: human BRCA1 gene identity from NCBI Gene,
  gene ID 672.
- Validation of source identifiers, gene symbol and taxonomy ID.
- Retrieval timestamps, source URLs and response SHA-256 hashes.
- Explicit HTTP 502 responses when source retrieval fails.

Validation:
- 23 automated tests passed on Windows.
- Both evidence endpoints returned HTTP 200 in manual live checks.
- Automated source-retrieval tests use mocked responses.

Current limitations:
- Raw source responses are not yet stored.
- PubMed retrieval and AI summaries are not yet implemented.
- This research prototype is not for clinical decisions.
## Milestone 3: PubMed literature retrieval

Implemented:
- GET /literature/brca1 retrieves up to 10 unique PubMed records.
- Searches BRCA1[Title/Abstract], sorted by relevance.
- Returns PMIDs, titles, available abstracts and PubMed links.
- Preserves structured abstract labels and text within XML tags.
- Keeps articles without abstracts, using abstract: null.
- Includes separate search and fetch URLs, timestamps and hashes.
- Returns HTTP 502 when source retrieval fails.

Validation:
- 40 automated tests passed on Windows.
- Live retrieval returned 10 unique articles with abstracts.
- Tests cover duplicate identifiers, missing abstracts, record order,
  malformed/incomplete responses and endpoint success/failure.

Current limitations:
- Search ranking does not establish scientific evidence quality.
- Results are not restricted to human studies.
- Raw source responses and evidence bundles are not yet saved.
- AI summaries are not yet implemented.
- This research prototype is not for clinical decisions.


## Milestone 4: Saved evidence bundles

Implemented:
- Saves validated source-response bytes under data/raw/.
- Names raw files using their SHA-256 checksums.
- Reuses identical responses and detects corrupted existing files.
- Creates a combined gene, protein and literature JSON bundle.
- Verifies referenced raw files before saving the bundle.
- Records retrieval timestamps, Git commit and working-tree status.
- Uses atomic file replacement to avoid publishing partial files.

Create a bundle:
    .venv\Scripts\python.exe -m app.evidence

Validation:
- 51 automated tests passed on Windows.
- Live retrieval saved and verified all four source responses.
- First bundle contained 10 articles and four raw-file references.
- Its saved-file checksum matched the reported checksum.
- The generating code was committed with a clean working tree.

Storage:
- Bundles are saved under data/bundles/.
- Keep bundles together with their referenced data/raw/ files.
- The data folder is excluded from Git and needs a separate backup.

Current limitations:
- Bundle creation is available through the command line.
- Git provenance does not capture Python dependency versions.
- AI summaries and a user-facing web interface are not implemented.
- This research prototype is not for clinical decisions.

## Milestone 5: Readable evidence reports

Added Markdown report generation from a saved BRCA1 evidence bundle.

Capabilities:
- Present gene and protein identity with source links.
- Include PubMed titles, abstracts, and article links.
- Show retrieval dates and recorded Git provenance.
- Verify referenced raw files against their recorded SHA-256 hashes.
- Reject missing or corrupted raw files and paths outside data/raw.
- Handle empty article lists and missing abstracts.
- Run without an AI API or API credits.

Generate a report:

    .venv\Scripts\python.exe -m app.report data\bundles\<bundle-filename>.json

Replace <bundle-filename> with the name of an existing bundle.
Reports are saved under data/reports/.

Validation:
- 57 automated tests passed.
- A report was successfully generated from a saved evidence bundle.

Limitations:
- Reports present retrieved evidence; they are not AI summaries.
- Checksum verification checks file integrity, not scientific accuracy.
- Reports are for research use, not clinical decisions.

## Milestone 6: Local evidence viewer

Added a browser page at / for viewing saved BRCA1 evidence.

Capabilities:
- Display the saved bundle with the latest file modification time.
- Show gene and protein identity with source links.
- Display PubMed article titles and expandable abstracts.
- Verify raw-file checksums before displaying evidence.
- Show a helpful message when no bundle exists.
- Escape article text for safe HTML display.
- Read saved evidence without paid AI calls or new retrieval requests.

Start the local server:

    .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000 in a browser.

Validation:
- 61 automated tests passed.
- Browser page manually opened and evidence displayed successfully.
- Tests cover normal display, absent bundles, corrupted raw evidence,
  and HTML escaping.

Limitations:
- Intended for local use; authentication is not implemented.
- File modification time determines which bundle is displayed.
- Retrieved evidence is not an AI summary or scientific quality assessment.
- Research use only, not for clinical decisions.

## Milestone 7: Evidence bundle selection

Added a dropdown for choosing saved evidence bundles.

- Lists bundles by file modification time, newest first.
- Displays the latest bundle by default.
- Allows selection of an older saved bundle.
- Rejects unavailable filenames and paths outside the bundle folder.
- Verifies raw-file checksums before displaying evidence.
- Requires no paid AI API.

Validation: 65 automated tests passed, including bundle-selection tests.
The dropdown was also displayed successfully in the local browser.

## Milestone 8: Report downloads

Added a Download Markdown report link for the selected evidence bundle.

Capabilities:
- Generate and download a report directly from the local browser.
- Include gene, protein, literature, and provenance information.
- Verify raw-file checksums before generating the report.
- Reject unavailable bundles and paths outside the bundle folder.
- Block downloads when referenced raw evidence is missing or corrupted.
- Require no paid AI API.

Validation:
- 70 automated tests passed.
- A report was downloaded and its contents checked manually.

Reports present retrieved evidence and are not AI-generated summaries.
Research use only, not for clinical decisions.

## Milestone 9: Imported AI summaries

Added manual import and browser display of ChatGPT summaries.

Capabilities:
- Link each summary to an exact evidence bundle using SHA-256.
- Verify the bundle checksum and referenced raw files during import.
- Check that recognized PMID labels and PubMed URLs cite bundle articles.
- Save summaries separately from retrieved evidence.
- Preserve previous imports as separate files.
- Display the latest imported summary by file modification time.
- Show origin, import time, and Not yet reviewed status.
- Verify summary text checksums before display.
- Escape summary text for safe HTML display.
- Provide clickable PubMed citation links.

Validation:
- 83 automated tests passed.
- A summary was imported and displayed successfully in the browser.

Limitations:
- Summaries are manually copied from ChatGPT, not generated by the app.
- Citation membership does not prove that a source supports a claim.
- Summary text is displayed as plain text; tables may lose formatting.
- Scientific claims require human review.
- No paid AI API is required.

## Milestone 10: Summary review tracking

Added review records linked to exact imported summary versions.

Capabilities:
- Record reviewer name, review time, notes, scope, and checked PMIDs.
- Support in_progress, changes_requested, and reviewed decisions.
- Require whole-summary scope and all cited PMIDs for reviewed status.
- Preserve summaries and earlier reviews as separate files.
- Match reviews to the exact summary file checksum.
- Display the latest matching review by recorded review time.
- Escape reviewer names and notes for safe browser display.
- Show an unavailable status when review records cannot be validated.

Validation:
- 97 automated tests passed.
- The browser correctly displayed Not yet reviewed when no matching
  review record existed.

Limitations:
- Reviewer identity and review completion are self-reported.
- Citation checks do not establish scientific accuracy.
- Reviewed does not mean clinically validated.
- Review records are stored under data/reviews and excluded from Git.

## Milestone 11: Browser review form

Added a form for recording reviews directly from the local viewer.

Capabilities:
- Enter reviewer name, review notes, scope, and decision.
- Select the cited sources actually checked.
- Save reviews through the existing review-validation module.
- Link submissions to the exact displayed summary version.
- Reject changed summaries, invalid form tokens, and invalid selections.
- Preserve the original summary and previous review records.

Validation:
- 105 automated tests passed.
- The form was displayed successfully in the local browser.
- Submission tests use temporary data, not real review records.

Limitations:
- Intended for local use; user authentication is not implemented.
- Reviewer identity and completion remain self-reported.
- Refresh the viewer after restarting the server before submitting.
- Recording a review does not establish clinical validity.
