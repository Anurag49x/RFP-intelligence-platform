"""Generate comprehensive, in-depth PDF report detailing the LangGraph Multi-Agent Extraction Pipeline."""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding running headers and dynamic page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Draw header on pages after page 1
        if self._pageNumber > 1:
            self.drawString(50, 750, "RFP Intelligence Platform — Multi-Agent Extraction Architecture Guide")
            self.drawRightString(612 - 50, 750, "LangGraph Pipeline & Agent Logic")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(50, 742, 612 - 50, 742)
        
        # Draw footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(50, 45, 612 - 50, 45)
        self.drawString(50, 32, "Confidential — LangGraph Multi-Agent System Deep Dive Report")
        self.drawRightString(612 - 50, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_multi_agent_pdf(output_filename="outputs/Multi_Agent_Extraction_Deep_Dive_Guide.pdf"):
    out_path = Path(output_filename)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=48,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()
    
    # Color Palette
    primary_color = colors.HexColor("#1E3A8A")   # Deep Blue
    secondary_color = colors.HexColor("#0D9488") # Teal
    dark_neutral = colors.HexColor("#0F172A")    # Slate 900
    body_color = colors.HexColor("#334155")      # Slate 700
    accent_blue = colors.HexColor("#2563EB")     # Blue 600
    bg_light = colors.HexColor("#F8FAFC")        # Slate 50
    code_bg = colors.HexColor("#F1F5F9")         # Slate 100

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=secondary_color,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        'H1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=11,
        spaceAfter=4,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'H2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=body_color,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.5,
        textColor=body_color,
        leftIndent=12,
        spaceAfter=2.5,
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_neutral,
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
        backColor=code_bg,
        borderPadding=3,
        spaceAfter=3,
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=9.8,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=dark_neutral,
    )

    story = []

    # ==========================================
    # HEADER BANNER
    # ==========================================
    story.append(Paragraph("Multi-Agent Extraction System — Technical Deep Dive", title_style))
    story.append(Paragraph("LangGraph Orchestration, Specialist Agent Pipelines, Reconciliation & Validation Logic", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    meta_data = [
        [
            Paragraph("<b>Architecture:</b> LangGraph Parallel Multi-Agent Workflow", table_cell_style),
            Paragraph("<b>Output:</b> 20 Canonical Fields with Provenance Citations", table_cell_style),
        ],
        [
            Paragraph("<b>Agent Framework:</b> StateGraph with Custom Reducers & Feedback Loops", table_cell_style),
            Paragraph("<b>LLM / Extraction Engine:</b> Groq Qwen 27B + Evidence Grounding", table_cell_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[256, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # ==========================================
    # 1. OVERVIEW OF MULTI-AGENT EXTRACTION
    # ==========================================
    story.append(Paragraph("1. Multi-Agent System Architecture Overview", h1_style))
    story.append(Paragraph(
        "Single-prompt Large Language Model extraction fails on complex RFP procurement packages because a single context window "
        "cannot reliably process 100+ pages, preserve tabular specifications, resolve legal amendments across addenda, and verify "
        "factual citations. Our platform solves this using a <b>LangGraph Stateful Multi-Agent System</b>. "
        "Instead of dumping raw PDFs into an LLM, the system breaks extraction into specialized domain sub-tasks, coordinates them "
        "via a centralized state board (<code>RFPState</code>), executes parallel retrieval over our Hybrid Search Engine, resolves "
        "contractual overrides via an Addendum Reconciler, and enforces strict evidence grounding with an automated Critic/Validator.",
        body_style
    ))

    # Graph Topology Table
    graph_topology = [
        [
            Paragraph("Workflow Stage", table_header_style),
            Paragraph("Node Name", table_header_style),
            Paragraph("Agent Responsibility & Code Logic", table_header_style),
            Paragraph("State Transition", table_header_style),
        ],
        [
            Paragraph("<b>1. Orchestration</b>", table_cell_style),
            Paragraph("<code>Orchestrator</code>", table_cell_style),
            Paragraph("Initializes <code>RFPState</code>, binds bid identifier, and fans out execution to 4 specialist agents in parallel.", table_cell_style),
            Paragraph("<code>START → Specialists</code>", table_cell_style),
        ],
        [
            Paragraph("<b>2. Parallel Specialists</b>", table_cell_style),
            Paragraph("<code>entity_specialist</code><br/><code>logistics_specialist</code><br/><code>product_specialist</code><br/><code>legal_specialist</code>", table_cell_style),
            Paragraph("Specialist agents query the search tool for domain queries, collect candidate chunks, and prompt Groq LLM for field extraction.", table_cell_style),
            Paragraph("<code>Specialists → addendum_reconciler</code> (Fan-In)", table_cell_style),
        ],
        [
            Paragraph("<b>3. Addendum Reconciler</b>", table_cell_style),
            Paragraph("<code>addendum_reconciler</code>", table_cell_style),
            Paragraph("Fetches all addenda chunks, detects timeline and requirement modifications, overrides outdated fields, and logs audit diffs.", table_cell_style),
            Paragraph("<code>addendum_reconciler → validator</code>", table_cell_style),
        ],
        [
            Paragraph("<b>4. Validator & Critic</b>", table_cell_style),
            Paragraph("<code>validator</code>", table_cell_style),
            Paragraph("Audits all 20 fields against authentic chunk IDs in <code>EvidenceStore</code>. Rejects ungrounded claims or invalid citations.", table_cell_style),
            Paragraph("<code>validator → should_retry?</code>", table_cell_style),
        ],
        [
            Paragraph("<b>5. Feedback / Retry</b>", table_cell_style),
            Paragraph("<code>retry_agent</code>", table_cell_style),
            Paragraph("Executes targeted re-search with expanded queries for rejected fields (max 2 retries). Feeds back into validator.", table_cell_style),
            Paragraph("<code>retry_agent → validator</code> (Loop)", table_cell_style),
        ],
        [
            Paragraph("<b>6. Final Serializer</b>", table_cell_style),
            Paragraph("<code>serializer</code>", table_cell_style),
            Paragraph("Compiles canonical <code>BidOutput</code> model, aliases field names, and writes final validated JSON outputs.", table_cell_style),
            Paragraph("<code>serializer → END</code>", table_cell_style),
        ],
    ]

    g_table = Table(graph_topology, colWidths=[90, 110, 216, 100])
    g_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
    ]))
    story.append(g_table)
    story.append(Spacer(1, 8))

    # ==========================================
    # 2. SHARED STATE MANAGEMENT (RFPState)
    # ==========================================
    story.append(Paragraph("2. Shared State Management (<code>RFPState</code>)", h1_style))
    story.append(Paragraph(
        "<b>Code Module:</b> <code>app/graph/state.py</code><br/>"
        "LangGraph coordinates agents using a strongly-typed shared memory object. Because specialist agents run concurrently, "
        "we define custom <b>reducer functions</b> that merge results from parallel branches without race conditions:",
        body_style
    ))

    state_code = """class RFPState(TypedDict):
    bid_id: str
    extracted_fields: Annotated[Dict[str, FieldResult], merge_field_results]  # Merges parallel agent outputs
    addendum_changes: Annotated[List[AddendumChange], append_changes]        # Accumulates addendum diffs
    validation_result: Optional[ValidationResult]                             # Critic audit report
    retry_count: int                                                         # Loop counter (max 2)
    final_output: Optional[BidOutput]                                        # Serialized 20-field model
    errors: Annotated[List[str], append_strings]                              # Trace and error logs"""
    story.append(Paragraph(f"<font face='Courier' size='7'>{state_code.replace(chr(10), '<br/>&nbsp;&nbsp;')}</font>", code_style))
    story.append(Spacer(1, 6))

    # ==========================================
    # 3. SPECIALIST AGENTS DEEP DIVE
    # ==========================================
    story.append(Paragraph("3. Specialist Agent Extraction Pipelines & Logic", h1_style))
    story.append(Paragraph(
        "The 20 required procurement fields are partitioned into 4 specialist agent domains. "
        "Each specialist agent executes a standardized 4-step pipeline: "
        "<b>(1) Targeted Query Formulation $\\rightarrow$ (2) Tool-based Evidence Search $\\rightarrow$ (3) Structured LLM Grounding $\\rightarrow$ (4) FieldResult Construction</b>.",
        body_style
    ))

    # Entity Specialist
    story.append(Paragraph("Agent 1: Entity & Contact Specialist (<code>app/agents/entity_agent.py</code>)", h2_style))
    story.append(Paragraph(
        "• <b>Assigned Fields:</b> <code>bid_number</code>, <code>title</code>, <code>company_name</code>, <code>contact_info</code>, <code>bid_summary</code>.<br/>"
        "• <b>Targeted Queries:</b> <code>'official bid solicitation RFP number'</code>, <code>'issuing organization agency school district'</code>, <code>'procurement contact email phone'</code>.<br/>"
        "• <b>Real Extraction Logic (Bid 1):</b> Retrieves the Dallas ISD Bonfire portal HTML and RFP cover page. Extracts <code>bid_number: 'JA-207652'</code> and <code>company_name: 'Dallas Independent School District'</code> with chunk citations.<br/>"
        "• <b>Bid Summary Generation:</b> Synthesizes a concise 3-5 sentence procurement overview grounded strictly in the retrieved scope passages.",
        body_style
    ))

    # Logistics Specialist
    story.append(Paragraph("Agent 2: Dates & Logistics Specialist (<code>app/agents/logistics_agent.py</code>)", h2_style))
    story.append(Paragraph(
        "• <b>Assigned Fields:</b> <code>due_date</code>, <code>bid_submission_type</code>, <code>term_of_bid</code>, <code>pre_bid_meeting</code>, <code>delivery_date</code>.<br/>"
        "• <b>Targeted Queries:</b> <code>'due date closing deadline schedule'</code>, <code>'bid submission portal electronic sealed'</code>, <code>'delivery window calendar days after award'</code>, <code>'pre-bid conference mandatory date time'</code>.<br/>"
        "• <b>Real Extraction Logic (Bid 2):</b> Searches <code>PORFP_-_Dell_Laptop_Final.pdf</code>. Extracts <code>due_date: 'July 2, 2024 at 2:00 PM EST'</code>, <code>bid_submission_type: 'Electronic via eMMA portal'</code>, and <code>delivery_date: 'Within 45 calendar days after contract award'</code>.",
        body_style
    ))

    # Product & Specs Specialist
    story.append(Paragraph("Agent 3: Product & Technical Specs Specialist (<code>app/agents/product_agent.py</code>)", h2_style))
    story.append(Paragraph(
        "• <b>Assigned Fields:</b> <code>product</code>, <code>model_no</code>, <code>part_no</code>, <code>product_specification</code>, <code>mfg_for_registration</code>, <code>installation</code>.<br/>"
        "• <b>Targeted Queries:</b> <code>'product name quantity required devices'</code>, <code>'Dell model number SKU part number'</code>, <code>'technical specifications CPU processor RAM storage display'</code>, <code>'manufacturer authorization partner registration'</code>.<br/>"
        "• <b>Real Extraction Logic (Bid 2):</b> Searches <code>Dell_Laptop_Specs.pdf</code> and extracts Markdown tables. Populates <code>model_no: 'Dell Latitude 5550'</code>, <code>part_no: '210-BLMX'</code>, and <code>product_specification: 'Intel Core Ultra 5 125U (12 cores), 16GB DDR5 RAM, 256GB SSD, 15.6 FHD Display, 3-Year Extended Warranty'</code>.",
        body_style
    ))

    # Legal & Commercial Specialist
    story.append(Paragraph("Agent 4: Legal & Commercial Specialist (<code>app/agents/legal_agent.py</code>)", h2_style))
    story.append(Paragraph(
        "• <b>Assigned Fields:</b> <code>bid_bond_requirement</code>, <code>payment_terms</code>, <code>any_additional_documentation_required</code>, <code>contract_or_cooperative_to_use</code>.<br/>"
        "• <b>Targeted Queries:</b> <code>'bid bond surety proposal security deposit percentage'</code>, <code>'payment terms net invoicing'</code>, <code>'required affidavits forms certificates compliance'</code>, <code>'state master contract cooperative vehicle'</code>.<br/>"
        "• <b>Real Extraction Logic (Bid 2):</b> Reads <code>Contract_Affidavit.pdf</code> and <code>Mercury_Affidavit.pdf</code>. Extracts <code>any_additional_documentation_required: 'Contract Affidavit and Mercury Affidavit'</code> and accurately records <code>bid_bond_requirement: 'Not required'</code> (zero hallucination).",
        body_style
    ))

    story.append(Spacer(1, 8))

    # ==========================================
    # 4. ADDENDUM RECONCILIATION AGENT
    # ==========================================
    story.append(Paragraph("4. Addendum Reconciliation Agent & Override Logic", h1_style))
    story.append(Paragraph(
        "<b>Code Module:</b> <code>app/reconciliation/reconciler.py</code><br/>"
        "<b>The Procurement Problem:</b> In government and school RFPs, addenda legally supersede original contract terms. "
        "If an AI only reads the base RFP, it reports outdated deadlines and incorrect specifications.",
        body_style
    ))
    story.append(Paragraph(
        "<b>How the Addendum Reconciler Operates:</b><br/>"
        "1. <b>Addenda Harvesting:</b> Queries Qdrant for all chunks where <code>document_type = 'addendum'</code> ordered sequentially by <code>addendum_number</code>.<br/>"
        "2. <b>Modification Analysis:</b> Passes the current draft fields and addenda text into a specialized reconciliation prompt.<br/>"
        "3. <b>Override Execution:</b> When an amendment alters a field, the Reconciler overwrites the value, attaches the addendum chunk citation, "
        "and creates an <code>AddendumChange</code> record.<br/>"
        "• <b>Concrete Bid 1 Walkthrough:</b><br/>"
        "&nbsp;&nbsp;• <i>Base RFP Draft:</i> <code>Due Date = June 25, 2024 at 2:00 PM CST</code> (from <code>JA-207652 FINAL.pdf</code>).<br/>"
        "&nbsp;&nbsp;• <i>Addendum 2 Clause:</i> <code>'The proposal due date has been extended to July 9, 2024 at 2:00 PM CST.'</code><br/>"
        "&nbsp;&nbsp;• <i>Reconciled State:</i> <code>Due Date: 'July 9, 2024 at 2:00 PM CST'</code>, source citation updated to <code>Bid_1_Addendum_2.pdf (Page 1)</code>, "
        "audit note: <code>'Extended by Addendum 2 (original date: June 25, 2024)'</code>.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # ==========================================
    # 5. VALIDATOR CRITIC & RETRY FEEDBACK LOOP
    # ==========================================
    story.append(Paragraph("5. Validator / Critic Agent & Targeted Retry Loop", h1_style))
    story.append(Paragraph(
        "<b>Code Modules:</b> <code>app/validation/validator.py</code>, <code>app/agents/retry_agent.py</code>, <code>app/graph/nodes/retry.py</code><br/>"
        "To eliminate hallucinations and enforce zero-defect extraction, the <b>Validator Critic</b> audits every field before allowing the pipeline to finish.",
        body_style
    ))

    val_rules = [
        [
            Paragraph("Deterministic Audit Rule", table_header_style),
            Paragraph("Validation Logic & Criteria", table_header_style),
            Paragraph("Action if Violated (Critic Action)", table_header_style),
        ],
        [
            Paragraph("<b>Rule 1: No Evidence → No Value</b>", table_cell_style),
            Paragraph("If <code>value != None</code>, <code>len(sources)</code> must be $\\ge 1$. A claim without source evidence is rejected.", table_cell_style),
            Paragraph("Flags <code>MISSING_CITATION</code> $\\rightarrow$ routes field to Retry Agent.", table_cell_style),
        ],
        [
            Paragraph("<b>Rule 2: Chunk Registry Provenance</b>", table_cell_style),
            Paragraph("Every cited <code>chunk_id</code> must exist in the local <code>EvidenceStore</code> database.", table_cell_style),
            Paragraph("Flags <code>UNKNOWN_CHUNK</code> $\\rightarrow$ forces re-extraction from verified chunks.", table_cell_style),
        ],
        [
            Paragraph("<b>Rule 3: Confidence Calibration</b>", table_cell_style),
            Paragraph("Confidence must be in $[0.0, 1.0]$. If <code>value is None</code>, confidence must be $\\le 0.20$.", table_cell_style),
            Paragraph("Flags <code>INVALID_CONFIDENCE</code> $\\rightarrow$ resets confidence score.", table_cell_style),
        ],
        [
            Paragraph("<b>Rule 4: Citation Validity</b>", table_cell_style),
            Paragraph("Citations must have valid non-empty <code>file_name</code> and <code>page_number >= 1</code>.", table_cell_style),
            Paragraph("Flags <code>INVALID_PAGE</code> $\\rightarrow$ triggers metadata repair.", table_cell_style),
        ],
    ]
    val_table = Table(val_rules, colWidths=[130, 222, 164])
    val_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
    ]))
    story.append(val_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>The Retry Feedback Loop in Action:</b><br/>"
        "When the Validator rejects a field, the conditional edge <code>should_retry</code> evaluates the state:<br/>"
        "• If <code>not validation_result.is_valid and retry_count < 2</code> $\\rightarrow$ routes to <code>retry_agent</code>.<br/>"
        "• The <code>RetryAgent</code> expands the search query with domain synonyms (e.g. <code>'all details specifications for bid bond surety'</code>) "
        "and queries the search tool with increased depth (<code>top_k=6</code>).<br/>"
        "• Re-extracted fields are merged back into <code>RFPState</code> and routed <b>back to the Validator</b> for re-auditing.<br/>"
        "• If still unverified after 2 retries, the field is safely resolved to <code>value: null</code> with <code>'Not found in documents.'</code>.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # ==========================================
    # 6. COMPLETE END-TO-END EXTRACTION JSON
    # ==========================================
    story.append(Paragraph("6. Serialized Canonical Output Schema", h1_style))
    story.append(Paragraph(
        "<b>Code Module:</b> <code>app/graph/nodes/serializer.py</code>, <code>app/extraction/schemas.py</code><br/>"
        "The Serializer formats the final state into the exact JSON schema required by Section 8.1 of the assignment specification:",
        body_style
    ))

    json_example = """{
  "bid_id": "Bid1",
  "fields": {
    "Due Date": {
      "value": "July 9, 2024 at 2:00 PM CST",
      "sources": [{"file": "Bid_1_Addendum_2.pdf", "page": 1, "chunk_id": "Bid1::Addendum_2.pdf::p1::chk_01"}],
      "confidence": 0.95,
      "notes": "Extended by Addendum 2 (original date: June 25, 2024)"
    },
    "Bid Bond Requirement": {
      "value": null,
      "sources": [],
      "confidence": 0.0,
      "notes": "Not found in documents."
    }
  },
  "addendum_changes": [{"field": "due_date", "change_type": "MODIFICATION", "new_value": "July 9, 2024 at 2:00 PM CST"}],
  "validation": {"passed": 19, "failed": 0, "not_found": 1}
}"""
    story.append(Paragraph(f"<font face='Courier' size='7'>{json_example.replace(chr(10), '<br/>&nbsp;&nbsp;')}</font>", code_style))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=6))
    story.append(Paragraph(
        "<b>Summary:</b> The LangGraph multi-agent extraction pipeline delivers deterministic precision, "
        "automatic addendum reconciliation, and strict evidence verification for all 20 canonical procurement fields.",
        callout_style
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Multi-Agent PDF successfully built at: {out_path.resolve()}")
    return str(out_path.resolve())


if __name__ == "__main__":
    build_multi_agent_pdf()
