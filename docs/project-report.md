\# BRCA1 Evidence Explorer: Linking biological records, literature, and human review



\## Purpose

BRCA1 Evidence Explorer is a local research prototype for inspecting the

sources behind a BRCA1 evidence report. A reader can move from a summary

to a cited abstract and identify the exact saved bundle used for review.



\## Methods

The Python and FastAPI application retrieves gene identity from NCBI Gene,

protein identity from UniProt, literature from PubMed, and compound

identifiers and selected properties from PubChem. It saves raw responses

with SHA-256 checksums. Manually imported AI summaries are stored separately

from retrieved evidence. Human review records are linked to the exact

summary version reviewed.



\## Worked example

The saved bundle brca1-cbbd29b367a3494db61bb4e1e2cdf07a.json contains

10 PubMed articles and references four raw responses. Its SHA-256 is

0dc0f835f5afe0831d22f6653f22aca38a370b63ffa317bdb35d7598257698ed.



A reproducible demonstration is to select this bundle, search for GPX4,

and compare the displayed passage for PMID 39265497 with the downloaded

JSON. Record the observed match count and a screenshot when performing

this demonstration.



\## Validation

Record the Git commit used for the demonstration, the test command,

the actual test result, and the date. Report automated software checks

separately from any human review of scientific claims.



\## Limitations

The literature collection is a small relevance-ranked sample, not a

systematic review. Literal searches can miss synonyms. Checksums verify

file integrity; citation checks verify that a PMID is in the bundle.

Neither establishes that a scientific interpretation is correct.



\## Demonstration: checking a search against its JSON export



\- Date tested: \[date]

\- Software commit: \[commit ID]

\- Python version: \[version]

\- Automated test result: \[paste the final pytest line]

\- Saved bundle: brca1-cbbd29b367a3494db61bb4e1e2cdf07a.json

\- Bundle SHA-256 reported by the exports: \[checksum]



| Search term | Matches on page | Matches in JSON | Observation |

|---|---:|---:|---|

| GPX4 | \[count] | \[count] | PMID 39265497 present: \[yes/no] |

| zzzz-no-match-123 | \[count] | \[count] | Empty matches list: \[yes/no] |



This demonstration checks whether the export preserves the search results

for one saved bundle. It does not evaluate how comprehensively the search

finds relevant literature or whether a compound acts on BRCA1.



\## Run the offline example



From the project root, with the project and test dependencies installed, run:



```text

python -m pytest -q tests/test\_compare.py::test\_offline\_literature\_export\_example

```



The example creates two synthetic articles in a temporary folder. It checks

that the JSON export returns one matching passage for GPX4 and no matches

for a deliberately absent term. Both exports must identify the same bundle

by its SHA-256 checksum. This demonstrates software behavior using synthetic

text; the October 18 bundle is the separate worked example using real records.



\## Milestone 23: Fresh-copy reproducibility check



I ran the synthetic literature-export example on Windows from a fresh

checkout in brca1-reader-check using a separate Python environment.



\- Tested commit: \[paste commit ID here]

\- Python: 3.13.16

\- pytest: 9.1.1

\- Result: 1 passed, 1 warning in 1.50s

\- Warning: Starlette reported a deprecation in its test client.



The test checked both a matching search and a zero-match search using

synthetic data. This was a fresh-copy check on the same PC.



\## Worked example: tracing a summary claim to its source



The October 18 BRCA1 bundle contained 10 PubMed records. Finding 3 in

the manually imported AI summary described experiments combining GPX4

and PARP inhibition. It cited PMID 39265497.



| Step | Evidence recorded |

|---|---|

| Identify the input | Saved bundle: `brca1-cbbd29b367a3494db61bb4e1e2cdf07a.json` |

| Identify the claim | Finding 3 described results in cancer cells, patient-derived organoids, and xenografts. |

| Locate the source | \[PubMed PMID 39265497](https://pubmed.ncbi.nlm.nih.gov/39265497/); the abstract was also available in the saved bundle. |

| Inspect the review | On 18 October 2026, the reviewer recorded checking the experimental models, the combination-treatment finding, and the distinction between preclinical results and patient benefit. |

| Report the scope | Status: review in progress. Only this finding was checked, using the saved abstract. The full text and the remaining findings were not assessed in this review. |



This example shows what the review record lets a reader establish: which

claim was checked, which source was used, and where the review stopped.

The software's citation check alone establishes only that the cited PMID

belongs to the bundle.



Integrity check. Using a synthetic bundle, the JSON export initially returned one matching article. After one referenced raw file was changed without updating its recorded checksum, the same request returned HTTP 400 with a checksum mismatch and no download attachment. This demonstrates detection of a change relative to the saved bundle. It does not establish the scientific accuracy of the original source.



A literal search for GPX4 matched one of ten articles in each of two saved BRCA1 bundles. Both matches referred to PMID 39265497. Neither bundle contained an additional GPX4-matching article. This comparison describes the contents of the two saved snapshots.



\## Comparing search results across two saved bundles



Each bundle contained 10 articles. The same literal search was run against

the saved titles and abstracts in each bundle.



| Search term | October 15 bundle | October 18 bundle | Matching PMID |

|---|---:|---:|---|

| GPX4 | 1 of 10 | 1 of 10 | 39265497 in both |

| Cezanne | 0 of 10 | 1 of 10 | 41359628 in the October 18 bundle only |



These counts describe the two saved bundles. The Cezanne result does not

establish when the article was published or when it first appeared in PubMed.



\## Milestone 27: Browser comparison of literature mentions



Searching for Cezanne in the browser matched 0 of 10 baseline articles

and 1 of 10 comparison articles. The browser linked PMID 41359628 under

“Matched only in comparison,” agreeing with the command-line result.

Clearing the search term restored the full comparison: 7 shared articles

and 3 unique to each bundle. These counts describe the saved snapshots.



Automated test run: 145 passed, 1 warning in 3.63 seconds.

## Milestone 28: From a comparison count to saved passages

In the browser comparison, Cezanne matched 0 of 10 baseline articles and
1 of 10 comparison articles. Following the comparison passage link opened
the October 18 bundle with Cezanne already selected. The page displayed
PMID 41359628, marked the title match, and showed three matching passages
from the saved abstract. This demonstrates that a reader can trace a count
to its source text without retyping the query or reselecting the bundle.

Milestone 29 — Multiple-term literature search. In a synthetic three-article bundle, one search term matched one article, another matched two, and a third matched none. The combined result contained two distinct PMIDs. The article matching both terms appeared once and retained both matched terms.

## Milestone 30: Multiple-term search in the browser

In the October 18 saved bundle, Cezanne and Ube2S each matched one article.
Both matched PMID 41359628, which appeared once in the results with both
terms listed. The control query zzzz-no-match-123 remained visible with
zero matches. The browser therefore showed two term matches but one
distinct article.

## Milestone 31: Navigation and multiple-term browser search

Full test suite: [paste the final pytest line here]

The browser test confirmed that the literature search page links to the
multiple-term search. When Cezanne and Ube2S matched the same test article,
the page listed the article once and displayed both terms. The unmatched
term remained visible with a count of zero.

