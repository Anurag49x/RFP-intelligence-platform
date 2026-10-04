# RFP Intelligence Platform — Master Implementation Plan

> This file is the single source of truth for the project.
>
> Antigravity must read and follow this plan before implementing or modifying the project.

---

# 1. Project Overview

## Project Name

**RFP Intelligence Platform: RAG Search Engine & Multi-Agent System**

## Objective

Build an evidence-first AI system that processes procurement/RFP bid folders containing HTML pages, PDFs, addendums, specification documents and affidavits.

The system must make bid information:

- searchable
- answerable
- extractable
- citation-grounded
- auditable
- robust to document variation
- usable on unseen bid folders

The final system must produce:

1. a structured JSON record for every bid
2. every important extracted value backed by source evidence
3. natural-language answers backed by citations

---

# 2. Problem Being Solved

RFP/bid information is fragmented across:

- procurement portal HTML pages
- main RFP documents
- addendums
- product/specification documents
- affidavits
- supporting documents

Important facts can include:

- bid numbers
- due dates
- submission methods
- contract terms
- pre-bid meetings
- bid bonds
- delivery requirements
- payment terms
- warranties
- product models
- part numbers
- technical specifications
- required affidavits
- procurement contacts

An addendum can modify the original RFP.

Therefore, simply doing:

    PDF → embedding → top-k → LLM

is NOT sufficient.

The system must understand:

    original requirement
            +
    applicable amendments
            =
    effective requirement

The system must also never invent information.

---

# 3. Official Assignment Requirements

The assignment has two core goals.

## A. RAG Search Engine

Build a real search engine over all bid documents.

It must:

- ingest PDF and HTML
- preserve page structure
- preserve tables
- clean extracted text
- attach metadata
- chunk documents intelligently
- generate embeddings
- store vectors
- support keyword search
- support hybrid search
- support metadata filters
- support reranking
- support query rewriting/expansion
- return citations
- be independently usable as API/CLI
- support incremental indexing

## B. Multi-Agent System

Build cooperating specialized agents.

They must:

- use the RAG search engine as a tool
- extract structured bid information
- reconcile addendums
- validate results
- retry failed fields
- answer natural-language questions
- produce cited output

---

# 4. Evaluation Rubric

| Criterion | Weight |
|---|---:|
| RAG Search Engine | 25% |
| Multi-Agent System | 25% |
| Extraction Accuracy | 20% |
| Robustness | 10% |
| Code Quality & Architecture | 10% |
| Documentation & Demo | 10% |

## Engineering priority

Prioritize in roughly this order:

1. retrieval correctness
2. evidence/citations
3. addendum reconciliation
4. extraction accuracy
5. validator/retry
6. unseen-bid robustness
7. testing/evaluation
8. observability
9. frontend polish

Do not spend most of the project on UI styling.

---

# 5. Core Architecture Principle

The central design rule is:

> **LLMs interpret evidence; deterministic software controls the system.**

Use deterministic software for:

- file discovery
- document classification
- metadata
- hashing
- chunk IDs
- indexing
- BM25
- RRF
- metadata filtering
- citation existence checks
- schema validation
- date parsing
- retry limits
- evaluation metrics
- incremental indexing

Use LLMs for:

- query understanding
- semantic query rewriting
- semantic extraction
- addendum interpretation
- natural-language synthesis
- semantic entailment validation

The system should never become one giant prompt.

---

# 6. Evidence-First Philosophy

The final system must follow:

    Question
       ↓
    Retrieval
       ↓
    Evidence
       ↓
    Extraction / Reasoning
       ↓
    Validation
       ↓
    Answer

Never:

    Question
       ↓
    LLM
       ↓
    Guess

## Hard rule

> **No important final fact exists without evidence.**

If evidence is unavailable:

```json
{
  "value": null,
  "sources": [],
  "confidence": 0.0,
  "notes": "Not found in documents"
}
```

Do not guess.

7. Supplied Documents
Bid1

Student and Staff Computing Devices

Files:

BidNet Direct bid page
JA-207652 Student and Staff Computing Devices FINAL.pdf
Addendum 1.pdf
Addendum 2.pdf
Bid2

Dell Laptops w/ Extended Warranty

Files:

BidNet Direct bid page
PORFP - Dell Laptop Final.pdf
Dell Laptop Specs.pdf
Contract Affidavit.pdf
Mercury Affidavit.pdf

Each folder represents one bid-level knowledge unit.

However, every individual source document must retain its own:

filename
page
document type
addendum number
document date
source location
8. Critical Generalization Requirement

The application must NOT be hard-coded to Bid1 or Bid2.

Do not write:

if bid_id == "Bid1":
    ...

Do not write:

if filename == "Addendum 2.pdf":
    ...

Do not hard-code the 20 answers.

Do not assume fixed filenames.

Do not assume a fixed number of PDFs.

The evaluator will test at least one unseen bid folder.

A new bid should work without modifying application code.

9. Target Architecture
                         USER
                           |
                           v
                   ORCHESTRATOR
                           |
                           v
                    SEARCH ENGINE
                           |
              +------------+------------+
              |                         |
              v                         v
         Dense Search                BM25
            Jina                    local
              |                         |
              +------------+------------+
                           |
                           v
                          RRF
                           |
                           v
                    Jina Reranker
                           |
                           v
                  Evidence + Citations
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
      Logistics         Product          Legal/
      Specialist        Specialist       Compliance
          |                |                |
          +----------------+----------------+
                           |
                           v
                Addendum Reconciliation
                           |
                           v
                     Validator
                      /      \
                   FAIL      PASS
                    |          |
                    v          v
              Targeted Retry  JSON
                    |          +
                    +-------> Q&A
                               +
                           Citations
10. Technology Stack
LLM

Use:

Groq API

Responsible for:

query rewriting
extraction reasoning
addendum interpretation
natural-language answers
semantic validation

LLM model must be configurable.

Embeddings

Use:

Jina Embeddings API

Embeddings must be hidden behind an adapter.

Conceptually:

EmbeddingProvider
       ↓
JinaEmbeddingProvider

Do not spread Jina-specific code across the application.

Reranking

Use:

Jina Reranker API

Reranking is a separate pipeline stage.

Conceptually:

Dense + BM25
      ↓
     RRF
      ↓
Candidate set
      ↓
Jina Reranker
      ↓
Final evidence
Vector DB

Use:

Qdrant

Development:

Qdrant running locally through Docker

Default:

http://localhost:6333
Keyword Search

Use:

BM25

Run locally.

Especially important for:

solicitation numbers
PORFP numbers
project identifiers
SKU codes
part numbers
model numbers
Agent Framework

Use:

LangGraph

Reasons:

explicit shared state
parallel worker execution
conditional routing
validation feedback loop
bounded retries
API

Use:

FastAPI

PDF

Primary:

PyMuPDF
pdfplumber

Optional:

Docling for difficult layouts
HTML

Use:

BeautifulSoup
trafilatura
Schemas

Use:

Pydantic

Observability

Use:

LangSmith
OpenTelemetry
Frontend

Preferred:

React/Next.js + FastAPI

Alternative:

Streamlit

Frontend comes after backend functionality.

11. Repository Structure
rfp-intelligence/
│
├── app/
│   ├── api/
│   ├── ingestion/
│   ├── search/
│   ├── agents/
│   ├── graph/
│   ├── schemas/
│   ├── evaluation/
│   └── config.py
│
├── tests/
│
├── eval/
│   ├── gold_questions.json
│   ├── extraction_gold.json
│   └── results/
│
├── data/
│   ├── Bid1/
│   ├── Bid2/
│   └── unseen/
│
├── outputs/
│   ├── ingestion/
│   ├── extraction/
│   └── traces/
│
├── frontend/
│
├── docs/
│   ├── architecture/
│   ├── screenshots/
│   └── demo/
│
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── main.py
├── README.md
└── plan.md
12. Environment Configuration

Use:

APP_ENV=development
LOG_LEVEL=INFO

GROQ_API_KEY=
GROQ_MODEL=

JINA_API_KEY=
JINA_EMBEDDING_MODEL=
JINA_RERANKER_MODEL=

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

LANGSMITH_API_KEY=
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=rfp-intelligence

Never:

hard-code keys
commit .env
put API keys in source code
hard-code model names
13. Phase Plan

The project will be implemented in this exact order.

