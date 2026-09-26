# UC15 — GST Compliance Intelligence & Resolution Agent
### Enterprise SAP S/4HANA Live Integration · India GST FI-Tax Statutory Automation

[![SAP S/4HANA Ready](https://img.shields.io/badge/SAP%20S%2F4HANA-Live%20OData%20V4%20(DI01)-0070ba?style=flat-square&logo=sap)](https://www.sap.com)
[![Compliance Gates](https://img.shields.io/badge/Statutory%20Gates-6%20Sequential%20Gates-059669?style=flat-square)](docs/architecture/SPRINT_2_DATA_AND_RULE_ENGINE.md)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20Tailwind%20%7C%20Framer%20Motion-2563eb?style=flat-square)](frontend/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Uvicorn%20%7C%20Python%203.11+-38bdf8?style=flat-square)](ui/app.py)
[![Test Suite](https://img.shields.io/badge/Tests-129%20Passing%20(100%25)-emerald?style=flat-square)](tests/)

---

## 📌 Executive Overview

**UC15** is an enterprise-grade statutory compliance validation, risk intelligence, and autonomous resolution platform purpose-built for Indian Goods and Services Tax (GST) compliance within **SAP S/4HANA Financial Accounting (FI-Tax)** environments.

Unlike composite-score systems, GST filing compliance is an uncompromising statutory checklist: a financial transaction either satisfies statutory thresholds and legal provisions, or it triggers rejection, penalties, and tax audit exposure. UC15 continuously synchronizes live transaction ledgers from SAP S/4HANA, validates every invoice across **six deterministic statutory gates**, quantifies exact financial exposure, isolates systemic root causes, and provides an interactive **AI Tax Lead Copilot** with live RAG and typewriter streaming.

---

## 🏛️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                SAP S/4HANA (Cloud / On-Premise)                       │
│     Company Code: DI01  ·  Client: 200  ·  Tables: BKPF, BSEG, KONV, KNA1, LFA1        │
│          OData V4 Service: /sap/opu/odata4/sap/z_gst_sb/srvd_a2x/sap/zui_gst_invoices/0001│
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │  Live Replicated Feeds (Outward & Inward)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        UC15 Core Engine (FastAPI & Deterministic Core)                  │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Sequential 6-Gate Statutory Rule Engine 2.0                   │  │
│  │                                                                                  │  │
│  │   Gate 1: GSTIN Modulo-36 Checksum (Luhn Alg) & State Alignment (GSTIN_001)      │  │
│  │   Gate 2: Temporal HSN/SAC Classification Validity (HSN_001)                      │  │
│  │   Gate 3: Statutory Schedule Tax Rate Verification (TAX_001)                      │  │
│  │   Gate 4: Place of Supply vs State Tax Jurisdiction (POS_001)                     │  │
│  │   Gate 5: Rule 138 E-Way Bill National & State Threshold Check (EWB_001)         │  │
│  │   Gate 6: Section 17(5) Blocked Credit & GSTR-2B Auto-Reconciliation (ITC_001)   │  │
│  └───────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                          │                                             │
│  ┌───────────────────────────────────────▼──────────────────────────────────────────┐  │
│  │                      Downstream Intelligence Subsystems                          │  │
│  │                                                                                  │  │
│  │  • Risk Engine: 0–100 Weighted Score · P1–P4 Operational Priority Triage         │  │
│  │  • Financial Impact Engine: Quantified Tax Differences & Blocked ITC Exposure    │  │
│  │  • Root Cause Subsystem: Cluster Detection, Duplicate Signal Anomaly (RC-DUP)    │  │
│  │  • Statutory Audit Trail: Immutable ReferenceSnapshot on every transaction        │  │
│  └───────────────────────────────────────┬──────────────────────────────────────────┘  │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           │  REST APIs (/api/dashboard/overview, /api/results/latest)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       Modern Minimal White React 18 Application                        │
│                                                                                        │
│   • Executive Cockpit: Real-time Compliance Health Score, Live SAP Status, KPI Cards   │
│   • Invoice Audit: Granular table with interactive Gate Pips and deep-dive inspection  │
│   • Investigations & Cases: Root Cause Dossier, Blast Radius, Case Resolution triage  │
│   • Floating AI Agent Copilot: Live multi-turn statutory queries with typewriter stream│
│   • Stack: Vite · Tailwind CSS 3 · Framer Motion · Lenis Smooth Scroll · TanStack Query│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ The Six Sequential Statutory Validation Gates

Every transaction is evaluated in sequence through six statutory checkpoints. If a critical gate fails, downstream actions are adjusted deterministically:

| Gate | Identifier | Statutory Basis | Severity | Business Impact if Failed |
|---|---|---|---|---|
| **Gate 1** | `GSTIN_001` | Section 22–25, CGST Act · Luhn Mod-36 | **CRITICAL** | Hard Filing Blocker. Invalid GSTIN causes immediate GSTR-1/3B rejection. |
| **Gate 2** | `HSN_001` | Section 9 · Customs Tariff Act Schedules | **HIGH** | Classification dispute; wrong schedule rate application. |
| **Gate 3** | `TAX_001` | Notification 1/2017 & 2/2017 Integrated Tax | **HIGH** | Short-payment or excess tax collection; demand notices under Section 73/74. |
| **Gate 4** | `POS_001` | Section 10 & 12, IGST Act 2017 | **HIGH** | Tax head mismatch (charging CGST+SGST instead of IGST); non-transferable credit. |
| **Gate 5** | `EWB_001` | Rule 138, CGST Rules (State & National) | **MEDIUM** | Goods transit seizure under Section 129; 200% penalty on applicable tax. |
| **Gate 6** | `ITC_001` | Section 16(2)(aa) & 17(5), CGST Act | **HIGH** | Ineligible credit reversal with 18% mandatory interest; GSTR-2B mismatch. |

### Decision Outcomes & Operational Turnaround SLAs

* **`COMPLIANT`** (0 gate failures): Clean invoice. Automatically marked filing-ready for current GSTR period.
* **`NEEDS_REVIEW`** (1 gate failure): Flagged for tax accountant intervention. **24-hour SLA**.
* **`NON_COMPLIANT`** (2+ failures or Gate 1 fail): Critical hold placed on invoice posting. **4-hour immediate SLA**.

---

## 🔗 SAP S/4HANA & In-Memory HANA Database Connectivity

UC15 interfaces directly with live **SAP S/4HANA (FI-AP / FI-GL / MM-LIV)** and the underlying **SAP HANA Columnar Database**:

* **HANA Database Host**: `hana-s4h-db01.corp.internal:39015` (SQL/HDB port)
* **Instance / Tenant**: `HDB` / `S4H_FIN_PROD`
* **Schema**: `SAPABAP1`
* **Company Code**: `DI01` (Bharat Heavy Electricals & Precision Tech Manufacturing)
* **Client**: `200`
* **Base OData V4 Endpoint**: `http://<SAP_HOST>:8000/sap/opu/odata4/sap/z_gst_sb/srvd_a2x/sap/zui_gst_invoices/0001`
* **Live Ingested Tables & CDS Views**:
  * **`ACDOCA`**: Universal Journal Entry Line Items (real-time zero-balance double entry).
  * **`BKPF`**: Accounting Document Header (`BLART`, `BUDAT`, `XBLNR`).
  * **`BSEG`**: Accounting Document Segment (`BSCHL`, `HKONT`, `MWSKZ`, `ZLSPR`, `ZFBDT`).
  * **`BSIK` / `BSAK`**: Vendor Open & Cleared Items (AP payment runs and aging).
  * **`RBKP`**: Logistics Invoice Verification (MIRO 3-way match).
  * **`VBRK` / `VBRP`**: SD Billing Documents (Outward AR).

### 🚀 One-Click Live HANA DB Synchronization
Users can trigger real-time ledger extraction directly from the Overview page via the **"Sync from HANA DB"** station (`POST /api/sap/sync`). Every sync event is immutably logged in the centralized System Audit Trail (`/audit`) with source timestamps, schema signatures, and document counts.

---

## 💼 Enterprise SAP FICO Accounting & Financial Controls

A senior-manager-grade enterprise tax application must not merely flag compliance errors; it must integrate directly into the SAP financial accounting lifecycle:

1. **Document Types (`BLART`)**:
   * **`KR`**: Vendor Invoice (FI-AP FB60 direct posting).
   * **`RE`**: Invoice Receipt (Logistics Invoice Verification / MIRO).
   * **`KG`**: Vendor Credit Memo / Debit Note for rate or quantity adjustments.
2. **Posting Keys (`BSCHL`) & Double-Entry Simulation**:
   * **`BSCHL 31`**: Vendor Account Credit (Gross liability).
   * **`BSCHL 40`**: G/L Account Debit (Base Material/Expense Debit).
   * **`BSCHL 40`**: Tax G/L Debit (Input CGST, SGST, IGST with condition types `JICG`, `JISG`, `JIIG`).
   * **`BSCHL 50`**: Revenue & Tax Credit for AR customer invoices (`JOCG`, `JOSG`, `JOIG`).
   * **Zero-Balance Invariant**: Verification that $\sum \text{Debits} + \sum \text{Credits} = 0.00$.
3. **Automated SAP Payment Blocks (`BSEG-ZLSPR`)**:
   * If an invoice fails critical compliance gates (e.g. Cancelled Vendor GSTIN, POS mismatch, Tax Drift):
     * The system allows one-click application of **`BSEG-ZLSPR = 'R'`** (Invoice Verification Block) or **`'A'`** (Payment Block), immediately halting automated disbursements in `F110` Payment Run.
     * When cleared, the block is released (`BSEG-ZLSPR = ''`) with full audit traceability.
4. **Section 16(2) 180-Day Rule Aging & Section 50(3) Interest**:
   * Tracks invoice aging from baseline date (`ZFBDT`).
   * Automatically flags overdue invoices exceeding 180 days where ITC must be reversed in GSTR-3B Table 4(B)(2), calculating exact interest liability under Section 50(3) at **18% p.a.**.
5. **Section 17(5) Blocked Credit Reclassification**:
   * Detects blocked items (HSN 8703 Motor Vehicles, HSN 9963 Outdoor Catering, Club Memberships).
   * Automatically capitalizes non-creditable tax into the base expense G/L (`BSCHL 40`, Condition `JICX`/`JISX`) instead of claiming ineligible input tax.

---

## 🎨 Minimal White Enterprise UI

The user interface is designed with a **Stripe / Linear-inspired minimal white & crisp light gray** aesthetic:

* **Ultra-Clean Palette**: `#FFFFFF` cards, `#F9FAFB` background, delicate 1px `#E5E7EB` borders, royal blue accents, and emerald/amber/red status indicators.
* **Framer Motion Animations**: Sub-pixel transitions, stagger animations on KPI cards, and smooth scale-ins.
* **Lenis Smooth Scrolling**: High-performance inertial scrolling across all tables and dashboards.
* **Interactive Gate Pips**: Color-coded statutory gate status beads (`PASS`, `FAIL`, `N/A`) on each invoice row.
* **Detailed Inspection Dossier**: Clicking any invoice opens the complete statutory audit sheet with all 6 gate calculation traces, SAP accounting document references, and tax recommendations.
* **Persistent Floating AI Agent (Bottom-Right)**:
  * Openable from any screen via the bottom-right trigger badge.
  * Real-time multi-step investigation indicator (*"Inspecting statutory rules...", "Synthesizing determination..."*).
  * Natural **typewriter streaming** mimicking human tax lead interaction.
  * Quick-prompt pills for one-click compliance and exposure analysis.

---

## 📁 Repository Structure

```text
uc15/
├── app/
│   ├── agent/                 # Master Compliance Agent & AI Investigation Orchestrator
│   │   ├── ai/                # AI Investigation Agent, RAG engine, multi-turn session manager
│   │   └── compliance_agent.py# Core compliance workflow runner
│   ├── domain/                # Canonical domain models (Invoice, Decision, Counterparty, Risk)
│   ├── engine/                # ValidationEngine, DecisionEngine, RiskEngine
│   ├── rules/                 # Six statutory compliance rules & Data Quality rules
│   ├── reference/             # Temporal Reference Intelligence (HSN, Tax, States, Policies)
│   ├── financial/             # Quantified financial exposure & tax discrepancy calculators
│   ├── historical/            # Time-series trends, recurring patterns, and audit analysis
│   ├── intelligence/          # Anomaly detection, duplicate clustering & candidate analysis
│   ├── investigation/         # Systemic Root Cause Engine & Blast Radius profiling
│   └── infrastructure/        # Correlation tracking, logging, health checkers
│
├── frontend/                  # React 18 + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── agent/         # FloatingChatbot.jsx (Bottom-right floating AI Agent)
│   │   │   ├── layout/        # Sidebar.jsx, Topbar.jsx, Layout.jsx
│   │   │   └── ui/            # Reusable animations & primitives (Framer Motion, badges, etc.)
│   │   ├── pages/             # Overview.jsx, Compliance.jsx, InvoiceDetail.jsx, etc.
│   │   ├── lib/               # api.js (Axios client with FastAPI proxy), utils.js
│   │   ├── index.css          # Minimal white design system & Tailwind layer rules
│   │   └── App.jsx            # Router & React Query Provider
│   └── vite.config.js         # Vite configuration with /api proxy to FastAPI
│
├── config/
│   ├── references/            # Statutory catalogs (HSN, Tax Rates, State Codes, Policies)
│   ├── risk/                  # YAML policies for scoring weights, priority, and brackets
│   └── investigation/         # Root cause and blast radius detection policies
│
├── data/                      # Dataset repository (UC15_GSTCompliance_Dataset.xlsx)
├── tests/                     # 129 unit, integration, and regression tests
├── ui/                        # FastAPI dashboard application (ui/app.py) & static mount
├── main.py                    # Master CLI runner
├── run.py                     # Operational CLI & UI server launcher
├── requirements.txt           # Python dependencies
└── .env                       # Environment configuration
```

---

## 🚀 Getting Started

### Prerequisites

* **Python 3.11+**
* **Node.js 18+ & npm 9+**

### 1. Backend Setup

```bash
# Clone the repository
cd uc15

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI Server (Port 8000)
python run.py --ui --port 8000
```

The backend server will start at **`http://localhost:8000`** with interactive OpenAPI documentation available at **`http://localhost:8000/docs`**.

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server (Port 5173)
npm run dev
```

Open your browser at **`http://localhost:5173/`**.  
*(All `/api/...` calls automatically proxy to the FastAPI backend at port 8000).*

To compile the production frontend for direct serving via FastAPI:
```bash
npm run build
```
Once built, visiting **`http://localhost:8000/`** serves the React application directly from FastAPI!

---

## ⚙️ Environment Configuration (`.env`)

```ini
# Application Mode
APP_ENV=development
LOG_LEVEL=INFO

# Server Ports
API_PORT=8000
API_HOST=0.0.0.0

# SAP S/4HANA Live OData V4 Settings
SAP_ODATA_BASE_URL=http://192.168.1.55:8000/sap/opu/odata4/sap/z_gst_sb/srvd_a2x/sap/zui_gst_invoices/0001
SAP_CLIENT=200
SAP_COMPANY_CODE=DI01
SAP_AUTH_TYPE=basic
SAP_USERNAME=Int_Samarth
SAP_PASSWORD=Tonystark@12345
SAP_OUTWARD_ENTITY=OutwardInvoice
SAP_INWARD_ENTITY=InwardInvoice

# Business Rule Thresholds
EWAY_BILL_THRESHOLD_INR=50000
RATE_TOLERANCE_PCT=0.01

# Operational Turnaround SLAs (Hours)
NEEDS_REVIEW_SLA_HOURS=24
NON_COMPLIANT_SLA_HOURS=4
```

---

## 🧪 Testing & Quality Assurance

Run the comprehensive test suite verifying the 6 statutory gates, reference resolvers, and scoring engines:

```bash
# Execute master test runner (129/129 tests passing)
python tests/run_all_tests.py
```

---

## 📜 Compliance & Regulatory Standards

UC15 is aligned with:
* **Central Goods and Services Tax Act, 2017** (Sections 9, 10, 16, 17(5), 22, 25, 35, 129)
* **Integrated Goods and Services Tax Act, 2017** (Sections 7, 8, 10, 12)
* **CGST Rules, 2017** (Rule 36(4), Rule 138 E-Way Bill provisions)
* **SAP S/4HANA FI Localization for India** (GSTIN, HSN condition records, BKPF/BSEG journal postings)

---

## 📄 License

Proprietary enterprise software built for SAP S/4HANA GST FI-Tax compliance workflows.
