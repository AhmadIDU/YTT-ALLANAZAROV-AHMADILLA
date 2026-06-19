export const fmt = {
  price: (n: number | string) =>
    new Intl.NumberFormat('uz-UZ').format(Number(n)) + " so'm",
  date: (iso: string) =>
    new Date(iso).toLocaleDateString('uz-UZ', { day:'2-digit', month:'2-digit', year:'numeric' }),
  dateTime: (iso: string) =>
    new Date(iso).toLocaleString('uz-UZ', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }),
  pct: (n: number | string) => `${Number(n).toFixed(1)}%`,
  qty: (n: number | string, unit = 'dona') => `${Number(n).toLocaleString('uz-UZ')} ${unit}`,
};
