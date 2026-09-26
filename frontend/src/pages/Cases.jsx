import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  FileText,
  ArrowRight,
  X,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  ExternalLink,
  Lock,
  Unlock,
  Copy,
  Check,
  Clock,
  User,
  Search,
  Filter,
  DollarSign,
  AlertCircle,
  FolderOpen
} from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatCurrency, formatDate, statusBadge, cn } from '@/lib/utils'
import { FadeIn, StaggerContainer, StaggerItem } from '@/components/ui/animations'
import { Skeleton, SectionHeader, EmptyState } from '@/components/ui/primitives'

const PRIORITY_MAP = {
  P1: 'bg-red-50 text-red-700 border border-red-200',
  P2: 'bg-amber-50 text-amber-700 border border-amber-200',
  P3: 'bg-blue-50 text-blue-700 border border-blue-200',
  P4: 'bg-gray-50 text-gray-600 border border-gray-200',
}

export default function Cases() {
  const navigate = useNavigate()
  const { id: routeCaseId } = useParams()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [copiedId, setCopiedId] = useState(false)
  const [reviewComment, setReviewComment] = useState('')
  const [actionSuccess, setActionSuccess] = useState('')
  const [actionError, setActionError] = useState('')

  // Query all cases
  const { data: casesData, isLoading, refetch } = useQuery({
    queryKey: ['cases'],
    queryFn: gstApi.getCases,
  })
  const rawCases = casesData?.cases || (Array.isArray(casesData) ? casesData : [])

  // Query specific case detail if routeCaseId is active
  const { data: activeCaseDetail, isLoading: isDetailLoading } = useQuery({
    queryKey: ['case-detail', routeCaseId],
    queryFn: () => gstApi.getCaseDetail(routeCaseId),
    enabled: Boolean(routeCaseId),
  })

  // Selected case is either the detailed record from server, or fallback to the item in list
  const selectedCase =
    activeCaseDetail ||
    rawCases.find(
      (c) => (c.case_id && c.case_id === routeCaseId) || (c.id && c.id === routeCaseId)
    )

  // Mutations for Case Human Review & Lifecycle
  const reviewMutation = useMutation({
    mutationFn: ({ caseId, decision, comment }) =>
      gstApi.reviewCase(caseId, {
        reviewer: 'Senior Tax Auditor',
        reviewer_role: 'Tax Manager',
        decision,
        comment: comment || `Audit review outcome: ${decision}`,
      }),
    onSuccess: (data, vars) => {
      setActionSuccess(`Case review submitted as ${vars.decision}`)
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case-detail', vars.caseId] })
      setTimeout(() => setActionSuccess(''), 4000)
    },
    onError: (err) => {
      setActionError(err.message || 'Failed to submit review decision')
      setTimeout(() => setActionError(''), 5000)
    },
  })

  const resolveMutation = useMutation({
    mutationFn: (caseId) =>
      gstApi.resolveCase(caseId, {
        actor: 'FINANCE_LEAD',
        comment: reviewComment || 'Compliance discrepancy resolved with reconciled GSTR-1/3B filing.',
      }),
    onSuccess: (data, caseId) => {
      setActionSuccess('Case successfully marked as RESOLVED')
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case-detail', caseId] })
      setTimeout(() => setActionSuccess(''), 4000)
    },
    onError: (err) => {
      setActionError(err.message || 'Failed to resolve case')
      setTimeout(() => setActionError(''), 5000)
    },
  })

  const closeMutation = useMutation({
    mutationFn: (caseId) =>
      gstApi.closeCase(caseId, {
        actor: 'SYSTEM_ADMIN',
        reason: reviewComment || 'Closed after statutory audit sign-off.',
      }),
    onSuccess: (data, caseId) => {
      setActionSuccess('Case successfully closed')
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case-detail', caseId] })
      setTimeout(() => setActionSuccess(''), 4000)
    },
    onError: (err) => {
      setActionError(err.message || 'Failed to close case')
      setTimeout(() => setActionError(''), 5000)
    },
  })

  // SAP Payment Block Mutation
  const paymentBlockMutation = useMutation({
    mutationFn: ({ invoiceNo, block }) =>
      block
        ? gstApi.applyPaymentBlock({ invoice_no: invoiceNo, reason: 'R - Tax Compliance Hold' })
        : gstApi.releasePaymentBlock({ invoice_no: invoiceNo, reason: 'Compliance Verified' }),
    onSuccess: (res, vars) => {
      setActionSuccess(
        vars.block ? 'SAP Payment Block "R" applied (BSEG-ZLSPR)' : 'SAP Payment Block released'
      )
      setActionError('')
      queryClient.invalidateQueries({ queryKey: ['case-detail', routeCaseId] })
      queryClient.invalidateQueries({ queryKey: ['sap-status'] })
      setTimeout(() => setActionSuccess(''), 4000)
    },
    onError: (err) => {
      setActionError(err.message || 'Failed to update SAP payment block')
      setTimeout(() => setActionError(''), 5000)
    },
  })

  // Filtered cases
  const filteredCases = rawCases.filter((c) => {
    const q = search.toLowerCase().trim()
    const matchesSearch =
      !q ||
      (c.case_id || '').toLowerCase().includes(q) ||
      (c.title || '').toLowerCase().includes(q) ||
      (c.invoice_id || '').toLowerCase().includes(q) ||
      (c.counterparty_gstin || '').toLowerCase().includes(q)

    const matchesPriority = priorityFilter === 'ALL' || c.priority === priorityFilter
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter

    return matchesSearch && matchesPriority && matchesStatus
  })

  const totalAtRisk = rawCases.reduce((acc, c) => acc + (c.financial_exposure || 0), 0)
  const readyCount = rawCases.filter(
    (c) => c.status === 'READY_FOR_RESOLUTION' || c.status === 'IN_REVIEW' || c.status === 'OPEN'
  ).length

  const handleCopyId = (cid) => {
    navigator.clipboard.writeText(cid)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  const closeDrawer = () => {
    navigate('/cases')
    setReviewComment('')
    setActionSuccess('')
    setActionError('')
  }

  return (
    <FadeIn>
      <div className="space-y-4">
        {/* KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Total Cases</p>
              <h3 className="text-xl font-bold text-gray-900 mt-0.5">{rawCases.length}</h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Active Review</p>
              <h3 className="text-xl font-bold text-amber-600 mt-0.5">{readyCount}</h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">P1 / P2 Critical</p>
              <h3 className="text-xl font-bold text-red-600 mt-0.5">
                {rawCases.filter((c) => c.priority === 'P1' || c.priority === 'P2').length}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
              <ShieldAlert size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">At-Risk Exposure</p>
              <h3 className="text-xl font-bold text-gray-900 mt-0.5">{formatCurrency(totalAtRisk)}</h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <DollarSign size={18} />
            </div>
          </div>
        </div>

        {/* Panel Main */}
        <div className="panel">
          <SectionHeader
            icon={<FileText size={16} />}
            title="Case Management & Statutory Resolution"
            subtitle="Review non-compliant exceptions, govern SAP payment blocks, and issue statutory determinations"
          />

          {/* Filter Bar */}
          <div className="flex items-center gap-3 flex-wrap mb-4">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input pl-8 text-[12px]"
                placeholder="Search by Case ID, Invoice No, GSTIN, or Title…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-1.5">
              <Filter size={13} className="text-gray-400" />
              <select
                className="select-field text-[12px] py-1.5"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
              >
                <option value="ALL">All Priorities</option>
                <option value="P1">P1 - Critical</option>
                <option value="P2">P2 - High</option>
                <option value="P3">P3 - Medium</option>
                <option value="P4">P4 - Low</option>
              </select>

              <select
                className="select-field text-[12px] py-1.5"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="READY_FOR_RESOLUTION">Ready for Resolution</option>
                <option value="APPROVED">Approved</option>
                <option value="RESOLVED">Resolved</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
          </div>

          {/* Case Listing */}
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : filteredCases.length === 0 ? (
            <EmptyState
              icon={<FileText size={22} />}
              title="No Matching Cases"
              description="No compliance failure cases match your filter criteria or search parameters."
            />
          ) : (
            <StaggerContainer className="space-y-2">
              {filteredCases.map((c, i) => {
                const caseId = c.case_id || c.id || `CASE-${i + 1}`
                const isSelected = routeCaseId === caseId

                return (
                  <StaggerItem key={caseId}>
                    <motion.div
                      className={cn(
                        'flex items-center gap-3.5 px-4 py-3.5 rounded-xl border cursor-pointer transition-all duration-150 group',
                        isSelected
                          ? 'bg-blue-50/70 border-blue-300 ring-2 ring-blue-100 shadow-sm'
                          : 'bg-white hover:bg-gray-50/80 border-gray-200 hover:border-blue-200'
                      )}
                      whileHover={{ x: 2 }}
                      onClick={() => navigate(`/cases/${caseId}`)}
                    >
                      <span
                        className={cn(
                          'px-2.5 py-1 rounded-md text-[11px] font-bold flex-shrink-0',
                          PRIORITY_MAP[c.priority] || PRIORITY_MAP.P4
                        )}
                      >
                        {c.priority || 'P4'}
                      </span>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[12px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                            {caseId}
                          </span>
                          <span className="text-[13px] font-semibold text-gray-900 truncate">
                            {c.title || `Case ${caseId}`}
                          </span>
                          <span className={cn('badge', statusBadge(c.status))}>{c.status || 'OPEN'}</span>
                        </div>
                        <p className="text-[12px] text-gray-500 mt-1 line-clamp-1">{c.description || '—'}</p>
                      </div>

                      {c.invoice_id && (
                        <div className="hidden sm:flex flex-col items-end flex-shrink-0 text-right">
                          <span className="text-[11px] font-semibold text-gray-400">Linked Invoice</span>
                          <span className="font-mono text-[11px] text-gray-700 font-medium">
                            {c.invoice_id}
                          </span>
                        </div>
                      )}

                      <div className="text-right flex-shrink-0 pl-2">
                        <p className="text-[12px] font-medium text-gray-700">{formatDate(c.created_at)}</p>
                        <p className="text-[11px] text-gray-400">{c.assigned_role || 'Tax Analyst'}</p>
                      </div>

                      <div className="p-1 rounded-md text-gray-400 group-hover:text-blue-600 group-hover:bg-blue-50 transition-colors">
                        <ArrowRight size={16} />
                      </div>
                    </motion.div>
                  </StaggerItem>
                )
              })}
            </StaggerContainer>
          )}
        </div>
      </div>

      {/* Slide-Over Case Detail Drawer */}
      <AnimatePresence>
        {routeCaseId && (
          <div className="fixed inset-0 z-50 overflow-hidden">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 bg-gray-900/30 backdrop-blur-xs"
              onClick={closeDrawer}
            />

            {/* Slide-out Panel */}
            <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 28, stiffness: 280 }}
                className="w-screen max-w-2xl bg-white shadow-2xl flex flex-col border-l border-gray-200"
              >
                {/* Drawer Header */}
                <div className="px-6 py-4 border-b border-gray-200 bg-white sticky top-0 z-10 flex items-center justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0">
                      <FileText size={16} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[13px] font-bold text-gray-900">
                          {selectedCase?.case_id || routeCaseId}
                        </span>
                        <button
                          onClick={() => handleCopyId(selectedCase?.case_id || routeCaseId)}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          title="Copy Case ID"
                        >
                          {copiedId ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                        </button>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-[11px] font-bold',
                            PRIORITY_MAP[selectedCase?.priority] || PRIORITY_MAP.P4
                          )}
                        >
                          {selectedCase?.priority || 'P3'}
                        </span>
                        <span className={cn('badge', statusBadge(selectedCase?.status))}>
                          {selectedCase?.status || 'OPEN'}
                        </span>
                      </div>
                      <p className="text-[12px] text-gray-500 truncate mt-0.5">
                        {selectedCase?.title || 'Statutory Compliance Case Dossier'}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={closeDrawer}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Notification Toasts */}
                {actionSuccess && (
                  <div className="mx-6 mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-[12px] text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 size={15} className="text-emerald-600 flex-shrink-0" />
                    <span>{actionSuccess}</span>
                  </div>
                )}
                {actionError && (
                  <div className="mx-6 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-[12px] text-red-800 flex items-center gap-2">
                    <AlertTriangle size={15} className="text-red-600 flex-shrink-0" />
                    <span>{actionError}</span>
                  </div>
                )}

                {/* Drawer Scrollable Content */}
                <div data-lenis-prevent className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
                  {isDetailLoading && !selectedCase ? (
                    <div className="space-y-4">
                      <Skeleton className="h-20 w-full" />
                      <Skeleton className="h-32 w-full" />
                      <Skeleton className="h-40 w-full" />
                    </div>
                  ) : !selectedCase ? (
                    <EmptyState
                      icon={<AlertCircle size={22} />}
                      title="Case Not Found"
                      description="The requested case identifier could not be located in statutory storage."
                    />
                  ) : (
                    <>
                      {/* Section: Statutory Summary & Risk */}
                      <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                            Executive Statutory Finding
                          </span>
                          <span className="text-[11px] font-semibold text-gray-500">
                            Risk Level: <strong className="text-gray-900">{selectedCase.risk_level || 'MEDIUM'}</strong>
                          </span>
                        </div>
                        <p className="text-[13px] text-gray-800 leading-relaxed font-medium">
                          {selectedCase.description || 'Statutory validation exception flagged for review.'}
                        </p>

                        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-200">
                          <div>
                            <span className="text-[11px] text-gray-500">Double-Count Safe Exposure:</span>
                            <p className="text-[15px] font-bold text-gray-900 mt-0.5">
                              {formatCurrency(selectedCase.financial_exposure || 0)}
                            </p>
                          </div>
                          <div>
                            <span className="text-[11px] text-gray-500">Root Cause Pattern:</span>
                            <p className="text-[13px] font-semibold text-gray-800 mt-0.5">
                              {selectedCase.root_cause || 'Place of Supply / Tax Symmetry Drift'}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Section: Failed Gate Details */}
                      {selectedCase.metadata?.failed_gate_details &&
                        selectedCase.metadata.failed_gate_details.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider flex items-center gap-1.5">
                              <AlertCircle size={14} className="text-red-500" />
                              Statutory Gate Violations (GST Law)
                            </h4>
                            <div className="space-y-2">
                              {selectedCase.metadata.failed_gate_details.map((detail, idx) => (
                                <div
                                  key={idx}
                                  className="p-3 bg-red-50/60 border border-red-200 rounded-lg text-[12px] text-red-900 leading-relaxed font-mono"
                                >
                                  {detail}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                      {/* Section: Linked Records & Cross-References */}
                      <div className="space-y-2">
                        <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider">
                          Linked Enterprise Records
                        </h4>
                        <div className="grid grid-cols-2 gap-3 p-4 bg-white border border-gray-200 rounded-xl">
                          <div>
                            <span className="text-[11px] text-gray-500">Linked Invoice No:</span>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="font-mono text-[12px] font-bold text-gray-900">
                                {selectedCase.invoice_id || '—'}
                              </span>
                              {selectedCase.invoice_id && (
                                <Link
                                  to={`/invoice/${encodeURIComponent(selectedCase.invoice_id)}`}
                                  className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 font-semibold"
                                >
                                  <ExternalLink size={12} /> Open Dossier
                                </Link>
                              )}
                            </div>
                          </div>

                          <div>
                            <span className="text-[11px] text-gray-500">Counterparty GSTIN:</span>
                            <p className="font-mono text-[12px] text-gray-800 font-semibold mt-1">
                              {selectedCase.counterparty_gstin || '—'}
                            </p>
                          </div>

                          <div className="pt-2 border-t border-gray-100">
                            <span className="text-[11px] text-gray-500">Assigned Investigator:</span>
                            <p className="text-[12px] text-gray-800 font-medium mt-0.5 flex items-center gap-1.5">
                              <User size={13} className="text-gray-400" />
                              {selectedCase.assigned_role || 'Tax Analyst'}
                            </p>
                          </div>

                          <div className="pt-2 border-t border-gray-100">
                            <span className="text-[11px] text-gray-500">Case Created Date:</span>
                            <p className="text-[12px] text-gray-800 font-medium mt-0.5 flex items-center gap-1.5">
                              <Clock size={13} className="text-gray-400" />
                              {formatDate(selectedCase.created_at)}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Section: SAP S/4HANA & Financial Controls */}
                      <div className="p-4 bg-gradient-to-br from-blue-50/50 to-indigo-50/30 border border-blue-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Lock size={15} className="text-blue-700" />
                            <h4 className="text-[12px] font-bold text-blue-900 uppercase tracking-wider">
                              SAP S/4HANA FICO Controls
                            </h4>
                          </div>
                          <span className="text-[11px] font-mono text-blue-700 bg-blue-100/70 px-2 py-0.5 rounded">
                            BSEG-ZLSPR
                          </span>
                        </div>
                        <p className="text-[12px] text-gray-600 leading-relaxed">
                          Prevent erroneous Accounts Payable disbursement during ongoing statutory inquiry.
                          Applies payment block directly against vendor line item in SAP S/4HANA Finance.
                        </p>

                        <div className="flex items-center gap-2.5 pt-1">
                          <button
                            onClick={() =>
                              paymentBlockMutation.mutate({
                                invoiceNo: selectedCase.invoice_id,
                                block: true,
                              })
                            }
                            disabled={paymentBlockMutation.isPending || !selectedCase.invoice_id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 transition-colors shadow-sm"
                          >
                            <Lock size={13} /> Apply Payment Block "R"
                          </button>

                          <button
                            onClick={() =>
                              paymentBlockMutation.mutate({
                                invoiceNo: selectedCase.invoice_id,
                                block: false,
                              })
                            }
                            disabled={paymentBlockMutation.isPending || !selectedCase.invoice_id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors"
                          >
                            <Unlock size={13} /> Release Payment Block
                          </button>
                        </div>
                      </div>

                      {/* Section: Historical Decisions Audit Trail */}
                      <div className="space-y-2">
                        <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider flex items-center justify-between">
                          <span>Audit Trail & Human Review Decisions</span>
                          <span className="text-[11px] font-normal text-gray-400">
                            {selectedCase.decisions?.length || 0} recorded
                          </span>
                        </h4>

                        {!selectedCase.decisions || selectedCase.decisions.length === 0 ? (
                          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-[12px] text-gray-400 text-center">
                            No human review decisions logged yet.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {selectedCase.decisions.map((dec, didx) => (
                              <div
                                key={dec.decision_id || didx}
                                className="p-3 bg-gray-50 border border-gray-200 rounded-lg space-y-1.5"
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span
                                      className={cn(
                                        'badge',
                                        dec.decision === 'APPROVE'
                                          ? 'badge-green'
                                          : dec.decision === 'REJECT'
                                          ? 'badge-red'
                                          : 'badge-amber'
                                      )}
                                    >
                                      {dec.decision}
                                    </span>
                                    <span className="text-[12px] font-bold text-gray-800">
                                      {dec.reviewer || 'Tax Reviewer'}
                                    </span>
                                    <span className="text-[11px] text-gray-400">({dec.reviewer_role})</span>
                                  </div>
                                  <span className="text-[11px] text-gray-400">{formatDate(dec.timestamp)}</span>
                                </div>
                                <p className="text-[12px] text-gray-600 pl-1">{dec.comment}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Section: Human Review & Lifecycle Actions */}
                      <div className="p-4 bg-white border border-gray-200 rounded-xl space-y-3">
                        <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider">
                          Submit Human Review & Governance
                        </h4>

                        <div>
                          <label className="text-[11px] font-semibold text-gray-500 block mb-1">
                            Auditor Comment / Statutory Rationale
                          </label>
                          <textarea
                            className="input w-full text-[12px] h-20 resize-none"
                            placeholder="Enter review findings, verified GSTR-2B details, or debit note references…"
                            value={reviewComment}
                            onChange={(e) => setReviewComment(e.target.value)}
                          />
                        </div>

                        <div className="flex items-center gap-2 flex-wrap pt-1">
                          <button
                            onClick={() =>
                              reviewMutation.mutate({
                                caseId: selectedCase.case_id,
                                decision: 'APPROVE',
                                comment: reviewComment,
                              })
                            }
                            disabled={reviewMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-sm"
                          >
                            <CheckCircle2 size={13} /> Approve Case
                          </button>

                          <button
                            onClick={() =>
                              reviewMutation.mutate({
                                caseId: selectedCase.case_id,
                                decision: 'REJECT',
                                comment: reviewComment,
                              })
                            }
                            disabled={reviewMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 transition-colors shadow-sm"
                          >
                            <X size={13} /> Reject Case
                          </button>

                          <button
                            onClick={() => resolveMutation.mutate(selectedCase.case_id)}
                            disabled={resolveMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 disabled:opacity-50 transition-colors"
                          >
                            Resolve Case
                          </button>

                          <button
                            onClick={() => closeMutation.mutate(selectedCase.case_id)}
                            disabled={closeMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold text-gray-700 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 transition-colors"
                          >
                            Close Case
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </motion.div>
            </div>
          </div>
        )}
      </AnimatePresence>
    </FadeIn>
  )
}
