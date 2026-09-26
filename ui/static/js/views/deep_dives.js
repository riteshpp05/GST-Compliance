/**
 * UC15 GST Compliance Investigation Platform — Deep-Dive Intelligence Views
 * Provides dedicated views for Risk, Financial, Historical, and Anomaly/Duplicate analytics.
 */

class DeepDivesView {
  constructor(container) {
    this.container = container;
  }

  // 1. RISK & FINANCIAL INTELLIGENCE DEEP DIVE (#risk)
  async renderRisk() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Statutory Risk &amp; Financial Impact Intelligence</h1>
          <p class="page-subtitle">Multi-Factor Risk Model, Monetary Exposures, and Statutory Rule Breakdown</p>
        </div>
      </div>

      <!-- Top Risk KPIs -->
      <div class="kpi-grid" id="riskKpiGrid">
        <div class="kpi-card skeleton" style="height:80px;"></div>
        <div class="kpi-card skeleton" style="height:80px;"></div>
        <div class="kpi-card skeleton" style="height:80px;"></div>
        <div class="kpi-card skeleton" style="height:80px;"></div>
      </div>

      <!-- Financial Exposure KPIs -->
      <div class="kpi-grid" id="finKpiGrid" style="margin-top:16px;">
        <div class="kpi-card skeleton" style="height:80px;"></div>
        <div class="kpi-card skeleton" style="height:80px;"></div>
        <div class="kpi-card skeleton" style="height:80px;"></div>
      </div>

