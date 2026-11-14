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

