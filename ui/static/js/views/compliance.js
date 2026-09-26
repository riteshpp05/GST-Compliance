/**
 * UC15 GST Compliance Investigation Platform — Compliance Explorer View
 */

class ComplianceView {
  constructor(container) {
    this.container = container;
    this.invoices = [];
    this.filtered = [];
    this.filters = {
      search: '',
      status: 'ALL',
      exposure: 'ALL',
    };
    this.sortCol = 'failed_gate_count';
    this.sortAsc = false;
    this.page = 1;
    this.pageSize = 10;
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Invoice Audit Center</h1>
          <p class="page-subtitle">Monitor transaction compliance status and inspect invoices</p>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-outline" id="btnExportCsv" onclick="window.complianceView.exportCsv()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Export Invoices
          </button>
        </div>
      </div>

      <!-- 3 Summary Status KPI Boxes (Approved, Needs Review, Blocked) -->
      <div class="kpi-grid" style="display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin-bottom:20px;">
        <!-- APPROVED BOX -->
        <div class="stat-card" id="kpiBoxApproved" onclick="window.complianceView.filterByKpi('COMPLIANT')" 
             style="cursor:pointer; border:1px solid #10B981; border-left:4px solid #10B981; padding:16px 20px; border-radius:8px; background:var(--card); transition:all 0.2s ease; position:relative; box-shadow:0 1px 3px rgba(0,0,0,0.05);"
             title="Click to filter by Approved transactions">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:#059669;">Approved</span>
            <span style="display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; background:#D1FAE5; color:#059669;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            </span>
          </div>
          <div style="display:flex; align-items:baseline; gap:8px; margin-top:8px;">
            <span id="kpiCountApproved" style="font-size:28px; font-weight:800; font-family:var(--font-mono); color:var(--text-primary);">0</span>
            <span style="font-size:12px; color:var(--text-secondary);">invoices</span>
          </div>
          <div style="font-size:11.5px; color:#059669; margin-top:4px; font-weight:500;">Ready for GST filing &amp; ITC claim</div>
        </div>

        <!-- NEEDS REVIEW BOX -->
        <div class="stat-card" id="kpiBoxNeedsReview" onclick="window.complianceView.filterByKpi('NEEDS_REVIEW')"
             style="cursor:pointer; border:1px solid #F59E0B; border-left:4px solid #F59E0B; padding:16px 20px; border-radius:8px; background:var(--card); transition:all 0.2s ease; position:relative; box-shadow:0 1px 3px rgba(0,0,0,0.05);"
             title="Click to filter by Needs Review transactions">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:#D97706;">Needs Review</span>
            <span style="display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; background:#FEF3C7; color:#D97706;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </span>
          </div>
          <div style="display:flex; align-items:baseline; gap:8px; margin-top:8px;">
            <span id="kpiCountNeedsReview" style="font-size:28px; font-weight:800; font-family:var(--font-mono); color:var(--text-primary);">0</span>
            <span style="font-size:12px; color:var(--text-secondary);">invoices</span>
          </div>
          <div style="font-size:11.5px; color:#D97706; margin-top:4px; font-weight:500;">Warnings &amp; reconciliation items</div>
        </div>

        <!-- BLOCKED BOX -->
        <div class="stat-card" id="kpiBoxBlocked" onclick="window.complianceView.filterByKpi('NON_COMPLIANT')"
             style="cursor:pointer; border:1px solid #EF4444; border-left:4px solid #EF4444; padding:16px 20px; border-radius:8px; background:var(--card); transition:all 0.2s ease; position:relative; box-shadow:0 1px 3px rgba(0,0,0,0.05);"
             title="Click to filter by Blocked transactions">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:#DC2626;">Blocked</span>
            <span style="display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; background:#FEE2E2; color:#DC2626;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
            </span>
          </div>
          <div style="display:flex; align-items:baseline; gap:8px; margin-top:8px;">
            <span id="kpiCountBlocked" style="font-size:28px; font-weight:800; font-family:var(--font-mono); color:var(--text-primary);">0</span>
            <span style="font-size:12px; color:var(--text-secondary);">invoices</span>
          </div>
          <div style="font-size:11.5px; color:#DC2626; margin-top:4px; font-weight:500;">Statutory gate failure &amp; held from filing</div>
        </div>
      </div>

      <!-- Streamlined Filter & Search Toolbar -->
      <div class="filter-bar" style="gap:12px; display:flex; justify-content:center; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
        <div class="search-box" style="flex:1; max-width:380px;">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" id="searchInput" placeholder="Search Invoice ID, Vendor, Customer, GSTIN..." value="${this.filters.search}">
        </div>

        <select class="filter-select" id="statusFilter" style="max-width:220px;">
          <option value="ALL">All Compliance Statuses</option>
          <option value="COMPLIANT">Approved</option>
          <option value="NEEDS_REVIEW">Needs Review</option>
          <option value="NON_COMPLIANT">Blocked (Non-Compliant)</option>
        </select>

        <button class="btn btn-outline" id="btnResetFilters" style="padding:6px 14px; font-size:11.5px;" onclick="window.complianceView.resetFilters()">
          Clear Filters
        </button>
      </div>

      <!-- Active Filter Summary & Result Count -->
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; font-size:12px; color:var(--text-secondary);">
        <div>
          Showing <strong id="filterResultCount" style="color:var(--text-primary); font-family:var(--font-mono);">0</strong> of <strong id="filterTotalCount" style="color:var(--text-primary); font-family:var(--font-mono);">0</strong> transactions
        </div>
        <div id="activeFilterTags" style="display:flex; gap:6px; flex-wrap:wrap;"></div>

      </div>

      <!-- Clean Data Table -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th class="sortable" style="text-align:left; padding-left:20px;" onclick="window.complianceView.sort('invoice_no')">Invoice ID</th>
              <th class="sortable" style="text-align:left;" onclick="window.complianceView.sort('invoice_date')">Date</th>
              <th class="sortable" style="text-align:left;" onclick="window.complianceView.sort('counterparty_name')">Counterparty / Vendor</th>
              <th class="sortable" style="text-align:right; padding-right:24px;" onclick="window.complianceView.sort('total_amt')">Invoice Value</th>
              <th class="sortable" style="text-align:center;" onclick="window.complianceView.sort('status')">Compliance Status</th>
              <th style="text-align:center;">Action</th>
            </tr>
          </thead>
          <tbody id="complianceTableBody">
            <tr><td colspan="6" style="text-align:center; padding:30px;"><div class="skeleton" style="height:200px;"></div></td></tr>
          </tbody>
        </table>

        <div class="pagination-bar" id="paginationBar">
          <div>Page <span id="currentPage">1</span> of <span id="totalPages">1</span></div>
          <div class="pagination-controls">
            <button class="page-btn" id="btnPrevPage" onclick="window.complianceView.changePage(-1)">&larr; Previous</button>
            <button class="page-btn" id="btnNextPage" onclick="window.complianceView.changePage(1)">Next &rarr;</button>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadInvoices();
  }