PHASE 0  → Project Setup
PHASE 1  → Document Ingestion
PHASE 2  → Chunking + Evidence Model
PHASE 3  → Jina Embeddings + Qdrant
PHASE 4  → BM25 + Hybrid Retrieval
PHASE 5  → Jina Reranker
PHASE 6  → Retrieval Evaluation
PHASE 7  → Incremental Indexing
PHASE 8  → Query Understanding
PHASE 9  → Evidence Retrieval Tool
PHASE 10 → LangGraph
PHASE 11 → Structured Extraction
PHASE 12 → Addendum Reconciliation
PHASE 13 → Validator + Retry
PHASE 14 → Q&A
PHASE 15 → API Hardening
PHASE 16 → Observability
PHASE 17 → Frontend
PHASE 18 → Full Testing
PHASE 19 → Unseen Bid Validation
PHASE 20 → Documentation + Demo

Never skip a phase gate.

14. PHASE 0 — Project Setup
Goal

Establish the project skeleton.

Build:

directory structure
Python environment
configuration
logging
FastAPI skeleton
/health
Docker Compose
local Qdrant
base schemas
README
basic tests

Do NOT build:

embeddings
retrieval
BM25
reranking
agents
extraction
addendum reconciliation
Q&A
frontend
Acceptance
application starts
/health works
config loads
Qdrant starts
tests pass
no secrets committed
README is accurate
15. PHASE 1 — Document Ingestion
Goal

Convert raw bid folders into structured canonical documents.

Pipeline:

File Discovery
      ↓
Classification
      ↓
PDF / HTML Parsing
      ↓
Cleaning
      ↓
Table Extraction
      ↓
Metadata
      ↓
Canonical Document
Supported
PDF
HTML
tables
page numbers
document dates
addendum numbers
document type
bid ID
PDF

Use:

PyMuPDF
pdfplumber
Docling if needed

Preserve:

page boundaries
text
tables
HTML

Use:

BeautifulSoup
trafilatura

Extract useful portal metadata where available.

Cleaning

Perform deterministic normalization:

whitespace
line breaks
safe hyphenation repair
repeated header/footer removal when reliable
preserve headings
preserve lists
preserve page boundaries
preserve tables
Errors

Gracefully handle:

unreadable PDFs
empty pages
parser exceptions
scanned pages

One bad page must not crash the entire bid.

Output

Create canonical JSON under:

outputs/ingestion/

Example:

outputs/ingestion/Bid1.json
outputs/ingestion/Bid2.json
Gate

Do not proceed until Bid1 and Bid2 ingestion has been manually inspected.

16. PHASE 2 — Chunking + Evidence Model
Goal

Transform canonical documents into retrieval-ready evidence.

Normal chunks

Target approximately:

600–800 tokens
~100 token overlap

Use:

section-aware chunking
heading-aware chunking
paragraph-aware chunking
list-aware chunking
Tables

Preserve important tables atomically whenever possible.

Context breadcrumbs

Example:

[Bid: Bid2]
[Document: Dell_Laptop_Specs.pdf]
[Type: specs]
[Page: 4]
[Section: Configuration]
Chunk model
class Chunk(BaseModel):
    chunk_id: str
    bid_id: str
    file_name: str
    doc_type: str
    page_number: int
    section_title: str | None
    addendum_number: int | None
    text: str
    is_table: bool
Citation
class Citation(BaseModel):
    file: str
    page: int
    chunk_id: str
    text: str
Evidence
class Evidence(BaseModel):
    evidence_id: str
    bid_id: str
    text: str
    citation: Citation
    doc_type: str
    addendum_number: int | None
    section: str | None
17. PHASE 3 — Jina Embeddings + Qdrant
Goal

Implement dense semantic retrieval.

Chunks
   ↓
Jina Embeddings
   ↓
Vectors
   ↓
Qdrant

Requirements:

batching
caching
retries
timeout handling
deterministic chunk IDs
metadata persistence

Store payload metadata with every vector.

Do not regenerate embeddings unnecessarily.

18. PHASE 4 — BM25 + Hybrid Retrieval
Goal

Add lexical search.

Pipeline:

          Query
         /     \
    Dense       BM25
       \         /
        \       /
          RRF
           ↓
       Candidates

BM25 should handle exact:

bid identifiers
PORFP numbers
SKUs
model numbers
part numbers
procurement terminology
Metadata filters

Support at least:

bid_id
doc_type
addendum_number
file_name

