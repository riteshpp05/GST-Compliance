import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  PieChart, Pie, Cell, BarChart, Bar,
  ResponsiveContainer, XAxis, YAxis, Tooltip,
} from 'recharts'
import {
  ShieldCheck, AlertTriangle, FileText, CheckCircle2, XCircle, TrendingUp,
  Zap, ArrowUpRight, Database, RefreshCw, Layers, Check, Server
} from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatCurrency, formatNumber, cn } from '@/lib/utils'
import { FadeIn, StaggerContainer, StaggerItem } from '@/components/ui/animations'
import { Skeleton, Badge, SectionHeader, Dot } from '@/components/ui/primitives'

/* ── Animated counter ─────────────────────────────────────────────── */
function Counter({ to, duration = 1200 }) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!to) return
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1)
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * to))
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [to])
  return <>{formatNumber(val)}</>
}

/* ── KPI card ─────────────────────────────────────────────────────── */
function KpiCard({ icon: Icon, label, value, sub, color = 'blue', loading, delay = 0 }) {
  const styles = {
    blue:   { wrap: 'bg-blue-50 border-blue-100',   icon: 'text-blue-600',   val: 'text-blue-700' },
    green:  { wrap: 'bg-emerald-50 border-emerald-100', icon: 'text-emerald-600', val: 'text-emerald-700' },
    red:    { wrap: 'bg-red-50 border-red-100',     icon: 'text-red-600',    val: 'text-red-700' },
    amber:  { wrap: 'bg-amber-50 border-amber-100', icon: 'text-amber-600',  val: 'text-amber-700' },
  }
  const s = styles[color]

  if (loading) return <div className="kpi-card"><Skeleton className="h-24" /></div>

  return (
    <motion.div
      className="kpi-card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.38, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -1, boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
    >
      <div className={cn('w-9 h-9 rounded-xl border flex items-center justify-center mb-3', s.wrap)}>
        <Icon size={17} className={s.icon} />
      </div>
      <div className={cn('text-2xl font-bold tabular-nums', s.val)}>
        <Counter to={typeof value === 'number' ? value : 0} />
      </div>
      <div className="text-[12px] font-medium text-gray-500 mt-0.5">{label}</div>
      {sub && <div className="text-[11px] text-gray-400 mt-1">{sub}</div>}
    </motion.div>
  )
}