  bindEvents() {
    const search = document.getElementById('searchInput');
    if (search) {
      search.addEventListener('input', (e) => {
        this.filters.search = e.target.value.trim().toLowerCase();
        this.page = 1;
        this.applyFilters();
      });
    }

    const statusSel = document.getElementById('statusFilter');
    if (statusSel) {
      statusSel.addEventListener('change', (e) => {
        this.filters.status = e.target.value;
        this.page = 1;
        this.applyFilters();
      });
    }

    const riskSel = document.getElementById('riskFilter');
    if (riskSel) {
      riskSel.addEventListener('change', (e) => {
        this.filters.riskLevel = e.target.value;
        this.page = 1;
        this.applyFilters();
      });
    }

    const expSel = document.getElementById('exposureFilter');
    if (expSel) {
      expSel.addEventListener('change', (e) => {
        this.filters.exposure = e.target.value;
        this.page = 1;
        this.applyFilters();
      });
    }
  }

  async loadInvoices() {
    try {
      this.invoices = await window.gstApi.getLatestResults();
      this.updateKpiCards();
      this.applyFilters();
    } catch (err) {
      const tbody = document.getElementById('complianceTableBody');
      if (tbody) {
        tbody.innerHTML = `
          <tr><td colspan="8" style="text-align:center; padding:40px; color:var(--status-red);">
            Unable to load compliance records. Click "Run Agent" if no analysis has been executed yet.
          </td></tr>
        `;
      }
    }
  }

  updateKpiCards() {
    let approved = 0;
    let needsReview = 0;
    let blocked = 0;

    for (const inv of (this.invoices || [])) {
      const st = String(inv.status || '').toUpperCase();
      if (st === 'COMPLIANT' || st === 'APPROVED' || inv.approval_status === 'APPROVED') {
        approved++;
      } else if (st === 'NEEDS_REVIEW' || st === 'REVIEW_REQUIRED') {
        needsReview++;
      } else if (st === 'NON_COMPLIANT' || st === 'BLOCKED' || st === 'REJECTED') {
        blocked++;
      } else {
        if (inv.failed_gate_count > 0) blocked++;
        else approved++;
      }
    }

    const appEl = document.getElementById('kpiCountApproved');
    const nrEl = document.getElementById('kpiCountNeedsReview');
    const blkEl = document.getElementById('kpiCountBlocked');

    if (appEl) appEl.textContent = approved;
    if (nrEl) nrEl.textContent = needsReview;
    if (blkEl) blkEl.textContent = blocked;

    this.updateActiveKpiHighlight();
  }

