import { Outlet } from 'react-router-dom'
import { NavigatorProvider } from '../navigator/NavigatorProvider'
import { DashboardProvider } from './DashboardContext'
import { ToastProvider } from './ToastContext'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import CommandPaletteModal from '../navigator/CommandPaletteModal'
import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'

export default function AdminLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const location = useLocation()
  
  return (
    <NavigatorProvider>
      <ToastProvider>
        <DashboardProvider>
        <div className="flex h-screen bg-zinc-950 text-white overflow-hidden font-sans">
          {/* Sidebar Navigation */}
          <Sidebar isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />
          
          {/* Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0">
            <TopBar onMenuClick={() => setIsMobileMenuOpen(true)} />
            
            <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 relative">
              <AnimatePresence mode="wait">
                <motion.div
                  key={location.pathname}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <Outlet />
                </motion.div>
              </AnimatePresence>
            </main>
          </div>

          {/* Floating Command Palette (Cmd+K) */}
          <CommandPaletteModal />
        </div>
      </DashboardProvider>
      </ToastProvider>
    </NavigatorProvider>
  )
}
