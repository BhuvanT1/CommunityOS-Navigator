import { Bell, Sparkles, Menu } from 'lucide-react'
import { useNavigator } from '../navigator/NavigatorProvider'
import { useDashboard } from './DashboardContext'

export function TopBar({ onMenuClick }: { onMenuClick?: () => void }) {
  const { setIsOpen } = useNavigator()
  const { settings } = useDashboard()

  return (
    <header className="h-16 border-b border-white/5 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-4 md:px-6">
      
      {/* Search / Command Trigger */}
      <div className="flex items-center gap-4 flex-1">
        {onMenuClick && (
          <button onClick={onMenuClick} className="md:hidden text-zinc-400 hover:text-white p-1">
            <Menu className="w-5 h-5" />
          </button>
        )}
        <button 
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-3 px-4 py-2 bg-zinc-900/80 border border-white/5 rounded-full text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors w-full md:w-96 group"
        >
          <Sparkles className="w-4 h-4 text-emerald-400 group-hover:animate-pulse" />
          <span className="text-sm font-medium text-left flex-1 truncate">Ask {settings?.municipality_name || 'CommunityOS'} Navigator...</span>
          <div className="hidden sm:flex items-center gap-1">
            <kbd className="inline-flex items-center justify-center px-1.5 h-5 text-[10px] font-medium bg-zinc-800 rounded border border-white/10 text-zinc-300">⌘</kbd>
            <kbd className="inline-flex items-center justify-center px-1.5 h-5 text-[10px] font-medium bg-zinc-800 rounded border border-white/10 text-zinc-300">K</kbd>
          </div>
        </button>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4 ml-4">
        <button className="relative w-10 h-10 rounded-full hover:bg-white/5 flex items-center justify-center text-zinc-400 hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-emerald-500 rounded-full ring-2 ring-zinc-950"></span>
        </button>
      </div>

    </header>
  )
}