  filterByKpi(status) {
    if (this.filters.status === status) {
      this.filters.status = 'ALL';
    } else {
      this.filters.status = status;
    }
    const statusSel = document.getElementById('statusFilter');
    if (statusSel) statusSel.value = this.filters.status;

    this.page = 1;
    this.applyFilters();
  }

  updateActiveKpiHighlight() {
    const boxApp = document.getElementById('kpiBoxApproved');
    const boxNr = document.getElementById('kpiBoxNeedsReview');
    const boxBlk = document.getElementById('kpiBoxBlocked');

    if (boxApp) {
      boxApp.style.boxShadow = this.filters.status === 'COMPLIANT' ? '0 0 0 2px #10B981, 0 4px 12px rgba(16,185,129,0.2)' : 'none';
      boxApp.style.transform = this.filters.status === 'COMPLIANT' ? 'translateY(-2px)' : 'none';
    }
    if (boxNr) {
      boxNr.style.boxShadow = this.filters.status === 'NEEDS_REVIEW' ? '0 0 0 2px #F59E0B, 0 4px 12px rgba(245,158,11,0.2)' : 'none';
      boxNr.style.transform = this.filters.status === 'NEEDS_REVIEW' ? 'translateY(-2px)' : 'none';
    }
    if (boxBlk) {
      boxBlk.style.boxShadow = this.filters.status === 'NON_COMPLIANT' ? '0 0 0 2px #EF4444, 0 4px 12px rgba(239,68,68,0.2)' : 'none';
      boxBlk.style.transform = this.filters.status === 'NON_COMPLIANT' ? 'translateY(-2px)' : 'none';
    }
  }


  applyFilters() {
    this.filtered = this.invoices.filter(inv => {
      // 1. Text Search
      if (this.filters.search) {
        const q = this.filters.search;
        const matchNo = (inv.invoice_no || '').toLowerCase().includes(q);
        const matchName = (inv.counterparty_name || '').toLowerCase().includes(q);
        const matchGstin = (inv.counterparty_gstin || '').toLowerCase().includes(q);
        const matchHsn = (inv.hsn_code || '').toLowerCase().includes(q);
        if (!matchNo && !matchName && !matchGstin && !matchHsn) return false;
      }

      // 2. Compliance Status
      if (this.filters.status !== 'ALL' && inv.status !== this.filters.status) {
        return false;
      }

      return true;
    });

    // Apply Sorting
    this.filtered.sort((a, b) => {
      let vA = a[this.sortCol];
      let vB = b[this.sortCol];

      if (vA === undefined || vA === null) vA = '';
      if (vB === undefined || vB === null) vB = '';

      if (typeof vA === 'number' && typeof vB === 'number') {
        return this.sortAsc ? vA - vB : vB - vA;
      }
      const strA = String(vA).toLowerCase();
      const strB = String(vB).toLowerCase();
      if (strA < strB) return this.sortAsc ? -1 : 1;
      if (strA > strB) return this.sortAsc ? 1 : -1;
      return 0;
    });

    this.renderTable();
    this.updateActiveKpiHighlight();
  }

  sort(col) {
    if (this.sortCol === col) {
      this.sortAsc = !this.sortAsc;
    } else {
      this.sortCol = col;
      this.sortAsc = false; // default descending
    }
    this.applyFilters();
  }

  changePage(delta) {
    const maxPage = Math.ceil(this.filtered.length / this.pageSize) || 1;
    this.page = Math.max(1, Math.min(maxPage, this.page + delta));
    this.renderTable();
  }

  resetFilters() {
    this.filters = {
      search: '',
      status: 'ALL',
    };
    const search = document.getElementById('searchInput');
    if (search) search.value = '';
    const status = document.getElementById('statusFilter');
    if (status) status.value = 'ALL';

    this.page = 1;
    this.applyFilters();
    this.updateActiveKpiHighlight();
  }

