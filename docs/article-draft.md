# BRCA1 Evidence Explorer: Tracing literature search results to saved source passages

## Abstract

A reader inspecting an AI-generated research summary needs to know which source was used, what the source said, and which claims a person checked. I developed BRCA1 Evidence Explorer, a local research prototype that links saved literature records, manually imported AI summaries, and version-specific human review notes. The application lets a reader compare two saved literature collections and follow a search result to the passage that matched.

In a collection of 10 saved article titles and abstracts, manual review and the application returned identical PubMed identifier sets for three preselected whole-word searches: ferroptosis, antibodies, and oocytes. In a separate search, Cezanne and Ube2S matched the same article; the application displayed that article once and retained both matching terms.

These checks demonstrate traceability and literal search behavior in a small collection. They do not establish comprehensive literature retrieval, summary accuracy, or drug activity.

## Introduction

This project began with a practical question: how can a reader trace a research-summary statement back to the saved evidence used to produce it?

I built BRCA1 Evidence Explorer as a local prototype for exploring that workflow. It retrieves source records, saves evidence snapshots, searches article titles and abstracts, and keeps manually imported AI summaries separate from retrieved evidence. Human review notes are attached to specific summary versions.

The walkthrough focuses on one example: comparing two saved BRCA1 literature bundles, finding a Cezanne text match, and opening the saved passage behind that result. It also describes a small manual search evaluation and the software installation checks performed during development.

The current application supports evidence inspection and review tracking. It does not predict compound activity, perform molecular docking, or establish treatment effectiveness.


## Methods

### Implementation and evidence tracking

BRCA1 Evidence Explorer is a local Python application with a FastAPI backend and browser pages. It retrieves BRCA1 identity records from NCBI Gene and UniProt, and literature records from PubMed. Raw responses are saved with SHA-256 hashes. Evidence bundles link the retrieved records to those saved responses.

The application checks referenced raw files against the hashes recorded in the selected bundle before displaying or processing evidence. These checks detect differences from the recorded content; they do not verify scientific accuracy or authenticate the original source.

Literature searches operate on saved titles and abstracts. Matching is case-insensitive and uses word boundaries around the supplied term. Synonyms and abbreviations are not automatically expanded. Multiple-term searches retain each article once in the combined results while listing its matching terms.

AI summaries are imported manually and stored separately from retrieved evidence. Review records are linked to the exact summary version and evidence bundle using checksums. Each review records the reviewer name, decision, scope, checked PMIDs, notes, and timestamp. Reviewer identity and completion are self-reported.


### Evidence collection

The evaluation used a saved BRCA1 literature bundle from October 18, 2026. The PubMed query was `BRCA1[Title/Abstract]`, ordered by relevance. At retrieval, the search reported 23,328 matching records; the bundle included 10. The evaluation used the saved titles and abstracts rather than rerunning the live PubMed query.

Bundle filename: `brca1-cbbd29b367a3494db61bb4e1e2cdf07a.json`

Bundle SHA-256: `0dc0f835f5afe0831d22f6653f22aca38a370b63ffa317bdb35d7598257698ed`

The comparison demonstration also used the October 15, 2026 bundle, containing 10 saved articles.

Baseline bundle filename: `brca1-1546dd5903e84e24a919b6f06e4ec17e.json`

Baseline bundle SHA-256: `bd80cde89959a5c94afa715360c7ae09314463413ab1892eef114120a5640d61`

The October 15 bundle was selected as the baseline and the October 18 bundle as the comparison.

### Manual and application searches

Three terms were selected before comparing results: `ferroptosis`, `antibodies`, and `oocytes`. For each term, the project author inspected the saved titles and abstracts and recorded the PMID of each matching article. A match required the whole word, ignoring capitalization. An article counted once per term even if the word appeared several times. Synonyms, inferred topics, and text in the imported AI summary were excluded.

The same three terms were then entered into the application's multiple-term search for the same bundle. Agreement was assessed separately for each term by comparing the manually recorded PMIDs with the PMIDs returned by the application. Equal counts alone were insufficient: the identifiers also had to match.

### Overlapping matches

A separate demonstration used `Cezanne` and `Ube2S` to check how the application displayed an article matching more than one term. The check was whether the PMID appeared once in the combined article list while retaining both matched terms. This demonstration was separate from the three-term manual evaluation.

## Results

| Search term | Manual PMID | Application PMID |
|---|---|---|
| ferroptosis | 39265497 | 39265497 |
| antibodies | 34421362 | 34421362 |
| oocytes | 38696471 | 38696471 |

In the overlapping-term demonstration, Cezanne and Ube2S each matched one article, PMID 41359628. The combined results contained one distinct article and listed both matching terms. The additional query `zzzz-no-match-123` returned zero matches.

A comparison of two saved bundles illustrates why the underlying snapshot matters. Cezanne matched no articles in the October 15 bundle and one of ten in the October 18 bundle (PMID 41359628). From the comparison page, the reader could open the matching bundle and inspect three saved passages.

The result describes the contents of those snapshots; it does not indicate when the paper first became available in PubMed.

## Limitations

The manual evaluation covered three terms in one ten-article collection and was performed by the project author. It was not an independent benchmark.

Literal search does not find synonyms unless the reader supplies them. File checksums establish whether saved content matches a recorded digest; they do not establish whether a paper supports a scientific claim.

## Figure 1. From a comparison count to a saved passage

