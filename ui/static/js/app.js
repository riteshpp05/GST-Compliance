/**
 * UC15 GST Compliance Investigation Platform — Main Application Controller
 * Initializes views, routes, global event listeners, sidebar toggles, and agent execution controls.
 */

class GSTApp {
  constructor() {
    this.mainContainer = document.getElementById('viewMount');
    this.overviewView = new OverviewView(this.mainContainer);
    this.complianceView = new ComplianceView(this.mainContainer);
    this.investigationsView = new InvestigationsView(this.mainContainer);
    this.invoiceDetailView = new InvoiceDetailView(this.mainContainer);
    this.deepDivesView = new DeepDivesView(this.mainContainer);
    this.aiAgentView = window.AIAgentView;
    this.caseWorkspaceView = new CaseWorkspaceView(this.mainContainer);
    this.auditTrailView = new AuditTrailView(this.mainContainer);

    window.complianceView = this.complianceView;
    window.investigationsView = this.investigationsView;
    window.auditTrailView = this.auditTrailView;
  }

  init() {
    // 1. Setup routes
    window.gstRouter.register('/overview', () => this.overviewView.render());
    window.gstRouter.register('/compliance', () => this.complianceView.render());
    window.gstRouter.register('/investigations', () => this.complianceView.render());
    window.gstRouter.register('/investigation/:id', (id) => this.invoiceDetailView.render(id));
    window.gstRouter.register('/workspace/:id', (caseId, subTab) => this.caseWorkspaceView.render(caseId, subTab));
    window.gstRouter.register('/cases/:id', (caseId, subTab) => this.caseWorkspaceView.render(caseId, subTab));
    window.gstRouter.register('/risk', () => this.complianceView.render());
    window.gstRouter.register('/financial', () => this.complianceView.render());
    window.gstRouter.register('/intelligence', () => this.complianceView.render());
    window.gstRouter.register('/ai_agent', () => this.aiAgentView ? this.aiAgentView.render(this.mainContainer) : window.AIAgentView.render(this.mainContainer));
    window.gstRouter.register('/audit_trail', () => this.auditTrailView.render());
    window.gstRouter.register('/history', () => this.auditTrailView.render());
    window.gstRouter.register('/case_management', () => window.location.hash = '#/compliance');
    window.gstRouter.register('/reconciliation', () => this.complianceView.render());
    window.gstRouter.register('/evidence', () => this.complianceView.render());

    // 2. Setup Sidebar Collapsing
    this.initSidebarToggle();

    // 3. Setup Global Command Search Bar
    this.initGlobalSearch();

    // 4. Setup Role Switcher, Dataset Selector & Environment Badge
    this.initRoleSelector();
    this.initDatasetSelector();
    this.initEnvironmentBadge();

    // 5. Global Run Agent Button
    const runBtn = document.getElementById('globalRunBtn');
    if (runBtn) {
      runBtn.addEventListener('click', () => this.runAgent());
    }

    // 6. Initial route trigger
    window.gstRouter.handleRoute();

    // 7. Update badge counts
    this.updateHeaderBadges();
  }

  initRoleSelector() {
    const select = document.getElementById('userRoleSelect');
    if (!select) return;

    const activeRole = sessionStorage.getItem('uc15_active_role') || 'INVESTIGATOR';
    select.value = activeRole;
    window.gstApi.setRoleProfile(activeRole);

    select.addEventListener('change', (e) => {
      const newRole = e.target.value;
      window.gstApi.setRoleProfile(newRole);
      window.showToast(`Role switched to ${newRole} (Headers updated)`);
      window.gstRouter.handleRoute();
    });
  }

  async initEnvironmentBadge() {
    const badge = document.getElementById('envModeBadge');
    const badgeText = document.getElementById('envModeBadgeText');
    if (!badge || !badgeText) return;

    try {
      const res = await window.gstApi.getReadiness();
      const env = (res.details?.configuration?.app_env || 'demo').toLowerCase().strip ? res.details?.configuration?.app_env.toLowerCase().strip() : 'demo';
      badge.className = `env-badge-container ${env === 'production' ? 'production' : (env === 'test' ? 'test' : 'demo')}`;

      if (env === 'production') {
        badgeText.textContent = 'PROD';
      } else if (env === 'test') {
        badgeText.textContent = 'TEST';
      } else {
        badgeText.textContent = 'DEMO';
      }
    } catch (_) {
      badge.className = 'env-badge-container demo';
      badgeText.textContent = 'DEMO';
    }
  }

