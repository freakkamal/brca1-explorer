\# BRCA1 Evidence Explorer: Tracing literature search results to saved source passages



\## Abstract



A reader inspecting an AI-generated research summary needs to know which

source was used, what the source said, and which claims a person checked.

We developed BRCA1 Evidence Explorer, a local research prototype that links

saved literature records, manually imported AI summaries, and

version-specific human review notes. The application lets a reader compare

two saved literature collections and follow a search result to the passage

that matched.



In a collection of 10 saved article titles and abstracts, manual review

and the application returned identical PubMed identifier sets for three

preselected whole-word searches: ferroptosis, antibodies, and oocytes.

In a separate search, Cezanne and Ube2S matched the same article; the

application displayed that article once and retained both matching terms.

These checks demonstrate traceability and literal search behavior in a

small collection. They do not establish comprehensive literature retrieval,

summary accuracy, or drug activity.



\## Methods



\### Evidence collection



The evaluation used a saved BRCA1 literature bundle from October 18, 2026.

The PubMed query was `BRCA1\[Title/Abstract]`, ordered by relevance. At

retrieval, the search reported 23,328 matching records; the bundle included

10\. The evaluation used the saved titles and abstracts rather than rerunning

the live PubMed query.



Bundle filename: `brca1-cbbd29b367a3494db61bb4e1e2cdf07a.json`



Bundle SHA-256: `0dc0f835f5afe0831d22f6653f22aca38a370b63ffa317bdb35d7598257698ed`



\### Manual and application searches



Three terms were selected before comparing results: `ferroptosis`,

`antibodies`, and `oocytes`. For each term, the project author inspected

the saved titles and abstracts and recorded the PMID of each matching

article. A match required the whole word, ignoring capitalization. An

article counted once per term even if the word appeared several times.

Synonyms, inferred topics, and text in the imported AI summary were excluded.



The same three terms were then entered into the application's multiple-term

search for the same bundle. Agreement was assessed separately for each term

by comparing the manually recorded PMIDs with the PMIDs returned by the

application. Equal counts alone were insufficient: the identifiers also

had to match.



\### Overlapping matches



A separate demonstration used `Cezanne` and `Ube2S` to check how the

application displayed an article matching more than one term. The check

was whether the PMID appeared once in the combined article list while

retaining both matched terms. This demonstration was separate from the

three-term manual evaluation.



\## Results



| Search term | Manual PMID | Application PMID |

|---|---|---|

| ferroptosis | 39265497 | 39265497 |

| antibodies | 34421362 | 34421362 |

| oocytes | 38696471 | 38696471 |



A comparison of two saved bundles illustrates why the underlying snapshot

matters. Cezanne matched no articles in the October 15 bundle and one of

ten in the October 18 bundle (PMID 41359628). From the comparison page,

the reader could open the matching bundle and inspect three saved passages.

The result describes the contents of those snapshots; it does not indicate

when the paper first became available in PubMed.



\## Limitations



The manual evaluation covered three terms in one ten-article collection

and was performed by the project author. It was not an independent benchmark.

Literal search does not find synonyms unless the reader supplies them.

File checksums establish whether saved content matches a recorded digest;

they do not establish whether a paper supports a scientific claim.