      <!-- Charts Row -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(400px, 1fr)); gap:20px; margin-top:20px;">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">Risk Severity Breakdown by Invoices</span>
          </div>
          <div class="panel-body" id="riskDeepChart">
            <div class="skeleton" style="height:160px;"></div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">Aggregate Exposure by Statutory Rule</span>
          </div>
          <div class="panel-body" id="finRuleChart">
            <div class="skeleton" style="height:160px;"></div>
          </div>
        </div>
      </div>

      <!-- Top Financial Exposures Table -->
      <div class="panel" style="margin-top:20px;">
        <div class="panel-header">
          <span class="panel-title">Top Monetary Exposures &amp; Rule Impacts</span>
        </div>
        <div class="panel-body" id="finTopTable" style="padding:0;">
          <div class="skeleton" style="height:200px;"></div>
        </div>
      </div>

      <!-- Top Risky Invoices Table -->
      <div class="panel" style="margin-top:20px;">
        <div class="panel-header">
          <span class="panel-title">Top Riskiest Invoices Requiring Statutory Mitigation</span>
        </div>
        <div class="panel-body" id="topRiskyTable" style="padding:0;">
          <div class="skeleton" style="height:200px;"></div>
        </div>
      </div>
    `;

    try {
      const [riskSum, results, finSum, topExposures] = await Promise.all([
        window.gstApi.getRiskSummary(),
        window.gstApi.getLatestResults(),
        window.gstApi.getFinancialSummary(),
        window.gstApi.getTopExposures(10),
      ]);

      // Risk KPIs
      const kEl = document.getElementById('riskKpiGrid');
      if (kEl) {
        kEl.innerHTML = `
          <div class="kpi-card">
            <div class="kpi-header-row">
              <span class="kpi-label">Portfolio Health</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20v-6M6 20V10M18 20V4"/></svg></div>
            </div>
            <div class="kpi-value" style="font-family:var(--font-mono); color:var(--emerald-600);">Active</div>
            <div class="kpi-sub">Statutory Audit Active</div>
          </div>
          <div class="kpi-card kpi-blocked">
            <div class="kpi-header-row">
              <span class="kpi-label">Critical Invoices</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
            </div>
            <div class="kpi-value" style="color:var(--rose-600);">${riskSum.by_level.CRITICAL || 0}</div>
            <div class="kpi-sub">Immediate Audit Required</div>
          </div>
          <div class="kpi-card kpi-review">
            <div class="kpi-header-row">
              <span class="kpi-label">High / Medium / Moderate</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
            </div>
            <div class="kpi-value" style="color:var(--amber-600);">${(riskSum.by_level.HIGH || 0) + (riskSum.by_level.MEDIUM || 0) + (riskSum.by_level.MODERATE || 0)}</div>
            <div class="kpi-sub">Review Recommended</div>
          </div>
          <div class="kpi-card kpi-compliant">
            <div class="kpi-header-row">
              <span class="kpi-label">Low / Clean Invoices</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>
            </div>
            <div class="kpi-value" style="color:var(--emerald-600);">${riskSum.by_level.LOW || 0}</div>
            <div class="kpi-sub">Clean / Approved</div>
          </div>
        `;
      }

      // Financial Exposure KPIs
      const agg = finSum.aggregate || finSum.aggregate_exposure || {};
      const totalExp = agg.total_potential_exposure !== undefined ? agg.total_potential_exposure : (agg.total_exposure || 0);

      const fEl = document.getElementById('finKpiGrid');
      if (fEl) {
        fEl.innerHTML = `
          <div class="kpi-card kpi-exposure">
            <div class="kpi-header-row">
              <span class="kpi-label">Total Potential Exposure</span>
              <div class="kpi-icon-pill"><span style="font-weight:800; font-size:13px;">₹</span></div>
            </div>
            <div class="kpi-value" style="font-size:24px; color:var(--indigo-600);">${GSTCharts.formatCurrency(totalExp)}</div>
            <div class="kpi-sub">Strict Monetary Reconciliation</div>
          </div>
          <div class="kpi-card kpi-compliant">
            <div class="kpi-header-row">
              <span class="kpi-label">Calculated Invoices</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>
            </div>
            <div class="kpi-value" style="color:var(--emerald-600);">${agg.calculated_count || topExposures.length}</div>
            <div class="kpi-sub">Deterministic Monetary Backing</div>
          </div>
          <div class="kpi-card kpi-review">
            <div class="kpi-header-row">
              <span class="kpi-label">Undetermined Exposures</span>
              <div class="kpi-icon-pill"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
            </div>
            <div class="kpi-value" style="color:var(--amber-600);">${agg.undetermined_count || 0}</div>
            <div class="kpi-sub">Requires Reference Pricing Documents</div>
          </div>
        `;
      }

      // Risk Chart
      const bars = [
        { label: 'Critical', value: riskSum.by_level.CRITICAL || 0, color: '#9F1239' },
        { label: 'High', value: riskSum.by_level.HIGH || 0, color: '#C2410C' },
        { label: 'Medium', value: riskSum.by_level.MEDIUM || 0, color: '#B45309' },
        { label: 'Moderate', value: riskSum.by_level.MODERATE || 0, color: '#4338CA' },
        { label: 'Low', value: riskSum.by_level.LOW || 0, color: '#15803D' },
      ];
      GSTCharts.renderBarChart(document.getElementById('riskDeepChart'), bars);

      // Financial Rule Chart
      const byRule = agg.by_rule || {};
      const segments = Object.entries(byRule).map(([r, amt], idx) => {
        const colors = ['#E67E22', '#C8202D', '#0B3D6B', '#6F42C1'];
        return { label: r, amount: amt, color: colors[idx % colors.length] };
      });
      GSTCharts.renderHorizontalStacked(document.getElementById('finRuleChart'), segments);

      // Top Financial Exposures Table
      const fTbl = document.getElementById('finTopTable');
      if (fTbl) {
        fTbl.innerHTML = `
          <table class="data-table">
            <thead>
              <tr>
                <th>Invoice No</th>
                <th>Counterparty</th>
                <th>Rule Category</th>
                <th>Impact Type</th>
                <th>Potential Exposure</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${topExposures.map(exp => `
                <tr>
                  <td><a href="#/investigation/${exp.invoice_id}" class="inv-link">${exp.invoice_id}</a></td>
                  <td>${exp.counterparty_name}</td>
                  <td>${exp.rule_category}</td>
                  <td>${(exp.impact_type || '').replace('_', ' ')}</td>
                  <td style="font-family:var(--font-mono); font-weight:700; color:var(--saffron-600);">
                    ${GSTCharts.formatCurrency(exp.potential_exposure)}
                  </td>
                  <td><a href="#/investigation/${exp.invoice_id}" class="btn btn-outline" style="padding:3px 8px; font-size:11px;">Inspect</a></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      // Top Risky Table
      const topRisky = [...results].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 10);
      const rTbl = document.getElementById('topRiskyTable');
      if (rTbl) {
        rTbl.innerHTML = `
          <table class="data-table">
            <thead>
              <tr>
                <th>Invoice No</th>
                <th>Counterparty</th>
                <th>Risk Level</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${topRisky.map(i => `
                <tr>
                  <td><a href="#/investigation/${i.invoice_no}" class="inv-link">${i.invoice_no}</a></td>
                  <td>${i.counterparty_name}</td>
                  <td><span class="risk-tag ${(i.risk_level || 'LOW').toLowerCase()}">${i.risk_level || 'LOW'}</span></td>
                  <td><span class="priority-tag ${(i.priority || 'P4').toLowerCase()}">${i.priority || 'P4'}</span></td>
                  <td><span class="badge-status ${i.status === 'COMPLIANT' ? 'compliant' : (i.status === 'NON_COMPLIANT' ? 'non-compliant' : 'needs-review')}">${i.status === 'COMPLIANT' ? 'Approved' : (i.status === 'NON_COMPLIANT' ? 'Blocked' : 'Needs Review')}</span></td>
                  <td><a href="#/investigation/${i.invoice_no}" class="btn btn-outline" style="padding:3px 8px; font-size:11px;">Inspect</a></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }
    } catch (err) {
      console.error(err);
    }
  }

  // Backward compatibility alias for renderFinancial
  async renderFinancial() {
    return this.renderRisk();
  }



  // 4. ANOMALY & DUPLICATE INTELLIGENCE DEEP DIVE (#intelligence)
  async renderIntelligence() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Duplicate &amp; Anomaly Intelligence</h1>
          <p class="page-subtitle">Exact/near duplicate detection and statistical transaction outlier discovery</p>
        </div>
      </div>

      <div class="analytics-grid">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">Duplicate Invoices &amp; Clusters</span>
          </div>
          <div class="panel-body" id="dupList">
            <div class="skeleton" style="height:150px;"></div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">Statistical Anomalies (Value, Frequency, Tax Rate)</span>
          </div>
          <div class="panel-body" id="anomList">
            <div class="skeleton" style="height:150px;"></div>
          </div>
        </div>
      </div>
    `;

    try {
      const [dupsResp, anomsResp] = await Promise.all([
        window.gstApi.getDuplicates(),
        window.gstApi.getAnomalies(),
      ]);

      const dupEl = document.getElementById('dupList');
      if (dupEl) {
        if (dupsResp.candidate_count === 0) {
          dupEl.innerHTML = `<div class="empty-state"><p>No duplicate invoice candidates identified.</p></div>`;
        } else {
          dupEl.innerHTML = dupsResp.candidates.map(c => `
            <div style="border:1px solid var(--border); padding:10px 14px; border-radius:var(--radius-sm); margin-bottom:10px; background:var(--bg-subtle);">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:var(--status-red); font-size:12.5px;">${c.match_type}</strong>
                <span style="font-family:var(--font-mono); font-weight:700; color:var(--saffron-600);">${(c.similarity_score || 100).toFixed(1)}% Match</span>
              </div>
              <div style="font-size:12px; margin-top:6px; display:flex; align-items:center; gap:8px; background:white; padding:8px 10px; border-radius:4px; border:1px solid #E2E8F0;">
                <a href="#/investigation/${encodeURIComponent(c.source_invoice_id)}" class="inv-link" style="display:inline; font-weight:700;">${c.source_invoice_id}</a>
                <span style="color:var(--saffron-600); font-weight:800;">&harr; (Duplicate Match) &harr;</span>
                <a href="#/investigation/${encodeURIComponent(c.matched_invoice_id)}" class="inv-link" style="display:inline; font-weight:700;">${c.matched_invoice_id}</a>
              </div>
              ${c.reasons && c.reasons.length > 0 ? `
                <div style="font-size:11px; color:var(--text-secondary); margin-top:4px; font-style:italic;">
                  Match Basis: ${c.reasons.join(', ')}
                </div>
              ` : ''}
            </div>
          `).join('');
        }
      }

      const anomEl = document.getElementById('anomList');
      if (anomEl) {
        if (!anomsResp.findings || anomsResp.findings.length === 0) {
          anomEl.innerHTML = `<div class="empty-state"><p>No statistical anomalies found.</p></div>`;
        } else {
          anomEl.innerHTML = anomsResp.findings.slice(0, 10).map(a => {
            const dimText = (a.dimension || a.anomaly_type || 'VALUE_ANOMALY').replace(/_/g, ' ');
            const lvlText = a.level || a.severity || 'HIGH';
            const expText = (a.evidence && (a.evidence.explanation || a.evidence.reason)) || a.explanation || `Statistical anomaly detected in ${dimText.toLowerCase()} (Score: ${a.score || 0}/100).`;

            return `
              <div style="border:1px solid var(--border); padding:10px 14px; border-radius:var(--radius-sm); margin-bottom:8px; background:var(--bg-subtle);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                  <strong style="color:var(--status-red); font-size:12.5px;">${dimText}</strong>
                  <span class="risk-tag ${lvlText.toLowerCase()}">${lvlText}</span>
                </div>
                <div style="font-size:12px; color:var(--text-primary); margin-top:2px;">
                  <a href="#/investigation/${a.invoice_id}" class="inv-link" style="display:inline; font-weight:700;">${a.invoice_id}</a>: ${expText}
                </div>
              </div>
            `;
          }).join('');
        }
      }
    } catch (err) {
      console.error(err);
    }
  }
}

window.DeepDivesView = DeepDivesView;