  renderTable() {
    const tbody = document.getElementById('complianceTableBody');
    const resCount = document.getElementById('filterResultCount');
    const totCount = document.getElementById('filterTotalCount');
    const curPageEl = document.getElementById('currentPage');
    const totPageEl = document.getElementById('totalPages');
    const prevBtn = document.getElementById('btnPrevPage');
    const nextBtn = document.getElementById('btnNextPage');

    if (!tbody) return;

    if (resCount) resCount.textContent = this.filtered.length;
    if (totCount) totCount.textContent = this.invoices.length;

    const totalPages = Math.ceil(this.filtered.length / this.pageSize) || 1;
    if (curPageEl) curPageEl.textContent = this.page;
    if (totPageEl) totPageEl.textContent = totalPages;
    if (prevBtn) prevBtn.disabled = this.page <= 1;
    if (nextBtn) nextBtn.disabled = this.page >= totalPages;

    if (this.filtered.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="6" class="empty-state" style="text-align:center;">
          <h3>No transactions match your search filters</h3>
          <p>Try clearing filters or search terms to view all compliance records.</p>
        </td></tr>
      `;
      return;
    }

    const startIdx = (this.page - 1) * this.pageSize;
    const pageItems = this.filtered.slice(startIdx, startIdx + this.pageSize);

    tbody.innerHTML = pageItems.map(inv => {
      const statusBadge = this.getStatusBadge(inv.status);

      return `
        <tr class="compliance-row">
          <td style="text-align:left; padding-left:20px; white-space:nowrap;">
            <div style="display:flex; align-items:center; gap:8px;">
              <a href="#/investigation/${inv.invoice_no}" class="inv-link" style="font-weight:700; font-family:var(--font-mono); font-size:13px;">
                ${inv.invoice_no}
              </a>
            </div>
          </td>
          <td style="text-align:left; white-space:nowrap; font-family:var(--font-mono); font-size:12.5px; color:var(--text-secondary);">
            ${inv.invoice_date || '—'}
          </td>
          <td style="text-align:left;">
            <div style="display:flex; flex-direction:column; gap:2px; max-width:280px;">
              <span title="${inv.counterparty_name || '—'}" style="font-weight:600; color:var(--text-primary); font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${inv.counterparty_name || '—'}
              </span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); letter-spacing:0.3px;">
                ${inv.counterparty_gstin || '—'}
              </span>
            </div>
          </td>
          <td style="text-align:right; font-family:var(--font-mono); white-space:nowrap; font-weight:700; color:var(--text-primary); font-size:13px; padding-right:24px;">
            ${GSTCharts.formatCurrency(inv.total_amt)}
          </td>
          <td style="text-align:center; white-space:nowrap;">${statusBadge}</td>
          <td style="text-align:center; white-space:nowrap;">
            <a href="#/investigation/${inv.invoice_no}" class="btn btn-inspect">
              <span>Inspect</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </a>
          </td>
        </tr>
      `;
    }).join('');
  }

  renderGateDots(gates) {
    if (!gates || gates.length === 0) return '<span style="color:var(--text-muted);">&mdash;</span>';

    return `
      <div class="gate-dots-row">
        ${gates.map(g => {
          let cls = 'na';
          if (g.status === 'PASS') cls = 'pass';
          else if (g.status === 'FAIL') cls = 'fail';
          else if (g.status === 'NEEDS_REVIEW') cls = 'review';

          return `
            <div class="gate-dot ${cls}" title="Gate ${g.gate_no}: ${g.name} &mdash; ${g.status}&#10;${g.detail || ''}">
              G${g.gate_no}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  renderSignals(inv) {
    const badges = [];
    if (inv.has_duplicate) {
      badges.push('<span class="badge-status info" style="padding:2px 6px; font-size:9px;" title="Duplicate invoice detected">DUP</span>');
    }
    if (inv.has_anomaly) {
      badges.push('<span class="badge-status non-compliant" style="padding:2px 6px; font-size:9px;" title="Statistical outlier detected">ANOM</span>');
    }
    if (badges.length === 0) {
      return '<span style="color:var(--text-muted); font-size:11px;">&mdash;</span>';
    }
    return `<div style="display:flex; gap:4px;">${badges.join('')}</div>`;
  }

  getStatusBadge(status) {
    if (status === 'COMPLIANT') {
      return `<span class="badge-status compliant"><span class="status-indicator-dot"></span>Approved</span>`;
    } else if (status === 'NEEDS_REVIEW') {
      return `<span class="badge-status needs-review"><span class="status-indicator-dot"></span>Needs Review</span>`;
    } else {
      return `<span class="badge-status non-compliant"><span class="status-indicator-dot"></span>Blocked</span>`;
    }
  }

  getRiskTag(level, score) {
    const lvl = (level || 'LOW').toLowerCase();
    return `<span class="risk-tag ${lvl}">${level || 'LOW'} Priority</span>`;
  }

  exportCsv() {
    if (!this.filtered || this.filtered.length === 0) {
      alert('No invoices to export.');
      return;
    }

    const headers = ['Invoice No', 'Date', 'Direction', 'Counterparty Name', 'Counterparty GSTIN', 'Taxable Value', 'Total Amount', 'Compliance Status', 'Risk Score', 'Risk Level', 'Priority', 'Potential Exposure'];
    const rows = this.filtered.map(i => [
      i.invoice_no,
      i.invoice_date,
      i.direction,
      `"${(i.counterparty_name || '').replace(/"/g, '""')}"`,
      i.counterparty_gstin,
      i.taxable_value_inr,
      i.total_amt,
      i.status,
      i.risk_score,
      i.risk_level,
      i.priority,
      i.potential_exposure || 0,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `GST_Compliance_Export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

window.ComplianceView = ComplianceView;
