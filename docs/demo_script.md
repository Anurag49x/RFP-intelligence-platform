# RFP Intelligence Platform — Video Demo Script (5–10 Minutes)

This script provides a structured guide for demonstrating the **RFP Intelligence Platform: RAG Search Engine & Multi-Agent System**.

---

## Demo Agenda & Timeline

| Time Window | Section | Key Features Demonstrated | Command / UI View |
|---|---|---|---|
| **0:00 – 1:00** | **System Architecture & Overview** | Problem statement, dual-branch retrieval, LangGraph agents | `docs/architecture.svg` / UI Dashboard |
| **1:00 – 3:00** | **Hybrid RAG Search** | Dense embeddings, BM25 exact match, RRF fusion, Jina reranker | `POST /search` / "Hybrid Search" Tab |
| **3:00 – 5:00** | **Addendum Reconciliation** | Superseding due date modification in Bid1 (Oct 1 -> Oct 10) | `POST /ask` / "Addendum History" Tab |
| **5:00 – 7:00** | **Structured 20-Field Extraction** | Parallel specialist agents, citation validation, null safety | `POST /extract` / "20-Field Extraction" Tab |
| **7:00 – 8:00** | **Negative / Unsupported Q&A** | Zero hallucination verification ("Not found in documents.") | `POST /ask` / "Evidence Q&A" Tab |
| **8:00 – 9:00** | **Agent Observability Trace** | Step-by-step trace of agent fan-out, validator, and retry | `outputs/traces/sample_extraction_trace.md` |
| **9:00 – 10:00** | **Unseen Bid Generalization** | Live indexing & extraction of unseen bid folder with zero code changes | `python -m scripts.test_unseen_bid` |

---

## Detailed Step-by-Step Script

### 1. System Architecture & Overview (0:00 – 1:00)
- **Voiceover**: *"Welcome to the demonstration of the RFP Intelligence Platform. Complex procurement bids are fragmented across portal HTML pages, RFP documents, addendums, hardware specifications, and affidavits. Simple vector search fails because addendums legally modify requirements. Our platform implements an evidence-first system with dual-branch hybrid retrieval and a LangGraph multi-agent architecture."*
- **Action**: Open the UI Dashboard at `http://127.0.0.1:8501` and display `docs/architecture.svg`.

---

### 2. Hybrid RAG Search (1:00 – 3:00)
- **Voiceover**: *"We combine Jina v3 1024-dimensional dense semantic embeddings with BM25 lexical search and Reciprocal Rank Fusion, followed by listwise cross-attention reranking."*
- **Action**:
  1. Navigate to **🔍 Hybrid Search** tab.
  2. Query: `"Dell Latitude 5550 with Intel Core Ultra 5"` on Bid2.
  3. Show the retrieved chunks, cosine similarity scores, page numbers, and exact technical snippets.
  4. Query: `"#E20P4600040"` to demonstrate exact alphanumeric procurement identifier retrieval via BM25.

---

### 3. Addendum Reasoning & Due Date Override (3:00 – 5:00)
- **Voiceover**: *"In Bid 1 (Dallas ISD), the original proposal due date was October 1, 2024. Addendum 2 explicitly revised and extended the due date to October 10, 2024. Our Addendum Reconciler automatically detects amendments and ensures the latest addendum takes precedence."*
- **Action**:
  1. Navigate to **📜 Addendum History** tab. Show the detected `MODIFICATION` event for `due_date`.
  2. Navigate to **💬 Evidence Q&A** tab.
  3. Ask: `"What is the final deadline for Bid1 after all addendums?"`
  4. Show the answer citing `Bid_1_Addendum_2.pdf (Page 1)` with exact timestamp `October 10, 2024 at 2:00 PM CST`.

---

### 4. Structured 20-Field Extraction (5:00 – 7:00)
- **Voiceover**: *"Our LangGraph pipeline fans out to specialized agents: Entity Specialist, Logistics Specialist, Product Specialist, and Legal Specialist. Each agent extracts structured fields supported strictly by source citations. If a requirement is absent, our rule enforces NO EVIDENCE -> NO VALUE."*
- **Action**:
  1. Navigate to **📋 20-Field Extraction** tab.
  2. Select `Bid1` and click **Run Multi-Agent Extraction**.
  3. Inspect the 20-field table. Highlight `Bid Number`, `Due Date`, `Product Specification`, `Bid Bond Requirement`, and verified citation links.

---

### 5. Negative & Unsupported Query Handling (7:00 – 8:00)
- **Voiceover**: *"A critical benchmark requirement is preventing hallucinations. When information does not exist in the documents, the system must report 'Not found in documents.' rather than guessing."*
- **Action**:
  1. In **💬 Evidence Q&A**, ask: `"What is the required vendor employee headcount?"`
  2. Show the response: `Not found in documents.` with confidence `0.0` and `0` citations.

---

### 6. Multi-Agent Observability Trace (8:00 – 9:00)
- **Voiceover**: *"We provide full observability through structured spans capturing latencies, chunk IDs, LLM outputs, validator decisions, and targeted retry repairs."*
- **Action**:
  1. Navigate to **🕵️ Agent Observability Trace** tab.
  2. Show the sequence: `Orchestrator -> Specialists -> Addendum Reconciler -> Validator -> Serializer`.

---

### 7. Unseen Bid Generalization (9:00 – 10:00)
- **Voiceover**: *"To prove generalization, we test the system on an unseen bid folder with completely new filenames and documents with zero source code modifications."*
- **Action**:
  1. Run command: `python -m scripts.test_unseen_bid` in terminal.
  2. Show live discovery, ingestion, chunking, indexing, addendum override, and structured extraction completing with `application_code_changed = false`.