Example:

bid_id=Bid2
doc_type=specs
19. PHASE 5 — Jina Reranking
Goal

Improve final precision.

Pipeline:

Dense candidates
+
BM25 candidates
       ↓
      RRF
       ↓
15–20 candidates
       ↓
Jina Reranker
       ↓
Top 5

Candidate and top-k values must be configurable.

Track latency and errors.

20. PHASE 6 — Retrieval Evaluation

The assignment requires at least 15 expected question/source pairs.

Create preferably:

30 gold questions

Distribution:

5 exact identifiers
5 dates/logistics
5 addendum questions
5 product/specification
4 legal/compliance
3 negative/not-found
3 cross-bid

Each question should include:

{
  "id": "Q01",
  "bid_id": "Bid1",
  "question": "...",
  "expected_sources": [],
  "expected_answer": "..."
}
Metrics

Measure:

Recall@1
Recall@3
Recall@5
MRR
P50 latency
P95 latency
Compare
Dense only
BM25 only
Hybrid RRF
Hybrid + reranker
Integrity rule

Only report actual measured results.

Never fabricate benchmark numbers.

21. PHASE 7 — Incremental Indexing
Goal

Adding a new bid must not re-index everything.

Maintain:

file_hash
file_name
bid_id
indexed_at
chunk_ids

Behavior:

new file
→ index

same hash
→ skip

changed hash
→ replace only changed document

new bid
→ index only new bid

Test:

Bid1 → index
Bid1 again → skip
Modify one file → re-index only that file
Add Bid3 → index Bid3 only
22. PHASE 8 — Query Understanding

Implement deterministic terminology expansion.

Examples:

deadline
→ due date
→ submission deadline
→ closing date
→ solicitation due
manufacturer
→ OEM
dock
→ docking station

Groq may be used for semantic query rewriting.

The system should retain the original user query.

23. PHASE 9 — Evidence Retrieval Tool

Create a stable retrieval interface:

search_rfp(
    query: str,
    bid_id: str | None = None,
    doc_type: str | None = None,
    addendum_number: int | None = None,
    top_k: int = 5
) -> list[Evidence]

Agents must use this interface.

Agents must not directly manipulate the vector database.

24. PHASE 10 — LangGraph
Shared state
class RFPState(TypedDict):
    bid_id: str
    folder_path: str
    mode: Literal["extract", "qa"]
    query: str | None
    plan: list[str]
    retrieved_evidence: list[Evidence]
    extracted_fields: dict[str, FieldResult]
    addendum_changes: list[AddendumChange]
    validation_results: list[ValidationResult]
    retry_count: int
    final_output: dict | None
    final_answer: str | None
    errors: list[str]
Required agents
Orchestrator
receives goal
determines mode
creates plan
routes agents
manages retries
determines completion
Retrieval Agent
query rewriting
metadata filtering
search invocation
evidence return
Logistics Specialist
Due Date
Bid Submission Type
Term of Bid
Pre Bid Meeting
Installation
Delivery Date
Product/Technical Specialist
Model_no
Part_no
Product
Product Specification
Legal/Compliance Specialist
Bid Bond Requirement
Payment Terms
Additional Documentation
MFG for Registration
Contract or Cooperative to use
Entity Specialist
Bid Number
Title
contact_info
company_name
Addendum Reconciliation Agent
identify amendments
compare original/current values
identify changes
determine effective value
create audit trail
Validator/Critic
evidence support
citation validity
schema validity
date/number formats
consistency
hallucination checks
Q&A/Report Agent
natural-language responses
cited answers
structured reports
25. Parallel Execution

Independent specialist agents should run in parallel when practical.

                 Orchestrator
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      Logistics    Product      Legal
          |           |           |
          +-----------+-----------+
                      |
                      v
             Addendum Reconciler
                      |
                      v
                  Validator

Use typed structured outputs between nodes.

26. PHASE 11 — Structured Extraction

The final output must contain exactly these 20 fields:

Bid Number
Title
Due Date
Bid Submission Type
Term of Bid
Pre Bid Meeting
Installation
Bid Bond Requirement
Delivery Date
Payment Terms
Any Additional Documentation Required
MFG for Registration
Contract or Cooperative to use
Model_no
Part_no
Product
contact_info
company_name
Bid Summary
Product Specification

