/**
 * Internet ulanish holatini kuzatuvchi hook
 */
import { useEffect } from 'react';
import { usePosStore } from '../store/posStore';

export function useOnlineStatus(): boolean {
  const setOnlineStatus = usePosStore(s => s.setOnlineStatus);
  const isOnline        = usePosStore(s => s.isOnline);

  useEffect(() => {
    const onOnline  = () => setOnlineStatus(true);
    const onOffline = () => setOnlineStatus(false);

    window.addEventListener('online',  onOnline);
    window.addEventListener('offline', onOffline);

    return () => {
      window.removeEventListener('online',  onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, [setOnlineStatus]);

  return isOnline;
}