![Panel A: Cezanne matched zero of ten baseline articles and one of ten comparison articles.](figures/figure-1a-comparison.png)

![Panel B: The passage viewer shows PMID 41359628 and the saved text containing Cezanne.](figures/figure-1b-passage.png)

Panel A shows the result for two saved BRCA1 bundles. Selecting the comparison passage link opens the article and matching text in Panel B while preserving the search term and bundle selection.


## Use of AI assistance

ChatGPT was used to assist with software development, troubleshooting, test drafting, documentation, and preparation of manually imported literature summaries. The application does not call an OpenAI API to generate summaries automatically.

Imported summaries are labelled as AI-generated interpretation and kept separate from retrieved evidence. Citation checks establish whether recognized PMIDs belong to the selected bundle; they do not establish that a cited article supports an associated claim.

The small search evaluation reported here assesses literal matching behavior. It does not evaluate the scientific accuracy of AI-generated summaries. Human review remains necessary.


## Software version and validation

The project was checked on Windows using Python 3.13.16 at Git commit `4dbee82da66d3a62ae93231eb4693db6c89ce5bc`.

The repository contains `requirements.txt` and `requirements-dev.txt`. Running `python -m pip check` in the project environment reported no broken requirements.

The full automated test suite was run with `python -m pytest -q`: 147 tests passed, with one warning, in 2.95 seconds. The warning concerned deprecated use of httpx with Starlette's TestClient.

These results describe the tested local environment. Passing software tests does not establish scientific accuracy, clinical validity, or compatibility with every operating system. Test execution time may differ on other machines.


## Fresh-environment installation check

On November 19, 2026, a separate Python virtual environment was created on the same Windows PC. Dependencies were installed from `requirements-dev.txt`, which includes `requirements.txt`.

The new environment reported no broken requirements. Running the full test suite with its Python interpreter produced 147 passed tests and one Starlette TestClient deprecation warning in 3.43 seconds.

This check used the existing project files with freshly installed dependencies. It was not a fresh repository checkout, an independent reproduction, or a cross-platform test. It did not assess scientific accuracy.

After the original validation run, `httpx==0.28.1` was moved from the development requirements to the runtime requirements because the application uses it for source retrieval. The subsequent fresh-environment check used the revised dependency files. Commit `d0a3790c82a9694b35bc2debff77c237ba9ed683` records the later documented snapshot used in the reproduction instructions.


## Reproduction instructions

These instructions currently apply to readers who have been granted repository access. Without the separately stored evidence files, readers cannot reproduce the illustrated evidence views. The screenshot in Panel B shows one of the three matching passages available in the application.

The documented project snapshot is Git commit `d0a3790c82a9694b35bc2debff77c237ba9ed683`. The fresh-environment check described above used Python 3.13.16 on Windows.

In a separate checkout of the repository, select this snapshot:

```cmd
git checkout --detach d0a3790c82a9694b35bc2debff77c237ba9ed683
```

From that checkout's root directory, create an environment using an installed Python 3.13 interpreter:

```cmd
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q
```

The `py` command requires the Windows Python launcher. If it is unavailable, use the full path to an installed Python 3.13 executable for the environment-creation command.

Start the local viewer with:

```cmd
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ in a browser.

Reproducing the article's recorded search results requires the same saved evidence bundles and their referenced raw files. Running a new live retrieval may return different records or ordering. Imported summaries and review histories additionally require their corresponding saved files.

These instructions describe the intended reproduction procedure. The completed fresh-environment check used existing project files on the author's PC, rather than a separate checkout.


## Software and data availability

The source code, tests, documentation, and commit history are stored in a private GitHub repository. The repository is not currently accessible to general readers.

Saved source responses, evidence bundles, imported summaries, and review records are stored separately in the local data directory and backed up to an external drive. These files are excluded from Git tracking and are not included in the GitHub repository.

Reproducing the exact reported evidence searches requires the original saved bundles and their referenced raw files. Retrieving new records from the source services may produce different results. A reader-accessible software and evidence package has not yet been released.

## What this prototype demonstrates and what comes next

The demonstrated workflow connects a search result to a particular evidence snapshot and its saved source passages. It also separates imported AI interpretation from retrieved records and records which summary version a person reviewed.

The small manual evaluation found matching PMID sets for three search terms. Automated tests and a fresh-environment installation check provide additional evidence about software behavior, but they do not establish scientific accuracy or general usefulness to researchers.

The next development priorities are a shareable example dataset, an installation check by another person, and broader search evaluation. These steps would help determine whether the workflow remains understandable and reliable beyond the author's own environment.

## Fresh GitHub checkout validation

On 22 November 2026, I cloned the milestone-37-synthetic-demo branch into a separate directory on the same Windows PC and created a new Python virtual environment.

The tested commit was `ea4932579d4a31f942014b2a04814134cf388623`.

After installing the development requirements, the synthetic demonstration completed successfully. It confirmed a matching search, a zero-match search, and overlapping search terms counted as one distinct record. The demonstration used fictional records and removed its temporary files.

The full automated test suite reported **147 passed, 1 warning in 6.13 seconds**. The warning concerned deprecated httpx usage by Starlette's test client.

This check demonstrates that the tested GitHub checkout could run the synthetic example and automated tests in a fresh environment on the author's PC. It is not independent reproduction on another person's computer, and it does not validate scientific claims or reproduce the separately stored research evidence.