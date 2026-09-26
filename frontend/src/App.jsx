import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import Overview from '@/pages/Overview'
import Compliance from '@/pages/Compliance'
import InvoiceDetail from '@/pages/InvoiceDetail'
import Investigations from '@/pages/Investigations'
import Cases from '@/pages/Cases'
import AuditTrail from '@/pages/AuditTrail'
import { AlertCircle, ArrowLeft } from 'lucide-react'

function NotFound() {
  return (
    <div className="panel text-center py-20 max-w-lg mx-auto mt-10">
      <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center justify-center mx-auto mb-3 border border-amber-200">
        <AlertCircle size={22} />
      </div>
      <h2 className="text-lg font-bold text-gray-900">Page Not Found</h2>
      <p className="text-sm text-gray-500 mt-1 mb-6">
        The requested path does not exist or has been moved.
      </p>
      <Link to="/" className="btn-primary">
        <ArrowLeft size={14} /> Back to Dashboard
      </Link>
    </div>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="compliance" element={<Compliance />} />
            <Route path="invoice/:id" element={<InvoiceDetail />} />
            <Route path="investigations" element={<Investigations />} />
            <Route path="investigations/:id" element={<Investigations />} />
            <Route path="cases" element={<Cases />} />
            <Route path="cases/:id" element={<Cases />} />
            <Route path="audit" element={<AuditTrail />} />
            {/* Redirect legacy routes */}
            <Route path="ingestion" element={<Navigate to="/" replace />} />
            <Route path="agent" element={<Navigate to="/" replace />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