Each field:

{
  "value": "...",
  "sources": [],
  "confidence": 0.0,
  "notes": "..."
}

Missing field:

{
  "value": null,
  "sources": [],
  "confidence": 0.0,
  "notes": "Not found in documents"
}

Do not invent values.

27. Requirement-State Semantics

The system must distinguish:

Document exists
        ≠
Document required
        ≠
Requirement fulfilled

Do not infer a procurement requirement merely because a document is present.

28. PHASE 12 — Addendum Reconciliation

This is one of the most important domain-specific components.

Use:

Base RFP
   ↓
Addendum 1
   ↓
Addendum 2
   ↓
Effective Requirements

Represent changes:

class AddendumChange(BaseModel):
    field: str
    original_value: Any
    updated_value: Any
    source: Citation
    reason: str

Example:

{
  "field": "Due Date",
  "original_value": "original value",
  "updated_value": "new value",
  "source": {
    "file": "Addendum 2.pdf",
    "page": 1
  },
  "reason": "Addendum explicitly changed the submission deadline."
}

Never use:

newest document wins for every field

Instead use field-dependent authority.

29. Source Authority

General rule:

Explicit amendment
        >
Original requirement

But source authority depends on the field.

Examples:

Final deadline
→ solicitation/addendum

Portal metadata
→ portal source

Required product
→ RFP/PORFP

Technical configuration
→ specification document

Required affidavit
→ procurement requirement

Affidavit content
→ actual affidavit

Every final value must preserve the source that establishes it.

30. Identifier Handling

A bid can have multiple identifiers.

Use:

class BidIdentity(BaseModel):
    bid_id: str
    official_identifier: str
    alternate_identifiers: list[str]
    title: str

Do not discard:

sourcing numbers
portal IDs
project IDs
PORFP numbers
solicitation identifiers

All should remain searchable.

31. Date Handling

Use:

class DateValue(BaseModel):
    raw_text: str
    parsed_datetime: datetime | None
    timezone_text: str | None
    source: Citation

Keep:

source text
normalized value
timezone information
citation

Do not silently overwrite the original representation.

32. Confidence

Confidence must be explainable.

Suggested levels:

High
directly stated
strong retrieval
valid citation
validator passed
Medium
clearly supported but somewhat indirect
Low
ambiguous evidence
Not Found
0

If using a numerical formula, document the formula.

Do not pretend confidence is mathematically objective if it is only heuristic.

33. PHASE 13 — Validator

For every extracted field verify:

evidence exists
citation exists
citation points to real source
value matches evidence
schema valid
format valid
sources are not contradictory
applicable addendums were considered
unsupported assumptions were not introduced

Deterministic checks should handle:

schema
citation structure
date format
numeric format
retry count

LLM semantic validation may classify:

SUPPORTED
UNSUPPORTED
AMBIGUOUS
34. Retry Loop

If a field fails:

Validator
   ↓
Failed field
   ↓
Targeted retrieval
   ↓
Re-extraction
   ↓
Validator

Do not rerun unrelated fields unnecessarily.

Hard-limit retries.

Default:

2–3 retries

No infinite loops.

35. Guardrails

Hard rules:

No evidence → no value

No citation → reject

Ambiguous evidence → low confidence / unresolved

Missing evidence → null

Validation failure → targeted retry

The system must explicitly prefer:

"Not found in documents"

over guessing.

36. PHASE 14 — Q&A

Supported examples:

What is the submission deadline for Bid1 after all addendums?

Which affidavits are required for the Dell laptop bid?

Compare the warranty requirements of both bids.

Is a bid bond required, and if so, how much?

What changed in Addendum 2 compared to the original RFP?

Pipeline:

Question
   ↓
Query Understanding
   ↓
Retrieval
   ↓
RRF
   ↓
Reranking
   ↓
Evidence
   ↓
Groq
   ↓
Citation Validation
   ↓
Answer

For cross-bid questions:

Retrieve Bid1 evidence
+
Retrieve Bid2 evidence
        ↓
Synthesis
        ↓
Cited answer
37. API

Required endpoints:

GET  /health
POST /index
GET  /search
POST /extract
POST /ask
/search

Should support:

q
bid_id
doc_type
addendum_number
top_k

Return:

