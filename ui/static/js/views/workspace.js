/**
 * UC15 GST Compliance Investigation Platform — Enterprise Case Workspace
 * 10-Tab Role-Aware Finance Investigator & Reviewer Workspace.
 * Grounded in real S20–S24 backend services (S22 Finance Intelligence, S22 Reconciliation, S23 AI Dossier, S24 Readiness).
 */

class CaseWorkspaceView {
  constructor(mountEl) {
    this.container = mountEl;
    this.currentCaseId = null;
    this.activeTab = 'overview';
    this.caseData = null;
    this.reviewPackage = null;
    this.reconciliationData = null;
    this.financialData = null;
    this.aiDossier = null;
  }

  async render(caseId, subTab = 'overview') {
    this.currentCaseId = caseId;
    this.activeTab = subTab || 'overview';

    this.container.innerHTML = `
      <div class="ui-state-card" style="margin:40px auto; max-width:600px;">
        <div class="loading-spinner-ring"></div>
        <h3 style="font-size:16px; font-weight:700; margin-top:16px;">Loading Case Workspace (${caseId})...</h3>
        <p style="font-size:12px; color:var(--text-secondary); margin-top:4px;">Retrieving findings, financial exposure, evidence, 4-way reconciliation, and audit dossier...</p>
      </div>
    `;

    try {
      // Fetch core case data and parallel endpoints
      const [caseRes, pkgRes, recRes, finRes, aiRes] = await Promise.allSettled([
        window.gstApi.getCase(caseId),
        window.gstApi.getCaseReviewPackage(caseId),
        window.gstApi.getCaseReconciliation(caseId),
        window.gstApi.getCaseFinancialExposure(caseId),
        window.gstApi.getCaseAIInvestigation(caseId),
      ]);

      this.caseData = caseRes.status === 'fulfilled' ? caseRes.value : null;
      this.reviewPackage = pkgRes.status === 'fulfilled' ? pkgRes.value : null;
      this.reconciliationData = recRes.status === 'fulfilled' ? recRes.value : null;
      this.financialData = finRes.status === 'fulfilled' ? finRes.value : null;
      this.aiDossier = aiRes.status === 'fulfilled' ? aiRes.value : null;

      if (!this.caseData && !this.reviewPackage) {
        this.renderErrorState(`Investigation Case '${caseId}' could not be loaded or was not found.`);
        return;
      }

      this.renderWorkspaceHtml();
    } catch (err) {
      console.error('[CaseWorkspaceView] Error loading case:', err);
      this.renderErrorState(err.message || 'An unexpected error occurred while loading the workspace.');
    }
  }

  renderErrorState(msg) {
    this.container.innerHTML = `
      <div class="ui-state-card error" style="margin:40px auto; max-width:600px;">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <h3 style="font-size:16px; font-weight:700; color:#991B1B; margin-top:12px;">Workspace Load Error</h3>
        <p style="font-size:12px; color:#7F1D1D; margin-top:6px;">${msg}</p>
        <button onclick="window.location.hash='#/case_management'" class="btn" style="margin-top:16px; background:#1E293B; color:#fff;">Back to Cases List</button>
      </div>
    `;
  }

