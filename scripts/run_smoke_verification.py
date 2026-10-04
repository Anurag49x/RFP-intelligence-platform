"""Minimal, target-driven Smoke Verification Suite for Real Cloud APIs (Tests A to H).

Executes EXACTLY:
A. Groq LLM — 1 real call
B. Groq OCR — 1 real call
C. Jina Embeddings — 1 real call
D. Jina Reranker — 1 real call
E. Qdrant health check — 1 call
F. ONE real retrieval query
G. ONE real Q&A query
H. ONE real extraction for Bid1 (using 1 agent / focused fields)
"""

import io
import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.config import get_settings
from app.embeddings.jina import JinaEmbeddingProvider
from app.extraction.llm import LLMExtractor
from app.ingestion.ocr import GroqOCRProvider
from app.lexical.bm25 import BM25Index
from app.qa.engine import QAEngine
from app.qa.models import AskRequest
from app.rerankers.jina import JinaRerankerProvider
from app.retrieval.hybrid import HybridSearchEngine
from app.schemas.canonical import Evidence, SearchFilters, SearchResult
from app.vectorstore.qdrant import QdrantVectorStore


def create_synthetic_ocr_image() -> bytes:
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    text_content = "Dallas ISD RFP JA-207652\nDue Date: October 10, 2024\nDell Latitude 5550 Laptops"
    draw.text((20, 30), text_content, fill=(0, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def run_smoke_tests():
    settings = get_settings()
    results = {}
    print("\n=======================================================")
    print("      REAL API SMOKE & INTEGRATION SUITE (A to H)")
    print("=======================================================\n")

    # A. Groq LLM
    print("[A] Groq LLM — 1 Real Call...")
    t0 = time.time()
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": "Return exactly: integration_test_ok"}],
            temperature=0.0,
            max_tokens=20,
        )
        txt = resp.choices[0].message.content.strip()
        elapsed_a = round((time.time() - t0) * 1000, 2)
        print(f"  [+] Groq LLM ({settings.groq_model}): PASS ({elapsed_a}ms) -> '{txt}'")
        results["A_groq_llm"] = {"status": "PASS", "elapsed_ms": elapsed_a, "output": txt}
    except Exception as e:
        elapsed_a = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Groq LLM: FAIL ({elapsed_a}ms) -> {e}")
        results["A_groq_llm"] = {"status": "FAIL", "elapsed_ms": elapsed_a, "error": str(e)}

    # B. Groq Vision OCR
    print("\n[B] Groq Vision OCR — 1 Real Call...")
    t0 = time.time()
    try:
        ocr_p = GroqOCRProvider(api_key=settings.groq_api_key, model=settings.groq_ocr_model)
        img_bytes = create_synthetic_ocr_image()
        ocr_res = ocr_p.ocr_image(img_bytes, mime_type="image/png", page_number=1)
        elapsed_b = round((time.time() - t0) * 1000, 2)
        print(f"  [+] Groq Vision OCR ({settings.groq_ocr_model}): PASS ({elapsed_b}ms) -> snippet: '{ocr_res.text[:50]}...'")
        results["B_groq_ocr"] = {"status": "PASS", "elapsed_ms": elapsed_b, "output": ocr_res.text[:100]}
    except Exception as e:
        elapsed_b = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Groq Vision OCR: FAIL ({elapsed_b}ms) -> {e}")
        results["B_groq_ocr"] = {"status": "FAIL", "elapsed_ms": elapsed_b, "error": str(e)}

    # C. Jina Embeddings
    print("\n[C] Jina Embeddings — 1 Real Call...")
    t0 = time.time()
    try:
        emb_p = JinaEmbeddingProvider(api_key=settings.jina_api_key)
        vecs = emb_p.embed_documents(["Dallas ISD RFP laptop submission deadline"])
        elapsed_c = round((time.time() - t0) * 1000, 2)
        dim = len(vecs[0]) if vecs else 0
        print(f"  [+] Jina Embeddings ({emb_p.model_name}): PASS ({elapsed_c}ms) -> {len(vecs)} vector, dim={dim}")
        results["C_jina_embeddings"] = {"status": "PASS", "elapsed_ms": elapsed_c, "dimension": dim}
    except Exception as e:
        elapsed_c = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Jina Embeddings: FAIL ({elapsed_c}ms) -> {e}")
        results["C_jina_embeddings"] = {"status": "FAIL", "elapsed_ms": elapsed_c, "error": str(e)}

    # D. Jina Reranker
    print("\n[D] Jina Reranker — 1 Real Call...")
    t0 = time.time()
    try:
        rerank_p = JinaRerankerProvider(api_key=settings.jina_api_key)
        ev1 = Evidence(bid_id="Bid1", file_name="Addendum.pdf", page_number=1, chunk_id="c1", text="Due date is Oct 10 2024", document_type="addendum")
        ev2 = Evidence(bid_id="Bid1", file_name="RFP.pdf", page_number=2, chunk_id="c2", text="Laptop specs", document_type="rfp")
        c1 = SearchResult(rank=1, chunk_id="c1", text="Due date is Oct 10 2024", score=0.5, retrieval_source="dense", evidence=ev1)
        c2 = SearchResult(rank=2, chunk_id="c2", text="Laptop specs", score=0.6, retrieval_source="dense", evidence=ev2)
        reranked = rerank_p.rerank("submission deadline", [c1, c2], top_k=1)
        elapsed_d = round((time.time() - t0) * 1000, 2)
        top_cid = reranked[0].chunk_id if reranked else "none"
        print(f"  [+] Jina Reranker ({rerank_p.model_name}): PASS ({elapsed_d}ms) -> Top chunk: {top_cid}")
        results["D_jina_reranker"] = {"status": "PASS", "elapsed_ms": elapsed_d, "top_chunk": top_cid}
    except Exception as e:
        elapsed_d = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Jina Reranker: FAIL ({elapsed_d}ms) -> {e}")
        results["D_jina_reranker"] = {"status": "FAIL", "elapsed_ms": elapsed_d, "error": str(e)}

    # E. Qdrant Health Check
    print("\n[E] Qdrant Health Check — 1 Check...")
    t0 = time.time()
    try:
        qdrant = QdrantVectorStore()
        info = qdrant.client.get_collections()
        elapsed_e = round((time.time() - t0) * 1000, 2)
        print(f"  [+] Qdrant Vector Store: PASS ({elapsed_e}ms) -> Collections count: {len(info.collections)}")
        results["E_qdrant_health"] = {"status": "PASS", "elapsed_ms": elapsed_e, "collections": len(info.collections)}
    except Exception as e:
        elapsed_e = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Qdrant Vector Store: FAIL ({elapsed_e}ms) -> {e}")
        results["E_qdrant_health"] = {"status": "FAIL", "elapsed_ms": elapsed_e, "error": str(e)}

    # F. ONE Real Retrieval Query
    print("\n[F] ONE Real Retrieval Query...")
    t0 = time.time()
    try:
        bm25 = BM25Index.load("data/bm25/corpus.jsonl")
        engine = HybridSearchEngine(
            embedding_provider=JinaEmbeddingProvider(api_key=settings.jina_api_key),
            vector_store=QdrantVectorStore(),
            bm25_index=bm25,
            reranker=JinaRerankerProvider(api_key=settings.jina_api_key),
        )
        res = engine.search("What is the proposal submission deadline for Dallas ISD?", top_k=3, filters=SearchFilters(bid_id="Bid1"), use_reranker=True)
        elapsed_f = round((time.time() - t0) * 1000, 2)
        top_text = res.results[0].text[:80] if res.results else "No hits"
        print(f"  [+] Hybrid Retrieval Query: PASS ({elapsed_f}ms) -> Top match: '{top_text}...'")
        results["F_real_retrieval"] = {"status": "PASS", "elapsed_ms": elapsed_f, "top_text": top_text}
    except Exception as e:
        elapsed_f = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Hybrid Retrieval Query: FAIL ({elapsed_f}ms) -> {e}")
        results["F_real_retrieval"] = {"status": "FAIL", "elapsed_ms": elapsed_f, "error": str(e)}

    # G. ONE Real Q&A Query
    print("\n[G] ONE Real Q&A Query...")
    t0 = time.time()
    try:
        qa_engine = QAEngine(search_engine=engine, api_key=settings.groq_api_key, model_name=settings.groq_model)
        ask_req = AskRequest(question="What is the submission deadline for Dallas ISD?", bid_id="Bid1", top_k=3)
        ask_res = qa_engine.answer_question(ask_req)
        elapsed_g = round((time.time() - t0) * 1000, 2)
        print(f"  [+] Grounded Q&A Query: PASS ({elapsed_g}ms)")
        print(f"      Answer: '{ask_res.answer}'")
        print(f"      Citations count: {len(ask_res.citations)}")
        results["G_real_qa"] = {"status": "PASS", "elapsed_ms": elapsed_g, "answer": ask_res.answer, "citations_count": len(ask_res.citations)}
    except Exception as e:
        elapsed_g = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Grounded Q&A Query: FAIL ({elapsed_g}ms) -> {e}")
        results["G_real_qa"] = {"status": "FAIL", "elapsed_ms": elapsed_g, "error": str(e)}

    # H. ONE Real Extraction for Bid1
    print("\n[H] ONE Real Field Extraction for Bid1...")
    t0 = time.time()
    try:
        extractor = LLMExtractor(api_key=settings.groq_api_key, model_name=settings.groq_model)
        # Fetch top evidence passages for due_date
        due_res = engine.search("due date closing deadline submission", top_k=3, filters=SearchFilters(bid_id="Bid1"))
        passages = [r.evidence for r in due_res.results]
        ext_res = extractor.extract_fields(field_names=["due_date", "issuing_organization"], evidence_passages=passages, bid_id="Bid1")
        elapsed_h = round((time.time() - t0) * 1000, 2)
        val_due = ext_res.get("due_date").value if ext_res.get("due_date") else None
        print(f"  [+] Real Extraction (Bid1): PASS ({elapsed_h}ms) -> Extracted due_date: '{val_due}'")
        results["H_real_extraction"] = {"status": "PASS", "elapsed_ms": elapsed_h, "due_date": val_due}
    except Exception as e:
        elapsed_h = round((time.time() - t0) * 1000, 2)
        print(f"  [-] Real Extraction (Bid1): FAIL ({elapsed_h}ms) -> {e}")
        results["H_real_extraction"] = {"status": "FAIL", "elapsed_ms": elapsed_h, "error": str(e)}

    print("\n=======================================================")
    print("       SMOKE & INTEGRATION SUMMARY RESULT")
    print("=======================================================")
    all_passed = all(r.get("status") == "PASS" for r in results.values())
    for k, v in results.items():
        st = v["status"]
        lat = v.get("elapsed_ms", 0)
        print(f"  {k:20s}: {st:4s} ({lat:7.2f}ms)")

    if all_passed:
        print("\nALL SMOKE TESTS A-H PASSED SUCCESSFULLY!")
    else:
        print("\nSOME SMOKE TESTS FAILED. Inspect outputs above.")

    return results


if __name__ == "__main__":
    run_smoke_tests()