{
  "query": "...",
  "results": [
    {
      "score": 0.92,
      "text": "...",
      "source": {
        "file": "...",
        "page": 2,
        "chunk_id": "..."
      },
      "metadata": {}
    }
  ]
}
38. Frontend / Live Website

The live application should look like a real RFP analyst tool.

Dashboard

Show:

indexed bids
documents
chunks
indexing status
Search

Show:

query
filters
ranked results
source snippets
file
page
chunk
scores
Q&A

Show:

question
grounded answer
citations
confidence
expandable evidence
Extract Bid

Show:

20 fields
value
confidence
validation status
citations

Clicking a field should reveal its evidence.

Addendum History

Show:

Original
   ↓
Addendum 1
   ↓
Addendum 2
   ↓
Effective Requirement

Show:

old value
new value
source
explanation
Compare

Optional:

Bid1 vs Bid2

Every comparison should remain citation-backed.

Index Documents

Show:

files discovered
document classification
chunks
embeddings
skipped files
errors
incremental updates
Agent Trace

Show:

Orchestrator
 ↓
Retrieval
 ↓
Specialists
 ↓
Addendum
 ↓
Validator
 ↓
Retry
 ↓
PASS
 ↓
Output
39. GitHub Presentation

The repository should communicate:

This is a real engineering system, not a demo wrapper around an LLM.

README top section should contain:

title
problem
architecture diagram
capabilities
demo link
evaluation results
quick start
sample JSON
agent trace
repository structure

Capabilities:

✓ PDF + HTML ingestion
✓ Table-aware parsing
✓ Dense retrieval
✓ BM25 retrieval
✓ Hybrid RRF
✓ Jina reranking
✓ Metadata filtering
✓ Citation-backed evidence
✓ 20-field structured extraction
✓ Addendum reconciliation
✓ LangGraph orchestration
✓ Validator + retry
✓ Incremental indexing
✓ Unseen-bid support
✓ Retrieval evaluation
✓ Observability

Only mark implemented capabilities as complete.

40. Evaluation
Retrieval

At least 15 gold pairs.

Prefer 30.

Measure:

Recall@1
Recall@3
Recall@5
MRR
P50 latency
P95 latency

Compare:

Dense
BM25
Hybrid
Hybrid + Reranker
Extraction

Measure:

20-field accuracy
citation coverage
addendum accuracy
not-found accuracy
Runtime

Track:

embedding latency
retrieval latency
reranking latency
LLM latency
end-to-end latency
token usage
API calls
retry count
41. Tests

Required categories:

test_discovery
test_classifier
test_pdf_parser
test_html_parser
test_table_extraction
test_cleaning
test_chunking
test_bm25
test_hybrid_retrieval
test_metadata_filtering
test_addendum_reconciliation
test_citation_validation
test_validator
test_incremental_indexing
test_end_to_end

Important tests:

Ingestion
page boundaries
HTML parsing
table extraction
metadata
addendum classification
malformed files
empty pages
Retrieval
exact identifier search
semantic retrieval
metadata filtering
citations
reranking
Addendum
new value overrides old value
unrelated value remains unchanged
changes are recorded
multiple amendments handled correctly
Guardrails
unsupported values rejected
missing citations rejected
missing fields become null
retry count bounded
Incremental indexing
unchanged file skipped
changed file replaced
new bid indexed without code modification
42. Critical Bid1 Demonstrations

Bid1 should demonstrate the system's amendment handling.

Important cases:

original deadline
revised deadline
Addendum 1 clarifications
OEM warranty requirements
laptop-only etching clarification
deployment requirements
other changed/clarified requirements

The system must show:

Original evidence
      ↓
Addendum evidence
      ↓
Change record
      ↓
Effective value
43. Critical Bid2 Demonstrations

Bid2 should demonstrate cross-document synthesis.

Use:

PORFP
+
Dell specification
+
Affidavits
+
portal metadata

Show that procurement requirements and technical specifications can originate from different files while remaining one bid-level knowledge unit.

Important cases:

PORFP identifier
project identifier
manufacturer
Dell laptop model
dock
delivery requirement
warranty
required affidavits
technical configuration
44. Important Demo Questions

Use questions that expose different system capabilities.