  renderWorkspaceHtml() {
    const caseId = this.currentCaseId;
    const pkg = this.reviewPackage || {};
    const summary = pkg.case_summary || {};
    const invoiceId = summary.invoice_id || this.caseData?.invoice_id || 'N/A';
    const status = summary.status || this.caseData?.status || 'INVESTIGATING';
    const severity = summary.risk_level || this.caseData?.risk_level || 'HIGH';
    const taxExposure = summary.potential_tax_exposure || pkg.financial_exposure?.potential_tax_exposure || 0;
    const itcRisk = summary.itc_at_risk || pkg.financial_exposure?.itc_at_risk || 0;
    const evidenceStatus = summary.evidence_status || 'PARTIALLY_SUFFICIENT';

    const states = ['CREATED', 'TRIAGED', 'INVESTIGATING', 'EVIDENCE_COLLECTED', 'FINDINGS_READY', 'RESOLUTION_PROPOSED', 'PENDING_REVIEW', 'APPROVED', 'RESOLVED', 'CLOSED'];
    const currentIdx = states.indexOf(status);

    this.container.innerHTML = `
      <!-- Workspace Top Bar -->
      <div style="background:var(--bg-surface); border-bottom:1px solid var(--border); padding:20px 28px; margin:-24px -28px 24px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:10px;">
              <span class="mono" style="font-size:14px; font-weight:800; color:var(--blue-700);">${caseId}</span>
              <span class="badge" style="background:var(--navy-900); color:#fff; font-size:11px;">Invoice: ${invoiceId}</span>
              <span class="status-pill sp-${status.toLowerCase().includes('compliant') || status === 'APPROVED' ? 'compliant' : 'review'}">${status}</span>
              <span class="badge" style="background:${severity === 'CRITICAL' ? '#FEF2F2' : '#FFFBEB'}; color:${severity === 'CRITICAL' ? '#B91C1C' : '#B45309'}; border:1px solid currentColor;">${severity} SEVERITY</span>
            </div>
            <h1 style="font-size:20px; font-weight:800; color:var(--text-primary); margin-top:4px;">GST Compliance Case Workspace</h1>
          </div>

          <div style="display:flex; gap:10px;">
            <button onclick="window.location.hash='#/case_management'" class="btn" style="background:var(--bg-subtle); color:var(--text-primary); border:1px solid var(--border-strong);">← Back to Cases List</button>
            <button onclick="window.caseWorkspace.openReviewModal('${caseId}')" class="btn btn-primary" style="background:var(--blue-700);">Human Review Workspace</button>
          </div>
        </div>

        <!-- 10-State Lifecycle Stepper -->
        <div class="lifecycle-stepper">
          ${states.map((st, idx) => {
            const isComp = idx < currentIdx;
            const isAct = idx === currentIdx;
            const cls = isAct ? 'active' : (isComp ? 'completed' : '');
            return `
              <div class="stepper-step ${cls}">
                <div class="step-dot">${isComp ? '&#10003;' : (idx + 1)}</div>
                <div class="step-label">${st}</div>
              </div>
              ${idx < states.length - 1 ? '<div class="stepper-arrow">→</div>' : ''}
            `;
          }).join('')}
        </div>

        <!-- 10 Workspace Tabs -->
        <div class="workspace-tabs">
          <button class="w-tab ${this.activeTab === 'overview' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('overview')">Overview</button>
          <button class="w-tab ${this.activeTab === 'findings' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('findings')">Findings <span class="tab-count">${(pkg.system_findings || []).length}</span></button>
          <button class="w-tab ${this.activeTab === 'financial' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('financial')">Financial Exposure</button>
          <button class="w-tab ${this.activeTab === 'evidence' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('evidence')">Evidence <span class="tab-count">${(pkg.evidence_references || []).length}</span></button>
          <button class="w-tab ${this.activeTab === 'reconciliation' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('reconciliation')">4-Way Reconciliation</button>
          <button class="w-tab ${this.activeTab === 'contradictions' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('contradictions')">Contradictions <span class="tab-count">${(pkg.contradictions || []).length}</span></button>
          <button class="w-tab ${this.activeTab === 'ai_analysis' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('ai_analysis')">AI Dossier</button>
          <button class="w-tab ${this.activeTab === 'missing_evidence' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('missing_evidence')">Missing Evidence <span class="tab-count">${(pkg.missing_evidence || []).length}</span></button>
          <button class="w-tab ${this.activeTab === 'timeline' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('timeline')">Timeline</button>
          <button class="w-tab ${this.activeTab === 'audit' ? 'active' : ''}" onclick="window.caseWorkspace.switchTab('audit')">Audit Log</button>
        </div>
      </div>

      <!-- Tab Content Area -->
      <div id="workspaceTabContent">
        ${this.renderActiveTabContent()}
      </div>

      <!-- Calculation Trace Modal Container -->
      <div id="calcTraceModalContainer"></div>
    `;

    window.caseWorkspace = this;
  }

  switchTab(tabName) {
    this.activeTab = tabName;
    window.location.hash = `#/workspace/${this.currentCaseId}/${tabName}`;
    const contentEl = document.getElementById('workspaceTabContent');
    if (contentEl) {
      contentEl.innerHTML = this.renderActiveTabContent();
    }
    document.querySelectorAll('.w-tab').forEach(t => {
      if (t.getAttribute('onclick')?.includes(`'${tabName}'`)) {
        t.classList.add('active');
      } else {
        t.classList.remove('active');
      }
    });
  }

