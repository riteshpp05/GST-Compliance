/**
 * UC15 GST Compliance Investigation Platform — Investigation Queue View
 * Implements priority-ranked case investigation, category discovery, and systemic scope tracking.
 */

class InvestigationsView {
  constructor(container) {
    this.container = container;
    this.investigationProfile = null;
    this.rootCauses = [];
    this.invoices = [];
    this.selectedCategory = 'ALL';
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Enterprise Investigation Queue</h1>
          <p class="page-subtitle">Prioritized triage queue, category discovery, and systemic blast radius metrics</p>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="badge-status info">Triage Strategy: Risk &times; Financial Exposure</span>
        </div>
      </div>

      <!-- Systemic Scope & Blast Radius KPI Ribbon -->
      <div class="kpi-grid" id="investigationKpiGrid">
        <div class="kpi-card skeleton" style="height:85px;"></div>
        <div class="kpi-card skeleton" style="height:85px;"></div>
        <div class="kpi-card skeleton" style="height:85px;"></div>
        <div class="kpi-card skeleton" style="height:85px;"></div>
      </div>

      <!-- Investigation Categories Matrix -->
      <div class="panel" style="margin-bottom:20px;">
        <div class="panel-header">
          <span class="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            Statutory Investigation Categories &amp; Failure Cohorts
          </span>
          <span style="font-size:11.5px; color:var(--text-secondary);">Select a category to filter the priority queue</span>
        </div>
        <div class="panel-body">
          <div id="categoryGrid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px;">
            <div class="skeleton" style="height:80px;"></div>
            <div class="skeleton" style="height:80px;"></div>
            <div class="skeleton" style="height:80px;"></div>
            <div class="skeleton" style="height:80px;"></div>
            <div class="skeleton" style="height:80px;"></div>
            <div class="skeleton" style="height:80px;"></div>
          </div>
        </div>
      </div>

      <!-- Priority Queue Table -->
      <div class="panel" style="margin-top:20px;">
        <div class="panel-header">
          <span class="panel-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            Triage Priority Queue (Sorted by Risk, Financial Exposure &amp; Recurrence)
          </span>
          <span id="queueCountBadge" class="badge-status info">0 Invoices</span>
        </div>
        <div class="panel-body" id="priorityQueueTableContainer" style="padding:0;">
          <div class="skeleton" style="height:240px;"></div>
        </div>
      </div>
    `;

    await this.loadData();
  }

  async loadData() {
    try {
      const [profile, rootCausesResp, invoices] = await Promise.all([
        window.gstApi.getInvestigationProfile('default'),
        window.gstApi.getRootCauses(),
        window.gstApi.getLatestResults(),
      ]);

      this.investigationProfile = profile;
      this.rootCauses = rootCausesResp.candidates || [];
      this.invoices = invoices;

      this.renderKpis();
      this.renderCategories();
      this.renderQueueTable();
    } catch (err) {
      this.container.innerHTML = `
        <div class="empty-state" style="padding:80px 20px;">
          <h3>Investigation Intelligence Not Ready</h3>
          <p style="color:var(--text-secondary); margin-bottom:16px;">
            Execute a compliance validation run to generate root cause hypotheses and blast radius profiles.
          </p>
          <button class="btn btn-primary" onclick="window.gstApp.runAgent()">Execute Full Compliance Run</button>
        </div>
      `;
    }
  }

  renderKpis() {
    const el = document.getElementById('investigationKpiGrid');
    if (!el || !this.investigationProfile) return;

    const pr = this.investigationProfile;
    const br = pr.blast_radius || {};

    el.innerHTML = `
      <div class="kpi-card kpi-blocked">
        <div class="kpi-header-row">
          <span class="kpi-label">Primary Root Cause</span>
          <div class="kpi-icon-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          </div>
        </div>
        <div class="kpi-value" style="font-size:18px; color:var(--rose-600);">
          ${pr.primary_root_cause ? pr.primary_root_cause.root_cause_type.replace('_', ' ') : 'None'}
        </div>
        <div class="kpi-sub">Confidence: <strong>${pr.primary_root_cause ? pr.primary_root_cause.confidence : 'N/A'}</strong></div>
      </div>

      <div class="kpi-card kpi-exposure">
        <div class="kpi-header-row">
          <span class="kpi-label">Cohort Exposure</span>
          <div class="kpi-icon-pill"><span style="font-weight:800; font-size:12px;">₹</span></div>
        </div>
        <div class="kpi-value" style="font-size:20px; color:var(--indigo-600);">${GSTCharts.formatCurrency(pr.financial_exposure)}</div>
        <div class="kpi-sub"><strong>${br.affected_invoice_count || 0}</strong> Invoices Affected</div>
      </div>

      <div class="kpi-card kpi-review">
        <div class="kpi-header-row">
          <span class="kpi-label">Systemic Boundary</span>
          <div class="kpi-icon-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>
          </div>
        </div>
        <div class="kpi-value" style="font-size:18px; color:var(--amber-600);">${pr.systemic_classification || 'ISOLATED'}</div>
        <div class="kpi-sub">Trend: <strong>${pr.trend || 'STABLE'}</strong></div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header-row">
          <span class="kpi-label">Root Cause Hypotheses</span>
          <div class="kpi-icon-pill">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </div>
        </div>
        <div class="kpi-value" style="font-size:22px;">${this.rootCauses.length}</div>
        <div class="kpi-sub">Multi-Factor Evaluated</div>
      </div>
    `;
  }

  renderCategories() {
    const el = document.getElementById('categoryGrid');
    if (!el) return;

    const categories = [
      { id: 'ALL', label: 'All Discrepancies' },
      { id: 'ITC', label: 'ITC & 2B Process' },
      { id: 'TAX', label: 'Tax Rate & HSN' },
      { id: 'PLACE_OF_SUPPLY', label: 'Place of Supply' },
      { id: 'EWAY_BILL', label: 'E-Way Bill Compliance' },
      { id: 'MASTER_DATA', label: 'Master Data & GSTIN' },
      { id: 'ANOMALIES', label: 'Statistical Outliers' },
    ];

    el.innerHTML = categories.map(cat => {
      const isSelected = this.selectedCategory === cat.id;
      const count = this.getCategoryCount(cat.id);
      return `
        <div onclick="window.investigationsView.filterCategory('${cat.id}')"
          style="background:${isSelected ? 'var(--blue-50)' : 'var(--bg-surface)'};
                 border:1px solid ${isSelected ? 'var(--blue-800)' : 'var(--border)'};
                 border-radius:var(--radius-md); padding:12px 14px; cursor:pointer;
                 transition:all 0.15s ease; display:flex; align-items:center; justify-content:space-between;">
          <div>
            <div style="font-size:12.5px; font-weight:${isSelected ? '700' : '600'}; color:${isSelected ? 'var(--blue-900)' : 'var(--text-primary)'};">
              ${cat.label}
            </div>
          </div>
          <span style="font-family:var(--font-mono); font-weight:700; font-size:13px; color:${count > 0 ? 'var(--status-red)' : 'var(--text-muted)'};">
            ${count}
          </span>
        </div>
      `;
    }).join('');
  }

  getCategoryCount(catId) {
    if (!this.invoices) return 0;
    if (catId === 'ALL') {
      return this.invoices.filter(d => d.status !== 'COMPLIANT').length;
    }
    if (catId === 'ANOMALIES') {
      return this.invoices.filter(d => d.has_anomaly).length;
    }
    return this.invoices.filter(d => {
      return (d.gates || []).some(g => g.category === catId && g.status === 'FAIL');
    }).length;
  }

  filterCategory(catId) {
    this.selectedCategory = catId;
    this.renderCategories();
    this.renderQueueTable();
  }

  renderRootCauses() {
    const el = document.getElementById('rootCauseCandidateList');
    if (!el) return;

    if (this.rootCauses.length === 0) {
      el.innerHTML = `<div class="empty-state"><p>No root causes generated.</p></div>`;
      return;
    }

    el.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px;">
        ${this.rootCauses.map((rc, idx) => {
          const isPrimary = idx === 0;
          const scoreVal = rc.score ? rc.score.total_score.toFixed(1) : '—';
          return `
            <div style="border:1px solid ${isPrimary ? 'var(--blue-700)' : 'var(--border)'};
                        border-radius:var(--radius-sm); padding:12px 14px;
                        background:${isPrimary ? 'var(--blue-50)' : '#fff'};">
              <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px;">
                <div style="display:flex; align-items:center; gap:8px;">
                  ${isPrimary ? '<span style="background:var(--saffron-500); color:#fff; font-size:9.5px; font-weight:800; padding:2px 6px; border-radius:3px;">PRIMARY</span>' : '<span style="background:#E2E8F0; color:var(--text-secondary); font-size:9.5px; font-weight:700; padding:2px 6px; border-radius:3px;">CONTRIBUTING</span>'}
                  <strong style="font-size:13px; color:var(--blue-900);">${rc.root_cause_type.replace('_', ' ')}</strong>
                </div>
                <div style="font-family:var(--font-mono); font-size:11.5px; font-weight:700; color:var(--blue-800);">
                  Confidence: ${rc.confidence || 'HIGH'}
                </div>
              </div>
              <p style="font-size:12px; color:var(--text-secondary); margin-bottom:6px; line-height:1.4;">
                ${rc.causality_statement || rc.description}
              </p>
              <div style="display:flex; gap:12px; font-size:11px; color:var(--text-muted);">
                <span>Affected Invoices: <strong style="color:var(--text-primary);">${(rc.affected_invoice_ids || []).length}</strong></span>
                <span>Confidence: <strong style="color:var(--text-primary);">${rc.confidence}</strong></span>
                <span>Exposure: <strong style="color:var(--saffron-600); font-family:var(--font-mono);">${GSTCharts.formatCurrency(rc.financial_exposure)}</strong></span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  renderBlastRadius() {
    const el = document.getElementById('blastRadiusOverviewPanel');
    if (!el || !this.investigationProfile) return;

    const br = this.investigationProfile.blast_radius;
    if (!br) {
      el.innerHTML = `<div class="empty-state"><p>No blast radius profile available</p></div>`;
      return;
    }

    el.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:14px;">
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
          <div style="background:var(--bg-subtle); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px 14px; text-align:center;">
            <div style="font-size:10px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Systemic Classification</div>
            <div style="font-size:16px; font-weight:800; color:var(--blue-900); margin-top:3px;">${br.systemic_classification}</div>
          </div>
          <div style="background:var(--bg-subtle); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px 14px; text-align:center;">
            <div style="font-size:10px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Temporal Trajectory</div>
            <div style="font-size:16px; font-weight:800; color:var(--blue-900); margin-top:3px;">${br.trend}</div>
          </div>
        </div>

        <div class="blast-chain">
          <div class="blast-node">
            <div class="lbl">Root Cause</div>
            <div class="val" style="font-size:12px;">${br.root_cause_id.replace('RC-', '')}</div>
          </div>
          <div class="blast-arrow">&rarr;</div>
          <div class="blast-node">
            <div class="lbl">Invoices</div>
            <div class="val">${br.affected_invoice_count}</div>
          </div>
          <div class="blast-arrow">&rarr;</div>
          <div class="blast-node">
            <div class="lbl">Vendors</div>
            <div class="val">${br.affected_counterparty_count}</div>
          </div>
          <div class="blast-arrow">&rarr;</div>
          <div class="blast-node">
            <div class="lbl">Exposure</div>
            <div class="val" style="color:var(--saffron-600); font-family:var(--font-mono);">${GSTCharts.formatCurrency(br.total_potential_exposure)}</div>
          </div>
        </div>

        <div style="font-size:11.5px; color:var(--text-secondary); background:var(--bg-subtle); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px 14px;">
          Duration: <strong>${br.duration_periods} Tax Period(s)</strong> (${br.first_detected_period || '—'} &rarr; ${br.last_detected_period || '—'}) &middot; Top Vendor Share: <strong>${((br.top_counterparty_share || 0) * 100).toFixed(0)}%</strong>
        </div>
      </div>
    `;
  }

  renderQueueTable() {
    const el = document.getElementById('priorityQueueTableContainer');
    const badge = document.getElementById('queueCountBadge');
    if (!el) return;

    let items = this.invoices.filter(d => d.status !== 'COMPLIANT');

    if (this.selectedCategory !== 'ALL') {
      if (this.selectedCategory === 'ANOMALIES') {
        items = items.filter(d => d.has_anomaly);
      } else {
        items = items.filter(d => (d.gates || []).some(g => g.category === this.selectedCategory && g.status === 'FAIL'));
      }
    }

    // Deterministic Priority Sorting:
    // 1. Priority P1 > P2 > P3 > P4
    // 2. Risk Score (descending)
    // 3. Potential Exposure (descending)
    // 4. Failed gate count (descending)
    const priWeight = { P1: 4, P2: 3, P3: 2, P4: 1 };
    items.sort((a, b) => {
      const pDiff = (priWeight[b.priority] || 0) - (priWeight[a.priority] || 0);
      if (pDiff !== 0) return pDiff;
      const rDiff = (b.risk_score || 0) - (a.risk_score || 0);
      if (rDiff !== 0) return rDiff;
      const eDiff = (b.potential_exposure || 0) - (a.potential_exposure || 0);
      if (eDiff !== 0) return eDiff;
      return (b.failed_gate_count || 0) - (a.failed_gate_count || 0);
    });

    if (badge) badge.textContent = `${items.length} Invoices`;

    if (items.length === 0) {
      el.innerHTML = `
        <div class="empty-state">
          <h3>No invoices in this investigation category</h3>
          <p>Select another category or view all discrepancies.</p>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th style="width:50px;">Rank</th>
            <th>Priority</th>
            <th>Invoice No</th>
            <th>Counterparty</th>
            <th>Compliance Status</th>
            <th>Failed Gates</th>
            <th>Audit Priority</th>
            <th>Potential Exposure</th>
            <th style="text-align:right;">Action</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((inv, idx) => {
            const failedNames = (inv.failed_gate_names || []).join(', ') || 'Review Flagged';
            return `
              <tr>
                <td style="font-family:var(--font-mono); font-weight:700; color:var(--text-muted);">#${idx + 1}</td>
                <td><span class="priority-tag ${(inv.priority || 'P4').toLowerCase()}">${inv.priority || 'P4'}</span></td>
                <td><a href="#/investigation/${inv.invoice_no}" class="inv-link">${inv.invoice_no}</a></td>
                <td>
                  <div style="font-weight:600;">${inv.counterparty_name}</div>
                  <div style="font-size:10px; color:var(--text-muted); font-family:var(--font-mono);">${inv.counterparty_gstin}</div>
                </td>
                <td>
                  <span class="badge-status ${inv.status === 'COMPLIANT' ? 'compliant' : (inv.status === 'NON_COMPLIANT' ? 'non-compliant' : 'needs-review')}">
                    ${inv.status === 'COMPLIANT' ? 'Approved' : (inv.status === 'NON_COMPLIANT' ? 'Blocked' : 'Needs Review')}
                  </span>
                </td>
                <td style="font-size:11.5px; color:var(--status-red); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                  ${failedNames}
                </td>
                <td>
                  <span class="risk-tag ${(inv.risk_level || 'LOW').toLowerCase()}">
                    ${inv.risk_level || 'LOW'} Priority
                  </span>
                </td>
                <td style="font-family:var(--font-mono); font-weight:700; color:var(--saffron-600); text-align:right;">
                  ${GSTCharts.formatCurrency(inv.potential_exposure)}
                </td>
                <td style="text-align:right;">
                  <a href="#/investigation/${inv.invoice_no}" class="btn btn-outline" style="padding:4px 10px; font-size:11px;">
                    Investigate &rarr;
                  </a>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;
  }
}

window.InvestigationsView = InvestigationsView;
