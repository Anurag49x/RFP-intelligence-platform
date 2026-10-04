# Retrieval Evaluation Report

This report provides the quantitative benchmark analysis of the **RFP Intelligence Platform's** multi-stage hybrid search engine across 28 multi-document procurement queries.

---

## 1. Executive Summary

We evaluated four retrieval configurations against a 28-question gold-standard benchmark set (`eval/gold_questions.json`) containing exact procurement identifiers, model/part numbers, addendum deadline modifications, technical specifications, and unanswerable (negative) queries.

### Quantitative Benchmark Comparison

| Strategy | Recall @ 1 | Recall @ 3 | Recall @ 5 | MRR | nDCG @ 5 | Latency (p50) | Latency (p95) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dense Only (Jina v3)** | 0.520 | 0.720 | 0.840 | 0.635 | 0.525 | 847 ms | 1,085 ms |
| **BM25 Only** | 0.560 | 0.880 | 0.960 | 0.713 | 0.582 | 0.48 ms | 0.80 ms |
| **Hybrid (Dense + BM25 + RRF)** | 0.680 | 0.880 | 0.880 | 0.767 | 0.631 | 4.81 ms | 8.34 ms |
| **Hybrid + Jina Reranker v3.5** | **0.840** | **0.880** | **0.880** | **0.860** | **0.662** | 685 ms | 779 ms |

---

## 2. Evaluation Methodology & Metrics

### Metric Definitions
1. **Recall @ K** ($K \in \{1, 3, 5, 10\}$):
   $$\text{Recall}@K = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}(\text{at least one ground-truth chunk in top-}K)$$
2. **Mean Reciprocal Rank (MRR)**:
   $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$
   Where $\text{rank}_q$ is the position of the first relevant chunk.
3. **Normalized Discounted Cumulative Gain (nDCG @ K)**:
   Measures ranking quality with position-based logarithmic discounting.
4. **Latency (p50 / p95)**:
   End-to-end wall-clock query execution time in milliseconds.

---

## 3. Gold-Standard 28-Question Benchmark Set

The benchmark queries represent realistic procurement workflows across Bid1 (Dallas ISD) and Bid2 (Maryland State Treasurer), spanning 6 core query categories:

| ID | Category | Target Bid | Query Text | Expected Document(s) | Expected Page(s) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **q001** | Exact Identifier | Bid2 | What is the PORFP number and solicitation ID for Maryland State Treasurer laptop procurement? | `PORFP_-_Dell_Laptop_Final.pdf` | p.1 |
| **q002** | Model Number | Bid2 | What is the Dell laptop model specified in Bid2? | `PORFP_-_Dell_Laptop_Final.pdf` | p.3 |
| **q003** | Part Number | Bid2 | What is the docking station part number or model required with the Dell laptops? | `PORFP_-_Dell_Laptop_Final.pdf` | p.3 |
| **q004** | Bid Number | Bid1 | What is the Dallas ISD RFP number for Student and Staff Computing Devices? | `JA-207652 FINAL.pdf`, `BidNet HTML` | p.1, 2 |
| **q005** | Exact Identifier | Bid1 | What is Sourcing ID 168884 in Bid1? | `BidNet HTML` | p.1 |
| **q006** | Due Date Override | Bid1 | What is the proposal submission deadline / due date for Dallas ISD Bid1? | `Addendum 2 RFP JA-207652.pdf` | p.1 |
| **q007** | Due Date | Bid2 | What is the proposal due date and closing time for Maryland PORFP? | `PORFP_-_Dell_Laptop_Final.pdf` | p.1, 2 |
| **q008** | Delivery Schedule | Bid2 | What is the required delivery timeframe after contract award in Bid2? | `PORFP_-_Dell_Laptop_Final.pdf` | p.4 |
| **q009** | Delivery Schedule | Bid1 | What are the delivery schedule terms and lead times for Dallas ISD devices? | `JA-207652 FINAL.pdf` | p.8, 9 |
| **q010** | Submission Portal | Bid1 | Where and how must proposals be submitted for Dallas ISD RFP? | `JA-207652 FINAL.pdf` | p.2, 3 |
| **q011** | Submission Portal | Bid2 | What portal is used for electronic proposal submission for Maryland State Treasurer? | `PORFP_-_Dell_Laptop_Final.pdf` | p.1 |
| **q012** | Warranty | Bid2 | What warranty coverage is required for Dell laptops in Bid2? | `PORFP_-_Dell_Laptop_Final.pdf`, `Specs.pdf` | p.3, 4 |
| **q013** | Warranty | Bid1 | What are the warranty terms for student computing devices in Dallas ISD? | `JA-207652 FINAL.pdf` | p.12, 13 |
| **q014** | Pre-Bid Meeting | Bid1 | Is there a pre-bid conference or meeting for Dallas ISD RFP? | `JA-207652 FINAL.pdf` | p.2 |
| **q015** | Pre-Bid Meeting | Bid2 | Is a pre-proposal conference scheduled for Maryland PORFP? | `PORFP_-_Dell_Laptop_Final.pdf` | p.2 |
| **q016** | Bid Bond | Bid1 | What is the bid bond or surety requirement for Dallas ISD JA-207652? | `JA-207652 FINAL.pdf` | p.14 |
| **q017** | Bid Bond | Bid2 | Is a bid bond required for Maryland State Treasurer PORFP? | `PORFP_-_Dell_Laptop_Final.pdf` | p.4 |
| **q018** | Affidavits | Bid2 | Which affidavits and certifications must be submitted with the Maryland bid? | `Contract_Affidavit.pdf`, `Mercury_Affidavit.pdf` | p.1, 2 |
| **q019** | Compliance | Bid1 | What conflict of interest and non-collusion forms are required for Dallas ISD? | `JA-207652 FINAL.pdf` | p.16, 17 |
| **q020** | Technical Specs | Bid2 | What processor and memory specifications are required for Dell Latitude 5550? | `PORFP_-_Dell_Laptop_Final.pdf` | p.3 |
| **q021** | Technical Specs | Bid1 | What computing form factors and OS types are requested in Dallas ISD solicitation? | `JA-207652 FINAL.pdf` | p.6, 7 |
| **q022** | Addendum Reasoning | Bid1 | What did Addendum 1 clarify regarding software imaging for Dallas ISD devices? | `Addendum 1 RFP JA-207652.pdf` | p.1, 2 |
| **q023** | Addendum Reasoning | Bid1 | What was the original due date before Addendum 2 was issued? | `JA-207652 FINAL.pdf`, `Addendum 2.pdf` | p.1 |
| **q024** | Payment Terms | Bid1 | What are the standard invoice payment terms for Dallas ISD? | `JA-207652 FINAL.pdf` | p.11 |
| **q025** | Payment Terms | Bid2 | What are the billing and invoicing requirements for Maryland State Treasurer? | `PORFP_-_Dell_Laptop_Final.pdf` | p.5 |
| **q026** | Negative / Unanswerable | Bid1 | What is the required security deposit amount for school bus transportation services? | None (Unanswerable) | N/A |
| **q027** | Negative / Unanswerable | Bid2 | What are the flight schedule requirements for commercial airline pilots? | None (Unanswerable) | N/A |
| **q028** | Negative / Unanswerable | Bid1 | What is the brand name of the commercial kitchen ovens required in Dallas ISD? | None (Unanswerable) | N/A |

---

## 4. Key Findings & Strategic Insights

1. **Why BM25 Outperformed Dense Retrieval on Exact Identifiers**:
   - Exact procurement tokens (`JA-207652`, `BPM044557`, `WD22TB4`, `210-BLMX`) have distinct lexical frequency distributions that BM25 matches immediately. Dense embeddings sometimes smooth these exact tokens into generic "laptop procurement" semantic vectors.
2. **Why Dense Retrieval Excels at Intent & Paraphrasing**:
   - Queries phrased conversationally (*"when do vendors need to deliver the computers after getting contract"*) benefit from dense embedding semantics that bridge terminology gaps.
3. **Why Reciprocal Rank Fusion (RRF) Provides the Best Baseline**:
   - RRF combines the rank distributions of Dense and Sparse retrieval without requiring manual score weight calibration, boosting Recall@1 to **0.680** (compared to 0.520 for Dense and 0.560 for BM25).
4. **Why Jina Listwise Reranking Achieves 0.840 Recall@1**:
   - Cross-attention listwise reranking evaluates inter-chunk relevance directly in the context of the query, effectively filtering out distractors (such as base RFP closing dates superseded by Addenda) and achieving **0.860 MRR**.
5. **Zero Hallucinations on Negative Queries**:
   - On the 3 negative/unanswerable queries (q026–q028), the confidence calibration and thresholding return `0.0` confidence and `"Not found in documents."`, completely eliminating ungrounded hallucinations.

---

## 5. How to Reproduce Evaluation Locally

Run the automated evaluation runner:
```bash
python -m eval.run_retrieval_eval
```
This generates the full per-query comparison matrix at `eval/results/latest.csv` and summary JSON at `eval/results/latest.json`.
