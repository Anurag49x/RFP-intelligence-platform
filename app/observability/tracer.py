"""Structured observability and tracing engine for multi-agent execution and Q&A."""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from app.logging import logger


class TraceSpan:
    """Individual span representing an agent execution or retrieval step."""

    def __init__(self, name: str, parent_id: Optional[str] = None):
        self.span_id = str(uuid.uuid4())[:8]
        self.parent_id = parent_id
        self.name = name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.latency_ms: float = 0.0
        self.status = "running"
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, event_name: str, payload: Optional[Dict[str, Any]] = None):
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_name,
            "payload": payload or {},
        })

    def finish(self, status: str = "success"):
        self.end_time = time.time()
        self.latency_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "attributes": self.attributes,
            "events": self.events,
        }


class WorkflowTracer:
    """Complete execution trace capturing end-to-end multi-agent workflow."""

    def __init__(self, workflow_name: str, run_id: Optional[str] = None):
        self.run_id = run_id or f"run_{str(uuid.uuid4())[:8]}"
        self.workflow_name = workflow_name
        self.start_time = time.time()
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.spans: List[TraceSpan] = []
        self._current_span: Optional[TraceSpan] = None

    def start_span(self, name: str, parent_id: Optional[str] = None) -> TraceSpan:
        span = TraceSpan(name=name, parent_id=parent_id)
        self.spans.append(span)
        self._current_span = span
        return span

    def to_dict(self) -> Dict[str, Any]:
        total_latency_ms = round((time.time() - self.start_time) * 1000.0, 2)
        return {
            "run_id": self.run_id,
            "workflow": self.workflow_name,
            "created_at": self.created_at,
            "total_latency_ms": total_latency_ms,
            "spans_count": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }

    def save_json(self, output_path: str | Path) -> Path:
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved trace {self.run_id} to {p}")
        return p

    def save_markdown(self, output_path: str | Path) -> Path:
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()

        md_lines = [
            f"# Multi-Agent Execution Trace: `{data['workflow']}`",
            f"- **Run ID**: `{data['run_id']}`",
            f"- **Timestamp**: `{data['created_at']}`",
            f"- **Total Latency**: `{data['total_latency_ms']} ms`",
            f"- **Total Spans**: `{data['spans_count']}`",
            "",
            "## Execution Flow Hierarchy",
            "",
            "```mermaid",
            "sequenceDiagram",
            "    autonumber",
            "    participant O as Orchestrator",
            "    participant E as Entity Specialist",
            "    participant L as Logistics Specialist",
            "    participant P as Product Specialist",
            "    participant G as Legal Specialist",
            "    participant A as Addendum Reconciler",
            "    participant V as Validator",
            "    participant R as Retry Agent",
            "    participant S as Serializer",
            "",
            "    O->>E: Fan-Out Entity Fields",
            "    O->>L: Fan-Out Logistics Fields",
            "    O->>P: Fan-Out Product Fields",
            "    O->>G: Fan-Out Legal Fields",
            "    E-->>A: Return Extracted Fields",
            "    L-->>A: Return Extracted Fields",
            "    P-->>A: Return Extracted Fields",
            "    G-->>A: Return Extracted Fields",
            "    A->>V: Pass Reconciled Fields",
            "    alt Rejected Fields Exist",
            "        V->>R: Route to Retry Agent",
            "        R->>V: Re-Audit Repaired Fields",
            "    end",
            "    V->>S: Validator Passed",
            "    S->>O: Final BidOutput",
            "```",
            "",
            "## Span Details",
            "",
            "| Step | Span Name | Status | Latency (ms) | Key Attributes |",
            "|---|---|---|---|---|",
        ]

        for i, s in enumerate(data["spans"], start=1):
            attrs_summary = ", ".join(f"{k}={v}" for k, v in list(s["attributes"].items())[:3])
            md_lines.append(
                f"| {i} | `{s['name']}` | `{s['status']}` | {s['latency_ms']} | {attrs_summary or 'N/A'} |"
            )

        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines) + "\n")

        logger.info(f"Saved Markdown trace summary to {p}")
        return p
