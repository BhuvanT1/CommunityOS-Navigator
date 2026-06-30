import { useEffect, useState } from 'react';
import { collection, query, where, getDocs } from 'firebase/firestore';
import { db } from '../../services/firebase';
import { useAuth } from '../../contexts/AuthContext';

export default function MyReportsView() {
  const { user } = useAuth();
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;

    const fetchReports = async () => {
      try {
        const q = query(
          collection(db, 'incidents'),
          where('reporter_uid', '==', user.uid)
        );
        const snapshot = await getDocs(q);
        const fetched = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        // Sort in memory to avoid requiring a composite index
        fetched.sort((a: any, b: any) => (b.timestamp || 0) - (a.timestamp || 0));
        setReports(fetched);
      } catch (error) {
        console.error("Error fetching reports", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, [user]);

  if (!user) {
    return <div className="p-8 text-center text-zinc-400">Please sign in to view your reports.</div>;
  }

  return (
    <div className="absolute inset-0 bg-black text-white pt-20 pb-20 overflow-y-auto px-4 z-40">
      <div className="max-w-xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">My Reports</h1>
        <p className="text-zinc-400 mb-6 text-sm">Track the status of the issues you've reported.</p>

        {loading ? (
          <div className="flex justify-center p-8">
            <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : reports.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center text-zinc-500">
            You haven't reported any issues yet.
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((report) => (
              <div key={report.id} className="bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800 flex flex-col shadow-lg">
                <div className="flex">
                  <div className="w-24 h-24 bg-zinc-800 flex-shrink-0">
                    <img src={report.image_url} alt="Report" className="w-full h-full object-cover" />
                  </div>
                  <div className="p-3 flex-1 flex flex-col justify-center">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-bold text-sm text-zinc-200">{report.analysis?.decision?.category || 'General'}</h3>
                        <p className="text-xs text-zinc-500 mt-1">
                          {new Date(report.timestamp).toLocaleDateString()} • {report.gps_verified ? 'GPS Verified' : 'Unverified Location'}
                        </p>
                      </div>
                      <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase ${
                        report.status === 'RESOLVED' ? 'bg-emerald-500/20 text-emerald-400' :
                        report.status === 'REJECTED' ? 'bg-red-500/20 text-red-400' :
                        report.status === 'MERGED' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {report.status}
                      </span>
                    </div>
                  </div>
                </div>
                {/* Detailed Information */}
                <div className="px-4 py-3 border-t border-zinc-800/50 bg-zinc-900/50">
                  <div className="space-y-2">
                    {report.analysis?.summary && (
                      <div>
                        <span className="text-[10px] uppercase font-bold text-zinc-500">AI Summary</span>
                        <p className="text-xs text-zinc-300">{report.analysis.summary}</p>
                      </div>
                    )}
                    {report.resolution_notes && (
                      <div className="mt-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2">
                        <span className="text-[10px] uppercase font-bold text-emerald-500">Resolution Notes</span>
                        <p className="text-xs text-emerald-400 mt-1">{report.resolution_notes}</p>
                      </div>
                    )}
                    {report.verification_notes && (
                      <div className="mt-2 bg-blue-500/10 border border-blue-500/20 rounded-lg p-2">
                        <span className="text-[10px] uppercase font-bold text-blue-500">Verification</span>
                        <p className="text-xs text-blue-400 mt-1">{report.verification_notes}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
