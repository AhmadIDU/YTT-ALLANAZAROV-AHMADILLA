/**
 * Shtrixkod skaner hook
 * USB/Bluetooth skaner klaviatura kiritish sifatida ishlaydigan qurilmalar uchun
 */
import { useEffect, useRef, useCallback } from 'react';

interface UseBarcodeOptions {
  onScan: (barcode: string) => void;
  minLength?: number;
  maxDelay?: number;  // ms — skaner odatda tez kiritadi
  enabled?: boolean;
}

export function useBarcode({
  onScan,
  minLength = 3,
  maxDelay = 100,
  enabled = true,
}: UseBarcodeOptions): void {
  const bufferRef  = useRef<string>('');
  const timerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastKeyRef = useRef<number>(0);

  const flush = useCallback(() => {
    const barcode = bufferRef.current.trim();
    bufferRef.current = '';
    if (barcode.length >= minLength) {
      onScan(barcode);
    }
  }, [onScan, minLength]);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Input/textarea ichida bo'lsa va Ctrl/Alt bilan emas
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;

      const now = Date.now();
      const delta = now - lastKeyRef.current;
      lastKeyRef.current = now;

      // Enter — skaner bo'lsa flush qilish
      if (e.key === 'Enter') {
        if (timerRef.current) clearTimeout(timerRef.current);
        flush();
        return;
      }

      // Tezlik tekshirish: agar juda sekin kiritilsa — bu inson
      if (delta > 300 && bufferRef.current.length > 0) {
        bufferRef.current = '';
      }

      // Faqat chop etish mumkin bo'lgan belgilar
      if (e.key.length === 1) {
        bufferRef.current += e.key;

        // Timer — Enter bo'lmasa ham avtomatik flush
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(flush, maxDelay + 50);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, flush, maxDelay]);
}
