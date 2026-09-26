#!/usr/bin/env python3
"""
UC15 GST Compliance Intelligence & Resolution Agent — Main Entrypoint (v2.0)

Usage:
    python main.py                                      # default batch run (Excel dataset)
    python main.py --invoice INV-8000001                # single invoice validation
    python main.py --file data/raw/sample_invoices.csv  # batch run from CSV
    python main.py --file data/raw/sample_invoices.json # batch run from JSON
    python main.py --mock                               # run controlled mock scenarios
    python main.py --ui                                 # launch FastAPI Checkpoint Dashboard
"""
from __future__ import annotations

import argparse
import sys

from app.agent.compliance_agent import GSTComplianceAgent
from app.config.settings import settings
from app.infrastructure.logging import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UC15 GST Compliance Intelligence & Resolution Agent (v2.0)"
    )
    parser.add_argument("--invoice", help="Run validation for a single invoice by invoice number")
    parser.add_argument("--file", help="Input file path to ingest (supports .xlsx, .csv, .json)")
    parser.add_argument("--mock", action="store_true", help="Run with mock scenario data provider")
    parser.add_argument("--ui", action="store_true", help="Launch the FastAPI checkpoint dashboard")
    parser.add_argument("--risk", action="store_true", help="Display detailed risk analytics for all invoices")
    parser.add_argument("--top-risky", type=int, nargs="?", const=5, help="Display the top N riskiest invoices (default: 5)")
    parser.add_argument("--history", "--historical", dest="historical", action="store_true", help="Display historical time-series intelligence, trend, and recurring pattern report")
    parser.add_argument("--financial", "--exposure", dest="financial", action="store_true", help="Display financial impact and exposure intelligence report")
    parser.add_argument("--top-exposures", type=int, nargs="?", const=5, help="Display top N financial exposures (default: 5)")
    parser.add_argument("--intelligence", action="store_true", help="Display duplicate & anomaly intelligence summary report")
    parser.add_argument("--duplicates", action="store_true", help="Display duplicate candidate analysis and clusters")
    parser.add_argument("--anomalies", action="store_true", help="Display statistical transaction anomaly analysis")
    parser.add_argument("--investigation", action="store_true", help="Display unified root cause & blast radius investigation report")
    parser.add_argument("--demo", action="store_true", help="Run in controlled DEMO mode with synthetic sample data (blocked in production)")
    parser.add_argument("--root-causes", action="store_true", help="Display detailed candidate root cause analysis")
    parser.add_argument("--blast-radius", action="store_true", help="Display detailed multi-dimensional blast radius analysis")
    parser.add_argument("--strict-checksum", action="store_true", help="Enable strict GSTIN Luhn Modulo-36 checksum verification")
    parser.add_argument("--sap", action="store_true", help="Ingest live invoice data from SAP S/4HANA OData V4 (Docs 8094-8104)")
    parser.add_argument("--hybrid", action="store_true", help="Ingest live SAP S/4HANA invoices augmented with statutory sandbox scenarios")
    parser.add_argument("--pipeline", action="store_true", help="Run full end-to-end statutory audit, reconciliation, and financial exposure pipeline")
    parser.add_argument("--log-level", default=settings.log_level, help="Set logging level (DEBUG, INFO, etc.)")
    args = parser.parse_args()

    setup_logging(level=args.log_level)

    from app.config.production_validator import validate_production_configuration_or_exit
    validate_production_configuration_or_exit()

    if args.demo:
        env = os.getenv("APP_ENV", "development").lower().strip()
        if env in ("production", "prod"):
            print("\nERROR: Cannot run demo mode (--demo) when APP_ENV=production!\n")
            return 1
        print("\n[DEMO MODE ACTIVE] Ingesting synthetic sample invoice dataset (data_origin=SYNTHETIC, environment=DEMO)...\n")
        args.mock = True

    if args.ui:
        import uvicorn
        uvicorn.run("ui.app:app", host=settings.api_host, port=settings.api_port, reload=False)
        return 0

    agent = GSTComplianceAgent(
        source_file=args.file,
        mock=args.mock,
        sap=args.sap,
        hybrid=args.hybrid,
    )

    if args.strict_checksum:
        agent.registry = agent.registry
        if agent.validation_engine and agent.validation_engine.context:
            agent.validation_engine.context.validate_gstin_checksum = True

    if args.pipeline:
        args.risk = True
        args.financial = True
        args.intelligence = True
        args.investigation = True

    if args.invoice:
        decision = agent.run_invoice(args.invoice)
        return 0 if decision else 1
    else:
        results = agent.run_all()
        print(f"\nExcel and JSON written to {settings.results_dir}/ ({len(results)} invoices)")
        if agent.ingestion_result:
            s = agent.ingestion_result.summary()
            print(f"Ingestion Summary: {s['valid_count']} valid, {s['warning_count']} warnings, {s['invalid_count']} rejected.")

        if (args.risk or args.top_risky) and agent.batch_risk_report:
            limit = args.top_risky if args.top_risky else 5
            top_items = agent.batch_risk_report.top_risky_invoices[:limit]
            print("=" * 75)
            print(f"  TOP {len(top_items)} RISKY INVOICES (Risk Engine v1.0)")
            print("=" * 75)
            print(f"{'Rank':<5} {'Invoice No':<14} {'Score':<7} {'Level':<10} {'Priority':<9} {'Primary Drivers'}")
            print("-" * 75)
            for idx, item in enumerate(top_items, 1):
                drivers = ", ".join(f"{f.rule_id} (+{f.contribution:.0f})" for f in item.risk_factors if f.rule_id)[:30]
                print(f"#{idx:<4} {item.invoice_id:<14} {item.risk_score:<7.1f} {item.risk_level:<10} {item.priority:<9} {drivers}")
            print("=" * 75)

        if args.historical:
            hist_report = agent.historical_service.generate_report()
            print("\n" + hist_report.to_text_summary())

        if args.financial or args.top_exposures:
            top_n = args.top_exposures if isinstance(args.top_exposures, int) else 5
            fin_report = agent.get_financial_report(top_n=top_n)
            print("\n" + fin_report.to_text_summary())

        if args.intelligence or args.duplicates or args.anomalies:
            intel_report = agent.get_intelligence_report()
            print("\n" + intel_report.to_text_summary())

        if args.investigation or args.root_causes or args.blast_radius:
            profile = agent.get_investigation_profile()
            if profile:
                from app.investigation.reporting.report import InvestigationReportFormatter
                if args.root_causes:
                    print(InvestigationReportFormatter.format_root_causes_detail(profile))
                if args.blast_radius:
                    print(InvestigationReportFormatter.format_blast_radius_detail(profile))
                if args.investigation or (not args.root_causes and not args.blast_radius):
                    print(InvestigationReportFormatter.format_cli_summary(profile))

        return 0



if __name__ == "__main__":
    sys.exit(main())
