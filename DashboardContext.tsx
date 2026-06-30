import React, { createContext, useContext, useState, useEffect, useMemo, useRef } from 'react'
import type { ReactNode } from 'react'
import { useIncidents, type Incident } from '../../hooks/useIncidents'
import { useToast } from './ToastContext'

type DashboardContextType = {
  activeFilters: Record<string, any>
  setActiveFilters: React.Dispatch<React.SetStateAction<Record<string, any>>>
  mapState: { lat: number; lng: number; zoom: number }
  setMapState: React.Dispatch<React.SetStateAction<{ lat: number; lng: number; zoom: number }>>
  highlightedIncident: string | null
  setHighlightedIncident: React.Dispatch<React.SetStateAction<string | null>>
  incidents: Incident[]
  filteredIncidents: Incident[]
  loading: boolean
  settings: Record<string, any>
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [activeFilters, setActiveFilters] = useState<Record<string, any>>({})
  const [mapState, setMapState] = useState({ lat: 20.5937, lng: 78.9629, zoom: 5.5 })
  const [highlightedIncident, setHighlightedIncident] = useState<string | null>(null)
  const [settings, setSettings] = useState<Record<string, any>>({ demo_mode: false, municipality_name: "CommunityOS" })

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/settings`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.data) {
          setSettings(data.data);
        }
      })
      .catch(err => console.error("Failed to load settings:", err));
  }, []);

  const { incidents, loading } = useIncidents()
  const { showToast } = useToast()
  const previousIncidentsRef = useRef<Incident[]>(incidents)

  // Request notification permission if enabled
  useEffect(() => {
    if (settings.push_notifications && 'Notification' in window) {
      if (Notification.permission === 'default') {
        Notification.requestPermission()
      }
    }
  }, [settings.push_notifications]);

  // Monitor changes for AI Activity Notifications
  useEffect(() => {
    const prev = previousIncidentsRef.current
    if (prev.length > 0 && incidents.length > 0) {
      // Detect New Incident
      if (incidents.length > prev.length) {
        const newIncident = incidents.find(i => !prev.find(p => p.id === i.id))
        if (newIncident) {
          showToast(`New citizen report received: ${newIncident.category}`, "info")
          
          if (settings.push_notifications && 'Notification' in window && Notification.permission === 'granted') {
            new Notification('CommunityOS Alert', {
              body: `New ${newIncident.priority_score >= 80 ? 'CRITICAL ' : ''}incident: ${newIncident.category}`,
              icon: '/favicon.ico'
            });
          }

          if (newIncident.priority_score >= 80) {
            setTimeout(() => showToast(`Gemini classified incident ${newIncident.id.slice(0,6)} as Critical.`, "error"), 1500)
          }
        }
      }

      // Detect Status changes & Merges
      incidents.forEach(inc => {
        const prevInc = prev.find(p => p.id === inc.id)
        if (prevInc) {
          if (prevInc.status !== 'RESOLVED' && inc.status === 'RESOLVED') {
            showToast(`Incident ${inc.id.slice(0,6)} resolved.`, "success")
          }
          if (prevInc.status !== 'ASSIGNED' && inc.status === 'ASSIGNED') {
            showToast(`Crew assigned to ${inc.id.slice(0,6)}.`, "info")
          }
          if ((inc.merged_report_count || 0) > (prevInc.merged_report_count || 0)) {
            showToast(`Duplicate reports automatically merged into ${inc.id.slice(0,6)}.`, "info")
          }
        }
      })
    }
    previousIncidentsRef.current = incidents
  }, [incidents, showToast, settings.push_notifications])

  const filteredIncidents = useMemo(() => {
    return incidents.filter(incident => {
      // Search (ID, Category, Description, Street)
      if (activeFilters.search) {
        const q = activeFilters.search.toLowerCase();
        const matchesSearch = 
          (incident.id || '').toLowerCase().includes(q) ||
          (incident.category || '').toLowerCase().includes(q) ||
          (incident.description && incident.description.toLowerCase().includes(q)) ||
          (incident.analysis?.geo?.street_name && incident.analysis.geo.street_name.toLowerCase().includes(q));
        if (!matchesSearch) return false;
      }
      
      // Status
      if (activeFilters.status && activeFilters.status !== 'ALL') {
        if ((incident.status || '').toLowerCase() !== activeFilters.status.toLowerCase()) return false;
      }

      // Category
      if (activeFilters.category && activeFilters.category !== 'ALL') {
        if ((incident.category || '').toLowerCase() !== activeFilters.category.toLowerCase()) return false;
      }

      // Priority
      if (activeFilters.priority && activeFilters.priority !== 'ALL') {
        const score = incident.priority_score;
        if (activeFilters.priority === 'CRITICAL' && score < 80) return false;
        if (activeFilters.priority === 'HIGH' && (score < 60 || score >= 80)) return false;
        if (activeFilters.priority === 'MEDIUM' && (score < 40 || score >= 60)) return false;
        if (activeFilters.priority === 'LOW' && score >= 40) return false;
      }

      // Time
      if (activeFilters.time && activeFilters.time !== 'ALL') {
        const hoursDiff = (Date.now() - incident.last_updated) / (1000 * 60 * 60);
        if (activeFilters.time === '24H' && hoursDiff > 24) return false;
        if (activeFilters.time === '7D' && hoursDiff > 168) return false;
      }

      // AI Confidence
      if (activeFilters.confidence && activeFilters.confidence !== 'ALL') {
        const conf = incident.analysis?.decision?.confidence || 100;
        if (activeFilters.confidence === 'HIGH' && conf < 90) return false;
        if (activeFilters.confidence === 'LOW' && conf >= 70) return false;
      }

      return true;
    });
  }, [incidents, activeFilters]);

  return (
    <DashboardContext.Provider 
      value={{
        activeFilters, setActiveFilters,
        mapState, setMapState,
        highlightedIncident, setHighlightedIncident,
        incidents, filteredIncidents, loading,
        settings
      }}
    >
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const context = useContext(DashboardContext)
  if (!context) throw new Error("useDashboard must be used within DashboardProvider")
  return context
}
