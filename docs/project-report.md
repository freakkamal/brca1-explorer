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

