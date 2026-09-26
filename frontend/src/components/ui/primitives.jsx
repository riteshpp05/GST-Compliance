import { cn } from '@/lib/utils'

export function Badge({ children, variant = 'slate', className }) {
  return <span className={cn('badge', `badge-${variant}`, className)}>{children}</span>
}

export function Skeleton({ className }) {
  return <div className={cn('skeleton', className)} />
}

export function Dot({ color = 'gray', pulse = false }) {
  const c = { green: 'bg-emerald-500', red: 'bg-red-500', amber: 'bg-amber-400', blue: 'bg-blue-500', gray: 'bg-gray-400' }
  return (
    <span className="relative inline-flex items-center justify-center">
      <span className={cn('w-2 h-2 rounded-full', c[color])} />
      {pulse && <span className={cn('absolute inline-flex w-full h-full rounded-full opacity-60 animate-ping', c[color])} />}
    </span>
  )
}

export function SectionHeader({ icon, title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between mb-5 gap-4">
      <div className="flex items-center gap-2.5">
        {icon && (
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0">
            {icon}
          </div>
        )}
        <div>
          <h2 className="section-title">{title}</h2>
          {subtitle && <p className="section-sub">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </div>
  )
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-gray-400 mb-3">{icon}</div>
      <h3 className="text-[13px] font-semibold text-gray-700 mb-1">{title}</h3>
      <p className="text-[12px] text-gray-400 max-w-xs">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function LoadingSpinner({ size = 18 }) {
  return (
    <svg className="animate-spin text-blue-500" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

export function Input({ className, ...props }) {
  return <input className={cn('input', className)} {...props} />
}

export function Select({ className, children, ...props }) {
  return (
    <select className={cn('select-field', className)} {...props}>{children}</select>
  )
}

export function Divider({ className }) {
  return <div className={cn('divider', className)} />
}
