import { MapPin, Navigation, Search } from 'lucide-react';

interface TrustBadgeProps {
  location_source?: string;
  gps_verified?: boolean;
}

export function TrustBadge({ location_source, gps_verified }: TrustBadgeProps) {
  if (location_source === 'gps' || gps_verified) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-medium whitespace-nowrap">
        <Navigation className="w-3 h-3" />
        <span>GPS Verified</span>
      </div>
    );
  }
  
  if (location_source === 'manual_pin') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded-full text-xs font-medium whitespace-nowrap">
        <MapPin className="w-3 h-3" />
        <span>Manual Pin</span>
      </div>
    );
  }
  
  if (location_source === 'address_search') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded-full text-xs font-medium whitespace-nowrap">
        <Search className="w-3 h-3" />
        <span>Address Search</span>
      </div>
    );
  }

  // Fallback for old/demo data
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-medium whitespace-nowrap">
      <Navigation className="w-3 h-3" />
      <span>GPS Verified</span>
    </div>
  );
}
