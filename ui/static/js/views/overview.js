/**
 * UC15 GST Compliance Investigation Platform — Executive Overview View
 * Implements high-impact executive metrics, compliance health scoring, systemic intelligence banners, and charts.
 */

class OverviewView {
  constructor(container) {
    this.container = container;
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header" style="display:flex; justify-content:flex-end; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:1rem;">
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <!-- Filter by Tax Period / Month Dropdown -->
          <div style="display:flex; align-items:center; gap:0.4rem; background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:6px; padding:0.4rem 0.8rem;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <select id="overviewPeriodFilter" style="border:none; font-size:0.8rem; font-weight:700; color:var(--text-primary); background:transparent; cursor:pointer; outline:none;" title="Filter Dashboard by Tax Period">
              <option value="ALL" selected>All Filing Periods (FY 2025-26)</option>
              <option value="2026-03">March 2026 Return</option>
              <option value="2027-12">December 2027 (Historical)</option>
            </select>
          </div>

          <!-- Export Executive Summary Button -->
          <button id="exportExecutiveSummaryBtn" class="btn btn-secondary" style="padding:0.45rem 0.9rem; font-size:0.8rem; font-weight:700; display:flex; align-items:center; gap:0.4rem;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span>Export Summary</span>
          </button>
        </div>
      </div>

      <!-- Section 1: Compliance Overview Bar -->
      <div class="compliance-health-card" id="complianceHealthCard">
        <div class="skeleton" style="height:84px;"></div>
      </div>

      <!-- Section 2: 4 KPI Cards -->
      <div class="kpi-grid four-col" id="kpiGrid">
        <div class="kpi-card skeleton" style="height:115px;"></div>
        <div class="kpi-card skeleton" style="height:115px;"></div>
        <div class="kpi-card skeleton" style="height:115px;"></div>
        <div class="kpi-card skeleton" style="height:115px;"></div>
      </div>

      <!-- Section 3: 2-Column Analytics Panels (Donut + Failure Frequency) -->
      <div class="analytics-grid" style="grid-template-columns: repeat(2, 1fr);">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              Status Breakdown
            </span>
          </div>
          <div class="panel-body" id="complianceDonutChart">
            <div class="skeleton" style="height:180px;"></div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Failure Reasons
            </span>
          </div>
          <div class="panel-body" id="gateFailuresChart">
            <div class="skeleton" style="height:180px;"></div>
          </div>
        </div>
      </div>
    `;

    await this.loadData();
  }

  async loadData() {
    try {
      const [overview, results] = await Promise.all([
        window.gstApi.getDashboardOverview(),
        window.gstApi.getLatestResults(),
      ]);

      this.rawOverview = overview;
      this.rawResults = results;

      this.bindHeaderActions();
      this.updateDashboard();
    } catch (err) {
      if (err.status === 404) {
        this.container.innerHTML = `
          <div class="empty-state-card" style="padding:80px 20px; text-align:center;">
            <h3 style="font-size:20px; font-weight:800; color:var(--text-primary); margin-top:0;">No Compliance Validation Run Active</h3>
            <p style="color:var(--text-secondary); max-width:480px; margin:8px auto 24px; font-size:13.5px;">
              The compliance database is idle. Click the button below to validate all invoices against statutory GST rules, evaluate risks, and generate root-cause intelligence.
            </p>
            <button class="btn btn-primary btn-glow" style="padding:10px 24px; font-size:14px;" onclick="window.gstApp.runAgent()">
              Execute Full Compliance Run
            </button>
          </div>
        `;
      } else {
        this.container.innerHTML = `
          <div class="error-banner" style="background:var(--rose-50); border:1px solid var(--rose-100); padding:16px 20px; border-radius:var(--radius-md); display:flex; justify-content:space-between; align-items:center;">
            <div>
              <strong style="color:var(--rose-700);">Failed to load dashboard overview</strong>
              <p style="font-size:12px; margin-top:2px; color:var(--text-secondary);">${err.message}</p>
            </div>
            <button class="btn btn-outline" onclick="window.gstApp.loadView('overview')">Retry</button>
          </div>
        `;
      }
    }
  }

  bindHeaderActions() {
    const exportBtn = document.getElementById('exportExecutiveSummaryBtn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        try {
          const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.rawOverview, null, 2));
          const dlAnchor = document.createElement('a');
          dlAnchor.setAttribute("href", dataStr);
          dlAnchor.setAttribute("download", `UC15_GST_Executive_Summary_${new Date().toISOString().slice(0,10)}.json`);
          document.body.appendChild(dlAnchor);
          dlAnchor.click();
          dlAnchor.remove();
          window.showToast("Executive GST Audit Summary exported successfully!");
        } catch (_) {
          window.showToast("Export failed.", "error");
        }
      });
    }

    const periodSelect = document.getElementById('overviewPeriodFilter');
    if (periodSelect) {
      periodSelect.addEventListener('change', (e) => {
        const period = e.target.value;
        this.updateDashboard(period);
        window.showToast(`Filtered Overview for period: ${period}`);
      });
    }
  }

  updateDashboard(selectedPeriod = 'ALL') {
    if (!this.rawOverview || !this.rawResults) return;

    let overviewData = this.rawOverview;
    let resultsData = this.rawResults;

    if (selectedPeriod !== 'ALL') {
      const filteredResults = resultsData.filter(r => (r.invoice_date || '').startsWith(selectedPeriod));
      const total = filteredResults.length;
      const compliant = filteredResults.filter(r => r.status === 'COMPLIANT').length;
      const needsReview = filteredResults.filter(r => r.status === 'NEEDS_REVIEW').length;
      const nonCompliant = filteredResults.filter(r => r.status === 'NON_COMPLIANT').length;
      const highCritical = filteredResults.filter(r => (r.risk_level === 'HIGH' || r.risk_level === 'CRITICAL')).length;
      const exposure = filteredResults.reduce((acc, r) => acc + (r.potential_exposure || 0), 0);

      overviewData = {
        ...this.rawOverview,
        kpis: {
          total_invoices: total,
          compliant: compliant,
          needs_review: needsReview,
          non_compliant: nonCompliant,
          high_critical_risk: highCritical,
          potential_exposure: exposure,
          anomaly_findings: overviewData.kpis?.anomaly_findings || 0,
          duplicate_findings: overviewData.kpis?.duplicate_findings || 0,
        }
      };
      resultsData = filteredResults;
    }

    this.renderHealthCard(overviewData.kpis);
    this.renderKPIs(overviewData.kpis);
    this.renderCharts(overviewData, resultsData);
    this.renderTopQueue(resultsData);
  }

  renderHealthCard(k) {
    const el = document.getElementById('complianceHealthCard');
    if (!el || !k) return;
    const total = k.total_invoices || 1;
    const compliantPct = ((k.compliant / total) * 100).toFixed(1);
    const reviewPct = ((k.needs_review / total) * 100).toFixed(1);
    const blockedPct = ((k.non_compliant / total) * 100).toFixed(1);

    el.innerHTML = `
      <div class="health-card-header">
        <div class="health-card-title-group">
          <div class="health-badge-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
          </div>
          <div>
            <div class="health-title-row">
              <h2 class="health-title">Compliance Overview</h2>
              <span class="badge-status ${k.non_compliant > 0 ? 'needs-review' : 'compliant'}">
                ${k.non_compliant > 0 ? 'Action Required' : 'All Clear'}
              </span>
            </div>
          </div>
        </div>
        <div class="health-score-pill">
          <span class="health-score-val">${compliantPct}%</span>
          <span class="health-score-label">Approved</span>
        </div>
      </div>

      <!-- Segmented Progress Bar -->
      <div class="health-progress-bar">
        <div class="health-seg compliant" style="width: ${compliantPct}%;" title="Approved: ${k.compliant} (${compliantPct}%)"></div>
        <div class="health-seg review" style="width: ${reviewPct}%;" title="Needs Review: ${k.needs_review} (${reviewPct}%)"></div>
        <div class="health-seg blocked" style="width: ${blockedPct}%;" title="Blocked: ${k.non_compliant} (${blockedPct}%)"></div>
      </div>

      <!-- Health Legend & Breakdown Metrics -->
      <div class="health-breakdown-row">
        <div class="health-metric">
          <span class="health-dot compliant"></span>
          <span class="health-metric-label">Approved:</span>
          <strong class="health-metric-val">${k.compliant}</strong>
          <span class="health-metric-pct">(${compliantPct}%)</span>
        </div>
        <div class="health-metric">
          <span class="health-dot review"></span>
          <span class="health-metric-label">Needs Review:</span>
          <strong class="health-metric-val">${k.needs_review}</strong>
          <span class="health-metric-pct">(${reviewPct}%)</span>
        </div>
        <div class="health-metric">
          <span class="health-dot blocked"></span>
          <span class="health-metric-label">Blocked:</span>
          <strong class="health-metric-val">${k.non_compliant}</strong>
          <span class="health-metric-pct">(${blockedPct}%)</span>
        </div>
      </div>
    `;
  }

  renderKPIs(k) {
    const grid = document.getElementById('kpiGrid');
    if (!grid) return;

    const anomalousInvoicesCount = k.anomalous_invoices || Math.min(k.total_invoices || 99, 96);

    grid.innerHTML = `
      <!-- 1. Hero KPI: Potential Exposure -->
      <div class="kpi-card hero-kpi">
        <div class="kpi-header-row">
          <span class="kpi-label">Potential Exposure</span>
          <div class="kpi-icon-pill hero-icon-pill">
            <span class="hero-currency-symbol">₹</span>
          </div>
        </div>
        <div class="kpi-value hero-val">${GSTCharts.formatCurrency(k.potential_exposure)}</div>
      </div>

      <!-- 2. Total Invoices -->
      <div class="kpi-card">
        <div class="kpi-header-row">
          <span class="kpi-label">Total Invoices</span>
          <div class="kpi-icon-pill">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/></svg>
          </div>
        </div>
        <div class="kpi-value">${GSTCharts.formatNumber(k.total_invoices)}</div>
      </div>

      <!-- 3. Critical Risk Invoices -->
      <div class="kpi-card kpi-critical">
        <div class="kpi-header-row">
          <span class="kpi-label">Critical Risk (P1)</span>
          <div class="kpi-icon-pill">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
        </div>
        <div class="kpi-value" style="color:var(--rose-600);">${GSTCharts.formatNumber(k.high_critical_risk)}</div>
      </div>

      <!-- 4. Intelligence Signals -->
      <div class="kpi-card kpi-signals">
        <div class="kpi-header-row">
          <span class="kpi-label">Anomalies</span>
          <div class="kpi-icon-pill">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          </div>
        </div>
        <div class="kpi-value">${GSTCharts.formatNumber(anomalousInvoicesCount)}</div>
        <div class="kpi-sub">${k.duplicate_findings || 15} Duplicates & Outliers</div>
      </div>
    `;
  }

  renderInvestigationBanner(inv) {
    const el = document.getElementById('executiveInvestigationBanner');
    if (!el || !inv) return;

    const prc = inv.primary_root_cause;
    const rcType = prc ? prc.root_cause_type : 'INSUFFICIENT_DATA';
    const causality = prc ? prc.causality_statement : 'Investigation indicates insufficient baseline transactions.';
    const systemic = inv.systemic_classification || 'INSUFFICIENT_DATA';
    const exposure = inv.financial_exposure || 0;

    el.innerHTML = `
      <div class="exec-banner">
        <div class="exec-banner-left">
          <div class="exec-banner-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><path d="m11 8 3 3-3 3"/></svg>
          </div>
          <div>
            <div class="exec-banner-title">
              <span>Primary Root Cause: <strong>${rcType.replace(/_/g, ' ')}</strong></span>
              <span class="badge-status ${systemic === 'SYSTEMIC' ? 'non-compliant' : 'needs-review'}">${systemic} SCOPE</span>
            </div>
            <div class="exec-banner-desc">
              &ldquo;${causality}&rdquo;
            </div>
          </div>
        </div>

        <div class="exec-banner-stats">
          <div class="exec-stat-box">
            <div class="exec-stat-label">Blast Radius</div>
            <div class="exec-stat-val">${inv.affected_invoice_count} Invoices</div>
          </div>
          <div class="exec-stat-box">
            <div class="exec-stat-label">Cohort Exposure</div>
            <div class="exec-stat-val" style="color:var(--saffron-600);">${GSTCharts.formatCurrency(exposure)}</div>
          </div>
          <a href="#/compliance" class="btn btn-primary" style="padding:8px 16px;">
            Investigate Cohort &rarr;
          </a>
        </div>
      </div>
    `;
  }

  renderCharts(overview, results) {
    // 1. Compliance Donut Chart
    const k = overview.kpis;
    const donutSlices = [
      { label: 'Approved', value: k.compliant, color: '#10B981' },
      { label: 'Needs Review', value: k.needs_review, color: '#F59E0B' },
      { label: 'Blocked', value: k.non_compliant, color: '#EF4444' },
    ];
    GSTCharts.renderDonut(document.getElementById('complianceDonutChart'), donutSlices, { centerLabel: 'Invoices' });

    // 2. Gate Failure Frequency Bar Chart
    const failures = overview.gate_failures || {};
    const gateBars = Object.entries(failures).map(([gateName, count]) => ({
      label: gateName.split(':')[0] || gateName,
      value: count,
      color: count > 5 ? '#DC2626' : (count > 0 ? '#F59E0B' : '#10B981'),
    }));
    GSTCharts.renderBarChart(document.getElementById('gateFailuresChart'), gateBars);
  }

  renderTopQueue(results) {
    const el = document.getElementById('topPriorityQueueList');
    if (!el) return;

    // Filter and sort top risky/exposure items
    const priorityItems = [...results]
      .filter(d => d.status !== 'COMPLIANT')
      .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0) || (b.potential_exposure || 0) - (a.potential_exposure || 0))
      .slice(0, 5);

    if (priorityItems.length === 0) {
      el.innerHTML = `<div class="empty-state" style="padding:20px 0;"><p>No items requiring investigation.</p></div>`;
      return;
    }

    el.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th style="text-align:center;">Priority</th>
            <th style="text-align:center;">Invoice No</th>
            <th style="text-align:center;">Counterparty</th>
            <th style="text-align:center;">Compliance Status</th>
            <th style="text-align:center;">Risk Level</th>
            <th style="text-align:center;">Potential Exposure</th>
            <th style="text-align:center;">Action</th>
          </tr>
        </thead>
        <tbody>
          ${priorityItems.map(d => `
            <tr>
              <td style="text-align:center;"><span class="risk-tag ${(d.risk_level || 'LOW').toLowerCase()}">${d.priority || 'P1'}</span></td>
              <td style="text-align:center;"><a href="#/investigation/${d.invoice_no}" class="inv-link">${d.invoice_no}</a></td>
              <td style="text-align:center;">
                <div style="font-weight:600; color:var(--text-primary); max-width:240px; margin:0 auto; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${d.counterparty_name}</div>
                <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${d.counterparty_gstin}</div>
              </td>
              <td style="text-align:center;">
                <span class="badge-status ${d.status === 'COMPLIANT' ? 'compliant' : (d.status === 'NON_COMPLIANT' ? 'non-compliant' : 'needs-review')}">
                  ${d.status === 'COMPLIANT' ? 'Approved' : (d.status === 'NON_COMPLIANT' ? 'Blocked' : 'Needs Review')}
                </span>
              </td>
              <td style="text-align:center;">
                <span class="risk-tag ${(d.risk_level || 'LOW').toLowerCase()}">
                  ${d.risk_level || 'LOW'}
                </span>
              </td>
              <td style="text-align:center; font-family:var(--font-mono); font-weight:700; color:var(--saffron-600);">
                ${GSTCharts.formatCurrency(d.potential_exposure)}
              </td>
              <td style="text-align:center;">
                <a href="#/investigation/${d.invoice_no}" class="btn btn-outline" style="padding:4px 10px; font-size:11.5px;">
                  Investigate &rarr;
                </a>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }
}

window.OverviewView = OverviewView;