  initSidebarToggle() {
    const sidebar = document.getElementById('appSidebar');
    const toggleBtn = document.getElementById('sidebarCollapseBtn');
    if (!sidebar || !toggleBtn) return;

    // Load persisted state
    const isCollapsed = localStorage.getItem('uc15_sidebar_collapsed') === 'true';
    if (isCollapsed) {
      sidebar.classList.add('collapsed');
    }

    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      const state = sidebar.classList.contains('collapsed');
      localStorage.setItem('uc15_sidebar_collapsed', state);
    });

    // Keyboard shortcut: Ctrl+B / Cmd+B to toggle sidebar
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        sidebar.classList.toggle('collapsed');
        localStorage.setItem('uc15_sidebar_collapsed', sidebar.classList.contains('collapsed'));
      }
    });
  }

  initGlobalSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    if (!searchInput) return;

    // Press '/' to focus search bar
    window.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        searchInput.focus();
      }
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (window.location.hash !== '#/compliance') {
          window.location.hash = '#/compliance';
          setTimeout(() => {
            if (window.complianceView) {
              window.complianceView.filters.search = query;
              const subSearch = document.getElementById('searchInput');
              if (subSearch) subSearch.value = query;
              window.complianceView.applyFilters();
            }
          }, 100);
        } else {
          if (window.complianceView) {
            window.complianceView.filters.search = query;
            const subSearch = document.getElementById('searchInput');
            if (subSearch) subSearch.value = query;
            window.complianceView.applyFilters();
          }
        }
      }
    });
  }

  async runAgent() {
    const btn = document.getElementById('globalRunBtn');
    const prevHtml = btn ? btn.innerHTML : '<span>Run Pipeline</span>';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation: spin 0.8s linear infinite;">
          <line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/>
          <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
          <line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/>
          <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
        </svg>
        <span>Validating S1&ndash;S9...</span>
      `;
    }

    try {
      const res = await window.gstApi.runAgent();
      console.log('[GSTApp] Run completed successfully:', res);
      window.showToast('Statutory pipeline completed successfully!');
      // Re-trigger current route to refresh view data
      window.gstRouter.handleRoute();
      this.updateHeaderBadges();
    } catch (err) {
      window.showToast(`Validation run failed: ${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = prevHtml;
      }
    }
  }

  async initDatasetSelector() {
    const select = document.getElementById('headerDatasetSelect');
    if (!select) return;

    try {
      const res = await window.gstApi.getDatasets();
      const datasets = res.datasets || [];
      const activeId = res.active_dataset_id;

      if (datasets.length > 0) {
        select.innerHTML = datasets.map(d => `
          <option value="${d.id}" ${d.id === activeId ? 'selected' : ''}>
            ${d.name} (${d.invoice_count})
          </option>
        `).join('');
      }

      select.onchange = async (e) => {
        const dsId = e.target.value;
        try {
          select.disabled = true;
          const r = await window.gstApi.selectDataset(dsId);
          window.showToast(r.message || 'Active dataset switched!');
          window.gstRouter.handleRoute();
          this.updateHeaderBadges();
        } catch (err) {
          window.showToast(`Dataset switch failed: ${err.message}`, 'error');
        } finally {
          select.disabled = false;
        }
      };
    } catch (_) {
      console.warn('[GSTApp] Failed to load dataset options');
    }
  }

  async updateHeaderBadges() {
    try {
      const ov = await window.gstApi.getDashboardOverview();
      const statusText = document.getElementById('sidebarStatusText') || document.getElementById('headerStatusBadgeText');
      if (statusText && ov && ov.kpis) {
        statusText.textContent = `Statutory Engine Online · ${ov.kpis.total_invoices} Invoices`;
      }
      this.initDatasetSelector();
    } catch (_) {
      const statusText = document.getElementById('sidebarStatusText') || document.getElementById('headerStatusBadgeText');
      if (statusText) statusText.textContent = `Statutory Engine Ready`;
    }
  }

  loadView(viewName) {
    window.location.hash = `#/${viewName}`;
  }
}

// Global UI Helpers
window.showToast = function(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  const iconColor = type === 'error' ? '#EF4444' : '#10B981';
  toast.innerHTML = `
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3000);
};

window.copyToClipboard = function(text, label = 'Text') {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      window.showToast(`${label} copied to clipboard`);
    }).catch(() => {
      prompt("Copy to clipboard: Ctrl+C, Enter", text);
    });
  } else {
    prompt("Copy to clipboard: Ctrl+C, Enter", text);
  }
};

// Bootstrap once DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.gstApp = new GSTApp();
  window.gstApp.init();
});
