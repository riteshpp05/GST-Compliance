import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, ShieldCheck, Bot, FileText,
  FolderOpen, Upload, History, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

import Logo from '@/components/ui/Logo'

const navItems = [
  { label: 'Overview',       icon: LayoutDashboard, to: '/',              end: true },
  { label: 'Invoice Audit',  icon: ShieldCheck,     to: '/compliance' },
  { label: 'Investigations', icon: FolderOpen,      to: '/investigations' },
  { label: 'Cases',          icon: FileText,        to: '/cases' },
  { label: 'Audit Trail',    icon: History,         to: '/audit' },
]

export default function Sidebar({ collapsed, onToggle }) {
  return (
    <aside className={cn('sidebar', collapsed && 'collapsed')}>

      {/* Brand */}
      <div className="flex items-center px-3.5 h-14 border-b border-gray-100 flex-shrink-0">
        <Logo size={28} showText={!collapsed} animate />
      </div>

      {/* Nav */}
      <nav data-lenis-prevent className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto scroll-thin">
        {!collapsed && (
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest px-2 py-2">
            Platform
          </p>
        )}
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className="block">
            {({ isActive }) => (
              <motion.div
                className={cn('nav-link', isActive && 'active')}
                whileHover={{ x: collapsed ? 0 : 2 }}
                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                title={collapsed ? item.label : undefined}
              >
                <item.icon
                  size={16}
                  className={cn('flex-shrink-0', isActive ? 'text-blue-600' : 'text-gray-400')}
                />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -4 }}
                      transition={{ duration: 0.15 }}
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="p-2 border-t border-gray-100 flex-shrink-0">
        <button
          onClick={onToggle}
          className={cn('nav-link w-full', collapsed && 'justify-center')}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed
            ? <ChevronRight size={15} className="text-gray-400" />
            : <><ChevronLeft size={15} className="text-gray-400" /><span className="text-gray-500">Collapse</span></>
          }
        </button>
      </div>
    </aside>
  )
}
