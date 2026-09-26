/**
 * UC15 GST Compliance Investigation Platform — Data Ingestion & Dataset Management View
 * Renders file uploader for CSV, Excel (.xlsx), and JSON datasets, ingestion metrics,
 * and registered datasets directory table with active dataset switching.
 */

class IngestionView {
  constructor(container) {
    this.container = container;
    this.datasets = [];
    this.activeDatasetId = null;
    this.lastUploadResult = null;
  }

  async render() {
    this.container.innerHTML = `
      <div class="view-header">
        <div>
          <div class="breadcrumb">Compliance Intelligence / Integration &amp; Ingestion</div>
          <h1 class="page-title">Data Integration &amp; Ingestion Workspace</h1>
          <p class="page-subtitle">Direct SAP S/4HANA live ERP connector status and ad-hoc multi-format invoice dataset ingestion (Excel, CSV, JSON).</p>
        </div>
        <div class="header-actions">
          <a href="/api/datasets/templates/csv" class="btn btn-secondary" download>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Sample CSV Template
          </a>
        </div>
      </div>

      <!-- Live SAP S/4HANA Connector Card -->
      <div class="detail-card" style="margin-bottom: 1.5rem; background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color:#FFFFFF; border: 1px solid #334155;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
          <div>
            <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.3rem;">
              <span class="badge" style="background:#2563EB; color:#FFFFFF; font-weight:700; font-size:0.75rem; text-transform:uppercase;">Primary System Mode</span>
              <span class="badge" style="background:#10B981; color:#FFFFFF; font-weight:700; font-size:0.75rem;">● Live SAP S/4HANA Ready</span>
            </div>
            <h3 style="margin:0; font-size:1.1rem; font-weight:700; color:#F8FAFC;">SAP S/4HANA Direct ERP Integration (OData / CDS Views)</h3>
            <p style="margin:0.3rem 0 0 0; font-size:0.85rem; color:#94A3B8;">
              Canonical SAP FI (BKPF/BSEG) &amp; SD (VBRK/VBRP) connector. Live invoice postings automatically sync into the GST Statutory Audit Engine.
            </p>
          </div>
          <div style="display:flex; gap:1rem; font-family:var(--font-mono); font-size:0.8rem; background:rgba(255,255,255,0.06); padding:0.8rem 1.2rem; border-radius:6px; border:1px solid rgba(255,255,255,0.1);">
            <div>
              <div style="color:#94A3B8; font-size:0.7rem; text-transform:uppercase;">Company Code</div>
              <strong style="color:#38BDF8;">BUKRS: 1000</strong>
            </div>
            <div style="border-left:1px solid rgba(255,255,255,0.1); padding-left:1rem;">
              <div style="color:#94A3B8; font-size:0.7rem; text-transform:uppercase;">Live Adapter Status</div>
              <strong style="color:#34D399;">OData Active (2026)</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- Ingestion & Upload Grid -->
      <div class="grid-2col" style="display:grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
        
        <!-- Upload Card -->
        <div class="detail-card">
          <div class="card-header">
            <h3 class="card-title" style="display:flex; align-items:center; gap:0.5rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              Ad-Hoc Dataset File Upload
            </h3>
            <span class="badge badge-info">Offline / Ad-hoc Ingestion</span>
          </div>
          <form id="datasetUploadForm" style="display:flex; flex-direction:column; gap:1rem;">
            <div class="form-group">
              <label style="font-size:0.85rem; font-weight:600; color:var(--text-muted); display:block; margin-bottom:0.4rem;">Dataset Title (Optional)</label>
              <input type="text" id="datasetCustomName" class="form-control" placeholder="e.g. Q3 Vendor Invoices 2026" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-secondary); color:var(--text-primary);" />
            </div>

            <!-- Drag Drop Dropzone -->
            <div id="dropZone" style="border: 2px dashed var(--border-color); border-radius: 8px; padding: 2rem; text-align: center; cursor: pointer; transition: background 0.2s, border-color 0.2s;" onclick="document.getElementById('fileInput').click()">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" stroke-width="1.8" style="margin-bottom:0.5rem;"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M12 12v9"/><path d="m16 16-4-4-4 4"/></svg>
              <p style="font-weight:600; margin:0.3rem 0; color:var(--text-primary);">Click or Drag & Drop File to Upload</p>
              <p style="font-size:0.8rem; color:var(--text-muted); margin:0;">Supports <strong>.csv</strong>, <strong>.xlsx</strong>, and <strong>.json</strong> files (Max 20MB)</p>
              <input type="file" id="fileInput" accept=".csv, .xlsx, .xls, .json" style="display:none;" />
              <div id="selectedFileInfo" style="margin-top:0.8rem; font-weight:600; color:var(--accent-blue); display:none;"></div>
            </div>

            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:0.5rem;">
              <label style="display:flex; align-items:center; gap:0.5rem; font-size:0.85rem; color:var(--text-primary); cursor:pointer;">
                <input type="checkbox" id="setActiveCheck" checked style="accent-color:var(--accent-blue);" />
                Automatically set as active dataset upon ingestion
              </label>
              <button type="submit" id="uploadSubmitBtn" class="btn btn-primary" style="padding:0.6rem 1.2rem;" disabled>
                Upload & Ingest
              </button>
            </div>
          </form>
        </div>

        <!-- Ingestion Report / Guidance Card -->
        <div class="detail-card">
          <div class="card-header">
            <h3 class="card-title" style="display:flex; align-items:center; gap:0.5rem;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--emerald-600)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              Validation & Schema Contract
            </h3>
            <span class="badge badge-success">Ingestion Engine 2.0</span>
          </div>

          <div id="ingestionReportContainer">
            <p style="font-size:0.88rem; color:var(--text-muted); line-height:1.5;">
              The Statutory Ingestion Engine parses your uploaded files through standard normalizers, verifying required GST invoice schema fields:
            </p>
            <ul style="font-size:0.85rem; color:var(--text-primary); margin:0.8rem 0; padding-left:1.2rem; line-height:1.6;">
              <li><strong>Invoice & Date</strong>: Unique Invoice ID and ISO Filing Period Date.</li>
              <li><strong>Counterparty Details</strong>: Name and 15-character GSTIN format.</li>
              <li><strong>Tax Precision Breakdown</strong>: Taxable Value, CGST, SGST, IGST, Total Value.</li>
              <li><strong>E-Way Bill & ITC Status</strong>: EWB Status and GSTR-2B ITC Match.</li>
            </ul>

            <div style="background:var(--bg-secondary); border-radius:6px; padding:1rem; border:1px solid var(--border-color); margin-top:1rem;">
              <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:0.5rem;">Supported Formats</div>
              <div style="display:flex; gap:0.5rem;">
                <span class="badge badge-info" style="font-family:var(--font-mono);">.CSV</span>
                <span class="badge badge-info" style="font-family:var(--font-mono);">.XLSX</span>
                <span class="badge badge-info" style="font-family:var(--font-mono);">.JSON</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Dataset Registry Directory -->
      <div class="detail-card">
        <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h3 class="card-title">Registered Dataset Directory</h3>
            <p class="card-subtitle" style="margin:0.2rem 0 0 0; font-size:0.85rem; color:var(--text-muted);">Manage registered datasets and toggle active statutory compliance dataset.</p>
          </div>
          <button id="refreshDatasetsBtn" class="btn btn-secondary" style="padding:0.4rem 0.8rem; font-size:0.8rem;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
            Refresh List
          </button>
        </div>

        <div id="datasetTableContainer" style="margin-top:1rem; overflow-x:auto;">
          <div style="text-align:center; padding:2rem; color:var(--text-muted);">Loading registered datasets...</div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.fetchDatasets();
  }

  bindEvents() {
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const selectedFileInfo = document.getElementById('selectedFileInfo');
    const uploadSubmitBtn = document.getElementById('uploadSubmitBtn');
    const uploadForm = document.getElementById('datasetUploadForm');
    const refreshBtn = document.getElementById('refreshDatasetsBtn');

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.fetchDatasets());
    }

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          const file = e.target.files[0];
          selectedFileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
          selectedFileInfo.style.display = 'block';
          uploadSubmitBtn.disabled = false;
        }
      });
    }

    if (dropZone) {
      ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropZone.style.background = 'var(--bg-secondary)';
          dropZone.style.borderColor = 'var(--accent-blue)';
        }, false);
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          dropZone.style.background = 'transparent';
          dropZone.style.borderColor = 'var(--border-color)';
        }, false);
      });

      dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files[0]) {
          fileInput.files = files;
          const file = files[0];
          selectedFileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
          selectedFileInfo.style.display = 'block';
          uploadSubmitBtn.disabled = false;
        }
      });
    }

    if (uploadForm) {
      uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        const customName = document.getElementById('datasetCustomName')?.value.trim() || '';
        const setActive = document.getElementById('setActiveCheck')?.checked ?? true;

        const formData = new FormData();
        formData.append('file', file);
        if (customName) formData.append('custom_name', customName);
        formData.append('set_active', setActive ? 'true' : 'false');

        uploadSubmitBtn.disabled = true;
        uploadSubmitBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Ingesting...`;

        try {
          const res = await window.gstApi.uploadDataset(formData);
          window.showToast(res.message || 'Dataset uploaded successfully!');
          this.lastUploadResult = res.dataset;
          this.renderUploadFeedback(res.dataset);
          
          // Reset form
          uploadForm.reset();
          selectedFileInfo.style.display = 'none';
          uploadSubmitBtn.disabled = true;
          uploadSubmitBtn.textContent = 'Upload & Ingest';

          // Refresh header and dataset list
          await this.fetchDatasets();
          if (window.gstApp && typeof window.gstApp.updateHeaderBadges === 'function') {
            window.gstApp.updateHeaderBadges();
          }
        } catch (err) {
          window.showToast(`Upload failed: ${err.message}`, 'error');
          uploadSubmitBtn.disabled = false;
          uploadSubmitBtn.textContent = 'Upload & Ingest';
        }
      });
    }
  }

  renderUploadFeedback(ds) {
    const el = document.getElementById('ingestionReportContainer');
    if (!el) return;

    el.innerHTML = `
      <div style="background:var(--emerald-50); border:1px solid var(--emerald-300); border-radius:8px; padding:1.2rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
          <h4 style="margin:0; color:var(--emerald-900); font-size:1rem; display:flex; align-items:center; gap:0.4rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--emerald-600)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Ingestion Complete: ${ds.name}
          </h4>
          <span class="badge badge-success">${ds.status}</span>
        </div>

        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:0.8rem; margin-bottom:1rem;">
          <div style="background:white; padding:0.6rem; border-radius:6px; text-align:center; border:1px solid var(--border-color);">
            <div style="font-size:1.2rem; font-weight:700; color:var(--emerald-700);">${ds.invoice_count}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">Valid Invoices</div>
          </div>
          <div style="background:white; padding:0.6rem; border-radius:6px; text-align:center; border:1px solid var(--border-color);">
            <div style="font-size:1.2rem; font-weight:700; color:var(--accent-blue);">${ds.hsn_master_count}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">HSN Masters</div>
          </div>
          <div style="background:white; padding:0.6rem; border-radius:6px; text-align:center; border:1px solid var(--border-color);">
            <div style="font-size:1.2rem; font-weight:700; color:var(--indigo-600);">${ds.state_code_count}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">State Masters</div>
          </div>
        </div>

        <div style="margin-top:1rem; padding-top:0.8rem; border-top:1px dashed var(--emerald-200); display:flex; gap:0.8rem; align-items:center;">
          <button id="runPipelineAndRedirectBtn" class="btn btn-primary" style="flex:1; display:flex; align-items:center; justify-content:center; gap:0.5rem; padding:0.65rem 1rem; font-weight:600;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Execute Statutory Pipeline &amp; View Overview
          </button>
        </div>
      </div>
    `;

    const runBtn = document.getElementById('runPipelineAndRedirectBtn');
    if (runBtn) {
      runBtn.addEventListener('click', async () => {
        runBtn.disabled = true;
        runBtn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Executing S1&ndash;S9 Rules...`;
        try {
          if (window.gstApp && typeof window.gstApp.runAgent === 'function') {
            await window.gstApp.runAgent();
          } else {
            await window.gstApi.runAgent();
          }
          window.location.hash = '#/overview';
        } catch (err) {
          window.showToast(`Pipeline failed: ${err.message}`, 'error');
          runBtn.disabled = false;
          runBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg> Execute Statutory Pipeline &amp; View Overview`;
        }
      });
    }
  }

  async fetchDatasets() {
    const container = document.getElementById('datasetTableContainer');
    try {
      const res = await window.gstApi.getDatasets();
      this.datasets = res.datasets || [];
      this.activeDatasetId = res.active_dataset_id;

      this.renderDatasetsTable(container);
    } catch (err) {
      if (container) {
        container.innerHTML = `<div style="color:var(--rose-600); padding:1rem;">Failed to fetch datasets: ${err.message}</div>`;
      }
    }
  }

  renderDatasetsTable(container) {
    if (!container) return;
    if (this.datasets.length === 0) {
      container.innerHTML = `<div style="padding:1.5rem; text-align:center; color:var(--text-muted);">No datasets registered.</div>`;
      return;
    }

    const rowsHtml = this.datasets.map(d => {
      const isActive = d.is_active || d.id === this.activeDatasetId;
      const formatBadgeClass = d.file_format === 'CSV' ? 'badge-info' : (d.file_format === 'EXCEL' ? 'badge-success' : 'badge-warning');
      const formattedDate = new Date(d.upload_timestamp).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
      const sizeKb = (d.size_bytes / 1024).toFixed(1);

      return `
        <tr style="${isActive ? 'background: rgba(14, 165, 233, 0.04);' : ''}">
          <td style="text-align:center;">
            ${isActive ? '<span class="badge badge-success" style="font-weight:700;">ACTIVE</span>' : '<span class="badge" style="background:var(--slate-200); color:var(--slate-700);">INACTIVE</span>'}
          </td>
          <td>
            <div style="font-weight:600; color:var(--text-primary);">${d.name}</div>
            <div style="font-size:0.78rem; font-family:var(--font-mono); color:var(--text-muted);">${d.file_name}</div>
          </td>
          <td>
            <span class="badge ${formatBadgeClass}">${d.file_format}</span>
          </td>
          <td style="font-family:var(--font-mono); font-weight:600; text-align:center;">
            ${d.invoice_count}
          </td>
          <td style="font-size:0.82rem; color:var(--text-muted);">
            ${d.uploaded_by || 'User'}
          </td>
          <td style="font-size:0.82rem; color:var(--text-muted);">
            ${formattedDate} (${sizeKb} KB)
          </td>
          <td>
            <div style="display:flex; gap:0.5rem; align-items:center;">
              ${!isActive ? `
                <button class="btn btn-secondary btn-sm activate-ds-btn" data-id="${d.id}" style="padding:0.3rem 0.6rem; font-size:0.78rem;">
                  Activate Dataset
                </button>
              ` : '<span style="font-size:0.8rem; color:var(--emerald-600); font-weight:600;">Currently Active</span>'}
              
              ${d.is_deletable !== false ? `
                <button class="btn btn-secondary btn-sm delete-ds-btn" data-id="${d.id}" style="padding:0.3rem 0.6rem; font-size:0.78rem; color:var(--rose-600); border-color:var(--rose-200);">
                  Delete
                </button>
              ` : '<span class="badge" style="background:var(--slate-100); color:var(--slate-500); font-size:0.7rem;">SYSTEM LOCKED</span>'}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <table class="data-table" style="width:100%;">
        <thead>
          <tr>
            <th style="width:100px; text-align:center;">Status</th>
            <th>Dataset Title / File Name</th>
            <th>Format</th>
            <th style="text-align:center;">Invoices</th>
            <th>Ingested By</th>
            <th>Date & Size</th>
            <th style="width:200px;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    `;

    // Bind action buttons
    container.querySelectorAll('.activate-ds-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const dsId = e.currentTarget.getAttribute('data-id');
        if (!dsId) return;
        try {
          btn.disabled = true;
          btn.textContent = 'Activating...';
          const res = await window.gstApi.selectDataset(dsId);
          window.showToast(res.message || 'Dataset activated!');
          const activatedDs = this.datasets.find(d => d.id === dsId);
          if (activatedDs) this.renderUploadFeedback(activatedDs);
          await this.fetchDatasets();
          if (window.gstApp && typeof window.gstApp.updateHeaderBadges === 'function') {
            window.gstApp.updateHeaderBadges();
          }
        } catch (err) {
          window.showToast(`Failed to activate dataset: ${err.message}`, 'error');
          btn.disabled = false;
          btn.textContent = 'Activate Dataset';
        }
      });
    });

    container.querySelectorAll('.delete-ds-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const dsId = e.currentTarget.getAttribute('data-id');
        if (!dsId) return;
        if (!confirm('Are you sure you want to delete this custom dataset?')) return;
        try {
          const res = await window.gstApi.deleteDataset(dsId);
          window.showToast(res.message || 'Dataset deleted!');
          await this.fetchDatasets();
          if (window.gstApp && typeof window.gstApp.updateHeaderBadges === 'function') {
            window.gstApp.updateHeaderBadges();
          }
        } catch (err) {
          window.showToast(`Failed to delete dataset: ${err.message}`, 'error');
        }
      });
    });
  }
}

// Attach Singleton to Window
window.IngestionView = IngestionView;
