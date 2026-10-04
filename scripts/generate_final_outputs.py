"""Generate final 20-field extracted JSON files for Bid1 and Bid2."""

import json
from pathlib import Path
from app.graph.runner import RFPExtractionPipeline


def generate_final_bid_outputs():
    pipeline = RFPExtractionPipeline()
    out_dir = Path("outputs").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for bid_id in ["Bid1", "Bid2"]:
        print(f"Extracting {bid_id}...")
        output = pipeline.extract_bid(bid_id)
        aliased_data = output.to_aliased_dict()

        target_file = out_dir / f"{bid_id}_extracted.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(aliased_data, f, indent=2)

        print(f"Saved {bid_id} extracted JSON ({len(aliased_data)} fields) to {target_file}")


if __name__ == "__main__":
    generate_final_bid_outputs()
