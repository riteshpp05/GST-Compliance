/**
 * UC15 GST Compliance Investigation Platform — Centralized API Client
 * Encapsulates all REST communication with backend endpoints.
 */

class GSTApiClient {
  constructor() {
    this.cache = new Map();
    this.cacheTtlMs = 60000; // 1 minute client cache for idempotent GETs
  }

  clearCache() {
    this.cache.clear();
  }

  async _fetch(endpoint, options = {}, useCache = false) {
    const cacheKey = `${options.method || 'GET'}:${endpoint}`;
    if (useCache && this.cache.has(cacheKey)) {
      const entry = this.cache.get(cacheKey);
      if (Date.now() - entry.timestamp < this.cacheTtlMs) {
        return entry.data;
      }
    }

    const authHeaders = {};
    const apiKey = sessionStorage.getItem('uc15_api_key');
    const authToken = sessionStorage.getItem('uc15_auth_token');
    if (apiKey) authHeaders['X-API-Key'] = apiKey;
    if (authToken) authHeaders['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;

    try {
      const response = await fetch(endpoint, {
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          ...authHeaders,
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        let errDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson && errJson.detail) {
            errDetail = errJson.detail;
          }
        } catch (_) {}
        const error = new Error(errDetail);
        error.status = response.status;
        throw error;
      }

      const data = await response.json();
      if (useCache) {
        this.cache.set(cacheKey, { timestamp: Date.now(), data });
      }
      return data;
    } catch (err) {
      console.error(`[GSTApiClient] Request failed for ${endpoint}:`, err);
      throw err;
    }
  }

  // Core Agent Execution
  async checkHealth() {
    return this._fetch('/api/health');
  }

  async runAgent() {
    this.clearCache();
    return this._fetch('/api/run', { method: 'POST' });
  }

  // Dashboard Overview
  async getDashboardOverview() {
    return this._fetch('/api/dashboard/overview', {}, true);
  }

  // Compliance Results
  async getLatestResults() {
    return this._fetch('/api/results/latest', {}, true);
  }

  async getInvoiceResult(invoiceNo) {
    return this._fetch(`/api/results/${encodeURIComponent(invoiceNo)}`, {}, true);
  }

  // Unified Invoice Dossier (Central Endpoint)
  async getInvoiceDossier(invoiceNo) {
    return this._fetch(`/api/investigation/invoice/${encodeURIComponent(invoiceNo)}`, {}, false);
  }

  // --- Invoice Workspace: Correct, Re-check, Approve ---
  async correctInvoice(invoiceNo, corrections, reason = '', correctedBy = 'FINANCE_USER') {
    this.clearCache();
    return this._fetch(`/api/invoice/${encodeURIComponent(invoiceNo)}/correct`, {
      method: 'POST',
      body: JSON.stringify({ corrections, reason, corrected_by: correctedBy }),
    });
  }

