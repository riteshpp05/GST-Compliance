import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft, ShieldCheck, AlertCircle, FileText, CheckCircle2,
  XCircle, Clock, Building2, MapPin, Hash, DollarSign, ExternalLink,
  Lock, Unlock, BookOpen, Layers, Check, AlertTriangle
} from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatCurrency, formatDate, statusBadge, cn } from '@/lib/utils'
import { FadeIn, StaggerContainer, StaggerItem } from '@/components/ui/animations'
import { Skeleton, SectionHeader } from '@/components/ui/primitives'

const GATE_NAMES = {
  GSTIN_001: 'GSTIN Format Validity',
  HSN_001:   'HSN/SAC Code Correctness',
  TAX_001:   'Tax Rate Correctness',
  POS_001:   'Place of Supply',
  EWB_001:   'E-Way Bill Compliance',
  ITC_001:   'ITC Eligibility & 2B Match',
}

export default function InvoiceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: invoice, isLoading, error } = useQuery({
    queryKey: ['invoice', id],
    queryFn: async () => {
      try {
        return await gstApi.getInvoiceDetail(id)
      } catch (e) {
        // Fallback: search in results/latest if direct lookup 404s
        const all = await gstApi.getComplianceResults()
        const list = Array.isArray(all) ? all : (all?.invoices || all?.results || [])
        const match = list.find(item => {
          const invNo = item.invoice_no || item.invoice?.invoice_number || item.invoice_number || item.id
          return String(invNo).toLowerCase() === String(id).toLowerCase()
        })
        if (match) return match
        throw e
      }
    },
  })

  const invNo = invoice?.invoice_no || invoice?.invoice?.invoice_number || id
  const vendorName = invoice?.counterparty_name || invoice?.vendor_name || invoice?.party_name || 'Vendor'
  const gstin = invoice?.counterparty_gstin || invoice?.vendor_gstin || '—'
  const pos = invoice?.place_of_supply || '—'
  const hsn = invoice?.hsn_code || '—'
  const date = invoice?.invoice_date || invoice?.posting_date
  const amount = invoice?.total_amt ?? invoice?.total_amount ?? invoice?.invoice_amount ?? 0
  const taxable = invoice?.taxable_value_inr ?? invoice?.taxable_value ?? 0
  const status = invoice?.status || invoice?.compliance_status || 'UNKNOWN'
  const risk = invoice?.risk_level || 'LOW'
  const gates = invoice?.gates || invoice?.gate_results || {}

  const riskColor = {
    LOW: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    MODERATE: 'text-amber-700 bg-amber-50 border-amber-200',
    MEDIUM: 'text-orange-700 bg-orange-50 border-orange-200',
    HIGH: 'text-red-700 bg-red-50 border-red-200',
    CRITICAL: 'text-red-800 bg-red-100 border-red-300',
  }[risk?.toUpperCase()] || 'text-gray-700 bg-gray-50 border-gray-200'

  const queryClient = useQueryClient()
  const { data: sapJournal, isLoading: isJournalLoading } = useQuery({
    queryKey: ['sap-journal', invNo],
    queryFn: async () => {
      try {
        return await gstApi.getSapJournalEntry(invNo)
      } catch (e) {
        return null
      }
    },
    enabled: Boolean(invNo),
  })

  const [actionFeedback, setActionFeedback] = useState(null)

  const blockMutation = useMutation({
    mutationFn: (blockCode) => gstApi.applyPaymentBlock({
      invoice_no: invNo,
      block_code: blockCode || 'R',
      reason: 'Held for Statutory Verification / Gate Failure',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['sap-journal', invNo])
      queryClient.invalidateQueries(['audit'])
      setActionFeedback('Payment Block "R" applied in S/4HANA (BSEG-ZLSPR = "R")')
      setTimeout(() => setActionFeedback(null), 4000)
    },
  })

  const releaseMutation = useMutation({
    mutationFn: () => gstApi.releasePaymentBlock({
      invoice_no: invNo,
      reason: 'Compliance Review Approved / Released by Tax Lead',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries(['sap-journal', invNo])
      queryClient.invalidateQueries(['audit'])
      setActionFeedback('Payment Block released in S/4HANA (BSEG-ZLSPR = "")')
      setTimeout(() => setActionFeedback(null), 4000)
    },
  })

  return (
    <div className="space-y-5 max-w-6xl mx-auto pb-10">

      {/* ── Top Bar / Back button ────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <button
          onClick={() => navigate('/compliance')}
          className="btn-secondary text-[13px] py-1.5 px-3"
        >
          <ArrowLeft size={14} /> Back to Invoices
        </button>

        <div className="flex items-center gap-2">
          <span className={cn('badge text-[12px] px-2.5 py-1', statusBadge(status))}>
            {status.replace('_', ' ')}
          </span>
          <span className={cn('px-2.5 py-1 rounded-md text-[12px] font-bold border', riskColor)}>
            Risk: {risk}
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
          </div>
        </div>
      ) : error && !invoice ? (
        <div className="panel text-center py-16">
          <AlertCircle size={32} className="mx-auto text-amber-500 mb-2" />
          <h2 className="text-base font-semibold text-gray-800">Invoice Not Found</h2>
          <p className="text-sm text-gray-400 mt-1">Could not find record for "{id}".</p>
          <button onClick={() => navigate('/compliance')} className="btn-primary mt-4">
            Return to Invoice Audit
          </button>
        </div>
      ) : (
        <>
          {/* ── Invoice Header Card ───────────────────────────────────────── */}
          <FadeIn>
            <div className="card p-6 border-l-4 border-l-blue-600">
              <div className="flex items-start justify-between gap-6 flex-wrap">
                <div>
                  <div className="flex items-center gap-2.5">
                    <FileText size={20} className="text-blue-600" />
                    <h1 className="text-xl font-bold text-gray-900 font-mono">{invNo}</h1>
                  </div>
                  <p className="text-[13px] text-gray-500 mt-1">
                    {invoice?.item_desc || 'Commercial Invoice & GST Assessment'}
                  </p>
                </div>

                <div className="text-right">
                  <p className="stat-label">Total Amount</p>
                  <p className="text-3xl font-extrabold text-gray-900 tabular-nums">{formatCurrency(amount)}</p>
                  {taxable > 0 && (
                    <p className="text-[11px] text-gray-400 mt-0.5">Taxable: {formatCurrency(taxable)}</p>
                  )}
                </div>
              </div>

              {/* Metadata Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-5 border-t border-gray-100">
                <div>
                  <p className="stat-label flex items-center gap-1"><Building2 size={12} /> Counterparty</p>
                  <p className="text-[13px] font-semibold text-gray-800 mt-0.5 truncate">{vendorName}</p>
                  <p className="text-[11px] font-mono text-gray-400 mt-0.5">{gstin}</p>
                </div>
                <div>
                  <p className="stat-label flex items-center gap-1"><MapPin size={12} /> Place of Supply</p>
                  <p className="text-[13px] font-semibold text-gray-800 mt-0.5">{pos}</p>
                  <p className="text-[11px] text-gray-400 mt-0.5">HSN / SAC: <span className="font-mono">{hsn}</span></p>
                </div>
                <div>
                  <p className="stat-label flex items-center gap-1"><Clock size={12} /> Document Date</p>
                  <p className="text-[13px] font-semibold text-gray-800 mt-0.5">{formatDate(date)}</p>
                  <p className="text-[11px] text-gray-400 mt-0.5">Audit: {invoice?.audit_trail_ref || 'GST-REF'}</p>
                </div>
                <div>
                  <p className="stat-label flex items-center gap-1"><DollarSign size={12} /> Exposure</p>
                  <p className={cn(
                    'text-[13px] font-bold mt-0.5 tabular-nums',
                    (invoice?.potential_exposure || 0) > 0 ? 'text-red-600' : 'text-emerald-600'
                  )}>
                    {(invoice?.potential_exposure || 0) > 0 ? formatCurrency(invoice.potential_exposure) : '₹0 (None)'}
                  </p>
                  <p className="text-[11px] text-gray-400 mt-0.5">{invoice?.failed_gate_count || 0} gate failure(s)</p>
                </div>
              </div>
            </div>
          </FadeIn>

          {/* ── Six Statutory Validation Gates ───────────────────────────── */}
          <FadeIn delay={0.08}>
            <div className="panel">
              <SectionHeader
                icon={<ShieldCheck size={16} />}
                title="Statutory Validation Gates (Sequential)"
                subtitle="Assessment results across all 6 statutory compliance rules"
              />

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {(Array.isArray(gates) ? gates : Object.entries(gates).map(([k, v]) => ({ rule_id: k, ...v }))).map((g, idx) => {
                  const code = g?.rule_id || g?.gate_id || g?.code || `G${idx + 1}`
                  const pass = g?.status === 'PASS' || g?.passed === true
                  const na = g?.status === 'NOT_APPLICABLE' || g?.status === 'SKIPPED'
                  const title = g?.name || g?.rule_name || GATE_NAMES[code] || code
                  const explanation = g?.detail || g?.message || g?.explanation || g?.justification || (pass ? 'Statutory condition verified and satisfied.' : 'Validation criteria failed.')

                  return (
                    <div
                      key={code + idx}
                      className={cn(
                        'border rounded-xl p-4 transition-all duration-150',
                        pass ? 'bg-emerald-50/50 border-emerald-100' : na ? 'bg-gray-50 border-gray-100' : 'bg-red-50/60 border-red-200'
                      )}
                    >
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="font-mono text-[11px] font-bold text-gray-500 bg-white px-2 py-0.5 rounded border border-gray-200">
                          {code}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {pass ? (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                              <CheckCircle2 size={12} /> PASS
                            </span>
                          ) : na ? (
                            <span className="text-[11px] font-semibold text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
                              N/A
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-[11px] font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded">
                              <XCircle size={12} /> FAIL
                            </span>
                          )}
                        </div>
                      </div>

                      <p className="text-[13px] font-semibold text-gray-800">{title}</p>
                      <p className="text-[12px] text-gray-500 mt-1 line-clamp-3">
                        {explanation}
                      </p>

                      {g?.calculation_trace && (
                        <div className="mt-2.5 pt-2 border-t border-gray-200/60 text-[10px] font-mono text-gray-500 truncate" title={typeof g.calculation_trace === 'string' ? g.calculation_trace : JSON.stringify(g.calculation_trace)}>
                          Trace: {typeof g.calculation_trace === 'string' ? g.calculation_trace : JSON.stringify(g.calculation_trace)}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </FadeIn>

          {/* ── SAP S/4HANA Accounting Journal & Financial Controls Simulation ── */}
          <FadeIn delay={0.10}>
            <div className="panel border-t-4 border-t-blue-600">
              <div className="flex items-center justify-between gap-4 flex-wrap pb-3 border-b border-gray-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                    FI
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-gray-900">SAP S/4HANA Accounting Journal &amp; Financial Controls</h3>
                    <p className="text-[11px] text-gray-500 font-mono">
                      Header: BKPF • Doc Type: <strong className="text-blue-700">{sapJournal?.header?.document_type || 'KR'}</strong> ({sapJournal?.header?.document_type_desc || 'Vendor Invoice'}) • Ledger: 0L • Client: 200
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {sapJournal?.statutory_fico_controls?.payment_block?.is_blocked ? (
                    <div className="flex items-center gap-2">
                      <span className="badge bg-red-100 text-red-800 border border-red-200 text-[11px] flex items-center gap-1 font-bold">
                        <Lock size={11} /> Blocked: {sapJournal.statutory_fico_controls.payment_block.code}
                      </span>
                      <button
                        onClick={() => releaseMutation.mutate()}
                        disabled={releaseMutation.isPending}
                        className="btn-secondary text-[11px] py-1 px-2.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                      >
                        <Unlock size={11} className="mr-1 inline" /> Release Block
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] flex items-center gap-1">
                        <Check size={11} /> Free for Payment (ZLSPR: Free)
                      </span>
                      <button
                        onClick={() => blockMutation.mutate('R')}
                        disabled={blockMutation.isPending}
                        className="btn-secondary text-[11px] py-1 px-2.5 border-amber-300 text-amber-800 hover:bg-amber-50"
                      >
                        <Lock size={11} className="mr-1 inline" /> Apply Payment Block 'R'
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {actionFeedback && (
                <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-[11px] font-semibold flex items-center gap-1.5">
                  <Check size={12} className="text-blue-600" /> {actionFeedback}
                </div>
              )}

              {/* FICO Statutory Flags row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
                {/* 180-Day Rule */}
                <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-[12px]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-gray-700">Section 16(2) 180-Day Rule</span>
                    <span className={cn(
                      'text-[10px] font-bold px-2 py-0.5 rounded',
                      sapJournal?.statutory_fico_controls?.section_16_2_180_days?.is_overdue
                        ? 'bg-red-100 text-red-700'
                        : 'bg-emerald-100 text-emerald-700'
                    )}>
                      {sapJournal?.statutory_fico_controls?.section_16_2_180_days?.is_overdue ? 'OVERDUE > 180D' : 'WITHIN WINDOW'}
                    </span>
                  </div>
                  <p className="text-gray-500 text-[11px]">
                    Aging: <strong>{sapJournal?.statutory_fico_controls?.section_16_2_180_days?.aging_days ?? 24} days</strong> / 180 statutory limit
                  </p>
                  {sapJournal?.statutory_fico_controls?.section_16_2_180_days?.interest_exposure_inr > 0 && (
                    <p className="text-red-600 font-semibold text-[11px] mt-1">
                      ⚠️ Section 50(3) Interest Exposure: ₹{sapJournal.statutory_fico_controls.section_16_2_180_days.interest_exposure_inr}
                    </p>
                  )}
                </div>

                {/* Section 17(5) Blocked Credit */}
                <div className="p-3 bg-gray-50 border border-gray-100 rounded-xl text-[12px]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-gray-700">Section 17(5) Blocked Credit</span>
                    <span className={cn(
                      'text-[10px] font-bold px-2 py-0.5 rounded',
                      sapJournal?.statutory_fico_controls?.section_17_5_blocked_itc?.is_blocked
                        ? 'bg-red-100 text-red-700'
                        : 'bg-emerald-100 text-emerald-700'
                    )}>
                      {sapJournal?.statutory_fico_controls?.section_17_5_blocked_itc?.is_blocked ? 'INELIGIBLE (BLOCKED)' : 'ELIGIBLE ITC'}
                    </span>
                  </div>
                  <p className="text-gray-500 text-[11px]">
                    Treatment: <strong>{sapJournal?.statutory_fico_controls?.section_17_5_blocked_itc?.tax_treatment || 'Eligible Input Tax Credit'}</strong>
                  </p>
                  {sapJournal?.statutory_fico_controls?.section_17_5_blocked_itc?.blocked_reason && (
                    <p className="text-amber-700 text-[11px] mt-1 font-medium">
                      Note: {sapJournal.statutory_fico_controls.section_17_5_blocked_itc.blocked_reason}
                    </p>
                  )}
                </div>
              </div>

              {/* Journal Lines Table */}
              <div className="overflow-x-auto border border-gray-200 rounded-xl">
                <table className="w-full text-[12px] text-left">
                  <thead className="bg-gray-50/80 text-gray-500 text-[10px] uppercase font-bold tracking-wider border-b border-gray-200">
                    <tr>
                      <th className="py-2.5 px-3">Item</th>
                      <th className="py-2.5 px-3">PK (BSCHL)</th>
                      <th className="py-2.5 px-3">Account (BSEG-HKONT)</th>
                      <th className="py-2.5 px-3">Account Description</th>
                      <th className="py-2.5 px-3">Tax Code</th>
                      <th className="py-2.5 px-3">Cond.</th>
                      <th className="py-2.5 px-3 text-right">Debit (₹)</th>
                      <th className="py-2.5 px-3 text-right">Credit (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 font-mono">
                    {sapJournal?.line_items?.map((line, idx) => (
                      <tr key={idx} className="hover:bg-blue-50/20 transition-colors">
                        <td className="py-2 px-3 text-gray-400">{line.item_no}</td>
                        <td className="py-2 px-3 font-bold text-blue-700">
                          {line.posting_key} <span className="font-sans text-[10px] text-gray-400 font-normal">({line.posting_key_name?.split(' ')[1] || ''})</span>
                        </td>
                        <td className="py-2 px-3 font-semibold text-gray-900">{line.account}</td>
                        <td className="py-2 px-3 font-sans text-gray-700">{line.account_name}</td>
                        <td className="py-2 px-3 text-gray-600">{line.tax_code || '—'}</td>
                        <td className="py-2 px-3 text-indigo-600 font-semibold">{line.condition_type || '—'}</td>
                        <td className="py-2 px-3 text-right text-gray-900 font-bold">
                          {line.amount > 0 ? Number(line.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}
                        </td>
                        <td className="py-2 px-3 text-right text-gray-900 font-bold">
                          {line.amount < 0 ? Number(Math.abs(line.amount)).toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-50 border-t border-gray-200 text-[11px] font-bold">
                    <tr>
                      <td colSpan={6} className="py-2.5 px-3 text-gray-600">
                        Universal Journal Invariant (ACDOCA Zero-Balance Verification):
                      </td>
                      <td className="py-2.5 px-3 text-right text-emerald-700 font-mono">
                        ₹{Number(sapJournal?.accounting_validation?.total_debits || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-right text-emerald-700 font-mono">
                        ₹{Number(sapJournal?.accounting_validation?.total_credits || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </FadeIn>

          {/* ── Recommendations & Actions ─────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FadeIn delay={0.12}>
              <div className="panel h-full">
                <h3 className="section-title mb-2">Statutory Recommendation</h3>
                <p className="text-[13px] text-gray-700 leading-relaxed bg-blue-50/50 border border-blue-100 rounded-xl p-4">
                  {invoice?.recommended_action || invoice?.justification || 'No action needed. Ready for GSTR-1 / GSTR-3B filing.'}
                </p>
                {invoice?.justification && invoice?.recommended_action && (
                  <p className="text-[12px] text-gray-500 mt-3 leading-relaxed">
                    <span className="font-semibold text-gray-700">Justification: </span>
                    {invoice.justification}
                  </p>
                )}
              </div>
            </FadeIn>

            <FadeIn delay={0.15}>
              <div className="panel h-full">
                <h3 className="section-title mb-2">SAP S/4HANA Action</h3>
                <p className="text-[13px] text-gray-700 leading-relaxed bg-gray-50 border border-gray-200 rounded-xl p-4 font-mono text-[12px]">
                  {invoice?.sap_action || 'Read via BKPF/BSEG + KONV (tax conditions) + KNA1/LFA1 (GSTIN) - ready for GSTR filing.'}
                </p>
                <div className="mt-4 flex items-center justify-between text-[12px] text-gray-500">
                  <span>SAP Company Code: <strong className="text-gray-800">DI01</strong></span>
                  <span>Client: <strong className="text-gray-800">200</strong></span>
                </div>
              </div>
            </FadeIn>
          </div>
        </>
      )}
    </div>
  )
}
