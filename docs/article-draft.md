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

