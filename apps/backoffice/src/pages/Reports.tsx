/**
 * Hisobotlar sahifasi — ABC, marjin, kassir samaradorligi
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { Download, TrendingUp, Package, Users } from 'lucide-react';
import { analyticsApi } from '../utils/api';
import { fmt } from '../utils/formatters';

const TABS = [
  { key: 'top',     label: 'Top mahsulotlar', icon: Package },
  { key: 'abc',     label: 'ABC tahlil',       icon: TrendingUp },
  { key: 'margin',  label: 'Marjinallik',       icon: TrendingUp },
  { key: 'cashiers',label: 'Kassirlar',         icon: Users },
] as const;

type Tab = typeof TABS[number]['key'];

export function Reports() {
  const [tab,      setTab]      = useState<Tab>('top');
  const [dateFrom, setDateFrom] = useState(() => new Date().toISOString().slice(0, 8) + '01');
  const [dateTo,   setDateTo]   = useState(() => new Date().toISOString().slice(0, 10));

  const params = { from: dateFrom, to: dateTo };

  const topQ  = useQuery({ queryKey: ['top-products', params], queryFn: () => analyticsApi.topProducts(params).then(r => r.data), enabled: tab === 'top' });
  const abcQ  = useQuery({ queryKey: ['abc', params],          queryFn: () => analyticsApi.abc(params).then(r => r.data),         enabled: tab === 'abc' });
  const margQ = useQuery({ queryKey: ['margin', params],       queryFn: () => analyticsApi.margin(params).then(r => r.data),      enabled: tab === 'margin' });
  const cashQ = useQuery({ queryKey: ['cashiers', params],     queryFn: () => analyticsApi.cashiers(params).then(r => r.data),    enabled: tab === 'cashiers' });

  const handleExport = async () => {
    try {
      const resp = await analyticsApi.export({ report_type: tab === 'top' ? 'top_products' : tab, from: dateFrom, to: dateTo, format: 'excel' });
      const url  = URL.createObjectURL(new Blob([resp.data]));
      const a    = document.createElement('a');
      a.href = url; a.download = `posskassa-${tab}-${dateFrom}.xlsx`; a.click();
    } catch { /* xato holat */ }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-gray-800">Hisobotlar</h1>
        <div className="flex items-center gap-3 flex-wrap">
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-400" />
          <span className="text-gray-400 text-sm">—</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-400" />
          <button onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 hover:border-blue-300 rounded-xl text-sm text-gray-600 transition-colors">
            <Download size={15} /> Excel
          </button>
        </div>
      </div>

      {/* Tab navigatsiya */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {/* Top mahsulotlar */}
      {tab === 'top' && (
        <div className="space-y-5">
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <h2 className="font-bold text-gray-800 mb-4">Daromad bo'yicha top mahsulotlar</h2>
            {topQ.isLoading ? <Loader /> : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={(topQ.data ?? []).slice(0, 15)} layout="vertical" margin={{ left: 120, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `${(v/1_000_000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="product_name" tick={{ fontSize: 11 }} width={120} />
                  <Tooltip formatter={(v: number) => [fmt.price(v), 'Daromad']} />
                  <Bar dataKey="total_revenue" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
          <TopTable data={topQ.data ?? []} />
        </div>
      )}

      {/* ABC tahlil */}
      {tab === 'abc' && (
        <div className="space-y-4">
          {abcQ.isLoading ? <Loader /> : (
            ['A', 'B', 'C'].map(group => {
              const g = abcQ.data?.[group];
              if (!g) return null;
              const colors: Record<string, string> = { A: 'green', B: 'blue', C: 'orange' };
              const c = colors[group];
              return (
                <div key={group} className={`bg-white rounded-xl border border-${c}-100 p-5 shadow-sm`}>
                  <div className={`flex items-center gap-3 mb-3`}>
                    <div className={`w-10 h-10 bg-${c}-100 text-${c}-700 rounded-xl flex items-center justify-center font-bold text-lg`}>
                      {group}
                    </div>
                    <div>
                      <div className="font-bold text-gray-800">{g.count} ta mahsulot</div>
                      <div className="text-sm text-gray-500">
                        {group === 'A' ? 'Daromadning 80%' : group === 'B' ? 'Keyingi 15%' : 'Oxirgi 5%'}
                      </div>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="text-gray-400 uppercase">
                        <tr>
                          <th className="text-left py-1">Mahsulot</th>
                          <th className="text-right py-1">Daromad</th>
                          <th className="text-right py-1">Ulushi</th>
                          <th className="text-right py-1">Jami ulush</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(g.items ?? []).slice(0, 10).map((p: { product_name: string; total_revenue: number; revenue_pct: number; cumulative_pct: number }, i: number) => (
                          <tr key={i} className="border-t border-gray-50">
                            <td className="py-1 font-medium text-gray-700">{p.product_name}</td>
                            <td className="py-1 text-right text-gray-600">{fmt.price(p.total_revenue)}</td>
                            <td className="py-1 text-right text-gray-600">{fmt.pct(p.revenue_pct)}</td>
                            <td className="py-1 text-right font-bold text-gray-700">{fmt.pct(p.cumulative_pct)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Marjinallik */}
      {tab === 'margin' && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {margQ.isLoading ? <div className="p-8"><Loader /></div> : (
            <>
              {/* Xulosa */}
              {margQ.data?.summary && (
                <div className="grid grid-cols-4 gap-0 border-b border-gray-100">
                  {[
                    { l: 'Jami daromad',    v: fmt.price(margQ.data.summary.total_revenue) },
                    { l: 'Jami tannarx',    v: fmt.price(margQ.data.summary.total_cost) },
                    { l: 'Jami foyda',      v: fmt.price(margQ.data.summary.total_profit) },
                    { l: "O'rtacha marjin", v: fmt.pct(margQ.data.summary.avg_margin_pct) },
                  ].map(s => (
                    <div key={s.l} className="p-5 border-r border-gray-100 last:border-0">
                      <div className="text-xs text-gray-400 mb-1">{s.l}</div>
                      <div className="font-bold text-gray-800">{s.v}</div>
                    </div>
                  ))}
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr className="text-left text-gray-400 text-xs uppercase">
                      <th className="px-4 py-3 font-medium">Mahsulot</th>
                      <th className="px-4 py-3 font-medium text-right">Daromad</th>
                      <th className="px-4 py-3 font-medium text-right">Tannarx</th>
                      <th className="px-4 py-3 font-medium text-right">Foyda</th>
                      <th className="px-4 py-3 font-medium text-right">Marjin %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(margQ.data?.items ?? []).map((p: { product_name: string; revenue: number; cost: number; profit: number; margin_pct: number }, i: number) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-800">{p.product_name}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{fmt.price(p.revenue)}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{fmt.price(p.cost)}</td>
                        <td className="px-4 py-3 text-right font-medium text-green-600">{fmt.price(p.profit)}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex items-center gap-1">
                            <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.min(100, p.margin_pct)}%` }} />
                            </div>
                            <span className={`text-xs font-medium ${p.margin_pct > 20 ? 'text-green-600' : p.margin_pct > 0 ? 'text-orange-500' : 'text-red-500'}`}>
                              {fmt.pct(p.margin_pct)}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Kassirlar */}
      {tab === 'cashiers' && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {cashQ.isLoading ? <div className="p-8"><Loader /></div> : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-gray-400 text-xs uppercase">
                  <th className="px-4 py-3 font-medium">#</th>
                  <th className="px-4 py-3 font-medium">Kassir</th>
                  <th className="px-4 py-3 font-medium text-right">Sotuvlar</th>
                  <th className="px-4 py-3 font-medium text-right">Daromad</th>
                  <th className="px-4 py-3 font-medium text-right">O'rtacha chek</th>
                  <th className="px-4 py-3 font-medium text-right">Ish kunlari</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(cashQ.data ?? []).map((c: { cashier_name: string; total_sales: number; total_revenue: number; avg_check: number; working_days: number }, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{c.cashier_name}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{c.total_sales}</td>
                    <td className="px-4 py-3 text-right font-bold text-blue-700">{fmt.price(c.total_revenue)}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{fmt.price(c.avg_check)}</td>
                    <td className="px-4 py-3 text-right text-gray-600">{c.working_days} kun</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function TopTable({ data }: { data: { product_name: string; total_qty: number; unit: string; total_revenue: number; gross_profit: number; sale_count: number }[] }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr className="text-left text-gray-400 text-xs uppercase">
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Mahsulot</th>
              <th className="px-4 py-3 text-right">Miqdor</th>
              <th className="px-4 py-3 text-right">Daromad</th>
              <th className="px-4 py-3 text-right">Foyda</th>
              <th className="px-4 py-3 text-right">Sotuvlar</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data.map((p, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                <td className="px-4 py-3 font-medium text-gray-800">{p.product_name}</td>
                <td className="px-4 py-3 text-right text-gray-600">{fmt.qty(p.total_qty, p.unit)}</td>
                <td className="px-4 py-3 text-right font-bold text-blue-700">{fmt.price(p.total_revenue)}</td>
                <td className="px-4 py-3 text-right font-medium text-green-600">{fmt.price(p.gross_profit)}</td>
                <td className="px-4 py-3 text-right text-gray-600">{p.sale_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Loader() {
  return (
    <div className="space-y-2 animate-pulse">
      {[...Array(6)].map((_, i) => <div key={i} className="h-8 bg-gray-100 rounded-lg" />)}
    </div>
  );
}