Exact identifier
What is the exact PORFP number?
Semantic retrieval
When is the proposal due?
Product
What processor is specified for the Dell Latitude 5550?
Metadata filtering
Search only Bid2 specification documents for the processor.
Addendum
What is the final Bid1 submission deadline after all addendums?
Addendum comparison
What changed in Addendum 2?
Compliance
Which affidavits are required for Bid2?
Cross-bid
Compare warranty requirements between Bid1 and Bid2.
Negative case

Ask for a fact that does not exist in the documents.

Expected:

Not found in documents.
45. Demo Video Plan

Target:

7–10 minutes

0:00–0:45 — Problem

Explain:

fragmented RFP information
multiple document types
amendments
need for grounded answers
0:45–1:30 — Architecture

Show:

Ingestion
→ Chunking
→ Dense + BM25
→ RRF
→ Jina Reranker
→ Evidence
→ LangGraph
→ Addendum
→ Validator
→ JSON/Q&A
1:30–2:45 — Search

Demonstrate:

semantic question
exact identifier
metadata filter
citation
2:45–4:00 — Addendum

Ask:

What is the final Bid1 deadline after all addendums?

Show:

Original
→ Addendum
→ Effective value

Show actual evidence.

4:00–5:15 — Extraction

Run full extraction.

Show:

20 fields
values
citations
confidence
validation

Open one difficult field.

5:15–6:00 — Negative case

Ask an unsupported question.

Show:

Not found in documents.
6:00–6:45 — Agent trace

Show:

Orchestrator
→ Retrieval
→ Specialists
→ Addendum
→ Validator
→ Retry
→ PASS
6:45–7:30 — Retrieval evaluation

Show actual measured:

Dense
BM25
Hybrid
Hybrid + Reranker

with Recall/MRR.

7:30–8:30 — Incremental / unseen bid

Add a new bid folder.

Show:

discover
→ classify
→ parse
→ embed
→ index

Then ask a question about it.

No code modification.

8:30–9:30 — Tests / GitHub

Show:

repository
tests
README
output JSON
evaluation
Final

Conclude with:

Every important final fact has evidence.
Addendums are reconciled.
The search engine is independently testable.
Agents operate on evidence rather than whole documents.
The system is measurable and works on unseen bids.
46. Rubric-to-Feature Mapping
Assignment Criterion	What We Must Demonstrate
RAG Search Engine	Dense + BM25 + RRF + reranker + filters + citations + API
Multi-Agent System	LangGraph + shared state + specialist agents + parallel execution
Extraction Accuracy	20-field JSON + source evidence + validation
Robustness	tables + missing fields + failures + unseen bids + incremental indexing
Code Quality	modular architecture + typing + tests + configuration
Documentation/Demo	README + architecture + benchmark + Q&A + trace + video

The UI is useful, but core backend functionality must remain the priority.

47. Selection-Focused Engineering Characteristics

The project should visibly communicate:

Evidence-first engineering

Facts are traceable to source evidence.

Strong retrieval engineering

Hybrid dense + lexical retrieval exists for a reason.

Procurement-aware retrieval

Exact identifiers are preserved.

Addendum intelligence

The system understands effective requirements rather than simply latest documents.

Controlled agent architecture

Agents have narrow responsibilities.

State-machine orchestration

LangGraph controls execution and retries.

Strong validation

Bad extraction is rejected.

Hallucination resistance

Unsupported facts are not invented.

Measurability

Retrieval and extraction have quantitative evaluation.

Robustness

The system is not dependent on the supplied two bids.

Production thinking

Configuration, logging, tests, errors, APIs and incremental indexing are implemented.

Explainability

A reviewer can inspect:

retrieved evidence
source
page
agent action
validation
retry
final value
48. Anti-Patterns to Avoid

Do NOT build:

❌ Question → embedding → top-k → LLM

❌ One giant RFP Agent

❌ Entire PDF passed to every agent

❌ Hard-coded Bid1/Bid2 logic

❌ Latest-document-wins logic for every field

❌ Flattened tables

❌ Uncited extracted fields

❌ Guessed values

❌ One LLM prompt producing entire JSON

❌ Unlimited retry loops

❌ Full-corpus re-indexing after every change

❌ Fabricated benchmark numbers

❌ Unnecessary microservices

❌ Excessive infrastructure complexity

❌ Frontend-first development
49. Phase Gates

Each phase must have a pass/fail gate.

