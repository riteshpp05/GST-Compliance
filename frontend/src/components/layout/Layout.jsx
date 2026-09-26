import { useState, useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import FloatingChatbot from '@/components/agent/FloatingChatbot'
import { cn } from '@/lib/utils'

export default function Layout() {
  const location = useLocation()
  const lenisRef = useRef(null)

  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem('sidebar_collapsed') === 'true'
  )

  const toggle = () => {
    const next = !sidebarCollapsed
    setSidebarCollapsed(next)
    localStorage.setItem('sidebar_collapsed', next)
  }

  /* Lenis smooth scroll with nested scroll support */
  useEffect(() => {
    let rafId
    let lenisInstance = null

    import('lenis').then(({ default: Lenis }) => {
      lenisInstance = new Lenis({
        lerp: 0.09,
        duration: 1.0,
        smoothWheel: true,
        allowNestedScroll: true,
        anchors: true,
      })
      lenisRef.current = lenisInstance

      function raf(time) {
        lenisInstance.raf(time)
        rafId = requestAnimationFrame(raf)
      }
      rafId = requestAnimationFrame(raf)
    }).catch(() => {})

    return () => {
      if (rafId) cancelAnimationFrame(rafId)
      if (lenisInstance) lenisInstance.destroy()
    }
  }, [])

  /* Reset scroll position on route change */
  useEffect(() => {
    if (lenisRef.current) {
      lenisRef.current.scrollTo(0, { immediate: true })
    } else {
      window.scrollTo(0, 0)
    }
  }, [location.pathname])

  /* Ctrl+B shortcut */
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); toggle() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  })

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar collapsed={sidebarCollapsed} onToggle={toggle} />
      <Topbar sidebarCollapsed={sidebarCollapsed} />

      <motion.main
        className={cn('main-content', sidebarCollapsed && 'sidebar-collapsed')}
        animate={{ marginLeft: sidebarCollapsed ? '60px' : '224px' }}
        transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      >
        <div className="px-6 py-5">
          <Outlet />
        </div>
      </motion.main>

      {/* ── Persistent Floating AI Agent Chatbot in bottom-right corner ── */}
      <FloatingChatbot />

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#fff',
            color: '#111827',
            border: '1px solid #e5e7eb',
            borderRadius: '10px',
            fontSize: '13px',
            fontWeight: '500',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
          },
          success: { iconTheme: { primary: '#059669', secondary: '#fff' } },
          error:   { iconTheme: { primary: '#DC2626', secondary: '#fff' } },
        }}
      />
    </div>
  )
}
