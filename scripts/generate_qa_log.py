"""Generate actual outputs/qa_log.json running the required 10 evaluation questions."""

import json
from pathlib import Path
from app.qa.engine import QAEngine
from app.qa.models import AskRequest


REQUIRED_QUESTIONS = [
    {"question": "What is the final deadline for Bid1?", "bid_id": "Bid1"},
    {"question": "Which affidavits are required for Bid2?", "bid_id": "Bid2"},
    {"question": "What changed in Addendum 2?", "bid_id": "Bid1"},
    {"question": "Compare warranty requirements between Bid1 and Bid2.", "bid_id": None},
    {"question": "Is a bid bond required, and if so, how much?", "bid_id": "Bid1"},
    {"question": "What is the Dell laptop model specified in Bid2?", "bid_id": "Bid2"},
    {"question": "What processor is specified for the laptops in Bid2?", "bid_id": "Bid2"},
    {"question": "What is E20P4600040?", "bid_id": "Bid2"},
    {"question": "What delivery time is required for Bid2?", "bid_id": "Bid2"},
    {"question": "What is the required vendor employee headcount?", "bid_id": "Bid1"},
]


def generate_qa_log(output_file: str = "outputs/qa_log.json") -> Path:
    engine = QAEngine()
    qa_results = []

    print(f"\nExecuting {len(REQUIRED_QUESTIONS)} evaluation Q&A queries against real corpus...\n")

    for i, item in enumerate(REQUIRED_QUESTIONS, start=1):
        q_text = item["question"]
        bid_id = item["bid_id"]
        req = AskRequest(question=q_text, bid_id=bid_id, top_k=5, include_trace=True)
        response = engine.answer_question(req)

        entry = {
            "query_index": i,
            "question": response.question,
            "bid_id": response.bid_id,
            "intent": response.intent.value,
            "answer": response.answer,
            "citations": [c.model_dump() for c in response.citations],
            "confidence": response.confidence,
            "validation_status": response.validation_status,
            "retrieval_metadata": response.retrieval_metadata,
        }
        qa_results.append(entry)
        print(f"[{i}/10] Q: {q_text}")
        print(f"       A: {response.answer[:100]}... (Citations: {len(response.citations)}, Status: {response.validation_status})\n")

    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(qa_results, f, indent=2)

    print(f"Successfully wrote {len(qa_results)} Q&A evaluation records to {out_path}")
    return out_path


if __name__ == "__main__":
    generate_qa_log()