Gate 0

Project starts and tests pass.

Gate 0

Project starts and tests pass.

Gate 1

Bid1 and Bid2 ingestion works.

Gate 2

Chunks/evidence are inspectable.

Gate 3

Jina embeddings + Qdrant work.

Gate 4

BM25 + RRF work.

Gate 5

Jina reranker works.

Gate 6

Retrieval benchmark works.

Gate 7

Incremental indexing works.

Gate 8

Query understanding works.

Gate 9

Evidence retrieval tool works.

Gate 10

LangGraph works with shared state.

Gate 11

20-field extraction works.

Gate 12

Addendum reconciliation works.

Gate 13

Validator/retry works.

Gate 14

Cited Q&A works.

Gate 15

API works robustly.

Gate 16

Observability works.

Gate 17

Frontend works.

Gate 18

Full test suite passes.

Gate 19

Unseen bid works without code changes.

Gate 20

README/demo/submission complete.

50. Final Development Order

Build in this exact order:

1. Project structure
2. Configuration
3. Ingestion
4. Canonical schemas
5. Chunking
6. Evidence model
7. Jina embeddings
8. Qdrant
9. BM25
10. RRF
11. Metadata filtering
12. Jina reranking
13. Retrieval evaluation
14. Incremental indexing
15. Query rewriting
16. Evidence retrieval tool
17. LangGraph state
18. Specialist agents
19. Structured extraction
20. Addendum reconciliation
21. Validator
22. Retry loop
23. Q&A
24. API hardening
25. Observability
26. Frontend
27. Tests
28. Unseen-bid validation
29. README
30. Demo
51. Final Quality Bar

The final system should behave like:

                      USER
                        |
                        v
                 ORCHESTRATOR
                        |
                        v
                  SEARCH ENGINE
                  /          \
               Dense         BM25
                  \          /
                   \        /
                      RRF
                       |
                       v
                   Reranker
                       |
                       v
                    Evidence
                       |
             +---------+---------+
             |         |         |
             v         v         v
         Logistics  Product    Legal
             \         |         /
              \        |        /
               +-------+-------+
                       |
                       v
              Addendum Reconciler
                       |
                       v
                   Validator
                   /       \
                Retry      Accept
                  |          |
                  v          v
             Re-extract   JSON/Q&A
                              |
                              v
                          Citations
52. The Two Defining Rules
Rule 1

No important final fact exists without evidence.

Rule 2

Every important behavior can be tested, traced, measured and explained.

53. What the Final Reviewer Should Be Able to Say

After seeing the project, the reviewer should be able to verify that:

this is a real search engine
retrieval is hybrid
exact identifiers are handled
results are reranked
metadata filters work
citations are first-class
agents have distinct responsibilities
agents operate through the retrieval tool
work can happen in parallel
addendums are explicitly reconciled
validation can reject incorrect output
rejected fields are retried
missing facts are not hallucinated
20 structured fields are extracted
retrieval quality is measured
extraction quality is measured
the code is modular and tested
indexing is incremental
unseen bids work without code changes
the system is observable
the UI provides a usable interface
the demo proves the important functionality
54. Antigravity Operating Rules

When implementing this project:

Read plan.md before changing architecture.
Follow the phase order.
Do not implement future phases early unless explicitly requested.
Do not overwrite working components unnecessarily.
Preserve tests after refactors.
Do not introduce bid-specific hard-coded logic.
Do not introduce secrets.
Do not fabricate evaluation data.
Prefer simple, testable components over complex abstractions.
Every feature must have an acceptance criterion.
Every phase must end with tests.
Do not claim a feature is complete until it is demonstrated against real data.
Keep external providers behind adapters.
Keep source evidence attached throughout the pipeline.
Prefer deterministic processing wherever possible.
Do not sacrifice retrieval correctness for UI polish.
55. Final Project Definition

The completed system should be describable as:

An evidence-first, hybrid RAG and multi-agent RFP intelligence platform that converts heterogeneous procurement documents into searchable evidence, citation-backed structured bid intelligence, and grounded natural-language answers. The platform explicitly reconciles addendums, validates extracted facts, supports incremental indexing, quantitatively evaluates retrieval and extraction quality, and generalizes to unseen bid folders without hard-coded bid-specific logic.

This is the final target architecture and implementation plan.
