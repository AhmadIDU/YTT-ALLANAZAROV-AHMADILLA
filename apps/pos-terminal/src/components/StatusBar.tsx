/**
 * Holat paneli — onlayn/oflayn, sinxronizatsiya, smena
 */
import React from 'react';
import { Wifi, WifiOff, RefreshCw, User, Clock } from 'lucide-react';
import { usePosStore } from '../store/posStore';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { runSync } from '../sync/syncWorker';
import { formatDateTime } from '../utils/formatters';

export function StatusBar() {
  const isOnline        = useOnlineStatus();
  const currentUser     = usePosStore(s => s.currentUser);
  const activeShift     = usePosStore(s => s.activeShift);
  const pendingCount    = usePosStore(s => s.pendingSyncCount);
  const refreshPending  = usePosStore(s => s.refreshPendingCount);

  const handleSync = async () => {
    await runSync();
    await refreshPending();
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-gray-900 text-white text-sm">
      {/* Chap: Onlayn holat */}
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
          isOnline ? 'bg-green-700 text-green-100' : 'bg-red-700 text-red-100'
        }`}>
          {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          {isOnline ? 'Onlayn' : 'Oflayn rejim'}
        </div>

        {/* Sinxronizatsiya tugmasi */}
        {pendingCount > 0 && (
          <button
            onClick={handleSync}
            className="flex items-center gap-1 px-2 py-1 bg-yellow-600 hover:bg-yellow-500 rounded-full text-xs font-medium transition-colors"
          >
            <RefreshCw size={12} />
            {pendingCount} ta sinxronlanmagan
          </button>
        )}
      </div>

      {/* O'rta: Smena ma'lumotlari */}
      {activeShift && (
        <div className="flex items-center gap-1.5 text-gray-300">
          <Clock size={14} />
          <span>Smena: {formatDateTime(activeShift.openedAt)}</span>
        </div>
      )}

      {/* O'ng: Foydalanuvchi */}
      {currentUser && (
        <div className="flex items-center gap-1.5 text-gray-300">
          <User size={14} />
          <span>{currentUser.fullName}</span>
          <span className="px-1.5 py-0.5 bg-gray-700 rounded text-xs uppercase">
            {currentUser.role === 'cashier' ? 'Kassir' :
             currentUser.role === 'manager' ? 'Menejer' : currentUser.role}
          </span>
        </div>
      )}
    </div>
  );
}
