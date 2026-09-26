import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'X-Role': 'tax_lead',
  },
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.response?.data?.error || err.message || 'Unknown error'
    return Promise.reject(new Error(msg))
  }
)

export const gstApi = {
  // ── Health ──────────────────────────────────────────────────────────────
  getHealth:    () => api.get('/health'),
  getReadiness: () => api.get('/ready'),

  // ── Dashboard / Overview ─────────────────────────────────────────────────
  // GET /api/dashboard/overview
  getDashboardOverview: () => api.get('/dashboard/overview'),

  // ── Run Pipeline ──────────────────────────────────────────────────────────
  // POST /api/run
  runAgent: () => api.post('/run'),

  // ── Results / Compliance ──────────────────────────────────────────────────
  // GET /api/results/latest   → invoice list with gate results
  getComplianceResults: (params) => api.get('/results/latest', { params }),

  // GET /api/results/{invoice_no}
  getInvoiceDetail: (invoiceNo) => api.get(`/results/${encodeURIComponent(invoiceNo)}`),

  // ── Risk ──────────────────────────────────────────────────────────────────
  // GET /api/risk/summary
  getRiskSummary: () => api.get('/risk/summary'),

  // ── Datasets / Ingestion ──────────────────────────────────────────────────
  // GET /api/datasets
  getDatasets: () => api.get('/datasets'),

  // POST /api/datasets/select  body: { dataset_id }
  selectDataset: (id) => api.post('/datasets/select', { dataset_id: id }),

  // POST /api/datasets/upload  (multipart)
  ingestFile: (formData) =>
    api.post('/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  // ── Cases ─────────────────────────────────────────────────────────────────
  // GET /api/cases
  getCases: () => api.get('/cases'),

  // GET /api/cases/{case_id}
  getCaseDetail: (id) => api.get(`/cases/${id}`),

  // POST /api/cases/{case_id}/assign
  updateCase: (id, data) => api.post(`/cases/${id}/assign`, data),

  // POST /api/cases/{case_id}/review
  reviewCase: (id, data) => api.post(`/cases/${id}/review`, data),

  // POST /api/cases/{case_id}/resolve
  resolveCase: (id, data) => api.post(`/cases/${id}/resolve`, data),

  // POST /api/cases/{case_id}/close
  closeCase: (id, data) => api.post(`/cases/${id}/close`, data),

  // GET /api/cases/{case_id}/findings
  getCaseFindings: (id) => api.get(`/cases/${id}/findings`),

  // GET /api/cases/{case_id}/timeline
  getCaseTimeline: (id) => api.get(`/cases/${id}/timeline`),

  // ── Investigations ────────────────────────────────────────────────────────
  // GET /api/investigation/root-causes
  getInvestigations: () => api.get('/investigation/root-causes'),

  // GET /api/investigation/summary
  getInvestigationSummary: () => api.get('/investigation/summary'),

  // GET /api/investigation/{inv_id}
  getInvestigationDetail: (id) => api.get(`/investigation/root-causes/${id}`),

  // POST /api/investigations
  createInvestigation: (data) => api.post('/investigations', data),

  // ── AI Agent / Sessions ───────────────────────────────────────────────────
  // POST /api/agent/session/start  → { session_id }
  startAgentSession: () => api.post('/agent/session/start', {}),

  // POST /api/agent/session/{session_id}/query  body: { query }
  sendAgentMessage: async (message) => {
    // Create a fresh session and query it in one call for simplicity
    const { session_id } = await api.post('/agent/session/start', {})
    return api.post(`/agent/session/${session_id}/query`, { query: message })
  },

  // GET /api/agent/sessions
  getAgentSessions: () => api.get('/agent/sessions'),

  // ── Audit Trail ───────────────────────────────────────────────────────────
  // GET /api/audit/logs
  getAuditTrail: (params) => api.get('/audit/logs', { params }),

  // ── Historical / Intelligence ─────────────────────────────────────────────
  getHistoricalSummary: () => api.get('/historical/summary'),
  getIntelligenceSummary: () => api.get('/intelligence/summary'),
  getFinancialSummary: () => api.get('/financial/summary'),

  // ── Operations ────────────────────────────────────────────────────────────
  getOperationsDashboard: () => api.get('/operations/dashboard'),

  // ── SAP S/4HANA & HANA Database ───────────────────────────────────────────
  getSapStatus: () => api.get('/sap/status'),
  syncSapHana: () => api.post('/sap/sync'),
  applyPaymentBlock: (data) => api.post('/sap/payment-block', data),
  releasePaymentBlock: (data) => api.post('/sap/payment-block/release', data),
  getSapJournalEntry: (invoiceNo) => api.get(`/sap/journal-entry/${encodeURIComponent(invoiceNo)}`),
}

export default gstApi
