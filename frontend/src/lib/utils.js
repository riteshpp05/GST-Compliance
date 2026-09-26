import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount) {
  if (amount === null || amount === undefined) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatNumber(n) {
  if (n === null || n === undefined) return '—'
  return new Intl.NumberFormat('en-IN').format(n)
}

export function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function riskColor(level) {
  const map = {
    LOW: 'text-emerald-400',
    MODERATE: 'text-amber-400',
    MEDIUM: 'text-orange-400',
    HIGH: 'text-red-400',
    CRITICAL: 'text-red-600',
  }
  return map[level?.toUpperCase()] || 'text-slate-400'
}

export function riskBadge(level) {
  const map = {
    LOW: 'badge-green',
    MODERATE: 'badge-amber',
    MEDIUM: 'badge-amber',
    HIGH: 'badge-red',
    CRITICAL: 'badge-red',
  }
  return map[level?.toUpperCase()] || 'badge-slate'
}

export function statusBadge(status) {
  const map = {
    COMPLIANT: 'badge-green',
    NON_COMPLIANT: 'badge-red',
    PARTIAL: 'badge-amber',
    PENDING: 'badge-blue',
    OPEN: 'badge-blue',
    READY_FOR_RESOLUTION: 'badge-amber',
    APPROVED: 'badge-green',
    RESOLVED: 'badge-green',
    REJECTED: 'badge-red',
    CLOSED: 'badge-slate',
    IN_PROGRESS: 'badge-purple',
    IN_REVIEW: 'badge-purple',
    INVESTIGATING: 'badge-purple',
  }
  return map[status?.toUpperCase()] || 'badge-slate'
}

export function truncate(str, n = 30) {
  if (!str) return '—'
  return str.length > n ? str.slice(0, n) + '…' : str
}

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}
