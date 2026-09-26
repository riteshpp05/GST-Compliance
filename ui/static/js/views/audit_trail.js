/**
 * UC15 GST Compliance Investigation Platform — Audit Trail & Decision Ledger View
 * Displays immutable chronological audit history for all approvals, rejections, and corrections.
 */

class AuditTrailView {
  constructor(container) {
    this.container = container;
    this.logs = [];
    this.filtered = [];
    this.filters = {
      search: '',
      action: 'ALL',
    };
    this.page = 1;
    this.pageSize = 15;
  }

  async render() {
    this.container.innerHTML = `
      <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px;">
        <div>
          <h1 class="page-title" style="font-size:1.45rem; font-weight:800; margin:0 0 6px 0;">Audit Trail & Decision Ledger</h1>
          <p class="page-subtitle" style="font-size:0.875rem; color:var(--text-secondary); margin:0;">
            Immutable chronological record of all approvals, rejections, inline corrections, and auditor actions
          </p>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-outline" id="btnExportAuditCsv" onclick="window.auditTrailView.exportCsv()" style="display:flex; align-items:center; gap:8px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Export Ledger
          </button>
        </div>
      </div>

      <!-- Filter Controls -->
      <div class="filter-card" style="background:var(--card); border:1px solid var(--border); border-radius:8px; padding:16px 20px; margin-bottom:20px; display:flex; gap:16px; align-items:center; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px; position:relative;">
          <input type="text" id="auditSearchInput" placeholder="Search by Invoice ID, User, or Reason..." 
                 style="width:100%; padding:8px 12px; border-radius:6px; border:1px solid var(--border); background:var(--bg); color:var(--text-primary); font-size:13px;">
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <label style="font-size:12px; font-weight:600; color:var(--text-secondary); text-transform:uppercase;">Action:</label>
          <select id="auditActionFilter" style="padding:8px 12px; border-radius:6px; border:1px solid var(--border); background:var(--bg); color:var(--text-primary); font-size:13px;">
            <option value="ALL">All Actions</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Blocked / Rejected</option>
            <option value="CORRECTION">Correction Applied</option>
          </select>
        </div>
      </div>

      <!-- Audit Events Table -->
      <div class="data-table-container" style="background:var(--card); border:1px solid var(--border); border-radius:8px; overflow:hidden;">
        <table class="data-table" style="width:100%; border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid var(--border); background:var(--bg-subtle, rgba(0,0,0,0.02));">
              <th style="text-align:left; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Timestamp</th>
              <th style="text-align:left; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Invoice ID</th>
              <th style="text-align:center; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Action Taken</th>
              <th style="text-align:left; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Auditor / User</th>
              <th style="text-align:left; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Reason / Justification Note</th>
              <th style="text-align:center; padding:12px 18px; font-size:11.5px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Dossier</th>
            </tr>
          </thead>
          <tbody id="auditTableBody">
            <tr><td colspan="6" style="text-align:center; padding:30px;"><div class="skeleton" style="height:120px;"></div></td></tr>
          </tbody>
        </table>

        <div class="pagination-bar" id="auditPaginationBar" style="display:flex; justify-content:space-between; align-items:center; padding:12px 20px; border-top:1px solid var(--border); font-size:12.5px; color:var(--text-secondary);">
          <div>Showing <span id="auditVisibleCount">0</span> of <span id="auditTotalCount">0</span> audit entries</div>
          <div style="display:flex; gap:8px;">
            <button class="page-btn" id="btnPrevAuditPage" onclick="window.auditTrailView.changePage(-1)" style="padding:4px 10px; border-radius:4px; border:1px solid var(--border); background:var(--card); cursor:pointer;">&larr; Previous</button>
            <button class="page-btn" id="btnNextAuditPage" onclick="window.auditTrailView.changePage(1)" style="padding:4px 10px; border-radius:4px; border:1px solid var(--border); background:var(--card); cursor:pointer;">Next &rarr;</button>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadAuditLogs();
  }

  bindEvents() {
    const search = document.getElementById('auditSearchInput');
    if (search) {
      search.addEventListener('input', (e) => {
        this.filters.search = e.target.value.trim().toLowerCase();
        this.page = 1;
        this.applyFilters();
      });
    }

    const actionSel = document.getElementById('auditActionFilter');
    if (actionSel) {
      actionSel.addEventListener('change', (e) => {
        this.filters.action = e.target.value;
        this.page = 1;
        this.applyFilters();
      });
    }
  }

  async loadAuditLogs() {
    try {
      const res = await fetch('/api/audit/logs?limit=500');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.logs = Array.isArray(data) ? data : (data.logs || []);
      this.applyFilters();
    } catch (err) {
      const tbody = document.getElementById('auditTableBody');
      if (tbody) {
        tbody.innerHTML = `
          <tr><td colspan="6" style="text-align:center; padding:40px; color:var(--status-red);">
            Unable to load audit logs: ${err.message}
          </td></tr>
        `;
      }
    }
  }

  applyFilters() {
    this.filtered = this.logs.filter(entry => {
      if (this.filters.search) {
        const q = this.filters.search;
        const inv = String(entry.invoice_no || '').toLowerCase();
        const actor = String(entry.actor || '').toLowerCase();
        const reason = String(entry.reason || '').toLowerCase();
        if (!inv.includes(q) && !actor.includes(q) && !reason.includes(q)) {
          return false;
        }
      }

      if (this.filters.action !== 'ALL') {
        const ev = String(entry.event_type || '').toUpperCase();
        if (this.filters.action === 'APPROVED' && ev !== 'APPROVED') return false;
        if (this.filters.action === 'REJECTED' && ev !== 'REJECTED' && ev !== 'BLOCKED') return false;
        if (this.filters.action === 'CORRECTION' && ev !== 'CORRECTION') return false;
      }

      return true;
    });

    this.renderRows();
  }

  renderRows() {
    const tbody = document.getElementById('auditTableBody');
    const visCount = document.getElementById('auditVisibleCount');
    const totCount = document.getElementById('auditTotalCount');
    const prevBtn = document.getElementById('btnPrevAuditPage');
    const nextBtn = document.getElementById('btnNextAuditPage');

    if (!tbody) return;

    if (totCount) totCount.textContent = this.logs.length;
    if (visCount) visCount.textContent = this.filtered.length;

    const totalPages = Math.ceil(this.filtered.length / this.pageSize) || 1;
    if (prevBtn) prevBtn.disabled = this.page <= 1;
    if (nextBtn) nextBtn.disabled = this.page >= totalPages;

    if (this.filtered.length === 0) {
      tbody.innerHTML = `
        <tr><td colspan="6" style="text-align:center; padding:40px; color:var(--text-secondary);">
          <div style="font-weight:600; font-size:14px; margin-bottom:4px;">No Audit Events Found</div>
          <div style="font-size:12px;">Approve, block, or correct invoices in the Invoice Audit Center to record persistent decisions.</div>
        </td></tr>
      `;
      return;
    }

    const startIdx = (this.page - 1) * this.pageSize;
    const pageItems = this.filtered.slice(startIdx, startIdx + this.pageSize);

    tbody.innerHTML = pageItems.map(row => {
      let badge = '';
      const ev = String(row.event_type || '').toUpperCase();
      if (ev === 'APPROVED') {
        badge = '<span class="badge-status compliant" style="padding:3px 10px; font-weight:700; font-size:11px;">APPROVED</span>';
      } else if (ev === 'REJECTED' || ev === 'BLOCKED') {
        badge = '<span class="badge-status non-compliant" style="padding:3px 10px; font-weight:700; font-size:11px;">BLOCKED</span>';
      } else if (ev === 'CORRECTION') {
        badge = '<span class="badge-status needs-review" style="padding:3px 10px; font-weight:700; font-size:11px; background:#EFF6FF; color:#2563EB; border-color:#93C5FD;">CORRECTED</span>';
      } else {
        badge = `<span class="badge-status" style="padding:3px 10px; font-size:11px;">${ev}</span>`;
      }

      const formattedDate = row.timestamp ? new Date(row.timestamp).toLocaleString('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }) : '—';

      return `
        <tr style="border-bottom:1px solid var(--border);">
          <td style="padding:12px 18px; font-family:var(--font-mono); font-size:12px; color:var(--text-secondary); white-space:nowrap;">
            ${formattedDate}
          </td>
          <td style="padding:12px 18px; font-family:var(--font-mono); font-weight:700; font-size:13px;">
            <a href="#/investigation/${row.invoice_no}" class="inv-link" style="color:var(--primary); text-decoration:none;">
              ${row.invoice_no}
            </a>
          </td>
          <td style="text-align:center; padding:12px 18px;">
            ${badge}
          </td>
          <td style="padding:12px 18px; font-size:13px; font-weight:600; color:var(--text-primary);">
            ${row.actor || 'System'}
          </td>
          <td style="padding:12px 18px; font-size:12.5px; color:var(--text-secondary); max-width:320px;">
            ${row.reason || 'No comment recorded'}
          </td>
          <td style="text-align:center; padding:12px 18px;">
            <a href="#/investigation/${row.invoice_no}" class="btn btn-outline" style="padding:4px 10px; font-size:11px; text-decoration:none;">
              View &rarr;
            </a>
          </td>
        </tr>
      `;
    }).join('');
  }

  changePage(delta) {
    const totalPages = Math.ceil(this.filtered.length / this.pageSize) || 1;
    this.page = Math.max(1, Math.min(totalPages, this.page + delta));
    this.renderRows();
  }

  exportCsv() {
    if (!this.filtered || this.filtered.length === 0) {
      alert('No audit events to export.');
      return;
    }
    const headers = ['Timestamp', 'Invoice No', 'Event Type', 'Action', 'Actor', 'Reason', 'Status'];
    const rows = this.filtered.map(r => [
      r.timestamp,
      r.invoice_no,
      r.event_type,
      `"${(r.action_label || '').replace(/"/g, '""')}"`,
      `"${(r.actor || '').replace(/"/g, '""')}"`,
      `"${(r.reason || '').replace(/"/g, '""')}"`,
      r.status,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join('\n'))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `GST_Audit_Trail_Export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

window.AuditTrailView = AuditTrailView;