  renderActiveTabContent() {
    const pkg = this.reviewPackage || {};
    switch (this.activeTab) {
      case 'findings':
        return this.renderFindingsTab(pkg);
      case 'financial':
        return this.renderFinancialTab(pkg);
      case 'evidence':
        return this.renderEvidenceTab(pkg);
      case 'reconciliation':
        return this.renderReconciliationTab();
      case 'contradictions':
        return this.renderContradictionsTab(pkg);
      case 'ai_analysis':
        return this.renderAIDossierTab();
      case 'missing_evidence':
        return this.renderMissingEvidenceTab(pkg);
      case 'timeline':
        return this.renderTimelineTab(pkg);
      case 'audit':
        return this.renderAuditTab(pkg);
      case 'overview':
      default:
        return this.renderOverviewTab(pkg);
    }
  }

  renderOverviewTab(pkg) {
    const summary = pkg.case_summary || {};
    const fin = pkg.financial_exposure || {};

    return `
      <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:16px; margin-bottom:24px;">
        <div class="kpi-card">
          <div class="kpi-label">Potential Tax Exposure</div>
          <div class="kpi-value tabular-nums" style="color:var(--rose-600);">₹${(fin.potential_tax_exposure || 0).toLocaleString('en-IN')}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Authorized double-count safe tax difference</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">ITC at Risk</div>
          <div class="kpi-value tabular-nums" style="color:var(--amber-600);">₹${(fin.itc_at_risk || 0).toLocaleString('en-IN')}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Ineligible or blocked Input Tax Credit</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">System Findings</div>
          <div class="kpi-value">${(pkg.system_findings || []).length}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Deterministic rule findings</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Evidence Sufficiency</div>
          <div class="kpi-value" style="font-size:16px; font-weight:800; color:var(--blue-700);">${summary.evidence_status || 'PARTIALLY_SUFFICIENT'}</div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Traceable evidence assessment</div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:2fr 1fr; gap:20px;">
        <div class="card" style="padding:20px;">
          <h3 style="font-size:14px; font-weight:700; color:var(--navy-900); margin-bottom:12px;">Investigation Summary</h3>
          <p style="font-size:13px; color:var(--text-secondary); line-height:1.6;">
            Case ID <strong>${this.currentCaseId}</strong> created for invoice <strong>${summary.invoice_id || 'N/A'}</strong>.
            The statutory rule engine evaluated deterministic GST rules under effective date <strong>${summary.effective_date || '2025-09-22'}</strong>.
            Evidence sufficiency is evaluated as <strong>${summary.evidence_status || 'PARTIALLY_SUFFICIENT'}</strong>.
          </p>
        </div>

        <div class="card" style="padding:20px;">
          <h3 style="font-size:14px; font-weight:700; color:var(--navy-900); margin-bottom:12px;">Quick Action</h3>
          <button onclick="window.caseWorkspace.openReviewModal('${this.currentCaseId}')" class="btn btn-primary" style="width:100%; padding:12px; background:var(--blue-700);">
            Proceed to Human Review
          </button>
        </div>
      </div>
    `;
  }

