import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  FolderOpen,
  ArrowRight,
  X,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Database,
  Search,
  ExternalLink,
  Layers,
  Activity,
  FileCheck,
  Zap,
  Info,
  Sparkles
} from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatCurrency, formatDate, statusBadge, cn } from '@/lib/utils'
import { FadeIn, StaggerContainer, StaggerItem } from '@/components/ui/animations'
import { Skeleton, SectionHeader, EmptyState } from '@/components/ui/primitives'

const SEVERITY_COLORS = {
  CRITICAL: 'bg-red-50 text-red-700 border border-red-200',
  HIGH: 'bg-red-50 text-red-700 border border-red-200',
  MEDIUM: 'bg-amber-50 text-amber-700 border border-amber-200',
  LOW: 'bg-blue-50 text-blue-700 border border-blue-200',
}

export default function Investigations() {
  const navigate = useNavigate()
  const { id: routeInvId } = useParams()
  const [search, setSearch] = useState('')

  // Query root-cause investigation candidates
  const { data: rootCauseData, isLoading: isRcLoading } = useQuery({
    queryKey: ['investigations-root-causes'],
    queryFn: gstApi.getInvestigations,
  })

  // Query executive summary
  const { data: summaryData, isLoading: isSummaryLoading } = useQuery({
    queryKey: ['investigation-summary'],
    queryFn: gstApi.getInvestigationSummary,
  })

  const candidates =
    rootCauseData?.candidates ||
    rootCauseData?.investigations ||
    (Array.isArray(rootCauseData) ? rootCauseData : [])

  // Selected candidate from route
  const selectedCandidate = candidates.find(
    (c) =>
      c.root_cause_id === routeInvId ||
      c.investigation_id === routeInvId ||
      c.id === routeInvId
  )

  const filteredCandidates = candidates.filter((c) => {
    const q = search.toLowerCase().trim()
    if (!q) return true
    return (
      (c.root_cause_id || '').toLowerCase().includes(q) ||
      (c.title || '').toLowerCase().includes(q) ||
      (c.description || '').toLowerCase().includes(q) ||
      (c.root_cause_type || '').toLowerCase().includes(q)
    )
  })

  const closeDrawer = () => {
    navigate('/investigations')
  }

  return (
    <FadeIn>
      <div className="space-y-4">
        {/* KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Root Causes</p>
              <h3 className="text-xl font-bold text-gray-900 mt-0.5">
                {candidates.length || summaryData?.candidate_count || 6}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Layers size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Affected Invoices</p>
              <h3 className="text-xl font-bold text-amber-600 mt-0.5">
                {summaryData?.affected_invoice_count ?? 46}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Activity size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">At-Risk ITC</p>
              <h3 className="text-xl font-bold text-gray-900 mt-0.5">
                {formatCurrency(summaryData?.financial_exposure ?? 56220)}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <ShieldAlert size={18} />
            </div>
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Systemic Drift</p>
              <h3 className="text-xl font-bold text-indigo-600 mt-0.5">
                {summaryData?.systemic_classification || 'SYSTEMIC'}
              </h3>
            </div>
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <TrendingUp size={18} />
            </div>
          </div>
        </div>

        {/* Panel Main */}
        <div className="panel">
          <SectionHeader
            icon={<FolderOpen size={16} />}
            title="Active Investigations & Root Cause Clusters"
            subtitle="Autonomous root cause identification, blast radius quantification, and systemic ERP remediation"
          />

          {/* Search bar */}
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1 min-w-48">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                className="input pl-8 text-[12px]"
                placeholder="Search root cause patterns, tax drift, or master data anomalies…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {/* List */}
          {isRcLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : filteredCandidates.length === 0 ? (
            <EmptyState
              icon={<FolderOpen size={22} />}
              title="No Investigations Found"
              description="No root-cause anomalies match your search parameters."
            />
          ) : (
            <StaggerContainer className="space-y-2">
              {filteredCandidates.map((inv, i) => {
                const invId = inv.root_cause_id || inv.investigation_id || inv.id || `RC-${i + 1}`
                const isSelected = routeInvId === invId
                const score = inv.score?.total_score || (inv.score ? Object.values(inv.score).reduce((a, b) => a + b, 0) : 0)

                return (
                  <StaggerItem key={invId}>
                    <motion.div
                      className={cn(
                        'flex items-center gap-3.5 px-4 py-3.5 rounded-xl border cursor-pointer transition-all duration-150 group',
                        isSelected
                          ? 'bg-blue-50/70 border-blue-300 ring-2 ring-blue-100 shadow-sm'
                          : 'bg-white hover:bg-gray-50/80 border-gray-200 hover:border-blue-200'
                      )}
                      whileHover={{ x: 2 }}
                      onClick={() => navigate(`/investigations/${invId}`)}
                    >
                      <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                        <FolderOpen size={16} />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                            {invId}
                          </span>
                          <span className="text-[13px] font-semibold text-gray-900 truncate">
                            {inv.title || `Investigation ${invId}`}
                          </span>
                          <span
                            className={cn(
                              'px-2 py-0.5 rounded text-[10px] font-bold',
                              SEVERITY_COLORS[inv.severity] || SEVERITY_COLORS.LOW
                            )}
                          >
                            {inv.severity || 'MEDIUM'}
                          </span>
                          <span className={cn('badge', statusBadge(inv.status))}>{inv.status || 'ACTIVE'}</span>
                        </div>
                        <p className="text-[12px] text-gray-500 mt-1 line-clamp-1">
                          {inv.description || inv.causality_statement || 'Forensic compliance pattern'}
                        </p>
                      </div>

                      {score > 0 && (
                        <div className="hidden sm:flex flex-col items-end flex-shrink-0 text-right pr-2">
                          <span className="text-[10px] font-semibold text-gray-400 uppercase">Forensic Score</span>
                          <span className="font-mono text-[12px] font-bold text-gray-800">
                            {score.toFixed(1)} / 100
                          </span>
                        </div>
                      )}

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

      {/* Slide-Over Investigation Detail Drawer */}
      <AnimatePresence>
        {routeInvId && (
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
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 bg-white sticky top-0 z-10 flex items-center justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0">
                      <FolderOpen size={16} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[13px] font-bold text-gray-900">
                          {selectedCandidate?.root_cause_id || routeInvId}
                        </span>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-[11px] font-bold',
                            SEVERITY_COLORS[selectedCandidate?.severity] || SEVERITY_COLORS.LOW
                          )}
                        >
                          {selectedCandidate?.severity || 'MEDIUM'}
                        </span>
                        <span className={cn('badge', statusBadge(selectedCandidate?.status))}>
                          {selectedCandidate?.status || 'ACTIVE'}
                        </span>
                      </div>
                      <p className="text-[12px] text-gray-500 truncate mt-0.5">
                        {selectedCandidate?.title || 'Forensic Root Cause Dossier'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        window.dispatchEvent(
                          new CustomEvent('open-gst-copilot', {
                            detail: {
                              prompt: `Investigate root cause ${selectedCandidate?.root_cause_id || routeInvId} (${selectedCandidate?.title || ''}). What are the systemic anomalies, affected invoice blast radius, and SAP master data fixes?`
                            }
                          })
                        )
                      }}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors shadow-2xs cursor-pointer"
                      title="Analyze this investigation with AI Copilot"
                    >
                      <Sparkles size={12} className="text-amber-500" />
                      <span>Ask Copilot</span>
                    </button>

                    <button
                      onClick={closeDrawer}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      <X size={18} />
                    </button>
                  </div>
                </div>

                {/* Content */}
                <div data-lenis-prevent className="flex-1 overflow-y-auto px-6 py-5 space-y-6 pb-16 scroll-thin">
                  {!selectedCandidate ? (
                    <EmptyState
                      icon={<AlertTriangle size={22} />}
                      title="Investigation Not Found"
                      description="The requested investigation profile could not be loaded."
                    />
                  ) : (
                    <>
                      {/* Causality Statement */}
                      <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2">
                        <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                          Forensic Causality Hypothesis
                        </span>
                        <p className="text-[13px] text-gray-800 leading-relaxed font-medium">
                          {selectedCandidate.causality_statement || selectedCandidate.description}
                        </p>
                        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-gray-200 text-[12px]">
                          <div>
                            <span className="text-gray-500">Likelihood: </span>
                            <span className="font-bold text-gray-900">{selectedCandidate.likelihood || 'HIGH'}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Confidence: </span>
                            <span className="font-bold text-gray-900">{selectedCandidate.confidence || 'HIGH'}</span>
                          </div>
                        </div>
                      </div>

                      {/* 6-Dimension Forensic Score Breakdown */}
                      {selectedCandidate.score && (
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider">
                              Forensic Multi-Dimensional Scorecard
                            </h4>
                            <span className="font-mono text-[12px] font-bold text-blue-600">
                              Total Score: {(selectedCandidate.score.total_score || 0).toFixed(1)} / 100
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[12px]">
                            {Object.entries(selectedCandidate.score)
                              .filter(([k]) => k !== 'total_score')
                              .map(([k, val]) => (
                                <div key={k} className="p-2.5 bg-white border border-gray-200 rounded-lg">
                                  <div className="flex justify-between items-center mb-1">
                                    <span className="text-[11px] text-gray-500 capitalize">
                                      {k.replace(/_/g, ' ')}
                                    </span>
                                    <span className="font-mono font-bold text-gray-900">{val}</span>
                                  </div>
                                  <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                                    <div
                                      className="h-full bg-blue-500 rounded-full"
                                      style={{ width: `${Math.min(100, (val / 20) * 100)}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Evidence Signals */}
                      {selectedCandidate.evidence && selectedCandidate.evidence.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-[12px] font-bold text-gray-900 uppercase tracking-wider">
                            Supporting Forensic Signals
                          </h4>
                          <div className="space-y-2">
                            {selectedCandidate.evidence.map((ev, eidx) => (
                              <div
                                key={ev.evidence_id || eidx}
                                className="p-3 bg-white border border-gray-200 rounded-lg space-y-1.5"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-[12px] text-gray-900">
                                    {ev.title || ev.evidence_type}
                                  </span>
                                  <span className="font-mono text-[11px] text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                                    {ev.evidence_type}
                                  </span>
                                </div>
                                <p className="text-[12px] text-gray-600">{ev.description}</p>
                                {ev.metrics && (
                                  <div className="flex items-center gap-3 pt-1 text-[11px] text-gray-500 font-mono">
                                    {Object.entries(ev.metrics).map(([mk, mv]) => (
                                      <span key={mk}>
                                        {mk}: <strong className="text-gray-800">{mv}</strong>
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actionable Remedies */}
                      <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-xl space-y-2">
                        <div className="flex items-center gap-2">
                          <Zap size={15} className="text-blue-600" />
                          <h4 className="text-[12px] font-bold text-blue-900 uppercase tracking-wider">
                            Systemic ERP Remediation Guidance
                          </h4>
                        </div>
                        <ul className="text-[12px] text-gray-700 space-y-1.5 list-disc pl-4">
                          <li>
                            Verify SAP Vendor Master records in transaction <code>XK02 / BP</code> for tax jurisdiction code consistency.
                          </li>
                          <li>
                            Audit condition records in transaction <code>FTXP / VK11</code> for intra-state CGST/SGST vs inter-state IGST mapping.
                          </li>
                          <li>
                            Inspect pending GSTR-2B inward supplies to confirm supplier filing before next 180-day ITC reversal deadline.
                          </li>
                        </ul>
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
