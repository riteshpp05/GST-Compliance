/**
 * UC15 GST Compliance Investigation Platform — Client-Side Hash Router
 * Maps URL hash routes to view controllers with parameter support.
 */

class GSTRouting {
  constructor() {
    this.routes = {};
    this.currentRoute = null;
    this.currentParam = null;

    this.routeTitles = {
      'overview': 'Overview',
      'compliance': 'Invoice Audit Center',
      'investigations': 'Invoice Audit Center',
      'risk': 'Invoice Audit Center',
      'financial': 'Invoice Audit Center',
      'intelligence': 'Invoice Audit Center',
      'ai_agent': 'AI Investigation Agent',
      'audit_trail': 'Audit Trail & Decision Ledger',
      'history': 'Audit Trail & Decision Ledger',
    };

    window.addEventListener('hashchange', () => this.handleRoute());
  }

  register(pattern, handler) {
    this.routes[pattern] = handler;
  }

  navigate(hash) {
    window.location.hash = hash;
  }

  updateBreadcrumb(title) {
    const el = document.getElementById('breadcrumbPageTitle');
    if (el) {
      el.textContent = title;
    }
  }

  handleRoute() {
    const rawHash = window.location.hash.slice(1) || '/overview';
    const cleanHash = rawHash.startsWith('/') ? rawHash : `/${rawHash}`;

    // Standalone approval center deprecated; redirect directly to Invoice Audit Center
    if (cleanHash === '/case_management' || cleanHash.startsWith('/case_management')) {
      window.location.hash = '#/compliance';
      return;
    }

    // Update active class on navigation tabs / sidebar links
    const tabName = cleanHash.split('/')[1] || 'overview';
    document.querySelectorAll('.sidebar-link, .nav-tab').forEach(tab => {
      const tabTarget = tab.getAttribute('data-tab');
      if (tabTarget === tabName) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    // Parameter routes: /workspace/:caseId or /cases/:caseId
    if (cleanHash.startsWith('/workspace/') || cleanHash.startsWith('/cases/')) {
      const parts = cleanHash.split('/');
      const caseId = parts[2] ? parts[2].trim() : '';
      const subTab = parts[3] || 'overview';

      this.updateBreadcrumb(`Case Workspace / ${caseId}`);
      if (this.routes['/workspace/:id']) {
        this.currentRoute = '/workspace/:id';
        this.currentParam = caseId;
        this.routes['/workspace/:id'](caseId, subTab);
        window.scrollTo(0, 0);
        return;
      }
    }

    // Check for parameter routes: /investigation/:id
    if (cleanHash.startsWith('/investigation/')) {
      const rawId = cleanHash.replace('/investigation/', '').trim();
      let invoiceId = rawId;
      try { invoiceId = decodeURIComponent(rawId); } catch(e) {}
      this.updateBreadcrumb(`Investigation / ${invoiceId}`);
      if (this.routes['/investigation/:id']) {
        this.currentRoute = '/investigation/:id';
        this.currentParam = invoiceId;
        this.routes['/investigation/:id'](invoiceId);
        window.scrollTo(0, 0);
        return;
      }
    }

    // Update breadcrumb for standard routes
    const pageTitle = this.routeTitles[tabName] || 'Executive Overview';
    this.updateBreadcrumb(pageTitle);

    // Exact matches
    if (this.routes[cleanHash]) {
      this.currentRoute = cleanHash;
      this.currentParam = null;
      this.routes[cleanHash]();
      window.scrollTo(0, 0);
      return;
    }

    // Fallback to overview
    if (this.routes['/overview']) {
      this.currentRoute = '/overview';
      this.routes['/overview']();
      window.scrollTo(0, 0);
    }
  }
}

window.gstRouter = new GSTRouting();