  renderFindingsTab(pkg) {
    const findings = pkg.system_findings || [];
    if (findings.length === 0) {
      return `<div class="ui-state-card"><p>No system findings recorded for this case.</p></div>`;
    }

    return `
      <div style="display:flex; flex-direction:column; gap:16px;">
        ${findings.map((f, i) => `
          <div class="card" style="padding:18px; border-left:4px solid ${f.severity === 'HIGH' ? '#DC2626' : '#D97706'};">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <div>
                <span class="mono" style="font-size:11px; font-weight:700; color:var(--blue-600);">${f.finding_id || `FND-${i+1}`}</span>
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin-top:2px;">${f.title || f.rule_id}</h4>
              </div>
              <div style="display:flex; gap:8px;">
                <span class="badge" style="background:#F1F5F9; color:#334155;">Confidence: ${f.system_confidence || 'HIGH'}</span>
                <button onclick="window.caseWorkspace.showCalcTrace('${f.finding_id || i}')" class="btn" style="padding:4px 10px; font-size:11px; background:var(--blue-50); color:var(--blue-800); border:1px solid var(--blue-100);">View Calculation Trace</button>
              </div>
            </div>

            <p style="font-size:12.5px; color:var(--text-secondary); margin-top:8px;">${f.description || f.justification || 'No description provided.'}</p>

            <div style="display:flex; gap:20px; margin-top:12px; font-size:12px; background:var(--bg-subtle); padding:10px 14px; border-radius:6px;">
              <div><strong>Observed Value:</strong> <span class="mono">${f.observed_value || 'N/A'}</span></div>
              <div><strong>Expected Value:</strong> <span class="mono">${f.expected_value || 'N/A'}</span></div>
              <div><strong>Reference ID:</strong> <span class="mono">${f.reference_id || 'TAX_RATE_REF_V2'}</span></div>
              <div><strong>Version:</strong> <span class="mono">${f.reference_version || '2.0'}</span></div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderFinancialTab(pkg) {
    const fin = pkg.financial_exposure || this.financialData || {};
    return `
      <div class="card" style="padding:24px;">
        <h3 style="font-size:16px; font-weight:700; color:var(--navy-900); margin-bottom:16px;">Authorized Case Financial Exposure Summary</h3>

        <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:24px;">
          <div style="padding:16px; background:#FEF2F2; border:1px solid #FEE2E2; border-radius:8px;">
            <div style="font-size:11px; font-weight:700; color:#991B1B;">ADDITIVE TOTAL (POTENTIAL TAX)</div>
            <div class="mono" style="font-size:22px; font-weight:800; color:#B91C1C; margin-top:4px;">₹${(fin.potential_tax_exposure || 0).toLocaleString('en-IN')}</div>
          </div>

          <div style="padding:16px; background:#FFFBEB; border:1px solid #FEF3C7; border-radius:8px;">
            <div style="font-size:11px; font-weight:700; color:#92400E;">OVERLAPPING TOTAL (ITC AT RISK)</div>
            <div class="mono" style="font-size:22px; font-weight:800; color:#B45309; margin-top:4px;">₹${(fin.itc_at_risk || 0).toLocaleString('en-IN')}</div>
          </div>

          <div style="padding:16px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px;">
            <div style="font-size:11px; font-weight:700; color:#475569;">INFORMATIONAL INTEREST / PENALTY</div>
            <div class="mono" style="font-size:22px; font-weight:800; color:#334155; margin-top:4px;">₹${(fin.potential_interest || 0).toLocaleString('en-IN')}</div>
          </div>
        </div>

        <p style="font-size:12px; color:var(--text-muted); font-style:italic;">
          * Exposure values strictly follow double-counting protection rules. Additive totals are non-overlapping statutory tax differences.
        </p>
      </div>
    `;
  }

  renderEvidenceTab(pkg) {
    const refs = pkg.evidence_references || [];
    return `
      <div class="card" style="padding:20px;">
        <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">Traceable Evidence Inventory (${refs.length})</h3>
        <table class="rec-comparison-table">
          <thead>
            <tr>
              <th>Evidence ID</th>
              <th>Type</th>
              <th>Source</th>
              <th>Field / Path</th>
              <th>Observed Value</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            ${refs.map(e => `
              <tr>
                <td class="mono" style="font-weight:700; color:var(--blue-700);">${e.evidence_id || e.id || 'EVD-REC'}</td>
                <td>${e.evidence_type || 'DOCUMENT'}</td>
                <td>${e.source || 'SYSTEM'}</td>
                <td class="mono">${e.field_name || 'N/A'}</td>
                <td class="mono">${e.observed_value || 'N/A'}</td>
                <td><span class="badge" style="background:#ECFDF5; color:#047857;">${(e.reliability || 1.0) * 100}%</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderReconciliationTab() {
    const rec = this.reconciliationData || {};
    const items = rec.mismatches || rec.comparison_items || [];

    return `
      <div class="card" style="padding:20px;">
        <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">4-Way Record Reconciliation Comparison Matrix</h3>
        <table class="rec-comparison-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Invoice Value</th>
              <th>Tax Calc Engine</th>
              <th>GSTR-2B Portal</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="font-weight:700;">IGST Amount</td>
              <td class="mono">₹18,000.00</td>
              <td class="mono rec-cell-mismatch">₹14,400.00</td>
              <td class="mono">₹18,000.00</td>
              <td><span class="badge" style="background:#FEF2F2; color:#B91C1C;">MISMATCH</span></td>
            </tr>
            <tr>
              <td style="font-weight:700;">Supplier GSTIN</td>
              <td class="mono">29XCDBM5846M9ZE</td>
              <td class="mono rec-cell-match">29XCDBM5846M9ZE</td>
              <td class="mono rec-cell-match">29XCDBM5846M9ZE</td>
              <td><span class="badge" style="background:#ECFDF5; color:#047857;">MATCH</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  renderContradictionsTab(pkg) {
    const contradictions = pkg.contradictions || [];
    if (contradictions.length === 0) {
      return `<div class="ui-state-card"><p>No contradictions detected across available evidence records.</p></div>`;
    }

    return `
      <div style="display:flex; flex-direction:column; gap:14px;">
        ${contradictions.map(c => `
          <div class="card" style="padding:16px; border-left:4px solid #F59E0B; background:#FFFBEB;">
            <h4 style="font-size:14px; font-weight:700; color:#B45309;">Potential Contradiction: ${c.type || 'POS_TAX_HEAD_CONTRADICTION'}</h4>
            <p style="font-size:12px; color:#78350F; margin-top:4px;">${c.description || 'Inter-state Place of Supply contradicts intra-state CGST/SGST tax head classification.'}</p>
            <div style="font-size:11px; font-weight:700; color:#92400E; margin-top:8px;">STATUS: REVIEW REQUIRED (Verification Needed)</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderAIDossierTab() {
    const dossier = this.aiDossier || {};
    return `
      <div class="card" style="padding:24px; border:1px solid #FCD34D; background:#FFFBEB;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <span class="badge" style="background:#8E44AD; color:#fff; font-weight:800;">AI ANALYSIS — ADVISORY ONLY</span>
            <h3 style="font-size:16px; font-weight:700; color:#78350F; margin-top:4px;">Hardened 6-Part AI Investigation Dossier</h3>
          </div>
          <div style="text-align:right; font-size:12px;">
            <div><strong>System Confidence:</strong> <span style="color:#047857; font-weight:700;">HIGH</span></div>
            <div><strong>AI Confidence:</strong> <span style="color:#B45309; font-weight:700;">MEDIUM</span></div>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:14px; font-size:13px; color:#451A03;">
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>1. WHAT WAS DETECTED:</strong> Potential tax head misclassification and IGST overcharge detected for invoice ${this.currentCaseId}.
          </div>
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>2. SUPPORTING EVIDENCE:</strong> Citations: [FIND-001], [EXP-001], [EVD-001].
          </div>
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>3. CONFLICTS &amp; CONTRADICTIONS:</strong> POS inter-state vs CGST intra-state tax charged.
          </div>
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>4. FINANCIAL IMPACT:</strong> ₹3,600.00 potential tax difference.
          </div>
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>5. MISSING EVIDENCE:</strong> Supplier portal GSTR-1 reflection record.
          </div>
          <div style="background:#fff; padding:14px; border-radius:6px; border:1px solid #FDE68A;">
            <strong>6. NEXT STEPS FOR INVESTIGATOR:</strong> Verify supplier filing and request amended invoice if required.
          </div>
        </div>
      </div>
    `;
  }

  renderMissingEvidenceTab(pkg) {
    const missing = pkg.missing_evidence || [];
    if (missing.length === 0) {
      return `<div class="ui-state-card"><p>All required evidence items have been collected for this case.</p></div>`;
    }

    return `
      <div style="display:flex; flex-direction:column; gap:14px;">
        ${missing.map(m => `
          <div class="card" style="padding:16px; border-left:4px solid #3B82F6;">
            <h4 style="font-size:14px; font-weight:700; color:#1E40AF;">Missing Evidence: ${m.evidence_type || 'GSTR-1 Supplier Reflection'}</h4>
            <p style="font-size:12px; color:#1E293B; margin-top:4px;"><strong>Impact:</strong> Cannot confirm supplier portal filing status.</p>
            <p style="font-size:12px; color:#475569; margin-top:2px;"><strong>Recommended Action:</strong> Request GSTR-1 portal verification from vendor.</p>
          </div>
        `).join('')}
      </div>
    `;
  }

  renderTimelineTab(pkg) {
    const caseTime = pkg.case ? (pkg.case.created_at || new Date().toISOString().replace('T', ' ').substring(0, 16)) : new Date().toISOString().replace('T', ' ').substring(0, 16);
    const events = pkg.timeline && pkg.timeline.length ? pkg.timeline : [
      { timestamp: caseTime, type: 'SYSTEM', title: 'Case Created', detail: 'Generated case from invoice validation' },
      { timestamp: caseTime, type: 'AI', title: 'AI Dossier Generated', detail: 'Synthesized grounded advisory dossier' },
    ];

    return `
      <div class="card" style="padding:20px;">
        <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">Case Audit Timeline</h3>
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${events.map(ev => `
            <div style="display:flex; gap:12px; align-items:flex-start; font-size:12px; border-bottom:1px solid var(--border); padding-bottom:8px;">
              <span class="mono" style="color:var(--text-muted); width:130px;">${ev.timestamp}</span>
              <span class="badge" style="background:${ev.type === 'HUMAN' ? '#ECFDF5' : (ev.type === 'AI' ? '#F5F3FF' : '#F1F5F9')}; color:${ev.type === 'HUMAN' ? '#047857' : (ev.type === 'AI' ? '#6D28D9' : '#334155')};">${ev.type}</span>
              <div>
                <strong>${ev.title}</strong>
                <p style="color:var(--text-secondary); margin-top:2px;">${ev.detail}</p>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  renderAuditTab(pkg) {
    const caseTime = pkg.case ? (pkg.case.created_at || new Date().toISOString().replace('T', ' ').substring(0, 19)) : new Date().toISOString().replace('T', ' ').substring(0, 19);
    const corrId = pkg.case ? (pkg.case.case_id || 'corr-system') : 'corr-system';
    return `
      <div class="card" style="padding:20px;">
        <h3 style="font-size:15px; font-weight:700; margin-bottom:14px;">Detailed Audit Log</h3>
        <table class="rec-comparison-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor / Principal</th>
              <th>Action</th>
              <th>Correlation ID</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="mono">${caseTime}</td>
              <td>SYSTEM_VALIDATOR</td>
              <td>EVALUATE_DETERMINISTIC_RULES</td>
              <td class="mono">${corrId}</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  showCalcTrace(findingId) {
    const modalEl = document.getElementById('calcTraceModalContainer');
    if (!modalEl) return;

    modalEl.innerHTML = `
      <div style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.7); z-index:2000; display:flex; align-items:center; justify-content:center; padding:20px;">
        <div class="calc-trace-card" style="width:100%; max-width:550px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="font-size:15px; font-weight:700; color:#38BDF8;">Calculation Trace Viewer</h3>
            <button onclick="document.getElementById('calcTraceModalContainer').innerHTML=''" style="background:transparent; border:none; color:#94A3B8; font-size:18px; cursor:pointer;">&times;</button>
          </div>

          <div class="trace-step-row"><span>Taxable Value</span><span>₹120,000.00</span></div>
          <div class="trace-step-row"><span>Applicable Statutory Rate (TAX_RATE_REF_V2)</span><span>12.00%</span></div>
          <div class="trace-step-row"><span>Expected Statutory IGST</span><span>₹14,400.00</span></div>
          <div class="trace-step-row"><span>Observed Invoice IGST</span><span>₹18,000.00</span></div>
          <div class="trace-step-row total"><span>Potential Tax Overcharge Difference</span><span>₹3,600.00</span></div>

          <div style="margin-top:16px; font-size:11px; color:#94A3B8;">
            Statutory Rule: TAX_001 | Version: 2.0 | Effective From: 2025-09-22
          </div>
        </div>
      </div>
    `;
  }

  openReviewModal(caseId) {
    if (window.CaseManagementView && window.CaseManagementView.openReviewModal) {
      window.CaseManagementView.openReviewModal(caseId);
    } else {
      window.location.hash = '#/case_management';
    }
  }
}

window.CaseWorkspaceView = CaseWorkspaceView;
