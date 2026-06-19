/**
 * Formatlash yordamchi funksiyalari — O'zbekiston uchun
 */

/** So'm formatida narx ko'rsatish */
export function formatPrice(amount: number): string {
  return new Intl.NumberFormat('uz-UZ', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount) + ' so\'m';
}

/** Qisqa narx formati */
export function formatPriceShort(amount: number): string {
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000)     return `${(amount / 1_000).toFixed(0)}K`;
  return amount.toString();
}

/** Sana va vaqtni formatlash */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('uz-UZ', {
    day:    '2-digit',
    month:  '2-digit',
    year:   'numeric',
    hour:   '2-digit',
    minute: '2-digit',
  });
}

/** Faqat sana */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('uz-UZ', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
}

/** Miqdor va o'lchov birligini formatlash */
export function formatQuantity(qty: number, unit: string): string {
  const unitLabels: Record<string, string> = {
    pcs: 'dona',
    kg:  'kg',
    l:   'litr',
    m:   'metr',
    box: 'quti',
  };
  const formatted = qty % 1 === 0 ? qty.toString() : qty.toFixed(3);
  return `${formatted} ${unitLabels[unit] ?? unit}`;
}
