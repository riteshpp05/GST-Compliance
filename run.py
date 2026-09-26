#!/usr/bin/env python3
"""
UC15 GST & Tax Compliance Validation Agent — CLI entrypoint.

Usage:
    python run.py                        # batch run against the dataset
    python run.py --invoice INV-8000001  # single invoice, verbose (all 6 gates)
    python run.py --ui                   # launch the FastAPI dashboard
"""
import argparse
import sys

from app.agent.compliance_agent import GSTComplianceAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the UC15 GST & Tax Compliance Validation Agent.")
    parser.add_argument("--invoice", help="Run a single invoice by invoice number")
    parser.add_argument("--ui", action="store_true", help="Launch the FastAPI dashboard instead")
    parser.add_argument("--port", type=int, default=None, help="Port to run the UI server on")
    parser.add_argument("--history", "--historical", dest="historical", action="store_true", help="Display historical time-series intelligence, trend, and recurring pattern report")
    parser.add_argument("--financial", "--exposure", dest="financial", action="store_true", help="Display financial impact and exposure intelligence report")
    parser.add_argument("--top-exposures", type=int, nargs="?", const=5, help="Display top N financial exposures (default: 5)")
    parser.add_argument("--intelligence", action="store_true", help="Display duplicate & anomaly intelligence summary report")
    parser.add_argument("--duplicates", action="store_true", help="Display duplicate candidate analysis and clusters")
    parser.add_argument("--anomalies", action="store_true", help="Display statistical transaction anomaly analysis")
    args = parser.parse_args()

    if args.ui:
        import uvicorn
        from app.config.settings import settings
        port = args.port or settings.api_port
        uvicorn.run("ui.app:app", host=settings.api_host, port=port, reload=False)
        return 0

    agent = GSTComplianceAgent()
    if args.invoice:
        agent.run_invoice(args.invoice)
    else:
        results = agent.run_all()
        print(f"\nExcel and JSON written to results/ ({len(results)} invoices)")
        if args.historical:
            report = agent.historical_service.generate_report()
            print("\n" + report.to_text_summary())
        if args.financial or args.top_exposures:
            top_n = args.top_exposures if isinstance(args.top_exposures, int) else 5
            fin_report = agent.get_financial_report(top_n=top_n)
            print("\n" + fin_report.to_text_summary())
        if args.intelligence or args.duplicates or args.anomalies:
            intel_report = agent.get_intelligence_report()
            print("\n" + intel_report.to_text_summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
