/**
 * UC15 GST Compliance Platform — Final Unified Invoice Compliance, Correction & Approval Workspace
 * Single-page end-to-end lifecycle:
 * Open Invoice -> Understand Compliance -> Fix Issues -> Re-check -> Approve
 */

const GST_STATE_CODES = {
  '01': 'Jammu and Kashmir',
  '02': 'Himachal Pradesh',
  '03': 'Punjab',
  '04': 'Chandigarh',
  '05': 'Uttarakhand',
  '06': 'Haryana',
  '07': 'Delhi',
  '08': 'Rajasthan',
  '09': 'Uttar Pradesh',
  '10': 'Bihar',
  '11': 'Sikkim',
  '12': 'Arunachal Pradesh',
  '13': 'Nagaland',
  '14': 'Manipur',
  '15': 'Mizoram',
  '16': 'Tripura',
  '17': 'Meghalaya',
  '18': 'Assam',
  '19': 'West Bengal',
  '20': 'Jharkhand',
  '21': 'Odisha',
  '22': 'Chhattisgarh',
  '23': 'Madhya Pradesh',
  '24': 'Gujarat',
  '25': 'Daman and Diu',
  '26': 'Dadra and Nagar Haveli',
  '27': 'Maharashtra',
  '28': 'Andhra Pradesh',
  '29': 'Karnataka',
  '30': 'Goa',
  '31': 'Lakshadweep',
  '32': 'Kerala',
  '33': 'Tamil Nadu',
  '34': 'Puducherry',
  '35': 'Andaman and Nicobar Islands',
  '36': 'Telangana',
  '37': 'Andhra Pradesh',
  '38': 'Ladakh',
  '97': 'Other Territory',
  '99': 'Center Jurisdiction'
};

function normalizeStateName(val) {
  if (!val) return 'Maharashtra';
  const str = String(val).trim();
  if (/^\d{1,2}$/.test(str)) {
    const code = str.padStart(2, '0');
    if (GST_STATE_CODES[code]) return GST_STATE_CODES[code];
  }
  const match = str.match(/^(\d{2})[\s\-]+(.+)/);
  if (match && GST_STATE_CODES[match[1]]) return GST_STATE_CODES[match[1]];
  const lower = str.toLowerCase();
  for (const name of Object.values(GST_STATE_CODES)) {
    if (name.toLowerCase() === lower) return name;
  }
  return str;
}

function renderStateOptions(selectedVal) {
  const normSelected = normalizeStateName(selectedVal);
  let html = '<option value="">-- Select State / UT --</option>';
  
  // Sort by state code in ascending numeric order (01, 02, 03...)
  const sortedEntries = Object.entries(GST_STATE_CODES).sort((a, b) => Number(a[0]) - Number(b[0]));
  
  for (const [code, name] of sortedEntries) {
    const isSel = (code === String(selectedVal).padStart(2, '0') || name.toLowerCase() === String(selectedVal || '').toLowerCase() || name.toLowerCase() === normSelected.toLowerCase());
    html += `<option value="${code}" ${isSel ? 'selected' : ''}>${code} - ${name}</option>`;
  }
  return html;
}

