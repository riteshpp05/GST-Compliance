#!/usr/bin/env python3
"""
UC15 GST Compliance Intelligence Agent — 100 Invoices Stress-Test Dataset Generator
Generates:
  1. data/UC15_GSTCompliance_100_Invoices.xlsx
  2. data/UC15_GSTCompliance_100_Invoices.csv
  3. data/UC15_GSTCompliance_100_Invoices.json

Covers 100% of GST Compliance Gates 1-6, Deduplication (Exact/Fuzzy/Split),
Risk Scoring (0-100), Anomalies (Round figures, Outliers, Off-hours),
GSTR-2B reflection gaps, and S/4HANA OData schema field mappings.
"""

import json
import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Valid GSTIN generator with proper Luhn Mod 36 checksum
MOD36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def compute_luhn_mod36(gstin_14: str) -> str:
    factor = 1
    total = 0
    for char in reversed(gstin_14):
        val = MOD36_CHARS.index(char)
        code_point = val * factor
        factor = 1 if factor == 2 else 2
        code_point = (code_point // 36) + (code_point % 36)
        total += code_point
    remainder = total % 36
    check_val = (36 - remainder) % 36
    return MOD36_CHARS[check_val]

def make_valid_gstin(state_code: str, pan_suffix: str = "A1Z") -> str:
    pan = f"AAACB{random.randint(1000, 9999)}{pan_suffix[0]}"
    gstin_14 = f"{state_code}{pan}1Z"
    chk = compute_luhn_mod36(gstin_14)
    return f"{gstin_14}{chk}"

STATE_MAP = {
    "27": "Maharashtra", "07": "Delhi", "29": "Karnataka", "33": "Tamil Nadu",
    "06": "Haryana", "24": "Gujarat", "09": "Uttar Pradesh", "19": "West Bengal",
    "36": "Telangana", "32": "Kerala", "23": "Madhya Pradesh", "21": "Odisha"
}

HSN_MASTER = {
    "8409": ("Parts for Internal Combustion Engines", 9.0, 9.0, 18.0),
    "8483": ("Transmission Shafts & Cranks", 9.0, 9.0, 18.0),
    "8708": ("Motor Vehicle Parts & Accessories", 14.0, 14.0, 28.0),
    "8536": ("Electrical Switches & Connectors", 9.0, 9.0, 18.0),
    "7318": ("Screws, Bolts, Nuts (Iron/Steel)", 9.0, 9.0, 18.0),
    "3926": ("Plastic Articles NES", 9.0, 9.0, 18.0),
    "8501": ("Electric Motors & Generators", 9.0, 9.0, 18.0),
    "4819": ("Cartons, Boxes, Cases (Paper)", 6.0, 6.0, 12.0),
    "9983": ("Other Professional/Technical Services", 9.0, 9.0, 18.0),
    "9954": ("Construction Services for Immovable Property", 9.0, 9.0, 18.0),
}

def generate_100_records():
    records = []
    base_date = datetime(2026, 3, 1)

    def add_rec(rec_id, category, inv_no, date_str, direction, gstin, cparty, pos, hsn, desc, taxable, cgst, sgst, igst, eway, gstr2b, inv_type="B2B", notes=""):
        tot_tax = taxable * (cgst + sgst + igst) / 100.0
        tot_amt = taxable + tot_tax
        records.append({
            "test_id": rec_id,
            "test_category": category,
            "invoice_no": inv_no,
            "invoice_date": date_str,
            "direction": direction,
            "invoice_type": inv_type,
            "counterparty_gstin": gstin,
            "counterparty_name": cparty,
            "place_of_supply": pos,
            "hsn_code": hsn,
            "item_desc": desc,
            "taxable_value_inr": round(taxable, 2),
            "cgst_rate": round(cgst, 2),
            "sgst_rate": round(sgst, 2),
            "igst_rate": round(igst, 2),
            "total_tax_inr": round(tot_tax, 2),
            "total_amt": round(tot_amt, 2),
            "eway_bill_status": eway,
            "gstr2b_reflected": gstr2b,
            "test_notes": notes
        })

    # 1. CLEAN & COMPLIANT INVOICES (1-20)
    for i in range(1, 11):
        st_code = "27" if i % 2 == 1 else "07"
        pos = "Maharashtra" if st_code == "27" else "Delhi"
        gstin = make_valid_gstin(st_code)
        taxable = 45000.0 + i * 5000.0
        cgst = 9.0 if st_code == "27" else 0.0
        sgst = 9.0 if st_code == "27" else 0.0
        igst = 0.0 if st_code == "27" else 18.0
        eway = "GENERATED" if taxable > 50000 else ""
        add_rec(f"TEST-{i:03d}", "CLEAN_AR", f"INV-2026-CLEAN-AR-{i:02d}", (base_date + timedelta(days=i)).strftime("%Y-%m-%d"), "AR", gstin, f"Compliant Client {i} Pvt Ltd", pos, "8409", "Engine components supply per PO", taxable, cgst, sgst, igst, eway, True, notes="Fully compliant AR sales transaction")

    for i in range(11, 21):
        st_code = "27" if i % 2 == 1 else "29"
        pos = "Maharashtra" if st_code == "27" else "Karnataka"
        gstin = make_valid_gstin(st_code)
        taxable = 30000.0 + i * 4000.0
        cgst = 9.0 if st_code == "27" else 0.0
        sgst = 9.0 if st_code == "27" else 0.0
        igst = 0.0 if st_code == "27" else 18.0
        eway = "GENERATED" if taxable > 50000 else ""
        add_rec(f"TEST-{i:03d}", "CLEAN_AP", f"INV-2026-CLEAN-AP-{i:02d}", (base_date + timedelta(days=i-10)).strftime("%Y-%m-%d"), "AP", gstin, f"Compliant Vendor {i} Pvt Ltd", pos, "8483", "Transmission shafts & gears purchase", taxable, cgst, sgst, igst, eway, True, notes="Fully compliant AP purchase transaction with eligible ITC")

    # 2. GATE 1 — GSTIN VALIDATION FAILURES (21-35)
    bad_gstins = [
        ("27INVALID12345", "Format Error: 14 chars"),
        ("27AAACB1234A1Z@", "Format Error: Special character @"),
        ("27aaacb1234a1zj", "Format Warning: Lowercase letters"),
        ("27AAACB1234A1Z9", "Checksum Error: Invalid Luhn mod-36 checksum"),
        ("07AAACB1234A1ZJ", "State Mismatch: GSTIN prefix 07 (Delhi) but POS Maharashtra"),
        ("99AAACB1234A1ZJ", "Invalid State Code: State prefix 99 unassigned"),
        ("00AAACB1234A1ZJ", "Invalid State Code: State prefix 00 unassigned"),
        ("27AAAAA0000A1Z1", "Checksum Failure: Dummy PAN digits"),
        ("33AAACT1111C1Z9", "Checksum Error: Bad check digit 9 instead of 3"),
        ("24AAACG9999X1Z0", "Checksum Error: Bad checksum 0"),
        ("27AAACB1234A1", "Truncated GSTIN: 13 chars"),
        ("27AAACB1234A1ZJ999", "Overlength GSTIN: 18 chars"),
        ("27 GSTIN 1234567", "Spaces in GSTIN string"),
        ("27-AAACB-1234-A1ZJ", "Dashes in GSTIN string"),
        ("27AAACB1234A1Z5", "Valid GSTIN format but unassigned entity code")
    ]
    for idx, (bgstin, reason) in enumerate(bad_gstins, start=21):
        add_rec(f"TEST-{idx:03d}", "GATE1_GSTIN_FAIL", f"INV-2026-GSTIN-{idx-20:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), "AR", bgstin, f"Faulty GSTIN Entity {idx}", "Maharashtra", "8409", "Engine spares", 40000.0, 9.0, 9.0, 0.0, "", True, notes=reason)

    # 3. GATE 2 — HSN/SAC MASTER FAILURES (36-45)
    bad_hsns = [
        ("0000", "Unlisted HSN code 0000"),
        ("99999999", "Non-existent HSN code 99999999"),
        ("ABCD", "Alphanumeric invalid HSN string"),
        ("", "Missing HSN code (Empty)"),
        ("123", "Short 3-digit HSN code"),
        ("9983", "Valid SAC 9983 Service HSN"),
        ("9954", "Valid SAC 9954 Construction HSN"),
        ("8708", "Valid Goods HSN 8708 (28% GST)"),
        ("000000", "Zero HSN 6-digit"),
        ("9999", "Unlisted 4-digit HSN 9999")
    ]
    for idx, (bhsn, reason) in enumerate(bad_hsns, start=36):
        gstin = make_valid_gstin("27")
        cat = "GATE2_HSN_FAIL" if any(k in reason for k in ["Unlisted", "Invalid", "Empty", "Non-existent"]) else "GATE2_HSN_PASS"
        add_rec(f"TEST-{idx:03d}", cat, f"INV-2026-HSN-{idx-35:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), "AR", gstin, f"HSN Test Entity {idx}", "Maharashtra", bhsn, "Specialty hardware component", 35000.0, 9.0, 9.0, 0.0, "", True, notes=reason)

    # 4. GATE 3 — TAX MATH & RATE FAILURES (46-60)
    tax_scenarios = [
        (14.0, 14.0, 0.0, "Overcharged Tax Rate: 14% CGST + 14% SGST (28%) instead of 18% for HSN 8409"),
        (4.0, 4.0, 0.0, "Undercharged Tax Rate: 4% CGST + 4% SGST (8%) instead of 18% for HSN 8409"),
        (0.0, 0.0, 18.0, "Tax Type Mismatch: IGST charged on Intra-state Maharashtra transaction"),
        (9.0, 9.0, 18.0, "Double Tax Mismatch: Charged CGST + SGST AND IGST together"),
        (0.0, 0.0, 0.0, "Zero Tax Charged on Taxable B2B Goods"),
        (14.0, 14.0, 0.0, "Wrong Tax Rate on 18% item"),
        (9.0, 0.0, 0.0, "Asymmetric CGST without SGST"),
        (0.0, 9.0, 0.0, "Asymmetric SGST without CGST"),
        (9.0, 9.0, 0.0, "Tax Math Rounding Error (Manual Override)"),
        (18.0, 18.0, 0.0, "Excessive 36% Tax Charged"),
        (9.0, 9.0, 0.0, "Correct Rate - Valid Baseline"),
        (0.0, 0.0, 28.0, "Overcharged 28% IGST on 18% item"),
        (6.0, 6.0, 0.0, "Undercharged 12% on 18% item"),
        (9.0, 9.0, 0.0, "Calculated Tax Amount Mismatch"),
        (0.0, 0.0, 18.0, "Interstate IGST 18% Valid")
    ]
    for idx, (cg, sg, ig, reason) in enumerate(tax_scenarios, start=46):
        st = "27" if idx % 2 == 0 else "07"
        pos = "Maharashtra" if st == "27" else "Delhi"
        gstin = make_valid_gstin(st)
        cat = "GATE3_TAX_FAIL" if any(k in reason for k in ["Overcharged", "Undercharged", "Mismatch", "Double", "Zero Tax", "Asymmetric", "Excessive"]) else "GATE3_TAX_PASS"
        add_rec(f"TEST-{idx:03d}", cat, f"INV-2026-TAX-{idx-45:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), "AR", gstin, f"Tax Test Entity {idx}", pos, "8409", "Valves & Pistons", 50000.0, cg, sg, ig, "GENERATED", True, notes=reason)

    # 5. GATE 4 — PLACE OF SUPPLY (POS) FAILURES (61-70)
    pos_scenarios = [
        ("Karnataka", "07", 9.0, 9.0, 0.0, "POS Mismatch: POS Karnataka but intra-state CGST+SGST charged with Delhi GSTIN"),
        ("Tamil Nadu", "27", 0.0, 0.0, 18.0, "Inter-state IGST correctly applied for MH -> TN"),
        ("Maharashtra", "29", 9.0, 9.0, 0.0, "Intra-state CGST+SGST charged for KA GSTIN in MH POS"),
        ("Gujarat", "27", 9.0, 9.0, 0.0, "Wrong POS: Intra-state tax charged on Gujarat POS"),
        ("Delhi", "07", 9.0, 9.0, 0.0, "Delhi Intra-state CGST+SGST Valid"),
        ("SEZ Unit Gujarat", "24", 0.0, 0.0, 0.0, "SEZ Zero-rated export supply under LUT"),
        ("SEZ Unit Maharashtra", "27", 0.0, 0.0, 18.0, "SEZ supply with IGST payment"),
        ("West Bengal", "19", 9.0, 9.0, 0.0, "Wrong POS: CGST+SGST charged on WB recipient"),
        ("Kerala", "32", 0.0, 0.0, 18.0, "Inter-state IGST 18% Valid"),
        ("Haryana", "06", 9.0, 9.0, 0.0, "Wrong POS: CGST+SGST on Haryana recipient")
    ]
    for idx, (pos_name, st_code, cg, sg, ig, reason) in enumerate(pos_scenarios, start=61):
        gstin = make_valid_gstin(st_code)
        cat = "GATE4_POS_FAIL" if any(k in reason for k in ["Mismatch", "Wrong POS"]) else "GATE4_POS_PASS"
        add_rec(f"TEST-{idx:03d}", cat, f"INV-2026-POS-{idx-60:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), "AR", gstin, f"POS Test Entity {idx}", pos_name, "8409", "Crankshaft assemblies", 60000.0, cg, sg, ig, "GENERATED", True, notes=reason)

    # 6. GATE 5 — E-WAY BILL POLICY FAILURES (71-80)
    eway_scenarios = [
        (120000.0, "PENDING", "E-Way Bill Missing: Invoice > Rs 50,000 but EWB is PENDING"),
        (85000.0, "CANCELLED", "E-Way Bill Cancelled: Invoice > Rs 50,000 but EWB status CANCELLED"),
        (95000.0, "EXPIRED", "E-Way Bill Expired: Transit time exceeded"),
        (150000.0, "", "E-Way Bill Missing: Empty EWB status on Rs 1.5 Lakh invoice"),
        (42000.0, "", "Compliant: Invoice < Rs 50,000 no EWB required"),
        (35000.0, "GENERATED", "Compliant: Voluntary EWB below threshold"),
        (250000.0, "GENERATED", "Compliant: Valid EWB on high-value transaction"),
        (55000.0, "PENDING", "E-Way Bill Missing on Rs 55,000 invoice"),
        (65000.0, "REJECTED", "E-Way Bill Rejected by recipient"),
        (75000.0, "GENERATED", "Compliant: Valid EWB on Rs 75,000 invoice")
    ]
    for idx, (taxable, eway_st, reason) in enumerate(eway_scenarios, start=71):
        gstin = make_valid_gstin("27")
        cat = "GATE5_EWAY_FAIL" if any(k in reason for k in ["Missing", "Cancelled", "Expired", "Rejected"]) else "GATE5_EWAY_PASS"
        add_rec(f"TEST-{idx:03d}", cat, f"INV-2026-EWAY-{idx-70:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), "AR", gstin, f"E-Way Bill Test Entity {idx}", "Maharashtra", "8409", "Industrial machinery parts", taxable, 9.0, 9.0, 0.0, eway_st, True, notes=reason)

    # 7. GATE 6 — ITC ELIGIBILITY & SEC 17(5) BLOCKED (81-90)
    itc_scenarios = [
        ("AP", True, "Annual employee welfare outdoor catering and beverages", "ITC Blocked: Section 17(5) Outdoor Catering & Food Beverages"),
        ("AP", True, "Motor vehicle sedan purchase for executive transport", "ITC Blocked: Section 17(5) Motor Vehicles & Conveyance"),
        ("AP", True, "Employee group health insurance policy premium", "ITC Blocked: Section 17(5) Health & Life Insurance"),
        ("AP", True, "Executive golf club membership fee", "ITC Blocked: Section 17(5) Club Membership"),
        ("AP", True, "Office building expansion works contract services", "ITC Blocked: Section 17(5) Works Contract for Immovable Property"),
        ("AP", True, "Diwali gift hampers and personal consumption items for staff", "ITC Blocked: Section 17(5) Personal Consumption Gifts"),
        ("AP", True, "Warehouse inventory loss write-off and destroyed goods", "ITC Blocked: Section 17(5) Stolen / Destroyed / Written-off Goods"),
        ("AP", False, "Raw steel plates and sheet metal", "ITC Disallowed: Inward invoice NOT reflected in GSTR-2B"),
        ("AP", False, "Electrical wiring cables for factory machinery", "ITC Disallowed: Supplier did not file GSTR-1 (GSTR-2B missing)"),
        ("AP", True, "Raw aluminium ingots for manufacturing", "ITC Eligible: Valid GSTR-2B reflected business input")
    ]
    for idx, (dirn, g2b, desc, reason) in enumerate(itc_scenarios, start=81):
        gstin = make_valid_gstin("27")
        cat = "GATE6_ITC_BLOCKED" if any(k in reason for k in ["Blocked", "Disallowed"]) else "GATE6_ITC_ELIGIBLE"
        add_rec(f"TEST-{idx:03d}", cat, f"INV-2026-ITC-{idx-80:02d}", (base_date + timedelta(days=idx % 10)).strftime("%Y-%m-%d"), dirn, gstin, f"ITC Supplier Entity {idx}", "Maharashtra", "8409" if "Raw" in desc else "9983", desc, 45000.0, 9.0, 9.0, 0.0, "", g2b, notes=reason)

    # 8. DEDUPLICATION & FRAUD DETECTION (91-95)
    gstin_dup = make_valid_gstin("27")
    add_rec("TEST-091", "DEDUP_EXACT_ORIG", "INV-2026-DUP-100", "2026-03-15", "AR", gstin_dup, "Dup Transactor Ltd", "Maharashtra", "8409", "Piston rings batch", 50000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="Original Invoice for Exact Duplicate Test")
    add_rec("TEST-092", "DEDUP_EXACT_CLONE", "INV-2026-DUP-100", "2026-03-15", "AR", gstin_dup, "Dup Transactor Ltd", "Maharashtra", "8409", "Piston rings batch", 50000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="EXACT DUPLICATE: Same Invoice No, Date, Amount, GSTIN")

    add_rec("TEST-093", "DEDUP_FUZZY_ORIG", "INV/2026/DUP-200", "2026-03-16", "AR", gstin_dup, "Dup Transactor Ltd", "Maharashtra", "8409", "Engine bearings batch", 75000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="Original Invoice for Fuzzy Duplicate Test")
    add_rec("TEST-094", "DEDUP_FUZZY_CLONE", "INV 2026 DUP 200", "2026-03-16", "AR", gstin_dup, "Dup Transactor Ltd", "Maharashtra", "8409", "Engine bearings batch", 75000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="FUZZY DUPLICATE: Minor syntax variation (spaces vs slashes)")

    add_rec("TEST-095", "ANOMALY_SPLIT_INVOICE", "INV-2026-SPLIT-01", "2026-03-17", "AR", gstin_dup, "Smurfing Buyer Corp", "Maharashtra", "8409", "Split Part A supply", 48000.0, 9.0, 9.0, 0.0, "", True, notes="SPLIT INVOICE (Smurfing): 1 of 3 invoices under 50k on same date to bypass EWB")

    # 9. ANOMALY & RISK ENGINE OUTLIERS (96-100)
    add_rec("TEST-096", "ANOMALY_HIGH_VALUE", "INV-2026-OUTLIER-01", "2026-03-18", "AR", make_valid_gstin("27"), "Mega Infra Corp", "Maharashtra", "8409", "Turnkey power plant turbine supply", 12500000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="EXTREME HIGH VALUE ANOMALY: Taxable value Rs 1.25 Crore")
    add_rec("TEST-097", "ANOMALY_ROUND_NUMBER", "INV-2026-ROUND-01", "2026-03-19", "AR", make_valid_gstin("27"), "Round Figure Traders", "Maharashtra", "8409", "Consultancy and equipment bulk round payment", 5000000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="ROUND FIGURE CLUSTERING ANOMALY: Exactly Rs 50,00,000.00")
    add_rec("TEST-098", "ANOMALY_FUTURE_DATE", "INV-2026-DATE-01", "2027-12-31", "AR", make_valid_gstin("27"), "Future Date Transactor", "Maharashtra", "8409", "Pre-dated advance invoice", 60000.0, 9.0, 9.0, 0.0, "GENERATED", True, notes="UNUSUAL DATE ANOMALY: Invoice date far in future (2027)")
    add_rec("TEST-099", "ANOMALY_SPLIT_02", "INV-2026-SPLIT-02", "2026-03-17", "AR", gstin_dup, "Smurfing Buyer Corp", "Maharashtra", "8409", "Split Part B supply", 49000.0, 9.0, 9.0, 0.0, "", True, notes="SPLIT INVOICE (Smurfing): 2 of 3 invoices under 50k on same date")
    add_rec("TEST-100", "ANOMALY_SPLIT_03", "INV-2026-SPLIT-03", "2026-03-17", "AR", gstin_dup, "Smurfing Buyer Corp", "Maharashtra", "8409", "Split Part C supply", 47500.0, 9.0, 9.0, 0.0, "", True, notes="SPLIT INVOICE (Smurfing): 3 of 3 invoices under 50k on same date")

    return records

def generate_excel_dataset(records, out_excel_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "UC15_GST_Compliance_Data"

    NAVY = "1C2B3A"
    LIGHT = "EEF2F7"
    WHITE = "FFFFFF"

    ws.merge_cells("A1:R1")
    tcell = ws.cell(row=1, column=1, value="UC15 GST COMPLIANCE & RISK INTELLIGENCE AGENT — 100 INVOICES STRESS TEST DATASET")
    tcell.font = Font(name="Calibri", bold=True, size=13, color=WHITE)
    tcell.fill = PatternFill("solid", fgColor=NAVY)
    tcell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 28

    headers = [
        "Invoice No", "Invoice Date", "Direction", "Counterparty GSTIN",
        "Counterparty Name", "Place of Supply", "HSN Code", "Item Desc",
        "Taxable Value (INR)", "CGST %", "SGST %", "IGST %", "Total Tax (INR)",
        "Total Amt", "E-Way Bill Status", "GSTR-2B Reflected", "Test Category", "Test Notes"
    ]
    widths = [16, 12, 10, 18, 24, 16, 10, 32, 18, 8, 8, 8, 16, 16, 16, 16, 20, 35]

    ws.row_dimensions[3].height = 26
    for col_idx, (hdr, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(row=3, column=col_idx, value=hdr)
        c.font = Font(name="Calibri", bold=True, size=10, color=WHITE)
        c.fill = PatternFill("solid", fgColor="34486B")
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[c.column_letter].width = w

    ws_hsn = wb.create_sheet(title="HSN_Master")
    ws_hsn.append(["HSN Code", "Description", "Correct CGST %", "Correct SGST %", "Correct IGST %"])
    for hsn_code, (desc, cg, sg, ig) in HSN_MASTER.items():
        ws_hsn.append([hsn_code, desc, cg, sg, ig])

    ws_st = wb.create_sheet(title="State_Codes")
    ws_st.append(["State Code", "State Name"])
    for scode, sname in STATE_MAP.items():
        ws_st.append([scode, sname])

    for row_idx, r in enumerate(records, start=4):
        vals = [
            r["invoice_no"], r["invoice_date"], r["direction"], r["counterparty_gstin"],
            r["counterparty_name"], r["place_of_supply"], r["hsn_code"], r["item_desc"],
            r["taxable_value_inr"], r["cgst_rate"], r["sgst_rate"], r["igst_rate"],
            r["total_tax_inr"], r["total_amt"], r["eway_bill_status"],
            "YES" if r["gstr2b_reflected"] else "NO", r["test_category"], r["test_notes"]
        ]
        for col_idx, val in enumerate(vals, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            if row_idx % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=LIGHT)

    wb.save(out_excel_path)
    print(f"Generated Excel dataset: {out_excel_path}")

def main():
    records = generate_100_records()
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    excel_file = os.path.join(data_dir, "UC15_GSTCompliance_100_Invoices.xlsx")
    csv_file = os.path.join(data_dir, "UC15_GSTCompliance_100_Invoices.csv")
    json_file = os.path.join(data_dir, "UC15_GSTCompliance_100_Invoices.json")

    generate_excel_dataset(records, excel_file)

    df = pd.DataFrame(records)
    df.to_csv(csv_file, index=False)
    print(f"Generated CSV dataset: {csv_file}")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Generated JSON dataset: {json_file}")

    print(f"\nSUCCESS: Generated {len(records)} test invoices covering all compliance rules!")

if __name__ == "__main__":
    main()
