import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Play, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { gstApi } from '@/lib/api'
import toast from 'react-hot-toast'

const titles = {
  '/':             'Overview',
  '/compliance':   'Invoice Audit Center',
  '/agent':        'AI Investigation Agent',
  '/investigations':'Investigations',
  '/cases':        'Case Management',
  '/ingestion':    'Data Ingestion',
  '/audit':        'Audit Trail',
}

export default function Topbar({ sidebarCollapsed }) {
  const location = useLocation()
  const [running, setRunning] = useState(false)
  const title = titles[location.pathname] || 'GST Compliance'

  const runPipeline = async () => {
    if (running) return
    setRunning(true)
    try {
      await gstApi.runAgent()
      toast.success('Pipeline completed!')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <header className={cn('topbar', sidebarCollapsed && 'sidebar-collapsed')}>

      {/* Page title */}
      <AnimatePresence mode="wait">
        <motion.h1
          key={location.pathname}
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 5 }}
          transition={{ duration: 0.2 }}
          className="text-[15px] font-semibold text-gray-900 mr-4 whitespace-nowrap"
        >
          {title}
        </motion.h1>
      </AnimatePresence>

      {/* Search */}
      <div className="flex-1 max-w-xs relative">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        <input
          className="input pl-8 pr-8 py-1.5 text-[13px]"
          placeholder="Search invoices, GSTINs…"
        />
        <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono text-gray-400 bg-gray-100 border border-gray-200 rounded px-1">/</kbd>
      </div>

      <div className="flex items-center gap-2.5 ml-auto">
        {/* SAP badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[12px] font-semibold text-emerald-700">SAP S/4HANA: DI01</span>
        </div>

        {/* Run button */}
        <motion.button
          className={cn('btn-primary', running && 'opacity-60 pointer-events-none')}
          onClick={runPipeline}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {running ? 'Running…' : 'Run Pipeline'}
        </motion.button>
      </div>
    </header>
  )
}