  async recheckInvoice(invoiceNo) {
    this.clearCache();
    return this._fetch(`/api/invoice/${encodeURIComponent(invoiceNo)}/recheck`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async approveInvoice(invoiceNo, action, comment, approvedBy = 'FINANCE_USER') {
    this.clearCache();
    return this._fetch(`/api/invoice/${encodeURIComponent(invoiceNo)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ action, comment, approved_by: approvedBy }),
    });
  }

  async getInvoiceCorrections(invoiceNo) {
    return this._fetch(`/api/invoice/${encodeURIComponent(invoiceNo)}/corrections`, {}, false);
  }

  async getInvoiceApproval(invoiceNo) {
    return this._fetch(`/api/invoice/${encodeURIComponent(invoiceNo)}/approval`, {}, false);
  }

  async getAuditLogs(params = {}) {
    let q = '';
    const queryParts = [];
    if (params.event_type) queryParts.push(`event_type=${encodeURIComponent(params.event_type)}`);
    if (params.invoice_no) queryParts.push(`invoice_no=${encodeURIComponent(params.invoice_no)}`);
    if (params.limit) queryParts.push(`limit=${encodeURIComponent(params.limit)}`);
    if (queryParts.length > 0) q = '?' + queryParts.join('&');
    return this._fetch(`/api/audit/logs${q}`, {}, false);
  }

  // Risk Intelligence
  async getRiskSummary() {
    return this._fetch('/api/risk/summary', {}, true);
  }

  // Financial Intelligence
  async getFinancialSummary() {
    return this._fetch('/api/financial/summary', {}, true);
  }

  async getFinancialExposure() {
    return this._fetch('/api/financial/exposure', {}, true);
  }

  async getTopExposures(limit = 5) {
    return this._fetch(`/api/financial/top-exposures?limit=${limit}`, {}, true);
  }

  // Historical Intelligence
  async getHistoricalSummary(periodType = 'MONTHLY') {
    return this._fetch(`/api/historical/summary?period_type=${periodType}`, {}, true);
  }

  async getHistoricalTrends(periodType = 'MONTHLY') {
    return this._fetch(`/api/historical/trends?period_type=${periodType}`, {}, true);
  }

  // Duplicate & Anomaly Intelligence
  async getIntelligenceSummary() {
    return this._fetch('/api/intelligence/summary', {}, true);
  }

  async getDuplicates() {
    return this._fetch('/api/intelligence/duplicates', {}, true);
  }

  async getAnomalies() {
    return this._fetch('/api/intelligence/anomalies', {}, true);
  }

  // Root Cause & Blast Radius Investigation
  async getInvestigationSummary() {
    return this._fetch('/api/investigation/summary', {}, true);
  }

  async getRootCauses() {
    return this._fetch('/api/investigation/root-causes', {}, true);
  }

  async getRootCauseById(rcId) {
    return this._fetch(`/api/investigation/root-causes/${encodeURIComponent(rcId)}`, {}, true);
  }

  async getBlastRadiusById(brId) {
    return this._fetch(`/api/investigation/blast-radius/${encodeURIComponent(brId)}`, {}, true);
  }

  async getInvestigationProfile(id = 'default') {
    return this._fetch(`/api/investigation/${encodeURIComponent(id)}`, {}, true);
  }

  // --- Unified API Endpoints ---
  async getReadiness() {
    return this._fetch('/ready');
  }

  async getCaseReviewPackage(caseId) {
    return this._fetch(`/api/v1/cases/${encodeURIComponent(caseId)}/review-package`, {}, true);
  }

  async getCaseReconciliation(caseId) {
    return this._fetch(`/api/v1/cases/${encodeURIComponent(caseId)}/reconciliation`, {}, true);
  }

  async getCaseFinancialExposure(caseId) {
    return this._fetch(`/api/v1/cases/${encodeURIComponent(caseId)}/financial-exposure`, {}, true);
  }

  async getCaseAIInvestigation(caseId) {
    return this._fetch(`/api/v1/cases/${encodeURIComponent(caseId)}/ai-investigation`, {}, true);
  }

  async getCases(status = null) {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return this._fetch(`/api/cases${query}`, {}, true);
  }

  async getCase(caseId) {
    return this._fetch(`/api/cases/${encodeURIComponent(caseId)}`, {}, true);
  }

  async submitCaseReview(caseId, payload) {
    this.clearCache();
    return this._fetch(`/api/cases/${encodeURIComponent(caseId)}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  setRoleProfile(roleName) {
    const roleKeys = {
      'ADMIN': 'key-admin-123',
      'INVESTIGATOR': 'key-investigator-123',
      'REVIEWER': 'key-reviewer-123',
      'AUDITOR': 'key-auditor-123',
      'ANALYST': 'key-analyst-123',
    };
    const key = roleKeys[roleName] || 'key-investigator-123';
    sessionStorage.setItem('uc15_api_key', key);
    sessionStorage.setItem('uc15_active_role', roleName);
    this.clearCache();
  }

  // --- Dataset Management APIs ---
  async getDatasets() {
    return this._fetch('/api/datasets');
  }

  async uploadDataset(formData) {
    this.clearCache();
    const authHeaders = {};
    const apiKey = sessionStorage.getItem('uc15_api_key');
    const authToken = sessionStorage.getItem('uc15_auth_token');
    if (apiKey) authHeaders['X-API-Key'] = apiKey;
    if (authToken) authHeaders['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;

    const response = await fetch('/api/datasets/upload', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        ...authHeaders,
      },
      body: formData,
    });

    if (!response.ok) {
      let errDetail = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) errDetail = errJson.detail;
      } catch (_) {}
      throw new Error(errDetail);
    }
    return response.json();
  }

  async selectDataset(datasetId) {
    this.clearCache();
    return this._fetch('/api/datasets/select', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId }),
    });
  }

  async deleteDataset(datasetId) {
    this.clearCache();
    return this._fetch(`/api/datasets/${encodeURIComponent(datasetId)}`, {
      method: 'DELETE',
    });
  }
}

// Global Singleton Instance
window.gstApi = new GSTApiClient();
