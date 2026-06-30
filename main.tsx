import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import AdminLayout from './components/admin/AdminLayout.tsx'
import Dashboard from './components/admin/Dashboard.tsx'
import ManualReviewQueue from './components/admin/views/ManualReviewQueue.tsx'
import IntelligenceMap from './components/admin/views/IntelligenceMap.tsx'
import Reports from './components/admin/views/Reports.tsx'
import Settings from './components/admin/views/Settings.tsx'
import LoginView from './components/admin/views/LoginView.tsx'
import { ErrorBoundary } from './ErrorBoundary.tsx'
import { AuthProvider, useAuth } from './contexts/AuthContext.tsx'
import { Navigate, Outlet } from 'react-router-dom'

const ProtectedRoute = () => {
  const { user, loading, isAdmin } = useAuth();
  
  if (loading) {
    return <div className="h-screen w-screen bg-black flex items-center justify-center text-white">Loading...</div>;
  }
  
  if (!user || !isAdmin) {
    return <Navigate to="/" replace />;
  }
  
  return <Outlet />;
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<App />} />
            <Route path="/login" element={<LoginView />} />
            <Route path="/admin" element={<ProtectedRoute />}>
              <Route element={<AdminLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="map" element={<IntelligenceMap />} />
                <Route path="review" element={<ManualReviewQueue />} />
                <Route path="reports" element={<Reports />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  </StrictMode>,
)