/* ── Custom tooltip ───────────────────────────────────────────────── */
const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-[12px] shadow-lg">
      {label && <p className="font-semibold text-gray-800 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="flex items-center gap-1.5 text-gray-600">
          <span className="w-2 h-2 rounded-full" style={{ background: p.fill || p.color }} />
          {p.name}: <span className="font-bold text-gray-900">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

const GATE_COLORS = ['#3B82F6','#059669','#D97706','#DC2626','#7C3AED','#0891B2']

export default function Overview() {
  const queryClient = useQueryClient()
  const { data: overview, isLoading } = useQuery({
    queryKey: ['overview'],
    queryFn: gstApi.getDashboardOverview,
    refetchInterval: 30000,
  })

  const { data: sapStatus, isLoading: isSapLoading } = useQuery({
    queryKey: ['sap-status'],
    queryFn: gstApi.getSapStatus,
    refetchInterval: 30000,
  })

  const [syncSuccessMsg, setSyncSuccessMsg] = useState(null)
  const syncMutation = useMutation({
    mutationFn: gstApi.syncSapHana,
    onSuccess: (res) => {
      queryClient.invalidateQueries(['overview'])
      queryClient.invalidateQueries(['compliance'])
      queryClient.invalidateQueries(['audit'])
      queryClient.invalidateQueries(['sap-status'])
      setSyncSuccessMsg(res?.message || 'Synchronized live documents from SAP HANA Database')
      setTimeout(() => setSyncSuccessMsg(null), 5000)
    },
  })

  const kpis = overview?.kpis || {}
  const total        = kpis.total_invoices || 0
  const compliant    = kpis.compliant || 0
  const nonCompliant = kpis.non_compliant || 0
  const needsReview  = kpis.needs_review || kpis.partial || 0
  const exposure     = kpis.potential_exposure ?? kpis.total_exposure ?? 0
  const rate         = total ? Math.round((compliant / total) * 100) : 0

  const pieData = [
    { name: 'Compliant',     value: compliant,    color: '#059669' },
    { name: 'Needs Review',  value: needsReview,  color: '#D97706' },
    { name: 'Non-Compliant', value: nonCompliant,  color: '#DC2626' },
  ].filter(d => d.value > 0)

  const rawGates = overview?.gate_failures || overview?.gate_failure_summary || {}
  const gateData = Object.entries(rawGates).map(([k, v], i) => ({
    gate: k.length > 15 ? k.split(' ')[0] + ' ' + (k.split(' ')[1] || '') : k,
    code: k,
    failures: v,
    fill: GATE_COLORS[i % GATE_COLORS.length],
  }))

  return (
    <div className="space-y-5">

      {/* ── SAP S/4HANA & HANA Database Sync Station ──────────────────── */}
      <FadeIn>
        <div className="card p-4 border border-blue-100 bg-gradient-to-r from-blue-50/60 via-white to-emerald-50/40">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
                <Database size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-gray-900 tracking-tight">SAP S/4HANA &amp; HANA Database Connectivity</h3>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                    <Dot color="green" pulse /> Live In-Memory Columnar Store
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-gray-500 mt-1 flex-wrap">
                  <span>Host: <strong className="font-mono text-gray-700">{sapStatus?.hana_host || 'hana-s4h-db01.corp.internal'}:{sapStatus?.hana_port || 39015}</strong></span>
                  <span>•</span>
                  <span>Client: <strong className="text-gray-700">{sapStatus?.sap_client || '200'}</strong></span>
                  <span>•</span>
                  <span>Company Code: <strong className="text-gray-700">{sapStatus?.company_code || 'DI01'}</strong></span>
                  <span>•</span>
                  <span>Schema: <strong className="font-mono text-gray-700">{sapStatus?.hana_schema || 'SAPABAP1'}</strong></span>
                  <span>•</span>
                  <span>Active Tables: <strong className="text-gray-700">ACDOCA, BKPF, BSEG, BSIK</strong></span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
                className={cn(
                  'btn-secondary text-[12px] py-1.5 px-3 flex items-center gap-1.5 shadow-sm border-blue-200 text-blue-700 hover:bg-blue-50',
                  syncMutation.isPending && 'opacity-60 cursor-not-allowed'
                )}
              >
                <RefreshCw size={13} className={cn(syncMutation.isPending && 'animate-spin text-blue-600')} />
                {syncMutation.isPending ? 'Syncing from HANA DB...' : 'Sync from HANA DB'}
              </button>
            </div>
          </div>

          {syncSuccessMsg && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-[12px] flex items-center gap-2 font-medium"
            >
              <Check size={14} className="text-emerald-600 shrink-0" />
              <span>{syncSuccessMsg}</span>
            </motion.div>
          )}
        </div>
      </FadeIn>

      {/* ── Health banner ─────────────────────────────────────────────── */}
      <FadeIn>
        <div className="card p-6 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div>
              <p className="stat-label mb-1">Compliance Health Score</p>
              <div className="flex items-end gap-3">
                <span className={cn(
                  'text-4xl font-black tabular-nums',
                  rate >= 80 ? 'text-emerald-600' : rate >= 60 ? 'text-amber-600' : 'text-red-600'
                )}>
                  {isLoading ? '—' : `${rate}%`}
                </span>
                <span className="text-gray-400 text-[13px] mb-1">invoices fully compliant</span>
              </div>
              <div className="mt-2 w-72 max-w-full">
                <div className="progress-bar">
                  <motion.div
                    className="progress-fill"
                    style={{
                      background: rate >= 80 ? '#059669' : rate >= 60 ? '#D97706' : '#DC2626'
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${rate}%` }}
                    transition={{ duration: 1.2, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {[
                { label: '6 Statutory Gates', color: 'blue' },
                { label: '24+ Active Rules',  color: 'amber' },
                { label: 'Engine Online',     color: 'green', dot: true },
              ].map((s) => (
                <div key={s.label} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg">
                  {s.dot && <Dot color="green" pulse />}
                  <span className="text-[12px] font-semibold text-gray-600">{s.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </FadeIn>

      {/* ── KPI row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={FileText}     label="Total Invoices"   value={total}        color="blue"  delay={0.05} loading={isLoading} />
        <KpiCard icon={CheckCircle2} label="Compliant"        value={compliant}    color="green" delay={0.10} loading={isLoading} />
        <KpiCard icon={XCircle}      label="Non-Compliant"    value={nonCompliant} color="red"   delay={0.15} loading={isLoading} />
        <KpiCard icon={TrendingUp}   label="Tax Exposure (₹)" value={exposure}     color="amber" delay={0.20} loading={isLoading}
          sub={exposure > 0 ? 'Requires resolution' : 'No exposure'} />
      </div>

      {/* ── Charts row ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Donut */}
        <FadeIn delay={0.15}>
          <div className="panel">
            <SectionHeader title="Compliance Breakdown" subtitle="Invoice status distribution" />
            {isLoading ? <Skeleton className="h-44" /> : (
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={pieData} innerRadius={48} outerRadius={76} paddingAngle={3}
                         dataKey="value" startAngle={90} endAngle={-270}>
                      {pieData.map((e, i) => <Cell key={i} fill={e.color} stroke="transparent" />)}
                    </Pie>
                    <Tooltip content={<Tip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2.5 flex-1">
                  {pieData.map((d) => (
                    <div key={d.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
                        <span className="text-[12px] text-gray-600">{d.name}</span>
                      </div>
                      <span className="text-[13px] font-bold text-gray-900 tabular-nums">{formatNumber(d.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </FadeIn>

        {/* Gate failure bar */}
        <FadeIn delay={0.2}>
          <div className="panel">
            <SectionHeader title="Gate Failure Analysis" subtitle="Failures per statutory gate" />
            {isLoading ? <Skeleton className="h-44" /> : gateData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={gateData} barCategoryGap="30%">
                  <XAxis dataKey="gate" tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<Tip />} cursor={{ fill: 'rgba(0,0,0,0.03)' }} />
                  <Bar dataKey="failures" radius={[3,3,0,0]}>
                    {gateData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-44 text-gray-400 text-[13px]">
                Run the pipeline to see gate data
              </div>
            )}
          </div>
        </FadeIn>
      </div>

      {/* ── Six gates status ──────────────────────────────────────────── */}
      <FadeIn delay={0.25}>
        <div className="panel">
          <SectionHeader title="Statutory Validation Gates" subtitle="Sequential compliance checks applied to every invoice" />
          <StaggerContainer className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { id: 'G1', label: 'GSTIN Format',    key: 'GSTIN Format Validity', code: 'GSTIN_001' },
              { id: 'G2', label: 'HSN/SAC Code',    key: 'HSN/SAC Code Correctness', code: 'HSN_001' },
              { id: 'G3', label: 'Tax Rate',         key: 'Tax Rate Correctness', code: 'TAX_001' },
              { id: 'G4', label: 'Place of Supply',  key: 'Place of Supply Correctness', code: 'POS_001' },
              { id: 'G5', label: 'E-Way Bill',       key: 'E-Way Bill Compliance', code: 'EWB_001' },
              { id: 'G6', label: 'ITC Eligibility',  key: 'ITC Eligibility / GSTR-2B Match', code: 'ITC_001' },
            ].map((gate) => {
              const failures = rawGates[gate.key] ?? rawGates[gate.code] ?? 0
              const pass = !isLoading && failures === 0
              return (
                <StaggerItem key={gate.id}>
                  <div className={cn(
                    'border rounded-xl p-4 text-center transition-colors',
                    pass ? 'bg-emerald-50 border-emerald-200' : isLoading ? 'bg-gray-50 border-gray-200' : 'bg-red-50 border-red-200'
                  )}>
                    <div className={cn(
                      'w-8 h-8 rounded-lg mx-auto mb-2 flex items-center justify-center text-[11px] font-black',
                      pass ? 'bg-emerald-100 text-emerald-700' : isLoading ? 'bg-gray-200 text-gray-500' : 'bg-red-100 text-red-700'
                    )}>
                      {gate.id}
                    </div>
                    <p className="text-[11px] font-semibold text-gray-800">{gate.label}</p>
                    <p className="text-[10px] font-mono text-gray-400 mt-0.5">{gate.code}</p>
                    <p className={cn(
                      'text-[12px] font-bold mt-1.5',
                      pass ? 'text-emerald-600' : isLoading ? 'text-gray-400' : 'text-red-600'
                    )}>
                      {isLoading ? '—' : pass ? '✓ Pass' : `${failures} fails`}
                    </p>
                  </div>
                </StaggerItem>
              )
            })}
          </StaggerContainer>
        </div>
      </FadeIn>
    </div>
  )
}
