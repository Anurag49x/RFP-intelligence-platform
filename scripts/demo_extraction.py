"""Demo script to run and display structured 20-field extraction for Bid1 and Bid2."""

import json
from app.graph.runner import RFPExtractionPipeline


def main():
    pipeline = RFPExtractionPipeline()

    for bid_id in ["Bid1", "Bid2"]:
        print(f"\n{'='*70}")
        print(f"  RUNNING EXTRACTION FOR {bid_id}")
        print(f"{'='*70}\n")
        state = pipeline.run_extraction(bid_id)
        final_output = state["final_output"]

        print(f"\n--- Extracted 20 Fields for {bid_id} (Aliased Format) ---")
        aliased = final_output.to_aliased_dict()
        print(json.dumps(aliased, indent=2))

        print(f"\n--- Addendum Changes ({len(state['addendum_changes'])}) ---")
        for ch in state["addendum_changes"]:
            print(f"  [{ch.field}] -> {ch.new_value} ({ch.change_type} via Addendum {ch.addendum_number} in {ch.file_name})")

        val_res = state["validation_result"]
        print(f"\n--- Validation Summary ---")
        print(f"  Is Valid: {val_res.is_valid if val_res else 'N/A'}")
        print(f"  Passed Fields: {len(val_res.passed_fields) if val_res else 0}")
        print(f"  Rejected Fields: {len(val_res.rejected_fields) if val_res else 0}")
        print(f"  Retry Attempts: {state['retry_count']}")


if __name__ == "__main__":
    main()
