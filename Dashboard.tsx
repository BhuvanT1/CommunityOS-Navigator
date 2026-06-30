import { AIBriefing } from './widgets/AIBriefing'
import { ImpactMeter } from './widgets/ImpactMeter'
import { PriorityCard } from './widgets/PriorityCard'
import { DecisionFeed } from './widgets/DecisionFeed'
import { useDashboard } from './DashboardContext'
import LiveMapView from './views/LiveMapView'

import { HotspotAnalyticsWidget } from './widgets/HotspotAnalyticsWidget'

export default function Dashboard() {
  const { mapState, loading } = useDashboard()

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 xl:col-span-8 h-[200px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
          <div className="col-span-12 xl:col-span-4 h-[200px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
        </div>
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-3 space-y-6">
            <div className="h-[150px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
            <div className="h-[400px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
          </div>
          <div className="col-span-12 lg:col-span-6 h-[600px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
          <div className="col-span-12 lg:col-span-3 h-[600px] bg-zinc-900 animate-pulse rounded-2xl border border-white/5"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Top Row: Briefing & Impact */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 xl:col-span-8">
          <AIBriefing />
        </div>
        <div className="col-span-12 xl:col-span-4">
          <ImpactMeter />
        </div>
      </div>

      {/* Main Row: Map, Priority, Decision Feed, Hotspot */}
      <div className="grid grid-cols-12 gap-6">
        
        {/* Left Column: Priority Cards & Feed */}
        <div className="col-span-12 lg:col-span-3 space-y-6 flex flex-col">
          <div className="flex-none">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-4">Recommended Actions</h3>
            <PriorityCard />
          </div>
          <div className="flex-1 min-h-[400px]">
            <DecisionFeed />
          </div>
        </div>

        {/* Center Column: Intelligence Map Area */}
        <div className="col-span-12 lg:col-span-6 bg-zinc-900 border border-white/5 rounded-2xl p-6 min-h-[600px] relative overflow-hidden flex flex-col">
          <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-zinc-500 via-zinc-900 to-zinc-950"></div>
          
          <div className="z-10 flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Live Intelligence Map</h3>
            <div className="flex items-center gap-3 text-xs text-zinc-500 font-medium">
              <span>Lat: {mapState.lat.toFixed(4)}</span>
              <span>Lng: {mapState.lng.toFixed(4)}</span>
              <span>Zoom: {Math.round(mapState.zoom)}</span>
            </div>
          </div>

          <LiveMapView />
        </div>

        {/* Right Column: AI Hotspot Analytics */}
        <div className="col-span-12 lg:col-span-3 min-h-[600px]">
          <HotspotAnalyticsWidget />
        </div>

      </div>

    </div>
  )
}