function formatINR(val) {
  if (val === null || val === undefined || isNaN(Number(val))) return '₹0.00';
  const num = Number(val);
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

class InvoiceDetailView {
  constructor(container) {
    this.container = container;
    this.currentInvoiceId = null;
    this.dossier = null;
    this.corrections = [];
    this.approval = null;
    this.showAuditHistory = false;
    this.expandedGates = {};
  }

  async render(invoiceId) {
    this.currentInvoiceId = invoiceId;
    this.container.innerHTML = `
      <div class="investigation-view" style="max-width:1100px; margin:0 auto;">
        <div class="inv-breadcrumb" style="display:flex; align-items:center; gap:8px; font-size:12px; margin-bottom:16px;">
          <a href="#/compliance" style="color:#2563EB; text-decoration:none; font-weight:600;">&larr; Invoice Audit Center</a>
          <span style="color:#CBD5E1;">/</span>
          <span style="color:var(--text-primary); font-family:var(--font-mono); font-weight:700;">${invoiceId}</span>
        </div>

        <div id="investigationContainer">
          <div class="skeleton" style="height:120px; margin-bottom:16px; border-radius:10px; background:#E2E8F0;"></div>
          <div class="skeleton" style="height:200px; margin-bottom:16px; border-radius:10px; background:#FFFFFF;"></div>
        </div>
      </div>
    `;

    await this.loadDossier(invoiceId);
  }

  async loadDossier(invoiceId) {
    try {
      this.dossier = await window.gstApi.getInvoiceDossier(invoiceId);
      try {
        const corrRes = await window.gstApi.getInvoiceCorrections(invoiceId);
        this.corrections = (corrRes && corrRes.corrections) ? corrRes.corrections : [];
      } catch (_) {
        this.corrections = [];
      }
      try {
        const appRes = await window.gstApi.getInvoiceApproval(invoiceId);
        this.approval = (appRes && appRes.approval) ? appRes.approval : null;
      } catch (_) {
        this.approval = null;
      }
      this.renderDossier();
    } catch (err) {
      const container = document.getElementById('investigationContainer');
      if (container) {
        container.innerHTML = `
          <div class="error-banner" style="background:#FEF2F2; border:1px solid #FECACA; padding:20px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <strong style="color:#991B1B; font-size:14px;">Failed to load invoice workspace for ${invoiceId}</strong>
              <p style="font-size:12px; color:#7F1D1D; margin-top:4px;">${err.message}</p>
            </div>
            <a href="#/compliance" class="btn btn-outline" style="font-size:12px;">Back to Invoice Audit Center</a>
          </div>
        `;
      }
    }
  }

  toggleGateDetail(gateKey) {
    this.expandedGates[gateKey] = !this.expandedGates[gateKey];
    this.renderDossier();
  }

  toggleAuditHistory() {
    this.showAuditHistory = !this.showAuditHistory;
    this.renderDossier();
  }

  focusCorrectionField(fieldName) {
    const el = document.getElementById(`corr_${fieldName}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.focus();
      el.style.outline = '2px solid #2563EB';
      setTimeout(() => { el.style.outline = ''; }, 2000);
    }
  }

  renderDossier() {
    const d = this.dossier || {};
    const container = document.getElementById('investigationContainer');
    if (!container) return;

    const dec = d.decision || {};
    const can = d.canonical || {};
    const timeline = d.timeline || [];
    const gates = dec.gates || [];

    // Financial Values
    const taxableVal = can.taxable_value !== undefined ? can.taxable_value : (dec.taxable_value_inr || 0);
    const cgstAmt = can.cgst_amount !== undefined ? can.cgst_amount : 0;
    const sgstAmt = can.sgst_amount !== undefined ? can.sgst_amount : 0;
    const utgstAmt = can.utgst_amount !== undefined ? can.utgst_amount : 0;
    const igstAmt = can.igst_amount !== undefined ? can.igst_amount : 0;
    const cessAmt = can.cess_amount !== undefined ? can.cess_amount : 0;
    const totalTax = can.total_tax !== undefined ? can.total_tax : (cgstAmt + sgstAmt + utgstAmt + igstAmt + cessAmt);
    const invoiceTotal = can.total_amount !== undefined ? can.total_amount : (taxableVal + totalTax);

    // Direction & Party Simplification (Customer vs Vendor, NO 'Counterparty')
    const isAP = (dec.direction || can.direction || 'AP').toUpperCase() === 'AP';
    const partyRole = isAP ? 'Vendor' : 'Customer';
    const partyName = isAP ? (dec.counterparty_name || can.counterparty_name || 'Vendor') : (dec.counterparty_name || can.counterparty_name || 'Customer');
    const partyGstin = isAP ? (dec.counterparty_gstin || can.seller_gstin || 'N/A') : (dec.counterparty_gstin || can.buyer_gstin || 'N/A');

    const pos = normalizeStateName(can.place_of_supply || dec.place_of_supply || 'Maharashtra');
    const rawSupplierState = can.seller_state || (isAP ? (partyGstin && partyGstin.length >= 2 ? partyGstin.slice(0, 2) : pos) : pos);
    const rawBuyerState = can.buyer_state || (!isAP ? (partyGstin && partyGstin.length >= 2 ? partyGstin.slice(0, 2) : pos) : pos);
    const supplierState = normalizeStateName(rawSupplierState);
    const buyerState = normalizeStateName(rawBuyerState);
    const partyState = isAP ? supplierState : buyerState;

    // Transaction Type (B2B vs B2C)
    const rawType = (can.invoice_type || 'B2B').toUpperCase();
    const isB2CL = rawType === 'B2CL' || (rawType === 'B2C' && Number(invoiceTotal) > 250000 && supplierState !== pos);
    const txnTypeDisplay = isB2CL ? 'B2C (Large)' : (rawType.startsWith('B2C') ? 'B2C' : (rawType === 'EXPORT' ? 'Export' : (rawType === 'SEZ' ? 'SEZ' : 'B2B')));
    const supplyTypeDisplay = (supplierState === pos ? 'Intra-State Supply' : 'Inter-State Supply');

    // Overall Status
    const appr = this.approval;
    let statusLabel = 'BLOCKED';
    let statusBadgeClass = 'non-compliant';
    let statusIcon = '🔴';

    if (appr && appr.status === 'APPROVED' && !appr.invalidated) {
      statusLabel = 'APPROVED';
      statusBadgeClass = 'compliant';
      statusIcon = '🟢';
    } else if (dec.status === 'COMPLIANT') {
      statusLabel = 'APPROVED';
      statusBadgeClass = 'compliant';
      statusIcon = '🟢';
    } else if (dec.status === 'NEEDS_REVIEW') {
      statusLabel = 'NEEDS REVIEW';
      statusBadgeClass = 'needs-review';
      statusIcon = '🟠';
    }

    // Gate Lookup Map
    const gateMap = {};
    gates.forEach(g => {
      const gNum = g.gate_no || (g.metadata && g.metadata.gate_no);
      if (gNum) gateMap[gNum] = g;
    });

    const g1 = gateMap[1] || { status: 'PASS', name: 'GSTIN Format', message: 'GSTIN format and active status verified.' };
    const g2 = gateMap[2] || { status: 'PASS', name: 'HSN/SAC Validation', message: 'HSN/SAC classification verified against master.' };
    const g3 = gateMap[3] || { status: 'PASS', name: 'Tax Rate & Calculation', message: 'Tax rates and mathematical amounts verified.' };
    const g4 = gateMap[4] || { status: 'PASS', name: 'Place of Supply & Jurisdiction', message: 'Place of supply and tax heads verified.' };
    const g5 = gateMap[5] || { status: 'PASS', name: 'E-Way Bill Compliance', message: 'E-Way bill statutory threshold verified.' };
    const g6 = gateMap[6] || { status: 'NOT_APPLICABLE', name: 'ITC Eligibility', message: 'ITC conditions verified.' };

    // Unified Tax Check (combining G3 & G4 for clean business UX)
    const taxCheckFailed = g3.status === 'FAIL' || g4.status === 'FAIL';
    const taxCheckReview = !taxCheckFailed && (g3.status === 'NEEDS_REVIEW' || g4.status === 'NEEDS_REVIEW');
    const taxCheckStatus = taxCheckFailed ? 'FAIL' : (taxCheckReview ? 'NEEDS_REVIEW' : 'PASS');
    const taxCheckMessage = (g4.status === 'FAIL' || g4.status === 'NEEDS_REVIEW') ? g4.message : g3.message;

    // Actual Issues Identification
    const activeIssues = [];
    if (taxCheckStatus === 'FAIL' || taxCheckStatus === 'NEEDS_REVIEW') {
      activeIssues.push({
        type: 'Tax Treatment',
        severity: taxCheckStatus === 'FAIL' ? 'critical' : 'warning',
        icon: taxCheckStatus === 'FAIL' ? '🔴' : '🟠',
        title: 'Tax Treatment Mismatch',
        desc: taxCheckMessage || 'Applied tax components or rates do not match statutory requirements.',
        actionField: 'cgst_rate',
        actionLabel: 'Fix Tax Treatment'
      });
    }
    if (g2.status === 'FAIL' || g2.status === 'NEEDS_REVIEW') {
      activeIssues.push({
        type: 'HSN/SAC',
        severity: g2.status === 'FAIL' ? 'critical' : 'warning',
        icon: g2.status === 'FAIL' ? '🔴' : '🟠',
        title: 'HSN/SAC Requirement Issue',
        desc: g2.message || 'Required HSN/SAC code is missing, invalid, or does not meet digit requirements.',
        actionField: 'hsn_sac',
        actionLabel: 'Fix HSN/SAC'
      });
    }
    if (g1.status === 'FAIL' || g1.status === 'NEEDS_REVIEW') {
      activeIssues.push({
        type: 'GSTIN',
        severity: g1.status === 'FAIL' ? 'critical' : 'warning',
        icon: g1.status === 'FAIL' ? '🔴' : '🟠',
        title: 'GSTIN Verification Issue',
        desc: g1.message || 'Customer/Vendor GSTIN format or checksum is invalid.',
        actionField: 'gstin',
        actionLabel: 'Fix GSTIN'
      });
    }
    if (g4.status === 'FAIL' || g4.status === 'NEEDS_REVIEW') {
      if (!activeIssues.some(i => i.type === 'Tax Treatment')) {
        activeIssues.push({
          type: 'Place of Supply',
          severity: g4.status === 'FAIL' ? 'critical' : 'warning',
          icon: g4.status === 'FAIL' ? '🔴' : '🟠',
          title: 'Place of Supply Mismatch',
          desc: g4.message || 'Place of supply requires verification against supplier jurisdiction.',
          actionField: 'place_of_supply',
          actionLabel: 'Fix Place of Supply'
        });
      }
    }
    if (g5.status === 'FAIL') {
      activeIssues.push({
        type: 'E-Way Bill',
        severity: 'critical',
        icon: '🔴',
        title: 'E-Way Bill Missing',
        desc: g5.message || 'Consignment value exceeds statutory threshold but E-Way Bill is not generated.',
        actionField: 'taxable_value',
        actionLabel: 'Review Value'
      });
    }

    // HSN Status determination
    const hsnCode = can.hsn_sac || dec.hsn_code || '';
    let hsnStatusBadge = '<span style="color:#059669; font-weight:700;">HSN/SAC &check; Valid</span>';
    if (!hsnCode) {
      if (rawType.startsWith('B2C')) {
        hsnStatusBadge = '<span style="color:#64748B;">HSN/SAC &mdash; Optional</span>';
      } else {
        hsnStatusBadge = '<span style="color:#DC2626; font-weight:700;">HSN/SAC &mdash; Required</span>';
      }
    } else if (g2.status === 'FAIL' || g2.status === 'NEEDS_REVIEW') {
      hsnStatusBadge = '<span style="color:#D97706; font-weight:700;">HSN/SAC &mdash; Needs Review</span>';
    }

    // Helper for Gate Status display
    const renderGateStatusTag = (status) => {
      if (status === 'PASS') return '<span style="color:#059669; font-weight:700;">&check; Passed</span>';
      if (status === 'FAIL') return '<span style="color:#DC2626; font-weight:700;">&cross; Failed</span>';
      if (status === 'NEEDS_REVIEW' || status === 'REVIEW') return '<span style="color:#D97706; font-weight:700;">&warning; Needs Review</span>';
      return '<span style="color:#64748B;">&mdash; Not Applicable</span>';
    };

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:20px;">

        <!-- =================================================================== -->
        <!-- SECTION A: INVOICE SUMMARY                                          -->
        <!-- =================================================================== -->
        <div class="panel" style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(15,23,42,0.05);">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:12px;">
                <h2 style="font-size:22px; font-weight:800; color:#0F172A; font-family:var(--font-mono); margin:0;">
                  Invoice #${dec.invoice_no || can.invoice_number || this.currentInvoiceId}
                </h2>
                <span class="badge-status ${statusBadgeClass}" style="padding:4px 12px; font-size:12px; font-weight:800; border-radius:20px;">
                  ${statusIcon} ${statusLabel}
                </span>
              </div>
              <div style="font-size:15px; font-weight:700; color:#1E293B; margin-top:8px;">
                ${partyRole}: <span style="color:#2563EB;">${partyName}</span>
              </div>
              <div style="font-size:12.5px; color:#64748B; margin-top:4px;">
                GSTIN: <strong style="font-family:var(--font-mono); color:#334155;">${partyGstin}</strong> &middot; State: <strong style="color:#334155;">${partyState}</strong>
              </div>
              <div style="font-size:12px; color:#64748B; margin-top:6px; display:flex; gap:12px; flex-wrap:wrap;">
                <span>Transaction: <strong style="color:#0F172A;">${txnTypeDisplay}</strong></span>
                <span>&bull;</span>
                <span>Supply: <strong style="color:#0F172A;">${supplyTypeDisplay}</strong></span>
                <span>&bull;</span>
                <span>Place of Supply: <strong style="color:#0F172A;">${pos}</strong></span>
                <span>&bull;</span>
                <span>Date: <strong style="color:#0F172A; font-family:var(--font-mono);">${dec.invoice_date || can.invoice_date || '—'}</strong></span>
              </div>
            </div>

            <!-- Financial KPIs -->
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px 20px; display:flex; gap:24px; align-items:center;">
              <div>
                <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Taxable Value</div>
                <div style="font-size:18px; font-weight:800; color:#0F172A; font-family:var(--font-mono); margin-top:2px;">${formatINR(taxableVal)}</div>
              </div>
              <div style="width:1px; height:32px; background:#E2E8F0;"></div>
              <div>
                <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Total GST</div>
                <div style="font-size:18px; font-weight:800; color:#2563EB; font-family:var(--font-mono); margin-top:2px;">${formatINR(totalTax)}</div>
              </div>
              <div style="width:1px; height:32px; background:#E2E8F0;"></div>
              <div>
                <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Invoice Total</div>
                <div style="font-size:20px; font-weight:800; color:#059669; font-family:var(--font-mono); margin-top:2px;">${formatINR(invoiceTotal)}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SECTION B: COMPLIANCE CHECKS                                        -->
        <!-- =================================================================== -->
        <div class="panel" style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid #F1F5F9; padding-bottom:8px;">
            <h3 style="font-size:15px; font-weight:800; color:#0F172A; margin:0;">Compliance Checks</h3>
            <span style="font-size:11.5px; color:#64748B;">Click any check to inspect explanation and required action</span>
          </div>

          <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
            <thead>
              <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569; text-align:left;">
                <th style="padding:10px 14px; font-weight:700;">Check</th>
                <th style="padding:10px 14px; font-weight:700;">Status</th>
                <th style="padding:10px 14px; font-weight:700;">Summary</th>
                <th style="padding:10px 14px; font-weight:700; text-align:right;">Action</th>
              </tr>
            </thead>
            <tbody>
              <!-- GSTIN Check -->
              <tr style="border-bottom:1px solid #F1F5F9; cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('gstin')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">GSTIN</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(g1.status)}</td>
                <td style="padding:12px 14px; color:#475569;">${g1.message || 'GSTIN verified'}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['gstin'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['gstin'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> ${g1.observed_value || g1.actual_value || 'GSTIN present'}</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> ${g1.expected_value || 'Valid 15-character registered GSTIN'}</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> ${g1.message || 'Statutory requirement under Section 22/24 CGST Act'}</div>
                      ${g1.status === 'FAIL' ? `<button onclick="window.invoiceDetailView.focusCorrectionField('gstin')" class="btn btn-outline" style="margin-top:8px; font-size:11px;">Fix GSTIN</button>` : ''}
                    </div>
                  </td>
                </tr>
              ` : ''}

              <!-- HSN/SAC Check -->
              <tr style="border-bottom:1px solid #F1F5F9; cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('hsn')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">HSN/SAC</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(g2.status)}</td>
                <td style="padding:12px 14px; color:#475569;">${g2.message || 'HSN classification verified'}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['hsn'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['hsn'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> HSN Code '${hsnCode || 'Missing'}' on line items</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> ${g2.expected_value || 'Mandatory 4 to 8 digit HSN code'}</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> ${g2.message || 'Notification No. 78/2020-Central Tax requires HSN based on turnover'}</div>
                      ${(g2.status === 'FAIL' || g2.status === 'NEEDS_REVIEW') ? `<button onclick="window.invoiceDetailView.focusCorrectionField('hsn_sac')" class="btn btn-outline" style="margin-top:8px; font-size:11px;">Fix HSN/SAC</button>` : ''}
                    </div>
                  </td>
                </tr>
              ` : ''}

              <!-- Tax Treatment Check (G3 & G4) -->
              <tr style="border-bottom:1px solid #F1F5F9; cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('tax')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">Tax</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(taxCheckStatus)}</td>
                <td style="padding:12px 14px; color:#475569;">${taxCheckMessage || 'Tax heads and calculations verified'}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['tax'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['tax'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> ${taxCheckMessage || 'Tax applied on transaction'}</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> ${supplierState === pos ? 'CGST + SGST (Intra-state)' : 'IGST (Inter-state)'}</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> Supplier state is ${supplierState} and Place of Supply is ${pos}.</div>
                      ${taxCheckStatus !== 'PASS' ? `<button onclick="window.invoiceDetailView.focusCorrectionField('cgst_rate')" class="btn btn-outline" style="margin-top:8px; font-size:11px;">Fix Tax Treatment</button>` : ''}
                    </div>
                  </td>
                </tr>
              ` : ''}

              <!-- Place of Supply Check -->
              <tr style="border-bottom:1px solid #F1F5F9; cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('pos')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">Place of Supply</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(g4.status)}</td>
                <td style="padding:12px 14px; color:#475569;">${g4.message || `Place of supply: ${pos}`}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['pos'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['pos'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> Declared Place of Supply is '${pos}'</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> Valid Place of Supply matching buyer registration or destination state</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> Governed by Section 10/12 of IGST Act</div>
                      ${g4.status !== 'PASS' ? `<button onclick="window.invoiceDetailView.focusCorrectionField('place_of_supply')" class="btn btn-outline" style="margin-top:8px; font-size:11px;">Fix Place of Supply</button>` : ''}
                    </div>
                  </td>
                </tr>
              ` : ''}

              <!-- E-Way Bill Check -->
              <tr style="border-bottom:1px solid #F1F5F9; cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('ewb')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">E-Way Bill</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(g5.status)}</td>
                <td style="padding:12px 14px; color:#475569;">${g5.message || (Number(invoiceTotal) >= 50000 ? 'Consignment exceeds threshold' : 'Not required (threshold not reached)')}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['ewb'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['ewb'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> Invoice value ${formatINR(invoiceTotal)}</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> E-Way Bill mandatory for goods movement exceeding INR 50,000</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> Rule 138 of CGST Rules</div>
                    </div>
                  </td>
                </tr>
              ` : ''}

              <!-- ITC Eligibility Check -->
              <tr style="cursor:pointer;" onclick="window.invoiceDetailView.toggleGateDetail('itc')">
                <td style="padding:12px 14px; font-weight:700; color:#0F172A;">ITC</td>
                <td style="padding:12px 14px;">${renderGateStatusTag(g6.status)}</td>
                <td style="padding:12px 14px; color:#475569;">${g6.message || (isAP ? 'Eligible for Input Tax Credit' : 'Not Applicable (Outward Supply)')}</td>
                <td style="padding:12px 14px; text-align:right; color:#2563EB; font-weight:600;">
                  ${this.expandedGates['itc'] ? 'Hide &and;' : 'Details &or;'}
                </td>
              </tr>
              ${this.expandedGates['itc'] ? `
                <tr style="background:#F8FAFC;">
                  <td colspan="4" style="padding:14px 18px;">
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; font-size:12px;">
                      <div><strong>What happened:</strong> ${isAP ? 'Inward supply evaluated for ITC' : 'Outward supply transaction'}</div>
                      <div style="margin-top:4px;"><strong>What is expected:</strong> Compliance with Section 16 & 17(5) CGST Act</div>
                      <div style="margin-top:4px;"><strong>Why:</strong> Recipient credit claims require valid tax invoice and GSTR-2B reflection</div>
                    </div>
                  </td>
                </tr>
              ` : ''}
            </tbody>
          </table>
        </div>

        <!-- =================================================================== -->
        <!-- SECTION C: ISSUES & INLINE CORRECTIONS                              -->
        <!-- =================================================================== -->
        <div class="panel" style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid #F1F5F9; padding-bottom:8px;">
            <h3 style="font-size:15px; font-weight:800; color:#0F172A; margin:0;">Issues Found</h3>
            <span style="font-size:11.5px; color:#64748B;">Fix issues inline and click Re-check to update status</span>
          </div>

          ${activeIssues.length === 0 ? `
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:14px; display:flex; align-items:center; gap:10px; color:#065F46; font-size:13px;">
              <span style="font-size:18px;">&check;</span>
              <div><strong>No compliance issues found.</strong> All statutory checks passed verification.</div>
            </div>
          ` : `
            <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
              ${activeIssues.map(iss => `
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; gap:12px;">
                  <div>
                    <div style="font-size:13px; font-weight:700; color:#92400E;">
                      ${iss.icon} ${iss.title}
                    </div>
                    <div style="font-size:12px; color:#78350F; margin-top:2px;">
                      ${iss.desc}
                    </div>
                  </div>
                  <button onclick="window.invoiceDetailView.focusCorrectionField('${iss.actionField}')" class="btn btn-primary" style="padding:6px 14px; font-size:11.5px; font-weight:700; background:#D97706; border-color:#D97706; color:#fff; border-radius:6px; cursor:pointer;">
                    ${iss.actionLabel}
                  </button>
                </div>
              `).join('')}
            </div>
          `}

          <!-- Inline Edit Form -->
          <div id="inline_correction_box" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px; margin-top:16px;">
            <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:12px;">Inline Correction Form</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">HSN / SAC Code</label>
                <input type="text" id="corr_hsn_sac" value="${hsnCode}" style="width:100%; padding:7px 10px; font-size:12px; font-family:var(--font-mono); border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">Place of Supply</label>
                <select id="corr_place_of_supply" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
                  ${renderStateOptions(pos)}
                </select>
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">${partyRole} GSTIN</label>
                <input type="text" id="corr_gstin" value="${partyGstin}" style="width:100%; padding:7px 10px; font-size:12px; font-family:var(--font-mono); border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">Transaction Type</label>
                <select id="corr_invoice_type" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
                  <option value="B2B" ${rawType === 'B2B' ? 'selected' : ''}>B2B</option>
                  <option value="B2C" ${rawType === 'B2C' ? 'selected' : ''}>B2C</option>
                  <option value="EXPORT" ${rawType === 'EXPORT' ? 'selected' : ''}>EXPORT</option>
                  <option value="SEZ" ${rawType === 'SEZ' ? 'selected' : ''}>SEZ</option>
                </select>
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">Taxable Value (₹)</label>
                <input type="number" step="0.01" id="corr_taxable_value" value="${taxableVal}" style="width:100%; padding:7px 10px; font-size:12px; font-family:var(--font-mono); border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">CGST Rate (%)</label>
                <input type="number" step="0.01" id="corr_cgst_rate" value="${can.cgst_rate !== undefined ? can.cgst_rate : 0}" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">SGST Rate (%)</label>
                <input type="number" step="0.01" id="corr_sgst_rate" value="${can.sgst_rate !== undefined ? can.sgst_rate : 0}" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">UTGST Rate (%)</label>
                <input type="number" step="0.01" id="corr_utgst_rate" value="${can.utgst_rate !== undefined ? can.utgst_rate : 0}" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">IGST Rate (%)</label>
                <input type="number" step="0.01" id="corr_igst_rate" value="${can.igst_rate !== undefined ? can.igst_rate : 0}" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
              </div>
            </div>

            <div style="margin-top:12px;">
              <label style="display:block; font-size:11px; font-weight:700; color:#475569; margin-bottom:4px;">Reason for Change</label>
              <input type="text" id="corr_reason" placeholder="e.g. Switched to CGST+SGST for intra-state supply, updated HSN to 6 digits" style="width:100%; padding:7px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
            </div>

            <div style="margin-top:14px; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
              <button onclick="window.invoiceDetailView.applyCorrections()" class="btn btn-primary" style="padding:8px 18px; font-size:12.5px; font-weight:700; background:#2563EB; border-color:#2563EB; color:#fff; border-radius:6px; cursor:pointer;">
                Save &amp; Apply Changes
              </button>
              <button onclick="window.invoiceDetailView.recheckCompliance()" class="btn btn-outline" style="padding:8px 18px; font-size:12.5px; font-weight:700; border:1px solid #2563EB; color:#2563EB; background:#EFF6FF; border-radius:6px; cursor:pointer;">
                Re-check Invoice
              </button>
              <div id="corr_feedback" style="font-size:12px; margin-left:6px;"></div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SECTION D: TAX & HSN/SAC DETAILS                                    -->
        <!-- =================================================================== -->
        <div class="panel" style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px;">
          <h3 style="font-size:15px; font-weight:800; color:#0F172A; margin:0 0 14px 0; border-bottom:1px solid #F1F5F9; padding-bottom:8px;">
            Tax Details &amp; Items
          </h3>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
            <!-- Applied Tax Table -->
            <div>
              <div style="font-size:12.5px; font-weight:700; color:#475569; margin-bottom:8px; text-transform:uppercase;">Applied Tax</div>
              <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                  <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569;">
                    <th style="padding:8px; text-align:left;">Tax Head</th>
                    <th style="padding:8px; text-align:right;">Rate</th>
                    <th style="padding:8px; text-align:right;">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:8px;">CGST</td>
                    <td style="padding:8px; text-align:right;">${can.cgst_rate !== undefined ? can.cgst_rate : 0}%</td>
                    <td style="padding:8px; text-align:right; font-family:var(--font-mono);">${formatINR(cgstAmt)}</td>
                  </tr>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:8px;">SGST</td>
                    <td style="padding:8px; text-align:right;">${can.sgst_rate !== undefined ? can.sgst_rate : 0}%</td>
                    <td style="padding:8px; text-align:right; font-family:var(--font-mono);">${formatINR(sgstAmt)}</td>
                  </tr>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:8px;">UTGST</td>
                    <td style="padding:8px; text-align:right;">${can.utgst_rate ? can.utgst_rate + '%' : '&mdash;'}</td>
                    <td style="padding:8px; text-align:right; font-family:var(--font-mono);">${utgstAmt ? formatINR(utgstAmt) : '&mdash;'}</td>
                  </tr>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:8px;">IGST</td>
                    <td style="padding:8px; text-align:right;">${can.igst_rate ? can.igst_rate + '%' : '&mdash;'}</td>
                    <td style="padding:8px; text-align:right; font-family:var(--font-mono);">${igstAmt ? formatINR(igstAmt) : '&mdash;'}</td>
                  </tr>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:8px;">Cess</td>
                    <td style="padding:8px; text-align:right;">${can.cess_rate ? can.cess_rate + '%' : '&mdash;'}</td>
                    <td style="padding:8px; text-align:right; font-family:var(--font-mono);">${cessAmt ? formatINR(cessAmt) : '&mdash;'}</td>
                  </tr>
                  <tr style="background:#F8FAFC; font-weight:800;">
                    <td style="padding:10px 8px; color:#0F172A;">Total GST</td>
                    <td style="padding:10px 8px;"></td>
                    <td style="padding:10px 8px; text-align:right; font-family:var(--font-mono); color:#2563EB;">${formatINR(totalTax)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Item & HSN Table -->
            <div>
              <div style="font-size:12.5px; font-weight:700; color:#475569; margin-bottom:8px; text-transform:uppercase;">HSN / Item Breakdown</div>
              <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                  <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569;">
                    <th style="padding:8px; text-align:left;">Item</th>
                    <th style="padding:8px; text-align:left;">HSN/SAC</th>
                    <th style="padding:8px; text-align:right;">Taxable</th>
                    <th style="padding:8px; text-align:right;">GST Rate</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style="border-bottom:1px solid #F1F5F9;">
                    <td style="padding:10px 8px; font-weight:600; color:#0F172A;">${can.item_desc || dec.item_desc || 'Primary Commodity / Service'}</td>
                    <td style="padding:10px 8px; font-family:var(--font-mono);">${hsnCode || 'Missing'}</td>
                    <td style="padding:10px 8px; text-align:right; font-family:var(--font-mono);">${formatINR(taxableVal)}</td>
                    <td style="padding:10px 8px; text-align:right;">${can.effective_tax_rate || 18}%</td>
                  </tr>
                </tbody>
              </table>

              <div style="margin-top:14px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <span style="font-size:11px; color:#64748B; text-transform:uppercase; font-weight:700;">HSN Verification Status</span>
                  <div style="font-size:13px; margin-top:2px;">${hsnStatusBadge}</div>
                </div>
                <button onclick="window.invoiceDetailView.focusCorrectionField('hsn_sac')" class="btn btn-outline" style="font-size:11px; padding:4px 10px;">
                  Edit HSN/SAC
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SECTION E: APPROVAL & AUDIT                                         -->
        <!-- =================================================================== -->
        <div class="panel" style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; border-bottom:1px solid #F1F5F9; padding-bottom:8px;">
            <h3 style="font-size:15px; font-weight:800; color:#0F172A; margin:0;">Approval &amp; Audit</h3>
            <button onclick="window.invoiceDetailView.toggleAuditHistory()" style="background:none; border:none; color:#2563EB; font-size:12px; font-weight:600; cursor:pointer; text-decoration:underline;">
              ${this.showAuditHistory ? 'Hide Audit History' : 'View Audit History (' + (this.corrections.length + (appr ? 1 : 0)) + ' records)'}
            </button>
          </div>

          <!-- Approval Status Box -->
          ${appr && appr.invalidated ? `
            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:14px; margin-bottom:14px; color:#92400E; font-size:12.5px;">
              <strong>⚠️ Approval Invalidated:</strong> Invoice data was updated after previous approval on ${new Date(appr.approved_at).toLocaleString()}. Please re-check and submit approval again.
            </div>
          ` : ''}

          ${appr && appr.status === 'APPROVED' && !appr.invalidated ? `
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:18px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="color:#065F46; font-weight:800; font-size:15px; display:flex; align-items:center; gap:8px;">
                    <span>🟢</span> APPROVED
                  </div>
                  <div style="color:#047857; font-size:12.5px; margin-top:4px;">
                    Approved by: <strong>${appr.approved_by}</strong> on ${new Date(appr.approved_at).toLocaleString()}
                  </div>
                  <div style="color:#065F46; font-size:12px; margin-top:8px; background:#FFFFFF; padding:8px 12px; border-radius:6px; border:1px solid #D1FAE5;">
                    <strong>Review Note:</strong> "${appr.comment}"
                  </div>
                </div>
                <button onclick="window.invoiceDetailView.submitApproval('REJECT')" class="btn btn-outline" style="color:#DC2626; border-color:#DC2626; font-size:12px;">
                  Revoke / Reject
                </button>
              </div>
            </div>
          ` : (statusLabel === 'BLOCKED' ? `
            <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:10px; padding:18px;">
              <div style="color:#991B1B; font-weight:800; font-size:15px; display:flex; align-items:center; gap:8px;">
                <span>🔴</span> Invoice cannot be approved
              </div>
              <div style="color:#7F1D1D; font-size:12.5px; margin-top:4px;">
                Resolve blocking issues first. Use the inline correction form above, then click Re-check Invoice.
              </div>
            </div>
          ` : `
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:18px;">
              <div style="color:#065F46; font-weight:800; font-size:15px; display:flex; align-items:center; gap:8px;">
                <span>🟢</span> ${statusLabel === 'APPROVED' ? 'APPROVED' : 'READY FOR REVIEW'}
              </div>
              <div style="color:#047857; font-size:12.5px; margin-top:4px;">
                All applicable compliance checks passed. Ready for authorized sign-off.
              </div>

              <div style="margin-top:14px; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <input type="text" id="appr_actor" value="FINANCE_LEAD" style="width:160px; padding:8px 10px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
                <input type="text" id="appr_comment" placeholder="Enter statutory sign-off justification (required)..." style="flex:1; min-width:260px; padding:8px 12px; font-size:12px; border:1px solid #CBD5E1; border-radius:6px; background:#FFFFFF;">
                <button onclick="window.invoiceDetailView.submitApproval('APPROVE')" class="btn btn-primary" style="background:#059669; border-color:#059669; color:#fff; font-weight:700; padding:8px 22px; font-size:12.5px; border-radius:6px; cursor:pointer;">
                  APPROVE INVOICE
                </button>
                <button onclick="window.invoiceDetailView.submitApproval('REJECT')" class="btn btn-outline" style="color:#DC2626; border-color:#DC2626; padding:8px 14px; font-size:12px; border-radius:6px;">
                  Reject
                </button>
              </div>
              <div id="appr_feedback" style="margin-top:6px; font-size:12px;"></div>
            </div>
          `)}

          <!-- Expandable Audit History -->
          ${this.showAuditHistory ? `
            <div style="margin-top:16px; border-top:1px solid #F1F5F9; padding-top:16px;">
              <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:10px;">
                Audit Trail &amp; Version History
              </div>
              ${this.corrections.length === 0 ? `
                <div style="font-size:12px; color:#64748B;">No field-level corrections recorded for this invoice.</div>
              ` : `
                <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:12px;">
                  ${this.corrections.slice().reverse().map(c => `
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px; font-size:12px;">
                      <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-weight:700; color:#0F172A;">Modified by ${c.corrected_by || 'User'}</span>
                        <span style="color:#64748B; font-family:var(--font-mono);">${new Date(c.timestamp).toLocaleString()}</span>
                      </div>
                      <div style="color:#475569;"><strong>Reason:</strong> ${c.reason || 'None specified'}</div>
                      <div style="margin-top:4px;">
                        ${Object.entries(c.changes || {}).map(([f, v]) => `
                          <span style="display:inline-block; margin-right:8px; font-size:11px;"><code>${f}</code>: <span style="text-decoration:line-through; color:#DC2626;">${v.old}</span> &rarr; <span style="color:#059669; font-weight:700;">${v.new}</span></span>
                        `).join('')}
                      </div>
                    </div>
                  `).join('')}
                </div>
              `}
              <div style="font-size:11.5px; color:#64748B; display:flex; gap:16px; margin-top:8px;">
                <span>Statutory Engine: <strong>v2.4.0 (Unified Six-Gate Rules)</strong></span>
                <span>Audit Trail Ref: <strong style="font-family:var(--font-mono);">${dec.audit_trail_ref || 'TR-2026-AUDIT'}</strong></span>
                <span>SAP Flag: <strong>${dec.sap_action || 'POST_APPROVED'}</strong></span>
              </div>
            </div>
          ` : ''}
        </div>

      </div>
    `;

    window.invoiceDetailView = this;
  }

  // Interactive Actions
  async applyCorrections() {
    const feedback = document.getElementById('corr_feedback');
    const invoiceId = this.currentInvoiceId;
    if (!invoiceId) return;

    const fields = ['hsn_sac', 'place_of_supply', 'gstin', 'invoice_type', 'taxable_value', 'cgst_rate', 'sgst_rate', 'utgst_rate', 'igst_rate', 'cess_rate'];
    const corrections = {};

    fields.forEach(f => {
      const el = document.getElementById(`corr_${f}`);
      if (el && el.value !== undefined && el.value !== '') {
        corrections[f] = el.value.trim();
      }
    });

    const reasonEl = document.getElementById('corr_reason');
    const reason = reasonEl ? reasonEl.value.trim() : 'Inline correction via workspace';

    try {
      if (feedback) feedback.innerHTML = '<span style="color:#2563EB;">Saving changes...</span>';
      const res = await window.gstApi.correctInvoice(invoiceId, corrections, reason);
      if (feedback) {
        feedback.innerHTML = `<span style="color:#059669; font-weight:600;">&check; ${res.message || 'Changes saved!'} Now click "Re-check Invoice".</span>`;
      }
      await this.loadDossier(invoiceId);
    } catch (err) {
      if (feedback) {
        feedback.innerHTML = `<span style="color:#DC2626; font-weight:600;">&cross; Failed: ${err.message}</span>`;
      }
    }
  }

  async recheckCompliance() {
    const feedback = document.getElementById('corr_feedback');
    const invoiceId = this.currentInvoiceId;
    if (!invoiceId) return;

    try {
      if (feedback) feedback.innerHTML = '<span style="color:#2563EB;">Re-running compliance engine...</span>';
      const res = await window.gstApi.recheckInvoice(invoiceId);
      if (feedback) {
        const badge = res.current_status === 'COMPLIANT' ? 'COMPLIANT (All gates passed)' : `${res.current_status} (${res.current_failed_gates} gate(s) failed)`;
        feedback.innerHTML = `<span style="color:#059669; font-weight:600;">&check; Result: ${badge}</span>`;
      }
      await this.loadDossier(invoiceId);
    } catch (err) {
      if (feedback) {
        feedback.innerHTML = `<span style="color:#DC2626; font-weight:600;">&cross; Re-check failed: ${err.message}</span>`;
      }
    }
  }

  async submitApproval(action) {
    const feedback = document.getElementById('appr_feedback');
    const invoiceId = this.currentInvoiceId;
    if (!invoiceId) return;

    const commentEl = document.getElementById('appr_comment');
    const actorEl = document.getElementById('appr_actor');
    const comment = commentEl ? commentEl.value.trim() : '';
    const actor = actorEl ? actorEl.value.trim() : 'FINANCE_LEAD';

    if (action === 'APPROVE' && (!comment || comment.length < 5)) {
      if (feedback) {
        feedback.innerHTML = '<span style="color:#DC2626; font-weight:600;">Please enter an approval comment (at least 5 characters).</span>';
      }
      return;
    }

    try {
      if (feedback) feedback.innerHTML = '<span style="color:#2563EB;">Recording decision...</span>';
      const res = await window.gstApi.approveInvoice(invoiceId, action, comment || 'Action performed via workspace', actor);
      if (feedback) {
        feedback.innerHTML = `<span style="color:#059669; font-weight:600;">&check; Invoice ${res.approval_status} recorded successfully!</span>`;
      }
      await this.loadDossier(invoiceId);
    } catch (err) {
      if (feedback) {
        feedback.innerHTML = `<span style="color:#DC2626; font-weight:600;">&cross; Decision failed: ${err.message}</span>`;
      }
    }
  }
}

window.InvoiceDetailView = InvoiceDetailView;
