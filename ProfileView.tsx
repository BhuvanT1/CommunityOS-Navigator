
import { useAuth } from '../../contexts/AuthContext';
import { MapPin, Clock, Award, Activity, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ProfileView() {
  const { user, profile } = useAuth();

  if (!user || !profile) {
    return <div className="p-8 text-center text-zinc-400">Please sign in to view your profile.</div>;
  }


  // Calculate Level and Progress based on backend reputation_score
  let citizenLevel = "New Citizen";
  let nextLevel = "Contributor";
  let levelProgress = 0; // 0 to 100
  let pointsToNext = 150 - profile.reputation_score;

  if (profile.reputation_score >= 1000) {
    citizenLevel = "Civic Hero";
    nextLevel = "Max Level";
    levelProgress = 100;
    pointsToNext = 0;
  } else if (profile.reputation_score >= 500) {
    citizenLevel = "Community Guardian";
    nextLevel = "Civic Hero";
    levelProgress = ((profile.reputation_score - 500) / 500) * 100;
    pointsToNext = 1000 - profile.reputation_score;
  } else if (profile.reputation_score >= 150) {
    citizenLevel = "Contributor";
    nextLevel = "Community Guardian";
    levelProgress = ((profile.reputation_score - 150) / 350) * 100;
    pointsToNext = 500 - profile.reputation_score;
  } else {
    levelProgress = ((profile.reputation_score - 100) / 50) * 100;
  }

  const impact = profile.impact_metrics || {
    average_resolution_time_hrs: 0,
    community_percentile: 50,
    total_issues_helped: 0,
    daily_contributions: {},
    areas_contributed: []
  };

  // Prepare Contribution Graph Data (Last 7 days)
  const last7Days = Array.from({length: 7}, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    const dateStr = d.toISOString().split('T')[0];
    return {
      date: dateStr,
      day: d.toLocaleDateString('en-US', { weekday: 'short' }),
      count: impact.daily_contributions[dateStr] || 0
    };
  });
  
  const maxContribution = Math.max(...last7Days.map(d => d.count), 1);

  return (
    <div className="absolute inset-0 bg-zinc-950 text-white pt-10 pb-24 overflow-y-auto px-4 z-40">
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-xl mx-auto space-y-6"
      >
        
        {/* Profile Header (Glassmorphism) */}
        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-3xl p-6 relative overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/20 rounded-full blur-3xl -mr-10 -mt-10"></div>
          
          <div className="flex items-center gap-5 relative z-10">
            <motion.img 
              initial={{ scale: 0.8 }} animate={{ scale: 1 }} transition={{ type: 'spring' }}
              src={profile.photoURL || `https://ui-avatars.com/api/?name=${profile.email}`} 
              alt="Avatar" 
              className="w-20 h-20 rounded-full border-2 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.3)] object-cover bg-zinc-800" 
            />
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[10px] font-black uppercase tracking-wider rounded-full mb-1">
                <Award className="w-3 h-3" />
                {citizenLevel}
              </div>
              <h1 className="text-2xl font-bold tracking-tight">{profile.name}</h1>
              <p className="text-zinc-400 text-sm font-medium">{profile.email}</p>
            </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-white/5">
            <div className="flex justify-between items-end mb-2">
              <span className="text-xs font-bold text-zinc-400 uppercase tracking-wide">Progress to {nextLevel}</span>
              <span className="text-xs text-emerald-400 font-bold">{pointsToNext} pts left</span>
            </div>
            <div className="h-2 bg-zinc-950/50 rounded-full overflow-hidden border border-white/5">
              <motion.div 
                initial={{ width: 0 }} animate={{ width: `${Math.max(2, levelProgress)}%` }} transition={{ duration: 1, ease: 'easeOut' }}
                className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)]"
              ></motion.div>
            </div>
          </div>
        </div>

        {/* Primary Stats */}
        <div className="grid grid-cols-2 gap-4">
          <motion.div whileHover={{ y: -2 }} className="bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-2xl p-5 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-100 transition-opacity"><Activity className="w-6 h-6 text-emerald-400" /></div>
            <div className="text-3xl font-black text-white tracking-tighter mb-1">
              {profile.reputation_score} <span className="text-emerald-400 text-sm font-bold align-middle">XP</span>
            </div>
            <div className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Reputation</div>
          </motion.div>
          <motion.div whileHover={{ y: -2 }} className="bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-2xl p-5 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-100 transition-opacity"><TrendingUp className="w-6 h-6 text-blue-400" /></div>
            <div className="text-3xl font-black text-white tracking-tighter mb-1">
              {profile.trust_score} <span className="text-blue-400 text-sm font-bold align-middle">/1000</span>
            </div>
            <div className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Trust Score</div>
          </motion.div>
        </div>

        {/* Impact Metrics Row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl p-4 text-center">
            <div className="text-xl font-bold text-white mb-1">Top {impact.community_percentile}%</div>
            <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Community Rank</div>
          </div>
          <div className="bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl p-4 text-center">
            <div className="text-xl font-bold text-amber-400 mb-1">{impact.total_issues_helped}</div>
            <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Issues Resolved</div>
          </div>
          <div className="bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl p-4 text-center">
            <div className="text-xl font-bold text-indigo-400 mb-1 flex items-center justify-center gap-1">
              <Clock className="w-4 h-4" />
              {impact.average_resolution_time_hrs.toFixed(1)}h
            </div>
            <div className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Avg Fix Time</div>
          </div>
        </div>

        {/* Contribution Graph */}
        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
          <h2 className="text-sm font-bold mb-4 text-zinc-300 flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-500" /> Recent Contributions
          </h2>
          <div className="flex items-end justify-between h-24 gap-2">
            {last7Days.map((day, i) => {
              const heightPct = day.count > 0 ? Math.max(15, (day.count / maxContribution) * 100) : 0;
              return (
                <div key={day.date} className="flex flex-col items-center gap-2 flex-1 group relative">
                  <div className="w-full bg-zinc-950/50 rounded-md flex items-end justify-center relative overflow-hidden h-16 border border-white/5">
                    <motion.div 
                      initial={{ height: 0 }} animate={{ height: `${heightPct}%` }} transition={{ duration: 0.5, delay: i * 0.1 }}
                      className={`w-full ${day.count > 0 ? 'bg-emerald-500 shadow-[0_-5px_15px_rgba(16,185,129,0.3)]' : 'bg-zinc-800'}`}
                    />
                    {/* Tooltip */}
                    {day.count > 0 && (
                      <div className="absolute top-0 inset-x-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 h-full text-xs font-bold">
                        {day.count}
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] font-medium text-zinc-500">{day.day}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Areas Contributed */}
        {impact.areas_contributed && impact.areas_contributed.length > 0 && (
          <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/10 rounded-3xl p-6">
             <h2 className="text-sm font-bold mb-3 text-zinc-300 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-500" /> Areas You've Improved
            </h2>
            <div className="flex flex-wrap gap-2">
              {impact.areas_contributed.map((area: string, idx: number) => (
                <div key={idx} className="px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-semibold rounded-full shadow-sm">
                  {area}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Earned Badges */}
        <div>
          <h2 className="text-sm font-bold mb-3 pl-2 text-zinc-300">Earned Badges</h2>
          {profile.badges && profile.badges.length > 0 ? (
            <div className="grid grid-cols-3 gap-3">
              {profile.badges.map((badge, idx) => (
                <motion.div 
                  initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: idx * 0.1 }}
                  key={idx} 
                  className="bg-zinc-900/60 backdrop-blur-md border border-amber-500/20 rounded-2xl p-4 flex flex-col gap-2 items-center text-center shadow-[0_0_15px_rgba(245,158,11,0.05)]"
                >
                  <span className="text-3xl drop-shadow-md">{badge.icon || '🏆'}</span>
                  <span className="text-[10px] font-bold text-amber-400 leading-tight">{badge.name}</span>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="bg-zinc-900/30 border border-zinc-800 border-dashed rounded-2xl p-6 text-center text-zinc-500 text-xs">
              Report your first verified issue to unlock badges.
            </div>
          )}
        </div>
        
      </motion.div>
    </div>
  );
}
