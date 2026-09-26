import { useQuery } from '@tanstack/react-query'
import { History, Clock, User, FileText } from 'lucide-react'
import { gstApi } from '@/lib/api'
import { formatDate, cn } from '@/lib/utils'
import { FadeIn, StaggerContainer, StaggerItem } from '@/components/ui/animations'
import { Skeleton, SectionHeader, EmptyState } from '@/components/ui/primitives'

const TYPE_STYLE = {
  HANA:          'bg-cyan-50 text-cyan-800 border border-cyan-200',
  PAYMENT_BLOCK: 'bg-amber-50 text-amber-800 border border-amber-200',
  VALIDATION:    'bg-blue-50 text-blue-700 border border-blue-200',
  RUN:           'bg-indigo-50 text-indigo-700 border border-indigo-200',
  INGEST:        'bg-emerald-50 text-emerald-700 border border-emerald-200',
  ERROR:         'bg-red-50 text-red-700 border border-red-200',
  AGENT:         'bg-purple-50 text-purple-700 border border-purple-200',
}

export default function AuditTrail() {
  const { data, isLoading } = useQuery({
    queryKey: ['audit'],
    queryFn: () => gstApi.getAuditTrail({ limit: 100 }),
  })
  const events = data?.events || data?.logs || (Array.isArray(data) ? data : [])

  return (
    <FadeIn>
      <div className="panel">
        <SectionHeader icon={<History size={15} />} title="Audit Trail" subtitle="System activity, SAP HANA Ingestion, and compliance event log" />

        {isLoading ? (
          <div className="space-y-2">{Array.from({length:6}).map((_,i) => <Skeleton key={i} className="h-14" />)}</div>
        ) : events.length === 0 ? (
          <EmptyState icon={<History size={22} />} title="No Audit Events"
            description="Events are recorded when you run pipelines, ingest data from SAP HANA, or act on compliance." />
        ) : (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-100" />

            <StaggerContainer className="space-y-2 pl-12">
              {events.map((evt, i) => {
                const t = (evt.action || evt.event_type || 'VALIDATION').toUpperCase()
                const style = TYPE_STYLE[Object.keys(TYPE_STYLE).find(k => t.includes(k))] || TYPE_STYLE.VALIDATION
                return (
                  <StaggerItem key={evt.id || i}>
                    <div className="relative">
                      <div className="timeline-dot" />
                      <div className="flex items-start gap-3 p-3.5 bg-gray-50 border border-gray-100 rounded-xl hover:bg-blue-50/40 hover:border-blue-100 transition-colors">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide', style)}>
                              {evt.action || evt.event_type || 'EVENT'}
                            </span>
                            <span className="text-[13px] font-medium text-gray-800">
                              {evt.description || evt.message || 'System event'}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-400 flex-wrap">
                            {evt.user && <span className="flex items-center gap-1 text-gray-600"><User size={9} />{evt.user}</span>}
                            {(evt.invoice_no || evt.invoice_id) && (
                              <span className="flex items-center gap-1 font-mono text-blue-600 font-semibold">
                                <FileText size={9} />Doc: {evt.invoice_no || evt.invoice_id}
                              </span>
                            )}
                            {evt.counterparty_name && (
                              <span className="text-gray-500 font-medium">Counterparty: {evt.counterparty_name}</span>
                            )}
                            {evt.total_amount > 0 && (
                              <span className="text-gray-700 font-mono font-medium">₹{Number(evt.total_amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                            )}
                            <span className="flex items-center gap-1"><Clock size={9} />{formatDate(evt.timestamp || evt.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </StaggerItem>
                )
              })}
            </StaggerContainer>
          </div>
        )}
      </div>
    </FadeIn>
  )
}
