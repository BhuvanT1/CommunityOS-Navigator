import { LayoutDashboard, Map as MapIcon, CheckSquare, FileText, Settings, X, LogOut } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useDashboard } from './DashboardContext'

export function Sidebar({ isOpen, onClose }: { isOpen?: boolean, onClose?: () => void }) {
  const location = useLocation()
  const { logout, user } = useAuth()
  const { settings } = useDashboard()
  
  const navItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/admin' },
    { icon: MapIcon, label: 'Intelligence Map', path: '/admin/map' },
    { icon: CheckSquare, label: 'Manual Review', path: '/admin/review' },
    { icon: FileText, label: 'Reports', path: '/admin/reports' },
    { icon: Settings, label: 'Settings', path: '/admin/settings' },
  ]

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm" onClick={onClose}></div>
      )}
      
      <nav aria-label="Main Navigation" className={`fixed inset-y-0 left-0 z-50 w-64 border-r border-white/5 bg-zinc-950 flex flex-col transform transition-transform duration-300 md:relative md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)]"></div>
            <span className="font-bold text-white tracking-wide truncate max-w-[150px]" title={settings?.municipality_name || 'CommunityOS'}>
              {settings?.municipality_name || 'CommunityOS'}
            </span>
          </div>
          {onClose && (
            <button onClick={onClose} className="md:hidden text-zinc-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
        
        <div className="flex-1 p-4 flex flex-col gap-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon
            return (
              <Link 
                key={item.label}
                to={item.path}
                onClick={onClose}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-sm font-medium ${
                  isActive 
                    ? 'bg-zinc-800/80 text-white shadow-sm' 
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                {item.label}
              </Link>
            )
          })}
        </div>

        <div className="p-4 border-t border-white/5">
          <div className="flex items-center justify-between px-3 py-2 text-sm font-medium text-zinc-400">
            <div className="flex items-center gap-3">
              {user?.photoURL ? (
                <img src={user.photoURL} alt="Profile" className="w-8 h-8 rounded-full border border-white/10" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs text-white">
                  AD
                </div>
              )}
              <div className="truncate w-24" title={user?.email || 'Dispatcher'}>
                {user?.displayName || 'Dispatcher'}
              </div>
            </div>
            <button 
              onClick={logout} 
              className="p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>
    </>
  )
}
