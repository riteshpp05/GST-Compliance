import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate, Link } from 'react-router-dom'
import { Search, Filter, ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatCurrency, formatDate, statusBadge, truncate, cn } from '@/lib/utils'
import { FadeIn } from '@/components/ui/animations'
import { Skeleton, Badge, SectionHeader, Select, Input } from '@/components/ui/primitives'

function GatePips({ gates }) {
  if (!gates) return null
  const list = Array.isArray(gates) ? gates : Object.entries(gates).map(([k, v]) => ({ gate_id: k, ...v }))
  return (
    <div className="flex gap-1 items-center">
      {list.slice(0, 6).map((result, i) => {
        const pass = result?.status === 'PASS' || result?.passed === true
        const na   = result?.status === 'NOT_APPLICABLE' || result?.status === 'SKIPPED'
        const code = result?.gate_id || result?.rule_id || `G${i+1}`
        return <span key={code} title={`${code}: ${result?.status || (pass ? 'PASS' : 'FAIL')}`} className={cn('gate-dot', na ? 'gate-na' : pass ? 'gate-pass' : 'gate-fail')} />
      })}
    </div>
  )
}

export default function Compliance() {
  const navigate = useNavigate()
  const [search, setSearch]       = useState('')
  const [statusFilter, setStatus] = useState('ALL')
  const [riskFilter, setRisk]     = useState('ALL')
  const [page, setPage]           = useState(1)
  const PER = 25

  const { data, isLoading } = useQuery({
    queryKey: ['compliance', statusFilter, riskFilter, page],
    queryFn: () => gstApi.getComplianceResults({
      status: statusFilter !== 'ALL' ? statusFilter : undefined,
      risk:   riskFilter   !== 'ALL' ? riskFilter   : undefined,
      page, per_page: PER,
    }),
  })

  const invoices    = Array.isArray(data) ? data : (data?.invoices || data?.results || [])
  const total       = data?.total || invoices.length
  const totalPages  = Math.max(1, Math.ceil(total / PER))
  const filtered    = invoices.filter(item => {
    const inv = item.invoice || item
    if (!search) return true
    const q = search.toLowerCase()
    return (inv.invoice_number || '').toLowerCase().includes(q)
        || (inv.vendor_gstin || '').toLowerCase().includes(q)
        || (inv.vendor_name || '').toLowerCase().includes(q)
  })

  const riskColor = (level) => ({
    LOW: 'text-emerald-600', MODERATE: 'text-amber-600',
    MEDIUM: 'text-orange-600', HIGH: 'text-red-600', CRITICAL: 'text-red-800',
  })[level?.toUpperCase()] || 'text-gray-500'

  return (
    <div className="space-y-4">

      {/* Filters */}
      <FadeIn>
        <div className="panel py-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-48">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input className="input pl-8" placeholder="Search invoice, GSTIN, vendor…"
                value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <div className="flex items-center gap-1.5">
              <Filter size={13} className="text-gray-400" />
              <Select value={statusFilter} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
                <option value="ALL">All Status</option>
                <option value="COMPLIANT">Compliant</option>
                <option value="NON_COMPLIANT">Non-Compliant</option>
                <option value="PARTIAL">Partial</option>
              </Select>
            </div>
            <Select value={riskFilter} onChange={(e) => { setRisk(e.target.value); setPage(1) }}>
              <option value="ALL">All Risk</option>
              <option value="LOW">Low</option>
              <option value="MODERATE">Moderate</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </Select>
            {total > 0 && <span className="text-[12px] text-gray-400 ml-auto">{total.toLocaleString()} records</span>}
          </div>
        </div>
      </FadeIn>

      {/* Table */}
      <FadeIn delay={0.08}>
        <div className="card overflow-hidden">
          <div data-lenis-prevent className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Invoice #</th><th>Vendor</th><th>GSTIN</th>
                  <th>Date</th><th>Amount</th><th>Gates</th>
                  <th>Status</th><th>Risk</th><th></th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>{Array.from({ length: 9 }).map((_, j) => <td key={j}><Skeleton className="h-4 w-full" /></td>)}</tr>
                  ))
                ) : filtered.length === 0 ? (
                  <tr><td colSpan={9} className="py-16 text-center text-gray-400 text-[13px]">No records found</td></tr>
                ) : (
                  filtered.map((item, i) => {
                    const inv = item.invoice || item
                    const invId = inv.invoice_no || inv.invoice_number || inv.invoice_id || inv.doc_number || `INV-${i+1}`
                    const vendorName = inv.counterparty_name || inv.vendor_name || inv.party_name || '—'
                    const gstin = inv.counterparty_gstin || inv.vendor_gstin || '—'
                    const amount = inv.total_amt ?? inv.total_amount ?? inv.taxable_value_inr ?? 0
                    const date = inv.invoice_date || inv.posting_date
                    const gatesData = item.gates || item.gate_results || inv.gates || inv.gate_results

                    return (
                    <motion.tr
                      key={invId + '-' + i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.015 }}
                      onClick={() => navigate(`/invoice/${encodeURIComponent(invId)}`)}
                      className="group cursor-pointer hover:bg-blue-50/50"
                    >
                      <td>
                        <Link
                          to={`/invoice/${encodeURIComponent(invId)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-mono text-[12px] text-blue-600 font-bold hover:underline"
                        >
                          {truncate(invId, 16)}
                        </Link>
                      </td>
                      <td><span className="font-medium text-gray-800">{truncate(vendorName, 22)}</span></td>
                      <td><span className="font-mono text-[11px] text-gray-500">{gstin}</span></td>
                      <td className="text-gray-500">{formatDate(date)}</td>
                      <td className="font-semibold text-gray-800 tabular-nums">{formatCurrency(amount)}</td>
                      <td><GatePips gates={gatesData} /></td>
                      <td>
                        <span className={cn('badge', statusBadge(item.status || inv.compliance_status || inv.status))}>
                          {(item.status || inv.compliance_status || inv.status || '—').replace('_', ' ')}
                        </span>
                      </td>
                      <td><span className={cn('text-[12px] font-bold', riskColor(item.risk_level || inv.risk_level))}>{item.risk_level || inv.risk_level || '—'}</span></td>
                      <td>
                        <Link
                          to={`/invoice/${encodeURIComponent(invId)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded border border-blue-200 transition-colors"
                        >
                          View <ArrowRight size={11} />
                        </Link>
                      </td>
                    </motion.tr>
                  )})
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
              <span className="text-[12px] text-gray-500">Page {page} of {totalPages} · {total} records</span>
              <div className="flex gap-2">
                <button className="btn-secondary text-[12px] py-1 px-2.5" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                  <ChevronLeft size={13} /> Prev
                </button>
                <button className="btn-secondary text-[12px] py-1 px-2.5" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                  Next <ChevronRight size={13} />
                </button>
              </div>
            </div>
          )}
        </div>
      </FadeIn>
    </div>
  )
}
