import { useEffect, useState } from 'react';
import { collection, query, onSnapshot, doc, updateDoc } from 'firebase/firestore';
import { db } from '../../services/firebase';
import { useAuth } from '../../contexts/AuthContext';

export default function NotificationTray() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user) return;

    const q = query(
      collection(db, 'notifications', user.uid, 'user_notifications')
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      let notifs = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() } as any));
      notifs.sort((a: any, b: any) => (b.timestamp || 0) - (a.timestamp || 0));
      notifs = notifs.slice(0, 10);
      setNotifications(notifs);
      setUnreadCount(notifs.filter(n => !n.read).length);
    });

    return () => unsubscribe();
  }, [user]);

  const markAsRead = async (id: string) => {
    if (!user) return;
    try {
      await updateDoc(doc(db, 'notifications', user.uid, 'user_notifications', id), { read: true });
    } catch (error) {
      console.error("Error marking notification as read:", error);
    }
  };

  const markAllAsRead = async () => {
    if (!user) return;
    try {
      const unreadNotifs = notifications.filter(n => !n.read);
      for (const n of unreadNotifs) {
        await updateDoc(doc(db, 'notifications', user.uid, 'user_notifications', n.id), { read: true });
      }
    } catch (error) {
      console.error("Error marking all as read:", error);
    }
  };

  if (!user) return null;

  return (
    <div className="absolute top-4 left-4 z-50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative bg-zinc-900 border border-white/10 p-2 rounded-full text-white hover:bg-zinc-800 transition-colors shadow-xl"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute 0 top-0 right-0 w-3 h-3 bg-red-500 rounded-full border border-black"></span>
        )}
      </button>

      {isOpen && (
        <div className="absolute top-12 left-0 w-80 bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
          <div className="p-3 border-b border-zinc-800 flex justify-between items-center bg-zinc-950">
            <h3 className="font-bold text-sm text-white">Notifications</h3>
            {unreadCount > 0 && (
              <button onClick={markAllAsRead} className="text-xs text-emerald-500 hover:text-emerald-400 font-medium">Mark all read</button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-sm text-zinc-500">No notifications yet.</div>
            ) : (
              notifications.map(notif => (
                <div 
                  key={notif.id} 
                  className={`p-3 border-b border-zinc-800/50 cursor-pointer hover:bg-zinc-800 transition-colors ${!notif.read ? 'bg-zinc-800/30' : ''}`}
                  onClick={() => markAsRead(notif.id)}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-bold text-xs text-zinc-200">{notif.title || notif.type}</span>
                    <span className="text-[10px] text-zinc-500">{new Date(notif.timestamp).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs text-zinc-400 line-clamp-2">{notif.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
