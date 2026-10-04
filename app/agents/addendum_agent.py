"""Addendum reconciliation agent node for multi-agent graph."""

from typing import Any, Dict, List, Optional, Tuple
from app.logging import logger
from app.reconciliation.models import AddendumChange
from app.reconciliation.reconciler import AddendumReconciler
from app.schemas.canonical import FieldResult


class AddendumAgent:
    """Agent node responsible for reconciling extracted fields against addendum modifications."""

    def __init__(self, reconciler: Optional[AddendumReconciler] = None):
        self.reconciler = reconciler or AddendumReconciler()

    def run(
        self,
        bid_id: str,
        extracted_fields: Dict[str, FieldResult],
    ) -> Tuple[Dict[str, FieldResult], List[AddendumChange]]:
        """Execute addendum reconciliation over all currently extracted fields."""
        logger.info(f"AddendumAgent running for bid '{bid_id}'...")
        reconciled_fields, changes = self.reconciler.reconcile(
            bid_id=bid_id,
            current_fields=extracted_fields,
        )
        if changes:
            logger.info(f"AddendumAgent applied {len(changes)} addendum changes for bid '{bid_id}'")
            for ch in changes:
                logger.info(
                    f"  - Field [{ch.field}]: '{ch.original_value}' -> '{ch.new_value}' ({ch.change_type} per Addendum {ch.addendum_number})"
                )
        else:
            logger.info(f"AddendumAgent found no overriding changes for bid '{bid_id}'")

        return reconciled_fields, changes
