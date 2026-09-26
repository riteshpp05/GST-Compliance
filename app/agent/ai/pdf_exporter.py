"""
app.agent.ai.pdf_exporter
=========================
PDF Dossier Exporter implementation for UC15 (Sprint 12.4).
Generates formatted, multi-page PDF audit dossier reports from an InvestigationDossier object
using ReportLab SimpleDocTemplate, Flowables, and custom styling.
"""

from __future__ import annotations

import io
import os
from typing import Optional, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.agent.ai.dossier import InvestigationDossier
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DossierPDFExporter:
    """
    Exports an InvestigationDossier object into an enterprise-grade PDF audit document.
    """

    @staticmethod
    def export_pdf(dossier: InvestigationDossier, output_target: Union[str, io.BytesIO]) -> Union[str, io.BytesIO]:
        """
        Render dossier PDF to file path or BytesIO buffer.
        """
        logger.info(f"Exporting PDF for dossier '{dossier.dossier_id}'...")

        doc = SimpleDocTemplate(
            output_target,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        primary_color = colors.HexColor("#1A365D")   # Deep navy
        secondary_color = colors.HexColor("#2B6CB0") # Slate blue
        accent_color = colors.HexColor("#C53030")    # Crimson red
        neutral_dark = colors.HexColor("#2D3748")    # Dark slate text
        bg_light = colors.HexColor("#EDF2F7")        # Light gray fill

        title_style = ParagraphStyle(
            "DossierTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
            spaceAfter=6,
        )

        subtitle_style = ParagraphStyle(
            "DossierSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=neutral_dark,
            spaceAfter=12,
        )

        section_heading = ParagraphStyle(
            "DossierSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=secondary_color,
            spaceBefore=10,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "DossierBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=neutral_dark,
            spaceAfter=4,
        )

        bold_body = ParagraphStyle(
            "DossierBoldBody",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        notice_style = ParagraphStyle(
            "DossierNotice",
            parent=body_style,
            fontName="Helvetica-Oblique",
            textColor=accent_color,
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("UC15 GST COMPLIANCE & INVESTIGATION DOSSIER", title_style))
        meta_text = (
            f"<b>Dossier ID:</b> {dossier.dossier_id} &nbsp;|&nbsp; "
            f"<b>Session ID:</b> {dossier.session_id} &nbsp;|&nbsp; "
            f"<b>Generated:</b> {dossier.generated_at[:19]}"
        )
        story.append(Paragraph(meta_text, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceAfter=10))

        # Scope Table
        scope_data = [
            [Paragraph("<b>Target Scope Focus:</b>", bold_body), Paragraph(dossier.entity_focus.summary_string(), body_style)],
        ]
        t_scope = Table(scope_data, colWidths=[130, 410])
        t_scope.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
            ])
        )
        story.append(t_scope)
        story.append(Spacer(1, 10))

        # 2. Executive Summary
        story.append(Paragraph("1. EXECUTIVE SUMMARY & AUDIT VERDICT", section_heading))
        story.append(Paragraph(dossier.executive_summary, body_style))
        story.append(Spacer(1, 8))

        if dossier.insufficient_evidence_notices:
            story.append(Paragraph("<b>EVIDENCE NOTICES & LIMITATIONS:</b>", notice_style))
            for notic in dossier.insufficient_evidence_notices:
                story.append(Paragraph(f"• {notic}", notice_style))
            story.append(Spacer(1, 8))

        # 3. Session History
        story.append(Paragraph("2. MULTI-TURN INVESTIGATION SESSION TRAIL", section_heading))
        if not dossier.session_history:
            story.append(Paragraph("<i>INSUFFICIENT EVIDENCE / NOT AVAILABLE: No query turns recorded in session.</i>", notice_style))
        else:
            turn_rows = [["Turn #", "User Query", "Intent", "Tools Executed"]]
            for turn in dossier.session_history:
                t_idx = f"#{turn.get('turn_index')}"
                q_txt = turn.get("user_query", "")[:60] + ("..." if len(turn.get("user_query", "")) > 60 else "")
                intent_t = str(turn.get("intent", ""))
                tools_t = ", ".join(turn.get("tools_used", []))
                turn_rows.append([t_idx, Paragraph(q_txt, body_style), intent_t, Paragraph(tools_t, body_style)])

            t_turns = Table(turn_rows, colWidths=[40, 220, 140, 140])
            t_turns.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ])
            )
            story.append(t_turns)
        story.append(Spacer(1, 10))

        # 4. Statutory Gate Results
        story.append(Paragraph("3. STATUTORY COMPLIANCE GATE RESULTS (GATES 1-6)", section_heading))
        if not dossier.gate_breakdown:
            story.append(Paragraph("<i>INSUFFICIENT EVIDENCE / NOT AVAILABLE: Gate validation details unavailable.</i>", notice_style))
        else:
            for inv in dossier.gate_breakdown[:3]:
                inv_no = inv.get("invoice_no") or inv.get("invoice_id") or "Target"
                status = inv.get("compliance_status") or inv.get("status") or "UNKNOWN"
                story.append(Paragraph(f"<b>Invoice {inv_no} &nbsp;—&nbsp; Compliance Verdict: {status}</b>", bold_body))

                gate_rows = [["Gate", "Gate Name", "Result", "Validation Details"]]
                gates = inv.get("gates") or inv.get("gate_results") or []
                for g in gates:
                    g_num = f"Gate {g.get('gate_number') or g.get('gate')}"
                    g_name = g.get("gate_name") or g.get("name") or "Gate"
                    g_stat = g.get("status") or g.get("result") or "N/A"
                    g_msg = g.get("message") or g.get("details") or ""
                    gate_rows.append([g_num, g_name, g_stat, Paragraph(g_msg, body_style)])

                t_gates = Table(gate_rows, colWidths=[55, 140, 75, 270])
                t_gates.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), bg_light),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("PADDING", (0, 0), (-1, -1), 4),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ])
                )
                story.append(t_gates)
                story.append(Spacer(1, 6))

        story.append(Spacer(1, 6))

        # 5. Risk & Exposure Table
        story.append(Paragraph("4. RISK PROFILE & FINANCIAL EXPOSURE ANALYSIS", section_heading))
        risk_txt = "N/A"
        if dossier.risk_assessment:
            score = dossier.risk_assessment.get("risk_score") or dossier.risk_assessment.get("score") or "N/A"
            level = dossier.risk_assessment.get("risk_level") or dossier.risk_assessment.get("level") or "N/A"
            prio = dossier.risk_assessment.get("risk_priority") or dossier.risk_assessment.get("priority") or "N/A"
            risk_txt = f"Level: {level} | Score: {score}/100 | Priority: {prio}"

        fin_txt = "N/A"
        if dossier.financial_exposure:
            tot = dossier.financial_exposure.get("total_potential_exposure") or dossier.financial_exposure.get("total_exposure") or 0.0
            itc = dossier.financial_exposure.get("itc_at_risk") or 0.0
            fin_txt = f"Total Exposure: INR {tot:,.2f} (ITC at Risk: INR {itc:,.2f})"

        rf_data = [
            [Paragraph("<b>Risk Profile:</b>", bold_body), Paragraph(risk_txt, body_style)],
            [Paragraph("<b>Financial Exposure:</b>", bold_body), Paragraph(fin_txt, body_style)],
        ]
        t_rf = Table(rf_data, colWidths=[130, 410])
        t_rf.setStyle(
            TableStyle([
                ("PADDING", (0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDF2F7")),
            ])
        )
        story.append(t_rf)
        story.append(Spacer(1, 10))

        # 6. Root Cause & Blast Radius
        story.append(Paragraph("5. ROOT CAUSE & BLAST RADIUS INTELLIGENCE", section_heading))
        rc_text = "*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Root cause intelligence not evaluated.*"
        if dossier.root_cause_analysis:
            rc_type = dossier.root_cause_analysis.get("root_cause_type") or dossier.root_cause_analysis.get("title") or "N/A"
            conf = dossier.root_cause_analysis.get("confidence") or "N/A"
            stmt = dossier.root_cause_analysis.get("causality_statement") or "N/A"
            rc_text = f"<b>Primary Root Cause:</b> {rc_type} (Confidence: {conf})<br/><b>Causality:</b> <i>\"{stmt}\"</i>"
        story.append(Paragraph(rc_text, body_style))
        story.append(Spacer(1, 6))

        br_text = "*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Blast radius impact scope not calculated.*"
        if dossier.blast_radius_analysis:
            sys_cls = dossier.blast_radius_analysis.get("systemic_classification") or "N/A"
            aff_inv = dossier.blast_radius_analysis.get("affected_invoice_count") or 0
            aff_cp = dossier.blast_radius_analysis.get("affected_counterparty_count") or 0
            br_text = f"<b>Systemic Classification:</b> {sys_cls} &nbsp;|&nbsp; <b>Affected Invoices:</b> {aff_inv} &nbsp;|&nbsp; <b>Affected Counterparties:</b> {aff_cp}"
        story.append(Paragraph(br_text, body_style))
        story.append(Spacer(1, 10))

        # 7. Regulatory Evidence
        story.append(Paragraph("6. REGULATORY GROUNDING & STATUTORY PROVENANCE", section_heading))
        if not dossier.regulatory_evidence:
            story.append(Paragraph("<i>INSUFFICIENT EVIDENCE / NOT AVAILABLE: No regulatory knowledge documents retrieved.</i>", notice_style))
        else:
            reg_rows = [["Doc Name", "Location", "Effective Dates", "Excerpt"]]
            for ev in dossier.regulatory_evidence[:4]:
                prov = ev.get("provenance", {})
                doc_n = prov.get("document_name") or "Statutory Document"
                loc = f"Page {prov.get('page_number')}" if prov.get("page_number") else f"Sec: {prov.get('section') or 'General'}"
                eff = f"{prov.get('effective_from') or 'ALL'} to {prov.get('effective_to') or 'ONGOING'}"
                txt = ev.get("chunk", {}).get("content") or ""
                txt_trunc = txt[:120] + ("..." if len(txt) > 120 else "")
                reg_rows.append([doc_n, loc, eff, Paragraph(txt_trunc, body_style)])

            t_reg = Table(reg_rows, colWidths=[120, 70, 100, 250])
            t_reg.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), bg_light),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ])
            )
            story.append(t_reg)
        story.append(Spacer(1, 10))

        # 8. Advisory Resolution Actions & SAP Guidance
        story.append(Paragraph("7. ADVISORY RESOLUTION ACTIONS & SAP GUIDANCE", section_heading))
        story.append(Paragraph("<b>ADVISORY NOTICE:</b> Action recommendations are ADVISORY GUIDANCE ONLY. UC15 performs zero live SAP API calls or mutations.", notice_style))
        story.append(Spacer(1, 4))
        for rec in dossier.advisory_recommendations:
            story.append(Paragraph(f"• {rec}", body_style))

        # Build PDF
        doc.build(story)
        logger.info(f"Successfully generated PDF dossier report for '{dossier.dossier_id}'.")
        return output_target
