/**
 * Dashboard — Bugungi ko'rsatkichlar
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import {
  ShoppingCart, TrendingUp, Package, CreditCard,
  RefreshCw, ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { analyticsApi, salesApi } from '../utils/api';
import { StatCard } from '../components/StatCard';
import { fmt } from '../utils/formatters';

const PAY_COLORS: Record<string, string> = {
  cash:   '#22c55e',
  uzcard: '#3b82f6',
  humo:   '#f97316',
  payme:  '#06b6d4',
  click:  '#8b5cf6',
  uzum:   '#ec4899',
};

const today = new Date().toISOString().slice(0, 10);
const monthStart = today.slice(0, 8) + '01';

export function Dashboard() {
  const { data: dash, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn:  () => analyticsApi.dashboard().then(r => r.data),
    refetchInterval: 60_000,   // Har daqiqada yangilash
  });

  const { data: monthly } = useQuery({
    queryKey: ['sales-monthly'],
    queryFn:  () => salesApi.summary({ from: monthStart, to: today, group_by: 'day' }).then(r => r.data),
  });

  if (isLoading) return <PageLoader />;

  const todayData  = dash?.today ?? {};
  const payBreak   = dash?.payment_breakdown ?? [];
  const series     = monthly?.series ?? [];
  const topProds   = todayData.top_products ?? [];

  return (
    <div className="space-y-6">
      {/* Sarlavha */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">{fmt.date(today)} — Bugungi holat</p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 hover:border-blue-300 transition-colors"
        >
          <RefreshCw size={16} /> Yangilash
        </button>
      </div>

      {/* Statistika kartalar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Bugungi sotuvlar"
          value={todayData.sales_count ?? 0}
          sub="ta sotuv"
          icon={ShoppingCart}
          color="blue"
        />
        <StatCard
          label="Bugungi daromad"
          value={fmt.price(todayData.revenue ?? 0)}
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          label="O'rtacha chek"
          value={fmt.price(todayData.avg_check ?? 0)}
          icon={CreditCard}
          color="purple"
        />
        <StatCard
          label="Oy daromadi"
          value={fmt.price(monthly?.total_revenue ?? 0)}
          sub={`${monthly?.total_sales ?? 0} ta sotuv`}
          icon={TrendingUp}
          color="orange"
        />
      </div>

      {/* Grafiklar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Oylik daromad grafigi */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-800">Oylik daromad (so'm)</h2>
            <Link to="/reports" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
              Batafsil <ArrowRight size={12} />
            </Link>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11 }}
                tickFormatter={v => v.slice(5)}   // MM-DD
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={v => `${(v / 1_000_000).toFixed(0)}M`}
                width={40}
              />
              <Tooltip
                formatter={(v: number) => [fmt.price(v), 'Daromad']}
                labelFormatter={l => fmt.date(l)}
              />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* To'lov usullari */}
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h2 className="font-bold text-gray-800 mb-4">To'lov usullari (bugun)</h2>
          {payBreak.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={payBreak}
                    dataKey="total"
                    nameKey="method"
                    cx="50%" cy="50%"
                    outerRadius={70}
                    label={({ method, percent }) =>
                      `${method} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {payBreak.map((entry: { method: string }) => (
                      <Cell
                        key={entry.method}
                        fill={PAY_COLORS[entry.method] ?? '#94a3b8'}
                      />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt.price(v)} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1 mt-2">
                {payBreak.map((p: { method: string; total: number; count: number }) => (
                  <div key={p.method} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: PAY_COLORS[p.method] ?? '#94a3b8' }}
                      />
                      <span className="text-gray-600 capitalize">{p.method}</span>
                    </div>
                    <span className="font-medium text-gray-800">{fmt.price(p.total)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center text-gray-400 py-10 text-sm">Bugun sotuv yo'q</div>
          )}
        </div>
      </div>

      {/* Eng ko'p sotiladigan mahsulotlar */}
      <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-gray-800">Bugungi top mahsulotlar</h2>
          <Link to="/reports?tab=top_products" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
            Barchasi <ArrowRight size={12} />
          </Link>
        </div>
        {topProds.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-100">
                  <th className="pb-2 font-medium">#</th>
                  <th className="pb-2 font-medium">Mahsulot</th>
                  <th className="pb-2 font-medium text-right">Miqdor</th>
                  <th className="pb-2 font-medium text-right">Daromad</th>
                </tr>
              </thead>
              <tbody>
                {topProds.map((p: { product_name: string; total_qty: number; unit: string; total_revenue: number }, i: number) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 text-gray-400">{i + 1}</td>
                    <td className="py-2 font-medium text-gray-800">{p.product_name}</td>
                    <td className="py-2 text-right text-gray-600">{fmt.qty(p.total_qty, p.unit)}</td>
                    <td className="py-2 text-right font-bold text-blue-700">{fmt.price(p.total_revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-400 py-8 text-sm">Bugun sotuv ma'lumotlari yo'q</div>
        )}
      </div>
    </div>
  );
}

function PageLoader() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-gray-200 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 h-64 bg-gray-200 rounded-xl" />
        <div className="h-64 bg-gray-200 rounded-xl" />
      </div>
    </div>
  );
}
