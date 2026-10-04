"""LangGraph multi-agent orchestration workflow definition."""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    addendum_node,
    entity_node,
    legal_node,
    logistics_node,
    product_node,
    retry_node,
    serialization_node,
    validator_node,
)
from app.graph.state import RFPState


def should_retry(state: RFPState) -> str:
    """Evaluate validation results and decide whether to route to retry or serialize."""
    val_result = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    if val_result and not val_result.is_valid and retry_count < max_retries:
        return "retry_agent"
    return "serializer"


def create_extraction_graph() -> StateGraph:
    """Construct and compile the multi-agent extraction graph."""
    builder = StateGraph(RFPState)

    # 1. Register specialist agents
    builder.add_node("entity_specialist", entity_node)
    builder.add_node("logistics_specialist", logistics_node)
    builder.add_node("product_specialist", product_node)
    builder.add_node("legal_specialist", legal_node)

    # 2. Register reconciliation, validation, repair, and serialization nodes
    builder.add_node("addendum_reconciler", addendum_node)
    builder.add_node("validator", validator_node)
    builder.add_node("retry_agent", retry_node)
    builder.add_node("serializer", serialization_node)

    # 3. Add parallel fan-out edges from START to specialists
    builder.add_edge(START, "entity_specialist")
    builder.add_edge(START, "logistics_specialist")
    builder.add_edge(START, "product_specialist")
    builder.add_edge(START, "legal_specialist")

    # 4. Fan-in edges from specialists to Addendum Reconciler
    builder.add_edge("entity_specialist", "addendum_reconciler")
    builder.add_edge("logistics_specialist", "addendum_reconciler")
    builder.add_edge("product_specialist", "addendum_reconciler")
    builder.add_edge("legal_specialist", "addendum_reconciler")

    # 5. Addendum reconciler to Validator
    builder.add_edge("addendum_reconciler", "validator")

    # 6. Conditional edge from Validator to RetryAgent or Serializer
    builder.add_conditional_edges(
        "validator",
        should_retry,
        {
            "retry_agent": "retry_agent",
            "serializer": "serializer",
        },
    )

    # 7. Loop back from RetryAgent to Validator for re-auditing
    builder.add_edge("retry_agent", "validator")

    # 8. Finish at Serializer
    builder.add_edge("serializer", END)

    return builder.compile()
